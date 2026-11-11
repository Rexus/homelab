"""Focused optional OpenBao contracts; native tests do not establish HSM qualification."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from jinja2 import Environment, StrictUndefined
import yaml

from tier_repo_test_support import UPSTREAM

ROLE = UPSTREAM / 'tier-0/ansible/roles/vault'
NATIVE = os.name == 'posix' and shutil.which('ansible-playbook') and shutil.which('openssl')
BAO = os.environ.get('OPENBAO_TEST_BINARY', '')
PLUGIN = os.environ.get('OPENBAO_TEST_PLUGIN', '')
SOFTHSM = os.environ.get('OPENBAO_TEST_SOFTHSM_UTIL', '')
SOFTHSM_LIB = os.environ.get('OPENBAO_TEST_SOFTHSM_LIBRARY', '')


def values(**overrides):
    defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
    defaults.update(vault_product='openbao', vault_ui_enabled=True, vault_disable_mlock=True,
                    vault_data_dir='/tmp/openbao-test/data', vault_node_id='bao-1',
                    vault_api_addr='https://bao-1.example.test:8200',
                    vault_cluster_addr='https://bao-1.example.test:8201',
                    vault_listener_address='127.0.0.1:8200', vault_tls_min_version='tls12',
                    vault_tls_cert_dest='/private/cert.pem', vault_tls_key_dest='/private/key.pem',
                    vault_tls_ca_dest='/private/ca.pem', openbao_pkcs11_enabled=True,
                    openbao_plugin_sha256='a' * 64, openbao_pkcs11_library='/usr/lib64/pkcs11/opensc-pkcs11.so')
    return defaults | overrides


def render(name, inputs):
    environment = Environment(undefined=StrictUndefined)
    environment.filters.update(ternary=lambda value, yes, no: yes if value else no, to_json=json.dumps)
    return environment.from_string((ROLE / f'templates/{name}.j2').read_text()).render(**inputs)


class OpenBaoContracts(unittest.TestCase):
    def test_default_and_legacy_seal_path_remain_vault(self):
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        self.assertEqual(defaults['vault_product'], 'vault')
        self.assertEqual(defaults['vault_seal_type'], 'shamir')
        self.assertFalse(defaults['openbao_pkcs11_enabled'])
        installer = (ROLE / 'tasks/vault-install.yml').read_text()
        self.assertLess(installer.index('seal-guard.yml'), installer.index('seal.yml'))
        legacy = render('vault.hcl', values(vault_product='vault'))
        self.assertNotIn('plugin "kms"', legacy)
        self.assertNotIn('seal "', legacy)
        self.assertIn('vault_transit', (ROLE / 'tasks/seal.yml').read_text())

    def test_declarative_plugin_and_exact_scoped_policy(self):
        config = render('vault.hcl', values())
        for expected in ('plugin "kms" "pkcs11"', 'plugin_auto_download = false',
                         'version = "v0.2.1"', '-alias=hsm=/usr/lib64/pkcs11/opensc-pkcs11.so'):
            self.assertIn(expected, config)
        self.assertNotIn('pin', config.lower())
        policy = render('openbao-signing-policy.hcl', values(
            openbao_client={'keys': ['release']}, openbao_signing_mount='hardware-signing',
            openbao_signing_keys=[{'name': 'release', 'algorithm': 'rsa-pss-sha256'},
                                  {'name': 'other', 'algorithm': 'ecdsa-p256-sha256'}]))
        self.assertIn('path "hardware-signing/sign/release/sha2-256"', policy)
        self.assertIn('"signature_algorithm" = ["pss"]', policy)
        self.assertIn('"key_version" = ["1"]', policy)
        self.assertNotIn('other', policy)
        self.assertNotIn('*', policy)
        self.assertNotIn('create', policy)

    def test_sensitive_api_and_no_private_key_or_software_fallback(self):
        for path in ROLE.rglob('*.yml'):
            yaml.safe_load(path.read_text())
        tasks = yaml.safe_load((ROLE / 'tasks/openbao-signing.yml').read_text())
        protected = next(task for task in tasks if 'block' in task)
        self.assertTrue(protected['no_log'])
        uri = protected['module_defaults']['ansible.builtin.uri']
        self.assertTrue(uri['validate_certs'])
        self.assertEqual(uri['follow_redirects'], 'none')
        keys = (ROLE / 'tasks/openbao-signing-key.yml').read_text()
        self.assertIn('type: external-key', keys)
        self.assertIn("json.data['keys']['1']", keys)
        for forbidden in ('/import', '/rotate', '/export', 'private_key:', 'type: rsa', 'type: aes'):
            self.assertNotIn(forbidden, keys)
        source = (ROLE / 'tasks/openbao-signing.yml').read_text()
        self.assertLess(source.index('openbao-signing-key.yml'), source.index('openbao-signing-client.yml'))
        install = (ROLE / 'tasks/openbao.yml').read_text()
        self.assertLess(install.index('openbao-inputs.yml'), install.index('ansible.builtin.copy'))
        self.assertIn('not item.stat.exists', install)
        self.assertIn("['xfs', 'ext4', 'btrfs']", install)
        self.assertNotIn('operator, init', install)
        play = yaml.safe_load((UPSTREAM / 'tier-0/ansible/playbooks/deployment/openbao-signing.yml').read_text())
        for task in play[1]['tasks']:
            include = task['ansible.builtin.include_role']
            expected = 'openbao-artifacts' if include['tasks_from'] == 'openbao-controller' else 'openbao-signing'
            self.assertIn(expected, include['apply']['tags'])


@unittest.skipUnless(NATIVE, 'native Ansible and OpenSSL require the Linux controller')
class OpenBaoNativeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='openbao-guards-')
        cls.root = Path(cls.temp.name)
        cls.private = cls.root / 'test-only.key'
        cls.public = cls.root / 'public.pem'
        subprocess.run(['openssl', 'genpkey', '-algorithm', 'EC', '-pkeyopt', 'ec_paramgen_curve:P-256',
                        '-out', str(cls.private)], check=True, capture_output=True)
        subprocess.run(['openssl', 'pkey', '-in', str(cls.private), '-pubout', '-out', str(cls.public)],
                       check=True, capture_output=True)
        der = subprocess.run(['openssl', 'pkey', '-pubin', '-in', str(cls.public), '-outform', 'DER'],
                             check=True, capture_output=True).stdout
        cls.pin = hashlib.sha256(der).hexdigest()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_tasks(self, tasks, inputs):
        play = self.root / 'guard.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                                        'vars': inputs, 'tasks': tasks}]))
        return subprocess.run(['ansible-playbook', '-i', 'localhost,', str(play)],
                              capture_output=True, text=True, timeout=120,
                              env=os.environ | {'ANSIBLE_NOCOLOR': '1'})

    def guard(self, **overrides):
        inputs = values(openbao_signing_address='https://signing.example.test:8200',
                        openbao_signing_ca_src='/private/ca.pem', openbao_signing_token='test-only',
                        openbao_signing_domain='pico-test', openbao_signing_hardware_profile='picohsm-opensc',
                        openbao_signing_provider_accepted=True, openbao_signing_node_ids=['bao-1', 'bao-2', 'bao-3'],
                        openbao_signing_token_serial='test-only-serial', openbao_signing_pin='test-only',
                        openbao_signing_keys=[dict(name='release', id='0x0001', label='release',
                                                  algorithm='ecdsa-p256-sha256', mechanism='CKM_ECDSA',
                                                  public_key_src=str(self.public), public_key_sha256=self.pin)])
        inputs.update(overrides)
        return self.run_tasks([{'ansible.builtin.import_tasks': str(ROLE / 'tasks/openbao-signing-inputs.yml')}], inputs)

    def test_original_spki_matches_native_module_and_wrong_pin_is_rejected(self):
        result = self.guard()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        key = dict(name='release', id='0x0001', label='release', algorithm='ecdsa-p256-sha256',
                   mechanism='CKM_ECDSA', public_key_src=str(self.public), public_key_sha256='0' * 64)
        rejected = self.guard(openbao_signing_keys=[key])
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('Original public key pin', rejected.stdout)

    def test_two_node_ha_unaccepted_provider_and_aes_are_rejected(self):
        for override in ({'openbao_signing_node_ids': ['bao-1', 'bao-2']},
                         {'openbao_signing_provider_accepted': False},
                         {'openbao_signing_hardware_profile': 'generic-aes'}):
            with self.subTest(override=override):
                self.assertNotEqual(self.guard(**override).returncode, 0)

    def test_existing_software_transit_key_guard_refuses_before_creation(self):
        tasks = yaml.safe_load((ROLE / 'tasks/openbao-signing-key.yml').read_text())
        guard = next(task for task in tasks if task['name'].startswith('Refuse software keys'))
        result = self.run_tasks([guard], values(openbao_transit_key={'status': 200, 'json': {'data': {
            'type': 'ecdsa-p256', 'latest_version': 1, 'exportable': False, 'allow_plaintext_backup': False,
            'keys': {'1': 'pico-test:release'}}}}, openbao_signing_domain='pico-test', openbao_key={'name': 'release'}))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('external-key', result.stdout)

    @unittest.skipUnless(BAO and PLUGIN, 'supply the accepted native OpenBao and plugin executable paths')
    def test_native_config_plugin_registration_and_legacy_snapshot_environment(self):
        config = self.root / 'openbao.hcl'
        config.write_text(render('vault.hcl', values(openbao_plugin_directory=str(Path(PLUGIN).parent),
                          openbao_plugin_sha256=hashlib.sha256(Path(PLUGIN).read_bytes()).hexdigest())))
        checked = subprocess.run([BAO, 'operator', 'validate-config', f'-config={config}'], capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        help_text = subprocess.run([PLUGIN, '-help'], capture_output=True, text=True)
        self.assertIn('-alias', help_text.stderr + help_text.stdout)
        environment = {k: v for k, v in os.environ.items() if not k.startswith(('BAO_', 'VAULT_'))}
        environment['VAULT_ADDR'] = 'http://127.0.0.1:1'
        probe = subprocess.run([BAO, 'status'], env=environment, capture_output=True, text=True)
        self.assertNotEqual(probe.returncode, 0)
        self.assertIn('127.0.0.1:1', probe.stderr)

    @unittest.skipUnless(BAO, 'supply the accepted native OpenBao executable path')
    def test_artifacts_tag_installs_cli_and_skips_api_and_recovery(self):
        inventory = self.root / 'inventory.yml'
        inventory.write_text(yaml.safe_dump({'all': {'children': {
            'control_recovery': {'hosts': {'unreachable-fixture': {'ansible_host': '192.0.2.250'}}},
            'controllers': {'hosts': {'localhost': {'ansible_connection': 'local'}}}}}}))
        destination = self.root / 'controller/bin/bao'
        variables = dict(openbao_binary_src=BAO, openbao_binary_sha256=hashlib.sha256(Path(BAO).read_bytes()).hexdigest(),
                         openbao_controller_binary_dest=str(destination), openbao_signing_prepare_backup_cli=True,
                         openbao_signing_address='https://127.0.0.1:1')
        inputs = self.root / 'artifact-inputs.json'
        inputs.write_text(json.dumps(variables))
        environment = os.environ | {'CONTROL_NODE_COLLECTIONS_MODE': 'check', 'ANSIBLE_NOCOLOR': '1',
                                    'ANSIBLE_CONFIG': str(UPSTREAM / 'tier-0/ansible/ansible.cfg')}
        result = subprocess.run(['ansible-playbook', '-i', str(inventory),
                                str(UPSTREAM / 'tier-0/ansible/playbooks/deployment/openbao-signing.yml'),
                                '-e', '@' + str(inputs), '--tags', 'openbao-artifacts'],
                                env=environment, capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout[-5000:] + result.stderr)
        self.assertEqual(hashlib.sha256(destination.read_bytes()).hexdigest(), variables['openbao_binary_sha256'])
        self.assertNotIn('Check initialized unsealed', result.stdout)
        self.assertNotIn('Provision accepted snapshot tooling', result.stdout)

    @unittest.skipUnless(BAO and PLUGIN and SOFTHSM and SOFTHSM_LIB, 'supply accepted native and SoftHSM fixture paths')
    def test_actual_raft_plugin_existing_ec_and_rsa_keys_and_scoped_certificate_login(self):
        # Software PKCS11 integration fixture only: no Yubi/Pico or physical failover qualification.
        with tempfile.TemporaryDirectory(prefix='openbao-runtime-') as directory:
            root = Path(directory)
            for child in ('tokens', 'data', 'logs'):
                (root / child).mkdir()
            token_config = root / 'softhsm.conf'
            token_config.write_text(f'directories.tokendir = {root}/tokens\nobjectstore.backend = file\nlog.level = ERROR\n')
            environment = {k: v for k, v in os.environ.items() if not k.startswith(('BAO_', 'VAULT_'))}
            environment['SOFTHSM2_CONF'] = str(token_config)
            subprocess.run([SOFTHSM, '--module', SOFTHSM_LIB, '--init-token', '--free', '--label', 'test-originals',
                            '--so-pin', 'fixture-so-pin', '--pin', 'fixture-user-pin'],
                           env=environment, check=True, capture_output=True)
            keys = []
            for name, algorithm, mechanism, keyargs in (
                ('ec-original', 'ecdsa-p256-sha256', 'CKM_ECDSA', ['EC', '-pkeyopt', 'ec_paramgen_curve:P-256']),
                ('rsa-original', 'rsa-pss-sha256', 'CKM_RSA_PKCS_PSS', ['RSA', '-pkeyopt', 'rsa_keygen_bits:2048']),
            ):
                private, public = root / f'{name}.key', root / f'{name}.pem'
                subprocess.run(['openssl', 'genpkey', '-algorithm', *keyargs, '-out', str(private)],
                               check=True, capture_output=True)
                subprocess.run(['openssl', 'pkey', '-in', str(private), '-pubout', '-out', str(public)],
                               check=True, capture_output=True)
                der = subprocess.check_output(['openssl', 'pkey', '-pubin', '-in', str(public), '-outform', 'DER'])
                object_id = f'{len(keys) + 1:04x}'
                subprocess.run([SOFTHSM, '--module', SOFTHSM_LIB, '--import', str(private), '--token', 'test-originals', '--label', name,
                                '--id', object_id, '--pin', 'fixture-user-pin'],
                               env=environment, check=True, capture_output=True)
                keys.append(dict(name=name, id='0x' + object_id, label=name, algorithm=algorithm, mechanism=mechanism,
                                 public_key_src=str(public), public_key_sha256=hashlib.sha256(der).hexdigest()))
            cert, tls_key = root / 'server.pem', root / 'server.key'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                            '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1',
                            '-keyout', str(tls_key), '-out', str(cert)], check=True, capture_output=True)
            client, client_key = root / 'client.pem', root / 'client.key'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '10',
                            '-subj', '/CN=fixture-worker', '-addext', 'basicConstraints=critical,CA:FALSE',
                            '-addext', 'extendedKeyUsage=clientAuth', '-keyout', str(client_key), '-out', str(client)],
                           check=True, capture_output=True)
            def free_port():
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1', 0))
                    return sock.getsockname()[1]
            port, cluster_port = free_port(), free_port()
            address = f'https://127.0.0.1:{port}'
            inputs = values(vault_api_addr=address, vault_cluster_addr=f'https://127.0.0.1:{cluster_port}',
                            vault_listener_address=f'127.0.0.1:{port}', vault_tls_cert_dest=str(cert),
                            vault_tls_key_dest=str(tls_key), vault_tls_ca_dest=str(cert), vault_data_dir=str(root / 'data'),
                            vault_log_dir=str(root / 'logs'), openbao_plugin_directory=str(Path(PLUGIN).parent),
                            openbao_pkcs11_library=SOFTHSM_LIB,
                            openbao_plugin_sha256=hashlib.sha256(Path(PLUGIN).read_bytes()).hexdigest())
            config = root / 'openbao.hcl'
            config.write_text(render('vault.hcl', inputs))
            context = ssl.create_default_context(cafile=str(cert))
            token = ''
            def request(path, body=None, method=None, ctx=context, auth=None):
                headers = {'X-Vault-Token': token if auth is None else auth}
                payload = None if body is None else json.dumps(body).encode()
                req = urllib.request.Request(address + '/v1/' + path, data=payload, headers=headers,
                                             method=method or ('POST' if body is not None else 'GET'))
                with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                    return json.loads(response.read() or '{}')
            log = (root / 'server.log').open('w+')
            process = subprocess.Popen([BAO, 'server', '-config=' + str(config)], env=environment,
                                       stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(80):
                    if process.poll() is not None:
                        log.seek(0)
                        self.fail('Disposable OpenBao startup failed: ' + log.read()[-5000:])
                    try:
                        request('sys/health')
                    except urllib.error.HTTPError as error:
                        if error.code == 501:
                            break
                    except (OSError, urllib.error.URLError):
                        pass
                    time.sleep(.1)
                init = request('sys/init', {'secret_shares': 1, 'secret_threshold': 1}, 'PUT')
                token = init['root_token']
                request('sys/unseal', {'key': init['keys_base64'][0]})
                for _ in range(60):
                    try:
                        state = request('sys/storage/raft/autopilot/state')
                    except urllib.error.HTTPError as error:
                        if error.code != 500:
                            raise
                        time.sleep(.2)
                        continue
                    if state.get('data', {}).get('healthy'):
                        break
                    time.sleep(.2)
                audits = request('sys/audit')['data']
                self.assertEqual(audits['file/']['options']['file_path'], str(root / 'logs/audit.log'))
                self.assertEqual(audits['stdout/']['options']['file_path'], 'stdout')
                inputs.update(openbao_signing_address=address, openbao_signing_ca_src=str(cert),
                              openbao_signing_token=token, openbao_signing_domain='test-originals',
                              openbao_signing_hardware_profile='yubihsm2',  # Accepted-profile schema exercised with a software fixture.
                              openbao_signing_provider_accepted=True, openbao_signing_node_ids=['bao-1'],
                              openbao_signing_learning_single=True, openbao_signing_token_serial='',
                              openbao_signing_token_label='test-originals', openbao_signing_pin='fixture-user-pin',
                              openbao_signing_keys=keys, openbao_signing_clients=[dict(name='worker',
                              certificate_src=str(client), keys=['ec-original'], bound_cidrs=['127.0.0.1/32'])])
                tasks = [{'ansible.builtin.include_role': {'name': str(ROLE), 'tasks_from': 'openbao-signing'}}]
                result = self.run_tasks(tasks, inputs)
                if result.returncode:
                    try:
                        diagnostic = request('sys/external-keys/configs/test-originals/keys/ec-original')
                    except urllib.error.HTTPError as error:
                        diagnostic = [error.code, error.read().decode()]
                    self.fail(result.stdout[-5000:] + result.stderr + '\nNative config read: ' + str(diagnostic))
                again = self.run_tasks(tasks, inputs)
                self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
                remote_role = request('auth/hardware-signing-cert/certs/test-originals-worker')['data']
                diagnostic = {k: v for k, v in remote_role.items() if k.startswith('token_')}
                diagnostic['certificate_preserved'] = remote_role['certificate'] == client.read_text()
                self.assertIn('changed=0', again.stdout[-300:], str(diagnostic))
                client_context = ssl.create_default_context(cafile=str(cert))
                client_context.load_cert_chain(str(client), str(client_key))
                login = request('auth/hardware-signing-cert/login', {'name': 'test-originals-worker'}, ctx=client_context, auth='')
                workload = login['auth']['client_token']
                self.assertEqual(login['auth']['policies'], ['test-originals-worker'])
                try:
                    request('hardware-signing/sign/ec-original/sha2-256', {'input': 'cXVhbGlmeQ==', 'key_version': '1',
                            'prehashed': False, 'marshaling_algorithm': 'asn1'}, auth=workload)
                except urllib.error.HTTPError as error:
                    capabilities = request('sys/capabilities', {'token': workload,
                                           'paths': ['hardware-signing/sign/ec-original/sha2-256']})
                    self.fail('Scoped signing denied: ' + error.read().decode() + ' ' + str(capabilities))
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    request('hardware-signing/sign/rsa-original/sha2-256', {'input': 'cXVhbGlmeQ=='}, auth=workload)
                self.assertEqual(denied.exception.code, 403)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                log.close()


if __name__ == '__main__':
    unittest.main()
