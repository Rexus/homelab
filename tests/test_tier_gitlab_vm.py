"""Focused GitLab VM contracts and CLI failure tests; no live deployment acceptance."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

from tier_repo_test_support import UPSTREAM


TIER = UPSTREAM / "tier-1"
ROLE = TIER / "ansible/roles/gitlab_container"
NATIVE = os.name == "posix" and shutil.which("ansible-playbook")
SHELL = os.name == "posix" and shutil.which("bash")


def inputs(**overrides):
    values = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    values.update(gitlab_hostname="git.example.test", gitlab_external_url="https://git.example.test",
                  gitlab_container_image="docker.io/gitlab/gitlab-ce:18.5.0-ce.0",
                  gitlab_oidc_enabled=True, gitlab_oidc_client_accepted=True,
                  gitlab_oidc_issuer="https://sso.example.test/realms/private",
                  gitlab_oidc_client_id="gitlab", gitlab_oidc_client_secret='private"secret\\#{literal}',
                  gitlab_backup_enabled=True, gitlab_backup_custody_accepted=True,
                  gitlab_backup_repository="sftp:backup@nas.example.test:/backups/gitlab",
                  gitlab_backup_password_src="/private/password", gitlab_backup_ssh_key_src="/private/key",
                  gitlab_backup_known_hosts_src="/private/known_hosts")
    return values | overrides


def render(name, values):
    environment = Environment(undefined=StrictUndefined)
    environment.filters.update(bool=bool, ternary=lambda value, yes, no: yes if value else no,
                               to_json=json.dumps)
    return environment.from_string((ROLE / f"templates/{name}.j2").read_text()).render(**values)


class GitLabVMContracts(unittest.TestCase):
    def test_optional_disk_reaches_the_existing_vm_module(self):
        root = TIER / "terraform/deployments/development"
        variables = (root / "variables.tf").read_text()
        disk_type = re.search(r"extra_disks\s*=\s*optional\(list\(object\(\{(.*?)\}", variables, re.S)
        self.assertIsNotNone(disk_type)
        for field in ("interface", "size_gb", "datastore_id", "storage_class", "iothread", "discard", "ssd"):
            self.assertRegex(disk_type[1], rf"\b{field}\s*=")
        self.assertRegex((root / "main.tf").read_text(), r"extra_disks\s*=\s*each.value.extra_disks")
        self.assertIn('extra_disks                 = coalesce(try(vm.extra_disks, null), [])',
                      (TIER / "terraform/modules/environment_guests/main.tf").read_text())

    def test_native_oidc_preserves_subject_and_secret_literal(self):
        config = render("gitlab.rb", inputs())
        for expected in ("uid_field: 'sub'", "pkce: true", "discovery: true",
                         "omniauth_auto_link_user'] = []", "omniauth_block_auto_created_users'] = true",
                         "https://git.example.test/users/auth/openid_connect/callback", r"\#{literal}"):
            self.assertIn(expected, config)
        self.assertIn("backup_keep_time'] = 0", config)
        disabled = render("gitlab.rb", inputs(gitlab_oidc_enabled=False, gitlab_backup_enabled=False))
        self.assertNotIn("omniauth", disabled)
        self.assertNotIn("backup_path", disabled)

    def test_yaml_and_sensitive_controller_custody(self):
        for path in ROLE.rglob("*.yml"):
            yaml.safe_load(path.read_text())
        tasks = yaml.safe_load((ROLE / "tasks/initial-access.yml").read_text())
        read = next(task for task in tasks if "ansible.builtin.slurp" in task)
        copy = next(task for task in tasks if "ansible.builtin.copy" in task)
        self.assertTrue(read["no_log"])
        self.assertTrue(copy["no_log"])
        self.assertFalse(copy["diff"])
        self.assertFalse(copy["ansible.builtin.copy"]["force"])
        self.assertEqual(copy["delegate_to"], "localhost")
        storage = (ROLE / "tasks/storage.yml").read_text()
        self.assertLess(storage.index("name: data_volume"), storage.index("persistent directories"))
        self.assertIn("item.stdout in ['xfs', 'ext4', 'btrfs']", storage)
        unit = render("gitlab-container.service", inputs())
        self.assertIn("RequiresMountsFor=/srv/gitlab", unit)

    def test_recovery_gates_precede_live_changes(self):
        tasks = yaml.safe_load((ROLE / "tasks/recovery.yml").read_text())
        self.assertIn("gitlab_restore_confirm | bool", tasks[0]["ansible.builtin.assert"]["that"])
        source = (ROLE / "tasks/recovery.yml").read_text()
        self.assertLess(source.index("Reject a different image"), source.index("state: stopped\n\n- name: Restore"))
        self.assertIn("gitlab_restore_target_image.stdout", source)
        self.assertIn("GITLAB_ASSUME_YES=1", source)
        self.assertIn("gitlab:doctor:secrets", source)
        self.assertNotIn("enabled: true", source)

    def test_runbook_is_controller_driven_and_states_recovery_limits(self):
        guide = (UPSTREAM / "docs/03-deployment/stage-9-development/step-1b-source-control-vm.md").read_text()
        self.assertNotIn("podman exec -it", guide)
        for recipe in ("gitlab-vm-initial-access.yml", "gitlab-vm-backup.yml", "gitlab-vm-recovery.yml"):
            self.assertIn(recipe, guide)
        self.assertIn("matching", guide)
        self.assertIn("SSO", guide)


@unittest.skipUnless(SHELL, "Requires Linux Bash for native script execution")
class GitLabVMBackupFailures(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gitlab-vm-test-")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.home = self.work / "live"
        (self.home / "config").mkdir(parents=True)
        (self.home / "data/backups").mkdir(parents=True)
        for name in ("gitlab-secrets.json", "gitlab.rb"):
            (self.home / "config" / name).write_text("retained sensitive fixture\n")
        self.bin = self.work / "bin"
        self.bin.mkdir()
        self.trace = self.work / "trace"
        self.environment = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                                TRACE=str(self.trace), FIXTURE_HOME=str(self.home))
        self.stub("restic", '''printf 'restic %s\\n' "$*" >> "$TRACE"
case "$*" in *'cat config'*) exit "${REPOSITORY_STATUS:-0}" ;;
  *backup*) exit "${RESTIC_BACKUP_STATUS:-0}" ;; esac
''')
        self.stub("podman", '''printf 'podman %s\\n' "$*" >> "$TRACE"
case "$*" in
  *'gitlab-backup create'*)
    [[ "${EXPORT_STATUS:-0}" == 0 ]] || exit "$EXPORT_STATUS"
    for arg in "$@"; do
      if [[ "$arg" == BACKUP=* && "${MISSING_ARCHIVE:-0}" == 0 ]]; then
        printf native-archive > "$FIXTURE_HOME/data/backups/${arg#BACKUP=}_gitlab_backup.tar"
      fi
    done ;;
  *) printf image-fixture ;;
esac
''')
        self.script = self.work / "backup.sh"
        self.write_script()

    def stub(self, name, source):
        path = self.bin / name
        path.write_text("#!/bin/bash\nset -euo pipefail\n" + source)
        path.chmod(0o755)

    def write_script(self, **overrides):
        values = inputs(gitlab_home=str(self.home), gitlab_data_min_free_bytes=1, **overrides)
        source = render("backup.sh", values)
        source = source.replace("/run/gitlab-vm-backup.lock", str(self.work / "job.lock"))
        source = source.replace("/etc/gitlab-vm-backup", str(self.work))
        self.script.write_text(source)
        result = subprocess.run(["bash", "-n", self.script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def job(self, *args, **environment):
        return subprocess.run(["bash", self.script, *args], capture_output=True, text=True,
                              env=self.environment | environment, timeout=15)

    def trace_text(self):
        return self.trace.read_text() if self.trace.exists() else ""

    def test_wrong_password_and_absent_repository_never_initialize_or_export(self):
        for status in ("1", "10", "12"):
            with self.subTest(status=status):
                result = self.job(REPOSITORY_STATUS=status)
                self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("podman", self.trace_text())
        self.assertNotIn("init", self.trace_text())

    def test_failed_or_missing_native_archive_never_uploads(self):
        for failure in ({"EXPORT_STATUS": "1"}, {"MISSING_ARCHIVE": "1"}):
            with self.subTest(failure=failure):
                result = self.job(**failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Incomplete local set retained", result.stderr)
        self.assertFalse(any("backup --tag" in line for line in self.trace_text().splitlines()))

    def test_partial_restic_snapshot_preserves_export_and_skips_check(self):
        result = self.job(RESTIC_BACKUP_STATUS="3")
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        sets = list(self.home.glob("gitlab-vm-set.*"))
        self.assertEqual(len(sets), 1)
        self.assertTrue((sets[0] / "config/gitlab-secrets.json").is_file())
        self.assertTrue(list(sets[0].glob("*_gitlab_backup.tar")))
        self.assertFalse(any(line.endswith(" check") for line in self.trace_text().splitlines()))

    def test_success_uploads_archive_config_and_identity_then_removes_only_set(self):
        result = self.job()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        trace = self.trace_text()
        self.assertLess(trace.index("gitlab-backup create"), trace.index("backup --tag"))
        self.assertIn(" check", trace)
        self.assertNotIn("prune", trace)
        self.assertNotIn("forget", trace)
        self.assertEqual(list(self.home.glob("gitlab-vm-set.*")), [])
        self.assertTrue((self.home / "config/gitlab-secrets.json").is_file())

    def test_missing_nas_mount_rejects_before_repository_or_guest_access(self):
        mount = self.work / "nas"
        repository = mount / "repository"
        repository.mkdir(parents=True)
        contract = dict(mount=str(mount), source="nas.test:/gitlab", fstype="nfs4",
                        marker="independent-commissioned-marker-0001", uid=os.getuid(), gid=os.getgid())
        values = inputs(gitlab_home=str(self.home), gitlab_backup_transport="filesystem",
                        gitlab_backup_repository=str(repository), gitlab_backup_filesystem=contract)
        (self.work / "filesystem.sh").write_text(render("backup-filesystem.sh", values))
        self.write_script(gitlab_backup_transport="filesystem", gitlab_backup_repository=str(repository),
                          gitlab_backup_filesystem=contract)
        self.stub("findmnt", "exit 1\n")
        result = self.job("--initialize")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.trace_text(), "")
        self.assertEqual(list(repository.iterdir()), [])

    def test_foreign_marker_and_nonempty_missing_repository_never_initialize(self):
        mount = self.work / "commissioned"
        repository = mount / "repository"
        repository.mkdir(parents=True)
        marker = mount / ".development-data-backup-target"
        contract = dict(mount=str(mount), source="nas.test:/gitlab", fstype="nfs4",
                        marker="independent-commissioned-marker-0001", uid=os.getuid(), gid=os.getgid())
        values = inputs(gitlab_home=str(self.home), gitlab_backup_transport="filesystem",
                        gitlab_backup_repository=str(repository), gitlab_backup_filesystem=contract,
                        gitlab_backup_min_free_bytes=1)
        (self.work / "filesystem.sh").write_text(render("backup-filesystem.sh", values))
        self.write_script(gitlab_backup_transport="filesystem", gitlab_backup_repository=str(repository),
                          gitlab_backup_filesystem=contract, gitlab_backup_min_free_bytes=1)
        self.stub("findmnt", f"printf '%s\\n' '{mount} nas.test:/gitlab nfs4'\n")
        marker.write_text("foreign-marker")
        self.assertNotEqual(self.job("--initialize").returncode, 0)
        self.assertEqual(self.trace_text(), "")
        marker.write_text(contract["marker"])
        retained = repository / "preserve-damaged-repository"
        retained.write_text("retain")
        result = self.job("--initialize", REPOSITORY_STATUS="10")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing to initialize a nonempty repository", result.stderr)
        self.assertEqual(retained.read_text(), "retain")
        self.assertNotIn(" init", self.trace_text())


@unittest.skipUnless(NATIVE, "Requires Linux Ansible")
class GitLabVMAnsible(unittest.TestCase):
    def setUp(self):
        self.environment = dict(os.environ, ANSIBLE_CONFIG=str(TIER / "ansible/ansible.cfg"))

    def test_owned_playbook_syntax_and_native_module_arguments(self):
        for recipe in ("source-control-vm", "gitlab-vm-initial-access", "gitlab-vm-backup", "gitlab-vm-recovery"):
            result = subprocess.run(["ansible-playbook", "--syntax-check", "-i", "localhost,",
                                     str(TIER / f"ansible/playbooks/deployment/{recipe}.yml")],
                                    env=self.environment, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        arguments = {}
        for path in (ROLE / "tasks").glob("*.yml"):
            for task in yaml.safe_load(path.read_text()):
                for name, parameters in task.items():
                    if name.startswith("ansible.builtin.") and isinstance(parameters, dict) and name != "ansible.builtin.set_fact":
                        arguments.setdefault(name, set()).update(parameters)
        result = subprocess.run(["ansible-doc", "--json", *arguments], env=self.environment,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        documentation = json.loads(result.stdout)
        for name, parameters in arguments.items():
            options = documentation[name]["doc"]["options"]
            accepted = set(options)
            for option in options.values():
                accepted.update(option.get("aliases", []))
            self.assertFalse(parameters - accepted, f"Unsupported {name} options: {parameters - accepted}")

    def test_real_preflight_rejects_unsafe_interfaces(self):
        with tempfile.TemporaryDirectory(prefix="gitlab-vm-guards-") as directory:
            work = Path(directory)
            playbook, fixture = work / "play.yml", work / "inputs.yml"
            playbook.write_text(yaml.safe_dump([dict(hosts="localhost", connection="local", gather_facts=False,
                                                   tasks=[{"ansible.builtin.include_role": {
                                                       "name": "gitlab_container", "tasks_from": "preflight"}}])]))

            def run(overrides):
                fixture.write_text(yaml.safe_dump(inputs(**overrides)))
                return subprocess.run(["ansible-playbook", "-i", "localhost,", str(playbook), "-e", f"@{fixture}"],
                                      env=self.environment, capture_output=True, text=True, timeout=30)

            accepted = run({})
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            for overrides in ({"gitlab_home": "/srv/gitlab/../foreign"},
                              {"gitlab_oidc_client_accepted": False},
                              {"gitlab_oidc_issuer": "http://idp.test/realm"},
                              {"gitlab_backup_custody_accepted": False},
                              {"gitlab_backup_initialize": True},
                              {"gitlab_backup_repository": "sftp:backup@nas.test:/backup/../live"},
                              {"gitlab_omnibus_extra_config": ["gitlab_rails['backup_path'] = '/nas'"]}):
                with self.subTest(overrides=overrides):
                    rejected = run(overrides)
                    self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)


if __name__ == "__main__":
    unittest.main()
