"""Model/IaC drift, reusable contracts and generated manual ownership."""

from pathlib import Path
import re
import unittest
from intake_model_fixture import IntakeModelFixture
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from intake_sources import (
    MODEL,
    VIEWS,
    TF,
    VARS,
    INVENTORY,
    ROLE,
    selected_inputs,
    check_wiring,
    trace_map,
)
from intake_model import impact, validate_trace
from intake_platform import dependencies, check_platform
import copy
from intake_views import render
from software_intake import OUTPUTS


class IntakeModelContracts(IntakeModelFixture):
    def test_checked_native_model_and_sources_agree(self):
        self.check()
        affected = set(impact(self.model, "DEF-proxy"))
        self.assertTrue(
            {
                "RUN-cache-1",
                "RUN-cache-2",
                "VM-cache-1",
                "VM-cache-2",
                "L-Consumers",
                "R-Consumers",
                "UC-update",
            }
            <= affected
        )
        allocated = {(e["from"], e["to"]) for e in self.model["edges"] if e["kind"] == "allocated-to"}
        self.assertTrue(
            {("L-Proxy", "R-Pair"), ("L-Cache", "DISK-cache-1"), ("L-Cache", "DISK-cache-2")}
            <= allocated
        )

    def test_resource_queries_connect_consumers_and_physical_backing(self):
        required = set(dependencies(self.model, "L-Proxy"))
        self.assertTrue(
            {
                "P-virtualization",
                "P-network",
                "P-storage",
                "P-fabric",
                "P-servers",
                "P-drives",
                "P-switches",
            }
            <= required
        )
        self.assertNotIn("P-storage-network", required)
        affected = set(impact(self.model, "P-servers"))
        self.assertTrue({"VM-cache-1", "VM-cache-2", "L-Proxy", "UC-update", "SC-http-hit"} <= affected)
        self.assertTrue(
            any(e.get("id") == "P-cabling" and e["kind"] == "connected-to" for e in self.model["edges"])
        )

    def test_selected_vm_cannot_lose_its_resource_contract(self):
        model = copy.deepcopy(self.model)
        model["edges"] = [e for e in model["edges"] if e.get("id") != "NET-cache-1"]
        with self.assertRaisesRegex(ValueError, "Missing resource contract"):
            check_platform(self.root, model, selected_inputs(self.root))

    def test_virtual_attachment_must_reach_the_vm_module(self):
        self.change(
            "tier-2/terraform/deployments/cache/main.tf",
            "bridge                      = each.value.bridge",
            "bridge                      = null",
        )
        with self.assertRaisesRegex(ValueError, "no longer wired: bridge"):
            check_platform(self.root, self.model, selected_inputs(self.root))

    def test_model_change_requires_native_regeneration(self):
        self.change(
            "architecture/design/software-intake/policy-proxy/definition.sysml",
            "Cache eligible HTTP",
            "Cache only eligible HTTP",
        )
        with self.assertRaisesRegex(ValueError, "needs regeneration"):
            self.check()

    def test_member_lists_cannot_disagree(self):
        self.change(INVENTORY, "cache-2:", "cache-renamed:")
        with self.assertRaisesRegex(ValueError, "members and Ansible cache hosts disagree"):
            selected_inputs(self.root)

    def test_mount_must_bind_to_a_real_disk(self):
        self.change(VARS, "drive-scsi1", "drive-scsi9")
        with self.assertRaisesRegex(ValueError, "no unique Terraform disk"):
            selected_inputs(self.root)

    def test_source_links_and_model_identities_must_resolve(self):
        records = trace_map(self.root)
        (self.root / ROLE / "tasks/squid.yml").unlink()
        with self.assertRaisesRegex(ValueError, "missing trace target"):
            trace_map(self.root)
        records["UNKNOWN"] = records.pop("DEF-proxy")
        with self.assertRaisesRegex(ValueError, "unknown model identities"):
            validate_trace(self.model, records)

    def test_storage_safety_path_cannot_be_unwired(self):
        self.change(ROLE + "/tasks/main.yml", "import_tasks: storage.yml", "import_tasks: other.yml")
        with self.assertRaisesRegex(ValueError, "role wiring changed"):
            check_wiring(self.root)

    def test_drawing_cannot_reverse_the_model_flow(self):
        self.change(
            VIEWS / "logical.layout.svg",
            'data-from="Consumers" data-to="Proxy"',
            'data-from="Proxy" data-to="Consumers"',
        )
        with self.assertRaisesRegex(ValueError, "reverses or invents"):
            render(self.root, self.model, selected_inputs(self.root), "logical")

    def test_generated_svg_cannot_drift(self):
        self.change(OUTPUTS["placement"], "Cache VIP", "A different listener")
        with self.assertRaisesRegex(ValueError, "Stale generated output"):
            self.check()


class IntakeManualIntegration(TierRepositoryTestCase):
    def test_manual_includes_model_assets_and_preserves_project_design(self):
        self.generate()
        manual = self.root / "verify-architecture" / "docs/auto-docs"
        source = UPSTREAM / "architecture"
        copied = manual / "architecture"
        for path in source.rglob("*"):
            if path.is_file():
                self.assertTrue((copied / path.relative_to(source)).is_file(), path.name)
                if path.suffix not in (".md", ".svg"):
                    self.assertEqual(
                        path.read_bytes(), (copied / path.relative_to(source)).read_bytes()
                    )
        for name in ("model-map.md", "07-software-intake/02-connected-model.md"):
            page = manual / "01-architecture" / name
            for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", page.read_text(encoding="utf-8")):
                target = target.split("#")[0]
                if target and not target.startswith(("http:", "https:")):
                    self.assertTrue((page.parent / target).exists(), (name, target))
        for page in copied.rglob("*.md"):
            for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", page.read_text(encoding="utf-8")):
                target = target.split("#")[0]
                if target and not target.startswith(("http:", "https:")):
                    self.assertTrue((page.parent / target).exists(), (str(page), target))
        record = self.root / "verify-architecture" / "architecture" / "intake-design.sysml"
        record.parent.mkdir(exist_ok=True)
        record.write_text("package SiteIntake { /* Selected site design */ }\n")
        retired = manual / "architecture/design/logical/software-intake/context.sysml"
        retired.parent.mkdir(parents=True, exist_ok=True)
        retired.write_text("// Old generated reference\n")
        self.generate("--refresh")
        self.assertEqual(record.read_text(), "package SiteIntake { /* Selected site design */ }\n")
        self.assertFalse(retired.exists(), "Refresh must remove the retired generated source")


if __name__ == "__main__":
    unittest.main()
