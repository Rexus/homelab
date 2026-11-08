"""The maintained VMID plan matches starter allocations and generated references."""

import json
import re
import xml.etree.ElementTree as ET

import hcl2
import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class VmidConventions(TierRepositoryTestCase):
    def test_starter_ids_match_categories_without_cluster_wide_collisions(self):
        linux_categories = {
            0: {"foundation": 2, "hsm": 2, "vault": 2, "cluster-endpoint": 3,
                "syslog": 4, "infrastructure-runner": 5},
            1: {"development": 2, "development-data": 2, "podman-runner": 5, "observability": 4},
            2: {"edge": 3, "cache": 3, "lab": 2},
        }
        allocated = {}

        def reserve(vmid, location):
            self.assertIsInstance(vmid, int, location)
            self.assertGreaterEqual(vmid, 100, location)
            self.assertNotIn(vmid, allocated, f"{location} collides with {allocated.get(vmid)}")
            allocated[vmid] = location

        for tier in range(3):
            for path in sorted((UPSTREAM / f"tier-{tier}/terraform/deployments").glob("*/terraform.tfvars.example")):
                with path.open(encoding="utf-8") as stream:
                    values = hcl2.load(stream)
                setup = path.parent.name
                for name, guest in {**values.get("vm_instances", {}), **values.get("lxc_instances", {}),
                                    **values.get("nodes", {})}.items():
                    vmid = guest["vm_id"]
                    location = f"tier-{tier}/{setup}/{name}"
                    reserve(vmid, location)
                    if setup in ("template-refresh", "immutable-template"):
                        self.assertTrue(9000 <= vmid <= 9999, location)
                        continue
                    if setup == "kubernetes":
                        category = 0 if "k8ctl" in name else 1
                    else:
                        category = linux_categories[tier][setup]
                    group = 3 if tier == 2 and setup in ("lab", "kubernetes") else tier
                    start = (category + 1) * 100 if tier == 0 else group * 1000 + category * 100
                    self.assertTrue(start <= vmid < start + 100, f"{location}: {vmid} outside {start}-{start+99}")
                # Commented optional guest examples also reserve IDs, not source-template references.
                for match in re.finditer(r"(?m)^\s*#\s+vm_id\s*=\s*(\d+)", path.read_text(encoding="utf-8")):
                    reserve(int(match[1]), f"tier-{tier}/{setup}/optional")
        catalog = yaml.safe_load((UPSTREAM / "tier-0/templates/proxmox.yml.example").read_text())
        for key, image in catalog["templates"].items():
            self.assertTrue(9000 <= image["vm_id"] <= 9999, key)
            reserve(image["vm_id"], f"templates/{key}")
        # The manual bootstrap host is separate from the later IaC runner and all Terraform guests.
        self.assertNotIn(601, allocated)

        refresh = yaml.safe_load((UPSTREAM / "tier-0/ansible/group_vars/template_refresh.yml.example").read_text())
        for replacement in refresh["template_refresh_replacements"]:
            self.assertIn(replacement["staged_vm_id"], allocated)
            self.assertIn(replacement["target_vm_id"], allocated)
            self.assertNotEqual(replacement["staged_vm_id"], replacement["target_vm_id"])

    def test_quick_reference_is_managed_and_reachable_from_reader_and_code_paths(self):
        self.generate()
        repo = self.root / "verify-architecture"
        manual = repo / "docs/auto-docs"
        relative = "conventions/vmid-convention.md"
        image = "conventions/vmid-convention.svg"
        reference = (manual / relative).read_text(encoding="utf-8")
        self.assertIn("AUTO-DOCS - DO NOT EDIT", reference)
        self.assertIn("**`2103` = Tier 2, Kubernetes worker, instance 03**", reference)
        self.assertIn("100 × (C + 1) + NN", reference)
        self.assertIn("three security tiers", reference)
        self.assertIn("retain its local VMIDs and state", reference)
        self.assertEqual((manual / image).read_bytes(), (UPSTREAM / "docs" / image).read_bytes())
        manifest = json.loads((repo / ".generated-files.json").read_text())
        for asset in (relative, image):
            self.assertIn(f"docs/auto-docs/{asset}", manifest["files"])
        for name in ("README.md", "docs/development/code-layout.md", "docs/deployment/foundation/README.md"):
            self.assertIn("vmid-convention.md", (UPSTREAM / name).read_text(), name)
        for tier in range(3):
            self.assertIn(relative, (self.root / f"verify-tier-{tier}/README.md").read_text())
        worksheet = repo / "platform-standards.md"
        self.assertIn(relative, worksheet.read_text())
        worksheet.write_text("# Project allocations\nKeep the existing local VMIDs.\n")
        self.generate("--refresh")
        self.assertIn("Keep the existing local VMIDs", worksheet.read_text())

    def test_visual_reference_has_the_same_categories_and_readable_format(self):
        path = UPSTREAM / "docs/conventions/vmid-convention.svg"
        diagram = ET.fromstring(path.read_text(encoding="utf-8"))
        self.assertAlmostEqual(float(diagram.attrib["width"]) / float(diagram.attrib["height"]), 4 / 3)
        text = " ".join(diagram.itertext())
        for label in ("T C NN", "Tier (T)", "Category (C)", "Kubernetes control plane",
                      "Kubernetes workers", "Infrastructure services", "Network / Edge",
                      "Observability", "Bootstrap / Automation", "Other / Reserved", "2103"):
            self.assertIn(label, text)
        self.assertIn("aria-labelledby", diagram.attrib)


if __name__ == "__main__":
    import unittest
    unittest.main()
