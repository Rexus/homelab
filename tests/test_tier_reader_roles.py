"""Design alternatives, staged realization and owned project records stay aligned."""

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class ReaderRoles(TierRepositoryTestCase):
    def test_architecture_views_connect_overview_domains_and_variants(self):
        root = UPSTREAM / "docs/architecture"
        overview = (root / "README.md").read_text()
        for target in ("reference-platform.md", "runtime-flows.md", "variants.md",
                       "compute/runtime.md", "compute/kubernetes.md", "delivery/controllers.md"):
            self.assertIn(f"({target})", overview)
        layers = overview.split("## Layered model\n", 1)[1].split("## Tiered model\n", 1)[0]
        tiers = overview.split("## Tiered model\n", 1)[1].split("## Tier and zone view\n", 1)[0]
        self.assertIn("flowchart LR", layers)
        self.assertIn("Edge --- Application --- Control", layers)
        self.assertIn("flowchart TB", tiers)
        self.assertIn("T2 --- T1 --- T0", tiers)
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
        self.assertIn("block-beta\n  columns 4", capability_map)
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
                         "Dedicated primary VM", "Dedicated replica VM", "Tier 0 Kubernetes",
                         "T2 -->|OIDC integration| IdP", "T1 -->|OIDC integration| IdP"):
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
            for stage in ("stage-1-foundation", "stage-2-trust", "stage-3-identity-runtime",
                          "stage-4-control-services", "stage-5-delivery", "stage-6-workloads"):
                self.assertIn(f"{stage}/README.md", deployment)
            self.assertIn("../architecture/README.md", deployment)
            self.assertIn("do not transfer resource or state ownership", deployment)
        reference = self.root / "verify-architecture/docs/auto-docs/deployment"
        self.assertEqual(sorted(path.parent.name for path in reference.glob("stage-*/README.md")),
                         ["stage-1-foundation", "stage-2-trust", "stage-3-identity-runtime",
                          "stage-4-control-services", "stage-5-delivery", "stage-6-workloads"])
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
