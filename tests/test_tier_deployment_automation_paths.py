"""Exercise deployment handoffs and real NAS repository commissioning without live infrastructure."""

import hashlib
import base64
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml
import jinja2

import test_tier_spinnaker_reference as reference
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / "tier-1/ansible/roles/delivery_platform"
RESTIC = os.environ.get("RESTIC_BINARY") or shutil.which("restic")
HUMAN_ROLE = UPSTREAM / "tier-0/ansible/roles/control_applications"


@unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook") and reference.BUILD,
                     "Requires native Ansible and Kustomize")
class RepositoryJobRendering(TierRepositoryTestCase):
    def render(self, helper, repo, **overrides):
        # Full product composition belongs to test_tier_spinnaker_reference.py.
        inputs = dict(helper.filesystem_inputs(), **overrides)
        role = repo / "ansible/roles/delivery_platform"
        output = Path(self.temp.name) / "render"
        native = output / "repository-native"
        fixture = Path(self.temp.name) / "inputs.yml"
        fixture.write_text(yaml.safe_dump(inputs))
        play = Path(self.temp.name) / "render.yml"
        kustomization = dict(apiVersion="kustomize.config.k8s.io/v1beta1", kind="Kustomization",
            namespace="{{ delivery_platform_spinnaker_namespace }}", resources=["repository-job.yml"],
            configMapGenerator=[dict(name="spinnaker-scripts", files=["filesystem-repository.sh"])])
        play.write_text(yaml.safe_dump([dict(
            hosts="localhost", connection="local", gather_facts=False,
            vars=dict(role_path=str(role), repository_job_directory=str(native),
                      ansible_python_interpreter="{{ ansible_playbook_python }}"),
            vars_files=[str(role / "defaults/main.yml"), str(fixture)],
            tasks=[
                {"name": "Prepare the commissioning component output", "ansible.builtin.file": {
                    "path": str(native), "state": "directory", "mode": "0700"}},
                {"name": "Render the production commissioning Job", "ansible.builtin.template": {
                    "src": str(role / "templates/spinnaker/repository-job.yml.j2"),
                    "dest": str(native / "repository-job.yml"), "mode": "0600"}},
                {"name": "Materialize the production commissioning script", "ansible.builtin.copy": {
                    "content": "{{ lookup('ansible.builtin.file', role_path ~ '/files/spinnaker/filesystem-repository.sh') }}\n",
                    "dest": str(native / "filesystem-repository.sh"), "mode": "0600"}},
                {"name": "Select only the commissioning Job and its script ConfigMap", "ansible.builtin.copy": {
                    "content": yaml.safe_dump(kustomization),
                    "dest": str(native / "kustomization.yaml"), "mode": "0600"}},
                {"name": "Resolve native namespace and script ConfigMap references", "ansible.builtin.set_fact": {
                    "repository_job_render": "{{ lookup('kubernetes.core.kustomize', dir=repository_job_directory) }}"}},
                {"name": "Store the component manifest and its review checksum", "ansible.builtin.copy": {
                    "content": "{{ item.content }}", "dest": str(output) + "/{{ item.name }}", "mode": "0600"},
                 "loop": [dict(name="repository-manifests.yml", content="{{ repository_job_render }}"),
                          dict(name="repository.sha256", content="{{ repository_job_render | hash('sha256') }}\n")]},
            ])], sort_keys=False))
        render_timeout = 60
        try:
            return subprocess.run(["ansible-playbook", "-i", "localhost,", str(play)],
                                  cwd=repo, env=dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg")),
                                  capture_output=True, text=True, timeout=render_timeout)
        except subprocess.TimeoutExpired as error:
            output = error.stdout or b""
            stderr = error.stderr or b""
            if isinstance(output, bytes):
                output = output.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            self.fail(f"Native repository Job render exceeded {render_timeout}s in {repo}.\n"
                      f"{output[-4000:]}\n{stderr[-2000:]}")

    def test_source_and_generated_job_bind_reviewed_storage_script_and_retained_secret(self):
        self.generate()
        helper = reference.SpinnakerReference()
        helper.temp = self.temp
        previous = None
        for repo in (UPSTREAM / "tier-1", self.root / "verify-tier-1"):
            result = self.render(helper, repo)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            output = Path(self.temp.name) / "render"
            rendered = (output / "repository-manifests.yml").read_bytes()
            if previous:
                self.assertEqual(previous, rendered)
            previous = rendered
            self.assertEqual((output / "repository.sha256").read_text().strip(),
                             hashlib.sha256(rendered).hexdigest())
            documents = list(yaml.safe_load_all(rendered))
            self.assertCountEqual([doc["kind"] for doc in documents], ["Job", "ConfigMap"])
            job = next(doc for doc in documents if doc["metadata"]["name"] == "spinnaker-repository-commission")
            if reference.kubernetes_validate:
                reference.kubernetes_validate.validate(job, "1.33.0", strict=True)
            self.assertEqual(job["spec"]["backoffLimit"], 0)
            pod = job["spec"]["template"]["spec"]
            self.assertFalse(pod["automountServiceAccountToken"])
            self.assertEqual(pod["securityContext"]["runAsUser"], 999)
            container = pod["containers"][0]
            self.assertEqual(container["image"], reference.SOFTWARE["restic_image"])
            self.assertEqual(container["command"], ["sh", "/bootstrap/filesystem-repository.sh", "commission"])
            env = {item["name"]: item for item in container["env"]}
            self.assertEqual(env["BACKUP_FILESYSTEM_INITIALIZE"]["value"], "false")
            self.assertEqual(env["RESTIC_REPOSITORY"]["value"], "/repository/spinnaker")
            self.assertEqual(env["RESTIC_PASSWORD"]["valueFrom"]["secretKeyRef"],
                             {"name": "spinnaker-backup", "key": "RESTIC_PASSWORD"})
            volumes = {item["name"]: item for item in pod["volumes"]}
            self.assertEqual(volumes["repository"]["persistentVolumeClaim"]["claimName"],
                             "spinnaker-nas-repository")
            scripts = next(doc for doc in documents if doc["kind"] == "ConfigMap" and
                           doc["metadata"]["name"] == volumes["scripts"]["configMap"]["name"])
            self.assertEqual(scripts["data"]["filesystem-repository.sh"].rstrip(),
                             (ROLE / "files/spinnaker/filesystem-repository.sh").read_text().rstrip())
        initialized = self.render(helper, UPSTREAM / "tier-1",
                                  delivery_platform_spinnaker_backup_filesystem_initialize=True)
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        rendered = (Path(self.temp.name) / "render/repository-manifests.yml").read_bytes()
        self.assertEqual((Path(self.temp.name) / "render/repository.sha256").read_text().strip(),
                         hashlib.sha256(rendered).hexdigest())
        self.assertNotEqual(previous, rendered, "Initialization must be bound into the reviewed render")
        job = next(doc for doc in yaml.safe_load_all(rendered)
                   if doc["metadata"]["name"] == "spinnaker-repository-commission")
        env = {item["name"]: item for item in job["spec"]["template"]["spec"]["containers"][0]["env"]}
        self.assertEqual(env["BACKUP_FILESYSTEM_INITIALIZE"]["value"], "true")


