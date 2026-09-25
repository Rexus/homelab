"""Connection targets and known-host resets respect tier-local environment inputs."""

import json
import os
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase


@unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"),
                     "Requires Ansible on Linux/WSL")
class SSHInputs(TierRepositoryTestCase):
    def test_connection_targets_use_static_ips_or_environment_dns(self):
        self.generate()
        play = self.root / "verify-target.yml"
        play.write_text(yaml.safe_dump([{
            "hosts": "all", "gather_facts": False,
            "tasks": [{"ansible.builtin.assert": {"that": "ansible_host == expected_target"}}],
        }]))
        cases = (
            ({"platform_host_ips": {"guest-1": "192.0.2.10"}}, "192.0.2.10"),
            ({"platform_host_ips": {"guest-1": "dhcp"}}, "guest-1.corp.example.com"),
            ({"platform_host_ips": {"guest-1": "dhcp"}, "platform_hostname_prefix": "test",
              "platform_domain": "example.test"}, "test-guest-1.example.test"),
            ({"platform_host_ips": {"guest-1": "dhcp"}, "platform_hostname_suffix": "test",
              "platform_domain": "example.test"}, "guest-test-1.example.test"),
            ({"platform_host_ips": {}}, "guest-1"),
        )
        for tier in ("tier-0", "tier-1", "tier-2"):
            repo = self.root / f"verify-{tier}"
            inventory = yaml.safe_load((repo / "ansible/inventory/hosts.yml.example").read_text())
            inventory["all"]["children"] = {"guests": {"hosts": {"guest-1": {}}}}
            path = self.root / f"{tier}-hosts.yml"
            path.write_text(yaml.safe_dump(inventory))
            for overrides, expected in cases:
                with self.subTest(tier=tier, expected=expected):
                    result = subprocess.run([
                        "ansible-playbook", "-i", str(path), str(play),
                        "-e", f"@{repo / 'ansible/group_vars/all.yml.example'}",
                        "-e", json.dumps(dict(overrides, expected_target=expected)),
                    ], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which("ssh-keygen"), "Requires OpenSSH key tools")
    def test_reset_keeps_base_environment_and_unrelated_keys(self):
        self.generate()
        fixture = self.root / "ssh-fixture"
        fixture.mkdir()
        key = fixture / "key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
                       check=True, capture_output=True)
        public_key = key.with_suffix(".pub").read_text().strip()
        known_hosts = fixture / "known_hosts"
        retained = ("192.0.2.10", "[192.0.2.10]:22", "192.0.2.30", "dhcp")
        removed = ("192.0.2.20", "[192.0.2.20]:22")
        known_hosts.write_text("".join(f"{host} {public_key}\n" for host in (*retained, *removed)))
        # Flow-style YAML is valid too; use Ansible's parser and normal extra-vars precedence.
        base = fixture / "base.yml"
        base.write_text('platform_host_ips: {guest: "192.0.2.10", unrelated: "192.0.2.30"}\n')
        overlay = fixture / "test.yml"
        overlay.write_text('platform_host_ips: {guest: "192.0.2.20", dynamic: dhcp}\n')
        playbook = self.root / "verify-shared/ansible/playbooks/reset-known-hosts.yml"
        command = ["ansible-playbook", "-i", "localhost,", str(playbook),
                   "-e", f"@{base}", "-e", f"@{overlay}",
                   "-e", json.dumps({"known_hosts_file": str(known_hosts)})]
        for attempt in range(2):
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual({line.split()[0] for line in known_hosts.read_text().splitlines()}, set(retained))
            if attempt == 1:
                self.assertRegex(result.stdout, r"changed=0\s")


if __name__ == "__main__":
    unittest.main()
