"""The physical documentation model and preservation of existing project records."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from documentation_migration import MOVES
from documentation import MOVED_SOFTWARE_ROUTES, compatibility_paths
from generated_files import MARKER
from test_tier_deployment_navigation import anchors, links


class DocumentationMigration(TierRepositoryTestCase):
    def test_retired_numbered_chapters_are_kept_only_for_owned_project_links(self):
        self.assert_project_alias(
            "01-architecture/17-kubernetes/README.md", "01-architecture/04-hosting/03-kubernetes.md",
            "architecture/17-kubernetes/README.md")

    def test_retired_operations_routes_preserve_owned_records_without_cluttering_fresh_trees(self):
        self.assert_project_alias(
            "05-operations/cache.md", "05-operations/02-software-intake/README.md",
            "administration/cache.md")

    def assert_project_alias(self, old, new, legacy):
        self.generate()
        repo = self.root / "verify-architecture"
        manual = repo / "docs/auto-docs"
        retired = manual / old
        current = manual / new
        self.assertFalse(retired.exists())
        self.assertTrue(current.is_file())
        self.assertTrue((manual / legacy).is_file())
        record = self.root / "verify-tier-0/docs/architecture/README.md"
        original = record.read_text() + ("\n[Existing guide]"
            f"(../../../verify-architecture/docs/auto-docs/{old}#site-section)\n")
        record.write_text(original)
        retired.parent.mkdir(parents=True, exist_ok=True)
        retired.write_text('# Previous cluster design\n\n## Site section\n')
        manifest_path = repo / ".generated-files.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][retired.relative_to(repo).as_posix()] = hashlib.sha256(retired.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        self.generate("--refresh", "--dry-run")
        self.assertIn("Previous cluster design", retired.read_text())
        self.generate("--refresh")
        self.assertEqual(record.read_text(), original)
        self.assertIn("Compatibility copy", retired.read_text())
        self.assertIn("site-section", anchors(retired.read_text()))
        self.assertIn(current.resolve(), [link.target for link in links(retired)])
        self.assertFalse((manual / "01-architecture/21-observability/README.md").exists())
        record.write_text('# Project design\n')
        self.generate("--refresh")
        self.assertFalse(retired.exists())
        self.assertTrue(current.is_file())

    def test_alias_targets_preserved_current_headings_after_refresh(self):
        self.generate()
        manual = self.root / "verify-architecture/docs/auto-docs"
        current = manual / "01-architecture/04-hosting/README.md"
        alias = manual / "architecture/hosting/README.md"
        current.write_text("# Local hosting design\n\n## Site-specific choices\n", encoding="utf-8")
        self.generate("--refresh")
        self.assertEqual(current.read_text(encoding="utf-8"),
                         "# Local hosting design\n\n## Site-specific choices\n")
        alias_links = list(links(alias))
        self.assertTrue(any(link.fragment == "site-specific-choices" for link in alias_links))
        for link in alias_links:
            if link.fragment:
                self.assertIn(link.fragment, anchors(current.read_text(encoding="utf-8")))

    @unittest.skipUnless(shutil.which("git"), "Requires Git")
    def test_secret_capability_docs_do_not_unignore_private_files(self):
        self.generate()
        generated = self.root / "verify-architecture"
        subprocess.run(["git", "init", "--quiet", str(generated)], check=True, capture_output=True)
        for repo, doc, private in (
            (UPSTREAM, "docs/01-architecture/08-cryptography/08-secrets.md", "docs/01-architecture/19-secrets/private.txt"),
            (UPSTREAM, "docs/05-operations/03-cryptography/README.md", "docs/05-operations/secrets/private.txt"),
            (generated, "docs/auto-docs/01-architecture/08-cryptography/08-secrets.md",
             "docs/auto-docs/01-architecture/19-secrets/private.txt"),
            (generated, "docs/auto-docs/05-operations/03-cryptography/README.md",
             "docs/auto-docs/05-operations/secrets/private.txt"),
        ):
            for path, ignored in ((doc, False), (private, True), ("secrets/private.txt", True)):
                result = subprocess.run(["git", "check-ignore", "--no-index", "--quiet", path],
                                        cwd=repo, capture_output=True)
                self.assertEqual(result.returncode, 0 if ignored else 1, f"{repo}: {path}")

    def test_moved_software_routes_preserve_anchors_and_project_records(self):
        self.generate()
        repo = self.root / "verify-architecture"
        manual = repo / "docs/auto-docs"
        record = repo / "docs/README.md"
        entries = []
        manifest_path = repo / ".generated-files.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for area in ("architecture", "01-architecture"):
            for route in MOVED_SOFTWARE_ROUTES:
                old = f"{area}/software/{route}"
                target = MOVES[old]
                alias = manual / old
                alias.parent.mkdir(parents=True, exist_ok=True)
                alias.write_text("# Previous guide\n\n## Site-specific old heading\n", encoding="utf-8")
                manifest["files"][alias.relative_to(repo).as_posix()] = hashlib.sha256(alias.read_bytes()).hexdigest()
                entries.append((alias, manual / target))
        original = "# Site choices\n\n" + "".join(
            f"[Previous guide](auto-docs/{alias.relative_to(manual).as_posix()}#site-specific-old-heading)\n"
            for alias, _ in entries
        )
        record.write_text(original, encoding="utf-8")
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.generate("--refresh", "--dry-run")
        self.assertEqual(record.read_text(encoding="utf-8"), original)
        self.generate("--refresh")
        self.assertEqual(record.read_text(encoding="utf-8"), original)
        for alias, target in entries:
            content = alias.read_text(encoding="utf-8")
            self.assertIn("site-specific-old-heading", anchors(content))
            self.assertTrue(set(anchors(target.read_text(encoding="utf-8"))) <= set(anchors(content)))
            self.assertIn(target.resolve(), [link.target for link in links(alias)])
        self.generate("--refresh")
        self.assertEqual(record.read_text(encoding="utf-8"), original)
        for link in links(record):
            self.assertIn(link.fragment, anchors(link.target.read_text(encoding="utf-8")))

    def test_refresh_preserves_owned_links_and_compatibility_anchors(self):
        self.generate()
        repo = self.root / "verify-architecture"
        manual = repo / "docs/auto-docs"
        record = repo / "docs/README.md"
        original = ("# Site choices\n\n"
                    "[Hosting](auto-docs/architecture/hosting/README.md)\n"
                    "[Foundation](auto-docs/deployment/foundation/README.md#step-4-publish-and-test-vm-templates)\n"
                    "[Previous deployment](auto-docs/02-deployment/foundation/README.md#old-section)\n"
                    "[Previous development](auto-docs/03-development/README.md#old-section)\n"
                    "[Previous administration](auto-docs/04-administration/README.md#old-section)\n"
                    "[Conventions](auto-docs/conventions/README.md)\n"
                    "[Paths](auto-docs/paths/README.md)\n"
                    "[Decisions](auto-docs/decisions/README.md)\n"
                    "[Reference](auto-docs/reference/README.md)\n")
        record.write_text(original, encoding="utf-8")
        old = manual / "deployment/foundation/README.md"
        old.write_text("# Old foundation\n\n## Step 4: Publish and test VM templates\n", encoding="utf-8")
        edited = manual / "architecture/hosting/README.md"
        edited.write_text("# Local edits\n\n<a id=\"site-section\"></a>\n", encoding="utf-8")
        manifest_path = repo / ".generated-files.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"][old.relative_to(repo).as_posix()] = hashlib.sha256(old.read_bytes()).hexdigest()
        for relative in ("02-deployment/foundation/README.md", "03-development/README.md",
                         "04-administration/README.md"):
            prior = manual / relative
            prior.write_text("# Previous guide\n\n## Old section\n", encoding="utf-8")
            manifest["files"][prior.relative_to(repo).as_posix()] = hashlib.sha256(prior.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.generate("--refresh", "--dry-run")
        self.assertEqual(record.read_text(encoding="utf-8"), original)
        self.assertIn("# Old foundation", old.read_text(encoding="utf-8"))
        self.generate("--refresh")
        self.assertEqual(record.read_text(encoding="utf-8"), original)
        self.assertEqual(edited.read_text(encoding="utf-8"), "# Local edits\n\n<a id=\"site-section\"></a>\n")
        for link in links(record):
            self.assertTrue(link.target.is_file(), str(link.target))
            if link.fragment:
                self.assertIn(link.fragment, anchors(link.target.read_text(encoding="utf-8")))
        for old, current in (("conventions/vmid-convention.svg", "02-conventions/vmid-convention.svg"),
                             ("reference/diagrams/palette.json", "08-reference/diagrams/palette.json")):
            self.assertEqual((manual / old).read_bytes(), (manual / current).read_bytes())
        for area, numbered in (("architecture", "01-architecture"), ("conventions", "02-conventions"),
                               ("deployment", "03-deployment"), ("02-deployment", "03-deployment"),
                               ("development", "04-development"), ("03-development", "04-development"),
                               ("administration", "05-operations"), ("04-administration", "05-operations"),
                               ("paths", "06-paths"), ("decisions", "07-decisions"),
                               ("reference", "08-reference")):
            for canonical in (manual / numbered).rglob("*.md"):
                if "> **Compatibility copy:**" in canonical.read_text(encoding="utf-8"):
                    continue
                alias = manual / area / canonical.relative_to(manual / numbered)
                if alias == edited:
                    continue
                self.assertTrue(alias.is_file(), str(alias))
                self.assertTrue(set(anchors(canonical.read_text(encoding="utf-8"))) <=
                                set(anchors(alias.read_text(encoding="utf-8"))), str(alias))
                self.assertIn(canonical.resolve(), [link.target for link in links(alias)])
        self.generate("--refresh")
        self.assertEqual(record.read_text(encoding="utf-8"), original)

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

    def test_fresh_trees_match_reader_intent_with_numbered_compatibility_copies(self):
        self.generate()
        reference = self.root / "verify-architecture/docs/auto-docs"
        for old, new in MOVES.items():
            self.assertFalse((UPSTREAM / "docs" / old).is_file(), old)
            alias = (Path(old) in compatibility_paths(Path("docs") / new)
                     and not old.startswith(("01-architecture/", "03-deployment/", "05-operations/")))
            self.assertEqual((reference / old).exists(), alias, old)
            self.assertTrue((reference / new).is_file(), new)
        for domain in ("05-networking", "04-hosting", "06-data", "09-identity", "08-cryptography",
                       "07-software-intake", "10-delivery", "11-operations"):
            self.assertTrue((reference / "01-architecture" / domain / "README.md").is_file())
        self.assertTrue((reference / "01-architecture/10-delivery/README.md").is_file())
        self.assertTrue((reference / "01-architecture/10-delivery/02-controllers.md").is_file())
        self.assertFalse((reference / "administration/compute").exists())
        for relative in ("01-hosting/proxmox-tls.md", "01-hosting/templates/template-lifecycle.md",
                         "06-resilience/backups/virtual-machines.md", "06-resilience/backups/recovery-set.md",
                         "01-hosting/terraform-state.md", "06-resilience/recovery/bootstrap.md",
                         "06-resilience/recovery/virtual-machines.md",
                         "06-resilience/recovery/host.md", "06-resilience/recovery/platform.md"):
            self.assertTrue((reference / "05-operations" / relative).is_file(), relative)
        for repo in self.root.iterdir():
            self.assertFalse((repo / "docs/owned").exists())
            self.assertFalse((repo / "docs/architecture.md").exists())
            manifest = json.loads((repo / ".generated-files.json").read_text())
            if repo.name == "verify-architecture":
                self.assertIn("docs/README.md", manifest["owned"])
                self.assertFalse((repo / "docs/architecture").exists())
                continue
            for area in ("architecture", "deployment", "development", "administration"):
                relative = f"docs/{area}/README.md"
                self.assertTrue((repo / relative).is_file())
                self.assertIn(relative, manifest["owned"])

    def test_refresh_removes_retired_auto_docs_and_reports_current_guide_paths(self):
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
                    "deployment/stage-1-logging/step-3b-redundant-intake.md",
                    "deployment/stage-1-logging/step-3c-nas-archive.md",
                    "deployment/stage-1-logging/step-3d-retention-lock.md",
                    "03-deployment/stage-2-logging/step-3b-redundant-intake.md",
                    "03-deployment/stage-2-logging/step-3c-nas-archive.md",
                    "03-deployment/stage-2-logging/step-3d-retention-lock.md",
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
                    "deployment/stage-7-delivery/step-1d-image-based-linux.md",
                    "deployment/foundation/procedures/proxmox.md",
                    "deployment/foundation/procedures/enterprise-linux-template.md",
                    "deployment/foundation/procedures/talos-template.md",
                    "deployment/foundation/procedures/vm-template.md",
                    "deployment/foundation/procedures/unifi-zones.md",
                    "deployment/foundation/procedures/object-storage.md",
                    "architecture/compute/README.md", "architecture/compute/runtime.md",
                    "architecture/hosting/vmid-convention.md", "reference/proxmox-conventions.md",
                    "reference/network-plan.md",
                    "administration/compute/backup-restore.md",
                    "administration/compute/proxmox-tls.md",
                    "administration/compute/template-lifecycle.md",
                    "administration/compute/reinstall.md",
                    "deployment/stage-1-software-intake/bootstrap-consumer.md",
                    "deployment/stage-1-software-intake/proxy-cache.md",
                    "deployment/stage-2-logging/receiver.md",
                    "deployment/stage-2-logging/sources.md",
                    "deployment/stage-2-logging/producer-trust.md",
                    "deployment/stage-6-secrets/monitoring.md",
                    "deployment/stage-8-observability/configuration.md",
                    "deployment/stage-8-observability/infrastructure-monitoring.md",
                    "deployment/stage-10-lab-environments/isolated-clusters.md"]
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
        result = self.generate("--refresh")
        self.assertFalse(deleted.exists())
        for old in examples:
            self.assertFalse((repo / "docs/auto-docs" / old).exists(), old)
            target = repo / "docs/auto-docs" / MOVES[old]
            self.assertTrue(target.is_file())
            if old != examples[2]:
                self.assertIn(f"current guide: docs/auto-docs/{MOVES[old]}", result.stdout)
        manifest = json.loads(manifest_path.read_text())
        for old in examples:
            self.assertNotIn(f"docs/auto-docs/{old}", manifest["files"])
        self.generate("--refresh")
        for old in examples:
            self.assertFalse((repo / "docs/auto-docs" / old).exists())

    def test_previous_design_split_is_preserved_without_seeding_more_domains(self):
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
        result = self.generate("--refresh")
        self.assertEqual(original.read_bytes(), expected)
        self.assertIn("Existing project documents preserved", result.stdout)
        self.assertIn("[retained local document](architecture/README.md)", (repo / "docs/README.md").read_text())
        self.assertFalse((repo / "docs/architecture/compute").exists())
        self.generate("--refresh")
        self.assertEqual(original.read_bytes(), expected)
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
            record = "docs/README.md" if repo_name == "architecture" else "docs/architecture/README.md"
            design = (repo / record).read_text()
            self.assertIn("retained local document", design)
            for area in ("deployment", "development", "administration"):
                guide = repo / f"docs/{area}/README.md"
                guide.parent.mkdir(parents=True, exist_ok=True)
                guide.write_text("# Approved local workflow\n")
            deleted = repo / "docs/development/README.md"
            deleted.unlink()
        self.generate("--refresh")
        for repo_name in examples:
            repo = self.root / f"verify-{repo_name}"
            self.assertEqual((repo / "docs/deployment/README.md").read_text(), "# Approved local workflow\n")
            self.assertEqual((repo / "docs/development/README.md").is_file(), repo_name == "tier-0")
