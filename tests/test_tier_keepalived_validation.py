"""Keepalived validation refuses incomplete groups before probes or owner stops."""

import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


TASKS = Path("ansible/roles/shared/tasks/keepalived_vip_validation.yml")
ANSIBLE = shutil.which("ansible-playbook")
ENABLED = "shared_keepalived_validation_enabled | default(true) | bool"
SENTINELS = ("NETWORK_FACTS_SENTINEL", "STOP_OWNER_SENTINEL", "LATER_PROBE_SENTINEL")


class KeepalivedValidation(TierRepositoryTestCase):
    def repositories(self):
        self.generate()
        return (UPSTREAM / "shared", self.root / "verify-shared")

    def test_generated_helper_preserves_native_gate_and_owner_recovery(self):
        source, generated = self.repositories()
        self.assertEqual((source / TASKS).read_bytes(), (generated / TASKS).read_bytes())
        tasks = yaml.safe_load((source / TASKS).read_text())
        first_setup = next(i for i, task in enumerate(tasks) if "ansible.builtin.setup" in task)
        self.assertTrue(all("ansible.builtin.assert" in task for task in tasks[:first_setup]))
        failover = next(task for task in tasks if "always" in task)
        restore, settle = failover["always"]
        self.assertEqual(restore["ansible.builtin.service"]["state"], "started")
        self.assertEqual(restore["when"], "shared_keepalived_owns_vip | default(false) | bool")
        self.assertIn("ansible.builtin.pause", settle)

    def run_fixture(self, owner, scenario, enabled=True):
        work = Path(self.temp.name) / f"{owner.name}-{scenario}-{enabled}"
        role_tasks = work / "roles/shared/tasks"
        role_tasks.mkdir(parents=True)
        tasks = yaml.safe_load((owner / TASKS).read_text())
        first_setup = next(i for i, task in enumerate(tasks) if "ansible.builtin.setup" in task)
        # Execute the real preflight unchanged; replace all remote/disruptive work with markers.
        safe_tasks = tasks[:first_setup] + [
            {"ansible.builtin.debug": {"msg": marker}, "when": ENABLED}
            for marker in SENTINELS
        ]
        (role_tasks / TASKS.name).write_text(yaml.safe_dump(safe_tasks, sort_keys=False))
        inventory = work / "hosts.yml"
        inventory.write_text(yaml.safe_dump({"all": {
            "vars": {"ansible_connection": "local", "ansible_host": "127.0.0.1"},
            "children": {"cache": {"hosts": {"cache1": {}, "cache2": {}}}},
        }}))
        validation = {
            "name": "Validate cache VIP in the next play",
            "hosts": "cache2" if scenario == "excluded" else "cache",
            "gather_facts": False,
            "vars": {
                "shared_keepalived_group": "cache",
                "shared_keepalived_vip": "192.0.2.10",
                "shared_keepalived_validation_enabled": enabled,
                "shared_keepalived_failover_enabled": True,
            },
            "tasks": [
                {"ansible.builtin.debug": {"msg":
                    "ACTIVE={{ ansible_play_hosts | sort }}; BATCH={{ ansible_play_batch | sort }}"}},
                {"ansible.builtin.include_role": {
                    "name": "shared", "tasks_from": "keepalived_vip_validation"}},
                {"ansible.builtin.debug": {"msg": "HELPER_COMPLETED"}},
            ],
        }
        if scenario == "serial":
            validation["serial"] = 1
        plays = [{
            "name": "Simulate cache provisioning in the first play",
            "hosts": "cache",
            "gather_facts": False,
            "tasks": [
                {"name": "Simulate cache1 OS disk provisioning failure",
                 "ansible.builtin.fail": {"msg": "CACHE1_PROVISIONING_FAILED"},
                 "when": "inventory_hostname == 'cache1' and fixture_scenario == 'failed'"},
                {"name": "Simulate cache1 being unreachable without contacting a host",
                 "ansible.builtin.ping": {},
                 "vars": {
                     "ansible_connection": "ssh",
                     # SSH fails through a local proxy process before opening any network connection.
                     "ansible_ssh_common_args": "-o ProxyCommand=" + (shutil.which("false") or "/bin/false"),
                     "ansible_ssh_args": "-o ControlMaster=no -o BatchMode=yes -o ConnectTimeout=1",
                     "ansible_ssh_retries": 0,
                 },
                 "when": "inventory_hostname == 'cache1' and fixture_scenario == 'unreachable'"},
            ],
            "vars": {"fixture_scenario": scenario},
        }, validation]
        playbook = work / "play.yml"
        playbook.write_text(yaml.safe_dump(plays, sort_keys=False))
        config = work / "ansible.cfg"
        config.write_text("[defaults]\nstdout_callback=default\nretry_files_enabled=False\n")
        command = [ANSIBLE, "-i", str(inventory), str(playbook)]
        if scenario == "limited":
            command.extend(["--limit", "cache2"])
        result = subprocess.run(
            command, cwd=work, capture_output=True, text=True, timeout=30,
            env=dict(os.environ, ANSIBLE_CONFIG=str(config), ANSIBLE_NOCOLOR="1",
                     ANSIBLE_ROLES_PATH=str(work / "roles"),
                     ANSIBLE_LOCAL_TEMP=str(work / "controller"),
                     ANSIBLE_REMOTE_TEMP=str(work / "remote")),
        )
        return result.returncode, result.stdout + result.stderr

    @unittest.skipUnless(os.name != "nt" and ANSIBLE and shutil.which("ssh"),
                         "Requires Linux/WSL Ansible and SSH")
    def test_incomplete_group_aborts_next_play_before_any_sentinel(self):
        for owner in self.repositories():
            for scenario in ("failed", "unreachable", "excluded", "limited", "serial"):
                with self.subTest(owner=owner, scenario=scenario):
                    status, output = self.run_fixture(owner, scenario)
                    self.assertNotEqual(status, 0, output)
                    self.assertIn("requires every member of cache", output)
                    if scenario == "serial":
                        self.assertIn("ACTIVE=['cache1', 'cache2']; BATCH=['cache1']", output)
                        self.assertIn("Missing from active play: []", output)
                        self.assertIn("Missing from current batch: ['cache2']", output)
                    else:
                        self.assertIn("ACTIVE=['cache2']; BATCH=['cache2']", output)
                        self.assertIn("Missing from active play: ['cache1']", output)
                        self.assertIn("Missing from current batch: ['cache1']", output)
                    if scenario == "failed":
                        self.assertIn("CACHE1_PROVISIONING_FAILED", output)
                    if scenario == "unreachable":
                        self.assertIn('"unreachable": true', output)
                    for marker in (*SENTINELS, "HELPER_COMPLETED"):
                        self.assertNotIn(marker, output)

    @unittest.skipUnless(os.name != "nt" and ANSIBLE, "Requires Linux/WSL Ansible")
    def test_healthy_group_reaches_the_validation_sentinels(self):
        for owner in self.repositories():
            with self.subTest(owner=owner):
                status, output = self.run_fixture(owner, "healthy")
                self.assertEqual(status, 0, output)
                for marker in (*SENTINELS, "HELPER_COMPLETED"):
                    self.assertEqual(output.count(marker), 2, output)

    @unittest.skipUnless(os.name != "nt" and ANSIBLE, "Requires Linux/WSL Ansible")
    def test_disabled_validation_skips_the_gate_for_an_incomplete_group(self):
        for owner in self.repositories():
            with self.subTest(owner=owner):
                status, output = self.run_fixture(owner, "excluded", enabled=False)
                self.assertEqual(status, 0, output)
                self.assertIn("HELPER_COMPLETED", output)
                for marker in SENTINELS:
                    self.assertNotIn(marker, output)
