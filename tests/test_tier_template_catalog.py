"""One project-owned consumer catalog, with template creation confined to Tier 0."""

import json
import unittest

from tier_repo_test_support import TierRepositoryTestCase


class SharedTemplateCatalog(TierRepositoryTestCase):
    def test_catalog_is_shared_and_tier_inputs_only_select_images(self):
        self.generate()
        catalog = self.root / "verify-shared/templates/proxmox-catalog.tfvars"
        self.assertTrue(catalog.is_file())
        self.assertIn("default_linux_vm_template_id = null", catalog.read_text())
        for tier in ("tier-0", "tier-1", "tier-2"):
            repo = self.root / f"verify-{tier}"
            common = (repo / "terraform/common.tfvars.example").read_text()
            self.assertNotRegex(common, r"(?m)^\s*(linux_vm_template_catalog|proxmox_template_catalog)\s*=")
            self.assertNotRegex(common, r"(?m)^\s*default_linux_vm_template_id\s*=")
            self.assertIn("../verify-shared/templates/proxmox-catalog.tfvars", common)
            self.assertIn("../verify-shared/templates/proxmox-catalog.tfvars", (repo / "README.md").read_text())
            self.assertFalse((repo / "templates/proxmox-catalog.tfvars").exists())
        for tier in ("tier-0", "tier-1", "tier-2"):
            variables = (self.root / f"verify-{tier}/terraform/modules/environment_guests/variables.tf").read_text()
            for field in ("title", "family", "node_name", "tags"):
                self.assertRegex(variables, rf"{field}\s*=")
        self.assertNotRegex(catalog.read_text(), r"(?m)^\s*(image_path|sha256|datastore_id|api_token)\s*=")

    def test_refresh_never_replaces_or_recreates_the_owned_catalog(self):
        self.generate()
        repo = self.root / "verify-shared"
        catalog = repo / "templates/proxmox-catalog.tfvars"
        manifest = json.loads((repo / ".generated-files.json").read_text())
        self.assertIn("templates/proxmox-catalog.tfvars", manifest["owned"])
        self.assertNotIn("templates/proxmox-catalog.tfvars", manifest["files"])
        catalog.write_text("# Project-approved references\n")
        self.generate("--refresh")
        self.assertEqual(catalog.read_text(), "# Project-approved references\n")
        catalog.unlink()
        self.generate("--refresh")
        self.assertFalse(catalog.exists())


if __name__ == "__main__":
    unittest.main()
