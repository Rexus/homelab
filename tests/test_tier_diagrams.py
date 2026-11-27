"""Portable Mermaid styling, placement conventions and generated diagram assets."""

import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


PALETTE = "08-reference/diagrams/palette.json"
IDENTITY_SVG = UPSTREAM / "docs/08-reference/diagrams/identity-operations.svg"
CACHE_SVG = UPSTREAM / "architecture/generated/software-intake/solution/SoftwareIntakeSolutionDesign.svg"
LOGGING_SVG = UPSTREAM / "docs/08-reference/diagrams/protected-logging.svg"
LOGGING_ROUTING_SVGS = tuple(UPSTREAM / f"docs/08-reference/diagrams/{name}.svg"
                           for name in ("logging-receivers", "logging-sender-routing", "logging-shared-endpoint"))
LAB_SVG = UPSTREAM / "docs/08-reference/diagrams/lab-ownership.svg"
INTAKE_SVG = UPSTREAM / "docs/08-reference/diagrams/verified-intake-placement.svg"
SUPPLY_SVG = UPSTREAM / "architecture/generated/software-intake/SoftwareIntakeLogicalDesign.svg"
SECRETS_SVG = UPSTREAM / "docs/08-reference/diagrams/secrets-context.svg"
BACKUP_SVG = UPSTREAM / "docs/08-reference/diagrams/backup-recovery-context.svg"
CRYPTO_SVG = UPSTREAM / "docs/08-reference/diagrams/cryptography-operations.svg"
TRUST_SVG = UPSTREAM / "docs/08-reference/diagrams/stage2-trust.svg"
USB_SVG = UPSTREAM / "docs/08-reference/diagrams/usb-key-service-context.svg"
CA_SVG = UPSTREAM / "docs/08-reference/diagrams/certificate-authority-operations.svg"
RUNNER_SVG = UPSTREAM / "docs/08-reference/diagrams/infrastructure-runner-placement.svg"
TELEMETRY_SVG = UPSTREAM / "docs/08-reference/diagrams/workload-telemetry-placement.svg"
REFERENCE_SVG = UPSTREAM / "docs/08-reference/diagrams/reference-platform-placement.svg"
RUNTIME_SVG = UPSTREAM / "docs/08-reference/diagrams/hosting-runtime-placement.svg"
BOOT_SVG = UPSTREAM / "docs/08-reference/diagrams/boot-integrity-key-protection.svg"
OBSERVABILITY_SVG = UPSTREAM / "docs/08-reference/diagrams/observability-capabilities.svg"
CONTROL_SVG = UPSTREAM / "docs/08-reference/diagrams/control-applications-placement.svg"
OBSERVABILITY_OPERATIONS_SVG = UPSTREAM / "docs/08-reference/diagrams/observability-operations.svg"
AVAILABILITY_SVG = UPSTREAM / "docs/08-reference/diagrams/availability-cases.svg"
PLATFORM_SVG = UPSTREAM / "docs/08-reference/diagrams/platform-cluster-runtime.svg"
FLUX_OWNERSHIP_SVG = UPSTREAM / "docs/08-reference/diagrams/tier1-flux-ownership.svg"
PKCS11_SVG = UPSTREAM / "docs/08-reference/diagrams/pkcs11-provider-placement.svg"
SIGNAL_SVG = UPSTREAM / "docs/08-reference/diagrams/signal-pipelines.svg"
K8S_PLATFORM_SVG = UPSTREAM / "docs/08-reference/diagrams/kubernetes-platform.svg"
PLACEMENT_SVGS = (IDENTITY_SVG, CACHE_SVG, LOGGING_SVG, LAB_SVG, INTAKE_SVG, SUPPLY_SVG, SECRETS_SVG,
                  BACKUP_SVG, CRYPTO_SVG, TRUST_SVG, USB_SVG, CA_SVG, RUNNER_SVG, TELEMETRY_SVG, REFERENCE_SVG,
                  RUNTIME_SVG, BOOT_SVG, OBSERVABILITY_SVG, CONTROL_SVG, OBSERVABILITY_OPERATIONS_SVG, AVAILABILITY_SVG,
                  PLATFORM_SVG, FLUX_OWNERSHIP_SVG, PKCS11_SVG, SIGNAL_SVG, K8S_PLATFORM_SVG,
                  *LOGGING_ROUTING_SVGS)
