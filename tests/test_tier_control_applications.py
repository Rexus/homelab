"""Tier 0 product contracts and opt-in, real pinned Helm rendering without Kubernetes."""

import base64
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import urllib.request

import jinja2
import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "tier-0/ansible/roles/control_applications"
EXAMPLE = ROOT / "tier-0/ansible/group_vars/control_applications.yml.example"


def fixture():
    values = yaml.safe_load(EXAMPLE.read_text())
    values.update({
        "control_applications_components": ["keycloak", "vault", "netbox", "headlamp"],
        "control_applications_hosts": {
            product: f"{product}.lab.test" for product in ("keycloak", "vault", "netbox", "headlamp")
        },
        "control_applications_ingress_class": "accepted-ingress",
        "control_applications_storage_class": "accepted-storage",
        "control_applications_oidc_issuer": "https://keycloak.lab.test/realms/platform",
        "control_applications_vault_token": "PRIVATE-RENDER-SENTINEL",
    })
    return values


def rendered_releases(overrides=None):
    """Exercise structured product templates on hosts without native Ansible."""
    values = yaml.safe_load((ROLE / "defaults/main.yml").read_text()) | fixture() | (overrides or {})
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(ROLE / "templates"), undefined=jinja2.StrictUndefined,
        trim_blocks=True, lstrip_blocks=True,
    )
    environment.filters.update({
        "to_json": json.dumps, "from_yaml": yaml.safe_load,
        "from_yaml_all": yaml.safe_load_all,
        "combine": lambda left, right: left | right,
    })

    def lookup(_plugin, name, template_vars=None):
        return environment.get_template(name).render(values | (template_vars or {}))

    environment.globals["lookup"] = lookup
    return yaml.safe_load(environment.get_template("releases.yml.j2").render(values))


