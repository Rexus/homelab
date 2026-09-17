"""Project-owned documentation and upstream auto-docs refresh contracts."""

import contextlib
import hashlib
import io
import json
import re
import unittest
from unittest.mock import patch

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from documentation import owned_template
from generate import REPOSITORIES
from generated_files import MARKER, RepositoryWriter

PROJECT_DOCS = (
    "docs/README.md", "docs/naming-conventions.md", "docs/owned/design/overview.md",
    "docs/owned/runbooks/recovery.md",
)


class RepositoryDocumentation(TierRepositoryTestCase):
    def test_frontdoors_and_project_templates_are_owned(self):
        self.generate()
        architecture = self.root / "verify-architecture"
        naming = architecture / "docs/naming-conventions.md"
        for name in REPOSITORIES:
            repo = self.root / f"verify-{name}"
            readme = repo / "README.md"
            content = readme.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("# verify "), name)
            self.assertIn("## Getting started", content)
            self.assertNotIn(MARKER, content)
            self.assertNotIn("${", content)
            links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", content)
            self.assertIn(naming, [(repo / target).resolve() for target in links])
            manifest = json.loads((repo / ".generated-files.json").read_text())
            self.assertIn("README.md", manifest["owned"])
            self.assertNotIn("README.md", manifest["files"])
        manifest = json.loads((architecture / ".generated-files.json").read_text())
        for relative in PROJECT_DOCS:
            self.assertTrue((architecture / relative).is_file(), relative)
            self.assertIn(relative, manifest["owned"])
            self.assertNotIn(relative, manifest["files"])
        for heading in ("VM and DNS names", "Resource IDs", "Networks", "Platform resources"):
            self.assertIn(f"## {heading}", naming.read_text())
        self.assertFalse((architecture / "docs/generated").exists())

    def test_auto_docs_have_notice_and_project_link_at_every_depth(self):
        self.generate("--repo", "architecture")
        architecture = self.root / "verify-architecture"
        manifest = json.loads((architecture / ".generated-files.json").read_text())
        for source in (UPSTREAM / "docs").rglob("*.md"):
            relative = "docs/auto-docs/" + source.relative_to(UPSTREAM / "docs").as_posix()
            document = architecture / relative
            content = document.read_text(encoding="utf-8")
            self.assertEqual(content.splitlines()[0], source.read_text(encoding="utf-8").splitlines()[0])
            self.assertIn("> **AUTO-DOCS - DO NOT EDIT**", content.split("## Table of contents")[0])
            self.assertIn("bash scripts/init-tier-repos.sh --refresh", content)
            link = re.search(r"\[project documentation\]\(([^)]+)\)", content)[1]
            self.assertEqual((document.parent / link).resolve(), architecture / "docs/README.md")
            self.assertIn(relative, manifest["files"])
            self.assertNotIn(relative, manifest["owned"])

    def test_template_updates_do_not_replace_existing_project_files(self):
        self.generate()
        architecture = self.root / "verify-architecture"
        targets = [(self.root / f"verify-{name}", "README.md") for name in REPOSITORIES]
        targets += [(architecture, relative) for relative in PROJECT_DOCS]
        templates = self.root / "test-templates"
        templates.mkdir()
        (templates / "changed.md").write_text("# New upstream starter\n")
        with patch("documentation.TEMPLATES", templates), contextlib.redirect_stdout(io.StringIO()):
            for repo, relative in targets:
                expected = (repo / relative).read_bytes()
                writer = RepositoryWriter(repo, refresh=True)
                owned_template(writer, "changed.md", relative)
                writer.finish()
                self.assertEqual((repo / relative).read_bytes(), expected)

    def test_refresh_preserves_local_project_and_auto_doc_edits_and_deletions(self):
        self.generate()
        architecture = self.root / "verify-architecture"
        edited = [self.root / f"verify-{name}/README.md" for name in REPOSITORIES]
        edited += [architecture / relative for relative in PROJECT_DOCS]
        edited += [architecture / "docs/auto-docs/architecture/overview.md"]
        deleted = [edited.pop(0), edited.pop(0), architecture / "docs/owned/runbooks/recovery.md",
                   architecture / "docs/auto-docs/security/secret-strategy.md"]
        for path in edited:
            path.write_text("# Project-owned changes\n", encoding="utf-8")
        for path in deleted:
            path.unlink()
        self.generate("--refresh")
        for path in edited:
            if path not in deleted:
                self.assertEqual(path.read_text(), "# Project-owned changes\n", path)
        for path in deleted:
            self.assertFalse(path.exists(), path)

    def test_legacy_upgrade_preserves_readmes_and_docs_without_dry_run_writes(self):
        originals = {}
        for name in REPOSITORIES:
            repo = self.root / f"verify-{name}"
            repo.mkdir(parents=True)
            readme = repo / "README.md"
            readme.write_text(f"# Previous {name} README\n", encoding="utf-8")
            originals[readme] = readme.read_bytes()
            manifest = {"generator": MARKER, "files": {
                "README.md": hashlib.sha256(originals[readme]).hexdigest()}, "owned": []}
            if name == "architecture":
                for filename, edited in (("README.md", False), ("local.md", True)):
                    relative = f"docs/generated/upstream/{filename}"
                    legacy = repo / relative
                    legacy.parent.mkdir(parents=True, exist_ok=True)
                    legacy.write_text("# Previous upstream guide\n")
                    manifest["files"][relative] = hashlib.sha256(legacy.read_bytes()).hexdigest()
                    if edited:
                        legacy.write_text("# Local edits to legacy guide\n")
                    originals[legacy] = legacy.read_bytes()
            manifest_path = repo / ".generated-files.json"
            manifest_path.write_text(json.dumps(manifest))
        snapshot = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        self.generate("--refresh", "--dry-run")
        self.assertEqual(snapshot, {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()})
        result = self.generate("--refresh")
        self.assertIn("Legacy docs preserved", result.stdout)
        for path, expected in originals.items():
            self.assertEqual(path.read_bytes(), expected, path)
        for name in REPOSITORIES:
            manifest = json.loads((self.root / f"verify-{name}/.generated-files.json").read_text())
            self.assertIn("README.md", manifest["owned"])
            self.assertNotIn("README.md", manifest["files"])
        self.assertTrue((self.root / "verify-architecture/docs/auto-docs/README.md").is_file())
        self.assertTrue((self.root / "verify-architecture/docs/naming-conventions.md").is_file())


if __name__ == "__main__":
    unittest.main()
