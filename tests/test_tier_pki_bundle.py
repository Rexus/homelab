"""Exercise production bundle construction and reject unsafe bootstrap inputs."""

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class PkiBundle(TierRepositoryTestCase):
    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'),
                         'Requires Ansible on Linux/WSL')
    def test_documented_controller_commands_resolve_roles_in_a_fresh_shell(self):
        self.generate()
        guides = (
            ('tier-0', 'stage-02-trust/README.md', 'openxpki-bundle.yml'),
            ('tier-2', 'stage-10-lab-environments/step-4b-public-https.md', 'public-certificate-schedule.yml'),
        )
        for collection, prefix, docs in (
            (UPSTREAM, '', UPSTREAM / 'docs'),
            (self.root, 'verify-', self.root / 'verify-architecture/docs/auto-docs'),
        ):
            for tier, guide, playbook in guides:
                content = (docs / '03-deployment' / guide).read_text()
                commands = [
                    shlex.split(line)
                    for block in re.findall(r'```bash\n(.*?)```', content, re.DOTALL)
                    for line in block.replace('\\\n', ' ').splitlines()
                    if 'ansible-playbook ' in line
                ]
                self.assertEqual(len(commands), 1, guide)
                arguments = commands[0]
                self.assertEqual(arguments.pop(0), 'ANSIBLE_CONFIG=ansible/ansible.cfg', guide)
                self.assertIn(f'ansible/playbooks/deployment/{playbook}', arguments)
                environment = dict(os.environ)
                environment.pop('ANSIBLE_CONFIG', None)
                environment.pop('ANSIBLE_ROLES_PATH', None)
                environment['ANSIBLE_CONFIG'] = 'ansible/ansible.cfg'
                # Parse the documented command without secrets, prompts or executing tasks.
                variables = arguments.index('-e')
                del arguments[variables:variables + 2]
                if '--ask-become-pass' in arguments:
                    arguments.remove('--ask-become-pass')
                result = subprocess.run(
                    [*arguments, '--syntax-check'], cwd=collection / f'{prefix}{tier}',
                    env=environment, capture_output=True, text=True, timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generated_repositories_include_the_owned_pki_recipes(self):
        self.generate()
        for name in ('openxpki-bundle.yml', 'openxpki-key.yml'):
            self.assertTrue((self.root / 'verify-tier-0/ansible/playbooks/deployment' / name).is_file())
        self.assertTrue((self.root / 'verify-tier-2/ansible/playbooks/maintenance/public-certificates.yml').is_file())
        self.assertTrue((self.root / 'verify-architecture/docs/auto-docs/01-architecture/08-cryptography/'
                         '02-algorithm-selection.md').is_file())

    @unittest.skipUnless(shutil.which('ansible-playbook') and os.environ.get('PKI_CONFIG_REPOSITORY'),
                         'Requires Linux Ansible and a pinned upstream configuration fixture')
    def test_native_builder_creates_restricted_immutable_configuration(self):
        from cryptography import x509
        from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

        with tempfile.TemporaryDirectory(prefix='pki-bundle-') as directory:
            root = Path(directory)
            digest = Argon2id(salt=os.urandom(16), length=32, iterations=3, lanes=4,
                              memory_cost=65536).derive_phc_encoded(b'disposable-test-password')
            values = dict(
                openxpki_bundle_directory=str(root / 'approved'),
                openxpki_bundle_repository=os.environ['PKI_CONFIG_REPOSITORY'],
                openxpki_bundle_portal_fqdn='ca.corp.test',
                openxpki_bundle_publication_url='http://ca.corp.test/download/',
                openxpki_bundle_dns_suffixes=['corp.test'],
                openxpki_bundle_signer_password='disposable-signer-password-' * 3,
                openxpki_bundle_datavault_secret='a5' * 32,
                openxpki_bundle_users={
                    'requester-test': dict(role='User', digest=digest),
                    'approver-test': dict(role='RA Operator', digest=digest),
                },
            )
            environment = dict(os.environ, ANSIBLE_CONFIG=str(UPSTREAM / 'tier-0/ansible/ansible.cfg'))
            environment.pop('ANSIBLE_ROLES_PATH', None)
            def run(inputs):
                parameters = root / 'inputs.yml'
                parameters.write_text(yaml.safe_dump(inputs))
                return subprocess.run(
                    ['ansible-playbook', '-i', 'localhost,',
                     str(UPSTREAM / 'tier-0/ansible/playbooks/deployment/openxpki-bundle.yml'),
                     '-e', f'@{parameters}'], cwd=UPSTREAM, env=environment,
                    text=True, capture_output=True, timeout=360,
                )
            result = run(values)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            bundle = root / 'approved/bundle'
            for path in bundle.rglob('*'):
                self.assertFalse(path.is_symlink(), path)
                self.assertEqual(path.stat().st_mode & 0o077, 0, path)
            realm = bundle / 'config.d/realm/infrastructure'
            read = lambda path: yaml.safe_load(path.read_text())
            signer = read(realm / 'crypto.yaml')['token']['ca-signer']
            self.assertEqual(signer['engine'], 'OpenSSL')
            self.assertEqual(signer['key_store'], 'OPENXPKI')
            self.assertEqual(signer['key'], '/srv/openxpki/keys/issuer.pem')
            system_secrets = read(bundle / 'config.d/system/crypto.yaml')['secret']
            self.assertEqual(system_secrets['default']['value'], values['openxpki_bundle_signer_password'])
            self.assertEqual(system_secrets['svault']['value'], values['openxpki_bundle_datavault_secret'])
            self.assertEqual(set(read(realm / 'auth/handler.yaml')), {'LocalPassword', 'System'})
            profile = read(realm / 'profile/default.yaml')
            self.assertEqual(profile['key']['generate'], 'client')
            self.assertEqual(profile['key']['rsa']['key_length'], [3072, 4096])
            self.assertEqual(profile['extensions']['basic_constraints']['ca'], 0)
            self.assertNotIn('ocsp', profile['extensions']['authority_info_access'])
            self.assertEqual(sorted(path.name for path in (realm / 'profile').glob('*.yaml')),
                             ['default.yaml', 'logging_client.yaml', 'logging_server.yaml', 'tls_server.yaml'])
            for kind, eku in [('client', 'client_auth'), ('server', 'server_auth')]:
                logging_profile = read(realm / f'profile/logging_{kind}.yaml')
                self.assertEqual(logging_profile['key']['generate'], 'client')
                self.assertEqual(logging_profile['validity']['notafter'], '+000030')
                self.assertEqual(logging_profile['extensions']['basic_constraints'], {'critical': 1, 'ca': 0})
                self.assertEqual(logging_profile['extensions']['extended_key_usage'], {'critical': 0, eku: 1})
            workflow = read(realm / 'workflow/def/certificate_signing_request_v2.yaml')
            self.assertEqual(workflow['action']['approve_csr']['param']['check_creator'], 1)
            self.assertEqual(workflow['condition']['acl_can_approve']['param']['condition2'],
                             '!global_is_creator')
            self.assertNotIn('Anonymous', workflow['acl'])
            self.assertNotIn('edit_validity', workflow['action'])
            original_workflow = read(Path(os.environ['PKI_CONFIG_REPOSITORY'])
                                     / 'config.d/realm.tpl/workflow/def/certificate_signing_request_v2.yaml')
            self.assertEqual(set(workflow['state']), set(original_workflow['state']))
            for state in workflow['state'].values():
                self.assertNotIn('edit_validity', state.get('button', {}))
                self.assertNotIn('edit_validity >', str(state.get('action')))
            self.assertIn('local-custodian', read(bundle / 'config.d/system/cli.yaml')['auth'])
            for name in ('certificate_enroll', 'certificate_privkey_export'):
                self.assertEqual(set(read(realm / f'workflow/def/{name}.yaml')['acl']), {'System'})
            revocation = read(realm / 'workflow/def/certificate_revocation_request_v2.yaml')
            self.assertEqual(revocation['action']['approve_crr']['param']['check_creator'], 1)
            self.assertEqual(revocation['condition']['is_approved']['class'],
                             'OpenXPKI::Server::Workflow::Condition::Approved')
            for field in ('hostname', 'hostname2'):
                pattern = read(realm / f'profile/template/{field}.yaml')['match']
                for hostname, allowed in (('host.corp.test', True), ('corp.test', True),
                                          ('other.test', False), ('*.corp.test', False),
                                          ('host.corp.test.attacker.test', False)):
                    check = subprocess.run(
                        ['perl', '-e', 'my ($r,$n)=@ARGV; exit($n =~ /$r/x ? 0 : 1);', pattern, hostname],
                        capture_output=True, timeout=10)
                    self.assertEqual(check.returncode == 0, allowed, hostname)
            self.assertEqual(list(read(bundle / 'config.d/system/realms.yaml')), ['infrastructure'])
            certificate = x509.load_pem_x509_certificate((root / 'approved/portal-bootstrap.pem').read_bytes())
            self.assertEqual(certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName)
                             .value.get_values_for_type(x509.DNSName), ['ca.corp.test'])
            original = (root / 'approved/configuration.tar.gz').read_bytes()
            self.assertNotEqual(run(values).returncode, 0)
            self.assertEqual((root / 'approved/configuration.tar.gz').read_bytes(), original)
            for key, unsafe in (
                ('openxpki_bundle_dns_suffixes', ['example.invalid']),
                ('openxpki_bundle_datavault_secret', 'weak'),
                ('openxpki_bundle_signer_password', 'weak'),
            ):
                rejected = dict(values, openxpki_bundle_directory=str(root / 'rejected'))
                rejected[key] = unsafe
                self.assertNotEqual(run(rejected).returncode, 0, key)
                self.assertFalse((root / 'rejected/configuration.tar.gz').exists())

    @unittest.skipUnless(
        shutil.which('ansible-playbook') and os.environ.get('PKI_CONFIG_REPOSITORY')
        and os.environ.get('OPENXPKI_UPSTREAM_CACHE'),
        'Requires native Linux Ansible and the pinned configuration/source fixtures')
    def test_native_pkcs11_builder_uses_existing_key_uri_and_protected_pin(self):
        from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

        source = Path(os.environ['OPENXPKI_UPSTREAM_CACHE'])
        revision = subprocess.run(['git', '-C', str(source), 'rev-parse', 'HEAD'],
                                  capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(revision, '5c0389789c6275095aec7d6db2dbd85cd5869405')
        native = source / 'core/server/OpenXPKI/Crypto'
        engine_source = native / 'Backend/OpenSSL/Engine/PKCS11.pm'
        self.assertTrue(engine_source.is_file())
        toolkit = (native / 'Toolkit.pm').read_text()
        self.assertIn('engine_section engine_usage key key_store', toolkit)
        parent_engine = (native / 'Backend/OpenSSL/Engine.pm').read_text()
        self.assertIn('ENGINE|OPENXPKI|DATAPOOL', parent_engine)
        native_sign = (native / 'Backend/OpenSSL/Command/issue_cert.pm').read_text()
        self.assertIn("if ($key_store ne 'ENGINE' && not -e $self->{KEYFILE})", native_sign)
        config = (native / 'Backend/OpenSSL/Config.pm').read_text()
        self.assertIn("$engine_name . ' = engine_config'", config)
        self.assertIn("'[ engine_config ]'", config)
        self.assertIn('$self->{ENGINE}->get_engine_section()', config)
        native_secret = yaml.safe_load((Path(os.environ['PKI_CONFIG_REPOSITORY'])
                                       / 'config.d/realm.tpl/crypto.yaml').read_text())['secret']
        self.assertEqual(native_secret['default'], {'import': 1})

        with tempfile.TemporaryDirectory(prefix='pki-hardware-bundle-') as temporary:
            root = Path(temporary)
            digest = Argon2id(salt=os.urandom(16), length=32, iterations=3, lanes=4,
                              memory_cost=65536).derive_phc_encoded(b'disposable-test-password')
            values = dict(
                openxpki_bundle_directory=str(root / 'approved'),
                openxpki_bundle_repository=os.environ['PKI_CONFIG_REPOSITORY'],
                openxpki_bundle_portal_fqdn='ca.corp.test',
                openxpki_bundle_publication_url='http://ca.corp.test/download/',
                openxpki_bundle_dns_suffixes=['corp.test'],
                openxpki_bundle_signer_backend='pkcs11',
                openxpki_bundle_signer_password='',
                openxpki_bundle_pkcs11_key_uri='pkcs11:serial=TESTSERIAL;id=%01;type=private',
                openxpki_bundle_pkcs11_library='/usr/lib/x86_64-linux-gnu/opensc-pkcs11.so',
                openxpki_bundle_pkcs11_engine_library='/usr/lib/x86_64-linux-gnu/engines-3/pkcs11.so',
                openxpki_bundle_datavault_secret='b6' * 32,
                openxpki_bundle_users={
                    'requester-test': dict(role='User', digest=digest),
                    'approver-test': dict(role='RA Operator', digest=digest),
                },
            )
            pin = '86427591'
            environment = dict(os.environ, HSM_ISSUER_PIN=pin,
                               ANSIBLE_CONFIG=str(UPSTREAM / 'tier-0/ansible/ansible.cfg'))
            environment.pop('ANSIBLE_ROLES_PATH', None)

            def run(inputs):
                parameters = root / 'inputs.yml'
                parameters.write_text(yaml.safe_dump(inputs))
                return subprocess.run([
                    'ansible-playbook', '-i', 'localhost,',
                    str(UPSTREAM / 'tier-0/ansible/playbooks/deployment/openxpki-bundle.yml'),
                    '-e', f'@{parameters}'], cwd=UPSTREAM, env=environment,
                    capture_output=True, text=True, timeout=360)

            result = run(values)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn(pin, result.stdout + result.stderr)
            bundle = root / 'approved/bundle'
            realm = bundle / 'config.d/realm/infrastructure'
            crypto = yaml.safe_load((realm / 'crypto.yaml').read_text())
            signer = crypto['token']['ca-signer']
            self.assertEqual(signer['engine'], 'PKCS11')
            self.assertEqual(signer['key_store'], 'ENGINE')
            self.assertEqual(signer['key'], values['openxpki_bundle_pkcs11_key_uri'])
            self.assertEqual(signer['engine_usage'], 'PRIV_KEY_OPS')
            self.assertEqual(signer['wrapper'], '')
            self.assertEqual(signer['secret'], 'default')
            self.assertEqual(crypto['secret']['default'], {'import': 1})
            self.assertEqual(crypto['token']['svault']['secret'], 'svault')
            section = signer['engine_section']
            self.assertEqual(section, '\n'.join([
                'engine_id = pkcs11',
                'dynamic_path = ' + values['openxpki_bundle_pkcs11_engine_library'],
                'MODULE_PATH = ' + values['openxpki_bundle_pkcs11_library'],
                'PIN = "__PIN__"', 'init = 0', '']))
            self.assertNotIn(pin, section)
            self.assertNotIn('/keys/issuer.pem', (realm / 'crypto.yaml').read_text())
            self.assertFalse(list(bundle.rglob('issuer.pem')))
            secrets = yaml.safe_load((bundle / 'config.d/system/crypto.yaml').read_text())['secret']
            self.assertEqual(secrets['default'], {'method': 'literal', 'export': 0, 'value': pin})
            self.assertEqual(secrets['svault']['value'], values['openxpki_bundle_datavault_secret'])
            artifact = root / 'approved/configuration.tar.gz'
            original = artifact.read_bytes()
            self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)
            for path in bundle.rglob('*'):
                self.assertFalse(path.is_symlink())
                self.assertEqual(path.stat().st_mode & 0o077, 0)

            # Execute the pinned engine's actual section substitution with a secret
            # handle double. This exercises neither a physical token nor signing.
            perl = r'''
BEGIN {
    $INC{'OpenXPKI.pm'} = 1;
    $INC{'OpenXPKI/Crypto/Backend/OpenSSL/Engine.pm'} = 1;
    $INC{'OpenXPKI/Server/Context.pm'} = 1;
    package OpenXPKI::Server::Context;
    sub import {}
    package OpenXPKI::Crypto::Backend::OpenSSL::Engine;
    sub key_usable { return 1 }
    sub get_passwd { return $_[0]->{TEST_PIN} }
}
use JSON::PP;
my $input = decode_json(do { local $/; <STDIN> });
require $input->{source};
my $engine = bless({ENGINE_SECTION => $input->{section}, TEST_PIN => $input->{pin}},
    'OpenXPKI::Crypto::Backend::OpenSSL::Engine::PKCS11');
print encode_json({engine => $engine->get_engine(), keyform => $engine->get_keyform(),
    section => $engine->get_engine_section()});
'''
            execution = subprocess.run(['perl', '-e', perl], input=json.dumps({
                'source': str(engine_source), 'section': section, 'pin': pin}),
                capture_output=True, text=True, timeout=15)
            self.assertEqual(execution.returncode, 0, execution.stderr)
            emitted = json.loads(execution.stdout)
            self.assertEqual(emitted['engine'], 'pkcs11')
            self.assertEqual(emitted['keyform'], 'engine')
            self.assertEqual(emitted['section'], section.replace('__PIN__', pin))

            self.assertNotEqual(run(values).returncode, 0)
            self.assertEqual(artifact.read_bytes(), original)
            invalid = []
            for index, (key, unsafe) in enumerate((
                ('openxpki_bundle_pkcs11_pin', '12345'),
                ('openxpki_bundle_pkcs11_pin', '648219'),
                ('openxpki_bundle_pkcs11_pin', '0001password'),
                ('openxpki_bundle_pkcs11_pin', 'quoted"pin'),
                ('openxpki_bundle_pkcs11_pin', 'back\\slash'),
                ('openxpki_bundle_pkcs11_pin', 'expand$pin'),
                ('openxpki_bundle_pkcs11_pin', 'new\nline'),
                ('openxpki_bundle_pkcs11_pin', values['openxpki_bundle_datavault_secret']),
                ('openxpki_bundle_pkcs11_key_uri', values['openxpki_bundle_pkcs11_key_uri'] + ';pin-value=secret'),
                ('openxpki_bundle_pkcs11_key_uri', values['openxpki_bundle_pkcs11_key_uri'] + ';%70in-value=secret'),
                ('openxpki_bundle_pkcs11_library', ''),
                ('openxpki_bundle_pkcs11_engine_library', 'relative/pkcs11.so'),
            )):
                rejected = dict(values, openxpki_bundle_directory=str(root / f'rejected-{index}'))
                rejected[key] = unsafe
                invalid.append({'name': 'Reject unsafe hardware input before creating its directory',
                    'block': [
                        {'ansible.builtin.include_role': {'name': 'openxpki_bundle'}, 'vars': rejected},
                        {'ansible.builtin.fail': {'msg': 'An unsafe hardware input was accepted.'}}],
                    'rescue': [
                        {'ansible.builtin.stat': {'path': rejected['openxpki_bundle_directory']},
                         'register': 'rejected_directory'},
                        {'ansible.builtin.assert': {'that': 'not rejected_directory.stat.exists'}}]})
            validation = root / 'reject-inputs.yml'
            validation.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                'gather_facts': True, 'become': False, 'tasks': invalid}], sort_keys=False))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(validation)],
                                    cwd=UPSTREAM, env=environment, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(list(root.glob('rejected-*')))
