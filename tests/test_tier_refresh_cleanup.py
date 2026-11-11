"""Refresh resets missing templates and cleans only the managed auto-docs namespace."""

import contextlib
import io
import json
import os
import shutil
import unittest

from tier_repo_test_support import TierRepositoryTestCase
from documentation_migration import prune_auto_docs
from generated_files import RepositoryWriter


class RefreshCleanup(TierRepositoryTestCase):
    def snapshot(self):
        return {path.relative_to(self.root): path.read_bytes() if path.is_file() else None
                for path in self.root.rglob("*")}

    @unittest.skipIf(os.name == "nt", "Requires unprivileged symlinks")
    def test_writer_rejects_symlinked_parent_inside_repository(self):
        repo = self.root / "verify-architecture"
        target = repo / "docs/auto-docs/01-architecture"
        target.mkdir(parents=True)
        sentinel = target / "README.md"
        sentinel.write_text("# Preserved document\n", encoding="utf-8")
        (target.parent / "architecture").symlink_to(target, target_is_directory=True)
        writer = RepositoryWriter(repo, refresh=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            writer.write("docs/auto-docs/architecture/README.md", "# Compatibility guide\n")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "# Preserved document\n")

    def test_refresh_restores_missing_scripts_owned_starters_and_the_complete_manual(self):
        self.generate()
        targets = [
            self.root / "verify-tier-0/scripts/proxmox-templates.sh",
            self.root / "verify-tier-0/README.md",
            self.root / "verify-shared/config/platform.tfvars",
            self.root / "verify-shared/templates/proxmox-catalog.tfvars",
            self.root / "verify-tier-0/.deployment-setups",
        ]
        manual = self.root / "verify-architecture/docs/auto-docs"
        targets += [path for path in manual.rglob("*") if path.is_file()]
        expected = {path: path.read_bytes() for path in targets}
        self.assertTrue(manual.resolve().is_relative_to(self.root.resolve()))
        shutil.rmtree(manual)
        for path in targets:
            if path.exists():
                path.unlink()
        before = self.snapshot()
        self.generate("--refresh", "--dry-run")
        self.assertEqual(self.snapshot(), before)
        self.generate("--refresh")
        for path, content in expected.items():
            self.assertEqual(path.read_bytes(), content, path)
        self.assertTrue(os.access(targets[0], os.X_OK))
        self.assertFalse((self.root / "verify-tier-0/.env.local").exists())
        self.assertFalse((self.root / "verify-tier-0/.terraform/state").exists())
        output = self.generate("--refresh").stdout
        self.assertIn("YELLOW: 0 preserved differences; RED: 0 retired files", output)

    def test_cleanup_includes_untracked_and_edited_retired_files_but_preserves_project_content(self):
        self.generate()
        repo = self.root / "verify-architecture"
        manual = repo / "docs/auto-docs"
        obsolete = manual / "retired/nested/old-guide.md"
        obsolete.parent.mkdir(parents=True)
        obsolete.write_text("# Extra file, never in the manifest\n")
        (manual / "empty/nested").mkdir(parents=True)
        manifest_path = repo / ".generated-files.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["owned"].append(obsolete.relative_to(repo).as_posix())
        recorded = manual / "retired/recorded.md"
        recorded.write_text("# Edited retired guide\n")
        manifest["files"][recorded.relative_to(repo).as_posix()] = "previous-generated-hash"
        untracked = manual / "extra.bin"
        untracked.write_bytes(b"untracked auto-doc asset")
        manifest_path.write_text(json.dumps(manifest))
        current = manual / "01-architecture/README.md"
        current.write_text("# Local edits to a current reference\n")
        protected = [repo / "README.md", repo / "docs/local.md", repo / ".env.local",
                     repo / ".terraform/state/original.tfstate"]
        for path in protected:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Local project data\n")
        before = self.snapshot()
        preview = self.generate("--repo", "architecture", "--refresh", "--dry-run").stdout
        self.assertEqual(self.snapshot(), before)
        self.assertIn(f"WOULD REMOVE {untracked}", preview)
        self.generate("--repo", "shared", "--refresh")
        self.assertTrue(untracked.exists())
        output = self.generate("--repo", "architecture", "--refresh").stdout
        for path in (obsolete, recorded, untracked):
            self.assertFalse(path.exists())
            self.assertIn(f"REMOVED {path}", output)
        self.assertFalse((manual / "retired").exists())
        self.assertFalse((manual / "empty").exists())
        for path in protected:
            self.assertEqual(path.read_text(), "Local project data\n")
        self.assertEqual(current.read_text(), "# Local edits to a current reference\n")
        manifest = json.loads(manifest_path.read_text())
        self.assertNotIn(obsolete.relative_to(repo).as_posix(), manifest["owned"])
        self.assertNotIn(recorded.relative_to(repo).as_posix(), manifest["files"])

    @unittest.skipIf(os.name == "nt", "Requires unprivileged symlinks")
    def test_cleanup_rejects_symlinks_before_removing_any_file(self):
        repo = self.root / "verify-architecture"
        manual = repo / "docs/auto-docs"
        manual.mkdir(parents=True)
        retired = manual / "a-retired.md"
        retired.write_text("Retain if cleanup validation fails\n")
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel.md"
        sentinel.write_text("Outside the managed tree\n")
        for target in (outside, sentinel, retired):
            link = manual / "z-link"
            link.symlink_to(target, target_is_directory=target.is_dir())
            with contextlib.redirect_stdout(io.StringIO()):
                writer = RepositoryWriter(repo, refresh=True)
                with self.assertRaisesRegex(ValueError, "symlink/junction"):
                    prune_auto_docs(writer, set())
            self.assertTrue(retired.exists())
            self.assertEqual(sentinel.read_text(), "Outside the managed tree\n")
            link.unlink()
        retired.unlink()
        manual.rmdir()
        manual.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink/junction"):
            prune_auto_docs(writer, set())
        self.assertEqual(sentinel.read_text(), "Outside the managed tree\n")
        manual.unlink()


if __name__ == "__main__":
    unittest.main()
