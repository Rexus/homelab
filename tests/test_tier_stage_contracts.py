"""Stage entry points distinguish supplied automation from intended end states."""

import os
import shutil
import stat
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class StageContracts(TierRepositoryTestCase):
    def test_os_baseline_does_not_advertise_unimplemented_security_controls(self):
        self.generate()
        unused = {"baseline_manage_packages", "baseline_manage_ssh", "baseline_disable_password_auth",
                  "baseline_permit_root_login", "baseline_manage_firewall", "baseline_ntp_enabled"}
        for collection, prefix in ((UPSTREAM, ""), (self.root, "verify-")):
            defaults = collection / f"{prefix}shared/ansible/roles/baseline/defaults/main.yml"
            self.assertFalse(unused.intersection(yaml.safe_load(defaults.read_text())))
            for tier in range(3):
                path = collection / f"{prefix}tier-{tier}/ansible/group_vars/all.yml.example"
                self.assertFalse(unused.intersection(yaml.safe_load(path.read_text())))
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            boundary = (docs / "reference/platform-inputs.md").read_text()
            self.assertIn("## OS baseline boundary", boundary)
            self.assertIn("not a full security", boundary)
            cluster = (docs / "deployment/stage-3-identity/procedures/kubernetes.md").read_text()
            self.assertIn("7. Security events", cluster)
            self.assertIn("API audit policy is not supplied", cluster)

    @unittest.skipUnless(os.name != "nt" and shutil.which("bash"), "Requires Linux file permissions and Bash")
    def test_new_local_inputs_and_overwrite_backups_are_private(self):
        self.generate()
        tier = self.root / "verify-tier-0"
        command = ["bash", "-c", "umask 022\nexec bash scripts/init-local-files.sh --setup syslog \"$@\"", "init"]
        for arguments in ([], ["--overwrite"]):
            result = subprocess.run([*command, *arguments], cwd=tier, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for relative in (".env.local", "terraform/common.tfvars", "ansible/inventory/hosts.yml",
                         "ansible/group_vars/syslog.yml", "terraform/deployments/syslog/terraform.tfvars"):
            path = tier / relative
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600, relative)
            backups = list(path.parent.glob(path.name + ".bak.*"))
            self.assertEqual(len(backups), 1, relative)
            self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600, relative)
        for relative in ("shared/scripts/deploy.sh", "tier-0/scripts/proxmox-templates.sh",
                         "shared/scripts/kubernetes-cluster.sh"):
            self.assertIn("umask 077", (UPSTREAM / relative).read_text())

    def test_first_six_stages_disclose_automation_before_the_numbered_path(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            stages = sorted((docs / "deployment").glob("stage-*/README.md"))[:6]
            self.assertEqual(len(stages), 6)
            for stage in stages:
                content = stage.read_text()
                opening = content.split("## Main path", 1)[0]
                self.assertIn("**Automation:**", opening, str(stage))
                self.assertIn("implementation-support.md#first-six-stages", opening, str(stage))
            support = (docs / "reference/implementation-support.md").read_text()
            summary = support.split("## First six stages", 1)[1].split("## Detailed coverage", 1)[0]
            self.assertIn("not yet an end-to-end installer", summary)
            self.assertIn("Stage 3, Step 3", summary)
            for stage in stages:
                self.assertIn(f"deployment/{stage.parent.name}/README.md", summary)
            self.assertIn("empty manifests do not meet a stage gate", " ".join(summary.split()))

    def test_software_issuer_path_hands_off_later_work_without_backwards_dependencies(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            software = (docs / "deployment/stage-2-trust/procedures/software-pki.md").read_text()
            self.assertIn('id="complete-identity-and-acceptance"', software)
            self.assertIn("## Accept the issuer and continue", software)
            self.assertIn("In Stage 3", software)
            self.assertIn("not a Stage 2 acceptance dependency", software)
            migration = docs / "administration/cryptography/hardware-migration.md"
            self.assertTrue(migration.is_file())
            self.assertFalse((docs / "architecture/cryptography/hardware-migration.md").exists())
            self.assertIn("## Qualify and roll over", migration.read_text())
            alternative = (docs / "deployment/stage-6-observability/step-1b-dedicated-vms.md").read_text()
            self.assertIn("Observability, Steps 2-4", alternative)
            self.assertIn("do not allocate or install a separate diagnostics runtime", alternative)
