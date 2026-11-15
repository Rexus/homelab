"""Architecture abstractions and deployment pictures retain their source contracts."""

import re
import unittest
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

import yaml

from tier_repo_test_support import UPSTREAM
from test_tier_diagrams import CACHE_SVG, FIGURES, IDENTITY_SVG, LOGGING_SVG, figure_sources


DOCS = UPSTREAM / "docs"
FENCES = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
LINKS = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def inventory_groups(tier):
    path = UPSTREAM / tier / "ansible/inventory/hosts.yml.example"
    return yaml.safe_load(path.read_text())["all"]["children"]


def guest_names(groups):
    return {name for group in groups.values() for name in (group.get("hosts") or {})}


class DeploymentViews(unittest.TestCase):
    def test_logging_layout_separates_intake_nas_backup_and_offline_custody(self):
        svg = ET.parse(LOGGING_SVG).getroot()
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        nodes = {element.get('id'): element for element in svg.iter() if element.get('id')}
        parents = {child: parent for parent in svg.iter() for child in parent}

        def ancestors(node):
            result = []
            while node in parents:
                node = parents[node]
                if node.get('id'):
                    result.append(node.get('id'))
            return result

        def rect(name):
            shape = nodes[name].find('svg:rect', namespace)
            return {key: float(shape.get(key)) for key in ('x', 'y', 'width', 'height')}

        receiver, nas, backup = map(rect, ('Receiver', 'NAS', 'RecoveryHost'))
        self.assertLess(receiver['x'] + receiver['width'], nas['x'])
        self.assertLess(nas['x'] + nas['width'], backup['x'])
        self.assertEqual(ancestors(nodes['Producers']), [])
        producer, owner = map(rect, ('Producers', 'T0'))
        self.assertLess(producer['x'] + producer['width'], owner['x'])
        self.assertIn('Pipeline', ancestors(nodes['Receiver']))
        self.assertIn('Receiver', ancestors(nodes['Local']))
        self.assertIn('NAS', ancestors(nodes['Chunks']))
        self.assertIn('NAS', ancestors(nodes['Snapshots']))
        self.assertIn('RecoveryHost', ancestors(nodes['Copy']))
        self.assertNotIn('NAS', ancestors(nodes['RecoveryHost']))
        self.assertIn('T0', ancestors(nodes['Recovery']))
        self.assertNotIn('Pipeline', ancestors(nodes['Recovery']))
        self.assertNotIn('Watchdog', nodes)
        self.assertEqual(nodes['NAS'].get('class'), 'data')
        online, offline = map(rect, ('Pipeline', 'Recovery'))
        self.assertGreater(offline['y'], online['y'] + online['height'])
        paths = {(path.get('data-from'), path.get('data-to')): path
                 for path in svg.findall('.//svg:path[@data-from]', namespace)}
        self.assertEqual(set(paths), {
            ('Producers', 'Log'), ('Log', 'Local'), ('Receiver', 'Chunks'),
            ('Chunks', 'Snapshots'), ('Pull', 'Chunks'), ('Pull', 'Copy'),
            ('Copy', 'Kit'),
        })
        self.assertIn('manual', paths['Copy', 'Kit'].get('class').split())
        self.assertEqual(figure_sources(DOCS / '05-operations/06-resilience/protected-logging.md')[0],
                         LOGGING_SVG.read_text())
        health = next(code for code in FENCES.findall((DOCS / '05-operations/06-resilience/protected-logging.md').read_text())
                      if 'participant Watchdog as External watchdog' in code)
        for interaction in ('Archive->>Watchdog: Checkpoint success ping',
                            'Backup->>NAS: Read and verify checkpoint with read-only access',
                            'Backup->>Watchdog: Backup success ping'):
            self.assertIn(interaction, health)

    def test_cache_requests_enter_from_below_and_leave_to_the_upstream_on_the_left(self):
        svg = ET.parse(CACHE_SVG).getroot()
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        nodes = {element.get('id'): element for element in svg.iter() if element.get('id')}
        parents = {child: parent for parent in svg.iter() for child in parent}

        def ancestors(node):
            result = []
            while node in parents:
                node = parents[node]
                if node.get('id'):
                    result.append(node.get('id'))
            return result

        def rect(name):
            shape = nodes[name].find('svg:rect', namespace)
            return {key: float(shape.get(key)) for key in ('x', 'y', 'width', 'height')}

        owner, clients, upstream = map(rect, ('T2', 'Consumers', 'Upstream'))
        self.assertEqual(ancestors(nodes['Consumers']), [])
        self.assertEqual(ancestors(nodes['Upstream']), [])
        self.assertGreater(clients['y'], owner['y'] + owner['height'])
        self.assertLess(upstream['x'] + upstream['width'], owner['x'])
        for name in ('VIP', 'Pair'):
            self.assertIn('T2', ancestors(nodes[name]))
            self.assertIn('Edge', ancestors(nodes[name]))
        paths = {(path.get('data-from'), path.get('data-to')): path
                 for path in svg.findall('.//svg:path[@data-from]', namespace)}
        self.assertIn(('VIP', 'Pair'), paths)
        for edge, axis in ((('Consumers', 'VIP'), 1), (('Pair', 'Upstream'), 0)):
            path = paths[edge]
            self.assertIn('connection', path.get('class').split())
            values = [float(value) for value in re.findall(r'-?\d+(?:\.\d+)?', path.get('d'))]
            self.assertLess(values[-2 + axis], values[axis], f'{edge}: preserve request direction')
        for relative in ('03-deployment/stage-01-software-intake/README.md',
                         '05-operations/02-software-intake/README.md'):
            self.assertEqual(figure_sources(DOCS / relative)[0], CACHE_SVG.read_text())

    def test_identity_networks_namespace_and_incoming_rule_have_distinct_scopes(self):
        cases = (
            ("01-architecture/09-identity/README.md", 0),
        )
        for relative, index in cases:
            code = FENCES.findall((DOCS / relative).read_text())[index]
            stack, scopes = [], {}
            for line in code.splitlines():
                group = re.match(r'\s*subgraph (\w+)\[', line)
                node = re.match(r'\s*(\w+)(?:\[|\{)', line)
                if group:
                    scopes[group[1]] = tuple(stack)
                    stack.append(group[1])
                elif line.strip() == 'end':
                    stack.pop()
                elif node:
                    scopes[node[1]] = tuple(stack)
            self.assertEqual(scopes['NetworkRule'], ())
            self.assertIn('T0', scopes['Ingress'])
            self.assertIn('Cluster', scopes['Ingress'])
            self.assertIn('Cluster', scopes['IdPNamespace'])
            self.assertIn('IdPNamespace', scopes['Data'])
            self.assertNotIn('Cluster', scopes['Directory'])
            self.assertIn('IdentityServices', scopes['Directory'])
            self.assertIn('class IdentityServices deploymentGroup', code)
            self.assertIn('class NetworkRule policy', code)
            self.assertIn('NetworkRule -. Governs HTTPS .-> Ingress', code)
            self.assertNotRegex(code, r'(?m)^\s*NetworkRule\s+(?:-->|<-->|--)')
            self.assertRegex(code, r'(?m)^  class Ingress(?:,Service)? traffic$')
            self.assertNotIn('Identity service networks', code)

    def test_identity_operations_storage_and_offline_custody_have_fixed_vertical_placement(self):
        svg = ET.parse(IDENTITY_SVG).getroot()
        namespace = {'svg': 'http://www.w3.org/2000/svg'}
        nodes = {element.get('id'): element for element in svg.iter() if element.get('id')}
        parents = {child: parent for parent in svg.iter() for child in parent}

        def ancestors(node):
            result = []
            while node in parents:
                node = parents[node]
                if node.get('id'):
                    result.append(node.get('id'))
            return result

        def rect(name):
            shape = nodes[name].find('svg:rect', namespace)
            return {key: float(shape.get(key)) for key in ('x', 'y', 'width', 'height')}

        self.assertEqual(ancestors(nodes['NetworkRule']), [])
        self.assertIn('Cluster', ancestors(nodes['Ingress']))
        self.assertIn('IdPNamespace', ancestors(nodes['Data']))
        self.assertIn('IdPNamespace', ancestors(nodes['Service']))
        self.assertNotIn('Cluster', ancestors(nodes['Directory']))
        self.assertIn('T0', ancestors(nodes['Recovery']))
        self.assertNotIn('IdentityServices', ancestors(nodes['Recovery']))
        app, recovery, online, owner = map(rect, ('IdP', 'Recovery', 'IdentityServices', 'T0'))
        data_path = nodes['Data'].find('svg:path', namespace).get('d')
        coordinates = [float(value) for value in re.findall(r'-?\d+(?:\.\d+)?', data_path)]
        self.assertGreater(min(coordinates[1::2]), app['y'] + app['height'])
        self.assertEqual((min(coordinates[::2]) + max(coordinates[::2])) / 2,
                         app['x'] + app['width'] / 2)
        self.assertGreater(recovery['y'], online['y'] + online['height'])
        self.assertEqual(recovery['x'], online['x'])
        self.assertEqual(recovery['width'], online['width'])
        self.assertLess(recovery['y'] + recovery['height'], owner['y'] + owner['height'])
        association = svg.find(".//svg:path[@data-from='NetworkRule']", namespace)
        self.assertEqual(association.get('data-to'), 'Ingress')
        self.assertIn('association', association.get('class').split())
        endpoints = yaml.safe_load((UPSTREAM / 'tier-0/ansible/group_vars/control_applications.yml.example').read_text())
        urls = endpoints['control_applications_ldap_url'].split()
        members = [urlsplit(url).hostname.split('.')[0] for url in urls]
        for target, name in zip(('Primary', 'Replica'), members):
            self.assertIn(name, ''.join(nodes[target].itertext()))
            self.assertIsNotNone(svg.find(f".//svg:path[@data-from='IdP'][@data-to='{target}']", namespace))
        self.assertEqual(len(urls), 2)
        for source, target in (('Ingress', 'Service'), ('Service', 'IdP')):
            self.assertIsNotNone(svg.find(f".//svg:path[@data-from='{source}'][@data-to='{target}']", namespace))
        self.assertEqual(figure_sources(DOCS / '03-deployment/stage-05-identity/README.md')[1],
                         IDENTITY_SVG.read_text())
        offline_ids = {element.get('id') for element in nodes['Recovery'].iter() if element.get('id')}
        for path in svg.findall('.//svg:path[@data-from]', namespace):
            self.assertNotIn(path.get('data-from'), offline_ids)
            self.assertNotIn(path.get('data-to'), offline_ids)

    def test_secrets_view_counts_independent_product_components(self):
        role = UPSTREAM / "tier-0/ansible/roles/control_applications"
        defaults = yaml.safe_load((role / "defaults/main.yml").read_text())
        values = (role / "templates/netbox-values.yml.j2").read_text()
        web = re.search(r"(?m)^replicaCount: (\d+)$", values)[1]
        worker = re.search(r"(?ms)^worker:\n.*?^  replicaCount: (\d+)$", values)[1]
        code = figure_sources(DOCS / "03-deployment/stage-06-secrets/README.md")[0]
        self.assertIn(f"netbox web x{web} / worker x{worker}", code)
        self.assertIn(f'vault x{defaults["control_applications_vault_replicas"]}', code)
        self.assertIn(f'netbox-db x{defaults["control_applications_database_instances"]}', code)
        node = ET.fromstring(code).find(".//{http://www.w3.org/2000/svg}g[@id='Added']")
        self.assertEqual(node.get('class'), 'group')

    def test_operating_reference_aggregates_keep_the_owned_guest_names(self):
        cases = (
            ("01-hosting/kubernetes-and-labs.md", 0, "tier-0", ("talos_control_plane", "cluster_endpoint")),
            ("02-software-intake/README.md", 0, "tier-2", ("cache",)),
            ("02-software-intake/verified-publication.md", 0, "tier-1", ("software_intake",)),
            ("03-cryptography/README.md", 0, "tier-0", ("issuing_ca", "identity_primary", "identity_replicas")),
            ("05-delivery.md", 0, "tier-1", ("development_data",)),
            ("06-resilience/protected-logging.md", 0, "tier-0", ("foundation_logging",)),
            ("06-resilience/observability.md", 1, "tier-1", ("observability",)),
        )
        for relative, index, tier, selected in cases:
            with self.subTest(page=relative):
                code = figure_sources(DOCS / "05-operations" / relative)[index]
                guest_labels = (" ".join(ET.fromstring(code).itertext()) if code.startswith('<svg')
                                else "\n".join(re.findall(r'\["([^"\n]+)"\]', code)))
                groups = inventory_groups(tier)
                for name in guest_names({key: groups[key] for key in selected}):
                    matches = re.findall(rf"(?<![\w-]){re.escape(name)}(?![\w-])", guest_labels)
                    self.assertEqual(len(matches), 1, f"{relative}: one depicted guest or named aggregate: {name}")

    def test_identity_replica_views_match_the_product_defaults(self):
        defaults = yaml.safe_load((UPSTREAM /
            "tier-0/ansible/roles/control_applications/defaults/main.yml").read_text())
        stage = ' '.join(ET.fromstring(figure_sources(DOCS / '03-deployment/stage-05-identity/README.md')[1]).itertext())
        operation = ' '.join(ET.parse(IDENTITY_SVG).getroot().itertext())
        for code in (stage, operation):
            self.assertIn(f'PostgreSQL x{defaults["control_applications_database_instances"]}', code)
            self.assertIn("control_cluster", code)
            self.assertIn("Identity Network / identity", code)
        self.assertIn(f'IdP pods x{defaults["control_applications_keycloak_replicas"]}', operation)
        ingress = (UPSTREAM /
            "tier-0/ansible/roles/control_applications/templates/ingress.yml.j2").read_text()
        self.assertIn("keycloak-http", ingress)
        self.assertIn('keycloak-http', stage)

    def test_operations_capability_entries_open_with_the_deployed_view(self):
        entries = (
            "01-hosting/README.md", "01-hosting/kubernetes-and-labs.md",
            "02-software-intake/README.md", "02-software-intake/verified-publication.md",
            "03-cryptography/README.md", "03-cryptography/certificate-authority.md",
            "04-identity.md", "05-delivery.md", "06-resilience/README.md",
            "06-resilience/protected-logging.md", "06-resilience/observability.md",
            "06-resilience/backups/postgresql.md", "06-resilience/backups/gitlab-data.md",
            "06-resilience/recovery/platform.md",
        )
        for relative in entries:
            with self.subTest(page=relative):
                page = (DOCS / "05-operations" / relative).read_text()
                figure = FIGURES.search(page)
                self.assertIsNotNone(figure, "Show the selected deployment before task/configuration tables")
                first_table = re.search(r"(?m)^\|", page)
                if first_table:
                    self.assertLess(figure.start(), first_table.start())
                caption = page[figure.end():].lstrip().splitlines()[0]
                self.assertRegex(caption, r"^(?:\*\*[^*]+:\*\* )?\*Figure(?: \d+ -|:) ")

    def test_architecture_diagrams_use_roles_not_site_guest_keys(self):
        names = set().union(*(guest_names(inventory_groups(f"tier-{tier}")) for tier in range(3)))
        documents = list((DOCS / "01-architecture").rglob("*.md"))
        self.assertTrue(documents, "Architecture correspondence check discovered no documents")
        for document in documents:
            for code in FENCES.findall(document.read_text()):
                for name in names:
                    self.assertNotRegex(code, rf"(?<![\w-]){re.escape(name)}(?![\w-])", str(document))

    def test_every_deployment_diagram_declares_scope_and_traceable_links(self):
        checked = 0
        for document in (DOCS / "03-deployment").rglob("*.md"):
            content = document.read_text()
            for fence in FIGURES.finditer(content):
                caption = content[fence.end():].lstrip().split("\n\n", 1)[0]
                self.assertRegex(caption, r"^\*\*(?:IaC|Manual|Integration|Workflow):\*\*", str(document))
                paths = LINKS.findall(caption)
                self.assertTrue(paths, str(document))
                for path in paths:
                    if not path.startswith(("https://", "http://", "#")):
                        self.assertTrue((document.parent / path.split("#", 1)[0]).exists(), path)
                if caption.startswith(("**IaC:**", "**Integration:**")):
                    self.assertTrue(any(re.search(r"/(?:tier-[012]|shared)/", path) for path in paths),
                                    str(document))
                checked += 1
        self.assertGreaterEqual(checked, 30)

    def test_deployment_resource_views_account_for_the_selected_starter_hosts(self):
        # Each row expands an actual input/inventory selection, not a second guest catalogue.
        cases = [
            ("stage-03-logging/README.md", 1, "tier-0", "syslog", ["foundation_logging"]),
            ("stage-02-trust/README.md", 0, "tier-0", "foundation",
             ["issuing_ca", "identity_primary", "identity_replicas"]),
            ("stage-02-trust/step-1b-usb-hsm.md", 0, "tier-0", "hsm", ["hsm_gateways"]),
            ("stage-05-identity/README.md", 0, "tier-0", "foundation",
             ["issuing_ca", "identity_primary", "identity_replicas"]),
            ("stage-04-kubernetes/README.md", 0, "tier-0", "kubernetes", ["talos_control_plane"]),
            ("stage-06-secrets/step-1b-vault-vm.md", 0, "tier-0", "vault", ["vault"]),
            ("stage-08-observability/step-1b-dedicated-vms.md", 0, "tier-1", "observability",
             ["observability"]),
            ("stage-07-delivery/README.md", 0, "tier-1", "kubernetes", ["talos_control_plane"]),
            ("stage-09-development/step-1b-source-control-vm.md", 0, "tier-1", "development",
             ["development_platform"]),
            ("stage-09-development/step-14b-podman-runner.md", 0, "tier-1", "podman-runner", ["podman_runner"]),
            ("stage-09-development/step-15b-image-based-linux.md", 0, "tier-0", "immutable-template",
             ["immutable_template_builders"]),
            ("stage-07-delivery/procedures/edge-proxy.md", 0, "tier-2", "edge", ["edge_load_balancers"]),
            ("stage-10-lab-environments/README.md", 0, "tier-2", "kubernetes", ["talos_control_plane"]),
            ("stage-10-lab-environments/README.md", 0, "tier-2", "lab", ["lab"]),
            ("stage-10-lab-environments/README.md", 0, "tier-0", "infrastructure-runner", ["infrastructure_runner"]),
            ("stage-01-software-intake/README.md", 0, "tier-2", "cache", ["cache"]),
        ]
        selections = {}
        for relative, index, tier, setup, selected in cases:
            with self.subTest(document=relative, setup=setup):
                code = figure_sources(DOCS / "03-deployment" / relative)[index]
                groups = inventory_groups(tier)
                hosts = guest_names({name: groups[name] for name in selected})
                selections.setdefault((relative, index), set()).update(hosts)
                inputs = (UPSTREAM / tier / f"terraform/deployments/{setup}/terraform.tfvars.example").read_text()
                self.assertTrue(hosts)
                for name in hosts:
                    self.assertRegex(inputs, rf'(?m)^\s*(?:"{re.escape(name)}"|{re.escape(name)})\s*=\s*\{{')
                    self.assertEqual(len(re.findall(rf"(?<![\w-]){re.escape(name)}(?![\w-])", code)), 1,
                                     f"{relative}: one depicted instance per guest key: {name}")
                self.assertIn(f"Tier {tier[-1]}", code)
        all_hosts = set().union(*(guest_names(inventory_groups(f"tier-{tier}")) for tier in range(3)))
        for (relative, index), selected in selections.items():
            code = figure_sources(DOCS / "03-deployment" / relative)[index]
            drawn = {name for name in all_hosts if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", code)}
            self.assertEqual(drawn, selected, relative)

    def test_application_installers_are_not_confused_with_owned_gitops_starters(self):
        cases = [
            ("stage-04-kubernetes", "tier-0", "cluster-platform", "infrastructure/cni"),
            ("stage-05-identity", "tier-0", "control-applications", "applications/keycloak"),
            ("stage-06-secrets", "tier-0", "control-applications", "applications/vault"),
            ("stage-07-delivery", "tier-1", "delivery-platform", "platform/artifact-registry"),
            ("stage-08-observability", "tier-1", "observability-platform", "platform/observability"),
            ("stage-09-development", "tier-1", "development-platform", "platform/source-control"),
            ("stage-10-lab-environments", "tier-2", "lab-environment", ""),
        ]
        for stage, tier, recipe, relative in cases:
            stage_docs = "\n".join(path.read_text() for path in (DOCS / "03-deployment" / stage).rglob('*.md'))
            self.assertIn(f"ansible/playbooks/deployment/{recipe}.yml", stage_docs, stage)
            self.assertTrue((UPSTREAM / tier / f"ansible/playbooks/deployment/{recipe}.yml").is_file())
            starter = UPSTREAM / tier / f"clusters/tier{tier[-1]}" / relative
            config = yaml.safe_load((starter / "kustomization.yaml").read_text())
            self.assertFalse(config.get("resources"), starter)

    def test_cluster_logging_picture_matches_tier_owned_node_streams(self):
        inputs = yaml.safe_load((UPSTREAM / "tier-0/ansible/group_vars/cluster_security_logging.yml.example").read_text())
        document = (DOCS / "03-deployment/stage-04-kubernetes/README.md").read_text()
        picture = figure_sources(DOCS / '03-deployment/stage-04-kubernetes/README.md')[2]
        nodes = inputs["cluster_security_logging_nodes"]
        self.assertEqual({node["name"] for node in nodes},
                         set(inventory_groups("tier-0")["talos_control_plane"]["hosts"]))
        for node in nodes:
            self.assertEqual(picture.count(f'security-log-{node["stream"]}'), 1)
        for expected in ("Existing log-1", "mTLS"):
            self.assertIn(expected, picture)
        self.assertIn('collectors do not replicate queue contents', document)

    def test_observability_pictures_account_for_selected_native_releases_and_counts(self):
        from test_tier_observability_platform import ROLE, platform_inputs, render_template
        inputs = platform_inputs()
        releases = yaml.safe_load(render_template(ROLE, 'releases.yml.j2', inputs))
        pictures = figure_sources(DOCS / '03-deployment/stage-08-observability/README.md')
        for release in releases:
            self.assertIn(release['name'], pictures[0], release['name'])
        expected_counts = {
            'otel-gateway': 'observability_gateway_replicas',
            'data-prepper': 'observability_prepper_replicas',
            'opensearch': 'observability_search_replicas',
        }
        svg = ET.fromstring(pictures[1])
        for name, key in expected_counts.items():
            match = next(node for node in svg.iter() if node.get('data-replicas') and name in ''.join(node.itertext()))
            self.assertEqual(int(match.get('data-replicas')), inputs[key])
        bridge = next(code for code in pictures if 'Allowlisted metric bridge' in code)
        self.assertIn('Tier 0', bridge)


if __name__ == "__main__":
    unittest.main()
