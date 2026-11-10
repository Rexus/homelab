"""Refresh maintained automation independently of site inputs and local extensions."""

import contextlib
import hashlib
import io
import json
import os
import subprocess
from unittest.mock import patch

from tier_repo_test_support import TierRepositoryTestCase
from generated_files import RepositoryWriter


class AutomationRefresh(TierRepositoryTestCase):
    def snapshot(self):
        return {path.relative_to(self.root): path.read_bytes()
                for path in self.root.rglob("*") if path.is_file()}

    def backup(self, path, data):
        relative = path.relative_to(self.root)
        return (self.root / ".refresh-backups" / relative).with_name(
            f"{path.name}.{hashlib.sha256(data).hexdigest()}.bak")

    def test_default_refresh_updates_automation_with_recoverable_backups(self):
        self.generate()
        paths = [self.root / "verify-tier-0" / relative for relative in (
            "ansible/playbooks/deployment/bootstrap-software-intake.yml",
            "terraform/modules/vm/main.tf", "ansible/runtime-requirements.txt",
            "terraform/deployments/foundation/.terraform.lock.hcl",
        )]
        paths += [self.root / "verify-shared" / relative for relative in (
            "ansible/roles/baseline/defaults/main.yml", "scripts/deploy.sh",
        )]
        originals = {path: path.read_bytes() for path in paths}
        edits = {path: b"# Local automation patch\n" + data for path, data in originals.items()}
        for path, data in edits.items():
            path.write_bytes(data)
        protected = [self.root / relative for relative in (
            "verify-tier-0/ansible/group_vars/bootstrap.yml",
            "verify-tier-0/ansible/ansible.cfg", "verify-tier-0/terraform/common.tfvars",
            "verify-tier-0/README.md", "verify-tier-0/.env.local",
            "verify-tier-0/.terraform/state/original.tfstate",
            "verify-tier-0/clusters/tier0/kustomization.yaml",
            "verify-tier-0/ansible/playbooks/custom-recovery.yml",
            "verify-shared/config/platform.tfvars", "verify-shared/config/guest-sizes.json",
            "verify-shared/templates/proxmox-catalog.tfvars",
        )]
        for path in protected:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"Local project configuration\n")
        result = self.generate("--refresh")
        for path, data in originals.items():
            self.assertEqual(path.read_bytes(), data)
            backup = self.backup(path, edits[path])
            self.assertEqual(backup.read_bytes(), edits[path])
            self.assertIn(f"REPLACED {path}", result.stdout)
            self.assertIn(f"Previous version: {backup}", result.stdout)
            if os.name != "nt":
                self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        for path in protected:
            self.assertEqual(path.read_bytes(), b"Local project configuration\n", path)
        retained = {path: path.read_bytes() for path in (self.root / ".refresh-backups").rglob("*.bak")}
        self.assertNotIn("REPLACED", self.generate("--refresh").stdout)
        paths[0].write_bytes(edits[paths[0]])
        self.generate("--refresh")
        self.assertEqual({path: path.read_bytes() for path in (self.root / ".refresh-backups").rglob("*.bak")}, retained)

    def test_dry_run_is_write_free_and_preserve_mode_keeps_comparison_templates(self):
        self.generate()
        path = self.root / "verify-tier-0/ansible/playbooks/deployment/bootstrap-software-intake.yml"
        current = path.read_bytes()
        path.write_bytes(b"# Local work\n")
        before = self.snapshot()
        output = self.generate("--refresh", "--dry-run").stdout
        self.assertEqual(self.snapshot(), before)
        self.assertIn(f"WOULD REPLACE {path}", output)
        self.assertIn(f"Planned backup: {self.backup(path, path.read_bytes())}", output)
        self.generate("--refresh", "--code-conflicts", "ask", "--dry-run")
        self.assertEqual(self.snapshot(), before)
        output = self.generate("--refresh", "--code-conflicts", "preserve").stdout
        self.assertEqual(path.read_bytes(), b"# Local work\n")
        self.assertIn(f"YELLOW {path}", output)
        self.assertEqual((self.root / ".refresh-review" / path.relative_to(self.root)).read_bytes(), current)
        self.assertFalse((self.root / ".refresh-backups").exists())

    def test_unverified_existing_code_is_preserved_even_with_replace_selected(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        relative = "ansible/playbooks/deployment/bootstrap-software-intake.yml"
        path = repo / relative
        path.write_bytes(b"# Unverified project content\n")
        manifest = repo / ".generated-files.json"
        values = json.loads(manifest.read_text())
        values["files"].pop(relative)
        manifest.write_text(json.dumps(values))
        output = self.generate("--refresh").stdout
        self.assertEqual(path.read_bytes(), b"# Unverified project content\n")
        self.assertIn("generation ownership is unverified", output)
        self.assertFalse((self.root / ".refresh-backups").exists())

    def test_ask_requires_a_terminal_and_offers_a_rendered_candidate(self):
        self.generate()
        before = self.snapshot()
        with self.assertRaises(subprocess.CalledProcessError) as failure:
            self.generate("--refresh", "--code-conflicts", "ask")
        self.assertIn("requires an interactive terminal", failure.exception.stderr)
        self.assertEqual(self.snapshot(), before)
        repo = self.root / "interactive"
        with contextlib.redirect_stdout(io.StringIO()):
            writer = RepositoryWriter(repo)
            writer.write("scripts/example.py", b"# Kit\n", automation=True)
            writer.finish()
            path = repo / "scripts/example.py"
            path.write_bytes(b"# Local work\n")
            writer = RepositoryWriter(repo, refresh=True, code_conflicts="ask")
            with patch("builtins.input", side_effect=["invalid", ""]) as prompt:
                writer.write("scripts/example.py", b"# Updated kit\n", automation=True)
            self.assertEqual(prompt.call_count, 2)
            writer.finish()
            self.assertEqual(path.read_bytes(), b"# Local work\n")
            candidate = self.root / ".refresh-review/interactive/scripts/example.py"
            self.assertEqual(candidate.read_bytes(), b"# Updated kit\n")
            writer = RepositoryWriter(repo, refresh=True, code_conflicts="ask")
            with patch("builtins.input", return_value="replace"):
                writer.write("scripts/example.py", b"# Updated kit\n", automation=True)
            writer.finish()
        self.assertEqual(path.read_bytes(), b"# Updated kit\n")
        self.assertEqual(self.backup(path, b"# Local work\n").read_bytes(), b"# Local work\n")

    def test_unusable_backup_prevents_replacing_the_local_file(self):
        repo = self.root / "backup-check"
        with contextlib.redirect_stdout(io.StringIO()):
            writer = RepositoryWriter(repo)
            writer.write("scripts/example.py", b"# Kit\n", automation=True)
            writer.finish()
            path = repo / "scripts/example.py"
            path.write_bytes(b"# Local work\n")
            backup = self.backup(path, path.read_bytes())
            backup.parent.mkdir(parents=True)
            backup.write_bytes(b"Incorrect backup content\n")
            writer = RepositoryWriter(repo, refresh=True)
            with self.assertRaisesRegex(ValueError, "Backup differs"):
                writer.write("scripts/example.py", b"# New kit\n", automation=True)
            self.assertEqual(path.read_bytes(), b"# Local work\n")
            if os.name != "nt":
                backup.unlink()
                external = self.root / "external.py"
                external.write_bytes(b"Outside backup\n")
                backup.symlink_to(external)
                with self.assertRaisesRegex(ValueError, "symlink"):
                    writer.write("scripts/example.py", b"# New kit\n", automation=True)
                self.assertEqual(external.read_bytes(), b"Outside backup\n")
                self.assertEqual(path.read_bytes(), b"# Local work\n")
