"""The physical documentation model and preservation of existing project records."""

import hashlib
import json
import shutil
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from documentation_migration import MOVES
from generated_files import MARKER


class DocumentationMigration(TierRepositoryTestCase):
    @unittest.skipUnless(shutil.which("git"), "Requires Git")
    def test_source_and_generated_docs_are_not_hidden_by_ignore_rules(self):
        self.generate()
        generated = self.root / "verify-architecture"
        subprocess.run(["git", "init", "--quiet", str(generated)], check=True, capture_output=True)
        for repo in (UPSTREAM, generated):
            paths = [path.relative_to(repo).as_posix() for path in (repo / "docs").rglob("*.md")]
            result = subprocess.run(["git", "check-ignore", "--no-index", "--stdin"],
                                    cwd=repo, input="\n".join(paths) + "\n", text=True,
                                    capture_output=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_fresh_trees_match_reader_intent_without_legacy_copies(self):
        self.generate()
        reference = self.root / "verify-architecture/docs/auto-docs"
        for old, new in MOVES.items():
            self.assertFalse((UPSTREAM / "docs" / old).is_file(), old)
            self.assertFalse((reference / old).exists(), old)
            self.assertTrue((reference / new).is_file(), new)
        for domain in ("networking", "compute", "identity", "cryptography", "delivery", "operations"):
            self.assertTrue((reference / "architecture" / domain / "README.md").is_file())
        for repo in self.root.iterdir():
            self.assertFalse((repo / "docs/owned").exists())
            self.assertFalse((repo / "docs/architecture.md").exists())
            manifest = json.loads((repo / ".generated-files.json").read_text())
            for area in ("architecture", "deployment", "development", "administration"):
                relative = f"docs/{area}/README.md"
                self.assertTrue((repo / relative).is_file())
                self.assertIn(relative, manifest["owned"])

    def test_refresh_redirects_unchanged_guides_and_preserves_edits_and_deletions(self):
        self.generate()
        repo = self.root / "verify-architecture"
        manifest_path = repo / ".generated-files.json"
        manifest = json.loads(manifest_path.read_text())
        examples = ["architecture/overview.md", "security/secret-strategy.md",
                    "platforms/proxmox/cluster-ha.md", "deployment/stages/foundation.md",
                    "architecture/system/capability-growth.md", "architecture/system-design/README.md",
                    "architecture/subsystem-design/compute/README.md",
                    "deployment/stage-0-foundation/README.md", "deployment/stage-1-trust/usb-hsm.md",
                    "deployment/stage-1-foundation/README.md",
                    "deployment/stage-1-foundation/procedures/syslog.md",
                    "deployment/stage-4-control-services/procedures/observability.md",
                    "deployment/stage-5-delivery/analytics.md",
                    "deployment/stage-4-control-services/step-2d-telemetry-vm.md",
                    "deployment/stage-6-workloads/README.md",
                    "deployment/stage-6-workloads/telemetry.md",
                    "deployment/stage-6-workloads/public-https.md",
                    "deployment/stage-3-identity-runtime/README.md",
                    "deployment/stage-3-identity-runtime/procedures/kubernetes.md",
                    "deployment/stage-4-control-services/README.md",
                    "deployment/stage-4-control-services/step-2b-vault-vm.md",
                    "deployment/stage-4-control-services/step-2c-seal-integration.md",
                    "architecture/cryptography/hardware-migration.md",
                    "deployment/foundation/step-3b-outbound-cache.md",
                    "deployment/software-intake/README.md",
                    "deployment/stage-1-logging/README.md",
                    "deployment/stage-3-identity/README.md",
                    "deployment/stage-3-identity/procedures/kubernetes.md",
                    "deployment/stage-3-identity/step-2b-manual-cluster.md",
                    "deployment/stage-9-workloads/README.md",
                    "deployment/stage-9-workloads/public-https.md",
                    "deployment/stage-9-workloads/telemetry.md",
                    "deployment/stage-10-workloads/README.md",
                    "deployment/stage-10-workloads/public-https.md",
                    "deployment/stage-10-workloads/telemetry.md",
                    "deployment/stage-10-workloads/isolated-clusters.md",
                    "deployment/stage-7-delivery/step-1b-source-control-vm.md",
                    "deployment/stage-7-delivery/step-1c-podman-runner.md",
                    "deployment/stage-7-delivery/step-1d-image-based-linux.md"]
        for old in examples:
            relative = f"docs/auto-docs/{old}"
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# Previous guide\n\n## Previous section\n\n<a id="stable-anchor"></a>\n')
            manifest["files"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        edited = repo / "docs/auto-docs" / examples[1]
        edited.write_text("# Locally adapted guide\n")
        deleted = repo / "docs/auto-docs" / examples[2]
        deleted.unlink()
        manifest_path.write_text(json.dumps(manifest))
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.generate("--refresh", "--dry-run")
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.generate("--refresh")
        pointer = repo / "docs/auto-docs" / examples[0]
        content = pointer.read_text()
        self.assertIn("AUTO-DOCS - DO NOT EDIT", content)
        self.assertIn('id="previous-section"', content)
        self.assertIn('id="stable-anchor"', content)
        self.assertIn("(README.md)", content)
        self.assertEqual(edited.read_text(), "# Locally adapted guide\n")
        self.assertFalse(deleted.exists())
        stage_pointer = repo / "docs/auto-docs" / examples[3]
        stage_content = stage_pointer.read_text()
        self.assertIn("(../README.md)", stage_content)
        self.assertIn('id="previous-section"', stage_content)
        progress_pointer = repo / "docs/auto-docs" / examples[4]
        self.assertIn("(../../deployment/readiness.md)", progress_pointer.read_text())
        self.assertIn("(../README.md)", (repo / "docs/auto-docs" / examples[5]).read_text())
        self.assertIn("(../../compute/README.md)", (repo / "docs/auto-docs" / examples[6]).read_text())
        for old, target in ((examples[7], "foundation/README.md"),
                            (examples[8], "stage-3-trust/step-1b-usb-hsm.md")):
            pointer_text = (repo / "docs/auto-docs" / old).read_text()
            self.assertIn(f"(../{target})", pointer_text)
            self.assertIn('id="stable-anchor"', pointer_text)
        for old in examples[9:]:
            pointer = repo / "docs/auto-docs" / old
            content = pointer.read_text()
            self.assertIn('id="stable-anchor"', content)
            self.assertIn("current guide", content)
            target = repo / "docs/auto-docs" / MOVES[old]
            self.assertTrue(target.is_file())
        self.generate("--refresh")
        self.assertEqual(pointer.read_text(), content)
        self.assertEqual(stage_pointer.read_text(), stage_content)

    def test_previous_design_split_is_preserved_and_linked_from_domain_records(self):
        repo = self.root / "verify-architecture"
        original = repo / "docs/architecture/README.md"
        original.parent.mkdir(parents=True)
        original.write_text("# Approved platform design\n\nLocal decisions and topology.\n")
        owned = ["docs/architecture/README.md", "docs/architecture/system-design/README.md",
                 "docs/architecture/subsystem-design/README.md"]
        for relative in owned[1:]:
            path = repo / relative
            path.parent.mkdir(parents=True)
            path.write_text(f"# Approved local design: {relative}\n")
        previous = {repo / relative: (repo / relative).read_bytes() for relative in owned}
        (repo / ".generated-files.json").write_text(json.dumps({
            "generator": MARKER, "files": {}, "owned": owned,
        }))
        expected = original.read_bytes()
        self.generate("--refresh")
        design = repo / "docs/architecture/compute/README.md"
        self.assertEqual(original.read_bytes(), expected)
        self.assertIn("[retained local document](../subsystem-design/README.md)", design.read_text())
        design.write_text("# Reviewed compute design\n")
        deleted = repo / "docs/architecture/networking/README.md"
        deleted.unlink()
        self.generate("--refresh")
        self.assertEqual(original.read_bytes(), expected)
        self.assertEqual(design.read_text(), "# Reviewed compute design\n")
        self.assertFalse(deleted.exists())
        for path, content in previous.items():
            self.assertEqual(path.read_bytes(), content)

    def test_old_project_records_are_retained_and_linked_not_migrated(self):
        examples = {
            "tier-0": ["docs/architecture.md", "docs/README.md", "README.md"],
            "architecture": ["docs/owned/design/overview.md", "docs/owned/runbooks/recovery.md", "README.md"],
        }
        originals = {}
        for repo_name, owned in examples.items():
            repo = self.root / f"verify-{repo_name}"
            for relative in owned:
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# Local project record: {relative}\n")
                originals[path] = path.read_bytes()
            (repo / ".generated-files.json").write_text(json.dumps({
                "generator": MARKER, "files": {}, "owned": owned,
            }))
        self.generate("--refresh")
        for path, data in originals.items():
            self.assertEqual(path.read_bytes(), data)
        for repo_name in examples:
            repo = self.root / f"verify-{repo_name}"
            design = (repo / "docs/architecture/README.md").read_text()
            self.assertIn("retained local document", design)
            for area in ("deployment", "development", "administration"):
                guide = repo / f"docs/{area}/README.md"
                guide.write_text("# Approved local workflow\n")
            deleted = repo / "docs/development/README.md"
            deleted.unlink()
        self.generate("--refresh")
        for repo_name in examples:
            repo = self.root / f"verify-{repo_name}"
            self.assertEqual((repo / "docs/deployment/README.md").read_text(), "# Approved local workflow\n")
            self.assertFalse((repo / "docs/development/README.md").exists())
