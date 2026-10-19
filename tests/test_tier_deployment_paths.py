"""Prerequisites and deployable capabilities have distinct, navigable entry points."""

import re

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class DeploymentPaths(TierRepositoryTestCase):
    def test_foundation_is_unnumbered_and_logging_is_the_first_capability(self):
        self.generate()
        for docs in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            root = docs / "deployment"
            foundation = (root / "foundation/README.md").read_text()
            self.assertTrue(foundation.startswith("# Foundation and prerequisites"))
            self.assertIn("not a numbered capability stage", foundation)
            self.assertNotIn("## Step 4: Establish protected logging", foundation)
            self.assertIn("stage-1-logging/README.md", foundation)
            stages = sorted(root.glob("stage-*/README.md"))
            self.assertEqual(stages[0].parent.name, "stage-1-logging")
            self.assertFalse((root / "stage-1-foundation").exists())
            for relative in ("stage-1-logging/README.md", "stage-4-control-services/monitoring.md",
                             "stage-5-delivery/analytics.md", "stage-6-workloads/telemetry.md"):
                content = (root / relative).read_text()
                steps = re.findall(r"(?m)^## Step (\d+):", content)
                self.assertEqual(steps, ["1", "2", "3"], relative)
                sections = re.split(r"(?m)^## Step \d+:", content)[1:]
                for section in sections:
                    self.assertIn("```mermaid", section, relative)
                self.assertIn("**Working repository:**", content, relative)
                self.assertIn("**Prerequisites:**", content, relative)
            logging = stages[0].read_text()
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
