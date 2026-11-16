"""Run native Ansible safety guards without changing a service or contacting ACME."""

from copy import deepcopy
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import hashlib
import json

import yaml

from tier_repo_test_support import UPSTREAM


@unittest.skipUnless(shutil.which('ansible-playbook'), 'Requires Linux Ansible')
class PkiGuards(unittest.TestCase):
    def test_new_recipes_pass_native_syntax_checks(self):
        for tier, recipes in (
            ('tier-0', ['deployment/openxpki-bundle.yml', 'deployment/openxpki-key.yml',
                        'deployment/openxpki-repository.yml', 'deployment/openxpki-portal-request.yml',
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

    def test_repository_preflight_rejects_unqualified_sources_before_installation(self):
        role = UPSTREAM / 'tier-0/ansible/roles/openxpki'
        guard = yaml.safe_load((role / 'tasks/repository.yml').read_text())[0]
        valid = dict(ansible_distribution='Debian', ansible_distribution_major_version='12',
                     ansible_architecture='x86_64', openxpki_repository_key_sha256='a' * 64,
                     openxpki_repository_uri='https://packages.example.test/bookworm/',
                     openxpki_repository_key_url='https://packages.example.test/Release.key')
        plays = [dict(name='approved source', hosts='localhost', connection='local',
                      gather_facts=False, vars=valid, tasks=[guard])]
        for changes in (dict(ansible_distribution='AlmaLinux'),
                        dict(ansible_distribution_major_version='13'),
                        dict(ansible_architecture='aarch64'),
                        dict(openxpki_repository_key_sha256=''),
                        dict(openxpki_repository_uri='http://packages.example.test/')):
            plays.append(dict(hosts='localhost', connection='local', gather_facts=False,
                vars=dict(valid, **changes), tasks=[
                    {'ansible.builtin.set_fact': {'source_rejected': False}},
                    {'block': [guard], 'rescue': [
                        {'ansible.builtin.set_fact': {'source_rejected': True}}]},
                    {'ansible.builtin.assert': {'that': ['source_rejected']}},
                ]))
        candidate_guard = yaml.safe_load((UPSTREAM / 'tier-0/ansible/playbooks/deployment/openxpki-repository.yml')
                                        .read_text())[-1]['tasks'][1]
        complete = '\n'.join(f'{package}:\n  Candidate: 3.34.0-1' for package in (
            'libopenxpki-perl', 'openxpki-cgi-session-driver', 'openxpki-i18n'))
        plays.append(dict(name='complete candidate set', hosts='localhost', connection='local',
            gather_facts=False, vars={'openxpki_repository_candidates': {'stdout': complete}},
            tasks=[candidate_guard]))
        for report in (complete.replace('3.34.0-1', '(none)', 1), 'libopenxpki-perl:\n  Candidate: 3.34.0-1'):
            plays.append(dict(hosts='localhost', connection='local', gather_facts=False,
                vars={'openxpki_repository_candidates': {'stdout': report}}, tasks=[
                    {'ansible.builtin.set_fact': {'candidates_rejected': False}},
                    {'block': [candidate_guard], 'rescue': [
                        {'ansible.builtin.set_fact': {'candidates_rejected': True}}]},
                    {'ansible.builtin.assert': {'that': ['candidates_rejected']}},
                ]))
        with tempfile.TemporaryDirectory(prefix='issuer-source-guards-') as directory:
            playbook = Path(directory) / 'guards.yml'
            playbook.write_text(yaml.safe_dump(plays, sort_keys=False))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)],
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(shutil.which('openssl'), 'Requires native OpenSSL')
    def test_portal_request_reuses_the_existing_key_without_contacting_the_issuer(self):
        with tempfile.TemporaryDirectory(prefix='issuer-portal-request-') as directory:
            work = Path(directory)
            key = work / 'portal-key.pem'
            created = subprocess.run(['openssl', 'genpkey', '-algorithm', 'EC',
                '-pkeyopt', 'ec_paramgen_curve:secp384r1', '-out', str(key)],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(created.returncode, 0, created.stderr)
            original = hashlib.sha256(key.read_bytes()).digest()
            inventory = work / 'hosts.yml'
            # An unreachable managed address proves the controller-only recipe does not SSH there.
            inventory.write_text(yaml.safe_dump({'all': {'children': {'issuing_ca': {
                'hosts': {'ca-fixture': {'ansible_host': '192.0.2.254'}}}}}}))
            values = dict(openxpki_tls_key_src=str(key), openxpki_portal_fqdn='ca.internal.test',
                          openxpki_ceremony_directory=str(work / 'requests'))
            recipe = UPSTREAM / 'tier-0/ansible/playbooks/deployment/openxpki-portal-request.yml'
            environment = dict(os.environ, ANSIBLE_ROLES_PATH=os.pathsep.join(str(UPSTREAM / path)
                for path in ('tier-0/ansible/roles', 'shared/ansible/roles')))
            args = ['ansible-playbook', '-i', str(inventory), str(recipe), '-e', json.dumps(values)]
            for attempt in range(2):
                result = subprocess.run(args, env=environment, cwd=UPSTREAM,
                                        capture_output=True, text=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if attempt:
                    self.assertIn('changed=0', result.stdout)
                self.assertEqual(hashlib.sha256(key.read_bytes()).digest(), original)
            csr = work / 'requests/ca-fixture-portal.csr'
            request = subprocess.run(['openssl', 'req', '-in', str(csr), '-verify', '-noout', '-text'],
                                     capture_output=True, text=True, timeout=10)
            self.assertEqual(request.returncode, 0, request.stdout + request.stderr)
            self.assertIn('DNS:ca.internal.test', request.stdout)
            csr_public = subprocess.check_output(['openssl', 'req', '-in', str(csr), '-pubkey', '-noout'])
            key_public = subprocess.check_output(['openssl', 'pkey', '-in', str(key), '-pubout'])
            self.assertEqual(csr_public, key_public)

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
