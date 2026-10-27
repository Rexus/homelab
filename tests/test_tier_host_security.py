"""Offline profile contracts, actual Ansible rejection paths and native config rendering."""

from copy import deepcopy
import base64
import getpass
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

import yaml

from tier_repo_test_support import UPSTREAM


ROLE = UPSTREAM / 'shared/ansible/roles/host_security'
NATIVE = os.name != 'nt' and bool(shutil.which('ansible-playbook'))


def load(relative):
    return yaml.safe_load((ROLE / relative).read_text())


def settings():
    values = load('defaults/main.yml')
    values.update(
        host_security_enabled=True, host_security_profile='linux-host-v1',
        host_security_action='apply', host_security_acknowledgement='apply-linux-host-v1',
        host_security_console_verified=True, host_security_key_access_verified=True,
        host_security_config_ownership_verified=True, host_security_operator_sources=['192.0.2.10/32'],
        host_security_ssh_users=[dict(name='automation', public_key_files=['/outside/git/operator.pub'])],
        host_security_time_servers=['192.0.2.123'], host_security_service_rules=[
            dict(source='192.0.2.32/28', port=443, protocol='tcp')],
        host_security_ssh_port=22, ansible_user='automation', ansible_connection='ssh',
        ansible_os_family='RedHat', ansible_distribution='AlmaLinux',
        ansible_distribution_major_version='10', ansible_architecture='x86_64', ansible_service_mgr='systemd',
        host_security_control_paths=dict(results=[]), host_security_forwarding=dict(stdout='0'),
        host_security_ipv6_forwarding=dict(stdout='0'),
        host_security_connection=dict(stdout='192.0.2.10 51234 192.0.2.20 22'),
        host_security_audit_status=dict(stdout='enabled 1\npid 123\nlost 0'),
        host_security_audit_rules=dict(stdout='No rules'),
        host_security_audit_config=dict(content=base64.b64encode(
            b'local_events = yes\nwrite_logs = yes\nlog_file = /var/log/audit/audit.log\n').decode()),
        host_security_audit_fragment_contents=dict(results=[]),
        host_security_nft_tables=dict(stdout='{"nftables": []}'),
        host_security_firewall_policies=dict(stdout='allow-host-ipv6'),
        host_security_persistent_policies=dict(stdout='allow-host-ipv6'),
        host_security_zone_bindings=dict(results=[]), host_security_nm_zones=dict(results=[]),
        host_security_direct_rules=dict(count=0),
        host_security_runtime_direct=dict(results=[]),
        host_security_firewall_info=dict(firewalld_info=dict(default_zone='public', zones={
            'public': dict(sources=[], interfaces=['eth0'], masquerade=False, forward_ports=[])})),
        host_security_enforced_firewall=dict(firewalld_info=dict(default_zone='public', zones={
            'public': dict(target='DROP', services=[], ports=[], protocols=[], rich_rules=['ssh', 'https'])})),
        host_security_enforced_audit=dict(stdout='enabled 1\npid 123\nlost 0'),
        host_security_enforced_audit_rules=dict(stdout=' '.join(
            'host_security_' + group for group in ['ssh', 'identity', 'privilege', 'firewall', 'time', 'clock'])),
        ansible_facts=dict(services={}),
    )
    return values


def run_plays(directory, plays):
    playbook = directory / 'test.yml'
    playbook.write_text(yaml.safe_dump(plays, sort_keys=False))
    return subprocess.run(
        ['ansible-playbook', '-i', 'localhost,', str(playbook)], cwd=UPSTREAM,
        env=dict(os.environ, ANSIBLE_ROLES_PATH=str(ROLE.parent), ANSIBLE_NOCOLOR='1'),
        capture_output=True, text=True, timeout=180,
    )


