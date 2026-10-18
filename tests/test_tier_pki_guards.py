"""Run native Ansible safety guards without changing a service or contacting ACME."""

from copy import deepcopy
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Requires Linux Ansible')
class PkiGuards(unittest.TestCase):
    def test_new_recipes_pass_native_syntax_checks(self):
        for tier, recipes in (
            ('tier-0', ['deployment/openxpki-bundle.yml', 'deployment/openxpki-key.yml',
                        'maintenance/openxpki-backup.yml', 'maintenance/openxpki-restore.yml']),
            ('tier-2', ['maintenance/public-certificates.yml', 'deployment/public-certificate-schedule.yml']),
        ):
            roles = os.pathsep.join(str(UPSTREAM / path) for path in (
                f'{tier}/ansible/roles', 'shared/ansible/roles'))
            for recipe in recipes:
                result = subprocess.run(
                    ['ansible-playbook', '--syntax-check', '-i', 'localhost,',
                     str(UPSTREAM / tier / 'ansible/playbooks' / recipe)],
                    env=dict(os.environ, ANSIBLE_ROLES_PATH=roles), cwd=UPSTREAM,
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_public_website_guards_reject_unsafe_inputs(self):
        base = UPSTREAM / 'tier-2/ansible/roles'
        public = base / 'public_certificates'
        edge = base / 'edge_load_balancer'
        variables = yaml.safe_load((public / 'defaults/main.yml').read_text())
        variables.update(yaml.safe_load((edge / 'defaults/main.yml').read_text()))
        variables.update(
            ansible_os_family='RedHat', edge_acme_enabled=True, edge_acme_terms_agreed=True,
            edge_acme_email='ops@corp.test', edge_acme_domains=['www.corp.test'],
            edge_acme_state_directory='/home/automation/.local/share/certificates',
            edge_public_https_backend='website', edge_backend_trust_files=[
                dict(name='private.pem', src='/local/trust/private.pem')],
            edge_haproxy_backends={'website': {'servers': [
                dict(name='app', address='10.30.40.10', port=443, tls=True,
                     verify_hostname='app.corp.test', ca_file='/etc/haproxy/trust/private.pem')]}})
        enrollment = yaml.safe_load((public / 'tasks/main.yml').read_text())[:2]
        origin_checks = [task for task in yaml.safe_load((edge / 'tasks/public_https.yml').read_text())
                         if 'ansible.builtin.assert' in task]
        cases = [('approved', variables, False)]
        for name, changes in (
            ('unaccepted terms', dict(edge_acme_terms_agreed=False)),
            ('nonprivate state', dict(edge_acme_state_directory='/')),
            ('wildcard', dict(edge_acme_domains=['*.corp.test'])),
            ('placeholder', dict(edge_acme_domains=['www.example.invalid'])),
            ('invalid trust filename', dict(edge_backend_trust_files=[
                dict(name='../escape', src='/local/trust/private.pem')])),
        ):
            cases.append((name, dict(variables, **changes), True))
        for name, server_changes in (
            ('cleartext origin', dict(tls=False)),
            ('missing origin identity', dict(verify_hostname='')),
            ('arbitrary trust path', dict(ca_file='/tmp/untrusted.pem')),
            ('raw origin options', dict(extra='verify none')),
        ):
            candidate = deepcopy(variables)
            candidate['edge_haproxy_backends']['website']['servers'][0].update(server_changes)
            cases.append((name, candidate, True))
        plays = []
        for name, values, reject in cases:
            tasks = deepcopy(enrollment + origin_checks)
            if reject:
                tasks = [
                    {'ansible.builtin.set_fact': {'unsafe_rejected': False}},
                    {'block': tasks, 'rescue': [
                        {'ansible.builtin.set_fact': {'unsafe_rejected': True}}]},
                    {'ansible.builtin.assert': {'that': ['unsafe_rejected'],
                                               'fail_msg': f'Unsafe case accepted: {name}'}},
                ]
            plays.append(dict(name=name, hosts='localhost', connection='local',
                              gather_facts=False, vars=values, tasks=tasks))
        with tempfile.TemporaryDirectory(prefix='pki-guards-') as directory:
            playbook = Path(directory) / 'guards.yml'
            playbook.write_text(yaml.safe_dump(plays, sort_keys=False))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)],
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
