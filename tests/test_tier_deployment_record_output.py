"""Successful deployment output points at a manual record without changing it."""

import os
from pathlib import Path
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


@unittest.skipIf(os.name == "nt", "Bash command fixtures run in isolated Linux/WSL")
class DeploymentRecordOutput(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.commands = self.parent / "commands"
        self.commands.mkdir(parents=True)
        fake = self.commands / "terraform"
        fake.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
tool, args = pathlib.Path(sys.argv[0]).name, sys.argv[1:]
steps = [arg for arg in args if arg in ("init", "validate", "plan", "apply", "destroy", "show", "output")]
step = steps[0] if steps else next((pathlib.Path(arg).name for arg in reversed(args)
                                  if arg.endswith(".yml") and not arg.startswith("@")), "")
if "-refresh-only" in args:
    step = "refresh"
if tool == os.getenv("RECORD_FAIL_TOOL") and step == os.getenv("RECORD_FAIL_STEP"):
    sys.exit(42)
if tool == "terraform":
    for arg in args:
        if arg.startswith("-out="):
            pathlib.Path(arg[5:]).write_text("fixture saved plan")
    if step in ("output", "show"):
        print("{}")
elif tool == "ansible-doc":
    print(json.dumps({name: {"doc": {"module": name}} for name in args
                      if name.startswith("community.proxmox.")}))
''')
        fake.chmod(0o755)
        for tool in ("ansible-doc", "ansible-playbook", "qemu-img"):
            (self.commands / tool).symlink_to(fake)
        self.environment = {
            name: value for name, value in os.environ.items()
            if not name.startswith(("PROXMOX_", "PM_", "TF_", "TEMPLATE_", "RECORD_"))
            and name != "DEPLOYMENT_REPO_DIR"
        }
        self.environment.update(PATH=f"{self.commands}:{os.environ['PATH']}", TEMPLATE_RUNTIME_MODE="check")

    def collection(self, *repositories):
        arguments = [argument for repo in repositories for argument in ("--repo", repo)]
        self.generate("--prefix", "HomeLab", *arguments)
        self.root = self.parent / "homelab-iac"
        self.record = self.root / "homelab-architecture/deployments.md"
        self.record.parent.mkdir(exist_ok=True)
        self.record.write_text("# Local deployments\n\n- [x] Existing service\n- [ ] ~~Unselected option~~\n")
        self.record_before = self.record.read_bytes()

    def run_script(self, repo, script, *arguments, **overrides):
        return subprocess.run(["bash", f"scripts/{script}.sh", *arguments], cwd=repo,
                              env=dict(self.environment, **overrides), capture_output=True,
                              text=True, timeout=30)

    def check_success(self, result, reminder=False, infrastructure=False):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        if reminder:
            self.assertIn(f"Deployment checklist: {self.record}", result.stdout)
            self.assertEqual(result.stdout.count("Deployment checklist:"), 1)
            self.assertIn("manually update the matching entry/option", result.stdout)
            self.assertIn("After completing the linked deployment path", result.stdout)
        else:
            self.assert_no_reminder(result)
        self.assertEqual("Infrastructure provisioned; service configuration pending." in result.stdout,
                         infrastructure)
        self.assertEqual(self.record.read_bytes(), self.record_before)

    def assert_no_reminder(self, result):
        self.assertNotIn("Deployment checklist:", result.stdout + result.stderr)
        self.assertNotIn("Infrastructure provisioned", result.stdout + result.stderr)

    def check_failure(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_no_reminder(result)
        self.assertEqual(self.record.read_bytes(), self.record_before)

    def test_path_resolution_handles_source_and_generated_repository_names(self):
        helper = UPSTREAM / "shared/scripts/lib/deployment-record.sh"
        cases = {
            "/kit/tier-0": "<prefix>-architecture/deployments.md",
            "/kit/tier-1": "<prefix>-architecture/deployments.md",
            "/kit/tier-2": "<prefix>-architecture/deployments.md",
            "/collection/homelab-tier-0": "/collection/homelab-architecture/deployments.md",
            "/collection/HomeLab-tier-1/": "/collection/homelab-architecture/deployments.md",
            "/parent with spaces/my-lab-tier-2": "/parent with spaces/my-lab-architecture/deployments.md",
        }
        for owner, expected in cases.items():
            with self.subTest(owner=owner):
                result = subprocess.run(["bash", "-eu", "-c", 'source "$1"; deployment_record_path "$2"',
                                         "record-test", str(helper), owner], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected + "\n")

    def test_deploy_reminds_after_full_or_ansible_runs_and_labels_terraform_only(self):
        self.collection("shared", "tier-2")
        repo = self.root / "homelab-tier-2"
        self.check_success(self.run_script(repo, "init-local-files", "--setup", "cache"))
        self.environment.update(TF_VAR_proxmox_api_url="https://pve.example.invalid:8006/",
                                TF_VAR_proxmox_api_token_id="fixture@pve!provision",
                                TF_VAR_proxmox_api_token_secret="fixture-disposable-value")

        for flags in ([], ["--ansible-only"], ["--terraform-only"]):
            with self.subTest(flags=flags):
                self.check_success(self.run_script(repo, "deploy", "cache", *flags), reminder=True,
                                   infrastructure="--terraform-only" in flags)
        for flags in (["--plan-only"], ["--plan-only", "--terraform-only"], ["--destroy"],
                      ["--destroy", "--terraform-only"], ["--recipe", "maintenance"],
                      ["--ansible-only", "--playbook", "maintenance/cache.yml"]):
            with self.subTest(flags=flags):
                self.check_success(self.run_script(repo, "deploy", "cache", *flags))
        for flags, tool, step in (([], "terraform", "init"), ([], "terraform", "apply"),
                                  (["--terraform-only"], "terraform", "apply"),
                                  ([], "ansible-playbook", "cache.yml"),
                                  (["--ansible-only"], "ansible-playbook", "cache.yml")):
            with self.subTest(flags=flags, step=step):
                self.check_failure(self.run_script(repo, "deploy", "cache", *flags,
                                   RECORD_FAIL_TOOL=tool, RECORD_FAIL_STEP=step))

        # The reminder is also informational when the project record does not exist yet.
        self.record.unlink()
        result = self.run_script(repo, "deploy", "cache", "--ansible-only")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"Deployment checklist: {self.record}", result.stdout)
        self.assertFalse(self.record.exists())

    def test_kubernetes_reminds_only_after_successful_apply(self):
        self.collection("shared", "tier-1")
        repo = self.root / "homelab-tier-1"
        self.check_success(self.run_script(repo, "kubernetes-cluster", "init"))
        self.check_failure(self.run_script(repo, "kubernetes-cluster", "apply"))
        self.check_success(self.run_script(repo, "kubernetes-cluster", "plan"))
        self.check_success(self.run_script(repo, "kubernetes-cluster", "export-plan"))
        self.check_failure(self.run_script(repo, "kubernetes-cluster", "apply",
                           RECORD_FAIL_TOOL="terraform", RECORD_FAIL_STEP="apply"))
        self.check_success(self.run_script(repo, "kubernetes-cluster", "apply"), reminder=True)
        state = repo / ".terraform/state/talos/terraform.tfstate"
        state.write_text("fixture state")
        self.check_success(self.run_script(repo, "kubernetes-cluster", "credentials"))
        self.check_failure(self.run_script(repo, "kubernetes-cluster", "credentials",
                           RECORD_FAIL_TOOL="terraform", RECORD_FAIL_STEP="output"))

    def test_template_apply_reminds_without_shared_only_after_all_publication_steps_succeed(self):
        self.collection("tier-0")
        repo = self.root / "homelab-tier-0"
        self.assertFalse((self.root / "homelab-shared").exists())
        for action in ("init", "setup", "plan", "import", "verify"):
            with self.subTest(action=action):
                self.check_success(self.run_script(repo, "proxmox-templates", action))
        for tool, step in (("terraform", "apply"), ("ansible-playbook", "template-policy.yml"),
                           ("terraform", "refresh")):
            with self.subTest(tool=tool, step=step):
                self.check_success(self.run_script(repo, "proxmox-templates", "plan"))
                self.check_failure(self.run_script(repo, "proxmox-templates", "apply",
                                   RECORD_FAIL_TOOL=tool, RECORD_FAIL_STEP=step))
        self.check_success(self.run_script(repo, "proxmox-templates", "plan"))
        self.check_success(self.run_script(repo, "proxmox-templates", "apply"), reminder=True)

        # The same standalone script also supports an upstream source-tree checkout.
        source_repo = repo.with_name("tier-0")
        repo.rename(source_repo)
        self.check_success(self.run_script(source_repo, "proxmox-templates", "plan"))
        result = self.run_script(source_repo, "proxmox-templates", "apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Deployment checklist: <prefix>-architecture/deployments.md", result.stdout)
        self.assertEqual(self.record.read_bytes(), self.record_before)


if __name__ == "__main__":
    unittest.main()
