"""Infrastructure diagnostics stay visible without moving Tier 0 control into Tier 1."""

import re

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class InfrastructureMonitoring(TierRepositoryTestCase):
    def test_source_and_generated_guides_cover_netdata_and_hardware(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            stage = docs / "deployment/stage-8-observability"
            overview = (stage / "README.md").read_text()
            self.assertEqual(re.findall(r"(?m)^## Step (\d+):", overview), ["1", "2", "3", "4"])
            self.assertIn('id="step-3-publish-and-verify-read-only-views"', overview)
            self.assertIn("infrastructure-monitoring.md", overview)
            for name in ("Netdata", "Proxmox", "hardware sensors", "critical alerting in Tier 0"):
                self.assertIn(name, overview)
            guide = " ".join((stage / "infrastructure-monitoring.md").read_text().split())
            for expected in ("Tier 0 owns Proxmox/BMC targets", "read-only", "Redfish", "IPMI",
                             "separate identities, data volumes", "parent synchronization",
                             "node-OS compatibility", "approved metrics", "cannot power-cycle",
                             "Tier 1 unavailable", "missing signals"):
                self.assertIn(expected.lower(), guide.lower())
            for step in range(1, 4):
                self.assertIn(f"## Step {step}:", guide)
            design = (docs / "architecture/operations/telemetry.md").read_text()
            for expected in ("## Infrastructure coverage", "Netdata remains part of Observability",
                             "No Tier 1 access", "raw Tier 0 Netdata views or Functions",
                             "unknown, not evidence of health", "two diagnostic domains",
                             "no default native Netdata stream or parent replication"):
                self.assertIn(expected, design)

    def test_diagram_scope_matches_native_installers_and_tier_local_inventory(self):
        self.generate()
        for collection, prefix, docs in (
            (UPSTREAM, "", UPSTREAM / "docs"),
            (self.root, "verify-", self.root / "verify-architecture/docs/auto-docs"),
        ):
            starter = collection / f"{prefix}tier-1/clusters/tier1/platform/observability/kustomization.yaml"
            self.assertEqual(yaml.safe_load(starter.read_text())["resources"], [])
            inventory = collection / f"{prefix}tier-0/ansible/inventory/hosts.yml.example"
            groups = yaml.safe_load(inventory.read_text())["all"]["children"]
            self.assertIn("hypervisors", groups)
            self.assertFalse((collection / f"{prefix}shared/ansible/inventory").exists())
            overview = (docs / "deployment/stage-8-observability/README.md").read_text()
            code = re.findall(r"```mermaid\n(.*?)```", overview, re.DOTALL)[2]
            for expected in ('subgraph T1[', 'subgraph T0[', "Existing platform Kubernetes",
                             "native releases", "Existing / manually inventoried",
                             "Native streaming", "Approved OTLP metrics"):
                self.assertIn(expected, code)
            self.assertIn("roles/infrastructure_monitoring", overview)
            self.assertIn("roles/observability_platform", overview)
            for tier, role in (("tier-0", "infrastructure_monitoring"),
                               ("tier-1", "observability_platform")):
                self.assertTrue((collection / f"{prefix}{tier}/ansible/roles/{role}/tasks/main.yml").is_file())
            self.assertIn("flowchart BT", code)
            self.assertIn("T0 ---->|Approved OTLP metrics| T1", code)
            self.assertIn("Inputs -->|Health metrics| Local", code)
