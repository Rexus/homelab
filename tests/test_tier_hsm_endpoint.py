"""Private USB-HSM endpoint design and opt-in scaffold remain aligned."""

import json
import os
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class HSMEndpoint(TierRepositoryTestCase):
    def test_design_separates_native_remoting_api_and_external_endpoint_scaffold(self):
        design = (UPSTREAM / "docs/01-architecture/08-cryptography/04-usb-hsm.md").read_text()
        for phrase in ("E1: Client failover", "E2: Private VIP", "E3: Private VIP and proxies",
                       "p11-kit", "restricted SSH", "YubiHSM 2", "PicoHSM", "public-key fingerprints",
                       "default Shamir", "does not make backups interchangeable", "No implicit product migration"):
            self.assertIn(phrase, design)
        deployment = (UPSTREAM / "docs/03-deployment/stage-3-trust/step-1b-usb-hsm.md").read_text()
        self.assertIn("scripts/deploy.sh hsm", deployment)
        self.assertIn("pkcs11-remoting.md", deployment)
        remoting = yaml.safe_load((UPSTREAM / "tier-0/ansible/roles/hsm_remote/defaults/main.yml").read_text())
        self.assertIs(remoting["hsm_remote_enabled"], False)
        self.assertEqual(remoting["hsm_remote_backends"], {})
        self.assertEqual(remoting["hsm_remote_expected_spki_sha256"], "")
        listener = (UPSTREAM / "tier-0/ansible/roles/hsm_remote/templates/sshd_config.j2").read_text()
        for boundary in ("ForceCommand", "DisableForwarding yes", "PasswordAuthentication no", "PermitTTY no"):
            self.assertIn(boundary, listener)
        single = (UPSTREAM / "docs/03-deployment/stage-3-trust/step-1d-single-usb.md").read_text()
        self.assertIn("hsm-issuer.yml", single)
        self.assertIn("hsm-token.yml", single)
        self.assertIn("do not bring offline root custody online", single)
        vm_inputs = (UPSTREAM / "tier-0/terraform/deployments/hsm/terraform.tfvars.example").read_text()
        self.assertIn('proxmox_node_name = "pve01"', vm_inputs)
        self.assertIn('proxmox_node_name = "pve02"', vm_inputs)
        self.assertNotIn("shared edge load-balancer", vm_inputs)
        baseline = yaml.safe_load((UPSTREAM / "tier-0/ansible/playbooks/deployment/hsm-gateways.yml").read_text())
        self.assertTrue(any(play.get("roles") == ["baseline"] for play in baseline))
        self.assertTrue(any(play.get("roles") == ["hsm_provider"] for play in baseline))

    @unittest.skipUnless(os.name != "nt" and shutil.which("ansible-playbook"),
                         "Requires Ansible on Linux/WSL")
    def test_renderer_is_opt_in_and_rejects_unvalidated_prerequisites(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        inventory = self.root / "local-hosts.yml"
        inventory.write_text(yaml.safe_dump({"all": {
            "vars": {"ansible_connection": "local"},
            "children": {"hsm_gateways": {"hosts": {"hsm-1": {}, "hsm-2": {}}}},
        }}))
        output = self.root / "rendered"
        inputs = {"ansible_become": False,
                  "platform_host_ips": {"hsm-1": "192.0.2.10", "hsm-2": "192.0.2.11"},
                  "hsm_proxy_ingress_output_dir": str(output) + "/{{ inventory_hostname }}"}
        variables = self.root / "inputs.json"

        def run(overrides):
            variables.write_text(json.dumps(dict(inputs, **overrides)))
            return subprocess.run(
                ["ansible-playbook", "-i", str(inventory), "ansible/playbooks/ingress.yml",
                 "-e", f"@{variables}"], cwd=repo,
                env=dict(os.environ, ANSIBLE_CONFIG=str(repo / "ansible/ansible.cfg")),
                capture_output=True, text=True,
            )

        disabled = run({})
        self.assertEqual(disabled.returncode, 0, disabled.stdout + disabled.stderr)
        self.assertFalse(output.exists())
        for overrides in (
            {"hsm_proxy_ingress_enabled": True},
            {"hsm_proxy_ingress_enabled": True,
             "hsm_proxy_ingress_application_ha_validated": True,
             "hsm_proxy_ingress_readiness_validated": True},
        ):
            rejected = run(overrides)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("explicitly validated application HA", rejected.stdout + rejected.stderr)
            self.assertFalse(output.exists())

        # Configuration rendering only: this fixture does not probe a signing service.
        accepted = {"hsm_proxy_ingress_enabled": True,
                    "hsm_proxy_ingress_application_ha_validated": True,
                    "hsm_proxy_ingress_readiness_validated": True,
                    "hsm_proxy_ingress_extra_backend_lines": [
                        "option httpchk GET /ready", "http-check expect status 200"]}
        for count in (2, 3):
            with self.subTest(replicas=count):
                hosts = {f"hsm-{number}": {} for number in range(1, count + 1)}
                inventory.write_text(yaml.safe_dump({"all": {
                    "vars": {"ansible_connection": "local"},
                    "children": {"hsm_gateways": {"hosts": hosts}},
                }}))
                inputs["platform_host_ips"] = {
                    host: f"192.0.2.{10 + number}" for number, host in enumerate(hosts)}
                rendered = run(accepted)
                self.assertEqual(rendered.returncode, 0, rendered.stdout + rendered.stderr)
                for host in hosts:
                    content = (output / host / "hsm-gateways-backend.cfg").read_text()
                    self.assertIn("mode tcp", content)
                    self.assertIn("http-check expect status 200", content)
                    for backend, address in inputs["platform_host_ips"].items():
                        self.assertIn(f"server {backend} {address}:8443", content)
                    self.assertEqual(content.count("  server "), count)
                repeated = run(accepted)
                self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
                self.assertNotRegex(repeated.stdout, r"changed=[1-9]")


if __name__ == "__main__":
    unittest.main()
