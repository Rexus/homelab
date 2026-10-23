"""Prerequisites and deployable capabilities have distinct, navigable entry points."""

import re

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class DeploymentPaths(TierRepositoryTestCase):
    def test_capability_names_have_unique_numbers_and_federation_belongs_to_identity(self):
        self.generate()
        expected = ["stage-1-software-intake", "stage-2-logging", "stage-3-trust", "stage-4-kubernetes",
                    "stage-5-identity", "stage-6-secrets",
                    "stage-7-delivery", "stage-8-observability", "stage-9-workloads"]
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            root = docs / "deployment"
            directories = sorted(path.name for path in root.glob("stage-*") if path.is_dir())
            self.assertEqual(directories, expected)
            numbers = [int(name.split("-")[1]) for name in directories]
            self.assertEqual(numbers, list(range(1, 10)))
            identity = (root / "stage-5-identity/README.md").read_text()
            secrets = (root / "stage-6-secrets/README.md").read_text()
            self.assertTrue(identity.startswith("# Stage 5: Identity\n"))
            self.assertTrue(secrets.startswith("# Stage 6: Secrets\n"))
            federation = identity.split("## Step 2: Deploy identity federation", 1)[1]
            for term in ("applications/keycloak/", "OIDC clients", "FreeIPA federation", "**Integration:**"):
                self.assertIn(term, federation)
            self.assertIn("## Step 1: Deploy the secret service", secrets)
            self.assertIn("Keycloak[\"Existing Keycloak / IdP\"]", secrets)
            added = re.search(r'subgraph Added\[.*?\n        end', secrets, re.DOTALL)[0]
            self.assertNotIn("Keycloak", added)
            self.assertIn("step-1b-vault-vm.md", secrets)
            self.assertIn("step-1c-seal-integration.md", secrets)
            index = (root / "README.md").read_text()
            self.assertIn('Runtime["4. Kubernetes<br/>', index)
            self.assertIn('Identity["5. Identity<br/>', index)
            self.assertIn('Control["6. Secrets<br/>', index)

    def test_foundation_is_unnumbered_and_intake_precedes_logging(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            root = docs / "deployment"
            foundation = (root / "foundation/README.md").read_text()
            self.assertTrue(foundation.startswith("# Foundation and prerequisites"))
            self.assertIn("not a numbered capability stage", foundation)
            self.assertNotIn("## Step 4: Establish protected logging", foundation)
            self.assertIn("stage-2-logging/README.md", foundation)
            stages = sorted(root.glob("stage-*/README.md"))
            self.assertEqual(stages[0].parent.name, "stage-1-software-intake")
            self.assertFalse((root / "stage-1-foundation").exists())
            expected_steps = {
                "stage-2-logging/README.md": ["1", "2", "3"],
                "stage-6-secrets/monitoring.md": ["1", "2", "3"],
                "stage-8-observability/README.md": ["1", "2", "3", "4"],
                "stage-9-workloads/telemetry.md": ["1", "2", "3"],
            }
            for relative, expected in expected_steps.items():
                content = (root / relative).read_text()
                steps = re.findall(r"(?m)^## Step (\d+):", content)
                self.assertEqual(steps, expected, relative)
                sections = re.split(r"(?m)^## Step \d+:", content)[1:]
                for section in sections:
                    self.assertIn("```mermaid", section, relative)
                self.assertIn("**Working repository:**", content, relative)
                self.assertIn("**Prerequisites:**", content, relative)
            logging = stages[1].read_text()
            for command in ("scripts/init-local-files.sh --setup syslog",
                            "scripts/deploy.sh syslog --plan-only", "scripts/deploy.sh syslog"):
                self.assertIn(command, logging)
            self.assertIn("OS baseline", logging)
            self.assertIn("sources.md", logging)
            self.assertIn("step-3c-nas-archive.md", logging)
            self.assertIn("declared durability limits", logging)

    def test_every_runnable_root_has_a_capability_and_walkthrough(self):
        self.generate()
        for docs, collection, prefix in (
            (UPSTREAM / "docs", UPSTREAM, ""),
            (self.root / "verify-architecture/docs/auto-docs", self.root, "verify-"),
        ):
            index = (docs / "deployment/README.md").read_text()
            capability_map = index.split("## IaC capability map\n", 1)[1].split("## Repository locations\n", 1)[0]
            entries = re.findall(r"(?m)^\| Tier ([012]) \| `([^`]+)` \|", capability_map)
            expected = set()
            for number in range(3):
                tier = collection / f"{prefix}tier-{number}"
                setups = set((tier / ".deployment-setups").read_text().splitlines()) | {"kubernetes"}
                if number == 0:
                    setups.add("templates")
                expected.update((str(number), setup) for setup in setups)
                for setup in setups:
                    self.assertTrue((tier / "terraform/deployments" / setup / "main.tf").is_file())
            self.assertEqual(set(entries), expected)
            self.assertEqual(len(entries), len(expected))
            self.assertIn("never rename state roots", index)

    def test_kubernetes_is_a_complete_reader_path_before_identity_consumers(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            deployment = docs / "deployment"
            cluster = (deployment / "stage-4-kubernetes/README.md").read_text()
            identity = (deployment / "stage-5-identity/README.md").read_text()
            self.assertEqual(re.findall(r"(?m)^## Step (\d+):", cluster), ["1", "2", "3"])
            for action in ("init", "plan", "apply", "credentials"):
                self.assertIn(f"bash scripts/kubernetes-cluster.sh {action}", cluster)
            for expected in ("independent DNS/time", "private", "API endpoint outside this cluster",
                             "project integration", "node/API audit forwarding", "etcd",
                             "../stage-5-identity/README.md", "step-1b-manual-cluster.md"):
                self.assertIn(expected, cluster)
            self.assertEqual(re.findall(r"(?m)^## Step (\d+):", identity), ["1", "2"])
            self.assertIn("../stage-4-kubernetes/README.md", identity)
            self.assertNotIn("## Step 2: Create the Kubernetes cluster", identity)
            for procedure in ("kubernetes.md", "talos-terraform.md"):
                self.assertTrue((deployment / "stage-4-kubernetes/procedures" / procedure).is_file())
                self.assertFalse((deployment / "stage-5-identity/procedures" / procedure).exists())
