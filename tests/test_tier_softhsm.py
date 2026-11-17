"""Real SoftHSM lifecycle tests, plus bounded Ansible wiring checks.

Run native tests on Linux with python3-pykcs11, python3-cryptography and libsofthsm2.
SOFTHSM_TEST_LIBRARY / SOFTHSM_TEST_PYTHON can select extracted native test packages.
No test accesses an operator's configured token store or a physical HSM.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / 'tier-0/ansible/roles/hsm_software'
HELPER = ROLE / 'files/softhsm_issuer.py'
PYTHON = os.environ.get('SOFTHSM_TEST_PYTHON', '/usr/bin/python3')
LIBRARY = os.environ.get('SOFTHSM_TEST_LIBRARY', '/usr/lib/softhsm/libsofthsm2.so')
ANSIBLE = shutil.which('ansible-playbook') if os.name != 'nt' else None
NATIVE = os.name != 'nt' and Path(LIBRARY).is_file() and Path(PYTHON).is_file()


class SoftwareHSMContract(unittest.TestCase):
    def test_initialization_is_explicit_and_credentials_use_stdin(self):
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        self.assertEqual(defaults['hsm_software_operation'], 'configure')
        tasks = yaml.safe_load((ROLE / 'tasks/token.yml').read_text())
        command = next(task for task in tasks if 'ansible.builtin.command' in task)
        self.assertTrue(command['no_log'])
        self.assertEqual(command['ansible.builtin.command']['argv'], [
            '/usr/bin/python3', '/usr/local/libexec/hsm-software-token.py'])
        self.assertIn('stdin', command['ansible.builtin.command'])
        self.assertIn("hsm_software_operation == 'initialize'", command['ansible.builtin.command']['stdin'])
        configure = (ROLE / 'tasks/configure.yml').read_text()
        self.assertIn('name: data_volume', configure)
        self.assertIn('scsi-0QEMU_QEMU_HARDDISK_drive-scsi1', configure)
        self.assertIn('python3-pykcs11', configure)
        self.assertNotIn('ansible.builtin.user:', configure)
        binding = (ROLE / 'tasks/bind.yml').read_text()
        self.assertIn('name: openxpki', binding)
        self.assertIn('tasks_from: preflight', binding)
        self.assertIn('tasks_from: issuer', binding)

    def test_software_inputs_do_not_modify_hardware_driver_contract(self):
        inputs = yaml.safe_load((UPSTREAM / 'tier-0/ansible/group_vars/hsm_software.yml.example').read_text())
        self.assertEqual(inputs['hsm_provider'], 'pkcs11')
        self.assertEqual(inputs['hsm_provider_mode'], 'client')
        self.assertEqual(inputs['hsm_provider_library'], '/usr/lib/softhsm/libsofthsm2.so')
        self.assertFalse(inputs['hsm_provider_custody_ready'])
        self.assertEqual(inputs['hsm_provider_environment'], {'SOFTHSM2_CONF': '/etc/hsm-provider/softhsm2.conf'})


class GeneratedSoftwareHSM(TierRepositoryTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='softhsm-generated-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name) / 'workspace with spaces'
        self.root = self.parent / 'verify-iac'

    def test_generated_software_recipe_inputs_and_native_helper_are_shipped(self):
        self.generate()
        tier = self.root / 'verify-tier-0'
        for relative in ('ansible/playbooks/deployment/hsm-software.yml',
                         'ansible/group_vars/hsm_software.yml.example',
                         'ansible/roles/hsm_software/files/softhsm_issuer.py',
                         'ansible/roles/hsm_software/tasks/bind.yml',
                         'ansible/roles/hsm_software/templates/softhsm2.conf.j2'):
            expected = (UPSTREAM / 'tier-0' / relative).read_text().replace(
                '../../../../shared/', '../../../../verify-shared/')
            expected = expected.replace('# Guide: docs/', '# Guide: ../verify-architecture/docs/auto-docs/')
            self.assertEqual((tier / relative).read_text(), expected, relative)


@unittest.skipUnless(NATIVE, 'Requires native SoftHSM2 and PyKCS11 on Linux')
class NativeSoftwareToken(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        probe = subprocess.run([PYTHON, '-c', 'import PyKCS11, cryptography'], capture_output=True, text=True)
        if probe.returncode:
            raise unittest.SkipTest('Native Python requires PyKCS11 and cryptography')
        cls.seed = tempfile.TemporaryDirectory(prefix='softhsm-seed-')
        cls.seed_root = Path(cls.seed.name) / 'custody'
        (cls.seed_root / 'tokens').mkdir(parents=True)
        cls.seed_config = Path(cls.seed.name) / 'softhsm2.conf'
        cls.seed_config.write_text(f'directories.tokendir = {cls.seed_root}/tokens\nobjectstore.backend = file\nlog.level = ERROR\n')
        cls.base_request = {
            'operation': 'initialize', 'root': str(cls.seed_root), 'library': LIBRARY,
            'label': 'test-issuer', 'key_label': 'ca-signer', 'key_id': '0001', 'rsa_bits': 3072,
            'issuer_data': cls.seed.name, 'expected_serial': '', 'expected_spki_sha256': '',
            'so_pin': 'independent-security-officer-pin', 'user_pin': 'independent-application-pin',
        }
        result = subprocess.run([PYTHON, str(HELPER)], input=json.dumps(cls.base_request),
                                env=dict(os.environ, SOFTHSM2_CONF=str(cls.seed_config)),
                                capture_output=True, text=True)
        if result.returncode:
            cls.seed.cleanup()
            raise AssertionError(result.stdout + result.stderr)
        cls.identity = json.loads(result.stdout)

    @classmethod
    def tearDownClass(cls):
        cls.seed.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='softhsm-native-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.root = self.directory / 'custody'
        shutil.copytree(self.seed_root, self.root)
        self.config = self.directory / 'softhsm2.conf'
        self.config.write_text(f'directories.tokendir = {self.root}/tokens\nobjectstore.backend = file\nlog.level = ERROR\n')
        self.request = dict(self.base_request, root=str(self.root), issuer_data=str(self.directory),
                            expected_serial=self.identity['serial'],
                            expected_spki_sha256=self.identity['spki_sha256'])

    def run_operation(self, operation='inspect', **overrides):
        request = dict(self.request, operation=operation, **overrides)
        result = subprocess.run([PYTHON, str(HELPER)], input=json.dumps(request),
                                env=dict(os.environ, SOFTHSM2_CONF=str(self.config)),
                                capture_output=True, text=True, timeout=45)
        for secret in (request.get('so_pin', ''), request.get('user_pin', '')):
            if secret:
                self.assertNotIn(secret, result.stdout + result.stderr)
                for path in self.root.rglob('*'):
                    if path.is_file():
                        self.assertNotIn(secret.encode(), path.read_bytes())
        return result, json.loads(result.stdout)

    def test_native_token_has_serial_bound_uri_and_pinned_public_key(self):
        result, identity = self.run_operation()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(identity['changed'])
        self.assertRegex(identity['serial'], r'^[a-f0-9]{16}$')
        self.assertRegex(identity['spki_sha256'], r'^[a-f0-9]{64}$')
        self.assertEqual(identity['key_uri'], f'pkcs11:token=test-issuer;serial={identity["serial"]};id=%00%01;type=private')

    def test_repeat_initialization_verifies_key_without_replacing_identity(self):
        before = (self.root / 'identity.json').read_bytes()
        result, identity = self.run_operation('initialize')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertFalse(identity['changed'])
        self.assertEqual(before, (self.root / 'identity.json').read_bytes())

    def test_inspection_changes_no_custody_files(self):
        before = {str(path.relative_to(self.root)): path.read_bytes()
                  for path in self.root.rglob('*') if path.is_file()}
        result, _ = self.run_operation()
        self.assertEqual(result.returncode, 0, result.stdout)
        after = {str(path.relative_to(self.root)): path.read_bytes()
                 for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(before, after)

    def test_pins_and_recorded_configuration_must_match(self):
        for override in ({'expected_serial': '0' * 16}, {'expected_spki_sha256': '0' * 64},
                         {'key_id': '02'}, {'label': 'other-issuer'}, {'rsa_bits': 4096},
                         {'key_label': 'other-key'}):
            with self.subTest(override=override):
                result, _ = self.run_operation(**override)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.root / 'initialization.pending').exists())

    def test_missing_record_never_authorizes_reinitialization(self):
        (self.root / 'identity.json').unlink()
        result, response = self.run_operation('initialize', expected_serial='', expected_spki_sha256='')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unregistered token', response['error'])

    def test_missing_token_with_record_requires_recovery(self):
        shutil.rmtree(self.root / 'tokens')
        (self.root / 'tokens').mkdir()
        result, response = self.run_operation('initialize')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('recover original token', response['error'])

    def test_partial_ceremony_is_not_retried(self):
        (self.root / 'initialization.pending').write_text('{}')
        result, response = self.run_operation('initialize')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Incomplete initialization', response['error'])

    def test_wrong_application_pin_never_changes_existing_record(self):
        original = (self.root / 'identity.json').read_bytes()
        result, _ = self.run_operation('initialize', user_pin='incorrect-application-pin')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(original, (self.root / 'identity.json').read_bytes())

    def test_cold_directory_restore_retains_uri_and_signing_identity(self):
        # setUp restored the stopped token's complete original directory, not a new token.
        result, identity = self.run_operation('initialize')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(identity['key_uri'], self.identity['key_uri'])
        self.assertEqual(identity['spki_sha256'], self.identity['spki_sha256'])

    def test_fresh_configure_never_creates_token_and_existing_issuer_refused(self):
        shutil.rmtree(self.root)
        (self.root / 'tokens').mkdir(parents=True)
        result, identity = self.run_operation('configure', expected_serial='', expected_spki_sha256='')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertFalse(identity['initialized'])
        self.assertFalse(list((self.root / 'tokens').iterdir()))
        (self.directory / 'deployment.json').write_text('{}')
        result, response = self.run_operation('initialize', expected_serial='', expected_spki_sha256='')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('planned migration', response['error'])

    def test_symlinked_token_files_are_refused(self):
        (self.root / 'tokens/foreign').symlink_to(self.config)
        result, response = self.run_operation()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Linked', response['error'])

    def test_changed_record_uri_is_not_trusted(self):
        record = self.root / 'identity.json'
        identity = json.loads(record.read_text())
        identity['key_uri'] = identity['key_uri'].replace('id=%00%01', 'id=%02')
        record.write_text(json.dumps(identity))
        result, response = self.run_operation()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('key URI differs', response['error'])

    def test_bad_new_pins_fail_before_any_native_write(self):
        shutil.rmtree(self.root)
        (self.root / 'tokens').mkdir(parents=True)
        for override in ({'so_pin': '', 'user_pin': ''},
                         {'so_pin': 'same-pin-for-both-users', 'user_pin': 'same-pin-for-both-users'}):
            result, _ = self.run_operation('initialize', expected_serial='', expected_spki_sha256='', **override)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((self.root / 'initialization.pending').exists())
            self.assertFalse(list((self.root / 'tokens').iterdir()))

    @unittest.skipUnless(shutil.which('openssl') and Path(os.environ.get(
        'SOFTHSM_TEST_ENGINE', '/usr/lib/x86_64-linux-gnu/engines-3/pkcs11.so')).is_file(),
        'Requires native OpenSSL PKCS11 engine')
    def test_existing_issuer_engine_creates_a_csr_from_the_serial_selected_key(self):
        engine = os.environ.get('SOFTHSM_TEST_ENGINE', '/usr/lib/x86_64-linux-gnu/engines-3/pkcs11.so')
        template = (UPSTREAM / 'tier-0/ansible/roles/hsm_provider/templates/issuer-openssl.cnf.j2').read_text()
        config = self.directory / 'openssl.cnf'
        config.write_text(template.replace('{{ hsm_issuer_engine_library }}', engine)
                          .replace('{{ hsm_provider_library }}', LIBRARY))
        csr = self.directory / 'issuer.csr'
        argv = ['openssl', 'req', '-new', '-engine', 'pkcs11', '-keyform', 'ENGINE',
                '-key', self.identity['key_uri'], '-passin', 'env:HSM_ISSUER_PIN',
                '-subj', '/CN=Fixture Infrastructure Issuing CA', '-sha384',
                '-addext', 'basicConstraints=critical,CA:TRUE,pathlen:0',
                '-addext', 'keyUsage=critical,keyCertSign,cRLSign', '-out', str(csr)]
        result = subprocess.run(argv, env=dict(os.environ, SOFTHSM2_CONF=str(self.config),
                                OPENSSL_CONF=str(config), HSM_ISSUER_PIN=self.request['user_pin']),
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        from cryptography import x509
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        import hashlib
        request = x509.load_pem_x509_csr(csr.read_bytes())
        self.assertTrue(request.is_signature_valid)
        self.assertEqual(hashlib.sha256(request.public_key().public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo)).hexdigest(), self.identity['spki_sha256'])


@unittest.skipUnless(ANSIBLE, 'Requires Ansible on Linux/WSL')
class SoftwareAnsiblePreflight(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='softhsm-ansible-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.variables = {
            'ansible_connection': 'local', 'ansible_become': False,
            'ansible_python_interpreter': '/usr/bin/python3',
            'ansible_distribution': 'Debian', 'ansible_distribution_major_version': '12',
            'ansible_architecture': 'x86_64', 'hsm_software_operation': 'inspect',
        }

    def run_preflight(self, **overrides):
        playbook = self.root / 'preflight.yml'
        playbook.write_text(yaml.safe_dump([{'hosts': 'localhost', 'gather_facts': False,
            'tasks': [{'ansible.builtin.import_role': {'name': 'hsm_software', 'tasks_from': 'preflight'}}]}]))
        variables = self.root / 'vars.json'
        variables.write_text(json.dumps(dict(self.variables, **overrides)))
        return subprocess.run([ANSIBLE, '-i', 'localhost,', str(playbook), '-e', f'@{variables}'],
                              env=dict(os.environ, ANSIBLE_ROLES_PATH=str(ROLE.parent), ANSIBLE_NOCOLOR='1'),
                              capture_output=True, text=True, timeout=45)

    def test_platform_and_operation_guards_execute_before_token_writes(self):
        result = self.run_preflight()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for override in ({'ansible_distribution': 'Rocky'}, {'ansible_distribution_major_version': '13'},
                         {'hsm_software_operation': 'reinitialize'}, {'hsm_software_key_id': 'not-hex'},
                         {'hsm_software_rsa_bits': 1024}, {'hsm_software_root': '/tmp/foreign'},
                         {'openxpki_create_issuer_key': True}):
            with self.subTest(override=override):
                result = self.run_preflight(**override)
                self.assertNotEqual(result.returncode, 0)

    def test_all_playbook_composition_has_valid_ansible_syntax(self):
        roles = os.pathsep.join((str(ROLE.parent), str(UPSTREAM / 'shared/ansible/roles')))
        result = subprocess.run([ANSIBLE, '-i', 'localhost,', '--syntax-check',
            str(UPSTREAM / 'tier-0/ansible/playbooks/deployment/hsm-software.yml')],
            env=dict(os.environ, ANSIBLE_ROLES_PATH=roles), capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
