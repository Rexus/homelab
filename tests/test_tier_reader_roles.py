"""Design alternatives, staged realization and owned project records stay aligned."""

import re

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class ReaderRoles(TierRepositoryTestCase):
    def test_deployment_guides_name_working_repositories_in_source_and_generated_docs(self):
        self.generate()
        source = UPSTREAM / "docs/deployment"
        generated = self.root / "verify-architecture/docs/auto-docs/deployment"
        for root in (source, generated):
            index = (root / "README.md").read_text(encoding="utf-8")
            self.assertIn("## Repository locations", index)
            self.assertIn("Run repository scripts from the owning tier's root", index)
            for name in ("tier-0", "tier-1", "tier-2", "shared", "architecture"):
                self.assertIn(f"`<prefix>-{name}/`", index)
            for name in ("tier-0", "tier-1", "tier-2", "shared"):
                link = re.search(rf"\[{name}/\]\(([^)]+)\)", index)[1]
                expected = UPSTREAM / name if root == source else self.root / f"verify-{name}"
                self.assertEqual((root / link).resolve(), expected)
            for document in [*root.glob("stage-*/**/*.md"), *root.glob("foundation/**/*.md"),
                             *root.glob("stage-1-software-intake/**/*.md")]:
                opening = "\n".join(document.read_text(encoding="utf-8").splitlines()[:22])
                self.assertRegex(opening, r"\*\*Working repositor(?:y|ies):\*\*|## Working repositories", str(document))
                self.assertIn("<prefix>-tier-", opening, str(document))
            for relative, owner in (
                ("stage-1-software-intake/proxy-cache.md", "tier-2"),
                ("stage-3-trust/step-1b-usb-hsm.md", "tier-0"),
                ("stage-5-identity/procedures/freeipa.md", "tier-0"),
                ("stage-6-secrets/step-1b-vault-vm.md", "tier-0"),
                ("stage-8-observability/step-1b-dedicated-vms.md", "tier-1"),
                ("stage-9-development/step-1b-source-control-vm.md", "tier-1"),
                ("stage-9-development/step-2b-podman-runner.md", "tier-1"),
                ("stage-9-development/step-2c-image-based-linux.md", "tier-0"),
                ("stage-7-delivery/procedures/edge-proxy.md", "tier-2"),
            ):
                content = (root / relative).read_text(encoding="utf-8")
                self.assertIn(f"**Working repository:** `<prefix>-{owner}`", content)
                self.assertNotIn("| Shared Ansible role |", content)
        for tier in ("tier-0", "tier-1", "tier-2"):
            readme = (self.root / f"verify-{tier}/README.md").read_text(encoding="utf-8")
            self.assertIn(f"All entry points below belong to `verify-{tier}`", readme)
            self.assertIn("deployment/README.md#repository-locations", readme)

    def test_deployment_code_links_match_the_named_repository(self):
        self.generate()
        for docs, repos in (
            (UPSTREAM / "docs/deployment", {name: UPSTREAM / name for name in
                                           ("tier-0", "tier-1", "tier-2", "shared")}),
            (self.root / "verify-architecture/docs/auto-docs/deployment",
             {name: self.root / f"verify-{name}" for name in
              ("tier-0", "tier-1", "tier-2", "shared")}),
        ):
            checked = 0
            for document in docs.rglob("*.md"):
                for line in document.read_text(encoding="utf-8").splitlines():
                    row = re.match(r"\| (Tier [012]|Shared) \|", line)
                    if not row:
                        continue
                    owner = row[1].lower().replace(" ", "-")
                    for link in re.findall(r"\[[^\]]*\]\(([^)#]+)(?:#[^)]*)?\)", line):
                        destination = (document.parent / link).resolve()
                        if any(destination.is_relative_to(repo) for repo in repos.values()):
                            self.assertTrue(destination.is_relative_to(repos[owner]),
                                            f"{document}: {owner}: {link}")
                            checked += 1
            self.assertGreater(checked, 30)

    def test_architecture_views_connect_overview_domains_and_variants(self):
        root = UPSTREAM / "docs/architecture"
        overview = (root / "README.md").read_text()
        for target in ("reference-platform.md", "runtime-flows.md", "variants.md",
                       "compute/runtime.md", "compute/kubernetes.md", "delivery/controllers.md"):
            self.assertIn(f"({target})", overview)
        layers = overview.split("## Layered model\n", 1)[1].split("## Tiered model\n", 1)[0]
        tiers = overview.split("## Tiered model\n", 1)[1].split("## Tier and zone view\n", 1)[0]
        self.assertIn("block-beta\n  columns 3", layers)
        self.assertLess(layers.index('Edge["'), layers.index('Application["'))
        self.assertLess(layers.index('Application["'), layers.index('Control["'))
        self.assertIn("block-beta\n  columns 1", tiers)
        self.assertLess(tiers.index('T2["'), tiers.index('T1["'))
        self.assertLess(tiers.index('T1["'), tiers.index('T0["'))
        for domain in ("networking", "compute", "identity", "cryptography", "delivery", "operations"):
            content = (root / domain / "README.md").read_text()
            self.assertIn("```mermaid", content, domain)
            self.assertIn("runtime-flows.md", content, domain)
        for document in ("runtime-flows.md", "reference-platform.md", "variants.md"):
            self.assertIn("delivery/controllers.md", (root / document).read_text(), document)
        self.assertIn("kubernetes.md", (root / "compute/runtime.md").read_text())

    def test_capability_placement_and_identity_detail_use_the_same_roles(self):
        root = UPSTREAM / "docs/architecture"
        overview = (root / "README.md").read_text()
        capability_map = overview.split("## Functional structure\n", 1)[1].split(
            "## How the platform works together\n", 1)[0]
        self.assertIn("block-beta\n  columns 5", capability_map)
        self.assertIn('Control["Control"]:2', capability_map)
        for ordered in (('T2["Tier 2', 'T1["Tier 1', 'T0["Tier 0'),
                        ('Edge["Edge', 'Application["Application', 'Control["Control')):
            positions = [capability_map.index(label) for label in ordered]
            self.assertEqual(positions, sorted(positions))
        control = capability_map.split('T0["Tier 0', 1)[1].split('Custodians[', 1)[0]
        for capability in ('IdM["Directory', 'IdP["Identity provider',
                           'PKI["Certificate', 'Secrets["Secrets'):
            self.assertIn(capability, control)
        self.assertIn("Outside connected layers", capability_map)
        identity = (root / "identity/README.md").read_text()
        for expected in ("## Terminology", "Identity and access management (IAM)",
                         "LDAP user federation", "Identity brokering", "Tier 0 / Control layer",
                         "Directory primary", "Directory replica", "control_cluster network",
                         "T2 -->|OIDC to the IdP| T0", "T1 -->|OIDC to the IdP| T0"):
            self.assertIn(expected, identity)
        self.assertNotRegex(identity, r"\bIAP\b")
        self.assertNotIn("identity broker", (root / "runtime-flows.md").read_text().lower())

    def test_architecture_has_no_installation_sequences_or_shell_examples(self):
        root = UPSTREAM / "docs/architecture"
        for document in root.rglob("*.md"):
            content = document.read_text(encoding="utf-8")
            self.assertNotRegex(content, r"(?m)^```(?:bash|sh|shell|powershell|hcl|yaml)", str(document))
            self.assertNotRegex(content, r"(?m)^## (?:Deployment order|Initial deployment|Rollout and validation|Repository path)$",
                                str(document))
            self.assertNotRegex(content, r"(?im)^## (?:Maturity|Capability growth|System states)", str(document))
            self.assertNotRegex(content, r"\bLevel [012]\b", str(document))
            prose = content.split("## References")[0]
            self.assertNotRegex(prose, r"(?im)^\d+\. (?:deploy|install|configure|run|start|move)\b", str(document))

    def test_domains_define_function_choices_and_constraints(self):
        root = UPSTREAM / "docs/architecture"
        for domain in ("compute", "identity", "cryptography", "delivery", "operations"):
            content = (root / domain / "README.md").read_text()
            for heading in ("Components and interfaces", "Design constraints", "Realization"):
                self.assertIn(f"## {heading}", content, domain)
        custody = (root / "cryptography/hsm-selection.md").read_text()
        for option in ("A: Software", "B: Single USB", "C: Replicated USB gateways", "D: Network HSM"):
            self.assertIn(option, custody)
        seal = (root / "cryptography/vault-seal.md").read_text()
        for choice in ("S1: Shamir", "S2: Transit", "S3: Native PKCS#11", "OpenBao", "Enterprise"):
            self.assertIn(choice, seal)
        delivery = (root / "delivery/artifact-supply.md").read_text()
        for choice in ("GitLab", "Harbor", "Dragonfly"):
            self.assertIn(choice, delivery)

    def test_generated_records_separate_static_design_from_progress(self):
        self.generate()
        for repo in self.root.iterdir():
            design = (repo / "docs/architecture/README.md").read_text()
            deployment = (repo / "docs/deployment/README.md").read_text()
            self.assertNotIn("Current maturity", design)
            self.assertNotIn("| Current readiness |", design)
            self.assertIn("Current readiness", deployment)
            self.assertIn("Required readiness", deployment)
            self.assertIn("deployment/readiness.md", deployment)
            self.assertIn("Selected variant / local procedure", deployment)
            for stage in ("stage-1-software-intake", "stage-2-logging", "stage-3-trust", "stage-4-kubernetes", "stage-5-identity",
                          "stage-6-secrets",
                          "stage-7-delivery", "stage-8-observability", "stage-9-development", "stage-10-lab-environments"):
                self.assertIn(f"{stage}/README.md", deployment)
            self.assertIn("../architecture/README.md", deployment)
            self.assertIn("do not transfer resource or state ownership", deployment)
        reference = self.root / "verify-architecture/docs/auto-docs/deployment"
        self.assertEqual(sorted((path.parent.name for path in reference.glob("stage-*/README.md")),
                                key=lambda name: int(name.split("-")[1])),
                         ["stage-1-software-intake", "stage-2-logging", "stage-3-trust", "stage-4-kubernetes", "stage-5-identity",
                          "stage-6-secrets",
                          "stage-7-delivery", "stage-8-observability", "stage-9-development", "stage-10-lab-environments"])
        for old in ("stages", "compute", "cryptography", "identity", "network", "delivery", "operations"):
            self.assertFalse((reference / old).exists(), old)
        architecture = self.root / "verify-architecture/docs/architecture"
        for domain in ("networking", "compute", "identity", "cryptography", "delivery", "operations"):
            self.assertTrue((architecture / domain / "README.md").is_file())
            self.assertTrue((reference.parent / "architecture" / domain / "README.md").is_file())
        for old in ("system", "subsystems", "system-design", "subsystem-design"):
            self.assertFalse((architecture / old).exists())
            self.assertFalse((reference.parent / "architecture" / old).exists())
        self.assertTrue((reference.parent / "architecture/reference-platform.md").is_file())
        for document in ("runtime-flows.md", "variants.md", "compute/runtime.md",
                         "compute/kubernetes.md", "delivery/controllers.md"):
            self.assertTrue((reference.parent / "architecture" / document).is_file(), document)
        platform = (architecture / "README.md").read_text()
        self.assertIn("auto-docs/architecture/runtime-flows.md", platform)
        self.assertIn("auto-docs/architecture/variants.md", platform)
        self.assertIn("Tier 2, Tier 1, Tier 0", platform)
        self.assertIn("Edge, Application, Control", platform)
        self.assertIn("| Capability | Owning tier | Security layer | Domain design |", platform)
        for domain in ("networking", "compute", "identity", "cryptography", "delivery", "operations"):
            selected = (architecture / domain / "README.md").read_text()
            self.assertIn("## Resulting domain design", selected)
            self.assertIn("auto-docs/architecture/variants.md", selected)
