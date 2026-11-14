"""Exercise delivery's native staged Flux renderer with real SOPS and retained inputs."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml
from jinja2 import Environment, StrictUndefined

try:
    import kubernetes_validate
except ImportError:
    kubernetes_validate = None

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
import test_tier_delivery_platform as delivery
import test_tier_spinnaker_reference as spinnaker


ROLE = UPSTREAM / "tier-1/ansible/roles/delivery_platform"
NATIVE_FLUX = delivery.NATIVE and all(shutil.which(tool) for tool in ("kustomize", "sops", "age-keygen"))
SERVICES = ["clouddriver", "echo", "fiat", "front50", "orca"]


class DeliveryFlux(TierRepositoryTestCase):
    def fixture(self, **overrides):
        key = Path(self.temp.name) / "age-key"
        if not key.exists():
            subprocess.run(["age-keygen", "-o", str(key)], check=True, capture_output=True, text=True)
        recipient = subprocess.run(["age-keygen", "-y", str(key)], check=True,
                                   capture_output=True, text=True).stdout.strip()
        root = Path(self.temp.name) / "platform-source"
        root.mkdir(exist_ok=True)
        subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
        (root / "clusters/tier1").mkdir(parents=True, exist_ok=True)
        credentials = {
            "spinnaker/spinnaker-mysql-root": {"password": "R" * 48},
            "spinnaker/spinnaker-redis-auth": {"password": "D" * 48},
            "spinnaker/spinnaker-keystore": {"password": "K" * 48},
            "spinnaker/spinnaker-oidc": {"clientSecret": "offline-private-client-fixture"},
            "spinnaker/spinnaker-backup": {
                "RESTIC_PASSWORD": "offline-private-retained-restic-password-32",
                "AWS_ACCESS_KEY_ID": "offline-access-key",
                "AWS_SECRET_ACCESS_KEY": "offline-object-storage-secret",
            },
        }
        for service in SERVICES:
            credentials[f"spinnaker/spinnaker-{service}-db"] = {
                "password": "P" * 48, "migration-password": "M" * 48}
        binary = base64.b64encode(b"offline-private-tls-keystore-fixture").decode()
        tls = {f"spinnaker/{service}-tls": dict.fromkeys(
            ["tls.crt", "tls.key", "ca.crt", "keystore.p12"], binary)
            for service in ["spinnaker", "spinnaker-mysql", "spinnaker-redis", *SERVICES, "gate", "rosco"]}
        return dict(delivery.DeliveryPlatform.inputs(self), **{
            **spinnaker.SpinnakerReference.native_inputs(self),
            "delivery_platform_owner": "flux",
            "delivery_platform_controller": "spinnaker",
            "delivery_platform_kubeconfig": "/does-not-exist/offline-kubeconfig",
            "delivery_platform_install_harbor": False,
            "delivery_platform_spinnaker_host": "spin.lab.test",
            "delivery_platform_spinnaker_delivery_mode": "flux",
            "delivery_platform_spinnaker_lifecycle": "fresh",
            "delivery_platform_manage_secrets": True,
            "delivery_platform_secrets": credentials,
            "delivery_platform_flux_output": str(root / "clusters/tier1"),
            "delivery_platform_flux_sops_age_recipients": [recipient],
            "delivery_platform_flux_secret_data": tls,
            **overrides,
        })

    def render(self, inputs, repo=None):
        result = delivery.DeliveryPlatform.run_role(self, repo or UPSTREAM / "tier-1", inputs,
                                                   {"CONTROL_NODE_COLLECTIONS_MODE": "check"}, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-14000:] + result.stderr[-4000:])
        for name in ("Inspect the selected persistent storage provisioner",
                     "Check every existing credential before changing any release"):
            output = result.stdout.split(f"TASK [delivery_platform : {name}]", 1)[1].split("\nTASK [", 1)[0]
            self.assertIn("skipping:", output)
        self.assertNotIn("TASK [delivery_platform : Create only the selected", result.stdout)
        self.assertNotIn("TASK [helm_release :", result.stdout)
        root = Path(inputs["delivery_platform_flux_output"]) / "platform/delivery"
        graph = [item for item in yaml.safe_load_all((root / "reconciliation.yaml").read_text()) if item]
        resources = {}
        for node in graph:
            name = node["metadata"]["name"]
            relative = Path(node["spec"]["path"]).relative_to("clusters/tier1")
            path = Path(inputs["delivery_platform_flux_output"]) / relative / "resources.yaml"
            content = path.read_text()
            if "sops:" in content:
                content = subprocess.run(
                    ["sops", "--decrypt", str(path)], check=True, capture_output=True, text=True,
                    env=dict(os.environ, SOPS_AGE_KEY_FILE=str(Path(self.temp.name) / "age-key")),
                ).stdout
            resources[name] = [item for item in yaml.safe_load_all(content) if item]
            spec = node["spec"]
            self.assertEqual(spec["sourceRef"], {"kind": "GitRepository", "name": "tier1-platform"})
            self.assertEqual(spec["serviceAccountName"], "platform-reconciler")
            self.assertFalse(spec["prune"])
            self.assertFalse(spec["force"])
            self.assertEqual(spec["deletionPolicy"], "Orphan")
        return root, graph, resources

    def test_native_entry_points_route_flux_to_shared_renderer_and_keep_legacy_defaults(self):
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        self.assertEqual(defaults["delivery_platform_owner"], "ansible")
        self.assertEqual(defaults["delivery_platform_spinnaker_delivery_mode"], "direct")
        tasks = yaml.safe_load((ROLE / "tasks/flux.yml").read_text())
        renderer = tasks[-1]
        self.assertEqual(renderer["ansible.builtin.include_role"]["name"], "flux_payload")
        self.assertEqual(renderer["vars"]["flux_payload_source_name"], "tier1-platform")
        self.assertFalse(any("kubernetes.core.k8s" in task for task in tasks))

    def test_data_guard_retains_claim_identity_and_requires_an_explicit_recovery_marker(self):
        environment = Environment(undefined=StrictUndefined, trim_blocks=True)
        environment.filters["to_json"] = json.dumps
        environment.filters["hash"] = lambda value, algorithm: hashlib.new(algorithm, value.encode()).hexdigest()
        template = environment.from_string((ROLE / "templates/spinnaker/flux-data-guard.yml.j2").read_text())
        for lifecycle in ("fresh", "adopt", "recover"):
            guard = yaml.safe_load(template.render(
                delivery_platform_spinnaker_namespace="spinnaker", delivery_platform_spinnaker_lifecycle=lifecycle,
                delivery_platform_spinnaker_job_revision="1", delivery_platform_spinnaker_recovery_id="accepted-recovery",
                delivery_platform_software=yaml.safe_load((ROLE / "files/software.yml").read_text())))
            self.assertNotIn("ttlSecondsAfterFinished", guard["spec"])
            pod = guard["spec"]["template"]["spec"]
            self.assertEqual({volume["persistentVolumeClaim"]["claimName"] for volume in pod["volumes"]},
                             {"data-spinnaker-mysql-0", "data-spinnaker-redis-0"})
            script = pod["containers"][0]["args"][0]
            self.assertEqual("Fresh initialization requires empty" in script, lifecycle == "fresh")
            self.assertEqual(".delivery-restored" in script, lifecycle == "recover")
            if os.name != "nt" and shutil.which("sh"):
                mounts = Path(self.temp.name) / lifecycle
                for name in ("mysql", "redis"):
                    (mounts / name).mkdir(parents=True)
                script = re.sub(r"(?<![\w/])/(mysql|redis)\b",
                                lambda match: str(mounts / match.group(1)), script)
                run = lambda: subprocess.run(["sh", "-ec", script], capture_output=True, text=True,
                                             env=dict(os.environ, RECOVERY_ID="accepted-recovery"))
                empty = run()
                self.assertEqual(empty.returncode == 0, lifecycle == "fresh", empty.stderr)
                (mounts / "mysql/mysql").mkdir()
                (mounts / "redis/appendonlydir").mkdir()
                if lifecycle == "recover":
                    for name in ("mysql", "redis"):
                        (mounts / name / ".delivery-restored").write_text("accepted-recovery")
                existing = run()
                self.assertEqual(existing.returncode == 0, lifecycle != "fresh", existing.stderr)
                if lifecycle == "recover":
                    (mounts / "mysql/.delivery-restored").write_text("unaccepted-recovery")
                    self.assertNotEqual(run().returncode, 0)

    def test_flux_accounts_and_fiat_use_the_promotion_roles_and_application_permissions(self):
        inputs = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        promotion = yaml.safe_load((UPSTREAM / "tier-1/ansible/roles/delivery_promotion/defaults/main.yml").read_text())
        groups = [inputs["delivery_platform_spinnaker_" + name + "_group"]
                  for name in ("admin", "reader", "writer", "promotion_requester", "promotion_approver", "promotion_executor")]
        for name in ("requester", "approver", "executor"):
            self.assertEqual(inputs[f"delivery_platform_spinnaker_promotion_{name}_group"],
                             promotion[f"delivery_promotion_{name}_role"])
        inputs.update(delivery_platform_spinnaker_delivery_mode="flux", delivery_platform_spinnaker_namespace="spinnaker",
                      spinnaker_native_sql_services=SERVICES, spinnaker_native_identity_groups=groups,
                      spinnaker_native_account_namespaces=["app", "delivery-promotion"])
        environment = Environment(undefined=StrictUndefined, trim_blocks=True)
        environment.filters.update(to_json=json.dumps, regex_escape=re.escape)
        template = environment.from_string((ROLE / "templates/spinnaker/service.yml.j2").read_text())
        clouddriver = yaml.safe_load(template.render(inputs, spinnaker_native_service="clouddriver"))
        accounts = {item["name"]: item for item in clouddriver["kubernetes"]["accounts"]}
        self.assertEqual(accounts["delivery-promotion"]["permissions"]["WRITE"],
                         [groups[0], promotion["delivery_promotion_executor_role"]])
        self.assertTrue(all(account["serviceAccount"] for account in accounts.values()))
        self.assertFalse(accounts["app"]["onlySpinnakerManaged"])
        fiat = yaml.safe_load(template.render(inputs, spinnaker_native_service="fiat"))
        permissions = fiat["auth"]["permissions"]["source"]["application"]
        self.assertTrue(permissions["resource"]["enabled"])
        self.assertFalse(permissions["prefix"]["enabled"])
        gate = yaml.safe_load(template.render(inputs, spinnaker_native_service="gate"))
        requirement = gate["spring"]["security"]["oauth2"]["client"]["registration"]["user-info-requirements"]["groups"]
        self.assertTrue(all(re.fullmatch(requirement.strip("/"), group) for group in groups))

    @unittest.skipUnless(delivery.NATIVE and os.environ.get("NATIVE_CHART_CACHE"),
                         "Requires native Helm and the pinned offline Harbor chart")
    def test_harbor_flux_values_keep_existing_internal_certificates_across_chart_renders(self):
        inputs = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        credentials = {f"harbor/harbor-{name}-internal-tls": {
            "ca.crt": "offline-retained-ca", "tls.crt": f"offline-retained-{name}-certificate",
            "tls.key": f"offline-retained-{name}-key"}
            for name in ("core", "jobservice", "registry", "portal", "trivy")}
        inputs.update(delivery_platform_owner="flux", delivery_platform_secrets=credentials,
                      delivery_platform_ingress_class="accepted-ingress", delivery_platform_harbor_host="harbor.lab.test",
                      delivery_platform_harbor_storage_class="persistent",
                      delivery_platform_harbor_database_password="offline-retained-database-password")
        environment = Environment(undefined=StrictUndefined, trim_blocks=True)
        environment.filters["to_json"] = json.dumps
        template = environment.from_string((ROLE / "templates/harbor-values.yml.j2").read_text())
        values = Path(self.temp.name) / "harbor-values.yml"
        values.write_text(template.render(inputs))
        pin = yaml.safe_load((ROLE / "files/software.yml").read_text())["harbor_chart"]
        chart = Path(os.environ["NATIVE_CHART_CACHE"]) / f"harbor-{pin}.tgz"
        for _ in range(2):
            result = subprocess.run(["helm", "template", "harbor", str(chart), "--namespace", "harbor",
                                     "--values", str(values)], check=True, capture_output=True, text=True)
            secrets = {f"harbor/{obj['metadata']['name']}": obj for obj in yaml.load_all(
                result.stdout, Loader=yaml.CSafeLoader) if obj and obj["kind"] == "Secret"}
            for name, secret in credentials.items():
                self.assertEqual({key: base64.b64decode(value).decode() for key, value in secrets[name]["data"].items()}, secret)

    @unittest.skipUnless(os.name != "nt" and shutil.which("sh"), "Requires a native shell")
    def test_database_verification_does_not_reinitialize_or_rotate_restored_users(self):
        tools = Path(self.temp.name) / "tools"
        tools.mkdir()
        client = tools / "mysql"
        client.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$SQL_LOG"\n')
        client.chmod(0o700)
        log = Path(self.temp.name) / "sql.log"
        result = subprocess.run(["sh", str(ROLE / "files/spinnaker/initialize-databases.sh")],
                                env=dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"],
                                         SQL_LOG=str(log), SPINNAKER_DATABASE_ACTION="verify"),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = log.read_text()
        self.assertEqual(calls.count("--execute=SELECT 1"), 5)
        self.assertFalse(any(statement in calls for statement in ("CREATE", "ALTER", "GRANT")))

    @unittest.skipUnless(NATIVE_FLUX and kubernetes_validate, "Requires native Flux tools and kubernetes-validate schemas")
    def test_staged_source_and_generated_render_preserve_data_and_encrypt_secret_material(self):
        self.generate()
        inputs = self.fixture()
        previous_resources = None
        for repo in (UPSTREAM / "tier-1", self.root / "verify-tier-1"):
            with self.subTest(repo=repo):
                root, graph, resources = self.render(inputs, repo)
                if previous_resources is not None:
                    self.assertEqual(previous_resources, resources)
                previous_resources = resources
                prefix = "platform-delivery-spinnaker"
                phases = ["prerequisites", "data-guard", "persistence", "databases", "workloads",
                          "backup-verification", "publication"]
                nodes = {node["metadata"]["name"]: node for node in graph}
                previous_stage = "platform-delivery-inputs"
                for phase in phases:
                    name = f"{prefix}-{phase}"
                    self.assertEqual(nodes[name]["spec"]["dependsOn"], [{"name": previous_stage}])
                    previous_stage = name
                prerequisite = resources[f"{prefix}-prerequisites"]
                claims = {item["metadata"]["name"] for item in prerequisite if item["kind"] == "PersistentVolumeClaim"}
                self.assertTrue({"data-spinnaker-mysql-0", "data-spinnaker-redis-0"}.issubset(claims))
                for phase, objects in resources.items():
                    for obj in objects:
                        if kubernetes_validate and obj["apiVersion"] != "traefik.io/v1alpha1":
                            kubernetes_validate.validate(obj, "1.33.0", strict=True)
                        if obj["kind"] == "Job":
                            self.assertNotIn("ttlSecondsAfterFinished", obj["spec"])
                            self.assertNotEqual(obj["metadata"]["name"], "spinnaker-databases")
                            health = nodes[phase]["spec"]["healthChecks"]
                            self.assertIn(obj["metadata"]["name"], [item["name"] for item in health])
                self.assertEqual({item["kind"] for item in resources[f"{prefix}-publication"]}, {"Ingress", "CronJob"})
                for path in root.rglob("*"):
                    if path.is_file():
                        text = path.read_text()
                        self.assertNotIn("offline-private", text)
                        self.assertNotIn(inputs["delivery_platform_secrets"]["spinnaker/spinnaker-mysql-root"]["password"], text)
                roles = [item for item in prerequisite if item["kind"] == "Role"]
                for role in roles:
                    writes = [rule for rule in role["rules"] if set(rule["verbs"]) - {"get", "list", "watch"}]
                    if writes:
                        self.assertEqual(role["metadata"]["namespace"], "delivery-promotion")
                        self.assertEqual(writes[0]["resources"], ["jobs"])
                        self.assertEqual(set(writes[0]["verbs"]), {"get", "list", "watch", "create", "delete"})
                self.assertFalse(any(item["kind"] == "Secret" and item.get("type") == "kubernetes.io/service-account-token"
                                     for objects in resources.values() for item in objects))
                recipe = yaml.safe_load((Path(inputs["delivery_platform_output"]) / "spinnaker-revoke-direct-access.yml").read_text())
                removals = recipe[0]["tasks"][1]["kubernetes.core.k8s"]["definition"]
                self.assertTrue(any(obj["kind"] == "Secret" and obj["metadata"]["name"] == "spinnaker-deployer-token"
                                    for obj in removals))

    @unittest.skipUnless(NATIVE_FLUX, "Requires native Ansible, Helm, Kustomize, SOPS and age")
    def test_recovery_fences_executors_and_publication_until_explicit_data_restoration(self):
        inputs = self.fixture(delivery_platform_spinnaker_lifecycle="recover",
                              delivery_platform_spinnaker_recovery_id="offline-accepted-recovery-01",
                              delivery_platform_spinnaker_recovery_fenced=True)
        _, _, resources = self.render(inputs)
        objects = [obj for stage in resources.values() for obj in stage]
        deployments = {obj["metadata"]["name"]: obj for obj in objects if obj["kind"] == "Deployment"}
        self.assertTrue(all(deployments[name]["spec"]["replicas"] == 0 for name in ("echo", "orca", "gate")))
        self.assertFalse(any(obj["kind"] == "Ingress" for obj in objects))
        cron = next(obj for obj in objects if obj["kind"] == "CronJob")
        self.assertTrue(cron["spec"]["suspend"])
        guard = next(obj for obj in objects if obj["kind"] == "Job" and obj["metadata"]["name"].startswith("spinnaker-data-"))
        self.assertIn(".delivery-restored", guard["spec"]["template"]["spec"]["containers"][0]["args"][0])
        database = next(obj for obj in objects if obj["kind"] == "Job" and obj["metadata"]["name"].startswith("spinnaker-databases-"))
        env = database["spec"]["template"]["spec"]["containers"][0]["env"]
        self.assertIn({"name": "SPINNAKER_DATABASE_ACTION", "value": "verify"}, env)


if __name__ == "__main__":
    unittest.main()
