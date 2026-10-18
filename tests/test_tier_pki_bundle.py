"""Exercise production bundle construction and reject unsafe bootstrap inputs."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class PkiBundle(TierRepositoryTestCase):
    def test_generated_repositories_include_the_owned_pki_recipes(self):
        self.generate()
        for name in ('openxpki-bundle.yml', 'openxpki-key.yml'):
            self.assertTrue((self.root / 'verify-tier-0/ansible/playbooks/deployment' / name).is_file())
        self.assertTrue((self.root / 'verify-tier-2/ansible/playbooks/maintenance/public-certificates.yml').is_file())
        self.assertTrue((self.root / 'verify-architecture/docs/auto-docs/architecture/cryptography/'
                         'algorithm-selection.md').is_file())

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
            environment = dict(os.environ, ANSIBLE_ROLES_PATH=str(UPSTREAM / 'tier-0/ansible/roles'))
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
            realm = bundle / 'config.d/realm/infrastructure'
            read = lambda path: yaml.safe_load(path.read_text())
            self.assertEqual(set(read(realm / 'auth/handler.yaml')), {'LocalPassword', 'System'})
            profile = read(realm / 'profile/default.yaml')
            self.assertEqual(profile['key']['generate'], 'client')
            self.assertEqual(profile['key']['rsa']['key_length'], [3072, 4096])
            self.assertEqual(profile['extensions']['basic_constraints']['ca'], 0)
            self.assertNotIn('ocsp', profile['extensions']['authority_info_access'])
            self.assertEqual(sorted(path.name for path in (realm / 'profile').glob('*.yaml')),
                             ['default.yaml', 'tls_server.yaml'])
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
