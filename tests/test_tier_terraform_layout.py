"""Readable root modules and deliberate migration of existing project inputs."""

import hashlib
import json
import os
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase
from payload import TIERS, TERRAFORM_ONLY_DEPLOYMENTS


class TerraformLayout(TierRepositoryTestCase):
    def test_roots_have_consistent_navigation_and_framework_files(self):
        self.generate()
        for tier in TIERS:
            repo = self.root / f"verify-{tier}"
            setups = set((repo / ".deployment-setups").read_text().splitlines())
            expected = setups | TERRAFORM_ONLY_DEPLOYMENTS.get(tier, set())
            roots = {path.name for path in (repo / "terraform/deployments").iterdir()}
            self.assertEqual(roots, expected)
            self.assertFalse((repo / "terraform/environments").exists())
            self.assertFalse((repo / "terraform/talos").exists())
            self.assertFalse((repo / "terraform/templates").exists())
            readme = (repo / "README.md").read_text()
            for name in roots:
                root = repo / "terraform/deployments" / name
                for filename in ("main.tf", "providers.tf", "versions.tf", "variables.tf"):
                    self.assertTrue((root / filename).is_file(), root / filename)
                self.assertIn(f"terraform/deployments/{name}/main.tf", readme)
                self.assertNotIn('provider "', (root / "main.tf").read_text())
                self.assertIn('backend "local"', (root / "versions.tf").read_text())
                self.assertIn('provider "proxmox"', (root / "providers.tf").read_text())
        kubernetes = self.root / "verify-tier-0/terraform/deployments/kubernetes"
        self.assertIn('../../../ansible/inventory/hosts.yml', (kubernetes / "variables.tf").read_text())
        templates = self.root / "verify-tier-0/terraform/deployments/templates"
        self.assertIn('../../../templates/proxmox.yml', (templates / "variables.tf").read_text())

    def test_refresh_preserves_legacy_roots_local_inputs_and_state(self):
        self.generate()
        for tier, name, old in (("tier-2", "lab", "environments/lab"),
                                ("tier-0", "kubernetes", "talos"),
                                ("tier-0", "templates", "templates")):
            repo = self.root / f"verify-{tier}"
            root = repo / "terraform/deployments" / name
            legacy = repo / "terraform" / old
            legacy.parent.mkdir(parents=True, exist_ok=True)
            root.rename(legacy)
            # Model a previous generated manifest, not a locally deleted new root.
            manifest_path = repo / ".generated-files.json"
            manifest = json.loads(manifest_path.read_text())
            for relative in list(manifest["files"]):
                if relative.startswith(f"terraform/deployments/{name}/"):
                    previous = relative.replace(f"terraform/deployments/{name}/", f"terraform/{old}/")
                    manifest["files"][previous] = manifest["files"].pop(relative)
            manifest_path.write_text(json.dumps(manifest))
            (legacy / "terraform.tfvars").write_text("# Project hardware values\n")
            (legacy / "terraform.test.tfvars").write_text("# Project overlay\n")
            (legacy / "backend_override.tf").write_text("# Project backend\n")
            (legacy / "main.tf").write_text("# Project resources\n")
            state_name = {"templates": "proxmox-templates", "kubernetes": "talos"}.get(name, name)
            state_dir = f"{state_name}/prod" if name == "lab" else state_name
            state = repo / f".terraform/state/{state_dir}/terraform.tfstate"
            state.parent.mkdir(parents=True)
            state.write_text('{"serial": 12}\n')
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in self.root.rglob("*") if path.is_file()}
        result = self.generate("--refresh")
        self.assertEqual(result.stdout.count("Legacy Terraform deployment preserved:"), 3)
        for path, digest in before.items():
            if path.name != ".generated-files.json":
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest, path)
        for tier, name in (("tier-2", "lab"), ("tier-0", "kubernetes"), ("tier-0", "templates")):
            root = self.root / f"verify-{tier}/terraform/deployments/{name}"
            self.assertTrue((root / "main.tf").is_file())
            self.assertFalse((root / "terraform.tfvars").exists())

    @unittest.skipIf(os.name == "nt", "Bash migration checks run under Linux/WSL")
    def test_commands_stop_before_using_defaults_or_calling_terraform(self):
        self.generate()
        commands = self.root / "commands"
        commands.mkdir()
        calls = self.root / "called-terraform"
        fake = commands / "terraform"
        fake.write_text('#!/bin/sh\ntouch "$CALLS"\nexit 99\n')
        fake.chmod(0o755)
        env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", CALLS=str(calls))
        for name in ("DEPLOYMENT_REPO_DIR", "TEMPLATE_STATE_PATH", "TEMPLATE_CATALOG_FILE"):
            env.pop(name, None)
        cases = (
            ("tier-2", "environments/lab", "lab", [
                ["scripts/init-local-files.sh", "--setup", "lab"],
                ["scripts/deploy.sh", "lab", "--plan-only"]]),
            ("tier-0", "talos", "talos", [
                ["scripts/kubernetes-cluster.sh", action] for action in ("init", "plan", "apply", "credentials")]),
            ("tier-0", "deployments/talos", "talos", [
                [f"scripts/{script}-cluster.sh", action] for script in ("kubernetes", "talos")
                for action in ("init", "plan", "apply", "credentials")]),
            ("tier-0", "templates", "proxmox-templates", [
                ["scripts/proxmox-templates.sh", action] for action in ("init", "plan", "apply")]),
        )
        for tier, old, plan_name, actions in cases:
            repo = self.root / f"verify-{tier}"
            legacy = repo / "terraform" / old
            legacy.mkdir(parents=True)
            live = legacy / "terraform.tfvars.json"
            live.write_text('{"project": "existing"}\n')
            plan = repo / f".terraform/plans/{plan_name}.tfplan"
            plan.parent.mkdir(parents=True, exist_ok=True)
            plan.write_text("obsolete plan")
            for args in actions:
                result = subprocess.run(["bash", *args], cwd=repo, env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Legacy Terraform deployment", result.stderr)
            self.assertFalse(calls.exists())
            self.assertFalse((repo / "ansible/inventory/hosts.yml").exists())
            self.assertFalse((repo / "templates/proxmox.yml").exists())
            self.assertFalse(list((repo / "terraform/deployments").glob("*/terraform.tfvars")))
            if tier == "tier-0":
                self.assertFalse(plan.exists())
            live.unlink()
            # Empty legacy folders and old provider caches do not constitute a live root.
            (legacy / ".terraform").mkdir()
            result = subprocess.run(["bash", *actions[0]], cwd=repo, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            if tier == "tier-0" and old in ("talos", "deployments/talos"):
                (repo / "ansible/inventory/hosts.yml").unlink()
                (repo / "terraform/deployments/kubernetes/terraform.tfvars").unlink()

    def test_refresh_preserves_previous_cluster_name_and_existing_state(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        current = repo / "terraform/deployments/kubernetes"
        previous = repo / "terraform/deployments/talos"
        current.rename(previous)
        manifest_path = repo / ".generated-files.json"
        manifest = json.loads(manifest_path.read_text())
        for relative in list(manifest["files"]):
            if relative.startswith("terraform/deployments/kubernetes/"):
                old = relative.replace("deployments/kubernetes/", "deployments/talos/")
                manifest["files"][old] = manifest["files"].pop(relative)
        manifest_path.write_text(json.dumps(manifest))
        local_inputs = previous / "terraform.tfvars"
        local_inputs.write_text("# Existing cluster hardware\n")
        state = repo / ".terraform/state/talos/terraform.tfstate"
        state.parent.mkdir(parents=True)
        state.write_text('{"serial": 24}\n')
        before = {path: path.read_bytes() for path in previous.rglob("*") if path.is_file()}
        result = self.generate("--refresh")
        self.assertIn(f"Legacy Terraform deployment preserved: {previous}", result.stdout)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual(state.read_text(), '{"serial": 24}\n')
        self.assertTrue((current / "main.tf").is_file())
        self.assertFalse((current / "terraform.tfvars").exists())
        self.assertFalse((repo / ".terraform/state/kubernetes").exists())


if __name__ == "__main__":
    unittest.main()
