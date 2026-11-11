"""Portable Mermaid styling, placement conventions and generated diagram assets."""

import hashlib
import json
import re
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


PALETTE = "08-reference/diagrams/palette.json"


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
    def test_source_and_generated_figures_omit_deployment_allocations(self):
        self.generate("--repo", "architecture")
        roots = (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs",
                 UPSTREAM / "scripts/tier-repos/templates")
        for root in roots:
            for document in root.rglob("*.md"):
                for code in diagrams(document):
                    self.assertNotRegex(code, r"(?i)\b(?:vm[ _-]?id|guest[ _-]?id)\b", str(document))
                    self.assertNotRegex(code, r"\b\d+(?:\.\d+){3}(?:/\d+)?\b", str(document))
                    self.assertNotRegex(code, r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b", str(document))
                    if re.search(r"(?m)^(?:flowchart|block-beta)\b", code):
                        self.assertNotRegex(code, r"\b\d+\s*(?:GiB|GB|MiB|MB|vCPUs?)\b", str(document))

    def test_palette_pairs_are_legible_on_light_and_dark_pages(self):
        palette = json.loads((UPSTREAM / "docs" / PALETTE).read_text())
        for role, style in palette["roles"].items():
            self.assertGreaterEqual(contrast(style["color"], style["fill"]), 4.5, role)
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

    def test_palette_refresh_preserves_edits_and_restores_missing_assets(self):
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
        self.assertEqual(target.read_bytes(), original)

    def test_placement_grids_keep_tiers_ordered_without_traffic_arrows(self):
        root = UPSTREAM / "docs/01-architecture"
        overview = diagrams(root / "README.md")
        layers = diagrams(root / "05-networking/README.md")[0]
        for code in (overview[0], diagrams(root / "02-organization/01-tier-ownership.md")[0],
                     diagrams(root / "04-hosting/03-kubernetes.md")[0],
                     diagrams(root / "04-hosting/01-runtime.md")[0]):
            self.assertIn("block-beta", code)
            order = [code.index(f'T{tier}["') for tier in (2, 1, 0)]
            self.assertEqual(order, sorted(order))
            self.assertNotIn("-->", code)
            self.assertNotIn("---", code)
        self.assertLess(layers.index('Edge["'), layers.index('Application["'))
        self.assertLess(layers.index('Application["'), layers.index('Control["'))
        identity = diagrams(root / "09-identity/README.md")[0]
        self.assertIn('T0Title["Tier 0 / Control layer"]', identity)
        self.assertIn("T2 ~~~ T1", identity)
        self.assertIn("T1 -->|OIDC to the IdP| T0", identity)
        self.assertIn("class Cluster runtime", identity)
        self.assertLess(identity.index('subgraph Cluster['), identity.index('subgraph Directory['))
        self.assertIn("Cluster -->|Protected LDAP federation| Directory", identity)

    def test_domain_views_group_authority_and_separate_offline_custody(self):
        root = UPSTREAM / "docs/01-architecture"
        for name in ("08-cryptography/README.md", "10-delivery/README.md"):
            code = diagrams(root / name)[0]
            boundary = "block:T" if "block-beta" in code else "subgraph T"
            order = [code.index(f"{boundary}{tier}") for tier in (2, 1, 0)]
            self.assertEqual(order, sorted(order), name)
            self.assertEqual(code.count(f"{boundary}0"), 1, name)
        crypto = diagrams(root / "08-cryptography/README.md")[0]
        self.assertLess(crypto.index("block:T0"), crypto.index('Root["'))
        self.assertGreater(crypto.index('Root["'), crypto.index('Identity["'))
        self.assertIn("Root -.-> Issuer", crypto)
        self.assertIn("Root -.-> Identity", crypto)
        controllers = diagrams(root / "10-delivery/02-controllers.md")[0]
        self.assertIn("T2 ~~~ T1 ~~~ T0", controllers)
        self.assertEqual(controllers.count('subgraph T0["'), 1)
        for name in ("08-cryptography/03-hsm-selection.md", "08-cryptography/05-network-hsm.md",
                     "08-cryptography/06-vault-seal.md"):
            for code in diagrams(root / name):
                self.assertIn("block:T0", code, name)
                self.assertRegex(code, r'(?i)offline (?:recovery|backup) custody', name)
        telemetry = diagrams(root / "11-operations/03-observability.md")[0]
        for tier in (2, 1):
            self.assertIn(f"T{tier} -->|Security / audit submissions| T0", telemetry)
        self.assertIn('subgraph T0["Tier 0 / Security Logging and Audit"]', telemetry)
        self.assertIn('Critical["Independent health / alerts"]', telemetry)
        self.assertIn('subgraph Cluster["Platform Kubernetes / separate workloads"]', telemetry)
        retention = diagrams(root / "11-operations/02-log-retention.md")[0]
        self.assertIn('subgraph T0["', retention)
        self.assertIn("Intake -->|Verified checkpoints| Protection", retention)
        self.assertIn("Storage -->|Backup| Recovery", retention)

    def test_charts_and_sequence_keep_theme_aware_text(self):
        root = UPSTREAM / "docs/01-architecture"
        charts = [code for code in diagrams(root / "01-background/README.md") if "xychart-beta" in code]
        self.assertEqual(len(charts), 2)
        palette = json.loads((UPSTREAM / "docs" / PALETTE).read_text())
        for chart in charts:
            initializer = re.search(r"%%\{init: (.+)\}%%", chart)
            config = json.loads(initializer[1])
            self.assertNotIn("theme", config)
            colours = config["themeVariables"]["xyChart"]["plotColorPalette"].split(",")
            self.assertEqual(colours, palette["charts"]["series"])
        sequence = next(code for code in diagrams(root / "09-identity/README.md") if "sequenceDiagram" in code)
        self.assertIn("sequenceDiagram", sequence)
        self.assertNotIn("theme", sequence)
        self.assertIn("rect rgba(", sequence)

    def test_logging_steps_keep_deployment_boundaries_and_inventory_names(self):
        root = UPSTREAM / "docs/03-deployment/stage-2-logging"
        tier = UPSTREAM / "tier-0"
        inventory = yaml.safe_load((tier / "ansible/inventory/hosts.yml.example").read_text())
        hosts = inventory["all"]["children"]["foundation_logging"]["hosts"]
        self.assertEqual(len(hosts), 1)
        guest = next(iter(hosts))
        hardware = (tier / "terraform/deployments/syslog/terraform.tfvars.example").read_text()
        self.assertIn(f'  "{guest}" = {{', hardware)
        defaults = yaml.safe_load((tier / "ansible/roles/syslog_ng/defaults/main.yml").read_text())
        steps = diagrams(root / "README.md")
        self.assertEqual(len(steps), 3)
        for code in steps:
            self.assertIn("flowchart", code)
            self.assertIn('subgraph T0["', code)
            self.assertIn('Tier 0 / Control layer', code)
            self.assertIn('subgraph PVE["', code)
            self.assertIn(f'VM["{guest}<br/>', code)
            self.assertLess(code.index('subgraph T0['), code.index('subgraph PVE['))
            self.assertLess(code.index('subgraph PVE['), code.index(f'VM["{guest}<br/>'))
            self.assertNotRegex(code, r'(?m)^\s*space(?::\d+)?(?:\s|$)')
        self.assertIn("Guarded filesystem<br/>UUID mount", steps[0])
        self.assertIn('interface     = "scsi1"', hardware)
        self.assertIn('scsi1 / local data disk', steps[0])
        self.assertIn(f'TLS {defaults["syslog_ng_tls_port"]}', steps[1])
        self.assertNotIn("log-2", steps[0])
        self.assertIn('subgraph NAS["', steps[2])
        self.assertIn('Existing NAS / independent custody', steps[2])
        self.assertIn('subgraph Recovery["', steps[2])
        self.assertIn('Existing Tier 0 recovery host', steps[2])
        self.assertLess(steps[2].index('subgraph T1['), steps[2].index('subgraph T0['))
        self.assertLess(steps[2].index('subgraph T0['), steps[2].index('subgraph Recovery['))
        self.assertIn('    subgraph Recovery[', steps[2])
        self.assertIn('Placement -->|Read-only NAS archive pull| Recovery', steps[2])
        redundant = diagrams(root / "step-3b-redundant-intake.md")[0]
        self.assertIn('subgraph PVE1["', redundant)
        self.assertIn('subgraph PVE2["', redundant)
        self.assertIn(f'VM1["{guest}<br/>', redundant)
        self.assertIn('VM2["log-2 / optional', redundant)
        self.assertIn('# "log-2"', hardware)
        self.assertIn("Not installed by adding a VM", redundant)
        inventory = (UPSTREAM / "tier-0/ansible/inventory/hosts.yml.example").read_text()
        for name in (guest, "log-2"):
            self.assertIn(name, inventory)

    def test_directory_peers_stack_and_issuers_remain_foundational(self):
        root = UPSTREAM / "docs"
        identity = diagrams(root / "01-architecture/09-identity/README.md")[0]
        self.assertIn('subgraph Directory["Directory authority / identity network"]\n        direction TB', identity)
        self.assertIn('Primary["Directory primary"] <--> Replica["Directory replica"]', identity)
        trust = diagrams(root / "03-deployment/stage-3-trust/README.md")[0]
        self.assertLess(trust.index('subgraph Identity['), trust.index('subgraph Crypto['))
        self.assertIn('Identity ~~~ Crypto', trust)
        directory = diagrams(root / "03-deployment/stage-5-identity/README.md")[0]
        self.assertIn('subgraph PVE["Existing Proxmox hosts"]\n      direction LR', directory)
        self.assertIn('Identity ~~~ ExistingCA', directory)
        control = diagrams(root / "03-deployment/stage-6-secrets/README.md")[0]
        self.assertIn('Identity ~~~ Log ~~~ Issuer', control)
        self.assertIn('idm-1 / idm-2<br/>FreeIPA pair', control)
        federation = diagrams(root / "03-deployment/stage-5-identity/README.md")[1]
        self.assertIn('Primary <-->|Replication| Replica', federation)

    def test_queries_enter_from_readers_and_alerts_retain_real_flow(self):
        root = UPSTREAM / "docs"
        access = diagrams(root / "03-deployment/stage-8-observability/README.md")[3]
        self.assertIn('flowchart LR', access)
        self.assertIn('Reader -->|Read-only queries| T1', access)
        self.assertNotIn('Read-only results| Reader', access)
        alerts = diagrams(root / "03-deployment/stage-6-secrets/procedures/independent-monitoring.md")[2]
        self.assertIn('flowchart RL', alerts)
        self.assertIn('Watch -->|Missing heartbeat alert| Admin', alerts)
        self.assertIn('Log -->|Configured heartbeat| Watch', alerts)
        external = re.search(r'subgraph External\[.*?\n  end', alerts, re.DOTALL)[0]
        self.assertNotIn('Admin[', external)

    def test_logging_diagrams_link_to_the_owning_iac_at_each_step(self):
        root = UPSTREAM / "docs/03-deployment/stage-2-logging"
        recipes = "../../../tier-0/ansible/playbooks/deployment/"
        expected = {
            "README.md": [
                ["../../../tier-0/terraform/deployments/syslog/terraform.tfvars.example",
                 "../../../tier-0/ansible/inventory/hosts.yml.example"],
                [recipes + "foundation-logging.yml", recipes + "logging-producers.yml",
                 "../../../shared/ansible/roles/log_forwarder/tasks/main.yml"],
                [recipes + "logging-archive.yml", recipes + "logging-backup.yml"],
            ],
            "step-3b-redundant-intake.md": [[
                "../../../tier-0/terraform/deployments/syslog/terraform.tfvars.example",
                "../../../tier-0/ansible/inventory/hosts.yml.example",
                "../../../tier-0/ansible/group_vars/syslog.yml.example",
                recipes + "foundation-logging.yml",
            ]],
        }
        for filename, steps in expected.items():
            document = root / filename
            captions = re.findall(r"```\s+\*\*IaC:\*\*(.*?)(?:\n\s*\n|$)",
                                  document.read_text(), re.DOTALL)
            self.assertEqual(len(captions), len(steps), filename)
            for caption, paths in zip(captions, steps):
                for path in paths:
                    self.assertIn(f"]({path})", caption)
                    self.assertTrue((document.parent / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
