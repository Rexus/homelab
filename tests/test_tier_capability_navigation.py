"""Capability journeys and the optional Windows intake remain discoverable."""

from pathlib import Path
import re

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from test_tier_deployment_navigation import links


def area(root, name):
    primary = {"architecture": "01-architecture", "deployment": "03-deployment",
               "operations": "05-operations"}
    if (root / primary[name]).is_dir():
        return root / primary[name]
    matches = list(root.glob(f"[0-9][0-9]-{name}"))
    if len(matches) == 1:
        return matches[0]
    direct = root / name
    if not matches and direct.is_dir():
        return direct
    raise AssertionError(f"Cannot find unique documentation area {name} in {root}")


class CapabilityNavigation(TierRepositoryTestCase):
    def test_operations_has_one_compact_route_per_operating_domain(self):
        self.generate()
        for root in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            operations = root / "05-operations"
            chapters = sorted(path for path in operations.iterdir() if path.name != "README.md")
            self.assertEqual([int(path.name[:2]) for path in chapters], list(range(1, 7)))
            destinations = {link.target for link in links(operations / "README.md")}
            for chapter in chapters:
                entry = chapter / "README.md" if chapter.is_dir() else chapter
                self.assertIn(entry.resolve(), destinations)

    def test_main_documentation_folders_follow_reading_order(self):
        expected = ["01-architecture", "02-conventions", "03-deployment", "04-development",
                    "05-operations", "06-paths", "07-decisions", "08-reference"]
        self.assertEqual(sorted(path.name for path in (UPSTREAM / "docs").iterdir() if path.is_dir()),
                         expected)

    def test_capability_journeys_in_source_and_generated_manual(self):
        self.generate()
        for root in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            index = root / "06-paths/capabilities.md"
            content = index.read_text(encoding="utf-8")
            rows = [line for line in content.splitlines() if line.startswith("| ")][2:]
            self.assertEqual(len(rows), 10)
            for row in rows:
                links = re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", row)
                self.assertGreaterEqual(len(links), 3, row)
                for link in links:
                    self.assertTrue((index.parent / link).is_file(), f"{index}: {link}")
            stages = area(root, "deployment")
            for stage in stages.glob("stage-*/README.md"):
                text = stage.read_text(encoding="utf-8")
                self.assertRegex(text, r"\]\([^)]*architecture/[^)]*\)", str(stage))
                self.assertRegex(text, r"\]\([^)]*operations/[^)]*\)", str(stage))

            design = (area(root, "architecture") / "README.md").read_text(encoding="utf-8")
            operations = (area(root, "operations") / "README.md").read_text(encoding="utf-8")
            support = (root / "08-reference/implementation-support.md").read_text(encoding="utf-8")
            names = ("Software intake", "Protected logging", "Cryptographic trust", "Kubernetes",
                     "Identity", "Secrets", "Delivery", "Observability", "Development platform",
                     "Lab environments")
            for number, name in enumerate(names, start=1):
                self.assertIn(name, design)
                self.assertIn(name, operations)
                self.assertIn(f"[{number}: {name}]", support)

    def test_each_deployment_capability_connects_its_design_and_operations(self):
        self.generate()
        for root in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            index = root / "06-paths/capabilities.md"
            rows = [line for line in index.read_text(encoding="utf-8").splitlines()
                    if line.startswith("| ")][2:]
            stages = {}
            for stage in area(root, "deployment").glob("stage-*/README.md"):
                heading = stage.read_text(encoding="utf-8").splitlines()[0]
                match = re.fullmatch(r"# Stage \d+: (.+)", heading)
                self.assertIsNotNone(match, str(stage))
                stages[match[1].lower()] = stage.resolve()
            self.assertEqual(len(stages), 10)
            mapped = set()
            for row in rows:
                capability = row.split("|")[1].strip().lower()
                self.assertIn(capability, stages, row)
                mapped.add(capability)
                destinations = [link.target for link in links(index, row)]
                self.assertEqual(len(destinations), 3, row)
                architecture, stage, operations = destinations
                self.assertEqual(stage, stages[capability], row)
                for page, expected in ((stage, (architecture, operations)),
                                       (architecture, (stage, operations)),
                                       (operations, (stage, architecture))):
                    targets = {link.target for link in links(page)}
                    for target in expected:
                        self.assertIn(target, targets, f"{page} must link to {target}")
            self.assertEqual(mapped, set(stages))

    def test_windows_option_extends_existing_policy_and_has_a_numbered_route(self):
        self.generate()
        for root in (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs"):
            stage = area(root, "deployment") / "stage-1-software-intake"
            overview = (stage / "README.md").read_text(encoding="utf-8")
            option = stage / "step-7b-windows-update.md"
            text = option.read_text(encoding="utf-8")
            self.assertIn("step-7b-windows-update.md", overview)
            self.assertIn("cache_squid_allowed_domains", text)
            self.assertIn("cache_squid_allowed_cidrs", text)
            entries = re.search(r"```yaml\n(.*?)```", text, re.S)
            self.assertIsNotNone(entries)
            domains = yaml.safe_load(entries[1])
            self.assertIsInstance(domains, list)
            self.assertIn(".windowsupdate.com", domains)
            self.assertIn(".update.microsoft.com", domains)
            self.assertNotIn("*", "".join(domains))
            self.assertIn("not been verified end to end", text)
