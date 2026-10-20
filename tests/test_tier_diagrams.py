"""Portable Mermaid styling, placement conventions and generated diagram assets."""

import hashlib
import json
import re
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


PALETTE = "reference/diagrams/palette.json"


def diagrams(document):
    return re.findall(r"```mermaid\n(.*?)```", document.read_text(encoding="utf-8"), re.DOTALL)


def luminance(colour):
    channels = [int(colour[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
              for value in channels]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(first, second):
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class DiagramConventions(TierRepositoryTestCase):
    def test_palette_pairs_are_legible_on_light_and_dark_pages(self):
        palette = json.loads((UPSTREAM / "docs" / PALETTE).read_text())
        for role, style in palette["roles"].items():
            backgrounds = [style["fill"]] if style["fill"] != "none" else [
                parent["fill"] for parent in palette["roles"].values() if parent["fill"] != "none"]
            for background in backgrounds:
                self.assertGreaterEqual(contrast(style["color"], background), 4.5, role)
        for background in ("#ffffff", "#0d1117"):
            self.assertGreaterEqual(contrast(palette["links"]["stroke"], background), 3)
        for colour in palette["charts"]["series"]:
            for background in ("#ffffff", "#333333"):
                self.assertGreaterEqual(contrast(colour, background), 3)
        self.assertGreaterEqual(contrast(palette["roles"]["default"]["color"],
                                         palette["links"]["labelBackground"]), 4.5)

    def test_source_and_generated_diagrams_use_the_same_portable_roles(self):
        self.generate("--repo", "architecture")
        source = UPSTREAM / "docs"
        generated = self.root / "verify-architecture/docs/auto-docs"
        palette = json.loads((source / PALETTE).read_text())
        self.assertEqual((source / PALETTE).read_bytes(), (generated / PALETTE).read_bytes())
        checked = 0
        for document in source.rglob("*.md"):
            blocks = diagrams(document)
            self.assertEqual(blocks, diagrams(generated / document.relative_to(source)), str(document))
            for code in blocks:
                if not re.search(r"(?m)^(?:flowchart|block-beta)\b", code):
                    continue
                definitions = dict(re.findall(r"(?m)^  classDef (\w+) (.+)$", code))
                self.assertIn("default", definitions, str(document))
                self.assertNotRegex(code, r"(?m)^\s*(?:style|linkStyle)\s", str(document))
                for role, declarations in definitions.items():
                    self.assertIn(role, palette["roles"], str(document))
                    actual = dict(item.split(":", 1) for item in declarations.split(","))
                    self.assertEqual(actual, palette["roles"][role], f"{document}: {role}")
                for role in re.findall(r"(?m)^  class [\w,]+ (\w+)$", code):
                    self.assertIn(role, definitions, str(document))
                if "flowchart" in code:
                    initializer = re.search(r"%%\{init: (.+)\}%%", code)
                    config = json.loads(initializer[1])
                    self.assertEqual(config["theme"], "base")
                    self.assertEqual(config["themeVariables"]["lineColor"], palette["links"]["stroke"])
                    self.assertEqual(config["themeVariables"]["edgeLabelBackground"],
                                     palette["links"]["labelBackground"])
                checked += 1
        self.assertGreater(checked, 50)

    def test_palette_refresh_updates_managed_assets_but_preserves_local_edits_and_deletion(self):
        self.generate("--repo", "architecture")
        repo = self.root / "verify-architecture"
        relative = "docs/auto-docs/" + PALETTE
        target = repo / relative
        original = target.read_bytes()
        manifest_path = repo / ".generated-files.json"
        manifest = json.loads(manifest_path.read_text())
        self.assertIn(relative, manifest["files"])
        self.assertNotIn(relative, manifest["owned"])
        old_generated = b"{}\n"
        target.write_bytes(old_generated)
        manifest["files"][relative] = hashlib.sha256(old_generated).hexdigest()
        manifest_path.write_text(json.dumps(manifest))
        self.generate("--repo", "architecture", "--refresh")
        self.assertEqual(target.read_bytes(), original)
        local = original.replace(b"#e2f3ed", b"#e3f3ed")
        self.assertNotEqual(local, original)
        target.write_bytes(local)
        self.generate("--repo", "architecture", "--refresh")
        self.assertEqual(target.read_bytes(), local)
        target.unlink()
        self.generate("--repo", "architecture", "--refresh")
        self.assertFalse(target.exists())

    def test_placement_grids_keep_tiers_ordered_without_traffic_arrows(self):
        root = UPSTREAM / "docs/architecture"
        overview = diagrams(root / "README.md")
        layers = overview[1]
        self.assertIn("block-beta\n  columns 3", layers)
        for code in (overview[0], overview[2],
                     diagrams(root / "compute/kubernetes.md")[0],
                     diagrams(root / "compute/runtime.md")[0],
                     diagrams(root / "operations/telemetry.md")[0]):
            self.assertIn("block-beta", code)
            order = [code.index(f'T{tier}["') for tier in (2, 1, 0)]
            self.assertEqual(order, sorted(order))
            self.assertNotIn("-->", code)
            self.assertNotIn("---", code)
        self.assertLess(layers.index('Edge["'), layers.index('Application["'))
        self.assertLess(layers.index('Application["'), layers.index('Control["'))
        identity = diagrams(root / "identity/README.md")[0]
        self.assertIn('subgraph T0["Tier 0 / Control layer"]', identity)
        self.assertIn("T2 ~~~ T1", identity)
        self.assertIn("T1 ~~~ Services", identity)
        self.assertIn("class Cluster runtime", identity)
        self.assertIn("Hosts -->|DNS, LDAP and Kerberos| Directory", identity)

    def test_charts_and_sequence_keep_theme_aware_text(self):
        root = UPSTREAM / "docs/architecture"
        charts = [code for code in diagrams(root / "private-cloud.md") if "xychart-beta" in code]
        self.assertEqual(len(charts), 2)
        palette = json.loads((UPSTREAM / "docs" / PALETTE).read_text())
        for chart in charts:
            initializer = re.search(r"%%\{init: (.+)\}%%", chart)
            config = json.loads(initializer[1])
            self.assertNotIn("theme", config)
            colours = config["themeVariables"]["xyChart"]["plotColorPalette"].split(",")
            self.assertEqual(colours, palette["charts"]["series"])
        sequence = diagrams(root / "runtime-flows.md")[0]
        self.assertIn("sequenceDiagram", sequence)
        self.assertNotIn("theme", sequence)
        self.assertIn("rect rgba(", sequence)

    def test_logging_steps_keep_deployment_boundaries_and_inventory_names(self):
        root = UPSTREAM / "docs/deployment/stage-1-logging"
        steps = diagrams(root / "README.md")
        self.assertEqual(len(steps), 3)
        for code in steps:
            self.assertIn("block-beta", code)
            self.assertIn('block:T0', code)
            self.assertIn('T0Title["Tier 0 / Control layer"]', code)
            self.assertIn('block:PVE\n', code)
            self.assertIn('VM["foundation-log-1', code)
            self.assertLess(code.index('block:T0'), code.index('block:PVE\n'))
            self.assertLess(code.index('block:PVE\n'), code.index('VM["foundation-log-1'))
            self.assertIn('classDef heading fill:none,stroke:none,color:#1f2937', code)
        self.assertIn("Allocated, not mounted", steps[0])
        self.assertNotIn("foundation-log-2", steps[0])
        self.assertIn('block:NAS\n', steps[2])
        self.assertIn('block:Recovery:3\n', steps[2])
        self.assertLess(steps[2].index('block:T1\n'), steps[2].index('block:T0'))
        self.assertLess(steps[2].index('block:T0'), steps[2].index('block:Recovery'))
        self.assertIn('Backup -- "Read-only NAS identity" --> Evidence', steps[2])
        redundant = diagrams(root / "step-3b-redundant-intake.md")[0]
        self.assertIn('block:PVE1\n', redundant)
        self.assertIn('block:PVE2\n', redundant)
        self.assertIn('VM2["foundation-log-2 / optional', redundant)
        self.assertIn("Not installed by adding a VM", redundant)
        inventory = (UPSTREAM / "tier-0/ansible/inventory/hosts.yml.example").read_text()
        for name in ("foundation-log-1", "foundation-log-2"):
            self.assertIn(name, inventory)


if __name__ == "__main__":
    unittest.main()
