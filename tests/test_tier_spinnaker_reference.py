"""Render the native reference, admit custom overlays, and compare the pinned upstream base."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

try:
    import kubernetes_validate
except ImportError:
    kubernetes_validate = None

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / "tier-1/ansible/roles/delivery_platform"
SOFTWARE = yaml.safe_load((ROLE / "files/software.yml").read_text())
SPINNAKER_RELEASE = SOFTWARE["spinnaker_release"]
SPINNAKER_REVISION = SOFTWARE["spinnaker_revision"]
UPSTREAM_CACHE = os.environ.get("SPINNAKER_UPSTREAM_CACHE")
CRD_CACHE = os.environ.get("SPINNAKER_CRD_CACHE")
# Released cert-manager v1.21.3 and Traefik chart v42.1.3; optional, never downloaded by tests.
CRD_SHA256 = {
    "cert-manager.yaml": "29810b2a84c8ee0731a79679ee1dfd7e93cd750eb0244542eec47fa8700f2749",
    "traefik.yaml": "164d529984ce726950383a34ea38c5cfd5aedb67dc6e04dfd1ea0854f28cb954",
}
KUSTOMIZE = shutil.which("kustomize")
KUBECTL = shutil.which("kubectl")
BUILD = [KUSTOMIZE, "build"] if KUSTOMIZE else [KUBECTL, "kustomize"] if KUBECTL else None
NATIVE = os.name != "nt" and shutil.which("ansible-playbook") and shutil.which("helm") and BUILD
RESTIC = os.environ.get("RESTIC_BINARY") or shutil.which("restic")
PORTS = {"clouddriver": 7002, "deck": 9000, "echo": 8089, "fiat": 7003,
         "front50": 8080, "gate": 8084, "orca": 8083, "rosco": 8087}


class SpinnakerReference(TierRepositoryTestCase):
    def resources(self):
        # Synthetic admission resources deliberately omit application configuration and dependencies.
        resources = []
        for name, port in PORTS.items():
            resources.append({
                "apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": name},
                "spec": {"selector": {"matchLabels": {"app": name}}, "template": {
                    "metadata": {"labels": {"app": name}}, "spec": {
                        "automountServiceAccountToken": False,
                        "containers": [{"name": name, "image": f"ghcr.io/spinnaker/{name}:{SPINNAKER_RELEASE}",
                                        "ports": [{"name": "http", "containerPort": port}],
                                        "volumeMounts": [{"name": "runtime", "mountPath": "/opt/spinnaker/config/",
                                                          "readOnly": True}],
                                        "securityContext": {"allowPrivilegeEscalation": False}}],
                        "volumes": [{"name": "runtime", "secret": {"secretName": "spinnaker-runtime"}}],
                    }}},
            })
            resources.append({
                "apiVersion": "v1", "kind": "Service", "metadata": {"name": name},
                "spec": {"selector": {"app": name}, "ports": [{"port": port, "targetPort": "http"}]},
            })
        resources.append({
            "apiVersion": "networking.k8s.io/v1", "kind": "Ingress", "metadata": {"name": "spinnaker"},
            "spec": {"ingressClassName": "accepted-ingress",
                     "tls": [{"secretName": "spinnaker-tls", "hosts": ["spin.lab.test"]}],
                     "rules": [{"host": "spin.lab.test", "http": {"paths": [
                         {"path": path, "pathType": "Prefix", "backend": {
                             "service": {"name": name, "port": {"number": port}}}}
                         for path, name, port in (("/", "deck", 9000), ("/api/v1", "gate", 8084))
                     ]}}]},
        })
        return resources

    def write_overlay(self, resources):
        overlay = Path(self.temp.name) / "project/overlay"
        overlay.mkdir(parents=True, exist_ok=True)
        (overlay / "resources.yml").write_text(yaml.safe_dump_all(resources))
        (overlay / "kustomization.yaml").write_text(yaml.safe_dump({
            "apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
            "namespace": "spinnaker", "resources": ["resources.yml"],
        }))
        return overlay

    def run_role(self, overlay, repo=None, **overrides):
        repo = repo or UPSTREAM / "tier-1"
        inputs = dict({
            "delivery_platform_controller": "spinnaker",
            "delivery_platform_install_harbor": False,
            "delivery_platform_ingress_class": "accepted-ingress",
            "delivery_platform_oidc_issuer": "https://sso.lab.test/realms/platform",
            "delivery_platform_oidc_ca_pem": "-----BEGIN CERTIFICATE-----\nOFFLINE-FIXTURE\n",
            "delivery_platform_spinnaker_host": "spin.lab.test",
            "delivery_platform_spinnaker_overlay": str(overlay),
            "delivery_platform_spinnaker_mode": "overlay",
            "delivery_platform_repository_root": str(overlay.parent),
            "delivery_platform_output": str(Path(self.temp.name) / "render"),
        }, **overrides)
        fixture = Path(self.temp.name) / "inputs.yml"
        fixture.write_text(yaml.safe_dump(inputs))
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", "ansible/playbooks/deployment/delivery-platform.yml",
             "-e", f"@{fixture}"], cwd=repo,
            env=dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg")),
            capture_output=True, text=True, timeout=300,
        )

    def assert_rejected(self, resources, task):
        result = self.run_role(self.write_overlay(resources))
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(task, result.stdout)
        self.assertNotIn("TASK [delivery_platform : Apply the complete reviewed", result.stdout)
        self.assertFalse((Path(self.temp.name) / "render/spinnaker-manifests.yml").exists())

    def native_inputs(self):
        return {
            "delivery_platform_spinnaker_mode": "native",
            "delivery_platform_spinnaker_overlay": "",
            "delivery_platform_spinnaker_storage_class": "persistent",
            "delivery_platform_spinnaker_ca_pem": "-----BEGIN CERTIFICATE-----\nFIXTURE\n-----END CERTIFICATE-----",
            "delivery_platform_spinnaker_destinations": ["team-delivery"],
            "delivery_platform_spinnaker_egress": [{"cidr": "192.0.2.1/32", "ports": [443, 6443]}],
            "delivery_platform_spinnaker_backup_s3_endpoint": "https://backups.lab.test",
            "delivery_platform_spinnaker_backup_s3_bucket": "platform-backups",
            "delivery_platform_spinnaker_backup_s3_prefix": "spinnaker",
            "delivery_platform_spinnaker_backup_ca_pem": "-----BEGIN CERTIFICATE-----\nFIXTURE\n-----END CERTIFICATE-----",
            "delivery_platform_spinnaker_backup_egress": [{"cidr": "198.51.100.10/32", "ports": [443]}],
        }

    def filesystem_inputs(self):
        return dict(self.native_inputs(), delivery_platform_spinnaker_backup_backend="filesystem",
                    delivery_platform_spinnaker_backup_filesystem_claim="spinnaker-nas-repository",
                    delivery_platform_spinnaker_backup_filesystem_repository="spinnaker",
                    delivery_platform_spinnaker_backup_filesystem_marker="offline-nas-custody-identity-000001",
                    delivery_platform_spinnaker_backup_s3_endpoint="",
                    delivery_platform_spinnaker_backup_ca_pem="", delivery_platform_spinnaker_backup_egress=[])

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize")
    def test_filesystem_backend_renders_existing_claim_without_s3_credentials_or_owned_storage(self):
        self.generate()
        previous = None
        for repo in (UPSTREAM / "tier-1", self.root / "verify-tier-1"):
            result = self.run_role(Path(self.temp.name) / "project/unused", repo=repo, **self.filesystem_inputs())
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            output = Path(self.temp.name) / "render"
            render = (output / "spinnaker-manifests.yml").read_bytes()
            if previous:
                self.assertEqual(previous, render)
            previous = render
            documents = list(yaml.safe_load_all(render))
            claims = [d["metadata"]["name"] for d in documents if d["kind"] == "PersistentVolumeClaim"]
            self.assertEqual(claims, ["spinnaker-backup"], "Only staging is created; NAS storage is preprovisioned")
            self.assertFalse((output / "spinnaker-backup-iam.json").exists())
            self.assertEqual((output / "spinnaker.sha256").read_text().strip(), hashlib.sha256(render).hexdigest())
            for doc in documents:
                if kubernetes_validate and doc["apiVersion"] not in ("cert-manager.io/v1", "traefik.io/v1alpha1"):
                    kubernetes_validate.validate(doc, "1.33.0", strict=True)
                if doc["kind"] not in ("Job", "CronJob") or not doc["metadata"]["name"].startswith("spinnaker-backup"):
                    continue
                spec = doc["spec"]["jobTemplate"]["spec"] if doc["kind"] == "CronJob" else doc["spec"]
                pod = spec["template"]["spec"]
                copy = pod["containers"][0]
                env = {v["name"]: v for v in copy["env"]}
                self.assertEqual(env["BACKUP_BACKEND"]["value"], "filesystem")
                self.assertEqual(env["RESTIC_REPOSITORY"]["value"], "/repository/spinnaker")
                self.assertNotIn("RESTIC_CACERT", env)
                self.assertFalse(any(k.startswith("AWS_") for k in env))
                volume = next(v for v in pod["volumes"] if v["name"] == "repository")
                self.assertEqual(volume, {"name": "repository", "persistentVolumeClaim": {
                    "claimName": "spinnaker-nas-repository"}})
                self.assertIn({"name": "repository", "mountPath": "/repository"}, copy["volumeMounts"])
                self.assertFalse(any(m["name"] == "repository" for c in pod["initContainers"]
                                     for m in c.get("volumeMounts", [])))
            policy = next(d for d in documents if d["metadata"]["name"] == "spinnaker-offcluster-backup")
            self.assertEqual(policy["spec"]["egress"], [])

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize")
    def test_filesystem_bootstrap_requires_retained_password_without_aws_keys_and_removes_stale_iam(self):
        output = Path(self.temp.name) / "render"
        output.mkdir()
        (output / "spinnaker-backup-iam.json").write_text("obsolete S3 render")
        inputs = dict(self.filesystem_inputs(), delivery_platform_manage_secrets=True, delivery_platform_secrets={
            "spinnaker/spinnaker-oidc": {"clientSecret": "private-oidc-fixture"},
            "spinnaker/spinnaker-keystore": {"password": "offlinePkcs12PasswordFixture00000001"},
            "spinnaker/spinnaker-backup": {"RESTIC_PASSWORD": "offline-retained-password-fixture-32"}})
        result = self.run_role(Path(self.temp.name) / "project/unused", **inputs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((output / "spinnaker-backup-iam.json").exists())
        self.assertFalse(any("backup" in p.name for p in (output / "credentials").iterdir()))
        for password in (None, "short"):
            inputs["delivery_platform_secrets"]["spinnaker/spinnaker-backup"] = (
                {} if password is None else {"RESTIC_PASSWORD": password})
            result = self.run_role(Path(self.temp.name) / "project/unused", **inputs)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("TASK [delivery_platform : Create only the selected", result.stdout)

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize")
    def test_filesystem_rejects_missing_shared_or_escaping_repository_inputs(self):
        for denied in (
            {"delivery_platform_spinnaker_backup_backend": "local"},
            {"delivery_platform_spinnaker_backup_filesystem_claim": ""},
            {"delivery_platform_spinnaker_backup_filesystem_claim": "spinnaker-backup"},
            {"delivery_platform_spinnaker_backup_filesystem_claim": "data-spinnaker-mysql-0"},
            {"delivery_platform_spinnaker_backup_filesystem_repository": "../backup"},
            {"delivery_platform_spinnaker_backup_filesystem_repository": "/backup"},
            {"delivery_platform_spinnaker_backup_filesystem_marker": ""},
        ):
            with self.subTest(denied=denied):
                result = self.run_role(Path(self.temp.name) / "project/unused", **dict(self.filesystem_inputs(), **denied))
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn("TASK [delivery_platform : Create only the selected", result.stdout)

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize")
    def test_complete_native_reference_renders_without_external_base(self):
        self.generate()
        previous = None
        for repo in (UPSTREAM / "tier-1", self.root / "verify-tier-1"):
            with self.subTest(repo=repo):
                result = self.run_role(Path(self.temp.name) / "project/unused", repo=repo, **self.native_inputs())
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                output = Path(self.temp.name) / "render"
                render = (output / "spinnaker-manifests.yml").read_bytes()
                documents = list(yaml.safe_load_all(render))
                self.assertEqual((output / "spinnaker.sha256").read_text().strip(), hashlib.sha256(render).hexdigest())
                if previous:
                    self.assertEqual(previous, render, "Source/generated native installations must be identical")
                previous = render
                self.check_native_contract(documents, render.decode())
                policy = json.loads((output / "spinnaker-backup-iam.json").read_text())
                deletes = [s for s in policy["Statement"] if "s3:DeleteObject" in s["Action"]]
                self.assertEqual([s["Resource"] for s in deletes],
                                 ["arn:aws:s3:::platform-backups/spinnaker/locks/*"])

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize")
    def test_commissioned_issuer_is_an_explicit_alternative_not_a_created_authority(self):
        inputs = dict(self.native_inputs(), delivery_platform_spinnaker_certificate_mode="issuer")
        result = self.run_role(Path(self.temp.name) / "project/unused", **inputs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        docs = list(yaml.safe_load_all((Path(self.temp.name) / "render/spinnaker-manifests.yml").read_text()))
        certificates = [d for d in docs if d["kind"] == "Certificate"]
        self.assertEqual(len(certificates), 10)
        self.assertFalse(any(d["kind"] in ("Issuer", "ClusterIssuer") for d in docs))
        self.assertTrue(all(not d["spec"].get("isCA", False) for d in certificates))

    def check_native_contract(self, documents, render):
        deployments = {d["metadata"]["name"]: d for d in documents if d["kind"] == "Deployment"}
        self.assertEqual(set(deployments), set(PORTS))
        self.assertNotIn("main-latest", render)
        self.assertNotIn("cluster-admin", render)
        self.assertNotIn("example.com", render)
        self.assertEqual(sum(d["kind"] == "Certificate" for d in documents), 0)
        self.assertEqual({d["metadata"]["name"] for d in documents if d["kind"] == "StatefulSet"},
                         {"spinnaker-mysql", "spinnaker-redis"})
        config = {}
        for doc in documents:
            if doc["kind"] == "ConfigMap":
                config.update(doc.get("data", {}))
        common = yaml.safe_load(config["spinnaker.yml"])
        self.assertTrue(common["services"]["fiat"]["enabled"])
        self.assertTrue(common["server"]["ssl"]["enabled"])
        self.assertEqual(common["server"]["ssl"]["key-store-password"], "${KEYSTORE_PASSWORD}")
        gate = yaml.safe_load(config["gate-local.yml"])
        registration = gate["spring"]["security"]["oauth2"]["client"]["registration"]
        self.assertEqual(registration["platform"]["client-secret"], "${OIDC_CLIENT_SECRET}")
        self.assertIn("groups", registration["user-info-requirements"])
        self.assertFalse(gate["security"]["basicform"]["enabled"])
        for name, deployment in deployments.items():
            pod = deployment["spec"]["template"]["spec"]
            self.assertFalse(pod["automountServiceAccountToken"])
            container = next(c for c in pod["containers"] if c["name"] == name)
            self.assertEqual(container["image"], f"ghcr.io/spinnaker/{name}:{SPINNAKER_RELEASE}")
            if name != "deck":
                self.assertEqual(container["readinessProbe"]["httpGet"]["scheme"], "HTTPS")
                sidecar = next(c for c in pod["initContainers"] if c["name"] == "redis-tls")
                self.assertEqual(sidecar["restartPolicy"], "Always")
            if name in ("clouddriver", "echo", "fiat", "front50", "orca"):
                sql = yaml.safe_load(config[f"{name}-local.yml"])["sql"]
                self.assertIn(f"/{name}?sslMode=VERIFY_IDENTITY", sql["connectionPools"]["default"]["jdbcUrl"])
                self.assertEqual(sql["connectionPools"]["default"]["user"], f"{name}_service")
                self.assertEqual(sql["migration"]["user"], f"{name}_migrate")
                refs = {v["valueFrom"]["secretKeyRef"]["name"] for v in container["env"] if "valueFrom" in v}
                self.assertIn(f"spinnaker-{name}-db", refs)
                self.assertNotIn("spinnaker-mysql-root", refs)
        envoy = yaml.safe_load(config["redis.yml"])
        context = envoy["static_resources"]["clusters"][0]["transport_socket"]["typed_config"]
        validation = context["common_tls_context"]["validation_context"]
        self.assertIn("trusted_ca", validation)
        self.assertIn("match_typed_subject_alt_names", validation)
        self.assertIn("appendonly yes", config["redis.conf"])
        self.assertIn("noeviction", config["redis.conf"])
        roles = [d for d in documents if d["kind"] == "Role"]
        self.assertEqual([d["metadata"]["namespace"] for d in roles], ["team-delivery"])
        for rule in roles[0]["rules"]:
            self.assertFalse(set(rule["resources"]) & {"secrets", "roles", "rolebindings", "serviceaccounts", "*"})
        targets = [d for d in documents if d["kind"] == "Namespace" and d["metadata"]["name"] == "team-delivery"]
        self.assertEqual(targets[0]["metadata"]["labels"]["pod-security.kubernetes.io/enforce"], "restricted")
        self.assertTrue(all(d["type"] == "kubernetes.io/service-account-token"
                            and not d.get("data") for d in documents if d["kind"] == "Secret"))
        backup = next(d for d in documents if d["kind"] == "CronJob")["spec"]["jobTemplate"]["spec"]
        pod = backup["template"]["spec"]
        self.assertEqual([c["name"] for c in pod["initContainers"]], ["redis-tls", "mysql", "redis"])
        self.assertEqual([c["name"] for c in pod["containers"]], ["independent-copy"])
        uploader = pod["containers"][0]
        self.assertEqual(uploader["image"], SOFTWARE["restic_image"])
        env = {v["name"]: v for v in uploader["env"]}
        self.assertEqual(env["RESTIC_REPOSITORY"]["value"], "s3:https://backups.lab.test/platform-backups/spinnaker")
        self.assertEqual(env["RESTIC_CACERT"]["value"], "/roots/backup.crt")
        self.assertTrue(all(env[k]["valueFrom"]["secretKeyRef"]["name"] == "spinnaker-backup"
                            for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "RESTIC_PASSWORD")))
        self.assertIn("test -s", config["backup-restic.sh"])
        self.assertIn('restic "$@" check --read-data', config["backup-restic.sh"])
        self.assertNotIn("insecure", config["backup-restic.sh"])
        self.assertNotIn("prune", config["backup-restic.sh"])

    @unittest.skipUnless(NATIVE and kubernetes_validate, "Requires native tools and kubernetes-validate")
    def test_native_resources_match_strict_kubernetes_schemas(self):
        result = self.run_role(Path(self.temp.name) / "project/unused", **self.native_inputs())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        schemas = {}
        if CRD_CACHE:
            for filename, checksum in CRD_SHA256.items():
                data = (Path(CRD_CACHE) / filename).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), checksum, filename)
                for crd in yaml.safe_load_all(data):
                    for version in crd["spec"]["versions"]:
                        schemas[(crd["spec"]["group"] + "/" + version["name"], crd["spec"]["names"]["kind"])] = (
                            version["schema"]["openAPIV3Schema"])
        for doc in yaml.safe_load_all((Path(self.temp.name) / "render/spinnaker-manifests.yml").read_text()):
            if doc["apiVersion"] in ("cert-manager.io/v1", "traefik.io/v1alpha1"):
                if schemas:
                    from jsonschema import Draft7Validator
                    schema = schemas[(doc["apiVersion"], doc["kind"])]
                    Draft7Validator(schema).validate(doc)
                continue
            with self.subTest(kind=doc["kind"], name=doc["metadata"]["name"]):
                kubernetes_validate.validate(doc, "1.33.0", strict=True)

    def test_generated_native_payload_preserves_license_and_all_runtime_sources(self):
        self.generate()
        source = ROLE / "files/spinnaker"
        generated = self.root / "verify-tier-1/ansible/roles/delivery_platform/files/spinnaker"
        for path in source.rglob("*"):
            if path.is_file():
                with self.subTest(path=path.relative_to(source)):
                    self.assertEqual(path.read_bytes(), (generated / path.relative_to(source)).read_bytes())
        manifest = yaml.safe_load((source / "upstream.yml").read_text())
        for name, record in manifest["files"].items():
            data = ((source / name).read_text().rstrip() + "\n").encode()
            self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"], name)

    @unittest.skipUnless(UPSTREAM_CACHE, "Requires a pinned offline upstream checkout")
    def test_vendored_files_correspond_to_the_official_pinned_release(self):
        upstream = self.pinned_upstream().parent
        source = ROLE / "files/spinnaker"
        for name, record in yaml.safe_load((source / "upstream.yml").read_text())["files"].items():
            actual = (upstream / record["source"]).read_text().rstrip() + "\n"
            self.assertEqual(hashlib.sha256(actual.encode()).hexdigest(), record["sha256"], name)

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize")
    def test_native_rejects_system_targets_open_egress_and_unreviewed_apply(self):
        for denied in (
            {"delivery_platform_spinnaker_destinations": ["kube-system"]},
            {"delivery_platform_spinnaker_destinations": ["spinnaker"]},
            {"delivery_platform_spinnaker_destinations": []},
            {"delivery_platform_spinnaker_egress": [{"cidr": "0.0.0.0/0", "ports": [443]}]},
            {"delivery_platform_spinnaker_storage_class": ""},
            {"delivery_platform_spinnaker_egress": [{"cidr": "::/000", "ports": [443]}]},
            {"delivery_platform_spinnaker_egress": [{"cidr": "999.999.999.999/32", "ports": [443]}]},
            {"delivery_platform_spinnaker_backup_s3_endpoint": ""},
            {"delivery_platform_spinnaker_backup_s3_endpoint": "http://backups.lab.test"},
            {"delivery_platform_spinnaker_backup_s3_endpoint": "https://store.backups.svc.cluster.local"},
            {"delivery_platform_spinnaker_backup_egress": []},
            {"delivery_platform_action": "apply", "delivery_platform_kubeconfig": "/absent/offline",
             "delivery_platform_context": "tier1-test", "delivery_platform_ca_path": "/absent/ca",
             "delivery_platform_spinnaker_review_sha256": "0" * 64},
        ):
            with self.subTest(denied=denied):
                result = self.run_role(Path(self.temp.name) / "project/unused", **dict(self.native_inputs(), **denied))
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn("TASK [delivery_platform : Check every existing credential", result.stdout)
                self.assertNotIn("TASK [delivery_platform : Create only the selected", result.stdout)

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize")
    def test_native_bootstrap_credentials_are_stable_private_and_absent_from_manifests(self):
        inputs = dict(self.native_inputs(), delivery_platform_manage_secrets=True,
                      delivery_platform_secrets={
                          "spinnaker/spinnaker-oidc": {"clientSecret": "private-oidc-fixture"},
                          "spinnaker/spinnaker-keystore": {"password": "offlinePkcs12PasswordFixture00000001"},
                          "spinnaker/spinnaker-backup": {"AWS_ACCESS_KEY_ID": "offline-access-key",
                                                         "AWS_SECRET_ACCESS_KEY": "offline-s3-secret-fixture",
                                                         "RESTIC_PASSWORD": "offline-restic-password-fixture-32"}})
        previous = None
        for _ in range(2):
            result = self.run_role(Path(self.temp.name) / "project/unused", **inputs)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            output = Path(self.temp.name) / "render"
            secrets = {p.name: p.read_bytes() for p in (output / "credentials").iterdir()}
            self.assertEqual(len(secrets), 12)
            self.assertEqual(len(set(secrets.values())), 12)
            if previous:
                self.assertEqual(previous, secrets)
            previous = secrets
            manifest = (output / "spinnaker-manifests.yml").read_bytes()
            self.assertNotIn(b"private-oidc-fixture", manifest)
            for secret in secrets.values():
                self.assertNotIn(secret.strip(), manifest)
            for path in output.rglob("*"):
                self.assertEqual(path.stat().st_mode & 0o077, 0, path)

    @unittest.skipUnless(os.name != "nt" and RESTIC, "Requires the pinned native restic binary")
    def test_native_backup_script_roundtrips_with_real_restic_and_fails_closed(self):
        version = subprocess.run([RESTIC, "version"], capture_output=True, text=True, check=True)
        self.assertIn(SOFTWARE["restic_image"].rsplit(":", 1)[1], version.stdout)
        root = Path(self.temp.name)
        staged = root / "staging/run-1"
        staged.mkdir(parents=True)
        (staged / "mysql.sql.gz").write_bytes(b"offline-dump-content")
        (staged / "redis.rdb").write_bytes(b"offline-rdb-content")
        script = ROLE / "files/spinnaker/backup-restic.sh"
        tools = root / "native-tools"
        tools.mkdir()
        (tools / "restic").symlink_to(Path(RESTIC).resolve())
        env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"],
                   BACKUP_DIRECTORY=str(staged.parent), BACKUP_RUN="run-1", RESTIC_HOST="spinnaker",
                   RESTIC_REPOSITORY=str(root / "independent-repository"), RESTIC_PASSWORD="offline-recovery-password",
                   RESTIC_CACHE_DIR=str(root / "cache"), RESTIC_CACERT="/etc/ssl/certs/ca-certificates.crt")
        run = subprocess.run(["sh", str(script)], env=env, text=True, capture_output=True, timeout=120)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        restore = root / "restored"
        result = subprocess.run([RESTIC, "restore", "latest", "--target", str(restore)], env=env,
                                text=True, capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(next(restore.rglob("mysql.sql.gz")).read_bytes(), b"offline-dump-content")
        self.assertEqual(next(restore.rglob("redis.rdb")).read_bytes(), b"offline-rdb-content")
        self.assertFalse(staged.exists(), "Successful independent copy must release local staging")
        staged.mkdir()
        (staged / "mysql.sql.gz").write_bytes(b"offline-dump-content")
        (staged / "redis.rdb").write_bytes(b"offline-rdb-content")
        denied = subprocess.run(["sh", str(script)], env=dict(env, RESTIC_PASSWORD="wrong-password"),
                                text=True, capture_output=True, timeout=120)
        self.assertEqual(denied.returncode, 12, denied.stdout + denied.stderr)
        self.assertNotIn("created restic repository", denied.stdout)
        (staged / "redis.rdb").unlink()
        incomplete = subprocess.run(["sh", str(script)], env=env, text=True, capture_output=True, timeout=30)
        self.assertNotEqual(incomplete.returncode, 0)

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize or kubectl")
    def test_scoped_admission_fixture_renders_source_and_generated_with_exact_hash(self):
        self.generate()
        overlay = self.write_overlay(self.resources())
        for repo in (UPSTREAM / "tier-1", self.root / "verify-tier-1"):
            with self.subTest(repo=repo):
                result = self.run_role(overlay, repo=repo)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                output = Path(self.temp.name) / "render"
                render = (output / "spinnaker-manifests.yml").read_bytes()
                self.assertEqual((output / "spinnaker.sha256").read_text().strip(), hashlib.sha256(render).hexdigest())
                documents = list(yaml.safe_load_all(render))
                self.assertEqual(sum(doc["kind"] == "Deployment" for doc in documents), 8)
                self.assertEqual(sum(doc["kind"] == "Service" for doc in documents), 8)

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize or kubectl")
    def test_missing_product_overlay_fails_before_render(self):
        result = self.run_role(Path(self.temp.name) / "project/absent")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((Path(self.temp.name) / "render").exists())

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize or kubectl")
    def test_eight_deployments_without_native_services_are_rejected(self):
        resources = [doc for doc in self.resources() if doc["kind"] != "Service"]
        self.assert_rejected(resources, "Require one Deployment and internal Service")

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize or kubectl")
    def test_wrong_service_selector_and_port_are_rejected(self):
        for field, value in (("selector", {"app": "another-service"}),
                             ("ports", [{"port": 8084, "targetPort": 1234}])):
            with self.subTest(field=field):
                resources = self.resources()
                service = next(doc for doc in resources if doc["kind"] == "Service"
                               and doc["metadata"]["name"] == "gate")
                service["spec"][field] = value
                self.assert_rejected(resources, "Require the Service to select its workload")

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize or kubectl")
    def test_empty_wrong_and_unbound_tls_ingress_are_rejected(self):
        for changed in ("empty-paths", "wrong-backend", "wrong-class", "wrong-tls-host"):
            with self.subTest(changed=changed):
                resources = self.resources()
                ingress = resources[-1]["spec"]
                if changed == "empty-paths":
                    ingress["rules"][0]["http"]["paths"] = []
                elif changed == "wrong-backend":
                    ingress["rules"][0]["http"]["paths"][1]["backend"]["service"]["name"] = "deck"
                elif changed == "wrong-class":
                    ingress["ingressClassName"] = "another-ingress"
                else:
                    ingress["tls"][0]["hosts"] = ["another.lab.test"]
                task = ("Require one ingress" if changed in ("wrong-class", "wrong-tls-host")
                        else "Require native Deck and Gate service routes")
                self.assert_rejected(resources, task)

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize or kubectl")
    def test_runtime_secret_name_in_unrelated_configmap_does_not_count_as_a_secret_mount(self):
        resources = self.resources()
        pod = resources[0]["spec"]["template"]["spec"]
        pod["volumes"] = [{"name": "runtime", "configMap": {"name": "spinnaker-runtime"}}]
        self.assert_rejected(resources, "Require a read-only native configuration mount")

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize or kubectl")
    def test_projected_runtime_secret_is_accepted(self):
        resources = self.resources()
        resources[0]["spec"]["template"]["spec"]["volumes"] = [{
            "name": "runtime", "projected": {"sources": [{"secret": {"name": "spinnaker-runtime"}}]},
        }]
        result = self.run_role(self.write_overlay(resources))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(NATIVE, "Requires native Ansible, Helm and Kustomize or kubectl")
    def test_unpinned_images_authority_and_changed_review_fail_before_cluster_access(self):
        resources = self.resources()
        resources[0]["spec"]["template"]["spec"]["containers"][0]["image"] = "ghcr.io/spinnaker/clouddriver:main-latest"
        self.assert_rejected(resources, "Validate every native container contract")
        resources = self.resources()
        resources.append({"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRoleBinding",
                          "metadata": {"name": "demo-admin"}})
        self.assert_rejected(resources, "Reject cluster authority")
        overlay = self.write_overlay(self.resources())
        result = self.run_role(overlay, delivery_platform_action="apply",
                               delivery_platform_kubeconfig="/nonexistent/offline-test",
                               delivery_platform_context="offline-test", delivery_platform_ca_path="/nonexistent/ca",
                               delivery_platform_spinnaker_review_sha256="0" * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Reject missing services or an unreviewed apply", result.stdout)
        self.assertNotIn("TASK [delivery_platform : Check every existing credential", result.stdout)

    def pinned_upstream(self):
        cache = Path(UPSTREAM_CACHE)
        head = subprocess.run(["git", "-C", str(cache), "rev-parse", "HEAD"], capture_output=True,
                              text=True, timeout=30, check=True)
        self.assertEqual(head.stdout.strip(), SPINNAKER_REVISION)
        status = subprocess.run(["git", "-C", str(cache), "status", "--porcelain", "--untracked-files=all",
                                 "--", "spinnaker-kustomize"], capture_output=True, text=True, timeout=30, check=True)
        self.assertEqual(status.stdout.strip(), "", "The upstream cache must contain unmodified reviewed manifests")
        return cache / "spinnaker-kustomize"

    @unittest.skipUnless(os.name != "nt" and BUILD and UPSTREAM_CACHE,
                         "Requires Linux/WSL, Kustomize and SPINNAKER_UPSTREAM_CACHE; no network fetch")
    def test_pinned_official_demo_renders_real_services_and_exposes_unresolved_defaults(self):
        native = subprocess.run([*BUILD, str(self.pinned_upstream())], capture_output=True,
                                text=True, timeout=60, check=True)
        documents = list(yaml.safe_load_all(native.stdout))
        deployments = {doc["metadata"]["name"] for doc in documents if doc["kind"] == "Deployment"}
        self.assertEqual(deployments, set(PORTS) | {"igor", "kayenta", "keel"})
        self.assertTrue(set(PORTS).issubset({doc["metadata"]["name"] for doc in documents if doc["kind"] == "Service"}))
        self.assertIn("main-latest", native.stdout)
        self.assertTrue(any(doc["kind"] == "ClusterRoleBinding" and doc["roleRef"]["name"] == "cluster-admin"
                            for doc in documents))
        configmaps = {doc["metadata"]["name"].rsplit("-", 1)[0]: doc.get("data", {})
                      for doc in documents if doc["kind"] == "ConfigMap"}
        gate = yaml.safe_load(configmaps["gate"]["gate-local.yml"])
        self.assertTrue(gate["security"]["basicform"]["enabled"])
        self.assertIn("password", gate["spring"]["security"]["user"])
        self.assertFalse(yaml.safe_load(configmaps["spinnaker"]["spinnaker.yml"])["services"]["fiat"]["enabled"])

    @unittest.skipUnless(NATIVE and UPSTREAM_CACHE,
                         "Requires native tools and SPINNAKER_UPSTREAM_CACHE; no network fetch")
    def test_pinned_official_demo_is_rejected_by_the_executor(self):
        overlay = Path(self.temp.name) / "project/upstream"
        shutil.copytree(self.pinned_upstream(), overlay)
        result = self.run_role(overlay)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Reject cluster authority", result.stdout)
        self.assertFalse((Path(self.temp.name) / "render").exists())


if __name__ == "__main__":
    unittest.main()
