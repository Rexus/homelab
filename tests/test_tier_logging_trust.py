"""Native issuer/renewal/revocation without infrastructure or exported producer keys."""

from pathlib import Path
from datetime import datetime, timedelta, timezone
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


@unittest.skipUnless(shutil.which('ansible-playbook') and shutil.which('openssl'), 'Requires native Ansible/crypto')
class ProducerAuthority(unittest.TestCase):
    def test_reviewed_csr_signing_renewal_revocation_and_key_custody(self):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

        with tempfile.TemporaryDirectory(prefix='logging-trust-') as temporary:
            root = Path(temporary)
            key = ec.generate_private_key(ec.SECP384R1())
            csr = (x509.CertificateSigningRequestBuilder()
                   .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'producer')]))
                   .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                   .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), True)
                   .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), False)
                   .sign(key, hashes.SHA256()))
            request = root / 'producer.csr'
            request.write_bytes(csr.public_bytes(serialization.Encoding.PEM))
            public_der = key.public_key().public_bytes(serialization.Encoding.DER,
                                                      serialization.PublicFormat.SubjectPublicKeyInfo)
            import hashlib
            fingerprint = ':'.join(f'{byte:02x}' for byte in hashlib.sha256(public_der).digest())
            variables = dict(logging_authority_directory=str(root / 'authority'),
                             logging_authority_passphrase='disposable-test-signing-passphrase',
                             logging_authority_initialize=True,
                             logging_authority_requests=[dict(name='producer', profile='client',
                                                              csr=str(request), key_sha256=fingerprint)])
            playbook = root / 'issue.yml'

            def run(expect_success=True):
                playbook.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local',
                    gather_facts=False, vars=variables,
                    roles=[str(UPSTREAM / 'tier-0/ansible/roles/logging_authority')])]))
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)],
                                        text=True, capture_output=True, timeout=60)
                self.assertEqual(result.returncode == 0, expect_success, result.stdout + result.stderr)

            variables['logging_authority_initialize'] = False
            run(False)
            variables['logging_authority_initialize'] = True
            run()
            leaf = root / 'authority/public/producer.pem'
            first = leaf.read_bytes()
            run()
            self.assertEqual(leaf.read_bytes(), first)
            self.assertFalse((root / 'authority/public/key.pem').exists())

            original = x509.load_pem_x509_certificate(first)
            ca = x509.load_pem_x509_certificate((root / 'authority/ca.pem').read_bytes())
            signing_key = serialization.load_pem_private_key((root / 'authority/key.pem').read_bytes(),
                                                             b'disposable-test-signing-passphrase')
            now = datetime.now(timezone.utc)
            expiring = (x509.CertificateBuilder().subject_name(original.subject).issuer_name(ca.subject)
                        .public_key(key.public_key()).serial_number(x509.random_serial_number())
                        .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1)))
            for extension in original.extensions:
                expiring = expiring.add_extension(extension.value, extension.critical)
            leaf.write_bytes(expiring.sign(signing_key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM))
            run()
            first = leaf.read_bytes()
            self.assertGreater(x509.load_pem_x509_certificate(first).not_valid_after_utc,
                               now + timedelta(days=60))

            receiver = root / 'receiver'
            request_play = root / 'receiver-request.yml'
            request_play.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                vars=dict(logging_receiver_directory=str(receiver), logging_receiver_name='receiver',
                          logging_receiver_dns='logs.internal.example'),
                tasks=[{'ansible.builtin.include_role':
                        dict(name=str(UPSTREAM / 'tier-0/ansible/roles/logging_authority'),
                             tasks_from='receiver-request')}])]))
            for attempt in range(2):
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(request_play)],
                                        text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if attempt == 0:
                    receiver_key = (receiver / 'key.pem').read_bytes()
            self.assertEqual((receiver / 'key.pem').read_bytes(), receiver_key)
            server_csr = x509.load_pem_x509_csr((receiver / 'server.csr').read_bytes())
            server_public = server_csr.public_key().public_bytes(serialization.Encoding.DER,
                                                               serialization.PublicFormat.SubjectPublicKeyInfo)
            server_fingerprint = ':'.join(f'{byte:02x}' for byte in hashlib.sha256(server_public).digest())
            variables['logging_authority_requests'].append(dict(name='receiver', profile='server',
                csr=str(receiver / 'server.csr'), key_sha256=server_fingerprint,
                san=['DNS:logs.internal.example']))
            run()
            subprocess.run(['openssl', 'verify', '-CAfile', str(root / 'authority/ca.pem'),
                '-purpose', 'sslserver', '-verify_hostname', 'logs.internal.example',
                str(root / 'authority/public/receiver.pem')], check=True, capture_output=True, timeout=10)

            certificate = x509.load_pem_x509_certificate(first)
            variables['logging_authority_revocations'] = [dict(serial_number=certificate.serial_number,
                revocation_date='20261019000000Z', reason='key_compromise')]
            run()
            verification = subprocess.run(['openssl', 'verify', '-CAfile', str(root / 'authority/ca.pem'),
                '-CRLfile', str(root / 'authority/public/revoked.pem'), '-crl_check', '-purpose', 'sslclient',
                str(leaf)], capture_output=True, text=True, timeout=10)
            self.assertNotEqual(verification.returncode, 0)
            self.assertIn('revoked', verification.stderr)
            variables['logging_authority_requests'][0]['key_sha256'] = ':'.join(['00'] * 32)
            run(False)
