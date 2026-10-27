"""GitLab hybrid dependency contracts and real offline native rendering."""

import configparser
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

from tier_repo_test_support import UPSTREAM


TIER = UPSTREAM / "tier-1"
ROLE = TIER / "ansible/roles/development_data"
NATIVE = os.name != "nt" and shutil.which("ansible-playbook") and shutil.which("openssl")


class DevelopmentData(unittest.TestCase):
    def test_input_editing_and_plan_review_precede_vm_apply(self):
        guide = (UPSTREAM / "docs/deployment/stage-9-development/procedures/data-services.md").read_text()
        markers = ("bash scripts/init-local-files.sh --setup development-data", "Set the full IP map",
                   "bash scripts/deploy.sh development-data --plan-only", "Review the plan's three VM identities",
                   "bash scripts/deploy.sh development-data --terraform-only")
        positions = [guide.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))

    def test_inventory_sizes_and_native_database_bootstrap(self):
        defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
        inventory = yaml.safe_load((TIER / "ansible/inventory/hosts.yml.example").read_text())
        hosts = inventory["all"]["children"]["development_data"]["hosts"]
        self.assertEqual(set(hosts), set(defaults["development_data_hosts"]))
        ips = yaml.safe_load((TIER / "ansible/group_vars/development_data.yml.example").read_text())["platform_host_ips"]
        self.assertTrue(set(hosts).issubset(ips))
        database = yaml.safe_load((ROLE / "tasks/postgresql.yml").read_text())
        self.assertEqual(database[0]["community.postgresql.postgresql_db"]["owner"], "gitlab")
        self.assertEqual(set(database[1]["loop"]), {"amcheck", "pg_trgm", "btree_gist"})
        storage = yaml.safe_load((ROLE / "tasks/object-storage.yml").read_text())
        self.assertTrue(storage[0]["amazon.aws.s3_bucket"]["ceph"])
        self.assertTrue(storage[0]["amazon.aws.s3_bucket"]["versioning"])
        self.assertFalse(storage[0]["amazon.aws.s3_bucket"]["force"])
        self.assertIn("amazon.aws.iam_policy", storage[1])
        for path in ROLE.rglob("*.yml"):
            yaml.safe_load(path.read_text())

    def test_cold_backup_shell_syntax_and_failure_recovery(self):
        environment = Environment(undefined=StrictUndefined)
        source = (ROLE / "templates/backup.sh.j2").read_text()
        for component in ("postgresql", "redis", "gitaly"):
            script = environment.from_string(source).render(
                data_component=component, development_data_backup_transport="sftp")
            self.assertIn("trap 'status=$?; start_source || status=1;", script)
            self.assertIn(f"gitlab-ctl start {component}", script)
            self.assertLess(script.index("trap 'status=$?;"), script.index(f"gitlab-ctl stop {component}"))
            self.assertLess(script.index(f"gitlab-ctl stop {component}"), script.index('backup --tag'))
            self.assertNotIn("prune", script)
            if os.name != "nt" and shutil.which("bash"):
                result = subprocess.run(["bash", "-n"], input=script, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(NATIVE, "Requires Linux Ansible collections and OpenSSL")
    def test_native_module_argument_contracts(self):
        arguments = {}
        for path in (ROLE / "tasks").glob("*.yml"):
            for task in yaml.safe_load(path.read_text()):
                for name, parameters in task.items():
                    if "." in name and name != "ansible.builtin.set_fact" and isinstance(parameters, dict):
                        arguments.setdefault(name, set()).update(parameters)
        result = subprocess.run(["ansible-doc", "--json", *arguments], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        documentation = json.loads(result.stdout)
        for name, parameters in arguments.items():
            with self.subTest(module=name):
                options = documentation[name]["doc"]["options"]
                accepted = set(options)
                for option in options.values():
                    accepted.update(option.get("aliases", []))
                self.assertFalse(parameters - accepted, f"Unsupported {name} options: {parameters - accepted}")

    @unittest.skipUnless(NATIVE, "Requires Linux Ansible collections and OpenSSL")
    def test_native_render_and_rejected_inputs(self):
        (UPSTREAM / ".tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="development-data-", dir=UPSTREAM / ".tmp") as temporary:
            work = Path(temporary)
            inventory = work / "hosts.yml"
            shutil.copyfile(TIER / "ansible/inventory/hosts.yml.example", inventory)
            certificate, key = work / "server.crt", work / "server.key"
            subprocess.run(
                ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
                 "-subj", "/CN=gitlab", "-addext", "extendedKeyUsage=serverAuth,clientAuth",
                 "-addext", "subjectAltName=DNS:postgres.lab.test,DNS:redis.lab.test,DNS:gitaly.lab.test",
                 "-keyout", str(key), "-out", str(certificate)],
                check=True, capture_output=True, text=True,
            )
            defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
            password = work / "restic.password"
            password.write_text(hashlib.sha256(b"independent offline backup password").hexdigest())
            inputs = {
                "platform_host_ips": {name: f"192.0.2.{n}" for n, name in
                                      enumerate(defaults["development_data_hosts"], 10)},
                "development_data_output": str(work / "output"),
                "development_data_gitlab_url": "https://gitlab.lab.test",
                "development_data_chart_app_version": "18.5.0",
                "development_data_package_version": "18.5.0-ce.0.el9",
                "development_data_package_url": "https://packages.lab.test/gitlab-ce.rpm",
                "development_data_package_sha256": hashlib.sha256(b"offline RPM fixture").hexdigest(),
                "development_data_package_key_fingerprint": hashlib.sha1(b"offline key fixture").hexdigest().upper(),
                "development_data_package_key_src": str(certificate),
                "development_data_client_cidrs": ["192.0.2.0/24"],
                "development_data_endpoints": {name: f"{host}.lab.test" for name, host in
                                                (("postgresql", "postgres"), ("redis", "redis"), ("gitaly", "gitaly"))},
                "development_data_tls": {name: {"cert_src": str(certificate), "key_src": str(key)}
                                         for name in ("postgresql", "redis", "gitaly")},
                "development_data_ca_src": str(certificate),
                "development_data_postgresql_client_cert_src": str(certificate),
                "development_data_postgresql_client_key_src": str(key),
                "development_data_backup_repository": {name: f"sftp:backup@recovery.lab.test:/backups/{name}"
                                                        for name in defaults["development_data_hosts"]},
                "development_data_backup_password_src": str(password),
                "development_data_backup_ssh_key_src": str(key),
                "development_data_backup_known_hosts_src": str(certificate),
                "development_data_backup_custody_accepted": True,
                "development_data_s3_endpoint": "https://s3.lab.test",
                "development_data_s3_mode": "ceph-rgw",
                "development_data_s3_iam_endpoint": "https://s3.lab.test",
                "development_data_s3_ca_src": str(certificate),
                "development_data_s3_keys": {
                    "application": {"access_key": "fixtureApplicationKey", "secret_key": "fixtureApplicationSecret"},
                    "backup": {"access_key": "fixtureBackupKey", "secret_key": "fixtureBackupSecret"}},
            }
            for name in ("postgresql_password", "redis_password", "gitaly_token", "shell_token"):
                inputs[f"development_data_{name}"] = hashlib.sha256(name.encode()).hexdigest()
            fixture = work / "inputs.yml"
            environment = dict(os.environ, ANSIBLE_CONFIG=str(TIER / "ansible/ansible.cfg"))

            def run(overrides=None, tier=TIER):
                fixture.write_text(yaml.safe_dump(inputs | (overrides or {})))
                return subprocess.run(
                    ["ansible-playbook", "-i", str(inventory),
                     "ansible/playbooks/deployment/development-data.yml", "-e", f"@{fixture}"],
                    cwd=tier, env=dict(environment, ANSIBLE_CONFIG=str(tier / "ansible/ansible.cfg")),
                    capture_output=True, text=True, timeout=180,
                )

            result = run()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            output = work / "output"
            platform = yaml.safe_load((output / "platform-inputs.yml").read_text())
            self.assertIs(platform["development_platform_gitlab_backup_enabled"], True)
            self.assertEqual(platform["development_platform_gitlab_backup_schedule"], "30 2 * * *")
            self.assertFalse((output / "backup-values.yml").exists())
            for host in defaults["development_data_hosts"]:
                native_config = (output / f"{host}.rb").read_text()
                self.assertNotIn("#{", native_config)
                ruby = os.environ.get("HOMELAB_RUBY") or shutil.which("ruby")
                if ruby:
                    checked = subprocess.run([ruby, "-c", str(output / f"{host}.rb")], capture_output=True, text=True)
                    self.assertEqual(checked.returncode, 0, checked.stderr)
            postgres = (output / "gitlab-db-1.rb").read_text()
            self.assertIn("clientcert=verify-full", postgres)
            self.assertIn("postgresql['md5_auth_cidr_addresses'] = []", postgres)
            self.assertIn("redis['port'] = 0", (output / "gitlab-redis-1.rb").read_text())
            gitaly = (output / "gitlab-gitaly-1.rb").read_text()
            self.assertIn("listen_addr: ''", gitaly)
            self.assertIn(inputs["development_data_shell_token"], gitaly)
            application = json.loads((output / "application-policy.json").read_text())
            backup = json.loads((output / "backup-policy.json").read_text())
            self.assertEqual(len(application["Statement"][0]["Resource"]), 8)
            self.assertEqual(len(backup["Statement"][0]["Resource"]), 10)
            self.assertNotIn("gitlab-backups", json.dumps(application))
            self.assertTrue(all(resource.startswith("arn:aws:s3:::gitlab-") for statement in
                                backup["Statement"] for resource in statement["Resource"]))
            secrets = yaml.safe_load((output / "dependency-secrets.yml").read_text())
            self.assertEqual(secrets["gitlab-shell-auth"]["secret"], inputs["development_data_shell_token"])
            connection = yaml.safe_load(secrets["gitlab-storage"]["connection"])
            self.assertTrue(connection["path_style"])
            self.assertEqual(connection["aws_access_key_id"], "fixtureApplicationKey")
            s3config = configparser.ConfigParser()
            s3config.read_string(secrets["gitlab-backup-storage"]["config"])
            self.assertTrue(s3config["default"].getboolean("check_ssl_hostname"))
            self.assertEqual(s3config["default"]["access_key"], "fixtureBackupKey")
            self.assertNotIn("gitlab-root", secrets)
            prepared = run({"development_data_s3_mode": "preprovisioned",
                            "development_data_s3_preprovisioned_accepted": True,
                            "development_data_s3_iam_endpoint": "",
                            "development_data_s3_denied_buckets": ["storage-private"]})
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            filesystem = {
                "development_data_backup_transport": "filesystem",
                "development_data_backup_ssh_key_src": "",
                "development_data_backup_known_hosts_src": "",
                "development_data_backup_repository": {
                    host: f"/mnt/gitlab-backup/{host}" for host in defaults["development_data_hosts"]},
                "development_data_backup_filesystem": {
                    host: {"mount": "/mnt/gitlab-backup", "source": f"nas.lab.test:/backups/{host}",
                           "fstype": "nfs4", "marker": hashlib.sha256(host.encode()).hexdigest(),
                           "uid": 65534, "gid": 65534} for host in defaults["development_data_hosts"]},
            }
            generated = subprocess.run(
                [sys.executable, str(UPSTREAM / "scripts/tier-repos/generate.py"),
                 "--root", str(work / "generated"), "--prefix", "verify"],
                capture_output=True, text=True, timeout=180)
            self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
            generated_tier = work / "generated/verify-iac/verify-tier-1"
            rendered = run(filesystem, tier=generated_tier)
            self.assertEqual(rendered.returncode, 0, rendered.stdout + rendered.stderr)
            for host in defaults["development_data_hosts"]:
                guard = (output / f"{host}-backup-filesystem.sh").read_text()
                self.assertIn(filesystem["development_data_backup_filesystem"][host]["marker"], guard)
                self.assertIn(f"RESTIC_REPOSITORY='/mnt/gitlab-backup/{host}'",
                              (output / f"{host}-backup.env").read_text())
                script = (output / f"{host}-backup.sh").read_text()
                self.assertNotIn("sftp.args", script)
                self.assertEqual(subprocess.run(["bash", "-n"], input=script + guard,
                                               text=True, capture_output=True).returncode, 0)
            for bad in (
                {"development_data_backup_transport": "local"},
                {"development_data_backup_filesystem": {}},
                {"development_data_backup_repository": {host: "/" for host in defaults["development_data_hosts"]}},
                {"development_data_backup_filesystem": {
                    host: contract | {"fstype": "ext4"} for host, contract in
                    filesystem["development_data_backup_filesystem"].items()}},
                {"development_data_backup_filesystem": {
                    host: contract | {"marker": "same-marker-for-all-hosts-00000000"} for host, contract in
                    filesystem["development_data_backup_filesystem"].items()}},
            ):
                with self.subTest(filesystem=bad):
                    rejected = run(filesystem | bad)
                    self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)
            for overrides in (
                {"development_data_package_version": "18.4.0-ce.0.el9"},
                {"development_data_client_cidrs": ["0.0.0.0/0"]},
                {"development_data_action": "apply"},
                {"development_data_action": "apply", "development_data_apply_confirm": True,
                 "development_data_package_version": "18.4.0-ce.0.el9"},
                {"development_data_ca_src": str(work / "missing.crt")},
                {"development_data_endpoints": inputs["development_data_endpoints"] | {"postgresql": "wrong.lab.test"}},
            ):
                with self.subTest(overrides=overrides):
                    result = run(overrides)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertNotIn("Gather the target operating system facts", result.stdout)


if __name__ == "__main__":
    unittest.main()
