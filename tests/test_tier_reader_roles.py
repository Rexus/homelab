"""Design alternatives, staged realization and owned project records stay aligned."""

import re

from test_tier_deployment_navigation import anchors
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class ReaderRoles(TierRepositoryTestCase):
    def test_deployment_guides_name_working_repositories_in_source_and_generated_docs(self):
        self.generate()
        source = UPSTREAM / "docs/03-deployment"
        generated = self.root / "verify-architecture/docs/auto-docs/03-deployment"
        for root in (source, generated):
            prefix = "<prefix>" if root == source else "verify"
            index = (root / "README.md").read_text(encoding="utf-8")
            self.assertIn("## Repository locations", index)
            self.assertIn("Run repository scripts from the owning tier's root", index)
            for name in ("tier-0", "tier-1", "tier-2", "shared", "architecture"):
                self.assertIn(f"`{prefix}-{name}/`", index)
            for name in ("tier-0", "tier-1", "tier-2", "shared"):
                link = re.search(rf"\[{name}/\]\(([^)]+)\)", index)[1]
                expected = UPSTREAM / name if root == source else self.root / f"verify-{name}"
                self.assertEqual((root / link).resolve(), expected)
            for document in [*root.glob("stage-*/**/*.md"), *root.glob("foundation/**/*.md"),
                             *root.glob("stage-01-software-intake/**/*.md")]:
                content = document.read_text(encoding="utf-8")
                # Result figures can precede context; execution ownership must precede commands.
                opening = re.split(r"(?m)^```(?:bash|sh|shell|powershell|hcl|yaml)\b", content, maxsplit=1)[0]
                if (document.relative_to(root).as_posix().startswith("foundation/bootstrap/") and
                        "**Run on `boot-1`**" in opening):
                    # Manual host preparation can precede checkout/generation of any tier repository.
                    continue
                self.assertRegex(opening, r"\*\*Working repositor(?:y|ies):\*\*|## Working repositories", str(document))
                self.assertIn(f"{prefix}-tier-", opening, str(document))
            for relative, owner in (
                ("../08-reference/proxy-cache.md", "tier-2"),
                ("stage-02-trust/step-1b-usb-hsm.md", "tier-0"),
                ("stage-05-identity/procedures/freeipa.md", "tier-0"),
                ("stage-06-secrets/step-1b-vault-vm.md", "tier-0"),
                ("stage-08-observability/step-1b-dedicated-vms.md", "tier-1"),
                ("stage-09-development/step-1b-source-control-vm.md", "tier-1"),
                ("stage-09-development/step-14b-podman-runner.md", "tier-1"),
                ("stage-09-development/step-15b-image-based-linux.md", "tier-0"),
                ("stage-07-delivery/procedures/edge-proxy.md", "tier-2"),
            ):
                content = (root / relative).read_text(encoding="utf-8")
                self.assertIn(f"**Working repository:** `{prefix}-{owner}`", content)
                self.assertNotIn("| Shared Ansible role |", content)
        for tier in ("tier-0", "tier-1", "tier-2"):
            readme = (self.root / f"verify-{tier}/README.md").read_text(encoding="utf-8")
            self.assertIn(f"All entry points below belong to `verify-{tier}`", readme)
            self.assertIn("03-deployment/README.md#repository-locations", readme)

    def test_deployment_code_links_match_the_named_repository(self):
        self.generate()
        for docs, repos in (
            (UPSTREAM / "docs/03-deployment", {name: UPSTREAM / name for name in
                                           ("tier-0", "tier-1", "tier-2", "shared")}),
            (self.root / "verify-architecture/docs/auto-docs/03-deployment",
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

    def test_architecture_routes_decisions_to_the_owning_capability(self):
        root = UPSTREAM / "docs/01-architecture"
        overview = (root / "README.md").read_text()
        for target in ("03-reference-platform.md", "01-background/README.md", "02-organization/README.md",
                       "04-hosting/README.md", "06-data/README.md", "10-delivery/README.md"):
            self.assertIn(f"({target})", overview)
        capabilities = overview.split("## Capabilities\n", 1)[1].split(
            "## How the platform works together\n", 1)[0]
        for chapter in ("04-hosting", "05-networking", "06-data", "07-software-intake",
                        "08-cryptography", "09-identity", "10-delivery", "11-operations"):
            self.assertIn(f"({chapter}/README.md)", capabilities)
        for principle in ("Zero trust", "scalability"):
            self.assertIn(principle, capabilities)
        self.assertIn("Read to make a decision", overview)
        self.assertEqual({path.name for path in root.iterdir() if path.is_dir()}, {
            "01-background", "02-organization", "04-hosting", "05-networking", "06-data",
            "07-software-intake", "08-cryptography", "09-identity", "10-delivery", "11-operations",
        })
        for document in ("05-networking/README.md", "04-hosting/README.md", "06-data/README.md", "09-identity/README.md",
                         "08-cryptography/README.md", "10-delivery/README.md", "11-operations/README.md"):
            content = (root / document).read_text()
            self.assertIn("```mermaid", content, document)
        interactions = {
            "09-identity/README.md": "## Service access",
            "10-delivery/README.md": "## Application delivery",
            "07-software-intake/README.md": "## Cache request and response",
        }
        for document, heading in interactions.items():
            content = (root / document).read_text()
            self.assertIn(heading, content)
            self.assertIn("sequenceDiagram", content)
        self.assertIn("kubernetes.md", (root / "04-hosting/01-runtime.md").read_text())

    def test_capability_placement_and_identity_detail_use_the_same_roles(self):
        root = UPSTREAM / "docs/01-architecture"
        overview = (root / "README.md").read_text()
        capability_map = overview.split("## Functional structure\n", 1)[1].split(
            "## Capabilities\n", 1)[0]
        self.assertIn("flowchart TB", capability_map)
        self.assertIn('subgraph Control["Control Services"]', capability_map)
        for ordered in (('T2["Tier 2', 'T1["Tier 1', 'T0["Tier 0'),
                        ('Edge["Edge', 'Workloads["Application', 'Control["Control')):
            positions = [capability_map.index(label) for label in ordered]
            self.assertEqual(positions, sorted(positions))
        control = capability_map.split('T0["Tier 0', 1)[1].split('Offline[', 1)[0]
        for capability in ('Directory authority', 'Identity provider',
                           'Certificate issuance', 'SSO / secrets'):
            self.assertIn(capability, control)
        self.assertIn("Outside connected runtimes", capability_map)
        identity = (root / "09-identity/README.md").read_text()
        for expected in ("## Terminology", "Identity and access management (IAM)",
                         "LDAP user federation", "Identity brokering", 'subgraph T0["Tier 0"]',
                         "Directory primary", "Directory replica", "Tier 0 Kubernetes / control_cluster",
                         "Consumers -->|OIDC sign-in| Ingress"):
            self.assertIn(expected, identity)
        self.assertNotRegex(identity, r"\bIAP\b")
        sequence = identity.split("## Service access\n", 1)[1].split("## Components and interfaces\n", 1)[0]
        self.assertNotIn("identity broker", sequence.lower())

    def test_architecture_has_no_installation_sequences_or_shell_examples(self):
        root = UPSTREAM / "docs/01-architecture"
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
        root = UPSTREAM / "docs/01-architecture"
        for document in ("04-hosting/README.md", "09-identity/README.md", "08-cryptography/README.md",
                         "10-delivery/README.md", "11-operations/README.md"):
            content = (root / document).read_text()
            for heading in ("Components and interfaces", "Design constraints"):
                self.assertIn(f"## {heading}", content, document)
            self.assertRegex(content, r"(?m)^## (?:Reference realization|Realization)$", document)
        data = (root / "06-data/README.md").read_text()
        for heading in ("Storage interfaces", "Administration and consumption", "Reference realization"):
            self.assertIn(f"## {heading}", data)
        custody = (root / "08-cryptography/03-hsm-selection.md").read_text()
        for option in ("A: Software", "B: Single USB", "C: Replicated USB gateways", "D: Network HSM"):
            self.assertIn(option, custody)
        seal = (root / "08-cryptography/06-vault-seal.md").read_text()
        for choice in ("S1: Shamir", "S2: Transit", "S3: Native PKCS#11", "OpenBao", "Enterprise"):
            self.assertIn(choice, seal)
        delivery = (root / "10-delivery/01-artifact-supply.md").read_text()
        for choice in ("GitLab", "Harbor", "Dragonfly"):
            self.assertIn(choice, delivery)

    def test_generated_configuration_comments_link_to_the_sibling_manual(self):
        self.generate()
        checked = 0
        for name in ("tier-0", "tier-1", "tier-2", "shared"):
            repo = self.root / f"verify-{name}"
            inputs = [*repo.rglob("*.example"), *repo.glob("config/*.tfvars"),
                      *repo.glob("templates/*.tfvars")]
            for path in inputs:
                comments = "\n".join(re.findall(r"(?m)^[ \t]*#[^\n]*", path.read_text(encoding="utf-8")))
                self.assertNotRegex(comments, r"(?<![\w/.-])docs/[0-9]{2}-", str(path))
                self.assertNotRegex(comments, r"<prefix>-(?:tier-[012]|shared|architecture|iac)\b", str(path))
                for reference in re.findall(r"\.\./verify-architecture/docs/auto-docs/[\w./#-]+", comments):
                    relative, _, fragment = reference.rstrip(".").partition("#")
                    target = (repo / relative).resolve()
                    self.assertTrue(target.is_file(), f"{path}: {reference}")
                    if fragment:
                        self.assertIn(fragment, anchors(target.read_text(encoding="utf-8")),
                                      f"{path}: {reference}")
                    checked += 1
            if name != "shared":
                schema = "terraform/deployments/kubernetes/variables.tf"
                example = repo / "terraform/deployments/kubernetes/terraform.tfvars.example"
                self.assertIn(schema, example.read_text(encoding="utf-8"))
                self.assertTrue((repo / schema).is_file())
                consumer = repo / "ansible/group_vars/software_consumer.yml.example"
                schema = "../verify-shared/ansible/roles/baseline/defaults/main.yml"
                self.assertIn(schema, consumer.read_text(encoding="utf-8"))
                self.assertTrue((repo / schema).is_file())
        self.assertGreater(checked, 50)

    def test_generated_delivery_records_follow_the_selected_stage_7_path(self):
        self.generate()
        design = (self.root / "verify-tier-1/docs/architecture/README.md").read_text(encoding="utf-8")
        self.assertIn("independent Tier 1 Flux reconciliation and Spinnaker application Git promotion", design)
        checklist = (self.root / "verify-architecture/deployments.md").read_text(encoding="utf-8")
        delivery = checklist.split("## 7. Delivery\n", 1)[1].split("## 8. Observability\n", 1)[0]
        self.assertIn("**Path 2b:** Spinnaker with Flux application promotion", delivery)
        self.assertIn("**Alternative 2a:** Argo CD", delivery)
        self.assertIn("direct Spinnaker", delivery)
        self.assertIn("stage-07-delivery/README.md#step-2-select-and-qualify-delivery", delivery)

    def test_script_setup_catalog_matches_tier_registrations(self):
        self.generate()
        expected = {setup for name in ("tier-0", "tier-1", "tier-2")
                    for setup in (UPSTREAM / name / ".deployment-setups").read_text(encoding="utf-8").splitlines()}
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            reference = (docs / "08-reference/repository-scripts.md").read_text(encoding="utf-8")
            catalog = reference.split("## Available setups\n", 1)[1].split("## What the deployment wrapper does\n", 1)[0]
            entries = re.findall(r"(?m)^\| `([^`]+)` \|", catalog)
            self.assertEqual(set(entries), expected)
            self.assertEqual(len(entries), len(expected))

    def test_generated_records_separate_static_design_from_progress(self):
        self.generate()
        for repo in self.root.iterdir():
            if repo.name == "verify-architecture":
                continue
            design = (repo / "docs/architecture/README.md").read_text()
            deployment = (repo / "docs/deployment/README.md").read_text()
            self.assertNotIn("Current maturity", design)
            self.assertNotIn("| Current readiness |", design)
            self.assertIn("Current readiness", deployment)
            self.assertIn("Required readiness", deployment)
            self.assertIn("03-deployment/readiness.md", deployment)
            self.assertIn("Selected variant / local procedure", deployment)
            for stage in ("stage-01-software-intake", "stage-02-trust", "stage-03-logging", "stage-04-kubernetes", "stage-05-identity",
                          "stage-06-secrets",
                          "stage-07-delivery", "stage-08-observability", "stage-09-development", "stage-10-lab-environments"):
                self.assertIn(f"{stage}/README.md", deployment)
            self.assertIn("../architecture/README.md", deployment)
            self.assertIn("do not transfer resource or state ownership", deployment)
        reference = self.root / "verify-architecture/docs/auto-docs/03-deployment"
        self.assertEqual(sorted((path.parent.name for path in reference.glob("stage-*/README.md")),
                                key=lambda name: int(name.split("-")[1])),
                         ["stage-01-software-intake", "stage-02-trust", "stage-03-logging", "stage-04-kubernetes", "stage-05-identity",
                          "stage-06-secrets",
                          "stage-07-delivery", "stage-08-observability", "stage-09-development", "stage-10-lab-environments"])
        for old in ("stages", "compute", "cryptography", "identity", "network", "delivery", "operations"):
            self.assertFalse((reference / old).exists(), old)
        architecture = self.root / "verify-architecture/docs/architecture"
        self.assertFalse(architecture.exists())
        for domain in ("networking", "hosting", "data", "identity", "cryptography", "software-intake",
                       "delivery", "development-platform", "operations"):
            self.assertTrue((reference.parent / "architecture" / domain / "README.md").is_file())
        self.assertTrue((reference.parent / "architecture/software-lifecycle.md").is_file())
        for old in ("system", "subsystems", "system-design", "subsystem-design"):
            self.assertFalse((architecture / old).exists())
            self.assertFalse((reference.parent / "architecture" / old).exists())
        self.assertTrue((reference.parent / "01-architecture/03-reference-platform.md").is_file())
        for document in ("README.md", "02-organization/README.md", "04-hosting/01-runtime.md",
                         "04-hosting/03-kubernetes.md", "10-delivery/02-controllers.md"):
            self.assertTrue((reference.parent / "architecture" / document).is_file(), document)
        for retired in ("06-reference-platform.md", "07-runtime-flows.md", "08-variants.md",
                        "17-kubernetes/README.md", "13-software-intake/01-design.md"):
            self.assertFalse((reference.parent / "01-architecture" / retired).exists(), retired)
            alias = reference.parent / "architecture" / retired
            self.assertTrue(alias.is_file(), retired)
            self.assertIn("Compatibility copy", alias.read_text())
        platform = (architecture.parent / "README.md").read_text()
        self.assertIn("auto-docs/01-architecture/README.md", platform)
        self.assertIn("auto-docs/01-architecture/02-organization/README.md", platform)
        self.assertIn("Tier 2, Tier 1, Tier 0", platform)
        self.assertIn("Edge, Application, Control", platform)
        self.assertIn("[deployments.md](../deployments.md)", platform)
        checklist = (self.root / "verify-architecture/deployments.md").read_text()
        self.assertIn("- [ ]", checklist)
        self.assertNotIn("| Deployed | Verified |", platform)
