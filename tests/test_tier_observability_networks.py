"""Match Observability network starters to the actual cluster/source inputs."""

from fnmatch import fnmatchcase
import ipaddress
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM
from test_tier_observability_platform import platform_inputs, render_template


def cluster_network(tier, field):
    text = (tier / 'terraform/deployments/kubernetes/terraform.tfvars.example').read_text()
    return ipaddress.ip_network(re.search(r'\b' + field + r'\s*=\s*"([^"]+)"', text).group(1))


class ObservabilityNetworks(TierRepositoryTestCase):
    def test_source_and_generated_policies_cover_selected_nodes_and_pod_diagnostics(self):
        self.generate()
        for collection, prefix in ((UPSTREAM, ''), (self.root, 'verify-')):
            with self.subTest(collection=prefix or 'source'):
                tiers = [collection / (prefix + f'tier-{n}') for n in range(3)]
                role = tiers[1] / 'ansible/roles/observability_platform'
                example = yaml.safe_load((tiers[1] / 'ansible/group_vars/observability_platform.yml.example').read_text())
                inputs = dict(platform_inputs(), **example)
                inputs['observability_egress'] = [
                    dict(grant, cidr='192.0.2.44/32') if grant['cidr'].startswith('REPLACE_') else grant
                    for grant in example['observability_egress']
                ]
                policies = yaml.safe_load(render_template(role, 'network-policy.yml.j2', dict(
                    inputs, component='metrics', selected_namespace='observability')))
                policy = next(item for item in policies
                              if item['metadata']['name'] == 'observability-isolation')['spec']
                sources = [ipaddress.ip_network(peer['ipBlock']['cidr'])
                           for rule in policy['ingress'] for peer in rule['from'] if 'ipBlock' in peer]
                nodes = {}
                for tier in tiers[1:]:
                    addresses = yaml.safe_load((tier / 'ansible/group_vars/talos.yml.example').read_text())
                    for name, address in addresses['platform_host_ips'].items():
                        self.assertTrue(any(ipaddress.ip_address(address) in subnet for subnet in sources), name)
                    if tier == tiers[1]:
                        nodes = addresses['platform_host_ips']
                log_hosts = yaml.safe_load((tiers[0] / 'ansible/group_vars/syslog.yml.example').read_text())
                for address in log_hosts['platform_host_ips'].values():
                    self.assertTrue(any(ipaddress.ip_address(address) in subnet for subnet in sources))

                grants = [(ipaddress.ip_network(peer['ipBlock']['cidr']), {port['port'] for port in rule['ports']})
                          for rule in policy['egress'] if 'ports' in rule
                          for peer in rule['to'] if 'ipBlock' in peer]
                api_service = next(cluster_network(tiers[1], 'service_cidr').hosts())
                self.assertTrue(any(api_service in subnet and 443 in ports for subnet, ports in grants))
                for address in nodes.values():
                    self.assertTrue(any(ipaddress.ip_address(address) in subnet and {6443, 10250} <= ports
                                        for subnet, ports in grants), address)
                unresolved = [grant for grant in example['observability_egress']
                              if grant['cidr'].startswith('REPLACE_')]
                self.assertEqual(unresolved, [{'cidr': 'REPLACE_WITH_IDP_INGRESS_IP/32', 'ports': [443]}])

                netdata = yaml.safe_load(render_template(role, 'netdata-values.yml.j2', dict(
                    inputs, instance='netdata-1', domain='pve01')))
                config = netdata['parent']['configs']['netdata']['data']
                patterns = re.search(r'^\s*allow connections from = (.+)$', config, re.MULTILINE).group(1).split()
                self.assertNotIn('*', patterns)
                pod = next(cluster_network(tiers[1], 'pod_cidr').hosts())
                for address in [str(pod), *nodes.values()]:
                    self.assertTrue(any(fnmatchcase(address, pattern) for pattern in patterns), address)
                stream = netdata['parent']['configs']['stream']['data']
                self.assertIn('allow from = ' + example['observability_netdata_allow_from'], stream)

                tooling = yaml.safe_load((tiers[1] / 'ansible/playbooks/control-node.yml').read_text())[0]['vars']
                self.assertIn('ansible.utils', tooling['control_node_setup_collection_names']['observability-platform'])
                packages = tooling['control_node_collection_catalog']['ansible.utils']['os_packages']
                for family in ('RedHat', 'Debian'):
                    self.assertIn('python3-netaddr', packages[family])
                self.assertIn('netaddr>=0.10.1', (tiers[1] / 'ansible/requirements.txt').read_text())

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'),
                         'Requires native Ansible and ansible.utils')
    def test_network_preflight_rejects_placeholders_unbounded_ranges_and_invalid_ports(self):
        role = UPSTREAM / 'tier-1/ansible/roles/observability_platform'
        tasks = yaml.safe_load((role / 'tasks/preflight.yml').read_text())
        names = {'Validate bounded telemetry source and egress networks', 'Validate explicit egress destination ports'}
        selected = [task for task in tasks if task['name'] in names]
        self.assertEqual(len(selected), 2)
        play = Path(self.temp.name) / 'network-gates.yml'
        play.write_text(yaml.safe_dump([{
            'hosts': 'localhost', 'connection': 'local', 'gather_facts': False, 'tasks': selected,
        }]))
        cases = [
            ('valid', ['192.0.2.0/24'], [{'cidr': '198.51.100.1/32', 'ports': [443]}], True),
            ('placeholder', [], [{'cidr': 'REPLACE_WITH_IDP_INGRESS_IP/32', 'ports': [443]}], False),
            ('wide-source', ['0.0.0.0/0'], [], False),
            ('bad-source', ['not-a-network'], [], False),
            ('bad-port', [], [{'cidr': '198.51.100.1/32', 'ports': [65536]}], False),
            ('text-port', [], [{'cidr': '198.51.100.1/32', 'ports': ['443']}], False),
            ('float-port', [], [{'cidr': '198.51.100.1/32', 'ports': [443.5]}], False),
            ('bool-port', [], [{'cidr': '198.51.100.1/32', 'ports': [True]}], False),
        ]
        for name, sources, destinations, succeeds in cases:
            with self.subTest(network=name):
                fixture = Path(self.temp.name) / 'network-inputs.yml'
                fixture.write_text(yaml.safe_dump({
                    'observability_telemetry_cidrs': sources, 'observability_egress': destinations,
                }))
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play), '-e', '@' + str(fixture)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, succeeds, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