class ControlApplicationContracts(unittest.TestCase):
    def test_tier_oidc_examples_are_public_additions_and_match_headlamp(self):
        patches = [yaml.safe_load((ROOT / f"tier-{tier}/terraform/deployments/kubernetes/"
                                  "oidc-machine-config.yaml.example").read_text()) for tier in range(3)]
        self.assertEqual(patches, [patches[0]] * 3)
        patch = patches[0]
        self.assertEqual(set(patch["machine"]), {"files"})
        self.assertEqual(set(patch["cluster"]), {"apiServer"})
        args = patch["cluster"]["apiServer"]["extraArgs"]
        self.assertTrue(all(key.startswith("oidc-") for key in args))
        self.assertEqual(args["oidc-client-id"], "headlamp")
        self.assertEqual(args["oidc-username-claim"], "sub")
        self.assertEqual(args["oidc-groups-prefix"] + "platform-viewers", fixture()["control_applications_headlamp_group"])
        self.assertEqual(patch["cluster"]["apiServer"]["extraVolumes"][0]["readonly"], True)
        self.assertEqual(patch["machine"]["files"][0]["permissions"], 0o644)

    def test_databases_use_cnpg_and_external_certificate_custody(self):
        releases = {release["name"]: release for release in rendered_releases()}
        for product in ("keycloak", "netbox"):
            database = next(obj for obj in releases[product]["before"] if obj["kind"] == "Cluster")
            self.assertEqual(database["apiVersion"], "postgresql.cnpg.io/v1")
            spec = database["spec"]
            self.assertEqual(spec["instances"], 3)
            self.assertFalse(spec["enableSuperuserAccess"])
            self.assertEqual(spec["bootstrap"]["initdb"]["owner"], product)
            self.assertEqual(spec["bootstrap"]["initdb"]["secret"]["name"], f"{product}-db")
            self.assertEqual(set(spec["certificates"]), {
                "serverCASecret", "clientCASecret", "serverTLSSecret", "replicationTLSSecret",
            })
            keys = {secret["name"]: secret["keys"] for secret in releases[product]["required_secrets"]}
            self.assertEqual(keys[f"{product}-db"], ["username", "password"])
            self.assertEqual(keys[f"{product}-db-replication"], ["tls.crt", "tls.key"])
            self.assertTrue(spec["plugins"][0]["isWALArchiver"])
            self.assertEqual(spec["plugins"][0]["parameters"]["barmanObjectName"], f"{product}-db-backup")
            store = next(obj for obj in releases[product]["before"] if obj["kind"] == "ObjectStore")
            self.assertEqual(store["spec"]["retentionPolicy"], "30d")
            self.assertEqual(store["spec"]["configuration"]["wal"]["compression"], "gzip")
            self.assertTrue(any(obj["kind"] == "ScheduledBackup" for obj in releases[product]["before"]))
            self.assertTrue(any(obj["kind"] == "Backup" for obj in releases[product]["after"]))

    def test_database_readiness_precedes_application_helm(self):
        tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
        database = next(index for index, task in enumerate(tasks)
                        if task.get("ansible.builtin.include_tasks") == "database.yml")
        applications = next(index for index, task in enumerate(tasks)
                            if task.get("ansible.builtin.include_role", {}).get("name") == "kubernetes_applications")
        self.assertLess(database, applications)
        preparation = yaml.safe_load((ROLE / "tasks/database.yml").read_text())
        self.assertEqual(preparation[-1]["kubernetes.core.k8s_info"]["wait_condition"],
                         {"type": "Ready", "status": "True"})

    def test_selection_preserves_dependency_order_and_vault_ceremony(self):
        releases = rendered_releases({"control_applications_components": ["headlamp", "vault"]})
        self.assertEqual([release["name"] for release in releases], ["vault", "headlamp"])
        vault = releases[0]
        self.assertFalse(vault["wait"])
        server = vault["values"]["server"]
        self.assertTrue(server["auditStorage"]["enabled"])
        self.assertTrue(server["dataStorage"]["enabled"])
        self.assertEqual(server["ha"]["replicas"], 3)
        self.assertTrue(server["ha"]["raft"]["enabled"])
        self.assertEqual(server["readinessProbe"]["path"], "/v1/sys/health?standbyok=true")
        self.assertEqual(server["ha"]["raft"]["config"].count("retry_join {"), 3)
        configured = rendered_releases({"control_applications_vault_phase": "configure"})[1]
        self.assertTrue(configured["wait"])

    def test_vault_enables_both_persistent_and_stdout_native_audit_devices(self):
        tasks = yaml.safe_load((ROLE / "tasks/vault.yml").read_text())[1]["block"]
        audit = next(task for task in tasks if "loop" in task and "community.hashi_vault.vault_write" in task)
        self.assertEqual(audit["loop"], [
            {"name": "file", "destination": "/vault/audit/audit.json"},
            {"name": "stdout", "destination": "stdout"},
        ])
        self.assertEqual(audit["community.hashi_vault.vault_write"]["data"]["type"], "file")

    def test_headlamp_has_only_namespace_view_bindings_for_human_group(self):
        release = next(obj for obj in rendered_releases() if obj["name"] == "headlamp")
        self.assertFalse(release["values"]["clusterRoleBinding"]["create"])
        self.assertFalse(release["values"]["config"]["unsafeUseServiceAccountToken"])
        self.assertEqual({obj["metadata"]["namespace"] for obj in release["before"]}, {"headlamp", "netbox"})
        for binding in release["before"]:
            self.assertEqual(binding["kind"], "RoleBinding")
            self.assertEqual(binding["roleRef"]["name"], "view")
            self.assertEqual(binding["subjects"], [{
                "kind": "Group", "name": "oidc:platform-viewers", "apiGroup": "rbac.authorization.k8s.io",
            }])

    def test_netbox_native_dependencies_and_no_implicit_privileges(self):
        release = next(obj for obj in rendered_releases() if obj["name"] == "netbox")
        values = release["values"]
        self.assertFalse(values["postgresql"]["enabled"])
        self.assertFalse(values["valkey"]["enabled"])
        self.assertEqual(values["externalDatabase"]["options"]["sslmode"], "verify-full")
        self.assertTrue(values["tasksDatabase"]["ssl"])
        self.assertEqual(values["tasksDatabase"]["database"], 0)
        self.assertEqual(values["cachingDatabase"]["database"], 1)
        self.assertEqual(values["remoteAuth"]["defaultPermissions"], {})
        self.assertEqual(values["remoteAuth"]["superuserGroups"], [])
        cache = next(obj for obj in release["before"] if obj["kind"] == "StatefulSet")
        self.assertEqual(cache["spec"]["replicas"], 1)
        self.assertEqual(cache["spec"]["template"]["spec"]["containers"][0]["command"],
                         ["valkey-server", "/etc/valkey/valkey.conf"])
        self.assertTrue(cache["spec"]["volumeClaimTemplates"])


@unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"), "Requires native Ansible")
class ControlApplicationGates(unittest.TestCase):
    def test_api_arguments_match_installed_native_modules(self):
        modules = {}

        def collect(tasks):
            for task in tasks:
                for name, arguments in task.items():
                    if name.startswith(("community.general.", "community.hashi_vault.")):
                        modules.setdefault(name, []).append(arguments)
                collect(task.get("block", []))

        for file in (ROLE / "tasks").glob("*.yml"):
            collect(yaml.safe_load(file.read_text()))
        result = subprocess.run(["ansible-doc", "--json", *modules], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        documentation = json.loads(result.stdout)
        for name, calls in modules.items():
            options = documentation[name]["doc"]["options"]
            allowed = set(options) | {alias for option in options.values() for alias in option.get("aliases", [])}
            for arguments in calls:
                self.assertFalse(set(arguments) - allowed, (name, set(arguments) - allowed))

    def test_native_api_module_tasks_pass_ansible_syntax_check(self):
        with tempfile.TemporaryDirectory(prefix="control-apps-api-") as directory:
            play = Path(directory) / "api.yml"
            play.write_text(yaml.safe_dump([{
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "tasks": [{"ansible.builtin.import_role": {"name": str(ROLE), "tasks_from": name}}
                          for name in ("keycloak", "clients", "vault", "kubernetes-sso")],
            }]))
            result = subprocess.run(
                ["ansible-playbook", "-i", "localhost,", str(play), "--syntax-check"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_incomplete_apply_and_broad_access_fail_before_execution(self):
        cases = [
            {"control_applications_action": "apply"},
            {"control_applications_components": ["unknown"]},
            {"control_applications_versions": {"keycloak": "latest"}},
            {"control_applications_components": ["headlamp"], "control_applications_headlamp_group": "system:masters"},
            {"control_applications_components": ["headlamp"], "control_applications_headlamp_namespaces": ["*"]},
            {"control_applications_ldap_url": "ldap://directory.lab.test"},
            {"control_applications_components": ["vault"], "control_applications_vault_replicas": 2},
            {"control_applications_components": ["vault"], "control_applications_vault_phase": "accept",
             "control_applications_action": "apply", "control_applications_kubeconfig": "/nonexistent",
             "control_applications_platform_accepted": True, "control_applications_recovery_custody_accepted": True},
        ]
        with tempfile.TemporaryDirectory(prefix="control-apps-gates-") as directory:
            play = Path(directory) / "preflight.yml"
            play.write_text(yaml.safe_dump([{
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "tasks": [{"ansible.builtin.include_role": {
                    "name": str(ROLE), "tasks_from": "preflight",
                }}],
            }]))
            for case in cases:
                with self.subTest(case=case):
                    result = subprocess.run(
                        ["ansible-playbook", "-i", "localhost,", str(play), "-e", json.dumps(fixture() | case)],
                        capture_output=True, text=True,
                    )
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("assertion", result.stdout.lower(), result.stdout + result.stderr)


@unittest.skipUnless(os.environ.get("HOMELAB_TALOSCTL"), "Set HOMELAB_TALOSCTL to the native Talos 1.13 CLI")
class NativeTalosOIDC(unittest.TestCase):
    """Ephemeral test-only credentials; no live API, Terraform apply or installer key generation."""

    @classmethod
    def cli(cls, *arguments):
        result = subprocess.run([os.environ["HOMELAB_TALOSCTL"], *map(str, arguments)],
                                capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        return result

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="control-apps-talos-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        cls.cli("gen", "config", "oidc-offline-test", "https://api.lab.test:6443",
                "--output", cls.root, "--talos-version", "v1.13.0", "--kubernetes-version", "1.36.0",
                "--with-docs=false", "--with-examples=false")
        generated = next(obj for obj in yaml.safe_load_all((cls.root / "controlplane.yaml").read_text())
                         if obj.get("version") == "v1alpha1")
        cls.ca = base64.b64decode(generated["cluster"]["ca"]["crt"]).decode()
        cls.baseline_patch = cls.root / "baseline.patch.yaml"
        cls.baseline_patch.write_text(yaml.safe_dump({
            "machine": {"features": {"kubePrism": {"enabled": True, "port": 7445}},
                        "logging": {"destinations": [{"endpoint": "tcp://127.0.0.1:6051", "format": "json_lines"}]}},
            "cluster": {"network": {"cni": {"name": "none"}}, "proxy": {"disabled": True},
                        "apiServer": {"extraArgs": {"audit-log-path": "/var/log/audit/kubernetes.log"},
                                      "auditPolicy": {"apiVersion": "audit.k8s.io/v1", "kind": "Policy",
                                                      "rules": [{"level": "Metadata"}]}}},
        }))
        cls.baseline = cls.root / "baseline.yaml"
        cls.cli("machineconfig", "patch", cls.root / "controlplane.yaml", "--patch",
                f"@{cls.baseline_patch}", "--output", cls.baseline)

    def patch(self, tier=0):
        patch = yaml.safe_load((ROOT / f"tier-{tier}/terraform/deployments/kubernetes/"
                               "oidc-machine-config.yaml.example").read_text())
        patch["machine"]["files"][0]["content"] = self.ca
        return patch

    def desired(self, name, source, patch):
        patch_file = self.root / f"{name}.patch.yaml"
        output = self.root / f"{name}.yaml"
        patch_file.write_text(yaml.safe_dump(patch))
        self.cli("machineconfig", "patch", source, "--patch", f"@{patch_file}", "--output", output)
        self.cli("validate", "--config", output, "--mode", "metal", "--strict")
        return output

    def test_native_talos_schema_for_all_tiers_and_both_node_types(self):
        for tier in range(3):
            for node_type, source in (("controlplane", self.baseline), ("worker", self.root / "worker.yaml")):
                with self.subTest(tier=tier, node_type=node_type):
                    self.desired(f"tier{tier}-{node_type}", source, self.patch(tier))

    def test_native_merge_preserves_bootstrap_x509_network_and_audit(self):
        before_docs = list(yaml.safe_load_all(self.baseline.read_text()))
        after_docs = list(yaml.safe_load_all(self.desired("preserve", self.baseline, self.patch()).read_text()))
        before = next(obj for obj in before_docs if obj.get("version") == "v1alpha1")
        after = next(obj for obj in after_docs if obj.get("version") == "v1alpha1")
        self.assertEqual([obj for obj in after_docs if obj is not after],
                         [obj for obj in before_docs if obj is not before])
        for path in (("machine", "ca"), ("machine", "features"), ("machine", "logging"),
                     ("cluster", "ca"), ("cluster", "aggregatorCA"), ("cluster", "serviceAccount"),
                     ("cluster", "network"), ("cluster", "proxy")):
            self.assertEqual(after[path[0]][path[1]], before[path[0]][path[1]], path)
        self.assertEqual(after["cluster"]["apiServer"]["auditPolicy"], before["cluster"]["apiServer"]["auditPolicy"])
        self.assertEqual(after["cluster"]["apiServer"]["extraArgs"]["audit-log-path"],
                         before["cluster"]["apiServer"]["extraArgs"]["audit-log-path"])

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"), "Requires native Ansible")
    def test_native_ansible_offline_render_and_refusal_gates(self):
        desired = self.desired("ansible", self.baseline, self.patch())
        nodes = {f"cp-{index}": {"ip": f"192.0.2.{index}", "role": "controlplane"} for index in range(1, 4)}
        plan = {"variables": {"cluster": {"value": {"talos_version": "v1.13.0"}},
                              "machine_config_patches": {"value": [yaml.safe_dump(self.patch())]}},
                "planned_values": {"outputs": {"nodes": {"value": nodes}, "machine_configurations": {
                    "value": {name: desired.read_text() for name in nodes}}}}}
        plan_file = self.root / "plan.json"
        play = self.root / "sso.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "connection": "local", "gather_facts": False,
            "tasks": [{"ansible.builtin.include_role": {"name": str(ROLE), "tasks_from": "kubernetes-sso"}}],
        }]))
        inputs = {"control_applications_sso_plan": str(plan_file),
                  "control_applications_sso_output": str(self.root / "render"),
                  "control_applications_sso_talosctl": os.environ["HOMELAB_TALOSCTL"],
                  "control_applications_oidc_issuer": self.patch()["cluster"]["apiServer"]["extraArgs"]["oidc-issuer-url"]}
        cases = [("valid", plan, True), ("wrong-schema", copy.deepcopy(plan), False),
                 ("x509-mutation", copy.deepcopy(plan), False), ("vm-replacement", copy.deepcopy(plan), False)]
        cases[1][1]["variables"]["cluster"]["value"]["talos_version"] = "v1.14.0"
        unsafe = self.patch()
        unsafe["cluster"]["apiServer"]["extraArgs"]["client-ca-file"] = "/bad/ca.crt"
        cases[2][1]["variables"]["machine_config_patches"]["value"] = [yaml.safe_dump(unsafe)]
        cases[3][1]["resource_changes"] = [{"type": "proxmox_virtual_environment_vm", "change": {"actions": ["create"]}}]
        update = {"type": "talos_machine_configuration_apply", "index": "cp-1", "change": {
            "actions": ["update"], "before": {"client_configuration": {"test": "unchanged"}},
            "after": {"apply_mode": "auto", "config_patches": None,
                      "machine_configuration_input": desired.read_text(), "node": nodes["cp-1"]["ip"],
                      "client_configuration": {"test": "unchanged"}},
        }}
        valid_update = copy.deepcopy(plan) | {"resource_changes": [update]}
        forced_reboot = copy.deepcopy(valid_update)
        forced_reboot["resource_changes"][0]["change"]["after"]["apply_mode"] = "reboot"
        cases.extend([("valid-provider-update", valid_update, True), ("forced-provider-reboot", forced_reboot, False)])
        for name, candidate, success in cases:
            with self.subTest(name=name):
                plan_file.write_text(json.dumps(candidate))
                result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(play), "-e", json.dumps(inputs)],
                                        capture_output=True, text=True, timeout=180)
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        for output in (self.root / "render").iterdir():
            self.assertEqual(output.stat().st_mode & 0o077, 0, output)

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"), "Requires native Ansible")
    def test_native_guard_rejects_audit_removal_and_skips_duplicate_patch(self):
        output = self.root / "compare"
        output.mkdir(exist_ok=True, mode=0o700)
        (output / "cp.current.yaml").write_text(self.baseline.read_text())
        (output / "oidc.patch.yaml").write_text(yaml.safe_dump(self.patch()))
        good = self.desired("guard", self.baseline, self.patch())
        desired = output / "cp.desired.canonical.yaml"
        play = self.root / "compare.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "connection": "local", "gather_facts": False,
            "tasks": [{"ansible.builtin.include_role": {"name": str(ROLE), "tasks_from": "sso-compare"}}],
        }]))
        inputs = {"control_applications_sso_output": str(output), "sso_node": {"key": "cp"},
                  "control_applications_sso_talosctl": os.environ["HOMELAB_TALOSCTL"]}
        for name in ("valid", "audit-removed", "already-installed"):
            candidate = list(yaml.safe_load_all(good.read_text()))
            if name == "audit-removed":
                next(obj for obj in candidate if obj.get("version") == "v1alpha1")["cluster"]["apiServer"].pop("auditPolicy")
            if name == "already-installed":
                (output / "cp.current.yaml").write_text(good.read_text())
            desired.write_text(yaml.safe_dump_all(candidate))
            result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(play), "-e", json.dumps(inputs)],
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode == 0, name != "audit-removed", result.stdout + result.stderr)
            if name == "already-installed":
                self.assertIn("skipping: [localhost]", result.stdout)

        (output / "cp.current.yaml").write_text(self.baseline.read_text())
        inputs["control_applications_sso_require_installed"] = True
        result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(play), "-e", json.dumps(inputs)],
                                capture_output=True, text=True, timeout=120)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Require an already-installed configuration", result.stdout)


