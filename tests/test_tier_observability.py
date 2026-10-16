"""Foundational evidence stays Tier 0-owned; shared analytics does not replace it."""

import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class Observability(TierRepositoryTestCase):
    def test_source_and_generated_logging_are_tier_zero_owned(self):
        self.generate()
        for collection, prefix in ((UPSTREAM, ""), (self.root, "verify-")):
            tier = collection / f"{prefix}tier-0"
            self.assertIn("syslog", (tier / ".deployment-setups").read_text().splitlines())
            inventory = yaml.safe_load((tier / "ansible/inventory/hosts.yml.example").read_text())
            hosts = inventory["all"]["children"]["foundation_logging"]["hosts"]
            self.assertEqual(set(hosts), {"foundation-log-1"})
            inputs = yaml.safe_load((tier / "ansible/group_vars/syslog.yml.example").read_text())
            self.assertEqual(set(inputs["platform_host_ips"]), set(hosts))
            root = tier / "terraform/deployments/syslog"
            hardware = (root / "terraform.tfvars.example").read_text()
            self.assertIn('network_zone_key = "management"', hardware)
            self.assertIn('interface     = "scsi1"', hardware)
            self.assertIn('# "foundation-log-2"', hardware)
            self.assertIn('source = "../../modules/environment_guests"', (root / "main.tf").read_text())
            for recipe in ("deployment/foundation-logging.yml", "maintenance/syslog.yml"):
                plays = yaml.safe_load((tier / "ansible/playbooks" / recipe).read_text())
                self.assertEqual(plays[0]["hosts"], "foundation_logging")
                self.assertEqual(plays[0]["roles"], ["baseline"])
            for other in ("tier-1", "tier-2", "shared"):
                self.assertFalse((collection / f"{prefix}{other}/terraform/deployments/syslog").exists())
            platform = collection / f"{prefix}tier-1"
            hardware = (platform / "terraform/deployments/observability/terraform.tfvars.example").read_text()
            self.assertNotRegex(hardware, r'(?m)^  "(?:health-1|apm-1)" =')

    @unittest.skipUnless(shutil.which("bash"), "Requires Bash")
    def test_generated_syslog_initializer_uses_local_inventory_and_separate_inputs(self):
        self.generate()
        tier = self.root / "verify-tier-0"
        result = subprocess.run(["bash", "scripts/init-local-files.sh", "--setup", "syslog"],
                                cwd=tier, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for path in ("ansible/inventory/hosts.yml", "ansible/group_vars/syslog.yml",
                     "terraform/deployments/syslog/terraform.tfvars"):
            self.assertTrue((tier / path).is_file(), path)
        self.assertFalse((tier / "terraform/deployments/foundation/terraform.tfvars").exists())
        self.assertFalse((self.root / "verify-shared/ansible/inventory").exists())

    def test_design_and_stages_preserve_evidence_and_access_boundaries(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            logging = (docs / "architecture/operations/security-logging.md").read_text()
            for expected in ("no loss of accepted records within a declared failure envelope",
                             "not the HA acceptance state", "Dashboards", "WORM",
                             "Producers cannot read, edit or delete", "Application owner / developer"):
                self.assertIn(expected, logging)
            telemetry = (docs / "architecture/operations/telemetry.md").read_text()
            for expected in ("Data Prepper", "vmalert", "Alertmanager", "Tier 2 normally retains collection",
                             "not independent querying or alerts", "separate SigNoZ/ClickHouse"):
                self.assertIn(expected, telemetry)
            foundation = (docs / "deployment/stage-1-foundation/README.md").read_text()
            self.assertIn("## Step 4: Establish protected logging", foundation)
            self.assertIn("procedures/syslog.md", foundation)
            later = (docs / "deployment/stage-4-control-services/procedures/observability.md").read_text()
            self.assertIn("An app owner receives an application-log view", later)
            self.assertIn("receiver/retention", (docs / "deployment/stage-1-foundation/README.md").read_text())

    def test_refresh_preserves_existing_logging_and_analytics_decisions(self):
        self.generate()
        owned = {
            "verify-tier-0/.deployment-setups": "foundation\nvault\nhsm\n",
            "verify-tier-0/ansible/group_vars/syslog.yml": "# Local receiver policy\n",
            "verify-tier-0/.terraform/state/syslog/prod/terraform.tfstate": '{"lineage":"local-logs"}\n',
            "verify-tier-1/terraform/deployments/observability/terraform.tfvars": '# Existing apm-1 resources\n',
            "verify-tier-1/ansible/inventory/hosts.yml": "all: {hosts: {apm-1: {}}}\n",
            "verify-tier-0/docs/deployment/README.md": "# Local logging acceptance\n",
        }
        for relative, content in owned.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.generate("--refresh")
        for relative, content in owned.items():
            self.assertEqual((self.root / relative).read_text(), content, relative)


if __name__ == "__main__":
    unittest.main()
