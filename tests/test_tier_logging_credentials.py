"""Native logging bootstrap custody; KVv2 protocol fixture is not live Vault qualification."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'tier-0/ansible/roles/logging_credentials'
PLAYBOOK = os.environ.get('ANSIBLE_PLAYBOOK', shutil.which('ansible-playbook'))


class NativeKV2:
    """Exercise the real community.hashi_vault modules through verified local HTTPS."""

    def __init__(self, base):
        self.token = secrets.token_urlsafe(32)
        self.document = None
        self.version = 0
        self.requests = []
        self.mutate_after_write = False
        self.race_on_write = False
        self.unavailable = False
        key, self.ca = base / 'tls.key', base / 'ca.pem'
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
            '-keyout', str(key), '-out', str(self.ca), '-subj', '/CN=localhost',
            '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1',
        ], check=True, capture_output=True, timeout=20)
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def respond(self, status, content):
                body = json.dumps(content).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def authenticate(self):
                fixture.requests.append((self.command, self.path))
                if self.headers.get('X-Vault-Token') != fixture.token:
                    self.respond(403, {'errors': ['permission denied']})
                    return False
                if fixture.unavailable:
                    self.respond(503, {'errors': ['sealed fixture']})
                    return False
                if self.path != '/v1/secret/data/logging/authority':
                    self.respond(403, {'errors': ['outside scoped path']})
                    return False
                return True

            def do_GET(self):
                if not self.authenticate():
                    return
                if fixture.document is None:
                    self.respond(404, {'errors': []})
                else:
                    self.respond(200, {'data': {'data': fixture.document, 'metadata': {
                        'version': fixture.version, 'destroyed': False, 'deletion_time': '',
                        'created_time': '2026-11-15T00:00:00Z',
                    }}})

            def do_POST(self):
                if not self.authenticate():
                    return
                content = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if fixture.race_on_write:
                    fixture.document = {'racing_owner': 'retain'}
                    fixture.version = 1
                if content.get('options', {}).get('cas') != 0 or fixture.version:
                    self.respond(400, {'errors': ['check-and-set parameter did not match current version']})
                    return
                fixture.document = content['data']
                fixture.version = 1
                if fixture.mutate_after_write:
                    fixture.document = {'version': 1, 'secrets': {'authority_passphrase': secrets.token_urlsafe(48)}}
                self.respond(200, {'data': {'version': fixture.version}})

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.ca), str(key))
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.address = f'https://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


@unittest.skipUnless(os.name != 'nt' and PLAYBOOK and shutil.which('openssl'),
                     'Requires native Ansible, OpenSSL and POSIX file permissions')
class LoggingCredentialCustody(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='logging-custody-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home = self.base / 'home'
        self.home.mkdir(mode=0o700)
        self.workspace = self.base / 'work'
        self.password_directory = self.home / '.config/tier-0/logging'
        self.cipher = self.workspace / 'credentials/logging-secrets.vault.yml'
        self.password = self.password_directory / 'ansible-vault.password'
        self.receipt = self.workspace / 'credentials/kv-migration.json'
        self.values = {
            'logging_credentials_workspace': str(self.workspace),
            'logging_credentials_repository_name': 'tier-0',
        }
        self.environment = os.environ.copy()
        self.environment.update({'HOME': str(self.home), 'ANSIBLE_NOCOLOR': '1',
                                 'ANSIBLE_PIPELINING': 'true', 'ANSIBLE_CONFIG': str(self.base / 'ansible.cfg')})
        (self.base / 'ansible.cfg').write_text('[defaults]\nretry_files_enabled=False\n', encoding='utf-8')
        self.play = self.base / 'play.yml'
        self.play.write_text(yaml.safe_dump([{
            'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'tasks': [
                {'ansible.builtin.include_role': {'name': str(ROLE)}},
                {'ansible.builtin.copy': {'dest': str(self.base / 'result.json'), 'mode': '0600',
                    'content': '{{ {"secrets": logging_managed_secrets, "verified": '
                               'logging_credentials_migration_verified} | to_json }}'}, 'no_log': True},
            ],
        }]), encoding='utf-8')

    def run_role(self, operation='read', backend='ansible_vault', expected=True, **values):
        variables = self.values | {'logging_credentials_operation': operation,
                                   'logging_credentials_backend': backend} | values
        source = self.base / 'input.json'
        source.write_text(json.dumps(variables), encoding='utf-8')
        source.chmod(0o600)
        output = subprocess.run([PLAYBOOK, '-i', 'localhost,', str(self.play), '-e', '@' + str(source)],
                                env=self.environment, text=True, capture_output=True, timeout=90)
        self.last_output = output.stdout + output.stderr
        self.assertEqual(output.returncode == 0, expected, output.stdout + output.stderr)
        for secret in (self.environment.get('VAULT_TOKEN'), values.get('logging_credentials_seed', {}).get('authority_passphrase')):
            if secret:
                self.assertNotIn(secret, output.stdout + output.stderr)
        if expected:
            return json.loads((self.base / 'result.json').read_text(encoding='utf-8'))
        return output

    def api(self):
        fixture = NativeKV2(self.base)
        self.addCleanup(fixture.close)
        self.environment.update({'VAULT_TOKEN': fixture.token, 'VAULT_ADDR': fixture.address,
                                 'VAULT_CACERT': str(fixture.ca), 'NO_PROXY': '127.0.0.1,localhost',
                                 'no_proxy': '127.0.0.1,localhost'})
        self.values['logging_credentials_vault_path'] = 'logging/authority'
        return fixture

    def run_entry(self, operation='read', backend='ansible_vault', issuer='independent', expected=True,
                  use_default_workspace=False, **values):
        inventory = self.base / 'tier-0/ansible/inventory/hosts.yml'
        inventory.parent.mkdir(parents=True, exist_ok=True)
        inventory.write_text('all:\n  hosts:\n    localhost:\n      ansible_connection: local\n', encoding='utf-8')
        config = self.base / 'ansible.cfg'
        config.write_text('[defaults]\nretry_files_enabled=False\nroles_path=' + str(ROLE.parent) + ':' +
                          str(ROOT / 'shared/ansible/roles') + '\n', encoding='utf-8')
        settings = {
            'logging_workflow_issuer': issuer,
            'logging_workflow_workspace': str(self.workspace),
            'logging_workflow_credential_operation': operation,
            'logging_workflow_credential_backend': backend,
            'logging_credentials_vault_path': 'logging/authority',
        } | values
        if use_default_workspace:
            settings.pop('logging_workflow_workspace')
            self.workspace = (self.home / '.local/share' / (ROOT / 'tier-0').name / 'logging' /
                              settings.get('platform_environment', 'prod'))
            self.cipher = self.workspace / 'credentials/logging-secrets.vault.yml'
            self.receipt = self.workspace / 'credentials/kv-migration.json'
        source = self.base / 'syslog.yml'
        source.write_text(yaml.safe_dump(settings), encoding='utf-8')
        source.chmod(0o600)
        self.environment['CONTROL_NODE_COLLECTIONS_MODE'] = 'check'
        output = subprocess.run([PLAYBOOK, '-i', str(inventory),
            str(ROOT / 'tier-0/ansible/playbooks/deployment/logging-secrets.yml'), '-e', '@' + str(source)],
            env=self.environment, text=True, capture_output=True, timeout=120)
        self.assertEqual(output.returncode == 0, expected, output.stdout + output.stderr)
        if self.environment.get('VAULT_TOKEN'):
            self.assertNotIn(self.environment['VAULT_TOKEN'], output.stdout + output.stderr)
        if values.get('logging_credentials_seed'):
            self.assertNotIn(values['logging_credentials_seed']['authority_passphrase'], output.stdout + output.stderr)
        return output

    def test_native_initialize_and_read_preserve_plaintext_ciphertext_and_owner_modes(self):
        first = self.run_role('initialize')
        ciphertext, unlock = self.cipher.read_bytes(), self.password.read_bytes()
        self.assertTrue(ciphertext.startswith(b'$ANSIBLE_VAULT;'))
        self.assertNotIn(first['secrets']['authority_passphrase'].encode(), ciphertext)
        self.assertEqual(len(first['secrets']['authority_passphrase']), 64)
        self.assertNotIn(first['secrets']['authority_passphrase'], self.last_output)
        self.assertEqual(self.run_role('initialize'), first)
        self.assertIn('changed=0', self.last_output)
        self.assertEqual(self.run_role('read'), first)
        self.assertEqual(self.cipher.read_bytes(), ciphertext)
        self.assertEqual(self.password.read_bytes(), unlock)
        for directory in (self.workspace, self.cipher.parent, self.password.parent):
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
        for file in (self.cipher, self.password):
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)
        self.assertEqual(sorted(path.name for path in self.cipher.parent.iterdir()), [self.cipher.name])

    def test_read_does_not_initialize_or_create_missing_secret_inputs(self):
        self.run_role(expected=False)
        self.assertFalse(self.workspace.exists())
        self.assertFalse(self.password.exists())

    def test_existing_key_without_retained_secret_fails_but_exact_seed_can_be_adopted(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        authority = self.workspace / 'authority'
        authority.mkdir(parents=True, mode=0o700)
        self.workspace.chmod(0o700)
        key = authority / 'key.pem'
        seed = {'authority_passphrase': secrets.token_hex(10)}
        key_bytes = ec.generate_private_key(ec.SECP384R1()).private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.BestAvailableEncryption(seed['authority_passphrase'].encode()))
        key.write_bytes(key_bytes)
        key.chmod(0o600)
        self.run_role('initialize', expected=False)
        self.assertFalse(self.password.exists())
        self.run_role('initialize', expected=False,
                      logging_credentials_seed={'authority_passphrase': secrets.token_urlsafe(48)})
        self.assertFalse(self.cipher.exists())
        self.assertFalse(self.password.exists())
        adopted = self.run_entry('initialize', logging_credentials_seed=seed)
        self.assertIn('community.crypto', adopted.stdout)
        output = self.run_role('read')
        self.assertEqual(output['secrets'], seed)
        self.assertEqual(key.read_bytes(), key_bytes)

    def test_missing_unlock_never_generates_a_replacement(self):
        self.run_role('initialize')
        original = self.cipher.read_bytes()
        self.password.unlink()
        self.run_role('initialize', expected=False)
        self.assertFalse(self.password.exists())
        self.assertEqual(self.cipher.read_bytes(), original)

    def test_wrong_unlock_and_changed_seed_never_rewrite_the_secret(self):
        self.run_role('initialize')
        original, password = self.cipher.read_bytes(), self.password.read_bytes()
        self.run_role('initialize', expected=False,
                      logging_credentials_seed={'authority_passphrase': secrets.token_urlsafe(48)})
        self.password.write_text(secrets.token_urlsafe(60), encoding='utf-8')
        self.run_role('initialize', expected=False)
        self.assertEqual(self.cipher.read_bytes(), original)
        self.password.write_bytes(password)

    def test_symlink_shared_directory_and_custody_colocation_are_rejected_before_creation(self):
        outside = self.base / 'outside'
        outside.mkdir(mode=0o700)
        self.workspace.symlink_to(outside, target_is_directory=True)
        self.run_role('initialize', expected=False)
        self.workspace.unlink()
        self.workspace.mkdir(mode=0o755)
        self.run_role('initialize', expected=False)
        self.workspace.chmod(0o700)
        self.run_role('initialize', expected=False,
                      logging_credentials_password_directory=str(self.workspace / 'unlock'))
        self.assertFalse(self.cipher.exists())
        self.assertFalse(self.password.exists())

    def test_native_kv2_migration_readback_retry_and_explicit_remote_read(self):
        fixture = self.api()
        first = self.run_role('initialize')
        ciphertext, unlock = self.cipher.read_bytes(), self.password.read_bytes()
        migrated = self.run_role('migrate', 'hashicorp_vault')
        self.assertTrue(migrated['verified'])
        self.assertEqual(migrated['secrets'], first['secrets'])
        self.assertEqual(fixture.document, {'version': 1, 'secrets': first['secrets']})
        self.assertEqual(self.run_role('migrate', 'hashicorp_vault'), migrated)
        self.assertEqual(sum(method == 'POST' for method, _ in fixture.requests), 1)
        self.assertEqual(self.cipher.read_bytes(), ciphertext)
        self.assertEqual(self.password.read_bytes(), unlock)
        self.assertNotIn(first['secrets']['authority_passphrase'], self.receipt.read_text(encoding='utf-8'))
        self.password.unlink()
        self.assertEqual(self.run_role('read', 'hashicorp_vault')['secrets'], first['secrets'])

    def test_conflicting_destination_fails_without_overwrite_or_verified_receipt(self):
        fixture = self.api()
        self.run_role('initialize')
        fixture.document, fixture.version = {'other_owner': 'retain'}, 1
        self.run_role('migrate', 'hashicorp_vault', expected=False)
        self.assertEqual(fixture.document, {'other_owner': 'retain'})
        self.assertEqual(fixture.requests, [('GET', '/v1/secret/data/logging/authority')])
        self.assertFalse(any(method == 'POST' for method, _ in fixture.requests))
        self.assertFalse(self.receipt.exists())

    def test_failed_readback_and_racing_writer_cannot_mark_migration_verified(self):
        fixture = self.api()
        self.run_role('initialize')
        fixture.mutate_after_write = True
        self.run_role('migrate', 'hashicorp_vault', expected=False)
        self.assertEqual(fixture.version, 1)
        self.assertFalse(self.receipt.exists())
        fixture.document, fixture.version = None, 0
        fixture.mutate_after_write = False
        fixture.race_on_write = True
        self.run_role('migrate', 'hashicorp_vault', expected=False)
        self.assertEqual(fixture.document, {'racing_owner': 'retain'})
        self.assertFalse(self.receipt.exists())

    def test_remote_outage_has_no_fallback_to_valid_local_recovery_copy(self):
        fixture = self.api()
        self.run_role('initialize')
        fixture.unavailable = True
        self.run_role('read', 'hashicorp_vault', expected=False)
        self.assertEqual(fixture.requests, [('GET', '/v1/secret/data/logging/authority')])
        self.assertTrue(self.cipher.exists())
        self.assertFalse(self.receipt.exists())

    def test_remote_tls_verification_and_schema_are_required(self):
        fixture = self.api()
        fixture.document, fixture.version = {'unrelated': 'credential'}, 1
        self.run_role('read', 'hashicorp_vault', expected=False)
        self.assertEqual(fixture.requests, [('GET', '/v1/secret/data/logging/authority')])
        wrong_ca = self.base / 'wrong-ca.pem'
        wrong_ca.write_text('untrusted CA', encoding='utf-8')
        fixture.document = {'version': 1, 'secrets': {'authority_passphrase': secrets.token_urlsafe(48)}}
        before = len(fixture.requests)
        self.run_role('read', 'hashicorp_vault', expected=False,
                      logging_credentials_vault_ca_file=str(wrong_ca))
        self.assertEqual(len(fixture.requests), before)

    def test_credentials_only_entrypoint_prepares_native_clients_without_producer_selection(self):
        fixture = self.api()
        initialized = self.run_entry('initialize', use_default_workspace=True)
        self.assertIn('logging-secrets requires Ansible collections: none', initialized.stdout)
        self.assertEqual(self.workspace, self.home / '.local/share/tier-0/logging/prod')
        ciphertext = self.cipher.read_bytes()
        migrated = self.run_entry('migrate', 'hashicorp_vault', use_default_workspace=True)
        self.assertIn('community.hashi_vault', migrated.stdout)
        self.assertIn('Migration verified: True', migrated.stdout)
        self.assertEqual(self.cipher.read_bytes(), ciphertext)
        self.password.unlink()
        read = self.run_entry('read', 'hashicorp_vault', use_default_workspace=True)
        self.assertIn('Logging credential operation read completed', read.stdout)
        self.assertNotIn(fixture.document['secrets']['authority_passphrase'], read.stdout + read.stderr)
        self.assertFalse((self.workspace / 'authority').exists())

    def test_credentials_only_entrypoint_does_not_initialize_unused_pki_secrets(self):
        self.run_entry('initialize', issuer='infrastructure', expected=False)
        self.assertFalse(self.cipher.exists())
        self.assertFalse(self.password.exists())


if __name__ == '__main__':
    unittest.main()
