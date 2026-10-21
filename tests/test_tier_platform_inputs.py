"""Common references are owned data; guest assignments and key files stay local."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from payload import TIERS


class PlatformInputs(TierRepositoryTestCase):
    def test_shared_profile_is_seed_owned_and_refresh_preserves_deletion(self):
        self.generate()
        shared = self.root / "verify-shared"
        profile = shared / "config/platform.tfvars"
        manifest = json.loads((shared / ".generated-files.json").read_text())
        self.assertIn("config/platform.tfvars", manifest["owned"])
        self.assertNotIn("config/platform.tfvars", manifest["files"])
        original = profile.read_bytes()
        self.generate("--refresh")
        self.assertEqual(profile.read_bytes(), original)
        profile.write_text('default_platform_node_name = "site-node"\n')
        self.generate("--refresh", "--dry-run")
        self.generate("--refresh")
        self.assertEqual(profile.read_text(), 'default_platform_node_name = "site-node"\n')
        profile.unlink()
        self.generate("--refresh")
        self.assertFalse(profile.exists())

    def test_only_tier_specific_networks_and_overrides_remain_local(self):
        expected = {
            "tier-0": {"management", "identity", "cryptography"},
            "tier-1": {"delivery_edge", "observability"},
            "tier-2": {"external_edge"},
        }
        profile = (UPSTREAM / "shared/config/platform.tfvars").read_text()
        self.assertIn("shared_network_zones = {", profile)
        self.assertEqual(profile.count("  application = {"), 1)
        for name in ("identity", "cryptography", "ceremony", "external_edge", "delivery_edge"):
            self.assertNotIn(f"  {name} = {{", profile)
        for tier in TIERS:
            root = UPSTREAM / tier
            common = (root / "terraform/common.tfvars.example").read_text()
            self.assertEqual(set(re.findall(r"^  (\w+) = \{", common, re.MULTILINE)), expected[tier])
            self.assertNotRegex(common, r"(?m)^ssh_public_keys\s*=")
            self.assertNotRegex(common, r"(?m)^proxmox_storage_classes\s*=")
            self.assertIn("TF_VAR_ssh_public_key_files", (root / "env.local.example").read_text())
            for setup in (root / ".deployment-setups").read_text().splitlines():
                deployment = root / "terraform/deployments" / setup
                self.assertIn('variable "ssh_public_key_files"', (deployment / "variables.tf").read_text())
                self.assertIn('variable "shared_network_zones"', (deployment / "variables.tf").read_text())
                self.assertRegex((deployment / "main.tf").read_text(),
                                 r"network_zones\s*=\s*merge\(var.shared_network_zones, var.network_zones\)")
                self.assertRegex((deployment / "main.tf").read_text(),
                                 r"ssh_public_key_files\s*=\s*var.ssh_public_key_files")

    @unittest.skipUnless(shutil.which("git"), "Requires Git")
    def test_keys_are_ignored_but_platform_profile_is_trackable(self):
        repo = Path(self.temp.name) / "ignore-check"
        repo.mkdir()
        shutil.copyfile(UPSTREAM / ".gitignore", repo / ".gitignore")
        subprocess.run(["git", "init", "--quiet", str(repo)], check=True, capture_output=True)
        for relative in ("id_ed25519", "secrets/id_rsa", "operator.pub", ".ssh/custom-key", ".env.local"):
            result = subprocess.run(["git", "check-ignore", relative], cwd=repo, capture_output=True)
            self.assertEqual(result.returncode, 0, relative)
        result = subprocess.run(["git", "check-ignore", "shared/config/platform.tfvars"],
                                cwd=repo, capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    @unittest.skipUnless(os.name != "nt" and shutil.which("terraform"), "Requires Terraform in Linux/WSL")
    def test_native_public_key_file_validation_without_providers(self):
        # Use the real module input contract, with no resources, providers or remote calls.
        repo = Path(self.temp.name) / "keys"
        repo.mkdir()
        inputs = {"name": "test", "node_name": "test", "template_vm_id": 9100,
                  "bridge": "test", "disk_size_gb": 32}
        (repo / "terraform.tfvars.json").write_text(json.dumps(inputs))
        key = repo / "operator.pub"
        for tier in TIERS:
            shutil.copyfile(UPSTREAM / tier / "terraform/modules/vm/variables.tf", repo / "variables.tf")
            subprocess.run(["terraform", "init", "-backend=false", "-input=false"],
                           cwd=repo, check=True, capture_output=True)
            for content, valid in (
                ("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITest operator\n", True),
                ("-----BEGIN OPENSSH PRIVATE KEY-----\nsecret\n", False),
                ("ssh-ed25519 AAAA one\nssh-ed25519 BBBB two\n", False),
                ("not a key\n", False),
                (None, False),
            ):
                if content is None:
                    key.unlink()
                else:
                    key.write_text(content)
                result = subprocess.run(
                    ["terraform", "plan", "-input=false", "-no-color",
                     f"-var=ssh_public_key_files={json.dumps([str(key)])}"],
                    cwd=repo, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode == 0, valid, f"{tier}: {result.stdout}{result.stderr}")


if __name__ == "__main__":
    unittest.main()
