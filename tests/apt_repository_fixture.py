"""A disposable signed APT repository and client; never install packages or alter host trust."""

from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit


def command(args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, timeout=40, **kwargs)


class AptRepository:
    def __init__(self, root, upstream, runs):
        self.root, self.upstream = root, upstream
        self.available, self.corrupt = True, False
        self.calls, self.files, self.packages = [], {}, {}
        self.home = root / 'signing'
        self.home.mkdir(mode=0o700)
        self.gpg = ['gpg', '--homedir', str(self.home), '--batch', '--pinentry-mode', 'loopback', '--passphrase', '']
        result = command(self.gpg + ['--quick-generate-key', 'Intake test <fixture@example.invalid>', 'rsa2048', 'sign', '1d'])
        if result.returncode:
            raise RuntimeError(result.stderr)
        self.key = root / 'publisher.gpg'
        result = subprocess.run(self.gpg + ['--export-options', 'export-minimal', '--export'], capture_output=True, timeout=20)
        if result.returncode:
            raise RuntimeError(result.stderr.decode())
        self.key.write_bytes(result.stdout)
        entries = []
        for key in runs:
            name = 'intake-' + key.removeprefix('RUN-')
            package = root / name
            (package / 'DEBIAN').mkdir(parents=True)
            (package / 'DEBIAN/control').write_text(
                f'Package: {name}\nVersion: 1.0\nArchitecture: all\nMaintainer: Test <fixture@example.invalid>\n'
                'Description: Disposable software intake acceptance data\n')
            (package / 'payload.txt').write_text('Synthetic package; never installed.\n')
            deb = root / (name + '.deb')
            result = command(['dpkg-deb', '--build', '--root-owner-group', str(package), str(deb)])
            if result.returncode:
                raise RuntimeError(result.stderr)
            data = deb.read_bytes()
            path = '/pool/' + deb.name
            self.files[path] = data
            self.packages[key] = (name, path)
            entries.append(f'Package: {name}\nVersion: 1.0\nArchitecture: all\nFilename: {path[1:]}\n'
                           f'Size: {len(data)}\nSHA256: {hashlib.sha256(data).hexdigest()}\n'
                           'Description: Synthetic retrieval fixture\n')
        packages = ('\n'.join(entries) + '\n').encode()
        self.files['/dists/stable/main/binary-amd64/Packages'] = packages
        now = datetime.now(timezone.utc)
        release = root / 'Release'
        release.write_text('Origin: Intake fixture\nSuite: stable\nCodename: stable\nArchitectures: amd64\nComponents: main\n'
            f'Date: {now:%a, %d %b %Y %H:%M:%S +0000}\nValid-Until: {now + timedelta(days=1):%a, %d %b %Y %H:%M:%S +0000}\n'
            f'SHA256:\n {hashlib.sha256(packages).hexdigest()} {len(packages)} main/binary-amd64/Packages\n')
        signed = root / 'InRelease'
        result = command(self.gpg + ['--digest-algo', 'SHA256', '--output', str(signed), '--clearsign', str(release)])
        if result.returncode:
            raise RuntimeError(result.stderr)
        self.files['/dists/stable/InRelease'] = signed.read_bytes()

    def close(self):
        command(['gpgconf', '--homedir', str(self.home), '--kill', 'gpg-agent'])

    def handler(self):
        repository = self
        class Origin(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def log_message(self, *args):
                pass
            def do_GET(self):
                path = urlsplit(self.path).path
                status = 503 if not repository.available else 200 if path in repository.files else 404
                data = repository.files.get(path, b'Not found') if status == 200 else b'Source unavailable'
                if status == 200 and repository.corrupt and path.endswith('.deb'):
                    data = data[:-1] + bytes([data[-1] ^ 1])
                repository.calls.append({'path': path, 'status': status,
                    'cache_control': self.headers.get('Cache-Control', '')})
                self.send_response(status)
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'public, max-age=600' if path.endswith('.deb') and status == 200 else 'no-store')
                self.end_headers()
                self.wfile.write(data)
        return Origin

    def client(self, proxy, name='client', trusted=True):
        root = self.root / name
        for directory in ('etc/parts', 'lists/partial', 'cache', 'downloads'):
            (root / directory).mkdir(parents=True, exist_ok=True)
        # Apply the exact owned template. It has no variable substitutions.
        policy = self.upstream / 'shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2'
        (root / 'etc/parts/90package-policy').write_text(policy.read_text())
        key = self.key
        if not trusted:
            key = root / 'unknown-publisher.gpg'
            key.write_bytes(b'')
        (root / 'etc/sources.list').write_text(f'deb [signed-by={key}] http://repo.example.test stable main\n')
        config = root / 'apt.conf'
        config.write_text(f'Dir::Etc "{root / "etc"}";\nDir::Etc::Parts "parts";\nDir::Etc::main "/dev/null";\n'
            'Dir::Etc::sourceparts "-";\nDir::Etc::trusted "/dev/null";\nDir::Etc::trustedparts "-";\n'
            f'Dir::State::lists "{root / "lists"}";\nDir::State::status "/dev/null";\nDir::Cache "{root / "cache"}";\n'
            'Debug::NoLocking "true";\nAcquire::Languages "none";\nAPT::Architecture "amd64";\n'
            'APT::Architectures { "amd64"; };\nAcquire::Retries "0";\nAcquire::http::Timeout "3";\n'
            f'Acquire::http::Proxy "http://127.0.0.1:{proxy}";\n')
        return root, dict(os.environ, APT_CONFIG=str(config), LC_ALL='C')

    def apt(self, client, *args, folder=None):
        root, environment = client
        destination = root / 'downloads' / (folder or 'metadata')
        destination.mkdir(exist_ok=True)
        return command(['apt-get', *args], env=environment, cwd=destination)
