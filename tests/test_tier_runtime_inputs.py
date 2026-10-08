"""Controller inputs stay stable across recipes without reaching managed hosts."""

import json
import os
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class RuntimeInputs(TierRepositoryTestCase):
    def test_secret_examples_keep_inventory_readable(self):
        variables = yaml.safe_load((UPSTREAM / "tier-0/ansible/group_vars/foundation.yml.example").read_text())
        self.assertIn("idm-1", variables["platform_host_ips"])
        for key, environment in (("dm", "FREEIPA_DM_PASSWORD"), ("admin", "FREEIPA_ADMIN_PASSWORD")):
            self.assertIn(f"lookup('ansible.builtin.env', '{environment}')",
                          variables[f"foundation_freeipa_{key}_password"])
        guide = (UPSTREAM / "docs/administration/secret-handling/ansible-vault.md").read_text()
        self.assertIn("--ansible-only --ansible-vars secrets/ansible-bootstrap-vars.yml", guide)
        self.assertIn("Do not encrypt inventory", guide)

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"),
                         "Requires Ansible on Linux/WSL")
    def test_tls_paths_and_password_injection_across_recipe_depths(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        variables = repo / "ansible/group_vars"
        environment = dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg"))
        environment.pop("FREEIPA_DM_PASSWORD", None)
        environment.pop("FREEIPA_ADMIN_PASSWORD", None)
        tasks = [{"ansible.builtin.assert": {"that": [
            "vault_tls_cert_src | realpath == expected_root + '/secrets/vault/vault01-fullchain.pem'",
            "vault_tls_key_src | realpath == expected_root + '/secrets/vault/vault01.key'",
            "vault_tls_ca_src | realpath == expected_root + '/secrets/vault/internal-ca.pem'",
            "foundation_freeipa_dm_password == expected_dm",
            "foundation_freeipa_admin_password == expected_admin",
        ]}}]
        for relative in ("ansible/playbooks/input-check.yml",
                         "ansible/playbooks/deployment/input-check.yml",
                         "ansible/playbooks/maintenance/input-check.yml"):
            playbook = repo / relative
            playbook.write_text(yaml.safe_dump([{"hosts": "localhost", "gather_facts": False, "tasks": tasks}]))
            for values in ({}, {"FREEIPA_DM_PASSWORD": "test-dm", "FREEIPA_ADMIN_PASSWORD": "test-admin"}):
                expected = {"expected_root": str(repo),
                            "expected_dm": values.get("FREEIPA_DM_PASSWORD", "change-me"),
                            "expected_admin": values.get("FREEIPA_ADMIN_PASSWORD", "change-me")}
                result = subprocess.run([
                    "ansible-playbook", "-i", "localhost,", str(playbook),
                    "-e", f"@{variables / 'foundation.yml.example'}",
                    "-e", f"@{variables / 'vault.yml.example'}", "-e", json.dumps(expected),
                ], env=dict(environment, **values), cwd=repo, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"),
                         "Requires Ansible on Linux/WSL")
    def test_ansible_only_precheck_does_not_execute_terraform(self):
        self.generate()
        common = yaml.safe_load((self.root / "verify-shared/ansible/playbooks/control-node.yml").read_text())
        terraform_task = next(task for task in common[0]["tasks"]
                              if task["name"] == "Verify Terraform is installed on the deployment machine")
        # A failing local stub proves whether the real precheck task was executed.
        commands = self.root / "commands"
        commands.mkdir()
        terraform = commands / "terraform"
        terraform.write_text("#!/bin/sh\necho unexpected-terraform-check >&2\nexit 97\n")
        terraform.chmod(0o755)
        playbook = self.root / "precheck.yml"
        playbook.write_text(yaml.safe_dump([{
            "hosts": "localhost", "connection": "local", "gather_facts": False, "tasks": [terraform_task],
        }]))
        environment = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}")
        for required in (False, True):
            result = subprocess.run([
                "ansible-playbook", "-i", "localhost,", str(playbook),
                "-e", json.dumps({"control_node_require_terraform": required}),
            ], env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, not required, result.stdout + result.stderr)
            if required:
                self.assertIn("unexpected-terraform-check", result.stdout + result.stderr)
