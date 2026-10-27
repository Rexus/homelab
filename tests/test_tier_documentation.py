"""Project-owned documentation and upstream auto-docs refresh contracts."""

import contextlib
import hashlib
import io
import json
import re
import unittest
from unittest.mock import patch

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from project_docs import owned_template
from generate import REPOSITORIES
from generated_files import MARKER, RepositoryWriter

PROJECT_DOCS = (
    "docs/README.md", "docs/naming-conventions.md",
)


class RepositoryDocumentation(TierRepositoryTestCase):
    def test_generated_storage_design_distinguishes_capability_api_and_hosting(self):
        self.generate()
        docs = self.root / "verify-architecture/docs/auto-docs"
        design = (docs / "architecture/compute/runtime.md").read_text(encoding="utf-8")
        for term in ("**Object storage**", "**S3-compatible API**", "Ceph RBD", "CephFS",
                     "Ceph Object Gateway (RGW)", "**outbound\nbackups to**",
                     "independent backup custody"):
            self.assertIn(term, design)
        self.assertIn("does not establish that RGW is deployed", design)
        self.assertIn("Live database data stays on qualified Proxmox/Ceph-backed block storage", design)
        foundation = (docs / "deployment/foundation/README.md").read_text(encoding="utf-8")
        self.assertIn("runtime.md#storage-interfaces", foundation)
        guide = (docs / "deployment/foundation/storage/README.md").read_text(encoding="utf-8")
        self.assertIn("## Use NAS file storage", guide)
        self.assertIn("## Qualify an object endpoint", guide)
        self.assertIn("does not deploy a storage gateway", guide)
        backups = (docs / "administration/compute/backup-restore.md").read_text()
        self.assertIn("### NAS file target", backups)
        self.assertIn("Datacenter -> Storage -> Add -> NFS", backups)
        self.assertIn("neither requires an object-storage API", backups)
        database_backups = (docs / "administration/backups/postgresql.md").read_text()
        inputs = yaml.safe_load((UPSTREAM / "tier-0/ansible/group_vars/control_applications.yml.example").read_text())
        defaults = yaml.safe_load((UPSTREAM / "tier-0/ansible/roles/control_applications/defaults/main.yml").read_text())
        self.assertIn(inputs["control_applications_backup_files"]["keycloak"]["claim"], database_backups)
        self.assertIn(f'keycloak-db / PostgreSQL x{defaults["control_applications_database_instances"]}', database_backups)
        self.assertIn("keycloak-db-files-first-&lt;revision&gt;", database_backups)
        tier0 = self.root / "verify-tier-0"
        self.assertNotIn("object-storage", (tier0 / ".deployment-setups").read_text())
        for path in ("terraform/deployments/object-storage", "ansible/roles/object_storage",
                     "ansible/playbooks/deployment/object-storage.yml",
                     "ansible/group_vars/object_storage.yml.example"):
            self.assertFalse((tier0 / path).exists(), path)
        data = (docs / "deployment/stage-9-development/procedures/data-services.md").read_text()
        self.assertIn("Existing Ceph endpoints can also use `preprovisioned`", data)

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
            if name != "architecture":
                for relative in ("docs/architecture/README.md", "docs/README.md",
                                 "docs/deployment/README.md", "docs/development/README.md",
                                 "docs/administration/README.md"):
                    self.assertIn(relative, manifest["owned"])
                    self.assertNotIn(relative, manifest["files"])
                    self.assertNotIn("${", (repo / relative).read_text())
                guides = (repo / "docs/README.md").read_text()
                for intent in ("Deployment", "Development", "Administration"):
                    self.assertIn(f"| {intent} |", guides)
        manifest = json.loads((architecture / ".generated-files.json").read_text())
        for relative in PROJECT_DOCS:
            self.assertTrue((architecture / relative).is_file(), relative)
            self.assertIn(relative, manifest["owned"])
            self.assertNotIn(relative, manifest["files"])
        for heading in ("VM and DNS names", "Role abbreviations", "Proxmox tags", "VMID ranges", "Networks and VLANs"):
            self.assertIn(f"## {heading}", naming.read_text())
        self.assertFalse((architecture / "docs/generated").exists())

    def test_architecture_starter_is_a_single_platform_record_and_standards(self):
        self.generate()
        repo = self.root / "verify-architecture"
        local_docs = sorted(path.relative_to(repo).as_posix() for path in (repo / "docs").rglob("*.md")
                            if not path.is_relative_to(repo / "docs/auto-docs"))
        self.assertEqual(local_docs, sorted(PROJECT_DOCS))
        self.assertFalse((repo / "site").exists())
        record = (repo / "docs/README.md").read_text()
        self.assertIn("## Selected design", record)
        self.assertIn("## Deployment checklist", record)
        self.assertIn("| Deployed | Verified |", record)
        self.assertIn("&#9744;", record)
        self.assertIn("generation proves no operational result", record)
        self.assertIn("auto-docs/architecture/README.md", record)
        for name in REPOSITORIES:
            self.assertTrue((self.root / f"verify-{name}/README.md").exists())

    def test_compact_refresh_preserves_old_scaffolding_and_recorded_deletions(self):
        self.generate("--repo", "architecture")
        repo = self.root / "verify-architecture"
        writer = RepositoryWriter(repo)
        writer.write("docs/architecture/identity/README.md", "# Local identity decisions\n", owned=True)
        writer.write("docs/administration/recovery.md", "# Local restore evidence\n", owned=True)
        writer.finish()
        (repo / "docs/administration/recovery.md").unlink()
        before = (repo / "docs/README.md").read_bytes()
        result = self.generate("--repo", "architecture", "--refresh")
        self.assertIn("Existing project documents preserved", result.stdout)
        self.assertEqual((repo / "docs/README.md").read_bytes(), before)
        self.assertEqual((repo / "docs/architecture/identity/README.md").read_text(), "# Local identity decisions\n")
        self.assertFalse((repo / "docs/administration/recovery.md").exists())
        self.assertFalse((repo / "docs/architecture/compute").exists())
        self.assertFalse((repo / "docs/deployment").exists())

    def test_tier_zero_frontdoor_starts_with_local_template_publication(self):
        self.generate()
        tier0 = (self.root / "verify-tier-0/README.md").read_text(encoding="utf-8")
        publisher = "bash scripts/proxmox-templates.sh init"
        setup = "bash ../verify-shared/scripts/init-local-files.sh"
        self.assertIn("Templates before VMs", tier0)
        self.assertIn("capability deployment checklist", tier0)
        self.assertIn("deployment/foundation/README.md", tier0)
        self.assertIn("deployment/stage-2-logging/README.md", tier0)
        self.assertIn("deployment/stage-3-trust/README.md", tier0)
        self.assertIn("FreeIPA runs on two dedicated VMs", tier0)
        self.assertIn("Keycloak is a later service in this cluster", tier0)
        self.assertIn("deployment/stage-4-kubernetes/procedures/talos-terraform.md", tier0)
        self.assertIn("deployment/stage-4-kubernetes/README.md", tier0)
        self.assertIn("Kubernetes control cluster", tier0)
        self.assertIn("current [Talos implementation]", tier0)
        self.assertLess(tier0.index(publisher), tier0.index("bash scripts/kubernetes-cluster.sh init"))
        self.assertLess(tier0.index("bash scripts/kubernetes-cluster.sh init"), tier0.index(setup))
        self.assertLess(tier0.index(publisher), tier0.index(setup))
        self.assertIn("template-lifecycle.md#local-workflow", tier0)
        self.assertNotIn("${", tier0)
        for tier in ("tier-1", "tier-2"):
            readme = (self.root / f"verify-{tier}/README.md").read_text(encoding="utf-8")
            self.assertNotIn(publisher, readme)
            self.assertIn("operator-run workflows", readme)
            self.assertIn("compute/provisioning.md", readme)
            self.assertNotIn("${", readme)

    def test_naming_worksheet_keeps_conventions_separate_from_inventory(self):
        self.generate("--repo", "architecture")
        architecture = self.root / "verify-architecture"
        naming = architecture / "docs/naming-conventions.md"
        content = naming.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("# verify Naming Conventions"))
        self.assertNotIn("${", content)
        self.assertIn("| Type | Standard | Comments |", content)
        self.assertIn("editable reference placeholders", content)
        self.assertNotIn("TBD", content)
        self.assertNotIn("Production / test name", content)
        self.assertNotIn("| FQDN |", content)
        self.assertIn("| Abbreviation | Full name | Comments |", content)
        self.assertIn("[role abbreviations](#role-abbreviations)", content)
        self.assertIn("| External domain | `example.com` |", content)
        self.assertIn("<role>.<env>.<internal-domain>", content)
        self.assertIn("<role>.<env>.<external-domain>", content)
        self.assertIn("require separate configuration", content)
        rows = content.splitlines()
        headers = [rows[index - 1] for index, row in enumerate(rows) if row.startswith("| ---")]
        for header in headers:
            self.assertNotRegex(header.lower(), r"example|choice|our")
            self.assertTrue(header.endswith("| Comments |"), header)
        self.assertIn("<env>-<role>-<n>", content)
        for example in ("idp.prod.corp.example.com", "critical", "restricted", "100-199", "9000-9999",
                        "10 / Control", "120 / Services", "320 / DMZ"):
            self.assertIn(example, content)
        self.assertIn("Tier = owning repo and potential impact", content)
        self.assertIn("Zone = network protection", content)
        self.assertNotRegex(content, r"T[012]-(?:Edge|Application|Control)")
        for column in ("Tier / layer", "CIDR", "Gateway"):
            self.assertNotIn(column, content)
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            relative = target.split("#")[0]
            self.assertTrue((naming.parent / relative if relative else naming).is_file(), target)

    def test_documentation_uses_formal_project_language(self):
        self.generate()
        documents = [UPSTREAM / "README.md", *(UPSTREAM / "docs").rglob("*.md"),
                     *(UPSTREAM / "scripts/tier-repos/templates").rglob("*.md"),
                     *self.root.rglob("*.md")]
        for document in documents:
            content = document.read_text(encoding="utf-8")
            # Link destinations and executable examples are not prose.
            prose = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
            prose = re.sub(r"\]\([^)]+\)", "]", prose)
            prose = re.sub(r'<a id="[^"]+"></a>', "", prose)
            self.assertNotRegex(prose.lower(), r"\b(you|your|yours|yourself|our|ours|we)\b", str(document))

    def test_repo_checklists_and_shared_cluster_procedure_are_reachable(self):
        self.generate()
        architecture = self.root / "verify-architecture/docs/auto-docs"
        for tier in ("tier-0", "tier-1", "tier-2", "shared"):
            readme = (self.root / f"verify-{tier}/README.md").read_text()
            self.assertIn(f"/paths/{tier}/README.md", readme)
            self.assertTrue((architecture / f"paths/{tier}/README.md").is_file())
        for tier in ("tier-0", "tier-1"):
            path = (architecture / f"paths/{tier}/README.md").read_text()
            self.assertIn("../../deployment/stage-4-kubernetes/procedures/kubernetes.md", path)
        tier0 = (architecture / "paths/tier-0/README.md").read_text()
        self.assertLess(tier0.index("cluster-ha.md"), tier0.index("template-lifecycle.md"))
        self.assertLess(tier0.index("step-1c-sdn.md"), tier0.index("template-lifecycle.md"))
        quickstart = tier0.split("## Getting started", 1)[1].split("## Navigation", 1)[0]
        self.assertLess(quickstart.index("template-lifecycle.md"), quickstart.index("kubernetes-cluster.sh init"))
        self.assertIn("operator-run bootstrap", (architecture / "deployment/stage-4-kubernetes/step-1b-manual-cluster.md").read_text())
        for step in range(1, 11):
            self.assertIn(f"**{step}:", tier0)
        bootstrap = (architecture / "deployment/README.md").read_text()
        self.assertIn("foundation/README.md", bootstrap)
        self.assertIn("stage-2-logging/README.md", bootstrap)
        self.assertIn("Terraform / OpenTofu", bootstrap)
        self.assertIn("Current wrappers call `terraform`", bootstrap)
        foundation = (architecture / "deployment/stage-4-kubernetes/procedures/kubernetes.md").read_text()
        for component in ("CNI", "Flux", "SOPS", "Storage", "cert-manager", "ingress", "CloudNativePG"):
            self.assertIn(component, foundation)
        self.assertIn("Immutable AlmaLinux or another node OS", foundation)
        self.assertIn("not a multi-OS installer", foundation)
        application = (architecture / "deployment/stage-7-delivery/procedures/platform-cluster.md").read_text()
        self.assertIn("kubernetes.md#cluster-foundation", application)
        self.assertNotIn("| 1. Networking |", application)

    def test_ten_capabilities_have_numbered_main_paths_and_adjacent_options(self):
        self.generate("--repo", "architecture")
        docs = self.root / "verify-architecture/docs/auto-docs"
        stages = sorted((docs / "deployment").glob("stage-*/README.md"),
                        key=lambda path: int(path.parent.name.split("-")[1]))
        self.assertEqual(len(stages), 10)
        index = (docs / "deployment/README.md").read_text()
        project = (self.root / "verify-architecture/docs/README.md").read_text()
        for number, stage in enumerate(stages, 1):
            content = stage.read_text(encoding="utf-8")
            self.assertTrue(content.startswith(f"# Stage {number}: "), stage)
            self.assertIn(f"{stage.parent.name}/README.md", index)
            self.assertIn(f"{stage.parent.name}/README.md", project)
            steps = re.findall(r"(?m)^## Step (\d+): ", content)
            self.assertGreaterEqual(len(steps), 2)
            self.assertEqual(steps, [str(n) for n in range(1, len(steps) + 1)])
            for expected in ("## Main path", "```mermaid", "**Result:**",
                             "## Capability available", "architecture/", "**Prerequisites:**"):
                self.assertIn(expected, content, stage)
            for option in stage.parent.glob("step-*.md"):
                text = option.read_text(encoding="utf-8")
                step, variant = re.match(r"step-(\d+)([a-z])-", option.name).groups()
                self.assertIn(step, steps, option)
                self.assertTrue(text.startswith(f"# Step {step}{variant}:"), option)
                self.assertRegex(text, rf"\*\*Branch from:\*\* \[Step {step}\]\(README\.md#step-{step}-")
                self.assertIn("**Change:**", text, option)
                self.assertIn("Return", text, option)
                self.assertIn(f"({option.name})", content, option)
        intake, logging, trust, cluster, identity, control, delivery, observability, development, workloads = (
            stage.read_text(encoding="utf-8") for stage in stages
        )
        foundation = (docs / "deployment/foundation/README.md").read_text()
        self.assertIn("not itself a reachable Flux source", " ".join(foundation.split()))
        self.assertIn("## Step 1: Provision the log host", logging)
        self.assertIn("Hardware protection", trust)
        self.assertIn("FreeIPA stays outside Kubernetes", identity)
        self.assertIn("kubernetes.md#cluster-foundation", cluster)
        self.assertIn("## Step 1: Deploy the policy proxy and cache", intake)
        self.assertIn("## Step 3: Verify operation and recovery", cluster)
        self.assertIn("control-applications.yml", control)
        self.assertIn("control_applications.yml.example", control)
        self.assertIn("Stage 9", delivery)
        self.assertIn("Direct CI explicitly trusts", development)
        self.assertIn("not a shipped controller", workloads)
        self.assertIn("# Stage 8: Observability", observability)
        self.assertIn("step-1b-dedicated-vms.md", observability)
        self.assertNotIn("step-2d-telemetry-vm.md", control)
        hardware = (stages[2].parent / "step-1b-usb-hsm.md").read_text()
        self.assertIn("OS baseline", hardware)
        self.assertIn("not a native HSM cluster", hardware)
        self.assertEqual(hardware.count("```mermaid"), 1)
        self.assertIn("step-1b-usb-hsm.md", project)
        self.assertIn("direct-CI trust, Vault and original-state handover", project)
        design = (docs / "architecture/reference-platform.md").read_text()
        self.assertIn("not a claim that every service is automated", design)
        self.assertIn("no network route", design)
        self.assertIn("independent recovery/unseal material", design)

    def test_source_and_generated_documentation_links_resolve(self):
        self.generate()
        source_docs = [UPSTREAM / "README.md", *(UPSTREAM / "docs").rglob("*.md")]
        generated_docs = list(self.root.rglob("*.md"))
        for document in [*source_docs, *generated_docs]:
            content = document.read_text(encoding="utf-8")
            for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
                if re.match(r"[a-z]+:", link):
                    continue
                relative, _, anchor = link.partition("#")
                target = (document.parent / relative).resolve() if relative else document
                self.assertTrue(target.exists(), f"{document}: {link}")
                if anchor and target.suffix == ".md":
                    target_content = target.read_text(encoding="utf-8")
                    headings = re.findall(r"^#{1,6} (.+)$", target_content, re.MULTILINE)
                    anchors = [re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
                               for heading in headings]
                    anchors.extend(re.findall(r'<a id="([^"]+)"></a>', target_content))
                    self.assertIn(anchor, anchors, f"{document}: {link}")

    def test_refresh_keeps_legacy_section_links_in_owned_readmes_valid(self):
        self.generate()
        readme = self.root / "verify-tier-0/README.md"
        documents = {
            "paths/README.md": "choose-your-repository",
            "deployment/stage-5-identity/procedures/freeipa.md": "what-you-configure",
            "deployment/README.md": "day-2-service-sequence",
        }
        content = "# Project deployment guide\n" + "\n".join(
            f"[Guide](../verify-architecture/docs/auto-docs/{path}#{anchor})"
            for path, anchor in documents.items()
        )
        readme.write_text(content)
        self.generate("--refresh")
        self.assertEqual(readme.read_text(), content)
        for path, anchor in documents.items():
            target = self.root / "verify-architecture/docs/auto-docs" / path
            self.assertIn(f'<a id="{anchor}"></a>', target.read_text())

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
        targets += [(self.root / f"verify-{name}", relative)
                    for name in REPOSITORIES if name != "architecture"
                    for relative in ("docs/architecture/README.md", "docs/README.md")]
        targets += [(architecture, relative) for relative in PROJECT_DOCS]
        templates = self.root / "test-templates"
        templates.mkdir()
        (templates / "changed.md").write_text("# New upstream starter\n")
        with patch("project_docs.TEMPLATES", templates), contextlib.redirect_stdout(io.StringIO()):
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
        edited += [self.root / f"verify-{name}" / relative
                   for name in REPOSITORIES if name != "architecture"
                   for relative in ("docs/architecture/README.md", "docs/README.md")]
        edited += [architecture / relative for relative in PROJECT_DOCS]
        edited += [architecture / "docs/auto-docs/architecture/README.md"]
        deleted = [edited.pop(0), edited.pop(0), architecture / "docs/naming-conventions.md",
                   self.root / "verify-tier-2/docs/architecture/README.md",
                   architecture / "docs/auto-docs/administration/secret-handling/strategy.md"]
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