FIGURES = re.compile(r"```mermaid\n(.*?)```|!\[[^\]]+\]\(([^)#]+\.svg)\)", re.DOTALL)


def diagrams(document):
    return re.findall(r"```mermaid\n(.*?)```", document.read_text(encoding="utf-8"), re.DOTALL)


def figure_sources(document):
    return [match[1] if match[1] is not None else (document.parent / match[2]).read_text(encoding="utf-8")
            for match in FIGURES.finditer(document.read_text(encoding="utf-8"))]


def luminance(colour):
    channels = [int(colour[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
              for value in channels]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(first, second):
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


class DiagramConventions(TierRepositoryTestCase):
    def test_capability_overviews_show_their_result_before_task_navigation(self):
        for folder in ('10-delivery', '11-operations'):
            for page in (UPSTREAM / 'docs/01-architecture' / folder).glob('*.md'):
                source = page.read_text()
                figure = FIGURES.search(source)
                contents = re.search(r'^## (?:Table of contents|Contents)', source, re.M)
                if figure and contents:
                    self.assertLess(figure.start(), contents.start(), str(page))

    def test_figures_do_not_silently_override_component_labels(self):
        for document in (UPSTREAM / 'docs').rglob('*.md'):
            for code in diagrams(document):
                labels = {}
                for name, label in re.findall(r'\b([A-Za-z_]\w*)\s*(?:\[\(|\{\{|\[|\{)\s*"([^"\n]+)"', code):
                    if name in labels:
                        self.assertEqual(labels[name], label, f'{document}: conflicting label for {name}')
                    labels[name] = label

    def test_colour_roles_separate_ownership_runtime_traffic_and_custody(self):
        roles = json.loads((UPSTREAM / "docs" / PALETTE).read_text())["roles"]
        distinct = ("tier0", "tier1", "tier2", "zoneEdge", "zoneServices", "zoneControl",
                    "kubernetes", "network", "traffic", "policy", "action", "group", "data", "custody")
        self.assertEqual(len({roles[name]["fill"] for name in distinct}), len(distinct))
        self.assertEqual(roles["data"]["fill"], "#eeeafa")
        self.assertEqual(roles["custody"]["fill"], "#fff2d1")
        self.assertEqual(roles["group"]["fill"], roles["replicas"]["fill"])
        for name in ("group", "deploymentGroup", "replicas"):
            self.assertEqual(roles[name]["stroke-dasharray"], "2 3")
        self.assertNotIn("stroke-dasharray", roles["network"])
        self.assertEqual(roles["traffic"]["fill"], "#d8cbb9")
        self.assertEqual(roles["traffic"]["stroke"], "#83715a")
        self.assertEqual(roles["traffic"]["color"], "#352a1e")
        for key in ("fill", "stroke", "color"):
            shades = [roles[name][key] for name in ("tier2", "tier1", "tier0")]
            for shade in shades:
                channels = [int(shade[index:index + 2], 16) for index in (1, 3, 5)]
                self.assertEqual(len(set(channels)), 1, f"{key}: {shade} must be grayscale")
            self.assertGreater(luminance(shades[0]), luminance(shades[1]), key)
            self.assertGreater(luminance(shades[1]), luminance(shades[2]), key)
        self.assertGreater(luminance(roles["zoneEdge"]["fill"]), luminance(roles["zoneServices"]["fill"]))
        self.assertGreater(luminance(roles["zoneServices"]["fill"]), luminance(roles["zoneControl"]["fill"]))
        identity = ET.parse(IDENTITY_SVG).getroot()
        nodes = {element.get('id'): element for element in identity.iter() if element.get('id')}
        for node, role in (("T0", "tier0"), ("Cluster", "kubernetes"), ("Directory", "network"), ("Ingress", "traffic"),
                           ("NetworkRule", "policy"), ("Pair", "replicas"), ("Data", "data"),
                           ("Recovery", "custody")):
            self.assertEqual(nodes[node].get('class'), role)
        for asset in PLACEMENT_SVGS:
            for selectors, declarations in re.findall(r'(?m)^\s*(\.[\w., ]+)\s*\{([^}]+)\}', asset.read_text()):
                if ',' in selectors:
                    self.assertNotRegex(declarations, r'(?<![\w-])(?:fill|stroke|color):',
                                        f'{asset}: shared resets must preserve semantic colours')
            for role, declarations in re.findall(r'(?m)^\s*\.([\w]+)\s*\{([^}]+)\}', asset.read_text()):
                if role in roles:
                    actual = dict(item.strip().split(':', 1) for item in declarations.split(';') if item.strip())
                    self.assertEqual({key: value.strip() for key, value in actual.items()}, roles[role])
        for document in (UPSTREAM / "docs").rglob("*.md"):
            for code in diagrams(document):
                boundaries = dict(re.findall(r'(?:subgraph\s+|block:)(\w+)\["([^"\n]+)"\]', code))
                for node, label in boundaries.items():
                    if re.search(r'\bnetwork(?:\s*/|$)|\bsubnet\b', label, re.I) and 'Kubernetes' not in label:
                        self.assertRegex(code, rf'(?m)^  class [\w,]*\b{node}\b[\w,]* network$',
                                         f'{document}: use the shared network palette')
                for names, tier in re.findall(r'(?m)^  class ([\w,]+) tier([012])$', code):
                    for node in names.split(','):
                        if node in boundaries:
                            label = boundaries[node].strip()
                            if not label:
                                heading = re.search(rf'\b{node}Title\["([^"\n]+)"\]', code)
                                self.assertIsNotNone(heading, f"{document}: name the tier boundary")
                                label = heading[1]
                            self.assertEqual(label, f'Tier {tier}',
                                             f"{document}: keep tier boundary titles to the tier name")
                for node, tier in re.findall(r'\b(T([012]))\["Tier [012]\b', code):
                    self.assertRegex(code, rf"(?m)^  class [\w,]*\b{node}\b[\w,]* tier{tier}$",
                                     f"{document}: tier colour also applies to compact block labels")

    def test_source_and_generated_figures_omit_deployment_allocations(self):
        self.generate("--repo", "architecture")
        roots = (UPSTREAM / "docs", self.root / "verify-architecture/docs/auto-docs",
                 UPSTREAM / "scripts/tier-repos/templates")
        for root in roots:
            for document in root.rglob("*.md"):
                # The allocation reference deliberately illustrates the VMID format.
                if document.name == "vmid-convention.md":
                    continue
                for code in figure_sources(document):
                    self.assertNotRegex(code, r"(?i)\b(?:vm[ _-]?id|guest[ _-]?id)\b", str(document))
                    self.assertNotRegex(code, r"(?i)\bvm:\d+\b", str(document))
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
        for asset in PLACEMENT_SVGS:
            original = ET.parse(asset).getroot()
            relative = asset.relative_to(source) if asset.is_relative_to(source) else asset.relative_to(UPSTREAM)
            copied = ET.parse(generated / relative).getroot()
            # Hyperlinks follow their owners into the generated collection; graphic semantics,
            # palette and geometry remain identical. Destination validity has its own contract test.
            for tree in (original, copied):
                for anchor in tree.iter("{http://www.w3.org/2000/svg}a"):
                    for key in ("href", "{http://www.w3.org/1999/xlink}href"):
                        if key in anchor.attrib:
                            anchor.set(key, "relocated-owner")
            self.assertEqual(ET.tostring(original), ET.tostring(copied))
        checked = 0
        for document in source.rglob("*.md"):
            blocks = diagrams(document)
            self.assertEqual(blocks, diagrams(generated / document.relative_to(source)), str(document))
            for code in blocks:
                if not re.search(r"(?m)^(?:flowchart|block-beta)\b", code):
                    continue
                definitions = dict(re.findall(r"(?m)^  classDef (\w+) (.+)$", code))
                self.assertIn("default", definitions, str(document))
                layout_styles = re.findall(r'(?m)^\s*(?:style|linkStyle)\s[^\n]*', code)
                for style in layout_styles:
                    self.assertEqual(style.strip(), 'style Layout fill:none,stroke:none', str(document))
                    self.assertIn('subgraph Layout[" "]', code, str(document))
                for role, declarations in definitions.items():
                    self.assertIn(role, palette["roles"], str(document))
                    actual = dict(item.split(":", 1) for item in declarations.split(","))
                    self.assertEqual(actual, palette["roles"][role], f"{document}: {role}")
                for role in re.findall(r"(?m)^  class [\w,]+ (\w+)$", code):
                    self.assertIn(role, definitions, str(document))
                initializer = re.search(r"%%\{init: (.+)\}%%", code)
                self.assertIsNotNone(initializer, str(document))
                config = json.loads(initializer[1])
                self.assertEqual(config["theme"], "base")
                self.assertEqual(config['fontFamily'], 'Arial, sans-serif')
                self.assertEqual(config['themeVariables']['fontFamily'], config['fontFamily'])
                self.assertEqual(config['themeVariables']['fontSize'], '14px')
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
                     diagrams(root / "04-hosting/03-kubernetes.md")[0]):
            self.assertRegex(code, r"(?m)^(?:block-beta|flowchart TB)$")
            order = [re.search(rf'\bT{tier}(?:\[|\n)', code).start() for tier in (2, 1, 0)]
            self.assertEqual(order, sorted(order))
            self.assertNotIn("-->", code)
            self.assertNotIn("---", code)
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        runtime = ET.parse(RUNTIME_SVG).getroot()
        nodes = {node.get('id'): node for node in runtime.iter() if node.get('id')}
        rows = [nodes[f'T{tier}'].find('svg:rect', namespace) for tier in (2, 1, 0)]
        for upper, lower in zip(rows, rows[1:]):
            self.assertLess(float(upper.get('y')) + float(upper.get('height')), float(lower.get('y')))
        self.assertFalse(runtime.findall('.//svg:path[@data-from]', namespace))
        self.assertLess(layers.index('Edge["'), layers.index('Application["'))
        self.assertLess(layers.index('Application["'), layers.index('Control["'))
        identity = diagrams(root / "09-identity/README.md")[0]
        self.assertIn('subgraph T0["Tier 0"]', identity)
        self.assertIn("Consumers -->|OIDC sign-in| Ingress", identity)
        self.assertIn("class Cluster kubernetes", identity)
        self.assertLess(identity.index('subgraph Cluster['), identity.index('subgraph Directory['))
        self.assertIn("IdPNamespace -->|LDAPS| Directory", identity)

    def test_domain_views_group_authority_and_separate_offline_custody(self):
        root = UPSTREAM / "docs/01-architecture"
        for name in ("08-cryptography/README.md", "10-delivery/README.md"):
            code = diagrams(root / name)[0]
            boundary = "block:T" if "block-beta" in code else "subgraph T"
            order = [code.index(f"{boundary}{tier}") for tier in (2, 1, 0)]
            self.assertEqual(order, sorted(order), name)
            self.assertEqual(code.count(f"{boundary}0"), 1, name)
        crypto = diagrams(root / "08-cryptography/README.md")[0]
        self.assertLess(crypto.index('subgraph T0['), crypto.index('Root["'))
        self.assertGreater(crypto.index('Root["'), crypto.index('Identity["'))
        self.assertIn("Root -. Signed intermediate certificates .-> Online", crypto)
        self.assertIn('subgraph Issuers["Issuing authorities"]', crypto)
        self.assertIn('class Root custody', crypto)
        controllers = diagrams(root / "10-delivery/02-controllers.md")[0]
        self.assertIn("flowchart BT", controllers)
        self.assertIn("T0 ~~~ T1", controllers)
        self.assertIn('T1 -. "Optional approved integration" .-> T2', controllers)
        self.assertEqual(controllers.count('subgraph T0["'), 1)
        for name in ("08-cryptography/03-hsm-selection.md", "08-cryptography/05-network-hsm.md",
                     "08-cryptography/06-vault-seal.md"):
            for code in diagrams(root / name):
                if "sequenceDiagram" in code:
                    continue  # Request timelines do not repeat the complete custody placement map.
                self.assertIn('subgraph T0[', code, name)
                self.assertRegex(code, r'(?i)offline (?:recovery|backup) custody', name)
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        telemetry = ET.parse(OBSERVABILITY_SVG).getroot()
        nodes = {node.get('id'): node for node in telemetry.iter() if node.get('id')}
        parents = {child: parent for parent in telemetry.iter() for child in parent}
        self.assertIs(parents[nodes['Evidence']], nodes['T0'])
        self.assertIs(parents[nodes['Critical']], nodes['T0'])
        self.assertIs(parents[nodes['Cluster']], nodes['T1'])
        sequence = next(code for code in diagrams(root / '11-operations/03-observability.md')
                        if 'participant Evidence as Protected evidence intake' in code)
        self.assertIn('Producers->>Evidence: Authenticated security records', sequence)
        self.assertIn('Producers->>Gateway: Authenticated OTLP signals', sequence)
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
        root = UPSTREAM / "docs/03-deployment/stage-03-logging"
        tier = UPSTREAM / "tier-0"
        inventory = yaml.safe_load((tier / "ansible/inventory/hosts.yml.example").read_text())
        hosts = inventory["all"]["children"]["foundation_logging"]["hosts"]
        self.assertEqual(len(hosts), 1)
        guest = next(iter(hosts))
        hardware = (tier / "terraform/deployments/syslog/terraform.tfvars.example").read_text()
        self.assertIn(f'  "{guest}" = {{', hardware)
        defaults = yaml.safe_load((tier / "ansible/roles/syslog_ng/defaults/main.yml").read_text())
        steps = figure_sources(root / "README.md")
        self.assertEqual(len(steps), 4)
        archive, provisioning, collection, enrollment = steps
        self.assertIn('sequenceDiagram', enrollment)
        self.assertIn('approve', enrollment.lower())
        self.assertEqual(archive, LOGGING_SVG.read_text())
        for code in (provisioning, collection):
            self.assertIn("flowchart", code)
            self.assertIn('subgraph T0["', code)
            self.assertIn('Tier 0', code)
            self.assertIn(guest, code)
            self.assertNotRegex(code, r'(?m)^\s*space(?::\d+)?(?:\s|$)')
        self.assertIn("Guarded filesystem<br/>UUID mount", provisioning)
        self.assertIn('interface     = "scsi1"', hardware)
        self.assertIn('scsi1 / local data disk', provisioning)
        self.assertIn('subgraph PVE["Proxmox Host"]', provisioning)
        for code in (collection,):
            self.assertIn('subgraph Network["Management Network / management"]', code)
            self.assertNotIn('subgraph PVE[', code)
        self.assertIn(f'TLS {defaults["syslog_ng_tls_port"]}', collection)
        self.assertNotIn("log-2", provisioning)
        redundant = ET.fromstring(figure_sources(root / "step-6b-redundant-intake.md")[0])
        nodes = {node.get('id'): node for node in redundant.iter() if node.get('id')}
        self.assertIn('Proxmox host A', ''.join(nodes['PVE1'].itertext()))
        self.assertIn('Proxmox host B', ''.join(nodes['PVE2'].itertext()))
        self.assertEqual(nodes['Placement'].get('class'), 'deploymentGroup')
        for receiver in ('VM1', 'VM2'):
            self.assertIn('management', ''.join(nodes[receiver].itertext()))
        self.assertIn(guest, ''.join(nodes['VM1'].itertext()))
        self.assertIn('log-2 / optional', ''.join(nodes['VM2'].itertext()))
        self.assertIn('# "log-2"', hardware)
        self.assertIn('Project integration', ''.join(nodes['Commit'].itertext()))
        alternate = redundant.find(".//{http://www.w3.org/2000/svg}path[@data-from='Sources'][@data-to='VM2']")
        self.assertIn('manual', alternate.get('class').split())
        inventory = (UPSTREAM / "tier-0/ansible/inventory/hosts.yml.example").read_text()
        for name in (guest, "log-2"):
            self.assertIn(name, inventory)

    def test_directory_peers_stack_and_issuers_remain_foundational(self):
        root = UPSTREAM / "docs"
        identity = diagrams(root / "01-architecture/09-identity/README.md")[0]
        self.assertIn('subgraph Directory["Identity Network / identity"]', identity)
        self.assertIn('Primary["Directory primary"]', identity)
        self.assertIn('Replica["Directory replica"]', identity)
        self.assertIn('Primary <-->|Replication| Replica', identity)
        self.assertIn('class Pair replicas', identity)
        self.assertIn('Ingress{{"HTTPS sign-in', identity)
        directory = diagrams(root / "03-deployment/stage-05-identity/README.md")[0]
        self.assertIn('subgraph Identity["Identity Network / identity"]', directory)
        self.assertIn('subgraph Crypto["Cryptography Network / cryptography"]', directory)
        self.assertIn('Identity ~~~ Crypto', directory)
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        control = ET.parse(CONTROL_SVG).getroot()
        nodes = {node.get('id'): node for node in control.iter() if node.get('id')}
        heights = [float(nodes[name].find('svg:rect', namespace).get('y'))
                   for name in ('IdentityNetwork', 'ManagementNetwork', 'CryptoNetwork')]
        self.assertEqual(heights, sorted(heights))
        self.assertIn('idm-1 / idm-2', ''.join(nodes['Identity'].itertext()))
        federation = ET.fromstring(figure_sources(root / "03-deployment/stage-05-identity/README.md")[1])
        replication = federation.find(".//{http://www.w3.org/2000/svg}path[@data-from='Primary'][@data-to='Replica']")
        self.assertIn('bidirectional', replication.get('class').split())

    def test_queries_enter_from_readers_and_alerts_retain_real_flow(self):
        root = UPSTREAM / "docs"
        access = next(code for code in diagrams(root / "03-deployment/stage-08-observability/README.md")
                      if 'participant Reader as Authorized reader' in code)
        self.assertIn('sequenceDiagram', access)
        for edge in ('Reader->>Search: Scoped log / trace query',
                     'Reader->>Metrics: Read-only metric query',
                     'Reader->>Diagnostics: Operational diagnostics'):
            self.assertIn(edge, access)
        self.assertNotIn('Read-only results| Reader', access)
        alerts = diagrams(root / "03-deployment/stage-06-secrets/procedures/independent-monitoring.md")[2]
        self.assertIn('flowchart RL', alerts)
        self.assertIn('Watch -->|Missing heartbeat alert| Admin', alerts)
        self.assertIn('Log -->|Configured heartbeat| Watch', alerts)
        external = re.search(r'subgraph External\[.*?\n  end', alerts, re.DOTALL)[0]
        self.assertNotIn('Admin[', external)

    def test_logging_diagrams_link_to_the_owning_iac_at_each_step(self):
        root = UPSTREAM / "docs/03-deployment/stage-03-logging"
        recipes = "../../../tier-0/ansible/playbooks/deployment/"
        main = (root / 'README.md').read_text()
        # The concise main route names the real inputs/combined command, then
        # links focused storage/custody procedures instead of repeating recipes.
        for input_name in ('terraform/deployments/syslog/terraform.tfvars', 'ansible/inventory/hosts.yml',
                           'ansible/group_vars/syslog.yml', 'ansible/group_vars/logging_producers.yml'):
            self.assertIn(input_name, main)
            self.assertTrue((UPSTREAM / 'tier-0' / (input_name + '.example')).is_file())
        self.assertIn('bash scripts/deploy.sh syslog\n', main)
        for related in ('step-7a-nas-archive.md', 'procedures/receiver.md', 'procedures/producer-trust.md'):
            self.assertIn(f']({related}', main)
            self.assertTrue((root / related).is_file())
        storage = (root / 'procedures/receiver.md').read_text()
        self.assertIn('../../../../tier-0/ansible/roles/syslog_ng/tasks/storage.yml', storage)
        archive = (root / 'step-7a-nas-archive.md').read_text()
        for recipe in ('logging-archive.yml', 'logging-backup.yml'):
            self.assertIn('ansible/playbooks/deployment/' + recipe, archive)
            self.assertTrue((UPSTREAM / 'tier-0/ansible/playbooks/deployment' / recipe).is_file())
        workflow = yaml.safe_load((UPSTREAM / 'tier-0/ansible/playbooks/deployment/logging-workflow.yml').read_text())
        roles = [task['ansible.builtin.include_role'] for play in workflow for task in play.get('tasks', [])
                 if 'ansible.builtin.include_role' in task]
        for role in ({'name': 'syslog_ng', 'tasks_from': 'storage'},
                     {'name': 'logging_workflow', 'tasks_from': 'verify'}):
            self.assertIn(role, roles)
        expected = {
            "step-6b-redundant-intake.md": [[
                "../../../tier-0/terraform/deployments/syslog/terraform.tfvars.example",
                "../../../tier-0/ansible/inventory/hosts.yml.example",
                "../../../tier-0/ansible/group_vars/syslog.yml.example",
                recipes + "foundation-logging.yml",
            ], [
                "../../../shared/ansible/roles/log_forwarder/templates/sender.conf.j2",
                "../../../tier-0/ansible/group_vars/syslog.yml.example",
            ], [
                recipes + "foundation-logging.yml",
                "../../../shared/ansible/roles/log_forwarder/templates/sender.conf.j2",
            ]],
        }
        for filename, steps in expected.items():
            document = root / filename
            source = document.read_text()
            captions = [source[figure.end():].lstrip().split('\n\n', 1)[0]
                        for figure in FIGURES.finditer(source)]
            self.assertEqual(len(captions), len(steps), filename)
            for caption, paths in zip(captions, steps):
                for path in paths:
                    self.assertIn(f"]({path})", caption)
                    self.assertTrue((document.parent / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
