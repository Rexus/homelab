"""Native crypto/Ansible checks and source-bound OpenXPKI CLI API doubles.

API doubles exercise retries and policy denial. They do not establish live issuer operation.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import getpass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

from tier_repo_test_support import UPSTREAM

ROLE = UPSTREAM / 'tier-0/ansible/roles/logging_pki'
SOURCE_REVISION = '5c0389789c6275095aec7d6db2dbd85cd5869405'


def load_adapter():
    sys.path.insert(0, str(ROLE / 'files'))
    spec = importlib.util.spec_from_file_location('logging_pki_enroll', ROLE / 'files/enroll.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_cli(path, arguments):
    """A process-separated CLI double using the pinned native command/response shapes."""
    data = json.loads(path.read_text())
    if arguments == ['--version']:
        print(data.get('version', 'OpenXPKI Community Edition v3.34.0'))
        return
    assert arguments[:3] == ['--auth-key', data['auth_key'], '--json'], arguments
    command = arguments[3:5]
    assert arguments[5:7] == ['--realm', 'infrastructure'], arguments
    remainder = arguments[7:]
    params, options = {}, {}
    if '--' in remainder:
        index = remainder.index('--')
        params = dict(item.split('=', 1) for item in remainder[index + 1:])
        remainder = remainder[:index]
    while remainder:
        option = remainder.pop(0)
        options[option] = True if option == '--deserialize' else remainder.pop(0)
    data.setdefault('calls', []).append({'command': command, 'params': params, 'options': options})
    workflows = data.setdefault('workflows', {})
    locks = data.setdefault('locks', {})
    output = None
    if command[0] == 'api':
        name = command[1]
        if name == 'version':
            output = {'server': {'version': '3.34.0', 'api': 2}, 'config': {}}
        elif name == 'get_session_info':
            output = {'role': data.get('role', 'System'), 'pki_realm': 'infrastructure', 'name': 'local-custodian'}
        elif name == 'config_show':
            if params['path'].endswith('certificate_signing_request_v2'):
                output = data['policy']
            else:
                output = data['profiles'][params['path'].split('.')[-1]]
        elif name == 'get_data_pool_entry':
            output = {'value': locks[params['key']]} if params['key'] in locks else None
        elif name == 'create_workflow_instance':
            assert params == {'workflow': 'certificate_signing_request_v2', 'use_lock': params['use_lock']}
            assert params['use_lock'] not in locks
            workflow_id = len(workflows) + 1
            locks[params['use_lock']] = workflow_id
            workflows[str(workflow_id)] = {'id': workflow_id, 'type': 'certificate_signing_request_v2',
                'state': 'SETUP_REQUEST_TYPE', 'proc_state': 'manual', 'context': {}}
            output = {'workflow': workflows[str(workflow_id)]}
        elif name == 'get_workflow_activities':
            workflow = workflows[params['id']]
            output = {'SETUP_REQUEST_TYPE': ['csr_select_profile', 'csr_upload_pkcs10'],
                'ENTER_SUBJECT': ['csr_edit_subject'], 'ENTER_SAN': ['csr_edit_san', 'global_skip'],
                'ENTER_CERT_INFO': ['global_skip'], 'SUBJECT_COMPLETE': ['csr_submit'],
                'PENDING': []}[workflow['state']]
        elif name == 'get_chain':
            output = {'complete': True, 'revoked': data.get('revoked', False),
                      'identifiers': [params['start_with'], 'issuer-id', 'root-id'],
                      'certificates': [data['leaves'][params['start_with']], data['issuer'], data['root']]}
        elif name == 'get_crl':
            assert params == {'issuer_identifier': 'issuer-id', 'format': 'PEM', 'ignore_expired': '1'}
            output = data['crl']
        else:
            raise AssertionError(name)
    elif command == ['workflow', 'show']:
        workflow = workflows[options['--id']]
        if data.get('approve') and workflow['state'] == 'PENDING':
            workflow['state'] = 'SUCCESS'
            workflow['proc_state'] = 'finished'
            workflow['context']['cert_identifier'] = workflow['context']['cert_subject'][3:]
        output = {'workflow': workflow}
    elif command == ['workflow', 'execute']:
        workflow = workflows[options['--id']]
        context = workflow['context']
        action = options['--action']
        if action == 'csr_select_profile':
            context.update(params)
        elif action == 'csr_upload_pkcs10':
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            request = x509.load_pem_x509_csr(params['pkcs10'].encode())
            context.update(params)
            context['cert_subject_parts'] = {'logging_name': request.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value}
            workflow['state'] = 'ENTER_SUBJECT'
        elif action == 'csr_edit_subject':
            context['cert_subject_parts'] = json.loads(params['cert_subject_parts'][7:])
            workflow['state'] = 'ENTER_SAN'
        elif action == 'csr_edit_san':
            context['cert_subject_alt_name'] = [['DNS', name] for name in json.loads(params['cert_san_parts'][7:])['dns']]
            workflow['state'] = 'ENTER_CERT_INFO'
        elif action == 'global_skip':
            workflow['state'] = 'ENTER_CERT_INFO' if workflow['state'] == 'ENTER_SAN' else 'SUBJECT_COMPLETE'
            context['cert_subject'] = 'CN=' + context['cert_subject_parts']['logging_name']
        elif action == 'csr_submit':
            workflow['state'] = 'PENDING'
        else:
            raise AssertionError('Adapter attempted an unexpected activity ' + action)
        output = {'workflow': workflow}
    else:
        raise AssertionError(command)
    path.write_text(json.dumps(data))
    print(output if isinstance(output, str) else json.dumps(output))


class NativeRequestDouble:
    def __init__(self, request, state='PENDING'):
        self.changed = False
        self.request = request
        self.workflow_id = None
        self.creates = 0
        self.state = state
        self.context = {'pkcs10': request['csr_pem'], 'cert_subject': f"CN={request['name']}",
                        'cert_profile': 'logging_' + request['profile'],
                        'cert_subject_style': 'approved_csr',
                        'cert_subject_parts': {'logging_name': request['name']},
                        'cert_subject_alt_name': [name.split(':', 1) for name in request.get('san', [])]}

    def check(self):
        pass

    def locked_workflow(self, lock, receipt_id=None):
        if self.workflow_id is None:
            self.workflow_id = 17
            self.creates += 1
            self.changed = True
        if receipt_id and receipt_id != self.workflow_id:
            raise RuntimeError('Replaced workflow')
        return self.workflow_id

    def show(self, workflow_id):
        return {'id': workflow_id, 'type': 'certificate_signing_request_v2',
                'state': self.state, 'proc_state': 'manual', 'context': self.context}

    def execute(self, *args):
        raise AssertionError('Pending approval must remain read-only')


@unittest.skipUnless(os.name == 'posix', 'Issuer-local filesystem locking requires Linux')
class LoggingEnrollmentContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = load_adapter()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='logging-pki-contract-')
        self.addCleanup(self.temporary.cleanup)
        self.request = {'name': 'sender', 'profile': 'client', 'csr_pem': 'public-csr',
                        'key_sha256': ':'.join(['ab'] * 32)}
        self.config = {'workspace': self.temporary.name, 'realm': 'infrastructure',
                       'generation': 'initial', 'issuer_sha256': 'issuer', 'root_sha256': 'root',
                       'attempts': 1, 'interval': 1, 'request': self.request}

    def test_pending_approval_retains_private_workflow_receipt_and_retries_same_id(self):
        issuer = NativeRequestDouble(self.request)
        first = self.adapter.enroll(self.config, issuer)
        issuer.changed = False
        second = self.adapter.enroll(self.config, issuer)
        self.assertEqual(first['workflow_id'], second['workflow_id'])
        self.assertEqual(issuer.creates, 1)
        self.assertFalse(second['changed'])
        directory = Path(first['directory'])
        self.assertEqual((directory / 'workflow.json').stat().st_mode & 0o777, 0o600)
        self.assertFalse((directory / 'leaf.pem').exists())

    def test_lost_local_receipt_reuses_native_lock(self):
        issuer = NativeRequestDouble(self.request)
        first = self.adapter.enroll(self.config, issuer)
        (Path(first['directory']) / 'workflow.json').unlink()
        second = self.adapter.enroll(self.config, issuer)
        self.assertEqual(first['workflow_id'], second['workflow_id'])
        self.assertEqual(issuer.creates, 1)

    def test_approved_descriptor_is_bound_to_generation_and_trust_pins(self):
        issuer = NativeRequestDouble(self.request)
        first = self.adapter.enroll(self.config, issuer)
        for key in ['generation', 'issuer_sha256', 'root_sha256']:
            changed = deepcopy(self.config)
            changed[key] = 'another-value'
            current = self.adapter.enroll(changed, NativeRequestDouble(self.request))
            self.assertNotEqual(first['directory'], current['directory'])

    def test_changed_workflow_identity_fields_stop_before_any_approval(self):
        changes = {'cert_profile': 'tls_server', 'cert_subject_style': 'arbitrary', 'pkcs10': 'another-csr',
                   'cert_subject': 'CN=another', 'cert_subject_parts': {'logging_name': 'another'},
                   'cert_subject_alt_name': [['DNS', 'another.internal.example']]}
        for field, value in changes.items():
            with self.subTest(field=field):
                issuer = NativeRequestDouble(self.request)
                issuer.context[field] = value
                with self.assertRaises(self.adapter.EnrollmentError):
                    self.adapter.enroll(self.config, issuer)

    def test_terminal_failure_never_replays_requester_actions(self):
        for state in ['REJECTED', 'CANCELED', 'FAILURE', 'VALIDITY_WARNING']:
            with self.subTest(state=state):
                with self.assertRaises(self.adapter.EnrollmentError):
                    self.adapter.enroll(self.config, NativeRequestDouble(self.request, state))

    def test_bounded_poll_wait_preserves_pending_native_workflow(self):
        self.config['attempts'] = 3
        issuer = NativeRequestDouble(self.request)
        with patch.object(self.adapter.time, 'sleep') as sleep:
            result = self.adapter.enroll(self.config, issuer)
        self.assertEqual(result['state'], 'PENDING')
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(issuer.creates, 1)

    def test_completed_workflow_requires_original_csr_profile_and_san(self):
        issuer = NativeRequestDouble(self.request, 'SUCCESS')
        del issuer.context['pkcs10']
        with self.assertRaises(self.adapter.EnrollmentError):
            self.adapter.enroll(self.config, issuer)

    def test_symlinked_workspace_is_rejected(self):
        issuer = NativeRequestDouble(self.request)
        first = self.adapter.enroll(self.config, issuer)
        directory = Path(first['directory'])
        moved = directory.with_name('retained')
        directory.rename(moved)
        directory.symlink_to(moved)
        with self.assertRaises(self.adapter.EnrollmentError):
            self.adapter.enroll(self.config, issuer)

    def test_missing_or_replaced_native_lock_cannot_rebind_existing_receipt(self):
        issuer = self.adapter.NativeIssuer(self.config)
        for response in [None, {'value': 99}]:
            with self.subTest(response=response):
                with patch.object(issuer, 'api', return_value=response) as api:
                    with self.assertRaises(self.adapter.EnrollmentError):
                        issuer.locked_workflow('logging-existing', receipt_id=17)
                    self.assertEqual(api.call_count, 1)

    def test_lost_create_reply_resumes_native_lock_without_duplicate_creation(self):
        issuer = self.adapter.NativeIssuer(self.config)
        responses = [None, self.adapter.EnrollmentError('Native timeout'), {'value': 17}]
        with patch.object(issuer, 'api', side_effect=responses) as api:
            with self.assertRaises(self.adapter.EnrollmentError):
                issuer.locked_workflow('logging-existing')
            self.assertEqual(issuer.locked_workflow('logging-existing'), 17)
            self.assertEqual(sum(call.args[0] == 'create_workflow_instance' for call in api.call_args_list), 1)

    def test_running_server_version_must_match_accepted_cli_contract(self):
        config = dict(self.config, cli='oxi', cli_version='OpenXPKI Community Edition v3.34.0')
        issuer = self.adapter.NativeIssuer(config)
        installed = subprocess.CompletedProcess(['oxi', '--version'], 0, config['cli_version'])
        for server in [{'version': '3.33.0', 'api': 2}, {'version': '3.34.0', 'api': 1}]:
            with self.subTest(server=server):
                with patch('native.subprocess.run', return_value=installed):
                    with patch.object(issuer, 'api', return_value={'server': server}) as api:
                        with self.assertRaises(self.adapter.EnrollmentError):
                            issuer.check()
                        api.assert_called_once_with('version')


@unittest.skipUnless(shutil.which('ansible-playbook') and shutil.which('openssl') and os.name == 'posix',
                     'Requires native Linux Ansible and community.crypto')
class LoggingNativeEnrollment(unittest.TestCase):
    def setUp(self):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
        self.temporary = tempfile.TemporaryDirectory(prefix='logging-pki-native-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.public = self.root / 'public'
        self.source = self.root / 'build/bundle/config.d/realm/infrastructure/profile'
        self.source.mkdir(parents=True)
        now = datetime.now(timezone.utc)
        root_key, issuer_key = ec.generate_private_key(ec.SECP384R1()), ec.generate_private_key(ec.SECP384R1())

        def certificate(name, key, issuer_name, signing_key, ca, request=None):
            builder = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
                       .issuer_name(issuer_name).public_key(key.public_key()).serial_number(x509.random_serial_number())
                       .not_valid_before(now - timedelta(minutes=2)).not_valid_after(now + timedelta(days=30))
                       .add_extension(x509.BasicConstraints(ca, 0 if ca and name != 'root' else None), True)
                       .add_extension(x509.KeyUsage(True, False, False, False, False, ca, ca, False, False), True))
            if request:
                builder = builder.add_extension(request.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value, False)
                try:
                    builder = builder.add_extension(request.extensions.get_extension_for_class(x509.SubjectAlternativeName).value, False)
                except x509.ExtensionNotFound:
                    pass
            return builder.sign(signing_key, hashes.SHA256())

        root_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'root')])
        root_cert = certificate('root', root_key, root_subject, root_key, True)
        issuer_cert = certificate('issuer', issuer_key, root_cert.subject, root_key, True)
        pem = lambda value: value.public_bytes(serialization.Encoding.PEM).decode()
        crl = (x509.CertificateRevocationListBuilder().issuer_name(issuer_cert.subject)
               .last_update(now - timedelta(minutes=1)).next_update(now + timedelta(days=1))
               .sign(issuer_key, hashes.SHA256()))
        self.requests, leaves = [], {}
        for profile, name in [('client', 'sender'), ('server', 'receiver')]:
            key = ec.generate_private_key(ec.SECP384R1())
            builder = (x509.CertificateSigningRequestBuilder()
                       .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
                       .add_extension(x509.BasicConstraints(False, None), True)
                       .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), True)
                       .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH if profile == 'client'
                                                             else ExtendedKeyUsageOID.SERVER_AUTH]), False))
            if profile == 'server':
                builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName('logs.internal.example')]), False)
            request = builder.sign(key, hashes.SHA256())
            path = self.root / f'{name}.csr'
            path.write_text(pem(request))
            der = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
            descriptor = {'name': name, 'profile': profile, 'csr': str(path),
                          'key_sha256': ':'.join(f'{byte:02x}' for byte in hashlib.sha256(der).digest())}
            if profile == 'server':
                descriptor['san'] = ['DNS:logs.internal.example']
            self.requests.append(descriptor)
            leaves[name] = pem(certificate(name, key, issuer_cert.subject, issuer_key, False, request))
        self.binding = self.root / 'deployment.json'
        self.binding.write_text(json.dumps({'configuration_sha256': 'a' * 64,
                                           'package_versions': {'libopenxpki-perl': '3.34.0'}}))
        for name, value in [('root', root_cert), ('issuer', issuer_cert)]:
            (self.root / f'{name}.pem').write_text(pem(value))
        self.auth_key = self.root / 'cli.pem'
        self.auth_key.write_text('existing-custodian-credential-never-returned')
        self.data_path = self.root / 'native.json'
        self.data = {'auth_key': str(self.auth_key), 'root': pem(root_cert), 'issuer': pem(issuer_cert),
                     'crl': pem(crl), 'leaves': leaves,
                     'wrong_crl': pem(x509.CertificateRevocationListBuilder().issuer_name(issuer_cert.subject)
                         .last_update(now - timedelta(minutes=1)).next_update(now + timedelta(days=1))
                         .sign(root_key, hashes.SHA256())),
                     'policy': {'condition': {'acl_can_approve': {'class': 'Workflow::Condition::LazyAND', 'param': {
                         'condition1': 'global_is_operator', 'condition2': '!global_is_creator'}},
                         'is_approved': {'class': 'OpenXPKI::Server::Workflow::Condition::Approved',
                                         'param': {'role': 'RA Operator'}}},
                         'action': {'approve_csr': {'class': 'OpenXPKI::Server::Workflow::Activity::Tools::Approve',
                                                    'param': {'check_creator': 1}}}}, 'profiles': {}}
        self.data_path.write_text(json.dumps(self.data))
        self.cli = self.root / 'oxi'
        self.cli.write_text(f'#!{sys.executable}\nimport sys\nfrom pathlib import Path\n'
                            f'sys.path.insert(0, {str(Path(__file__).parent)!r})\n'
                            f'from test_tier_logging_pki import fixture_cli\n'
                            f'fixture_cli(Path({str(self.data_path)!r}), sys.argv[1:])\n')
        self.cli.chmod(0o700)
        package_cli = self.root / 'dpkg-query'
        package_cli.write_text('#!/bin/sh\nprintf 3.34.0\n')
        package_cli.chmod(0o700)
        self.variables = {'ansible_become': False, 'ansible_python_interpreter': sys.executable,
            'logging_pki_issuer_host': 'localhost',
            'openxpki_activate_runtime': True, 'openxpki_managed_cli': True, 'openxpki_realm': 'infrastructure',
            'openxpki_data_mount': str(self.root), 'openxpki_configuration_sha256': 'a' * 64,
            'openxpki_package_versions': {'libopenxpki-perl': '3.34.0'},
            'openxpki_root_fingerprint': ':'.join(f'{byte:02x}' for byte in root_cert.fingerprint(hashes.SHA256())),
            'openxpki_issuer_fingerprint': ':'.join(f'{byte:02x}' for byte in issuer_cert.fingerprint(hashes.SHA256())),
            'logging_authority_directory': str(self.root / 'enrollment'), 'logging_authority_requests': self.requests,
            'logging_pki_public_directory': str(self.public), 'logging_pki_cli': str(self.cli),
            'logging_pki_cli_auth_key': str(self.auth_key), 'logging_pki_user': getpass.getuser(),
            'logging_pki_group': __import__('grp').getgrgid(os.getgid()).gr_name,
            'logging_pki_root': str(self.root / 'root.pem'), 'logging_pki_issuer': str(self.root / 'issuer.pem')}
        self.render_profiles()

    def run_play(self, tasks=None, expect_success=True):
        play = {'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                'vars': self.variables,
                'environment': {'PATH': str(self.root) + ':' + os.environ['PATH']}}
        if tasks is None:
            play['roles'] = [str(ROLE)]
        else:
            play['tasks'] = tasks
        path = self.root / 'play.yml'
        path.write_text(yaml.safe_dump([play]))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(path)], text=True,
                                capture_output=True, timeout=180, check=False)
        self.assertEqual(result.returncode == 0, expect_success, result.stdout + result.stderr)
        return result

    def render_profiles(self):
        self.variables.update({'logging_pki_profile_directory': str(self.source),
                               'openxpki_bundle_directory': str(self.root / 'build'),
                               'openxpki_bundle_realm': 'infrastructure',
                               'openxpki_bundle_dns_suffixes': ['internal.example']})
        self.run_play([{'ansible.builtin.include_role': {'name': str(ROLE), 'tasks_from': 'profiles'}}])
        self.data['profiles'] = {f'logging_{kind}': yaml.safe_load((self.source / f'logging_{kind}.yaml').read_text())
                                 for kind in ['client', 'server']}
        self.data_path.write_text(json.dumps(self.data))

    def approve(self):
        data = json.loads(self.data_path.read_text())
        data['approve'] = True
        self.data_path.write_text(json.dumps(data))

    def test_native_request_prepare_approval_resume_public_chain_and_idempotence(self):
        pending = self.run_play(expect_success=False)
        self.assertIn('separate RA Operator', pending.stdout)
        self.assertIn('workflow_id', pending.stdout)
        self.assertFalse((self.public / 'sender.pem').exists())
        self.approve()
        self.run_play()
        original = (self.public / 'sender.pem').read_bytes()
        final = self.run_play()
        self.assertIn('changed=0', final.stdout)
        self.assertEqual(original, (self.public / 'sender.pem').read_bytes())
        self.assertEqual((self.public / 'ca.pem').read_text().count('BEGIN CERTIFICATE'), 2)
        self.assertEqual({path.name for path in self.public.iterdir()},
                         {'sender.pem', 'receiver.pem', 'ca.pem', 'revoked.pem'})
        data = json.loads(self.data_path.read_text())
        self.assertEqual(len(data['workflows']), 2)
        self.assertTrue(all('approve' not in call['options'].get('--action', '') for call in data['calls']))
        self.assertNotIn(self.auth_key.read_text(), final.stdout + final.stderr)

    def test_native_modules_reject_changed_csr_key_before_creating_workflow(self):
        self.requests[0]['key_sha256'] = ':'.join(['00'] * 32)
        result = self.run_play(expect_success=False)
        self.assertIn('descriptor must match', result.stdout)
        self.assertFalse(json.loads(self.data_path.read_text()).get('workflows'))

    def test_native_approval_policy_change_blocks_before_submission(self):
        self.data['policy']['condition']['acl_can_approve']['param']['condition2'] = 'global_always_true'
        self.data_path.write_text(json.dumps(self.data))
        result = self.run_play(expect_success=False)
        self.assertIn('independent RA Operator approval policy differs', result.stdout)
        self.assertFalse(json.loads(self.data_path.read_text()).get('workflows'))

    def test_native_cli_version_change_blocks_before_submission(self):
        self.data['version'] = 'OpenXPKI Community Edition v0.0.0'
        self.data_path.write_text(json.dumps(self.data))
        result = self.run_play(expect_success=False)
        self.assertIn('Installed oxi version differs', result.stdout)
        self.assertFalse(json.loads(self.data_path.read_text()).get('workflows'))

    def test_native_crypto_rejects_wrong_issued_key_without_public_release(self):
        pending = self.run_play(expect_success=False)
        self.assertIn('Enrollment is pending', pending.stdout)
        data = json.loads(self.data_path.read_text())
        data['approve'] = True
        data['leaves']['sender'] = data['leaves']['receiver']
        self.data_path.write_text(json.dumps(data))
        rejected = self.run_play(expect_success=False)
        self.assertIn('issued certificate differs', rejected.stdout)
        self.assertFalse((self.public / 'sender.pem').exists())

    def test_native_signature_crl_verification_blocks_corrupt_crl(self):
        self.run_play(expect_success=False)
        data = json.loads(self.data_path.read_text())
        data['approve'] = True
        data['crl'] = data['wrong_crl']
        self.data_path.write_text(json.dumps(data))
        result = self.run_play(expect_success=False)
        self.assertIn('CRL signature failure', result.stdout)
        self.assertFalse((self.public / 'sender.pem').exists())

    def test_profile_builder_preserves_accepted_bundle_archive(self):
        archive = self.root / 'build/configuration.tar.gz'
        archive.write_bytes(b'accepted-immutable-configuration')
        result = self.run_play([{'ansible.builtin.include_role': {
            'name': str(ROLE), 'tasks_from': 'profiles'}}], expect_success=False)
        self.assertIn('new private bundle directory', result.stdout)
        self.assertEqual(archive.read_bytes(), b'accepted-immutable-configuration')


class OpenXPKISourceContract(unittest.TestCase):
    def test_pinned_native_calls_and_initial_selection_are_supported(self):
        cache = Path(os.environ.get('OPENXPKI_UPSTREAM_CACHE', UPSTREAM / '.tmp/openxpki-source'))
        if not cache.is_dir():
            self.skipTest('Set OPENXPKI_UPSTREAM_CACHE to the reviewed native source checkout')
        revision = subprocess.run(['git', '-C', str(cache), 'rev-parse', 'HEAD'], text=True,
                                  capture_output=True, check=True).stdout.strip()
        self.assertEqual(revision, SOURCE_REVISION)
        root = cache / 'core/server/OpenXPKI'
        create = (root / 'Server/API2/Plugin/Workflow/create_workflow_instance.pm').read_text()
        self.assertIn("use_lock => { isa => 'HashRef|Str'", create)
        self.assertIn("params   => { isa => 'HashRef', default => sub { {} }", create)
        self.assertIn("return $util->get_wf_info( id => $lock_id", create)
        util = (root / 'Server/API2/Plugin/Workflow/Util.pm').read_text()
        self.assertIn('NO check is performed on data types or required fields', util)
        cli = (root / 'Client/API/PluginRole.pm').read_text()
        self.assertIn("my ($key, $val) = split('=', $arg, 2)", cli)
        configuration = Path(os.environ.get('OPENXPKI_CONFIG_CACHE', cache.parent / 'openxpki-config-upstream'))
        workflow = yaml.safe_load((configuration / 'config.d/realm.tpl/workflow/def/certificate_signing_request_v2.yaml').read_text())
        self.assertEqual(workflow['state']['INITIAL']['action'], ['select_profile > SETUP_REQUEST_TYPE'])
        self.assertNotIn('validator', workflow['action']['select_profile'])
        self.assertIn('select_profile > SETUP_REQUEST_TYPE', workflow['state']['SETUP_REQUEST_TYPE']['action'])
        for command, parameters in [('get_chain', ['start_with', 'format']),
                                     ('get_crl', ['issuer_identifier', 'ignore_expired']),
                                     ('get_data_pool_entry', ['namespace', 'key', 'decrypt'])]:
            matches = list((root / 'Server/API2/Plugin').rglob(command + '.pm'))
            self.assertEqual(len(matches), 1)
            content = matches[0].read_text()
            for parameter in parameters:
                self.assertIn(parameter, content)
