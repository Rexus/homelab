"""Published references update Shared without changing consumer choices or old releases."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

import hcl2

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM

spec = importlib.util.spec_from_file_location("template_catalog_sync", UPSTREAM / "tier-0/scripts/lib/template-catalog.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class TemplateCatalogSync(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.catalog = Path(self.temp.name) / "consumer.tfvars"
        self.original = '''# Local selection stays under project control.
default_linux_vm_template_id = 110 # Already tested.
proxmox_template_catalog = {
  "109" = { title = "older-rocky", node_name = "pve02", family = "redhat", tags = ["retained"] }
  "110" = { title = "stale-title", node_name = "pve02", family = "redhat", tags = ["old"], note = "Keep this" }
}
# A project comment after the managed map.
'''
        self.catalog.write_text(self.original)
        self.candidates = {
            "rocky-build-1": {"vm_id": 110, "title": "rocky-10-tmpl", "node_name": "pve01",
                              "family": "redhat", "tags": ["el10", "rocky", "cloud-init"],
                              "sha256": "not-consumer-data", "image_path": "/private/artifact"},
            "talos-build-1": {"vm_id": 130, "title": "talos-tmpl", "node_name": "pve01",
                              "family": "talos", "tags": ["talos1", "cloud-init"]},
        }

    def values(self):
        return hcl2.loads(self.catalog.read_text(), serialization_options=hcl2.SerializationOptions(
            strip_string_quotes=True, with_comments=False,
        ))

    @unittest.skipUnless(shutil.which("terraform"), "Requires native Terraform formatting")
    def test_native_merge_preserves_default_retired_entries_and_is_idempotent(self):
        changed, default = sync.update_catalog(self.catalog, self.candidates)
        self.assertTrue(changed)
        self.assertEqual(default, 110)
        values = self.values()
        self.assertEqual(values["default_linux_vm_template_id"], 110)
        catalog = values["proxmox_template_catalog"]
        self.assertEqual(catalog["109"]["tags"], ["retained"])
        self.assertEqual(catalog["110"]["node_name"], "pve01")
        self.assertEqual(catalog["110"]["title"], "rocky-10-tmpl")
        self.assertEqual(catalog["110"]["note"], "Keep this")
        self.assertEqual(catalog["130"]["family"], "talos")
        self.assertNotIn("sha256", catalog["110"])
        self.assertNotIn("image_path", catalog["110"])
        self.assertIn("# Already tested.", self.catalog.read_text())
        self.assertIn("# A project comment after", self.catalog.read_text())
        before = self.catalog.read_bytes(), self.catalog.stat().st_mtime_ns
        self.assertEqual(sync.update_catalog(self.catalog, self.candidates), (False, 110))
        self.assertEqual((self.catalog.read_bytes(), self.catalog.stat().st_mtime_ns), before)

    @unittest.skipUnless(shutil.which("terraform"), "Requires native Terraform formatting")
    def test_unselected_default_stays_null_and_strings_remain_literal(self):
        self.catalog.write_text("default_linux_vm_template_id = null\nproxmox_template_catalog = {}\n")
        self.candidates["rocky-build-1"]["tags"] = ['literal-${not_a_variable}', 'literal-%{not_a_directive}']
        self.assertEqual(sync.update_catalog(self.catalog, self.candidates), (True, None))
        # Terraform, rather than only the Python parser, verifies literal string semantics.
        root = Path(self.temp.name) / "consumer"
        root.mkdir()
        (root / "main.tf").write_text('variable "default_linux_vm_template_id" { type = number }\n'
                                    'variable "proxmox_template_catalog" { type = any }\n')
        result = subprocess.run(["terraform", f"-chdir={root}", "console", f"-var-file={self.catalog}"],
                                input="jsonencode(var.proxmox_template_catalog)\n", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        catalog = json.loads(json.loads(result.stdout.strip()))
        self.assertEqual(catalog["110"]["tags"], self.candidates["rocky-build-1"]["tags"])

    def test_invalid_inputs_or_formatter_failure_leave_catalog_intact(self):
        for candidates in ({}, {"bad": {"vm_id": 110}},
                           {"a": self.candidates["rocky-build-1"], "b": self.candidates["rocky-build-1"]}):
            with self.assertRaises(ValueError):
                sync.update_catalog(self.catalog, candidates)
            self.assertEqual(self.catalog.read_text(), self.original)
        with patch.object(sync.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "terraform")):
            with self.assertRaises(subprocess.CalledProcessError):
                sync.update_catalog(self.catalog, self.candidates)
        self.assertEqual(self.catalog.read_text(), self.original)
        self.assertFalse(list(self.catalog.parent.glob(".proxmox-catalog-*")))
        self.catalog.write_text("proxmox_template_catalog = {\n")
        before = self.catalog.read_bytes()
        with self.assertRaises(Exception):
            sync.update_catalog(self.catalog, self.candidates)
        self.assertEqual(self.catalog.read_bytes(), before)

    def test_intervening_edit_is_not_overwritten(self):
        def edited_while_formatting(*args, **kwargs):
            self.catalog.write_text(self.original + "# Concurrent project edit.\n")
        with patch.object(sync.subprocess, "run", side_effect=edited_while_formatting):
            with self.assertRaisesRegex(ValueError, "changed during synchronization"):
                sync.update_catalog(self.catalog, self.candidates)
        self.assertTrue(self.catalog.read_text().endswith("# Concurrent project edit.\n"))


if __name__ == "__main__":
    unittest.main()