@unittest.skipUnless(os.name != "nt" and RESTIC and os.path.ismount("/dev/shm"),
                     "Requires native restic and an existing writable tmpfs mount")
class RepositoryCommissioning(unittest.TestCase):
    def setUp(self):
        destination = tempfile.TemporaryDirectory(prefix="commission-spinnaker-", dir="/dev/shm")
        self.addCleanup(destination.cleanup)
        self.repository = Path(destination.name)
        self.repository.rmdir()
        work = tempfile.TemporaryDirectory(prefix="commission-spinnaker-cache-")
        self.addCleanup(work.cleanup)
        self.work = Path(work.name)
        tools = self.work / "tools"
        tools.mkdir()
        (tools / "restic").symlink_to(Path(RESTIC).resolve())
        self.env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"],
                        RESTIC_REPOSITORY=str(self.repository), RESTIC_PASSWORD="retained-recovery-password-fixture-32",
                        RESTIC_CACHE_DIR=str(self.work / "cache"), BACKUP_FILESYSTEM_MOUNT="/dev/shm",
                        BACKUP_FILESYSTEM_MARKER="retained-storage-identity-fixture-0001")

    def commission(self, action="commission", **overrides):
        return subprocess.run(["sh", str(ROLE / "files/spinnaker/filesystem-repository.sh"), action],
                              env=dict(self.env, **overrides), capture_output=True, text=True, timeout=60)

    def restic(self, *arguments):
        result = subprocess.run([RESTIC, *arguments], env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_explicit_initialization_reruns_and_backup_restore_keep_the_original_repository(self):
        self.assertNotEqual(self.commission().returncode, 0)
        self.assertFalse(self.repository.exists())
        result = self.commission(BACKUP_FILESYSTEM_INITIALIZE="true")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        config = (self.repository / "config").read_bytes()
        marker = self.repository / ".spinnaker-backup-repository"
        self.assertEqual(marker.read_text().strip(), self.env["BACKUP_FILESYSTEM_MARKER"])
        payload = self.work / "original.txt"
        payload.write_bytes(b"independent recovery fixture")
        self.restic("backup", str(payload))
        before = json.loads(self.restic("snapshots", "--json").stdout)
        for initialize in ("true", "false"):
            result = self.commission(BACKUP_FILESYSTEM_INITIALIZE=initialize)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((self.repository / "config").read_bytes(), config)
            self.assertEqual(json.loads(self.restic("snapshots", "--json").stdout), before)
        restored = self.work / "restored"
        self.restic("restore", "latest", "--target", str(restored))
        self.assertEqual(next(restored.rglob("original.txt")).read_bytes(), payload.read_bytes())
        for overrides in ({"RESTIC_PASSWORD": "wrong-password"}, {"BACKUP_FILESYSTEM_MARKER": "wrong-marker"}):
            result = self.commission(BACKUP_FILESYSTEM_INITIALIZE="true", **overrides)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((self.repository / "config").read_bytes(), config)
            self.assertEqual(marker.read_text().strip(), self.env["BACKUP_FILESYSTEM_MARKER"])

    def test_failed_mount_symlink_and_runtime_verification_cannot_initialize(self):
        mount = self.work / "unmounted"
        mount.mkdir()
        target = mount / "spinnaker"
        denied = self.commission(BACKUP_FILESYSTEM_INITIALIZE="true", BACKUP_FILESYSTEM_MOUNT=str(mount),
                                 RESTIC_REPOSITORY=str(target))
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("NAS repository mount is absent", denied.stderr)
        self.assertFalse(target.exists())
        self.assertNotEqual(self.commission(action="verify", BACKUP_FILESYSTEM_INITIALIZE="true").returncode, 0)
        self.assertFalse(self.repository.exists(), "Normal backups cannot initialize even with the flag")
        self.repository.symlink_to(mount, target_is_directory=True)
        self.addCleanup(self.repository.unlink)
        self.assertNotEqual(self.commission(BACKUP_FILESYSTEM_INITIALIZE="true").returncode, 0)
        self.assertFalse(target.exists())

    def test_empty_or_partial_destination_is_preserved_and_never_repaired(self):
        self.repository.mkdir()
        self.assertNotEqual(self.commission(BACKUP_FILESYSTEM_INITIALIZE="true").returncode, 0)
        self.assertEqual(list(self.repository.iterdir()), [])
        partial = self.repository / "config"
        partial.write_bytes(b"partial or unrelated data")
        self.assertNotEqual(self.commission(BACKUP_FILESYSTEM_INITIALIZE="true").returncode, 0)
        self.assertEqual(partial.read_bytes(), b"partial or unrelated data")
        self.assertEqual([path.name for path in self.repository.iterdir()], ["config"])


class HumanAccessContracts(unittest.TestCase):
    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"), "Requires native Ansible")
    def test_native_apply_syntax_and_recovery_target_guards(self):
        tasks = yaml.safe_load((HUMAN_ROLE / "tasks/sso-human-apply.yml").read_text())
        guard = next(task for task in tasks if task["name"].startswith("Bind the public human configuration"))
        recovery = {"users": [{"user": {"client-certificate-data": "fixture-cert", "client-key-data": "fixture-key"}}],
                    "clusters": [{"cluster": {"server": "https://api.lab.test:6443",
                                  "certificate-authority-data": base64.b64encode(b"PUBLIC_CA").decode()}}]}
        cases = [("certificate-only", recovery, True)]
        for name, update in (("exec", {"exec": {"command": "unrelated-login"}}),
                             ("token", {"token": "unrelated-token"})):
            changed = copy.deepcopy(recovery)
            changed["users"][0]["user"].update(update)
            cases.append((name, changed, False))
        for name, update in (("wrong-server", {"server": "https://other.lab.test:6443"}),
                             ("wrong-ca", {"certificate-authority-data": "b3RoZXItQ0E="}),
                             ("insecure", {"insecure-skip-tls-verify": True})):
            changed = copy.deepcopy(recovery)
            changed["clusters"][0]["cluster"].update(update)
            cases.append((name, changed, False))
        with tempfile.TemporaryDirectory(prefix="human-sso-guard-") as directory:
            play = Path(directory) / "guard.yml"
            syntax = [dict(hosts="localhost", gather_facts=False,
                           tasks=[{"ansible.builtin.import_tasks": str(HUMAN_ROLE / "tasks/sso-human-apply.yml")}])]
            play.write_text(yaml.safe_dump(syntax))
            result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(play), "--syntax-check"],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for name, config, accepted in cases:
                with self.subTest(name=name):
                    play.write_text(yaml.safe_dump([dict(hosts="localhost", gather_facts=False, tasks=[guard],
                        vars=dict(sso_human_recovery={"stdout": json.dumps(config)},
                                  sso_human_api_server="https://api.lab.test:6443", sso_human_api_ca_pem="PUBLIC_CA"))]))
                    result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(play)],
                                            capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)

    def test_public_client_and_namespace_resources_work_without_a_headlamp_client_or_admin_kubeconfig(self):
        values = yaml.safe_load((HUMAN_ROLE / "defaults/sso-human.yml").read_text()) | dict(
            sso_human_keycloak_url="https://sso.lab.test", sso_human_namespaces=["team-a", "team-b"],
            sso_human_api_server="https://api.lab.test:6443", sso_human_api_ca_pem="PUBLIC_API_CA",
            sso_human_oidc_ca_pem="PUBLIC_IDP_CA", sso_human_kubelogin="/approved/kubelogin",
            sso_human_output="/private/human-cli")
        environment = jinja2.Environment(loader=jinja2.FileSystemLoader(HUMAN_ROLE / "templates"),
                                        undefined=jinja2.StrictUndefined, trim_blocks=True, lstrip_blocks=True)
        environment.filters.update(to_json=json.dumps,
                                   b64encode=lambda value: base64.b64encode(value.encode()).decode())
        render = lambda name: environment.get_template(f"sso-human-{name}.yml.j2").render(values)
        client = yaml.safe_load(render("client"))
        self.assertTrue(client["public_client"])
        self.assertTrue(client["standard_flow_enabled"])
        for option in ("implicit_flow_enabled", "direct_access_grants_enabled", "service_accounts_enabled",
                       "full_scope_allowed"):
            self.assertFalse(client[option])
        self.assertNotIn("secret", client)
        self.assertEqual(client["redirect_uris"], ["http://localhost:8000"])
        self.assertEqual(client["attributes"]["pkce.code.challenge.method"], "S256")
        audience = next(m["config"] for m in client["protocol_mappers"]
                        if m["protocolMapper"] == "oidc-audience-mapper")
        self.assertEqual(audience["included.custom.audience"], "headlamp")
        self.assertNotIn("included.client.audience", audience, "A future Headlamp client cannot be a prerequisite")
        self.assertEqual(audience["id.token.claim"], "true")
        groups = next(m["config"] for m in client["protocol_mappers"]
                      if m["protocolMapper"] == "oidc-group-membership-mapper")
        self.assertEqual(groups["full.path"], "false")
        self.assertEqual(groups["id.token.claim"], "true")
        bindings = list(yaml.safe_load_all(render("rbac")))
        self.assertEqual([b["metadata"]["namespace"] for b in bindings], ["team-a", "team-b"])
        for binding in bindings:
            self.assertEqual(binding["kind"], "RoleBinding")
            self.assertEqual(binding["roleRef"]["name"], "view")
            self.assertEqual(binding["subjects"][0]["name"], "oidc:platform-viewers")
            if reference.kubernetes_validate:
                reference.kubernetes_validate.validate(binding, "1.33.0", strict=True)
        kubeconfig = yaml.safe_load(render("kubeconfig"))
        identity = kubeconfig["users"][0]["user"]
        self.assertEqual(set(identity), {"exec"}, "Never copy the recovery identity to human output")
        self.assertEqual(identity["exec"]["command"], "/approved/kubelogin")
        self.assertIn("--oidc-pkce-method=S256", identity["exec"]["args"])
        self.assertIn("--oidc-redirect-url=" + client["redirect_uris"][0], identity["exec"]["args"])

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook") and shutil.which("openssl"),
                         "Requires native Ansible, OpenSSL and the declared collections")
    def test_native_offline_render_is_repeatable_and_rejects_unsafe_namespace_before_output(self):
        with tempfile.TemporaryDirectory(prefix="human-sso-") as directory:
            root = Path(directory)
            ca = root / "ca.pem"
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "2",
                            "-subj", "/CN=Offline Human SSO Fixture", "-addext", "basicConstraints=critical,CA:TRUE",
                            "-keyout", str(root / "key.pem"), "-out", str(ca)],
                           capture_output=True, check=True, timeout=30)
            # Availability fixture only; a token request must never occur during offline rendering.
            login = root / "kubelogin-help-fixture"
            login.write_text('#!/bin/sh\n[ "$*" = "get-token --help" ] || exit 90\n'
                             'echo "--oidc-pkce-method --certificate-authority-data --oidc-issuer-url"\n')
            login.chmod(0o700)
            values = dict(sso_human_keycloak_url="https://sso.lab.test", sso_human_namespaces=["team-a"],
                          sso_human_api_server="https://api.lab.test:6443", sso_human_api_ca_pem=ca.read_text(),
                          sso_human_oidc_ca_pem=ca.read_text(), sso_human_kubelogin=str(login),
                          sso_human_output=str(root / "render"))
            play = root / "play.yml"
            play.write_text(yaml.safe_dump([dict(hosts="localhost", connection="local", gather_facts=False,
                tasks=[{"ansible.builtin.include_role": {"name": str(HUMAN_ROLE), "tasks_from": "sso-human",
                                                         "defaults_from": "sso-human"}}])]))
            fixture = root / "inputs.yml"
            for repeat in range(2):
                fixture.write_text(yaml.safe_dump(values))
                result = subprocess.run(["ansible-playbook", "-i", "localhost,", str(play), "-e", "@" + str(fixture)],
                                        capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(set(p.name for p in (root / "render").iterdir()),
                                 {"keycloak-client.yml", "namespace-rbac.yml", "kubeconfig.yml"})
                if repeat:
                    self.assertRegex(result.stdout, r"changed=0\b")
            for namespaces in (["*"], ["kube-system"], [], ["team-a", "team-a"]):
                fixture.write_text(yaml.safe_dump(values | dict(sso_human_namespaces=namespaces,
                                                               sso_human_output=str(root / "denied"))))
                denied = subprocess.run(["ansible-playbook", "-i", "localhost,", str(play), "-e", "@" + str(fixture)],
                                        capture_output=True, text=True, timeout=60)
                self.assertNotEqual(denied.returncode, 0)
                self.assertFalse((root / "denied").exists())


if __name__ == "__main__":
    unittest.main()
