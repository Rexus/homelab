"""Small native signed repositories, confined to disposable directories."""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import gzip
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import ssl
import threading


def run(argv, **kwargs):
    result = subprocess.run([str(arg) for arg in argv], capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise AssertionError(f'{argv[0]} failed: {result.stdout}\n{result.stderr}')
    return result.stdout


class SignedRepositoryFixture:
    def __init__(self, root):
        self.root = root
        self.home = root / 'gnupg'
        self.home.mkdir(mode=0o700)
        run(['gpg', '--batch', '--homedir', self.home, '--pinentry-mode', 'loopback', '--passphrase', '',
             '--quick-gen-key', 'Intake fixture <fixture@example.invalid>', 'rsa2048', 'sign', '0'])
        records = run(['gpg', '--homedir', self.home, '--with-colons', '--list-keys'])
        self.fingerprint = next(line.split(':')[9] for line in records.splitlines() if line.startswith('fpr:'))
        self.key = root / 'publisher.asc'
        self.keyring = root / 'publisher.gpg'
        self.key.write_text(run(['gpg', '--homedir', self.home, '--armor', '--export', self.fingerprint]))
        with self.keyring.open('wb') as stream:
            subprocess.run(['gpg', '--homedir', str(self.home), '--export', self.fingerprint],
                           stdout=stream, stderr=subprocess.PIPE, check=True)

    def close(self):
        subprocess.run(['gpgconf', '--homedir', str(self.home), '--kill', 'gpg-agent'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    def sign(self, source, target, clearsign=False, signers=None):
        selectors = [value for signer in signers or [self.fingerprint] for value in ('--local-user', signer)]
        run(['gpg', '--batch', '--yes', '--homedir', self.home, '--pinentry-mode', 'loopback',
             '--passphrase', '', *selectors, '--armor',
             '--output', target, '--clearsign' if clearsign else '--detach-sign', source])

    def add_signer(self):
        run(['gpg', '--batch', '--homedir', self.home, '--pinentry-mode', 'loopback', '--passphrase', '',
             '--quick-gen-key', 'Additional fixture signer <extra@example.invalid>', 'rsa2048', 'sign', '0'])
        records = run(['gpg', '--homedir', self.home, '--with-colons', '--list-keys'])
        return next(line.split(':')[9] for line in records.splitlines()
                    if line.startswith('fpr:') and line.split(':')[9] != self.fingerprint)

    def apt(self, name='apt', expired=False, distribution='fixture', codename=None, origin='Fixture'):
        repository = self.root / name
        package = self.root / f'{name}-package'
        (package / 'DEBIAN').mkdir(parents=True)
        (package / 'DEBIAN/control').write_text(
            'Package: intake-fixture\nVersion: 1.0\nArchitecture: all\nMaintainer: Fixture <fixture@example.invalid>\n'
            'Description: Offline intake integrity fixture\n')
        (package / 'usr/share/intake-fixture').mkdir(parents=True)
        (package / 'usr/share/intake-fixture/data').write_text('signed index binds these package bytes\n')
        destination = repository / 'pool/main/i/intake-fixture/fixture_1.0_all.deb'
        destination.parent.mkdir(parents=True)
        run(['dpkg-deb', '--build', '--root-owner-group', package, destination])
        dist_path = repository / 'dists' / distribution
        index = dist_path / 'main/binary-amd64/Packages'
        index.parent.mkdir(parents=True)
        index.write_text(run(['apt-ftparchive', 'packages', 'pool'], cwd=repository))
        with gzip.GzipFile(str(index) + '.gz', 'wb', mtime=0) as stream:
            stream.write(index.read_bytes())
        metadata = run(['apt-ftparchive', 'release', f'dists/{distribution}'], cwd=repository)
        metadata = '\n'.join(line for line in metadata.splitlines() if not line.startswith('Date:'))
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(days=-1 if expired else 2)
        release = dist_path / 'Release'
        release.write_text(f'Origin: {origin}\nSuite: {distribution}\nCodename: {codename or distribution}\n'
                           'Architectures: amd64\nComponents: main\n'
                           f'Date: {format_datetime(now - timedelta(days=2))}\n'
                           f'Valid-Until: {format_datetime(expiry)}\n{metadata}\n')
        self.sign(release, dist_path / 'Release.gpg')
        self.sign(release, dist_path / 'InRelease', clearsign=True)
        return repository
    def rpm(self, name='rpm', signed=True):
        repository = self.root / name
        repository.mkdir()
        build = self.root / f'{name}-build'
        (build / 'SPECS').mkdir(parents=True)
        for version in ('1.0', '2.0'):
            spec = build / 'SPECS/fixture.spec'
            spec.write_text(f'''Name: intake-fixture
Version: {version}
Release: 1
Summary: Local intake integrity fixture
License: MIT
BuildArch: noarch
%description
Native RPM fixture with no scriptlets or dependencies.
%install
mkdir -p %{{buildroot}}/usr/share/intake-fixture
echo fixture > %{{buildroot}}/usr/share/intake-fixture/data
%files
/usr/share/intake-fixture/data
''')
            run(['rpmbuild', '--define', f'_topdir {build}', '--define', '__os_install_post %{nil}',
                 '--define', '_build_id_links none', '-bb', spec])
        for package in (build / 'RPMS/noarch').glob('*.rpm'):
            destination = repository / package.name
            shutil.copyfile(package, destination)
            if signed:
                run(['rpmsign', '--define', f'_gpg_name {self.fingerprint}',
                     '--define', f'_gpg_path {self.home}', '--define', '__gpg /usr/bin/gpg',
                     '--addsign', destination], env=dict(os.environ, GNUPGHOME=str(self.home)))
        run(['createrepo_c', '--checksum', 'sha256', repository])
        self.sign(repository / 'repodata/repomd.xml', repository / 'repodata/repomd.xml.asc')
        return repository


class RepositoryHttpsFixture:
    def __init__(self, directory, work):
        self.certificate = work / 'fixture.crt'
        key = work / 'fixture.key'
        run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
             '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1',
             '-keyout', key, '-out', self.certificate])
        key.chmod(0o600)
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *_args):
                pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(directory)))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.certificate), str(key))
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'https://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
