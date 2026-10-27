"""Keepalived remains source-scoped and cannot be silently cut off by hardening."""

from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from test_tier_host_security import NATIVE, ROLE, load, run_plays, settings


@unittest.skipUnless(NATIVE, 'Requires Linux Ansible, ansible.utils and netaddr')
class HostSecurityVrrp(unittest.TestCase):
    def test_exact_ipv4_ipv6_peers_render_only_scoped_vrrp_rules_idempotently(self):
        with tempfile.TemporaryDirectory(prefix='host-security-vrrp-') as temporary:
            directory = Path(temporary)
            values = dict(settings(), host_security_action='render', ansible_connection='local',
                          host_security_output_dir=str(directory / 'rendered'),
                          host_security_vrrp_peers=['192.0.2.21/32', '2001:db8::21/128'])
            plays = [dict(hosts='localhost', connection='local', gather_facts=False,
                          vars=values, roles=['host_security'])]
            for _ in range(2):
                result = run_plays(directory, plays)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('changed=0', result.stdout)
            zone = ET.parse(directory / 'rendered/public.xml').getroot()
            self.assertEqual(zone.attrib['target'], 'DROP')
            self.assertFalse(zone.findall('protocol') + zone.findall('service') + zone.findall('port'))
            rules = [rule for rule in zone.findall('rule') if rule.find('protocol') is not None]
            self.assertEqual(len(rules), 2)
            self.assertEqual({rule.find('source').attrib['address'] for rule in rules},
                             set(values['host_security_vrrp_peers']))
            for rule in rules:
                self.assertEqual(rule.find('protocol').attrib, dict(value='vrrp'))
                self.assertIsNotNone(rule.find('accept'))
                self.assertIsNone(rule.find('port'))
            self.assertEqual([rule.attrib['family'] for rule in rules], ['ipv4', 'ipv6'])
            if os.getenv('HOST_SECURITY_FIREWALL_LIBRARY_TEST') == '1':
                from firewall.core.io.zone import zone_reader
                native_zone = zone_reader('public.xml', str(directory / 'rendered'))
                self.assertEqual(native_zone.target, 'DROP')
                self.assertEqual(len(native_zone.rules), 4)

    def test_peer_type_bounds_duplicates_and_keepalived_guard_reject_before_mutations(self):
        checks = [task for name in ['preflight', 'apply'] for task in load(f'tasks/{name}.yml')
                  if 'ansible.builtin.assert' in task]
        base = settings()
        active = dict(services={'keepalived.service': dict(state='running', status='enabled')})
        cases = [(dict(host_security_vrrp_peers=['192.0.2.21/32'], ansible_facts=active), True),
                 (dict(host_security_vrrp_peers=[], ansible_facts=active), False),
                 (dict(host_security_vrrp_peers=[], ansible_facts=dict(services={
                     'keepalived.service': dict(state='stopped', status='enabled')})), False)]
        cases.extend((dict(host_security_vrrp_peers=peers), False) for peers in [
            True, '192.0.2.21/32', {'192.0.2.21/32': True}, ['0.0.0.0/0'], ['::/0'],
            ['192.0.2.0/24'], ['2001:db8::/64'], ['192.0.2.21/128'], ['2001:db8::21/32'],
            ['999.0.0.1/32'], ['192.0.2.21/32', '192.0.2.21/32'], ['0.0.0.0/32'], ['::/128']])
        plays = []
        for change, accepted in cases:
            tasks = deepcopy(checks)
            if not accepted:
                tasks = [{'ansible.builtin.set_fact': dict(vrrp_rejected=False)},
                         {'block': tasks, 'rescue': [
                             {'ansible.builtin.set_fact': dict(vrrp_rejected=True)}]},
                         {'ansible.builtin.assert': {'that': ['vrrp_rejected']}}]
            plays.append(dict(hosts='localhost', connection='local', gather_facts=False,
                              vars=dict(base, **change), tasks=tasks))
        with tempfile.TemporaryDirectory(prefix='host-security-vrrp-assertions-') as temporary:
            result = run_plays(Path(temporary), plays)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        apply = load('tasks/apply.yml')
        guard = next(i for i, task in enumerate(apply) if 'approved peers' in task['name'])
        install = next(i for i, task in enumerate(apply) if 'ansible.builtin.dnf' in task)
        self.assertLess(guard, install)

    def test_health_accepts_scoped_peers_but_not_a_zone_wide_protocol_allow(self):
        check = next(task for task in load('tasks/health.yml')
                     if task['name'] == 'Require the real drop policy and source-scoped access')
        values = dict(settings(), host_security_vrrp_peers=['192.0.2.21/32', '2001:db8::21/128'])
        zone = values['host_security_enforced_firewall']['firewalld_info']['zones']['public']
        zone['rich_rules'] += ['scoped-vrrp-ipv4', 'scoped-vrrp-ipv6']
        plays = [dict(hosts='localhost', connection='local', gather_facts=False, vars=values, tasks=[check])]
        with tempfile.TemporaryDirectory(prefix='host-security-vrrp-health-') as temporary:
            result = run_plays(Path(temporary), plays)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            zone['protocols'] = ['vrrp']
            result = run_plays(Path(temporary), plays)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
