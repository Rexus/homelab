"""Project licensing stays independent of the copied upstream notices."""

import hashlib
import json

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from generate import REPOSITORIES


class RepositoryLicensing(TierRepositoryTestCase):
    def test_fresh_repositories_have_scoped_notices_not_project_licenses(self):
        self.generate()
        upstream_license = (UPSTREAM / "LICENSE").read_text(encoding="utf-8")
        for name in REPOSITORIES:
            repo = self.root / f"verify-{name}"
            self.assertFalse((repo / "LICENSE").exists(), name)
            notice = (repo / "UPSTREAM-NOTICE").read_text(encoding="utf-8")
            self.assertIn(upstream_license, notice)
            self.assertIn("does not select a project-wide license", notice)
            self.assertIn("UPSTREAM-NOTICE", (repo / "README.md").read_text())
            manifest = json.loads((repo / ".generated-files.json").read_text())
            self.assertNotIn("LICENSE", manifest["files"])
            self.assertNotIn("LICENSE", manifest["owned"])
            self.assertIn("UPSTREAM-NOTICE", manifest["files"])
        auto_license = self.root / "verify-architecture/docs/auto-docs/LICENSE"
        self.assertEqual(auto_license.read_text(), upstream_license)

    def test_old_and_custom_project_licenses_are_never_changed_or_recreated(self):
        self.generate()
        expected = {}
        for index, name in enumerate(REPOSITORIES):
            repo = self.root / f"verify-{name}"
            license_file = repo / "LICENSE"
            original = (UPSTREAM / "LICENSE").read_bytes()
            manifest_path = repo / ".generated-files.json"
            manifest = json.loads(manifest_path.read_text())
            if index < 3:
                manifest["files"]["LICENSE"] = hashlib.sha256(original).hexdigest()
            if index == 0:
                license_file.write_bytes(original)
            elif index in (1, 3):
                license_file.write_bytes(b"Project-selected licensing terms\n")
            expected[license_file] = license_file.read_bytes() if license_file.exists() else None
            manifest_path.write_text(json.dumps(manifest))

        snapshot = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        result = self.generate("--refresh", "--dry-run")
        self.assertIn("Project licensing is no longer managed", result.stdout)
        self.assertEqual(snapshot, {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()})
        for _ in range(2):
            self.generate("--refresh")
            for license_file, content in expected.items():
                actual = license_file.read_bytes() if license_file.exists() else None
                self.assertEqual(actual, content, license_file)
                manifest = json.loads((license_file.parent / ".generated-files.json").read_text())
                self.assertNotIn("LICENSE", manifest["files"])
                if content is not None or license_file.parent.name == "verify-tier-1":
                    self.assertIn("LICENSE", manifest["owned"])

    def test_notices_refresh_with_edit_and_deletion_safeguards(self):
        self.generate()
        targets = [(self.root / "verify-shared", "UPSTREAM-NOTICE"),
                   (self.root / "verify-architecture", "docs/auto-docs/LICENSE")]
        expected = {}
        for repo, relative in targets:
            path = repo / relative
            expected[path] = path.read_bytes()
            path.write_bytes(b"Previous upstream notice\n")
            manifest_path = repo / ".generated-files.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["files"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest))
        self.generate("--refresh")
        for path, content in expected.items():
            self.assertEqual(path.read_bytes(), content)
            path.write_bytes(b"Locally reviewed attribution\n")
        self.generate("--refresh")
        for path in expected:
            self.assertEqual(path.read_bytes(), b"Locally reviewed attribution\n")
            path.unlink()
        self.generate("--refresh")
        for path in expected:
            self.assertFalse(path.exists())
