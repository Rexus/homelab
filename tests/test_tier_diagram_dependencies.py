"""Declared dependency placement and compact peers; rendering is checked separately."""

import json
import re
import unittest
import xml.etree.ElementTree as ET

import yaml

from test_tier_diagrams import (BACKUP_SVG, INTAKE_SVG, K8S_PLATFORM_SVG, LAB_SVG, PKCS11_SVG, PLATFORM_SVG, RUNNER_SVG,
                                RUNTIME_SVG, SECRETS_SVG, SIGNAL_SVG, SUPPLY_SVG, TELEMETRY_SVG, TRUST_SVG, USB_SVG,
                                diagrams, figure_sources)
from tier_repo_test_support import UPSTREAM


DOCS = UPSTREAM / "docs"


class DiagramDependencies(unittest.TestCase):
    def test_usb_api_policy_and_direct_provider_access_have_distinct_paths(self):
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        svg = ET.parse(USB_SVG).getroot()
        nodes = {node.get('id'): node for node in svg.iter() if node.get('id')}
        parents = {child: parent for parent in svg.iter() for child in parent}
        self.assertIs(parents[nodes['Clients']], svg)
        for child, parent in (('Interface', 'API'), ('Policy', 'API'), ('State', 'API'),
                              ('ProviderA', 'Pool'), ('ProviderB', 'Pool'), ('Custody', 'T0')):
            self.assertIs(parents[nodes[child]], nodes[parent])
        edges = {(edge.get('data-from'), edge.get('data-to'))
                 for edge in svg.findall('.//svg:path[@data-from]', namespace)}
        self.assertEqual(edges, {('Clients', 'Interface'), ('Clients', 'ProviderA'),
                                 ('Interface', 'Policy'), ('Policy', 'State'), ('Policy', 'ProviderA')})
        online = nodes['Online'].find('svg:rect', namespace)
        custody = nodes['Custody'].find('svg:rect', namespace)
        self.assertGreater(float(custody.get('y')), float(online.get('y')) + float(online.get('height')))

    def test_stage2_issuer_selection_keeps_root_custody_outside_connected_runtime(self):
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        svg = ET.parse(TRUST_SVG).getroot()
        nodes = {node.get('id'): node for node in svg.iter() if node.get('id')}
        parents = {child: parent for parent in svg.iter() for child in parent}
        inputs = (UPSTREAM / 'tier-0/terraform/deployments/foundation/terraform.tfvars.example').read_text()
        guests = re.findall(r'^  "([^"]+)" = \{', inputs, re.M)
        self.assertEqual(guests, ['ca-1'])
        self.assertEqual(''.join(nodes['Issuer'].find('svg:text', namespace).itertext()), 'ca-1 / issuer VM')
        self.assertNotRegex(''.join(svg.itertext()), r'\bidm-\d+\b')
        for child, parent in (('Issuer', 'Crypto'), ('Engine', 'Issuer'), ('State', 'Issuer'),
                              ('Root', 'Offline'), ('Recovery', 'Offline'), ('Offline', 'T0')):
            self.assertIs(parents[nodes[child]], nodes[parent])
        online = nodes['Online'].find('svg:rect', namespace)
        offline = nodes['Offline'].find('svg:rect', namespace)
        self.assertGreater(float(offline.get('y')), float(online.get('y')) + float(online.get('height')))
        transfer = svg.find(".//svg:path[@data-from='Root'][@data-to='Issuer']", namespace)
        self.assertIn('transfer', transfer.get('class').split())
        self.assertEqual(svg.get('viewBox'), '0 0 960 720')
        self.assertEqual(nodes['Portal'].get('class'), 'traffic')
        self.assertEqual(nodes['Offline'].get('class'), 'custody')

    def test_access_and_publication_links_identify_the_actual_caller_and_listener(self):
        cases = (
            ('05-networking/README.md', {('Internet', 'Gateways'), ('Gateways', 'Services'),
                                        ('Services', 'Endpoints'), ('AdminEntry', 'Administration')}),
            ('10-delivery/01-artifact-supply.md', {('Source', 'Registry'), ('Direct', 'Registry')}),
        )
        for path, expected in cases:
            with self.subTest(document=path):
                code = diagrams(DOCS / '01-architecture' / path)[0]
                edges = set(re.findall(r'^\s*(\w+)\s*-{2,}>\|[^|\n]*\|\s*(\w+)\s*$', code, re.M))
                self.assertEqual(edges, expected)

    def test_recovery_copies_and_keys_survive_the_protected_runtime(self):
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        svg = ET.parse(BACKUP_SVG).getroot()
        nodes = {node.get('id'): node for node in svg.iter() if node.get('id')}
        parents = {child: parent for parent in svg.iter() for child in parent}
        for name in ('Backup', 'Offsite'):
            self.assertIs(parents[nodes[name]], nodes['Copies'])
        for name in ('Source', 'Target', 'Operator', 'Custody'):
            self.assertIs(parents[nodes[name]], svg)
        def rect(name):
            shape = nodes[name].find('svg:rect', namespace)
            return {key: float(shape.get(key)) for key in ('x', 'y', 'width', 'height')}
        operator, target, copies, custody = map(rect, ('Operator', 'Target', 'Copies', 'Custody'))
        self.assertLess(operator['x'] + operator['width'], target['x'])
        self.assertGreater(custody['y'], max(target['y'] + target['height'], copies['y'] + copies['height']))
        edges = {(edge.get('data-from'), edge.get('data-to')) for edge in svg.findall('.//svg:path[@data-from]', namespace)}
        self.assertEqual(edges, {('Source', 'Backup'), ('Backup', 'Offsite'), ('Backup', 'Target'),
                                 ('Offsite', 'Target'), ('Operator', 'Target'), ('Custody', 'Target')})
        self.assertEqual(figure_sources(DOCS / '01-architecture/11-operations/04-backup-recovery.md')[0],
                         BACKUP_SVG.read_text())

    def test_external_entry_is_left_of_the_top_tier_and_reaches_real_interfaces(self):
        cases = (
            (LAB_SVG, '04-hosting/04-lab-environments.md', 'T2',
             (('Tenant', 'API'), ('Operator', 'Execution'), ('Execution', 'Nodes'))),
            (INTAKE_SVG, '07-software-intake/01-verification.md', 'T2',
             (('Proxy', 'Sources'), ('Worker', 'Proxy'), ('Consumer', 'Supply'))),
            (SUPPLY_SVG, '07-software-intake/README.md', 'T2',
             (('Proxy', 'Sources'), ('Consumers', 'Proxy'), ('Proxy', 'Cache'))),
            (SECRETS_SVG, '08-cryptography/08-secrets.md', 'T0',
             (('Consumers', 'Service'), ('Service', 'State'), ('Service', 'Logs'), ('Recovery', 'Runtime'))),
        )
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        for asset, document, highest_owner, edges in cases:
            with self.subTest(document=document):
                svg = ET.parse(asset).getroot()
                nodes = {node.get('id'): node for node in svg.iter() if node.get('id')}
                owner = nodes[highest_owner].find('svg:rect', namespace)
                top, left = float(owner.get('y')), float(owner.get('x'))
                for actor in svg.findall("svg:g[@class='actor']", namespace):
                    rect = actor.find('svg:rect', namespace)
                    self.assertGreaterEqual(float(rect.get('y')), top, actor.get('id'))
                    self.assertLess(float(rect.get('x')) + float(rect.get('width')), left, actor.get('id'))
                for name in ('T1', 'T0'):
                    if name in nodes and name != highest_owner:
                        rect = nodes[name].find('svg:rect', namespace)
                        self.assertGreater(float(rect.get('y')), top, name)
                for source, destination in edges:
                    edge = svg.find(f".//svg:path[@data-from='{source}'][@data-to='{destination}']", namespace)
                    self.assertIsNotNone(edge, (source, destination))
                self.assertEqual(figure_sources(DOCS / '01-architecture' / document)[0], asset.read_text())

    def test_proxy_clients_request_upward_and_secret_recovery_stays_below_connected_runtime(self):
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        for asset, lower, upper in ((SUPPLY_SVG, 'Consumers', 'T2'),
                                    (SECRETS_SVG, 'Recovery', 'Connected')):
            with self.subTest(asset=asset.name):
                svg = ET.parse(asset).getroot()
                nodes = {node.get('id'): node for node in svg.iter() if node.get('id')}
                lower_rect = nodes[lower].find('svg:rect', namespace)
                upper_rect = nodes[upper].find('svg:rect', namespace)
                self.assertGreater(float(lower_rect.get('y')),
                                   float(upper_rect.get('y')) + float(upper_rect.get('height')))
        svg = ET.parse(SECRETS_SVG).getroot()
        runtime = svg.find(".//svg:g[@id='Runtime']", namespace)
        self.assertIsNone(runtime.find("svg:g[@id='Recovery']", namespace))
        self.assertIsNotNone(runtime.find("svg:g[@id='State']", namespace))

    def test_host_capacity_blocks_track_the_shared_memory_profiles(self):
        profiles = json.loads((UPSTREAM / "shared/config/guest-sizes.json").read_text())["vm"]
        page = (DOCS / "01-architecture/04-hosting/01-runtime.md").read_text()
        code = next(block for block in diagrams(DOCS / "01-architecture/04-hosting/01-runtime.md")
                    if 'HostA["Physical host A' in block)
        unit = profiles["small"]["memory"]
        allocations = re.findall(r'\["(small|medium|large)"\]:(\d+)', code)
        self.assertEqual({profile for profile, _ in allocations}, {"small", "medium", "large"})
        for profile, span in allocations:
            self.assertEqual(profiles[profile]["memory"], int(span) * unit, profile)
        for profile in ("small", "medium", "large"):
            cores, memory = re.search(rf"\| `{profile}` \| (\d+) \| (\d+) GiB \|", page).groups()
            self.assertEqual(int(cores), profiles[profile]["cores"], profile)
            self.assertEqual(int(memory) * 1024, profiles[profile]["memory"], profile)

    def test_authority_maps_place_foundational_peers_to_the_right(self):
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        runtime = ET.parse(RUNTIME_SVG).getroot()
        nodes = {node.get('id'): node for node in runtime.iter() if node.get('id')}
        cluster = nodes['ControlNodes'].find('svg:rect', namespace)
        dedicated = nodes['Dedicated'].find('svg:rect', namespace)
        self.assertLess(float(cluster.get('x')) + float(cluster.get('width')), float(dedicated.get('x')))
        delivery = diagrams(DOCS / "01-architecture/10-delivery/README.md")[0]
        for peers in (("Build", "Deploy", "Source"), ("ControlDelivery", "Hosting")):
            positions = [delivery.index(f'{name}["') for name in peers]
            self.assertEqual(positions, sorted(positions))

    def test_controller_inputs_and_scoped_changes_keep_their_real_direction(self):
        code = diagrams(DOCS / "01-architecture/10-delivery/02-controllers.md")[0]
        for tier in (1, 0):
            self.assertRegex(code, rf'subgraph T{tier}\["[^\n]+\n    direction LR')
        normalized = code.replace("<br/>", " ")
        for edge in ('PF -- "Read state" --> Release', 'PF -- "Apply state" --> Platform',
                     'D -- "Promote app" --> Release',
                     'F -- "Read state" --> Approved', 'F -- "Apply state" --> Control'):
            self.assertIn(edge, normalized)
        for destination, controller, provider in (("Platform", "PF", "Release"), ("Control", "F", "Approved")):
            positions = [re.search(rf'(?m)^\s+{name}\["', code).start()
                         for name in (destination, controller, provider)]
            self.assertEqual(positions, sorted(positions))
        self.assertIn("T0 ~~~ T1", code)
        self.assertIn('T1 -. "Optional approved integration" .-> T2', code)

    def test_cluster_foundation_and_runner_providers_keep_declared_order(self):
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        svg = ET.parse(K8S_PLATFORM_SVG).getroot()
        nodes = {node.get('id'): node for node in svg.iter() if node.get('id')}
        parents = {child: parent for parent in svg.iter() for child in parent}
        for name in ('Apps', 'Reconcile', 'NodeServices'):
            self.assertIs(parents[nodes[name]], nodes['Cluster'])
        self.assertIs(parents[nodes['Existing']], nodes['T0'])
        positions = [float(nodes[name].find('svg:rect', namespace).get('x'))
                     for name in ('Apps', 'Reconcile', 'NodeServices')]
        self.assertEqual(positions, sorted(set(positions)))
        self.assertEqual(figure_sources(DOCS / '03-deployment/stage-04-kubernetes/README.md')[1],
                         K8S_PLATFORM_SVG.read_text())
        runner = diagrams(DOCS / "03-deployment/stage-09-development/step-14b-podman-runner.md")[0]
        self.assertIn('subgraph T1["Tier 1"]\n    direction LR', runner)
        self.assertIn("Runner -->|Starts jobs| Podman", runner)
        self.assertIn("Runner -->|HTTPS job polling| Git", runner)
        self.assertIn("Podman -->|HTTPS artifact publication| Registry", runner)
        self.assertLess(runner.index('subgraph VM['), runner.index('subgraph Existing['))

    def test_control_plane_and_edge_peers_stack_without_changing_instance_counts(self):
        cases = [
            ("stage-04-kubernetes/README.md", 0, "Cluster", "CP1 ~~~ CP2 ~~~ CP3"),
            ("stage-10-lab-environments/README.md", 0, "Cluster", "CP1 ~~~ CP2 ~~~ CP3"),
            ("stage-07-delivery/procedures/edge-proxy.md", 0, "Pool", "A ~~~ B ~~~ C"),
        ]
        for path, index, group, peers in cases:
            with self.subTest(document=path):
                code = diagrams(DOCS / "03-deployment" / path)[index]
                self.assertRegex(code, rf'subgraph {group}\["[^\n]+\n\s+direction TB')
                self.assertIn(peers, code)
        public = diagrams(DOCS / '03-deployment/stage-10-lab-environments/step-4b-public-https.md')[0]
        groups = yaml.safe_load((UPSTREAM / 'tier-2/ansible/inventory/hosts.yml.example').read_text())['all']['children']
        for host in groups['edge_load_balancers']['hosts']:
            self.assertEqual(len(re.findall(rf'(?<![\w-]){re.escape(host)}(?![\w-])', public)), 1)

    def test_controller_option_and_nodes_are_inside_the_runtime_they_extend(self):
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        svg = ET.parse(PLATFORM_SVG).getroot()
        nodes = {node.get('id'): node for node in svg.iter() if node.get('id')}
        parents = {child: parent for parent in svg.iter() for child in parent}
        self.assertIs(parents[nodes['Cluster']], nodes['Network'])
        self.assertIs(parents[nodes['Nodes']], nodes['Cluster'])
        self.assertIs(parents[nodes['Added']], nodes['Cluster'])
        self.assertEqual(nodes['Cluster'].get('class'), 'kubernetes')
        names = []
        positions = []
        for number in (1, 2, 3):
            node = nodes[f'CP{number}']
            self.assertIs(parents[node], nodes['Nodes'])
            names.append(''.join(node.itertext()).strip())
            positions.append(float(node.find('svg:rect', namespace).get('y')))
        inputs = (UPSTREAM / 'tier-1/terraform/deployments/kubernetes/terraform.tfvars.example').read_text()
        self.assertEqual(names, re.findall(r'^  (pctl-\d+) = \{', inputs, re.M))
        self.assertEqual(positions, sorted(set(positions)))
        controller = ''.join(nodes['Controller'].itertext())
        self.assertIn('Tier 1 Flux / platform owner', controller)
        self.assertIn('Spinnaker / app promotion', controller)
        self.assertEqual(figure_sources(DOCS / '03-deployment/stage-07-delivery/README.md')[0],
                         PLATFORM_SVG.read_text())

    def test_signal_and_hardware_views_keep_actual_endpoints_and_counts(self):
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        svg = ET.parse(SIGNAL_SVG).getroot()
        nodes = {node.get('id'): node for node in svg.iter() if node.get('id')}
        defaults = yaml.safe_load((UPSTREAM / 'tier-1/ansible/roles/observability_platform/defaults/main.yml').read_text())
        for node, key in (('Gateway', 'gateway'), ('Prepper', 'prepper'), ('Search', 'search')):
            self.assertEqual(int(nodes[node].get('data-replicas')), defaults[f'observability_{key}_replicas'])
        edges = {(edge.get('data-from'), edge.get('data-to')) for edge in svg.findall('.//svg:path[@data-from]', namespace)}
        self.assertEqual(edges, {('Apps', 'Gateway'), ('Gateway', 'Metrics'), ('Gateway', 'Prepper'), ('Prepper', 'Search')})
        svg = ET.parse(PKCS11_SVG).getroot()
        nodes = {node.get('id'): node for node in svg.iter() if node.get('id')}
        parents = {child: parent for parent in svg.iter() for child in parent}
        self.assertIs(parents[nodes['Client']], svg)
        client = nodes['Client'].find('svg:rect', namespace)
        owner = nodes['T0'].find('svg:rect', namespace)
        self.assertLess(float(client.get('x')) + float(client.get('width')), float(owner.get('x')))
        for number in (1, 2):
            self.assertIs(parents[nodes[f'H{number}']], nodes['Pool'])
            self.assertIs(parents[nodes[f'Token{number}']], nodes[f'Host{number}'])
            self.assertIs(parents[nodes[f'Host{number}']], nodes['T0'])
            network = nodes['Network'].find('svg:rect', namespace)
            host = nodes[f'Host{number}'].find('svg:rect', namespace)
            self.assertGreater(float(host.get('x')), float(network.get('x')) + float(network.get('width')))
            inputs = (UPSTREAM / 'tier-0/terraform/deployments/hsm/terraform.tfvars.example').read_text()
            member = re.search(rf'"hsm-{number}" = \{{(.*?)^  \}}', inputs, re.M | re.S)[1]
            self.assertIn(f'proxmox_node_name = "pve0{number}"', member)
            self.assertIn(f'mapping = "hsm-{number}-token"', member)
            self.assertRegex(member, r'network_zone_key\s*=\s*"cryptography"')
        edges = {(edge.get('data-from'), edge.get('data-to')) for edge in svg.findall('.//svg:path[@data-from]', namespace)}
        self.assertEqual(edges, {('Client', 'H1'), ('Client', 'H2'), ('H1', 'Token1'), ('H2', 'Token2')})
        recovery = nodes['Recovery'].find('svg:rect', namespace)
        network = nodes['Network'].find('svg:rect', namespace)
        self.assertGreater(float(recovery.get('y')), float(network.get('y')) + float(network.get('height')))

    def test_execution_owns_original_state_and_recovery_stays_outside_hosting(self):
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        svg = ET.parse(RUNNER_SVG).getroot()
        nodes = {node.get('id'): node for node in svg.iter() if node.get('id')}
        parents = {child: parent for parent in svg.iter() for child in parent}
        def rect(name):
            shape = nodes[name].find('svg:rect', namespace)
            return {key: float(shape.get(key)) for key in ('x', 'y', 'width', 'height')}
        tier1, tier0, execution, services, online, recovery = map(rect, ('T1', 'T0', 'Execution', 'Services', 'Online', 'Recovery'))
        self.assertLess(tier1['y'] + tier1['height'], tier0['y'])
        self.assertLess(execution['x'] + execution['width'], services['x'])
        self.assertGreater(recovery['y'], online['y'] + online['height'])
        self.assertIs(parents[nodes['State']], nodes['Execution'])
        self.assertIs(parents[nodes['Recovery']], nodes['T0'])
        edges = {(edge.get('data-from'), edge.get('data-to')) for edge in svg.findall('.//svg:path[@data-from]', namespace)}
        self.assertEqual(edges, {('Runner', 'State'), ('Runner', 'Vault')})
        blocks = diagrams(DOCS / "03-deployment/stage-09-development/README.md")
        sequence = next(block for block in blocks if 'participant Runner as iac-1' in block)
        self.assertIn('Runner->>Git: HTTPS job polling', sequence)
        self.assertIn('Runner->>Git: HTTPS job results', sequence)
        self.assertIn('Runner->>State: Read original inputs and resource bindings', sequence)
        self.assertIn('Runner->>State: Retain updated bindings', sequence)
        self.assertIn('iac-1 / gitlab-runner', ''.join(nodes['Runner'].itertext()))

    def test_workload_service_selects_members_with_independent_queue_volumes(self):
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        svg = ET.parse(TELEMETRY_SVG).getroot()
        nodes = {node.get('id'): node for node in svg.iter() if node.get('id')}
        tier2 = nodes['T2'].find('svg:rect', namespace)
        tier1 = nodes['T1'].find('svg:rect', namespace)
        self.assertLess(float(tier2.get('y')) + float(tier2.get('height')), float(tier1.get('y')))
        edges = {(edge.get('data-from'), edge.get('data-to')) for edge in svg.findall('.//svg:path[@data-from]', namespace)}
        self.assertEqual(edges, {('App', 'Receiver'), ('Receiver', 'A'), ('Receiver', 'B'),
                                 ('A', 'QueueA'), ('B', 'QueueB'), ('Collect', 'Gateway')})
        values = (UPSTREAM / 'tier-2/ansible/roles/workload_telemetry/templates/values.yml.j2').read_text()
        self.assertIn('fullnameOverride: otel-agent', values)
        self.assertIn('replicaCount: 2', values)
        self.assertIn('volumeClaimTemplates:', values)
        self.assertIn('metrics-client', values)
        self.assertIn('application-client', values)

    def test_vault_operator_is_external_and_recovery_is_below_connected_runtime(self):
        code = diagrams(DOCS / "03-deployment/stage-06-secrets/step-1b-vault-vm.md")[0]
        self.assertIn("flowchart LR", code)
        self.assertLess(code.index('Operator["'), code.index('subgraph T0['))
        self.assertIn('subgraph T0["Tier 0"]\n    direction BT', code)
        self.assertGreater(code.index('Recovery["'), code.index('subgraph Network['))
        self.assertIn('class Recovery custody', code)
        self.assertIn("Operator -->|Verified TLS / authorized bootstrap| VM", code)

    def test_long_workflows_wrap_rows_without_changing_chronology(self):
        cases = [
            ("README.md", ("Base", "Intake", "Trust", "Identity", "Runtime", "Logs", "Control",
                           "Delivery", "Visibility", "Workloads", "Development"),
             ("Base", "Intake", "Trust", "Logs", "Runtime", "Identity", "Control", "Delivery", "Visibility", "Development", "Workloads")),
            ("stage-10-lab-environments/README.md", ("User", "Request", "Gate", "CI"),
             ("User", "Request", "CI", "Gate")),
        ]
        for path, placement, sequence in cases:
            with self.subTest(document=path):
                code = next(code for code in diagrams(DOCS / "03-deployment" / path)
                            if "block-beta" in code)
                self.assertIn(f"block-beta\n  columns {3 if path == 'README.md' else 5}", code)
                positions = [code.index(f'{name}["') for name in placement]
                self.assertEqual(positions, sorted(positions))
                for first, second in zip(sequence, sequence[1:]):
                    self.assertIn(f"{first} --> {second}", code)


if __name__ == "__main__":
    unittest.main()
