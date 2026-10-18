"""Validate ceremony constraints and real HAProxy parsing with disposable material."""

import getpass
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


def command(argv, cwd, **kwargs):
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=120, **kwargs)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result


class PkiOperations(unittest.TestCase):
    @unittest.skipUnless(os.name != 'nt' and os.environ.get('PKI_CLCA_REPOSITORY'),
                         'Requires Linux and verified native clca fixture')
    def test_native_offline_root_constrains_subordinate_and_preserves_existing_key(self):
        from cryptography import x509

        with tempfile.TemporaryDirectory(prefix='clca-ceremony-') as temporary:
            root = Path(temporary)
            (root / 'etc').mkdir()
            templates = UPSTREAM / 'tier-0/templates/offline-root'
            configuration = (templates / 'clca.cfg.example').read_text()
            # This disposable fixture bypasses only interactive custody prompts.
            configuration += "\nBATCH=1\nget_passphrase() { printf '%s' 'test-only-passphrase'; }\n"
            (root / 'etc/clca.cfg').write_text(configuration)
            openssl = (templates / 'openssl.cnf.example').read_text()
            (root / 'etc/openssl.cnf').write_text(
                openssl.replace('REPLACE_WITH_APPROVED_ORGANIZATION', 'Disposable Test')
                .replace('REPLACE_WITH_APPROVED_ROOT_CA_NAME', 'Disposable Root')
                .replace('pki.example.invalid', 'pki.corp.test'))
            clca = ['bash', str(Path(os.environ['PKI_CLCA_REPOSITORY']) / 'bin/clca')]
            command(clca + ['genkey'], root)
            key = (root / 'private/cakey.pem').read_bytes()
            command(clca + ['initialize'], root, input='y\ny\n')
            certificate = x509.load_pem_x509_certificate((root / 'ca/cacert.pem').read_bytes())
            self.assertEqual(certificate.public_key().key_size, 4096)
            self.assertEqual(certificate.extensions.get_extension_for_class(x509.BasicConstraints)
                             .value.path_length, 1)
            command(['openssl', 'req', '-new', '-newkey', 'ec', '-pkeyopt',
                     'ec_paramgen_curve:secp384r1', '-nodes', '-subj', '/CN=Disposable Issuer',
                     '-addext', 'basicConstraints=critical,CA:TRUE,pathlen:5',
                     '-keyout', 'issuer.key', '-out', 'issuer.csr'], root)
            command(clca + ['certify', '--profile', 'level2', '--out', 'issuer.pem', 'issuer.csr'],
                    root, input='y\ny\n')
            issued = x509.load_pem_x509_certificate((root / 'issuer.pem').read_bytes())
            self.assertEqual(issued.extensions.get_extension_for_class(x509.BasicConstraints)
                             .value.path_length, 0)
            command(['openssl', 'verify', '-CAfile', 'ca/cacert.pem', 'issuer.pem'], root)
            command(clca + ['issuecrl'], root)
            command(['openssl', 'crl', '-in', 'crl/ca.crl', '-noout', '-verify',
                     '-CAfile', 'ca/cacert.pem'], root)
            repeated = subprocess.run(clca + ['genkey'], cwd=root, capture_output=True, timeout=10)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual((root / 'private/cakey.pem').read_bytes(), key)

    @unittest.skipUnless(shutil.which('ansible-playbook') and os.environ.get('PKI_HAPROXY_BINARY'),
                         'Requires Linux Ansible and native HAProxy parser')
    def test_real_haproxy_parser_accepts_bootstrap_and_verified_tls_configuration(self):
        role = UPSTREAM / 'tier-2/ansible/roles/edge_load_balancer'
        with tempfile.TemporaryDirectory(prefix='https-parser-') as temporary:
            root = Path(temporary)
            command(['openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt',
                     'ec_paramgen_curve:prime256v1', '-nodes', '-days', '2',
                     '-subj', '/CN=www.corp.test', '-addext', 'subjectAltName=DNS:www.corp.test',
                     '-keyout', 'key.pem', '-out', 'cert.pem'], root)
            (root / 'public.pem').write_bytes((root / 'cert.pem').read_bytes()
                                            + (root / 'key.pem').read_bytes())
            variables = yaml.safe_load((role / 'defaults/main.yml').read_text())
            variables.update(edge_acme_enabled=True, edge_acme_domains=['www.corp.test'],
                             edge_public_https_backend='website', edge_haproxy_backends={
                                 'website': {'servers': [dict(name='app', address='127.0.0.1', port=9443,
                                     tls=True, verify_hostname='origin.corp.test',
                                     ca_file=str(root / 'cert.pem'))]}})
            plays = []
            for live in (False, True):
                plays.append(dict(hosts='localhost', connection='local', gather_facts=False,
                    vars=dict(variables, edge_public_certificate=dict(stat=dict(exists=live))),
                    tasks=[{'ansible.builtin.template': dict(
                        src=str(role / 'templates/haproxy.cfg.j2'),
                        dest=str(root / f'haproxy-{live}.cfg'), mode='0600')}]))
            playbook = root / 'render.yml'
            playbook.write_text(yaml.safe_dump(plays))
            command(['ansible-playbook', '-i', 'localhost,', str(playbook)], root)
            for live in (False, True):
                configuration = root / f'haproxy-{live}.cfg'
                rendered = configuration.read_text()
                self.assertIn('verify required ca-file', rendered)
                self.assertIn('verifyhost origin.corp.test sni str(origin.corp.test)', rendered)
                self.assertEqual('frontend public_https' in rendered, live)
                self.assertEqual('TLS setup incomplete' in rendered, not live)
                # Parse as the unprivileged test account without touching /etc or starting a listener.
                rendered = rendered.replace('user haproxy', f'user {getpass.getuser()}')
                rendered = rendered.replace('group haproxy', f'group {getpass.getuser()}')
                rendered = rendered.replace('/etc/haproxy/certificates/public.pem', str(root / 'public.pem'))
                configuration.write_text(rendered)
                command([os.environ['PKI_HAPROXY_BINARY'], '-c', '-f', str(configuration)], root)

    def test_restore_and_key_creation_are_explicit_and_never_normal_convergence(self):
        role = UPSTREAM / 'tier-0/ansible/roles/openxpki'
        defaults = yaml.safe_load((role / 'defaults/main.yml').read_text())
        self.assertFalse(defaults['openxpki_create_issuer_key'])
        self.assertFalse(defaults['openxpki_restore_approved'])
        main = (role / 'tasks/main.yml').read_text()
        for sensitive in ('bootstrap.yml', 'restore.yml', 'backup.yml'):
            self.assertNotIn(sensitive, main)
        restore = (role / 'tasks/restore.yml').read_text()
        for guard in ('restore-attempt.json', 'openxpki_restore_history',
                      'openxpki_restore_manifest_sha256', 'openxpki_restore_binding == openxpki_binding'):
            self.assertIn(guard, restore)
        self.assertNotIn('state: started', restore)
