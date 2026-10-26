"""Tier 1 Observability scales independently without owning Tier 0 evidence."""

import re
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class Observability(TierRepositoryTestCase):
    def test_source_and_generated_vm_alternative_separates_roles_without_syslog(self):
        self.generate()
        expected = {"otel-1", "otel-2", "metrics-1", "metrics-2",
                    "search-1", "search-2", "search-3"}
        for collection, prefix in ((UPSTREAM, ""), (self.root, "verify-")):
            tier = collection / f"{prefix}tier-1"
            groups = yaml.safe_load((tier / "ansible/inventory/hosts.yml.example").read_text())["all"]["children"]
            self.assertEqual(set(groups["observability"]["hosts"]), expected)
            for legacy in ("telemetry_gateways", "security_telemetry", "archive"):
                self.assertNotIn(legacy, groups)
                self.assertNotIn(legacy, groups["guests"]["children"])
            inputs = yaml.safe_load((tier / "ansible/group_vars/observability.yml.example").read_text())
            self.assertEqual(set(inputs["platform_host_ips"]), expected)
            self.assertEqual(len(set(inputs["platform_host_ips"].values())), len(expected))
            hardware = (tier / "terraform/deployments/observability/terraform.tfvars.example").read_text()
            self.assertEqual(set(re.findall(r'^  "([^"]+)" = \{', hardware, re.MULTILINE)), expected)
            self.assertEqual(hardware.count('network_zone_key  = "observability"'), len(expected))
            self.assertEqual(hardware.count('storage_class     = "local"'), len(expected))
            self.assertIn('proxmox_node_name = "pve03"', hardware)
            for recipe in ("deployment/telemetry-hosts.yml", "maintenance/observability.yml"):
                plays = yaml.safe_load((tier / "ansible/playbooks" / recipe).read_text())
                self.assertEqual(plays[0]["roles"], ["baseline"])
                self.assertIn("observability", plays[0]["hosts"].split(":"))

    def test_kubernetes_first_design_and_native_installer_are_explicit(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            design = (docs / "architecture/operations/telemetry.md").read_text()
            for expected in ("logs, metrics and distributed traces", "Security Logging and Audit",
                             "do **not** have equal resource needs", "existing Tier 1 Kubernetes cluster",
                             "included initially", "readers must have no update/delete",
                             "Tier 1 index deletion never deletes Tier 0 originals"):
                self.assertIn(expected, design)
            deployment = (docs / "deployment/stage-8-observability/README.md").read_text()
            for expected in ("OpenSearch is included initially", "observability-platform.yml",
                             "writes to both", "replica shards", "complete worker/physical-host loss",
                             "no archive write/delete, retention or backup powers"):
                self.assertIn(expected, deployment)
        for tier in (UPSTREAM / "tier-1", self.root / "verify-tier-1"):
            starter = yaml.safe_load((tier / "clusters/tier1/platform/observability/kustomization.yaml").read_text())
            self.assertFalse(starter.get("resources"))
            self.assertTrue((tier / "ansible/playbooks/deployment/observability-platform.yml").is_file())
            self.assertTrue((tier / "ansible/roles/observability_platform/templates/releases.yml.j2").is_file())

    def test_source_and_generated_logging_are_tier_zero_owned(self):
        self.generate()
        for collection, prefix in ((UPSTREAM, ""), (self.root, "verify-")):
            tier = collection / f"{prefix}tier-0"
            self.assertIn("syslog", (tier / ".deployment-setups").read_text().splitlines())
            inventory = yaml.safe_load((tier / "ansible/inventory/hosts.yml.example").read_text())
            hosts = inventory["all"]["children"]["foundation_logging"]["hosts"]
            self.assertEqual(set(hosts), {"log-1"})
            inputs = yaml.safe_load((tier / "ansible/group_vars/syslog.yml.example").read_text())
            self.assertEqual(set(inputs["platform_host_ips"]), set(hosts))
            root = tier / "terraform/deployments/syslog"
            hardware = (root / "terraform.tfvars.example").read_text()
            self.assertIn('network_zone_key = "management"', hardware)
            self.assertIn('interface     = "scsi1"', hardware)
            for name in hosts:
                self.assertIn(f'  "{name}" = {{', hardware)
            self.assertIn('# "log-2"', hardware)
            self.assertIn('source = "../../modules/environment_guests"', (root / "main.tf").read_text())
            for recipe in ("deployment/foundation-logging.yml", "maintenance/syslog.yml"):
                plays = yaml.safe_load((tier / "ansible/playbooks" / recipe).read_text())
                self.assertEqual(plays[0]["hosts"], "foundation_logging")
                self.assertEqual(plays[0]["roles"], ["baseline", "syslog_ng"])
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
        inventory = yaml.safe_load((tier / "ansible/inventory/hosts.yml").read_text())
        hosts = inventory["all"]["children"]["foundation_logging"]["hosts"]
        inputs = yaml.safe_load((tier / "ansible/group_vars/syslog.yml").read_text())
        self.assertEqual(set(hosts), {"log-1"})
        self.assertEqual(set(inputs["platform_host_ips"]), set(hosts))
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
            foundation = (docs / "deployment/foundation/README.md").read_text()
            self.assertIn("Stage 2: Protected logging", foundation)
            later = (docs / "deployment/stage-8-observability/README.md").read_text()
            self.assertIn("An app owner receives an application-log view", later)
            logging_stage = (docs / "deployment/stage-2-logging/README.md").read_text()
            self.assertIn("declared durability limits", logging_stage)
            self.assertIn("independent encrypted backups", logging_stage)
            self.assertIn("lossless HA", logging_stage)

    def test_early_collection_and_offline_recovery_contracts_are_published(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            foundation = (docs / "deployment/foundation/README.md").read_text()
            self.assertIn("persistent local host logs from first boot", foundation)
            logging = (docs / "architecture/operations/security-logging.md").read_text()
            for expected in ("## Offline-readable evidence", "UTF-8 JSON Lines",
                             "independently held recovery kit", "no retention or backup authority"):
                self.assertIn(expected, logging)
            procedure = (docs / "deployment/stage-2-logging/README.md").read_text()
            self.assertIn("before PKI and FreeIPA", procedure)
            self.assertIn("Only the log-data volume and offline kit survive", procedure)
            operations = (docs / "administration/security-logging.md").read_text()
            self.assertIn("no-journal-replay", operations)
            self.assertIn("never let reindexing modify originals", operations)
            backup = (docs / "administration/compute/backup-restore.md").read_text()
            for expected in ("**3-2-1**", "including the primary", "two different",
                             "DatastoreBackup", "Datastore.Prune", "RPO", "RTO"):
                self.assertIn(expected, backup)
            recovery = (docs / "administration/recovery.md").read_text()
            self.assertLess(recovery.index("| 1 | Isolate"), recovery.index("| 3 | Restore Tier 0 intake"))
            self.assertLess(recovery.index("| 3 | Restore Tier 0 intake"), recovery.index("| 4 | Restore Tier 0 trust"))
        runbook = (self.root / "verify-architecture/docs/administration/recovery.md").read_text()
        self.assertIn("offline reader/key kit", runbook)
        self.assertIn("RPO/RTO and pruning custodian", runbook)

    def test_archive_choices_preserve_nas_limits_and_stronger_retention_as_an_option(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            design = (docs / "architecture/operations/log-retention.md").read_text()
            self.assertIn("A: NAS snapshots and independent backups", design)
            self.assertIn("B: Storage-enforced retention locks", design)
            self.assertIn("One person holding several roles is acceptable", design)
            self.assertIn("not evidence of WORM enforcement", design)
            self.assertIn("## Review triggers", design)
            stage = docs / "deployment/stage-2-logging"
            overview = (stage / "README.md").read_text()
            for option in ("step-3c-nas-archive.md", "step-3d-retention-lock.md"):
                self.assertIn(option, overview)
                self.assertIn(option, design)
                content = (stage / option).read_text()
                self.assertIn("**Automation boundary:**", content)
                for step in range(1, 4):
                    self.assertIn(f"## Step {step}:", content)
            drill = (docs / "administration/logging-drill.md").read_text()
            self.assertIn("not a passed prevention test", drill)
        record = (self.root / "verify-tier-0/docs/administration/logging-evidence.md").read_text()
        self.assertIn("Archive choice: A NAS-backed, B retention-locked, or combined", record)
        self.assertIn("residual privileged-deletion risk", record)

    def test_refresh_preserves_existing_logging_and_analytics_decisions(self):
        self.generate()
        owned = {
            "verify-tier-0/.deployment-setups": "foundation\nvault\nhsm\n",
            "verify-tier-0/ansible/inventory/hosts.yml": yaml.safe_dump({
                "all": {"children": {"foundation_logging": {"hosts": {"foundation-log-1": {}}}}},
            }),
            "verify-tier-0/ansible/group_vars/syslog.yml": yaml.safe_dump({
                "platform_host_ips": {"foundation-log-1": "10.10.10.30"},
            }),
            "verify-tier-0/terraform/deployments/syslog/terraform.tfvars": (
                'vm_instances = { "foundation-log-1" = { vm_id = 264 } }\n'
            ),
            "verify-tier-0/.terraform/state/syslog/prod/terraform.tfstate": '{"lineage":"local-logs"}\n',
            "verify-tier-1/terraform/deployments/observability/terraform.tfvars": (
                'vm_instances = { "logs-1" = { vm_id = 262 } }\n'
            ),
            "verify-tier-1/ansible/inventory/hosts.yml": (
                "all: {children: {security_telemetry: {hosts: {syslog-1: {}, logs-1: {}}}}}\n"
            ),
            "verify-tier-1/ansible/group_vars/observability.yml": (
                "platform_host_ips: {syslog-1: 10.20.31.10, logs-1: 10.20.31.11}\n"
            ),
            "verify-tier-1/terraform/common.tfvars": 'network_zones = { security_telemetry = {} }\n',
            "verify-tier-1/.terraform/state/observability/prod/terraform.tfstate": '{"lineage":"local-telemetry"}\n',
            "verify-tier-1/README.md": "# Local platform and observability\n",
            "verify-tier-0/docs/deployment/README.md": "# Local logging acceptance\n",
            "verify-architecture/docs/administration/recovery.md": "# Local offline logging runbook\n",
        }
        for relative, content in owned.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.generate("--refresh")
        for relative, content in owned.items():
            self.assertEqual((self.root / relative).read_text(), content, relative)
        starter = self.root / "verify-tier-0/ansible/inventory/hosts.yml.example"
        inventory = yaml.safe_load(starter.read_text())
        self.assertEqual(set(inventory["all"]["children"]["foundation_logging"]["hosts"]), {"log-1"})


if __name__ == "__main__":
    unittest.main()
