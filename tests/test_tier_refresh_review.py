"""Refresh ends with actionable comparisons while preserving private/project-owned files."""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from generated_files import RepositoryWriter
from refresh_review import print_refresh_review, use_color


class RefreshReviewTests(TierRepositoryTestCase):
    def retired(self, repo, relative, owned=False):
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Retained project history\n")
        manifest_path = repo / ".generated-files.json"
        manifest = json.loads(manifest_path.read_text())
        if owned:
            manifest["owned"].append(relative)
        else:
            manifest["files"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        return path

    def snapshot(self):
        return {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_clean_refresh_has_no_review_artifacts(self):
        self.generate()
        output = self.generate("--refresh", "--color", "never").stdout
        self.assertIn("YELLOW: 0 preserved differences; RED: 0 retired files", output)
        self.assertTrue(output.rstrip().endswith("No preserved differences or retired generated files to review."))
        self.assertFalse((self.root / ".refresh-review").exists())

    def test_preserved_differences_have_exact_rendered_candidates_and_retired_files_are_red(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        script = repo / "scripts/check-shared.sh"
        readme = repo / "README.md"
        deleted = repo / "ansible/group_vars/syslog.yml.example"
        expected = {script.relative_to(repo): script.read_bytes()}
        deleted_contents = deleted.read_bytes()
        script.write_text("# Local automation changes\n")
        readme.write_text("# Project-owned README\n")
        deleted.unlink()
        retired = self.retired(repo, "terraform/retired.tf")
        retired_owned = self.retired(repo, "docs/retired-selection.md", owned=True)
        retired_config = self.retired(repo, "ansible/retired.yml", owned=True)
        private = repo / ".env.local"
        private.write_text("LOCAL_PRIVATE_SENTINEL=retained\n")
        custom = repo / "docs/local-runbook.md"
        custom.write_text("# Independently authored runbook\n")
        state = repo / ".terraform/state/foundation/prod/terraform.tfstate"
        state.parent.mkdir(parents=True)
        state.write_text('{"serial": 7}\n')

        result = self.generate("--refresh", "--code-conflicts", "preserve", "--color", "always")
        review = result.stdout.split("\nRefresh review\n")[1]
        self.assertIn("YELLOW: 1 preserved differences; RED: 2 retired files", review)
        for relative, data in expected.items():
            candidate = self.root / ".refresh-review" / repo.name / relative
            self.assertEqual(candidate.read_bytes(), data)
            self.assertIn(f"\033[33mYELLOW {repo / relative}", review)
            self.assertIn(f"Rendered template: {candidate}", review)
        self.assertIn("../verify-shared", (self.root / ".refresh-review" / repo.name /
                                           "scripts/check-shared.sh").read_text())
        self.assertIn(f"Source template: {UPSTREAM / 'tier-0/scripts/check-shared.sh'}", review)
        for path in (retired, retired_config):
            self.assertIn(f"\033[31mRED {path}", review)
            self.assertTrue(path.exists())
        for path in (private, custom, state, readme, retired_owned):
            self.assertNotIn(str(path), review)
        self.assertTrue(retired_owned.exists())
        self.assertFalse((self.root / ".refresh-review" / repo.name / "README.md").exists())
        self.assertEqual(script.read_text(), "# Local automation changes\n")
        self.assertEqual(readme.read_text(), "# Project-owned README\n")
        self.assertEqual(deleted.read_bytes(), deleted_contents)
        self.assertNotIn(f"YELLOW {deleted}", review)
        self.assertIn('"serial": 7', state.read_text())

    def test_documentation_only_differences_are_quiet_but_configuration_remains_actionable(self):
        repo = self.root / "verify-tier-0"
        documents = ("README.md", "ansible/README", "terraform/readme.RST", "docs/guide.md", "docs/design.adoc")
        config = "ansible/runtime-requirements.txt"
        with contextlib.redirect_stdout(io.StringIO()):
            writer = RepositoryWriter(repo)
            for relative in (*documents, config):
                writer.write(relative, "original\n", owned=True)
            writer.finish()
            for relative in documents:
                (repo / relative).write_text("local project documentation\n")
            (repo / config).write_text("project requirements\n")
        progress = io.StringIO()
        with contextlib.redirect_stdout(progress):
            writer = RepositoryWriter(repo, refresh=True)
            for relative in (*documents, config):
                writer.write(relative, "current starter\n", owned=True)
            writer.finish()
        output = io.StringIO()
        print_refresh_review([writer.review], self.root, stream=output)
        self.assertIn("YELLOW: 1 preserved differences; RED: 0 retired files", output.getvalue())
        self.assertIn(f"YELLOW {repo / config}", output.getvalue())
        self.assertEqual((self.root / ".refresh-review" / repo.name / config).read_text(), "current starter\n")
        for relative in documents:
            self.assertEqual((repo / relative).read_text(), "local project documentation\n")
            self.assertNotIn(str(repo / relative), progress.getvalue() + output.getvalue())
            self.assertFalse((self.root / ".refresh-review" / repo.name / relative).exists())

    def test_dry_run_points_to_sources_without_writing_anything(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        changed = repo / "scripts/check-shared.sh"
        changed.write_text("# Local changes\n")
        retired = self.retired(repo, "retired.txt")
        before = self.snapshot()
        result = self.generate("--refresh", "--code-conflicts", "preserve", "--dry-run", "--color", "never")
        self.assertEqual(before, self.snapshot())
        review = result.stdout.split("\nRefresh review\n")[1]
        self.assertIn(f"Source template: {UPSTREAM / 'tier-0/scripts/check-shared.sh'}", review)
        self.assertNotIn("Rendered template:", review)
        self.assertIn(f"RED {retired}", review)
        self.assertNotIn("\033[", review)
        self.assertFalse((self.root / ".refresh-review").exists())

    def test_review_covers_only_selected_repositories(self):
        self.generate()
        shared = self.root / "verify-shared"
        shared_file = shared / "scripts/deploy.sh"
        shared_file.write_text("# Shared local edits\n")
        tier_file = self.retired(self.root / "verify-tier-0", "retired.tf")
        result = self.generate("--repo", "shared", "--refresh", "--code-conflicts", "preserve")
        review = result.stdout.split("\nRefresh review\n")[1]
        self.assertIn(f"YELLOW {shared_file}", review)
        self.assertNotIn(str(tier_file), review)
        self.assertNotIn("\033[", review)  # Captured/non-TTY output is plain in auto mode.
        self.assertFalse((self.root / ".refresh-review/verify-tier-0").exists())

    def test_retired_auto_docs_are_removed_but_project_license_is_untouched(self):
        self.generate()
        repo = self.root / "verify-architecture"
        old = self.retired(repo, "docs/auto-docs/administration/compute/backup-restore.md")
        license_path = repo / "LICENSE"
        license_path.write_text("Project-selected licensing\n")
        result = self.generate("--refresh")
        review = result.stdout.split("\nRefresh review\n")[1]
        self.assertIn(f"REMOVED {old}", review)
        self.assertIn("current guide: docs/auto-docs/administration/backups/virtual-machines.md", review)
        self.assertFalse(old.exists())
        self.assertFalse(old.parent.exists())
        self.assertNotIn(str(license_path), review)
        self.assertEqual(license_path.read_text(), "Project-selected licensing\n")
        result = self.generate("--refresh")
        self.assertNotIn(str(old), result.stdout.split("\nRefresh review\n")[1])

    def test_color_controls_keep_labels_and_honor_noninteractive_settings(self):
        class Terminal(io.StringIO):
            def isatty(self):
                return True

        with patch.dict(os.environ, {"TERM": "xterm"}, clear=True):
            self.assertTrue(use_color("auto", Terminal()))
            self.assertFalse(use_color("auto", io.StringIO()))
            self.assertFalse(use_color("never", Terminal()))
        with patch.dict(os.environ, {"TERM": "xterm", "NO_COLOR": "1"}, clear=True):
            self.assertFalse(use_color("auto", Terminal()))
            self.assertTrue(use_color("always", io.StringIO()))
        with patch.dict(os.environ, {"TERM": "dumb"}, clear=True):
            self.assertFalse(use_color("auto", Terminal()))

    @unittest.skipIf(os.name == "nt", "Requires unprivileged symlinks")
    def test_candidate_symlink_cannot_overwrite_an_external_file(self):
        repo = self.root / "verify-tier-0"
        with contextlib.redirect_stdout(io.StringIO()):
            writer = RepositoryWriter(repo)
            writer.write("managed.txt", "# Original\n")
            writer.finish()
            (repo / "managed.txt").write_text("# Local edits\n")
            writer = RepositoryWriter(repo, refresh=True)
            writer.write("managed.txt", "# Current template\n")
            writer.finish()
        external = Path(self.temp.name) / "external"
        external.mkdir()
        sentinel = external / "managed.txt"
        sentinel.write_text("# External content\n")
        (self.root / ".refresh-review").symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            print_refresh_review([writer.review], self.root, stream=io.StringIO())
        self.assertEqual(sentinel.read_text(), "# External content\n")


if __name__ == "__main__":
    unittest.main()