@unittest.skipUnless(
    os.name != "nt" and shutil.which("ansible-playbook") and shutil.which("helm")
    and os.environ.get("HOMELAB_NATIVE_CHART_TESTS") == "1",
    "Set HOMELAB_NATIVE_CHART_TESTS=1 with native Ansible/Helm and public chart access",
)
class NativeControlApplicationRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="control-apps-native-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.output = Path(cls.directory.name) / "render"
        play = Path(cls.directory.name) / "render.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": "localhost", "connection": "local", "gather_facts": False,
            "roles": [str(ROLE)],
        }]))
        inputs = fixture() | {"control_applications_output": str(cls.output)}
        environment = dict(os.environ, ANSIBLE_ROLES_PATH=str(ROOT / "shared/ansible/roles"))
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(play), "-e", json.dumps(inputs)],
            env=environment, capture_output=True, text=True, timeout=600,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.documents = {
            product: [obj for obj in yaml.safe_load_all((cls.output / f"{product}-manifests.yml").read_text()) if obj]
            for product in ("keycloak", "vault", "netbox", "headlamp")
        }

    def test_real_chart_workloads_and_tls_probes(self):
        keycloak = next(obj for obj in self.documents["keycloak"] if obj["kind"] == "StatefulSet")
        self.assertEqual(keycloak["spec"]["replicas"], 2)
        container = keycloak["spec"]["template"]["spec"]["containers"][0]
        self.assertEqual(container["args"], ["start"])
        env = {item["name"]: item for item in container["env"]}
        self.assertNotIn("KC_HTTP_ENABLED", env)
        self.assertIn("sslmode=verify-full", env["KC_DB_URL"]["value"])
        self.assertEqual(env["KC_BOOTSTRAP_ADMIN_PASSWORD"]["valueFrom"]["secretKeyRef"]["key"], "password")
        self.assertEqual(container["readinessProbe"]["httpGet"]["path"], "/health/ready")
        vault = next(obj for obj in self.documents["vault"] if obj["kind"] == "StatefulSet")
        self.assertEqual(vault["spec"]["replicas"], 3)
        self.assertEqual({claim["metadata"]["name"] for claim in vault["spec"]["volumeClaimTemplates"]},
                         {"data", "audit"})
        self.assertEqual(vault["spec"]["template"]["spec"]["containers"][0]["readinessProbe"]["httpGet"]["scheme"],
                         "HTTPS")
        self.assertNotIn("postStart", vault["spec"]["template"]["spec"]["containers"][0].get("lifecycle", {}))
        self.assertEqual(len(vault["spec"]["template"]["spec"]["containers"]), 1)

    def test_real_netbox_secret_mounts_and_headlamp_oidc_arguments(self):
        netbox = next(obj for obj in self.documents["netbox"] if obj["kind"] == "Deployment"
                      and obj["metadata"]["name"] == "netbox")
        pod = netbox["spec"]["template"]["spec"]
        env = {item["name"]: item for item in pod["containers"][0]["env"]}
        self.assertEqual(env["SUPERUSER_NAME"]["valueFrom"]["secretKeyRef"],
                         {"name": "netbox-superuser", "key": "username"})
        self.assertEqual(env["REQUESTS_CA_BUNDLE"]["value"], "/trust/services/ca.crt")
        self.assertTrue(any(volume.get("secret", {}).get("secretName") == "netbox-oidc" for volume in pod["volumes"]))
        for obj in self.documents["netbox"]:
            if obj["kind"] == "Deployment":
                pod = obj["spec"]["template"]["spec"]
            elif obj["kind"] == "CronJob":
                pod = obj["spec"]["jobTemplate"]["spec"]["template"]["spec"]
            else:
                continue
            mounts = {mount["mountPath"] for mount in pod["containers"][0]["volumeMounts"]}
            self.assertTrue({"/trust/db", "/trust/cache", "/trust/services"} <= mounts, obj["metadata"]["name"])
        media = next(obj for obj in self.documents["netbox"] if obj["kind"] == "PersistentVolumeClaim"
                     and obj["metadata"]["name"] == "netbox-media")
        self.assertEqual(media["spec"]["accessModes"], ["ReadWriteMany"])
        headlamp = next(obj for obj in self.documents["headlamp"] if obj["kind"] == "Deployment")
        container = headlamp["spec"]["template"]["spec"]["containers"][0]
        self.assertIn("-oidc-client-secret=$(OIDC_CLIENT_SECRET)", container["args"])
        self.assertIn("-oidc-use-pkce=$(OIDC_USE_PKCE)", container["args"])
        self.assertNotIn("-unsafe-use-service-account-token", container["args"])
        self.assertFalse(any(obj["kind"] == "ClusterRoleBinding" for obj in self.documents["headlamp"]))

    def test_rendered_support_and_private_output(self):
        for product, documents in self.documents.items():
            self.assertFalse(any(obj["kind"] == "Secret" for obj in documents), product)
            support = list(yaml.safe_load_all((self.output / f"{product}-after.yml").read_text()))
            ingress = next(obj for obj in support if obj["kind"] == "Ingress")
            self.assertEqual(ingress["kind"], "Ingress")
            self.assertEqual(ingress["spec"]["tls"][0]["secretName"], f"{product}-tls")
        for path in self.output.iterdir():
            self.assertEqual(path.stat().st_mode & 0o077, 0)
            self.assertNotIn("PRIVATE-RENDER-SENTINEL", path.read_text())

    def test_database_and_backup_crs_match_pinned_upstream_openapi(self):
        from jsonschema import Draft7Validator

        sources = {
            "Cluster": "cloudnative-pg/cloudnative-pg/v1.27.0/config/crd/bases/postgresql.cnpg.io_clusters.yaml",
            "Backup": "cloudnative-pg/cloudnative-pg/v1.27.0/config/crd/bases/postgresql.cnpg.io_backups.yaml",
            "ScheduledBackup": "cloudnative-pg/cloudnative-pg/v1.27.0/config/crd/bases/postgresql.cnpg.io_scheduledbackups.yaml",
            "ObjectStore": "cloudnative-pg/plugin-barman-cloud/v0.15.1/config/crd/bases/barmancloud.cnpg.io_objectstores.yaml",
        }
        schemas = {}
        for kind, source in sources.items():
            with urllib.request.urlopen(f"https://raw.githubusercontent.com/{source}", timeout=60) as response:
                crd = yaml.safe_load(response.read())
            schemas[kind] = next(version["schema"]["openAPIV3Schema"] for version in crd["spec"]["versions"]
                                 if version["name"] == "v1")
        for product in ("keycloak", "netbox"):
            for phase in ("before", "after"):
                documents = yaml.safe_load_all((self.output / f"{product}-{phase}.yml").read_text())
                for obj in documents:
                    if obj["kind"] in schemas:
                        errors = list(Draft7Validator(schemas[obj["kind"]]).iter_errors(obj))
                        self.assertFalse(errors, [f"{list(error.path)}: {error.message}" for error in errors])


if __name__ == "__main__":
    unittest.main()
