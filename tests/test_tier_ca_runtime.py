"""Exercise real Ansible safety assertions without installing a CA or contacting hosts."""

from copy import deepcopy
import json
import os
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / 'tier-0/ansible/roles/openxpki'


class CertificateAuthorityRuntime(TierRepositoryTestCase):
    def test_resources_and_recipes_stay_in_tier_zero(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        for source in (UPSTREAM / 'tier-0', repo):
            main = (source / 'terraform/deployments/foundation/main.tf').read_text()
            self.assertIn('extra_disks              = each.value.extra_disks', main)
            self.assertIn('source   = "../../modules/vm"', main)
            groups = yaml.safe_load((source / 'ansible/inventory/hosts.yml.example').read_text())['all']['children']
            self.assertNotIn('root_ca', groups['foundation']['children'])
            deploy = yaml.safe_load((source / 'ansible/playbooks/deployment/openxpki.yml').read_text())
            self.assertEqual(deploy[0]['hosts'], 'issuing_ca')
            self.assertEqual(deploy[0]['roles'], ['baseline', 'openxpki'])
            for taskfile in (source / 'ansible/roles/openxpki/tasks').glob('*.yml'):
                self.assertNotIn('ansible.builtin.shell', taskfile.read_text())
            identity = yaml.safe_load((source / 'ansible/playbooks/deployment/identity-freeipa.yml').read_text())
            self.assertNotIn('foundation', [play.get('hosts') for play in identity])
            primary = next(play for play in identity if play.get('name') == 'Configure the first FreeIPA identity host')
            self.assertTrue(any('ansible.builtin.fetch' in task for task in primary['tasks']))
            replica = next(play for play in identity if play.get('hosts') == 'identity_replicas')
            self.assertIn('ansible.builtin.meta', replica['pre_tasks'][0])
        for name in ('verify-shared', 'verify-tier-1', 'verify-tier-2'):
            self.assertFalse((self.root / name / 'ansible/roles/openxpki').exists())

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires Ansible on Linux/WSL')
    def test_native_preflight_and_database_guards_reject_unsafe_states(self):
        tasks = yaml.safe_load((ROLE / 'tasks/preflight.yml').read_text())
        assertions = [task for task in tasks if 'ansible.builtin.assert' in task]
        valid = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        valid.update(
            ansible_distribution='Debian', ansible_distribution_major_version='12', ansible_architecture='x86_64',
            openxpki_data_uuid='data-uuid', openxpki_deployment_id='test-ca',
            openxpki_configuration_src='/local/configuration.tar.gz', openxpki_configuration_sha256='a' * 64,
            openxpki_repository_key_sha256='b' * 64, openxpki_portal_fqdn='ca.internal.example.com',
            openxpki_listen_address='10.20.21.10', openxpki_admin_networks=['10.10.10.0/24'],
            openxpki_publication_networks=['10.0.0.0/8'],
            openxpki_package_versions={name: '3.34.0-1' for name in (
                'libopenxpki-perl', 'openxpki-cgi-session-driver', 'openxpki-i18n')},
            openxpki_database_password='x' * 40, openxpki_session_password='y' * 40,
            openxpki_session_secret='z' * 40,
            openxpki_configuration_stat=dict(stat=dict(isreg=True, checksum='a' * 64)),
            openxpki_data_facts=[dict(uuid='data-uuid', fstype='ext4', options='rw', size_available=10 * 1024**3)],
            openxpki_database_facts=[dict(uuid='data-uuid', options='rw')],
            openxpki_root_facts=[dict(uuid='root-uuid')],
            openxpki_binding_stat=dict(stat=dict(exists=False)), openxpki_existing_config=dict(stat=dict(exists=False)),
            openxpki_directories=dict(results=[dict(item='keys', stat=dict(exists=False))]),
        )
        cases = [('prepared', valid, assertions, False)]
        registered = dict(valid, openxpki_binding_stat=dict(stat=dict(exists=True, isreg=True, islnk=False)),
                          openxpki_binding_file=dict(content='eyJleHBlY3RlZCI6dHJ1ZX0='),
                          openxpki_binding=dict(expected=True))
        cases.append(('registered deployment', registered, assertions, False))
        for name, changes in (
            ('wrong platform', dict(ansible_distribution='AlmaLinux')),
            ('wrong architecture', dict(ansible_architecture='aarch64')),
            ('unsigned artifact', dict(openxpki_repository_key_sha256='')),
            ('unreviewed archive', dict(openxpki_configuration_stat=dict(stat=dict(isreg=True, checksum='c' * 64)))),
            ('missing data mount', dict(openxpki_data_facts=[])),
            ('wrong data mount', dict(openxpki_data_uuid='wrong')),
            ('missing database mount', dict(openxpki_database_facts=[])),
            ('root storage', dict(openxpki_root_facts=[dict(uuid='data-uuid')])),
            ('read-only database', dict(openxpki_database_facts=[dict(uuid='data-uuid', options='ro')])),
            ('unrestricted portal', dict(openxpki_admin_networks=['0.0.0.0/0'])),
            ('unregistered CA', dict(openxpki_existing_config=dict(stat=dict(exists=True)))),
            ('linked keys', dict(openxpki_directories=dict(results=[
                dict(item='keys', stat=dict(exists=True, isdir=False, islnk=True))]))),
            ('changed binding', dict(openxpki_binding_stat=dict(stat=dict(exists=True, isreg=True, islnk=False)),
                                     openxpki_binding_file=dict(content='e30='), openxpki_binding=dict(expected=True))),
        ):
            case = deepcopy(valid)
            case.update(changes)
            cases.append((name, case, assertions, True))
        database = yaml.safe_load((ROLE / 'tasks/database.yml').read_text())
        guard = next(task for task in database if 'ansible.builtin.assert' in task)
        for name, receipt, tables, initialize, rejected in (
            ('approved empty schema', False, 0, True, False),
            ('unapproved empty schema', False, 0, False, True),
            ('partial schema', False, 30, True, True),
            ('lost database', True, 0, True, True),
            ('existing database', True, 30, False, False),
        ):
            values = dict(openxpki_schema_receipt=dict(stat=dict(exists=receipt)),
                          openxpki_tables=dict(query_result=[[dict(total=tables)]]),
                          openxpki_initialize_database=initialize)
            cases.append((name, values, [guard], rejected))
        policy = yaml.safe_load((ROLE / 'tasks/policy.yml').read_text())[-1]
        policy_values = dict(
            openxpki_realm='infrastructure', openxpki_realms={'infrastructure': {}},
            openxpki_auth_handlers={'LocalPassword': {'type': 'Password'}, 'System': {'role': 'System'}},
            openxpki_auth_stacks={'LocalPassword': {'handler': 'LocalPassword', 'type': 'passwd'},
                                 '_System': {'handler': 'System'}},
        )
        cases.append(('production authentication', policy_values, [policy], False))
        for name, changes in (
            ('demo realm', dict(openxpki_realm='democa', openxpki_realms={'democa': {}})),
            ('test account handler', dict(openxpki_auth_handlers={
                **policy_values['openxpki_auth_handlers'], 'TestAccounts': {'type': 'Password'}})),
            ('anonymous portal', dict(openxpki_auth_stacks={
                **policy_values['openxpki_auth_stacks'], 'Anonymous': {'handler': 'Anonymous'}})),
        ):
            cases.append((name, dict(policy_values, **changes), [policy], True))
        plays = []
        for name, variables, checks, rejected in cases:
            checks = deepcopy(checks)
            if rejected:
                checks = [
                    {'ansible.builtin.set_fact': dict(ca_rejected=False)},
                    {'block': checks, 'rescue': [{'ansible.builtin.set_fact': dict(ca_rejected=True)}]},
                    {'ansible.builtin.assert': {'that': ['ca_rejected'], 'fail_msg': f'Unsafe case accepted: {name}'}},
                ]
            plays.append(dict(name=name, hosts='localhost', connection='local', gather_facts=False,
                              vars=variables, tasks=checks))
        if shutil.which('systemd-escape'):
            configuration = yaml.safe_load((ROLE / 'tasks/configuration.yml').read_text())
            escape = next(task for task in configuration if task.get('register') == 'openxpki_data_mount_unit')
            plays.append(dict(name='native mount path escaping', hosts='localhost', connection='local',
                              gather_facts=False,
                              vars=dict(openxpki_data_mount='/srv/openxpki-ca',
                                        expected_mount_unit=r'srv-openxpki\x2dca.mount'),
                              tasks=[escape, {'ansible.builtin.assert': {'that': [
                                  'openxpki_data_mount_unit.stdout == expected_mount_unit',
                              ]}}]))
        self.parent.mkdir(parents=True)
        playbook = self.parent / 'ca-guards.yml'
        playbook.write_text(yaml.safe_dump(plays, sort_keys=False))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)],
                                cwd=UPSTREAM, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipIf(os.name == 'nt', 'Bash wrapper checks run under Linux/WSL')
    def test_recipe_override_never_provisions_or_accepts_path_traversal(self):
        self.generate()
        repo = self.root / 'verify-tier-0'
        for path in ('inventory/hosts', 'group_vars/all', 'group_vars/foundation'):
            shutil.copyfile(repo / f'ansible/{path}.yml.example', repo / f'ansible/{path}.yml')
        commands = self.parent / 'commands'
        commands.mkdir()
        log = self.parent / 'calls.jsonl'
        for name in ('ansible-playbook', 'terraform'):
            command = commands / name
            command.write_text("#!/usr/bin/env python3\nimport json, os, sys\n"
                               "with open(os.environ['TEST_CA_LOG'], 'a') as f:\n"
                               "    f.write(json.dumps(sys.argv) + '\\n')\n")
            command.chmod(0o755)
        environment = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}", TEST_CA_LOG=str(log))
        for name in ('DEPLOYMENT_REPO_DIR', 'SHARED_REPO_DIR'):
            environment.pop(name, None)
        for args, success in (
            (['--playbook', 'deployment/openxpki.yml'], False),
            (['--ansible-only', '--playbook', '../openxpki.yml'], False),
            (['--ansible-only', '--playbook', 'deployment/missing.yml'], False),
            (['--ansible-only', '--playbook', 'deployment/openxpki.yml'], True),
            (['--recipe', 'maintenance', '--playbook', 'maintenance/openxpki.yml'], True),
        ):
            result = subprocess.run(['bash', 'scripts/deploy.sh', 'foundation', *args], cwd=repo,
                                    env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(len(calls), 4)
        self.assertTrue(all('ansible-playbook' in call[0] for call in calls))
        self.assertTrue(calls[1][-1].endswith('/deployment/openxpki.yml'))
        self.assertTrue(calls[3][-1].endswith('/maintenance/openxpki.yml'))