class HostSecurityContract(unittest.TestCase):
    def test_examples_and_all_tier_entrypoints_are_explicit_and_serial(self):
        self.assertIs(load('defaults/main.yml')['host_security_enabled'], False)
        self.assertEqual(load('defaults/main.yml')['host_security_profile'], '')
        for tier in range(3):
            root = UPSTREAM / f'tier-{tier}/ansible'
            example = yaml.safe_load((root / 'group_vars/host_security.yml.example').read_text())
            self.assertIs(example['host_security_enabled'], False)
            self.assertEqual(example['host_security_operator_sources'], [])
            self.assertEqual(example['host_security_acknowledgement'], '')
            play = yaml.safe_load((root / 'playbooks/deployment/host-security.yml').read_text())[0]
            self.assertEqual(play['roles'], ['host_security'])
            self.assertEqual(play['serial'], 1)
            self.assertIs(play['any_errors_fatal'], True)
            self.assertIn("default('host_security')", play['hosts'])
            maintenance = yaml.safe_load((root / 'playbooks/maintenance/host-security.yml').read_text())[0]
            self.assertEqual(maintenance['ansible.builtin.import_playbook'], '../deployment/host-security.yml')

    def test_os_packages_paths_and_existing_logging_are_preserved(self):
        operating_systems = load('defaults/main.yml')['host_security_os']
        self.assertEqual(operating_systems['Debian']['time_config'], '/etc/chrony/chrony.conf')
        self.assertEqual(operating_systems['RedHat']['time_config'], '/etc/chrony.conf')
        tasks = [task for path in (ROLE / 'tasks').glob('*.yml') for task in yaml.safe_load(path.read_text())]
        for task in tasks + load('handlers/main.yml'):
            self.assertNotIn('ansible.builtin.shell', task)
            service = task.get('ansible.builtin.systemd_service', {})
            self.assertNotEqual(service.get('state'), 'stopped')
            self.assertIsNot(service.get('enabled'), False)
            if 'ansible.builtin.command' in task:
                self.assertIn('changed_when', task)
        installs = [t['ansible.builtin.apt'] for t in tasks if 'ansible.builtin.apt' in t]
        self.assertEqual(installs[0]['policy_rc_d'], 101)
        rules = (ROLE / 'templates/50-host-security.rules.j2').read_text()
        self.assertNotIn('\n-D', rules)
        self.assertNotIn('\n-e', rules)
        self.assertNotIn('never,task', rules)
        self.assertFalse(any(t.get('ansible.builtin.template', {}).get('dest') == '/etc/audit/auditd.conf'
                             for t in tasks))

    @unittest.skipUnless(NATIVE, 'Requires Linux Ansible, ansible.utils and netaddr')
    def test_real_assertions_reject_unsafe_profiles_access_and_audit_ownership(self):
        checks = [task for file in ['preflight', 'access', 'apply', 'runtime-preflight', 'firewall-preflight', 'health']
                  for task in load(f'tasks/{file}.yml')
                  if 'ansible.builtin.assert' in task and 'host_security_public_keys' not in str(task)]
        valid = settings()
        cases = [('EL prepared', valid, True)]
        debian = dict(valid, ansible_os_family='Debian', ansible_distribution='Debian',
                      ansible_distribution_major_version='13')
        cases.append(('Debian prepared', debian, True))
        cases.append(('IPv6 operator', dict(valid, host_security_operator_sources=['2001:db8::10/128'],
                      host_security_connection=dict(stdout='2001:db8::10 51234 2001:db8::20 22')), True))
        changes = [
            dict(host_security_enabled=False), dict(host_security_enabled='true'),
            dict(host_security_profile='unselected'), dict(host_security_acknowledgement=''),
            dict(host_security_console_verified=False), dict(host_security_key_access_verified=False),
            dict(host_security_config_ownership_verified=False), dict(ansible_connection='local'),
            dict(ansible_distribution='Fedora'), dict(ansible_distribution_major_version='8'),
            dict(host_security_ssh_users=[]), dict(host_security_operator_sources=[]),
            dict(host_security_operator_sources=['0.0.0.0/0']),
            dict(host_security_operator_sources=['::/0']),
            dict(host_security_operator_sources=['999.1.2.3/32']),
            dict(host_security_operator_sources={'192.0.2.10/32': True}),
            dict(host_security_operator_sources=['192.0.2.10/32', '192.0.2.10/32']),
            dict(host_security_operator_sources=['192.0.2.11/32']),
            dict(host_security_connection=dict(stdout='192.0.2.10 51234 192.0.2.20 2222')),
            dict(ansible_user='root'), dict(host_security_time_servers=[]),
            dict(host_security_time_servers=['time.example.org\nallow all']),
            dict(host_security_service_rules=[dict(source='0.0.0.0/0', port=443, protocol='tcp')]),
            dict(host_security_service_rules=[dict(source='192.0.2.0/24', port=22, protocol='tcp')]),
            dict(host_security_service_rules=[dict(source='192.0.2.0/24', port=65536, protocol='udp')]),
            dict(host_security_forwarding=dict(stdout='1')),
            dict(host_security_ipv6_forwarding=dict(stdout='1')),
            dict(host_security_control_paths=dict(results=[dict(stat=dict(exists=True))])),
            dict(host_security_audit_status=dict(stdout='enabled 2')),
            dict(host_security_audit_rules=dict(stdout='-a never,task')),
            dict(host_security_audit_config=dict(content=base64.b64encode(b'write_logs = no\n').decode())),
            dict(host_security_audit_config=dict(content=base64.b64encode(b'log_file = /tmp/audit\n').decode())),
            dict(host_security_audit_fragment_contents=dict(results=[dict(
                content=base64.b64encode(b'-e 2\n').decode())])),
            dict(host_security_nft_tables=dict(stdout='{"nftables":[{"table":{"name":"foreign"}}]}')),
            dict(host_security_firewall_policies=dict(stdout='allow-all')),
            dict(host_security_persistent_policies=dict(stdout='allow-all')),
            dict(host_security_zone_bindings=dict(results=[dict(count=1)])),
            dict(host_security_direct_rules=dict(count=1)),
            dict(host_security_runtime_direct=dict(results=[dict(stdout='ipv4 filter INPUT 0 -j ACCEPT')])),
            dict(host_security_nm_zones=dict(results=[dict(stdout='trusted')])),
            dict(host_security_enforced_audit=dict(stdout='enabled 1\npid 123\nlost 1')),
            dict(host_security_enforced_audit_rules=dict(stdout='No rules')),
            dict(host_security_firewall_info=dict(firewalld_info=dict(default_zone='trusted', zones={}))),
            dict(ansible_facts=dict(services={'ufw.service': dict(state='running')})),
        ]
        for index, change in enumerate(changes):
            cases.append((f'rejected-{index}: {list(change)[0]}', dict(valid, **change), False))
        plays = []
        for name, variables, accept in cases:
            selected = deepcopy(checks)
            if not accept:
                selected = [
                    {'ansible.builtin.set_fact': dict(host_security_rejected=False)},
                    {'block': selected, 'rescue': [
                        {'ansible.builtin.set_fact': dict(host_security_rejected=True)}]},
                    {'ansible.builtin.assert': {'that': ['host_security_rejected'], 'fail_msg': name}},
                ]
            plays.append(dict(name=name, hosts='localhost', connection='local', gather_facts=False,
                              vars=variables, tasks=selected))
        with tempfile.TemporaryDirectory(prefix='host-security-assertions-') as temporary:
            result = run_plays(Path(temporary), plays)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(NATIVE and shutil.which('ssh-keygen'), 'Requires Linux Ansible and OpenSSH')
    def test_external_public_key_validation_and_exclusive_batches(self):
        with tempfile.TemporaryDirectory(prefix='host-security-keys-') as temporary:
            directory = Path(temporary)
            files = [directory / name for name in ['first', 'second']]
            for path in files:
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(path)], check=True)
            user = dict(name=getpass.getuser(), public_key_files=[str(p) + '.pub' for p in files])
            checks = [task for task in load('tasks/access.yml')
                      if task['name'] in ['Validate each external public key with the controller OpenSSH parser',
                                          'Reject private key material or key-file options masquerading as key text']]
            install = next(task for task in load('tasks/ssh.yml') if 'ansible.posix.authorized_key' in task)
            install['ansible.posix.authorized_key']['path'] = str(directory / 'authorized_keys')
            plays = [dict(hosts='localhost', connection='local', gather_facts=False,
                          vars=dict(host_security_ssh_users=[user]), tasks=checks + [install])]
            result = run_plays(directory, plays)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            authorized = (directory / 'authorized_keys').read_text()
            self.assertEqual(len(authorized.splitlines()), 2)
            user['public_key_files'] = [str(files[1]) + '.pub']
            result = run_plays(directory, plays)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((directory / 'authorized_keys').read_text().strip(),
                             Path(str(files[1]) + '.pub').read_text().strip())
            for invalid in [str(files[0]), str(directory / 'missing.pub')]:
                user['public_key_files'] = [invalid]
                result = run_plays(directory, plays)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(NATIVE, 'Requires Linux Ansible and collections')
    def test_all_tier_recipes_and_actual_apply_tasks_pass_native_syntax(self):
        with tempfile.TemporaryDirectory(prefix='host-security-syntax-') as temporary:
            playbook = Path(temporary) / 'apply.yml'
            playbook.write_text(yaml.safe_dump([dict(hosts='localhost', gather_facts=False, tasks=[{
                'ansible.builtin.import_role': dict(name='host_security', tasks_from='apply')}])]))
            paths = [playbook] + [UPSTREAM / f'tier-{tier}/ansible/playbooks/{recipe}/host-security.yml'
                                 for tier in range(3) for recipe in ['deployment', 'maintenance']]
            for path in paths:
                result = subprocess.run(
                    ['ansible-playbook', '-i', 'localhost,', str(path), '--syntax-check',
                     '-e', 'host_security_hosts=localhost'], cwd=UPSTREAM,
                    env=dict(os.environ, ANSIBLE_ROLES_PATH=str(ROLE.parent)),
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(NATIVE, 'Requires Linux Ansible, ansible.utils and netaddr')
    def test_native_render_both_families_is_idempotent_and_has_scoped_drop_policy(self):
        with tempfile.TemporaryDirectory(prefix='host-security-render-') as temporary:
            directory = Path(temporary)
            plays = []
            for family, distribution, major in [('RedHat', 'AlmaLinux', '10'), ('Debian', 'Debian', '13')]:
                values = dict(settings(), host_security_action='render', host_security_output_dir=str(directory / family),
                              ansible_os_family=family, ansible_distribution=distribution,
                              ansible_distribution_major_version=major, ansible_connection='local')
                values['host_security_operator_sources'].append('2001:db8::10/128')
                plays.append(dict(name=family, hosts='localhost', connection='local', gather_facts=False,
                                  vars=values, roles=['host_security']))
            result = run_plays(directory, plays)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            repeat = run_plays(directory, plays)
            self.assertEqual(repeat.returncode, 0, repeat.stdout + repeat.stderr)
            self.assertIn('changed=0', repeat.stdout)
            for family in ['RedHat', 'Debian']:
                output = directory / family
                firewall = ET.parse(output / 'public.xml').getroot()
                self.assertEqual(firewall.attrib['target'], 'DROP')
                self.assertEqual(len(firewall.findall('rule')), 3)
                self.assertFalse(firewall.findall('service') + firewall.findall('port') + firewall.findall('forward'))
                self.assertEqual({r.attrib['family'] for r in firewall.findall('rule')}, {'ipv4', 'ipv6'})
                for rule in firewall.findall('rule'):
                    self.assertIsNotNone(rule.find('source'))
                    self.assertIsNotNone(rule.find('port'))
                    self.assertIsNotNone(rule.find('accept'))
                ssh = (output / 'sshd_config').read_text()
                self.assertIn('AuthenticationMethods publickey\n', ssh)
                self.assertIn('PermitRootLogin no\n', ssh)
                self.assertIn('AllowUsers automation\n', ssh)
                self.assertNotIn('sshd_config.d', ssh)
                ssh_validator = os.getenv('HOST_SECURITY_SSHD')
                if ssh_validator:
                    check = subprocess.run([ssh_validator, '-G', '-f', str(output / 'sshd_config')],
                                           capture_output=True, text=True, timeout=15)
                    self.assertEqual(check.returncode, 0, check.stderr)
                    for policy in ['passwordauthentication no', 'permitrootlogin no',
                                   'authenticationmethods publickey', 'disableforwarding yes']:
                        self.assertIn(policy, check.stdout)
                chrony = (output / 'chrony.conf').read_text()
                self.assertIn('server 192.0.2.123 iburst', chrony)
                self.assertNotIn('\npool ', chrony)
                if os.getenv('HOST_SECURITY_FIREWALL_LIBRARY_TEST') == '1':
                    from firewall.core.io.zone import zone_reader
                    native_zone = zone_reader('public.xml', str(output))
                    self.assertEqual(native_zone.target, 'DROP')
                    self.assertEqual(len(native_zone.rules), 3)
                validator = os.getenv('HOST_SECURITY_CHRONYD') or shutil.which('chronyd')
                if validator:
                    check = subprocess.run([validator, '-p', '-f', str(output / 'chrony.conf')],
                                           capture_output=True, text=True, timeout=15)
                    self.assertEqual(check.returncode, 0, check.stderr)


if __name__ == '__main__':
    unittest.main()
