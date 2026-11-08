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
        expected = {p.relative_to(repo): p.read_bytes() for p in (script, readme, deleted)}
        script.write_text("# Local automation changes\n")
        readme.write_text("# Project-owned README\n")
        deleted.unlink()
        retired = self.retired(repo, "terraform/retired.tf")
        retired_owned = self.retired(repo, "docs/retired-selection.md", owned=True)
        private = repo / ".env.local"
        private.write_text("LOCAL_PRIVATE_SENTINEL=retained\n")
        custom = repo / "docs/local-runbook.md"
        custom.write_text("# Independently authored runbook\n")
        state = repo / ".terraform/state/foundation/prod/terraform.tfstate"
        state.parent.mkdir(parents=True)
        state.write_text('{"serial": 7}\n')

        result = self.generate("--refresh", "--color", "always")
        review = result.stdout.split("\nRefresh review\n")[1]
        self.assertIn("YELLOW: 3 preserved differences; RED: 2 retired files", review)
        for relative, data in expected.items():
            candidate = self.root / ".refresh-review" / repo.name / relative
            self.assertEqual(candidate.read_bytes(), data)
            self.assertIn(f"\033[33mYELLOW {repo / relative}", review)
            self.assertIn(f"Rendered template: {candidate}", review)
        self.assertIn("../verify-shared", (self.root / ".refresh-review" / repo.name /
                                           "scripts/check-shared.sh").read_text())
        self.assertIn(f"Source template: {UPSTREAM / 'scripts/tier-repos/templates/readmes/tier.md'}", review)
        for path in (retired, retired_owned):
            self.assertIn(f"\033[31mRED {path}", review)
            self.assertTrue(path.exists())
        for path in (private, custom, state):
            self.assertNotIn(str(path), review)
        self.assertEqual(script.read_text(), "# Local automation changes\n")
        self.assertEqual(readme.read_text(), "# Project-owned README\n")
        self.assertFalse(deleted.exists())
        self.assertIn('"serial": 7', state.read_text())

    def test_dry_run_points_to_sources_without_writing_anything(self):
        self.generate()
        repo = self.root / "verify-tier-0"
        changed = repo / "scripts/check-shared.sh"
        changed.write_text("# Local changes\n")
        retired = self.retired(repo, "retired.txt")
        before = self.snapshot()
        result = self.generate("--refresh", "--dry-run", "--color", "never")
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
        result = self.generate("--repo", "shared", "--refresh")
        review = result.stdout.split("\nRefresh review\n")[1]
        self.assertIn(f"YELLOW {shared_file}", review)
        self.assertNotIn(str(tier_file), review)
        self.assertNotIn("\033[", review)  # Captured/non-TTY output is plain in auto mode.
        self.assertFalse((self.root / ".refresh-review/verify-tier-0").exists())

    def test_legacy_redirects_are_reviewable_but_project_license_is_not_retired(self):
        self.generate()
        repo = self.root / "verify-architecture"
        old = self.retired(repo, "docs/auto-docs/administration/compute/backup-restore.md")
        license_path = repo / "LICENSE"
        license_path.write_text("Project-selected licensing\n")
        self.generate("--refresh")
        result = self.generate("--refresh")
        review = result.stdout.split("\nRefresh review\n")[1]
        self.assertIn(f"RED {old}", review)
        self.assertIn("legacy documentation redirect", review)
        self.assertIn("Relocated reference", old.read_text())
        self.assertNotIn(str(license_path), review)
        old.unlink()
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
