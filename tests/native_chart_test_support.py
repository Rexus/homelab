"""Real HTTPS Helm fixtures from exact cached packages; no network or TLS bypass.

NATIVE_CHART_CACHE optionally redirects repository lookup for native Ansible
tests. Chart selection, pinned versions, values and Helm execution stay real.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import partial
import hashlib
import http.server
import ipaddress
import os
from pathlib import Path
import shutil
import ssl
import tarfile
import threading

import yaml


def make_test_certificate(name):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                   .public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1))
                   .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                   .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),
                                  x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
                   .sign(key, hashes.SHA256()))
    return (key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                              serialization.NoEncryption()), certificate.public_bytes(serialization.Encoding.PEM))


@contextmanager
def cached_https_repository(directory, cache):
    """Serve unchanged native archives through Helm's verified HTTPS repository path."""
    directory.mkdir()
    entries = {}
    for package in sorted(Path(cache).glob('*.tgz')):
        shutil.copyfile(package, directory / package.name)
        with tarfile.open(package) as archive:
            metadata = next(member for member in archive.getmembers() if member.name.count('/') == 1
                            and member.name.endswith('/Chart.yaml'))
            chart = yaml.safe_load(archive.extractfile(metadata).read())
        chart['urls'] = [package.name]
        chart['digest'] = hashlib.sha256(package.read_bytes()).hexdigest()
        entries.setdefault(chart['name'], []).append(chart)
    if not entries:
        raise ValueError(f'No native chart packages (*.tgz) in {cache}')
    (directory / 'index.yaml').write_text(yaml.safe_dump({'apiVersion': 'v1', 'entries': entries}))
    key, certificate = make_test_certificate('native-offline-chart-cache')
    key_path, ca_path = directory.parent / 'test-key.pem', directory.parent / 'test-ca.pem'
    key_path.write_bytes(key)
    key_path.chmod(0o600)
    ca_path.write_bytes(certificate)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(ca_path, key_path)

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(directory)))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'https://127.0.0.1:{server.server_port}', ca_path
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@contextmanager
def native_chart_fixture(directory, release_variable):
    """Override only a real release's repository via Ansible's extra-variable precedence."""
    cache = os.environ.get('NATIVE_CHART_CACHE')
    if not cache:
        yield {}, {}
        return
    with cached_https_repository(directory, cache) as (repository, ca_path):
        inputs = {'helm_release_spec':
                  "{{ " + release_variable + " | combine({'repository': '" + repository + "'}) }}"}
        yield inputs, {
            'SSL_CERT_FILE': str(ca_path),
            'HELM_CACHE_HOME': str(directory.parent / 'helm-cache'),
            'HELM_CONFIG_HOME': str(directory.parent / 'helm-config'),
            'HELM_DATA_HOME': str(directory.parent / 'helm-data'),
        }
