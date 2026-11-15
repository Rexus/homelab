"""Native controller-side logging workflow with real CSRs and isolated authority custody."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


NATIVE = os.name != 'nt' and shutil.which('ansible-playbook') and shutil.which('openssl')


@unittest.skipUnless(NATIVE, 'Requires native Linux Ansible, community.crypto and OpenSSL')
class LoggingWorkflow(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='logging-workflow-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'owning-tier-0'
        self.workspace = self.root / 'private-logging'
        self.variables = self.repo / 'ansible/group_vars'
        self.inventory = self.repo / 'ansible/inventory/hosts.yml'
        self.recipe = self.repo / 'ansible/playbooks/deployment/test-workflow.yml'
        for directory in (self.variables, self.inventory.parent, self.recipe.parent):
            directory.mkdir(parents=True, exist_ok=True)
        self.inventory.write_text(yaml.safe_dump({'all': {
            'vars': {'platform_domain': 'corp.example.test', 'platform_internal_domain': 'internal.example.test',
                     'ansible_user': 'existing-operator',
                     'ansible_host': '{{ inventory_hostname }}.{{ platform_internal_domain }}'},
            'children': {
                'foundation_logging': {'hosts': {'log-1': {}}},
                'other_existing': {'hosts': {'node-a': {}, 'node-b': {}, 'unselected': {
                    'ansible_host': 'must-never-connect.invalid'}}},
                'issuing_ca': {'hosts': {'ca-1': {}}}}}}, sort_keys=False))
        self.catalog = {'log_forwarder_peer': 'logs.internal.example.test',
                        'log_forwarder_target': '{{ log_forwarder_peer }}',
                        'logging_producer_hosts': {
                            'node-a': {'setup': 'syslog'},
                            'node-b': {'setup': 'cache', 'streams': [
                                {'name': 'retained-app', 'kind': 'application', 'input': 'files',
                                 'files': ['/var/log/example-app/events.log']}]}}}
        self.write_values('logging_producers', self.catalog)
        self.write_values('syslog', {'platform_host_ips': {'node-a': '192.0.2.10'}})
        self.write_values('cache', {'platform_host_ips': {'node-b': '192.0.2.11'}})
        self.write_values('foundation', {'platform_host_ips': {'ca-1': '192.0.2.20'}})
        self.write_values('issuer', {'openxpki_activate_runtime': True,
                                     'openxpki_realm': 'retained-infrastructure'})
        self.env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local'), ANSIBLE_NOCOLOR='1',
                        ANSIBLE_ROLES_PATH=os.pathsep.join([
                            str(UPSTREAM / 'tier-0/ansible/roles'),
                            str(UPSTREAM / 'shared/ansible/roles')]))
        self.values = {'logging_workflow_repository': str(self.repo),
                       'logging_workflow_workspace': str(self.workspace),
                       'logging_workflow_action': 'prepare', 'logging_workflow_issuer': 'provided',
                       'logging_credentials_password_directory': str(self.root / 'separate-unlock')}

    def write_values(self, name, values):
        (self.variables / f'{name}.yml').write_text(yaml.safe_dump(values, sort_keys=False))

    def run_tasks(self, tasks, *, success=True, without=(), **values):
        inputs = {key: value for key, value in dict(self.values, **values).items() if key not in without}
        play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False, 'become': False,
                 'vars': inputs, 'tasks': tasks}]
        self.recipe.write_text(yaml.safe_dump(play, sort_keys=False))
        result = subprocess.run(['ansible-playbook', '-i', str(self.inventory), str(self.recipe)],
                                env=self.env, capture_output=True, text=True, timeout=130)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        self.assertNotIn('UNREACHABLE', result.stdout)
        return result

    @staticmethod
    def workflow(tasks_from='main'):
        return {'ansible.builtin.include_role': {'name': 'logging_workflow', 'tasks_from': tasks_from}}

    def public_requests(self):
        # Guest service/package runtime is outside this controller test. Build actual
        # producer keys/CSRs with the native collection, then use the real workflow's
        # CSR inspector, fingerprint derivation, receiver requests and issuance.
        return [
            self.workflow(),
            {'ansible.builtin.add_host': {'name': 'node-a', 'logging_workflow_source_address': '198.51.100.10'}},
            {'ansible.builtin.add_host': {'name': 'node-b', 'logging_workflow_source_address': '198.51.100.11'}},
            {'ansible.builtin.file': {'path': str(self.root / 'producer-keys'), 'state': 'directory', 'mode': '0700'},
             'when': "logging_run.action != 'verify'"},
            {'community.crypto.openssl_privatekey': {'path': str(self.root / 'producer-keys/{{ item }}.pem'),
                                                    'type': 'ECC', 'curve': 'secp384r1', 'regenerate': 'never',
                                                    'mode': '0600'},
             'loop': ['node-a-os', 'retained-app'], 'no_log': True,
             'when': "logging_run.action != 'verify'"},
            {'community.crypto.openssl_csr': {
                'path': '{{ logging_run.requests }}/{{ item }}.csr',
                'privatekey_path': str(self.root / 'producer-keys/{{ item }}.pem'),
                'common_name': '{{ item }}', 'use_common_name_for_san': False,
                'basic_constraints': ['CA:FALSE'], 'basic_constraints_critical': True,
                'key_usage': ['digitalSignature'], 'key_usage_critical': True,
                'extended_key_usage': ['clientAuth'], 'mode': '0644'},
             'loop': ['node-a-os', 'retained-app'], 'when': "logging_run.action != 'verify'"},
            self.workflow('requests'),
        ]

    def test_inputs_reuse_catalog_selection_setup_ips_and_existing_login(self):
        tasks = [self.workflow(), {'ansible.builtin.assert': {'that': [
            "groups.logging_workflow_producers | sort == ['node-a', 'node-b']",
            "'unselected' not in groups.logging_workflow_producers",
            "hostvars['node-a'].ansible_host == '192.0.2.10'",
            "hostvars['node-b'].ansible_host == '192.0.2.11'",
            "hostvars['node-a'].ansible_user == 'existing-operator'",
            "hostvars['node-b'].ansible_user == 'existing-operator'",
            "hostvars['node-a'].log_forwarder_streams[0].name == 'node-a-os'",
            "hostvars['node-b'].log_forwarder_streams[0].name == 'retained-app'",
            "logging_run.peer == 'logs.internal.example.test'",
            "logging_run.target == logging_run.peer",
            "logging_run.requests == logging_run.workspace ~ '/requests'",
            "logging_run.public == logging_run.workspace ~ '/public'"]}}]
        self.run_tasks(tasks)
        self.assertEqual(self.workspace.stat().st_mode & 0o777, 0o700)
        self.assertFalse((self.workspace / 'receivers/log-1/key.pem').exists())

    def test_default_workspace_uses_owning_repo_and_environment_outside_git(self):
        execution_home = self.root / 'execution-home'
        execution_home.mkdir()
        self.env['HOME'] = str(execution_home)
        expected = execution_home / '.local/share/owning-tier-0/logging/sandbox'
        self.run_tasks([self.workflow(), {'ansible.builtin.assert': {'that': [
            f"logging_run.repository == '{self.repo}'",
            f"logging_run.workspace == '{expected}'",
            "logging_run.producers | sort == ['node-a', 'node-b']"]}}],
            without=('logging_workflow_repository', 'logging_workflow_workspace'), platform_environment='sandbox')
        self.assertEqual(expected.stat().st_mode & 0o777, 0o700)

    def test_infrastructure_issuer_uses_distinct_issuer_settings_and_foundation_placement(self):
        self.run_tasks([self.workflow(), {'ansible.builtin.assert': {'that': [
            "logging_workflow_issuer_host == 'ca-1'",
            "hostvars['ca-1'].ansible_host == '192.0.2.20'",
            "logging_workflow_issuer_inputs.openxpki_realm == 'retained-infrastructure'",
            "logging_workflow_issuer_inputs.openxpki_activate_runtime",
            "logging_workflow_authority_placement.platform_host_ips['ca-1'] == '192.0.2.20'"]}}],
            logging_workflow_issuer='infrastructure')

    def test_unactivated_infrastructure_issuer_blocks_key_preparation(self):
        self.write_values('issuer', {'openxpki_activate_runtime': False})
        self.run_tasks([self.workflow()], success=False, logging_workflow_issuer='infrastructure')
        self.assertFalse(list(self.workspace.rglob('*.pem')))

    def test_actual_csrs_derive_fingerprints_addresses_and_effective_stream_classification(self):
        self.run_tasks(self.public_requests())
        manifest = json.loads((self.workspace / 'requests.json').read_text())
        requests = {item['name']: item for item in manifest['requests']}
        sources = {item['name']: item for item in manifest['sources']}
        self.assertEqual(set(requests), {'log-1', 'node-a-os', 'retained-app'})
        self.assertEqual(requests['log-1']['profile'], 'server')
        self.assertEqual(requests['log-1']['san'], ['DNS:logs.internal.example.test'])
        self.assertEqual(sources['node-a-os']['address'], '198.51.100.10')
        self.assertEqual(sources['retained-app']['address'], '198.51.100.11')
        self.assertEqual(sources['retained-app']['tls_dn'], 'CN=retained-app')
        self.assertEqual(sources['node-a-os']['kind'], 'security')
        self.assertEqual(sources['retained-app']['kind'], 'application')
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        for request in requests.values():
            csr = x509.load_pem_x509_csr(Path(request['csr']).read_bytes())
            der = csr.public_key().public_bytes(serialization.Encoding.DER,
                                                serialization.PublicFormat.SubjectPublicKeyInfo)
            expected = ':'.join(f'{value:02x}' for value in hashlib.sha256(der).digest())
            self.assertEqual(request['key_sha256'], expected)

    def test_independent_issuance_reuses_real_keys_and_encrypted_secret_without_prompts(self):
        tasks = self.public_requests() + [self.workflow('issue')]
        self.run_tasks(tasks, logging_workflow_action='apply', logging_workflow_issuer='independent')
        original = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob('*')
                    if path.is_file() and (path.suffix == '.pem' or path.name.endswith('.vault.yml')
                                           or path.name == 'ansible-vault.password') and path.name != 'revoked.pem'}
        self.assertTrue(original)
        self.assertTrue((self.workspace / 'credentials/logging-secrets.vault.yml').read_text().startswith('$ANSIBLE_VAULT;'))
        self.run_tasks(tasks, logging_workflow_action='apply', logging_workflow_issuer='independent')
        for relative, content in original.items():
            self.assertEqual((self.root / relative).read_bytes(), content, str(relative))
        public = self.workspace / 'authority/public'
        for name, purpose in (('log-1', 'sslserver'), ('node-a-os', 'sslclient'), ('retained-app', 'sslclient')):
            args = ['openssl', 'verify', '-CAfile', str(public / 'ca.pem'), '-CRLfile',
                    str(public / 'revoked.pem'), '-crl_check', '-purpose', purpose]
            if name == 'log-1':
                args += ['-verify_hostname', 'logs.internal.example.test']
            result = subprocess.run([*args, str(public / f'{name}.pem')], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_verify_reads_existing_requests_without_modifying_keys_or_public_manifest(self):
        self.run_tasks(self.public_requests())
        original = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in self.workspace.rglob('*')
                    if path.is_file()}
        original.update({path: (path.read_bytes(), path.stat().st_mtime_ns)
                         for path in (self.root / 'producer-keys').glob('*.pem')})
        self.run_tasks(self.public_requests(), logging_workflow_action='verify')
        for path, expected in original.items():
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), expected, str(path))

    def test_conflicting_existing_receiver_binding_blocks_manifest_replacement(self):
        self.run_tasks(self.public_requests())
        original = (self.workspace / 'requests.json').read_bytes()
        self.run_tasks(self.public_requests(), success=False, syslog_ng_sources=[{
            'name': 'node-a-os', 'address': '203.0.113.99', 'tier': 0, 'tls_dn': 'CN=node-a-os'}])
        self.assertEqual((self.workspace / 'requests.json').read_bytes(), original)

    def test_named_environment_reuses_each_owning_setup_overlay_without_leaking_between_hosts(self):
        self.write_values('syslog.test', {'platform_host_ips': {'node-a': '192.0.2.110'}})
        self.write_values('cache.test', {'platform_host_ips': {'node-b': '192.0.2.111'}})
        self.run_tasks([self.workflow(), {'ansible.builtin.assert': {'that': [
            "hostvars['node-a'].ansible_host == '192.0.2.110'",
            "hostvars['node-b'].ansible_host == '192.0.2.111'"]}}], platform_environment='test')

    def test_matching_legacy_binding_is_enriched_once_without_duplicate_source_names(self):
        self.run_tasks(self.public_requests(), syslog_ng_sources=[{
            'name': 'node-a-os', 'address': '198.51.100.10', 'tier': 0, 'tls_dn': 'CN=node-a-os'}])
        sources = json.loads((self.workspace / 'requests.json').read_text())['sources']
        self.assertEqual(len(sources), 2)
        self.assertEqual(next(source for source in sources if source['name'] == 'node-a-os')['kind'], 'security')

    def test_loss_of_created_authority_blocks_before_creating_new_credentials(self):
        self.run_tasks([self.workflow()])
        (self.workspace / 'authority-created.json').write_text('{"issuer":"independent"}')
        self.run_tasks([self.workflow(), self.workflow('independent')], success=False,
                       logging_workflow_issuer='independent')
        self.assertFalse((self.workspace / 'credentials').exists())

    def test_changed_authority_choice_requires_a_separate_trust_cutover(self):
        self.run_tasks([self.workflow()])
        (self.workspace / 'workflow.json').write_text('{"issuer":"independent"}')
        self.run_tasks([self.workflow()], success=False, logging_workflow_issuer='provided')

    def test_issuer_configuration_and_placement_follow_the_same_named_environment(self):
        self.write_values('issuer.test', {'openxpki_realm': 'environment-realm'})
        self.write_values('foundation.test', {'platform_host_ips': {'ca-1': '192.0.2.120'}})
        self.run_tasks([self.workflow(), {'ansible.builtin.assert': {'that': [
            "hostvars['ca-1'].ansible_host == '192.0.2.120'",
            "logging_workflow_issuer_inputs.openxpki_realm == 'environment-realm'"]}}],
            logging_workflow_issuer='infrastructure', platform_environment='test')

    def test_unrelated_guest_only_expressions_are_not_evaluated_for_controller_address_selection(self):
        self.write_values('syslog', {'platform_host_ips': {'node-a': '192.0.2.10'},
                                    'unrelated': '{{ nonexistent_guest_fact.address }}'})
        self.write_values('issuer', {'openxpki_activate_runtime': True,
                                    'openxpki_realm': 'infrastructure',
                                    'unrelated': '{{ nonexistent_guest_fact.path }}'})
        self.write_values('foundation', {'platform_host_ips': {'ca-1': '192.0.2.20'},
                                        'unrelated': '{{ inventory_dir }}/../../secrets/identity'})
        self.run_tasks([self.workflow(), {'ansible.builtin.assert': {'that': [
            "hostvars['node-a'].ansible_host == '192.0.2.10'",
            "hostvars['ca-1'].ansible_host == '192.0.2.20'",
            "'unrelated' not in logging_workflow_issuer_inputs"]}}], logging_workflow_issuer='infrastructure')


@unittest.skipUnless(NATIVE, 'Requires native Linux Ansible tasks and getent')
class LoggingAcceptance(unittest.TestCase):
    """CLI doubles check task dispatch and record checks, without exercising live forwarding."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='logging-acceptance-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.calls = self.root / 'calls.jsonl'
        self.records = self.root / 'store/records'
        script = '''
import datetime, json, os, pathlib, sys
command = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['LOGGING_TEST_CALLS'], 'a') as output:
    output.write(json.dumps({'command': command, 'args': args}) + '\\n')
if command == 'ip':
    print(json.dumps([{'prefsrc': '198.51.100.12', 'dst': args[-1]}]))
elif command in ('logger', 'openssl'):
    if command == 'logger':
        name, raw = 'node-a-os', args[-1]
    else:
        name = pathlib.Path(args[args.index('-cert') + 1]).parent.name
        raw = sys.stdin.read()
    directory = pathlib.Path(os.environ['LOGGING_TEST_RECORDS']) / name
    directory.mkdir(parents=True, exist_ok=True)
    record = {'source': name, 'source_tier': 0, 'peer_cn': name, 'peer_ip': '198.51.100.12',
              'transport': 'tls', 'raw': raw}
    if os.environ.get('LOGGING_TEST_BAD_PEER') == '1':
        record['peer_cn'] = 'wrong-identity'
    with (directory / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d') + '.jsonl')).open('a') as output:
        output.write(json.dumps(record) + '\\n')
'''
        for command in ('systemctl', 'logger', 'openssl', 'ip'):
            path = self.bin / command
            path.write_text(f'#!{sys.executable}\n' + script)
            path.chmod(0o700)
        self.inventory = self.root / 'hosts.yml'
        self.inventory.write_text(yaml.safe_dump({'all': {'hosts': {
            'localhost': {'ansible_connection': 'local'},
            'first-receiver': {'ansible_connection': 'local', 'logging_workflow_receiver_address': '127.0.0.2'},
            'target-receiver': {'ansible_connection': 'local', 'logging_workflow_receiver_address': '127.0.0.1'}}}}))
        self.env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local'), ANSIBLE_NOCOLOR='1',
                        ANSIBLE_ROLES_PATH=os.pathsep.join([str(UPSTREAM / 'tier-0/ansible/roles'),
                                                          str(UPSTREAM / 'shared/ansible/roles')]))
        self.process_environment = {'PATH': str(self.bin) + os.pathsep + os.environ['PATH'],
                                    'LOGGING_TEST_CALLS': str(self.calls),
                                    'LOGGING_TEST_RECORDS': str(self.records)}
        self.values = {'logging_run': {'target': 'localhost', 'peer': 'logs.internal.example.test',
                                       'receivers': ['first-receiver', 'target-receiver']},
                       'log_forwarder_streams': [
                           {'name': 'node-a-os', 'kind': 'security', 'input': 'journal'},
                           {'name': 'accepted-app', 'kind': 'application', 'input': 'files',
                            'files': ['/var/log/example-app/events.log']}],
                       'log_forwarder_config': str(self.root / 'producer-config'),
                       'syslog_ng_data_mount': str(self.root / 'store'),
                       'logging_workflow_source_address': '198.51.100.12'}

    def run_tasks(self, tasks, *, success=True):
        path = self.root / 'check.yml'
        path.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': self.values, 'environment': self.process_environment,
            'tasks': [{'ansible.builtin.set_fact': {'logging_run': '{{ logging_run }}'}}, *tasks]}], sort_keys=False))
        result = subprocess.run(['ansible-playbook', '-i', str(self.inventory), str(path)], env=self.env,
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_journal_and_file_stream_acceptance_use_the_selected_receiver_and_distinct_native_clients(self):
        result = self.run_tasks([{'ansible.builtin.include_role': {'name': 'logging_workflow', 'tasks_from': 'verify'}},
            {'ansible.builtin.assert': {'that': [
                "logging_workflow_test_receivers == ['target-receiver']",
                "logging_workflow_record.results[0].receiver == 'target-receiver'"]}}])
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual([item['command'] for item in calls].count('logger'), 1)
        tls = [item for item in calls if item['command'] == 'openssl']
        self.assertEqual(len(tls), 1)
        self.assertIn(str(self.root / 'producer-config/accepted-app/client.pem'), tls[0]['args'])
        self.assertIn('-verify_return_error', tls[0]['args'])
        self.assertIn('Explicit file streams require a real application event', result.stdout)
        self.assertEqual(len(list(self.records.glob('*/*.jsonl'))), 2)

    def test_mismatched_retained_identity_fails_acceptance(self):
        self.process_environment['LOGGING_TEST_BAD_PEER'] = '1'
        result = self.run_tasks([{'ansible.builtin.include_role': {'name': 'logging_workflow', 'tasks_from': 'verify'}}],
                                success=False)
        self.assertNotIn('TLS ingestion passed for', result.stdout)

    def test_file_only_selection_reports_its_actual_acceptance_scope(self):
        self.values['log_forwarder_streams'] = [self.values['log_forwarder_streams'][1]]
        result = self.run_tasks([{'ansible.builtin.include_role': {'name': 'logging_workflow', 'tasks_from': 'verify'}}])
        self.assertNotIn('journal streams', result.stdout.lower())
        self.assertIn('Explicit file streams require a real application event', result.stdout)
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertNotIn('logger', [item['command'] for item in calls])

    def test_source_address_discovery_resolves_the_configured_target_instead_of_first_receiver(self):
        plays = yaml.safe_load((UPSTREAM / 'tier-0/ansible/playbooks/deployment/logging-workflow.yml').read_text())
        producer = next(play for play in plays if play.get('name') == 'Prepare selected producer keys on their existing hosts')
        tasks = [task for task in producer['tasks'] if task['name'] in (
            'Resolve the configured intake before discovering the producer source address',
            'Inspect the actual source route toward the configured intake',
            'Retain the observed outbound source for the receiver ACL')]
        self.assertEqual(len(tasks), 3)
        self.run_tasks(tasks + [{'ansible.builtin.assert': {'that': [
            "logging_workflow_source_address == '198.51.100.12'"]}}])
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(calls, [{'command': 'ip', 'args': ['-j', '-4', 'route', 'get', '127.0.0.1']}])
