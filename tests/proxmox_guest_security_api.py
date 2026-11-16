"""TLS API fixture for exercising the installed native Proxmox modules, never a real cluster."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import ssl
import threading
from urllib.parse import parse_qs, unquote, urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


class GuestSecurityAPI:
    def __init__(self, directory):
        self.config = dict(name='vm-1', bios='ovmf', machine='q35', memory=2048, cores=2,
                           boot='order=scsi0', efidisk0='local-zfs:vm-701-disk-0,efitype=4m,pre-enrolled-keys=1',
                           scsi0='local-zfs:vm-701-disk-1,size=30G', scsi1='local-zfs:vm-701-disk-2,size=80G',
                           net0='virtio=BC:24:11:00:00:01,bridge=edge,firewall=1',
                           usb0='mapping=approved-hsm', smbios1='uuid=fixture-original-identity',
                           cipassword='private-fixture-cloud-init-value')
        self.status = 'running'
        self.template = False
        self.hastate = ''
        self.pending = {}
        self.calls = []
        self.failure = ''
        self.storage = dict(storage='local-zfs', content='images,rootdir', type='zfspool')
        self.exists = True
        self.refresh_digest()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, data, code=200):
                encoded = json.dumps(dict(data=data)).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def do_GET(self):
                url = urlsplit(self.path)
                path = unquote(url.path).removeprefix('/api2/json')
                owner.calls.append(('GET', path, parse_qs(url.query)))
                if path == '/version':
                    return self.respond(dict(version='9.1.0'))
                if path == '/nodes':
                    return self.respond([dict(node='pve01', status='online')])
                if path in ('/cluster/resources', '/nodes/pve01/qemu'):
                    return self.respond([owner.vm()] if owner.exists else [])
                if path == '/storage/local-zfs':
                    return self.respond(deepcopy(owner.storage))
                if path == '/nodes/pve01/qemu/701/config':
                    config = deepcopy(owner.config)
                    if parse_qs(url.query).get('current') == ['0']:
                        config.update(owner.pending)
                    return self.respond(config)
                if path == '/nodes/pve01/qemu/701/status/current':
                    return self.respond(dict(status=owner.status))
                if path.startswith('/nodes/pve01/tasks/') and path.endswith('/status'):
                    return self.respond(dict(status='stopped', exitstatus='OK'))
                return self.respond(dict(unexpected=path), 404)

            def fields(self):
                length = int(self.headers.get('Content-Length', 0))
                return {key: value[-1] for key, value in
                        parse_qs(self.rfile.read(length).decode(), keep_blank_values=True).items()}

            def do_POST(self):
                path = urlsplit(self.path).path.removeprefix('/api2/json')
                fields = self.fields()
                owner.calls.append(('POST', path, fields))
                if path == '/nodes/pve01/qemu/701/status/shutdown':
                    if owner.failure == 'shutdown':
                        return self.respond(dict(error='fixture shutdown refusal'), 500)
                    owner.status = 'stopped'
                    if owner.failure == 'changed-during-shutdown':
                        owner.config['memory'] = 4096
                        owner.refresh_digest()
                    return self.respond('UPID:pve01:fixture:shutdown:')
                if path == '/nodes/pve01/qemu/701/status/start':
                    owner.status = 'running'
                    return self.respond('UPID:pve01:fixture:start:')
                return self.respond(dict(unexpected=path), 404)

            def do_PUT(self):
                path = urlsplit(self.path).path.removeprefix('/api2/json')
                fields = self.fields()
                owner.calls.append(('PUT', path, fields))
                if path != '/nodes/pve01/qemu/701/config':
                    return self.respond(dict(unexpected=path), 404)
                if fields.get('digest') != owner.config['digest'] or owner.failure == 'digest':
                    return self.respond(dict(error='fixture concurrent digest mismatch'), 409)
                if owner.failure == 'allocation':
                    return self.respond(dict(error='fixture allocation refusal'), 500)
                if set(fields) != {'digest', 'tpmstate0'} or fields['tpmstate0'] != 'local-zfs:1,version=v2.0':
                    return self.respond(dict(error='fixture rejected unexpected configuration mutation'), 400)
                if 'tpmstate0' in owner.config or owner.status != 'stopped':
                    return self.respond(dict(error='fixture rejects replacement or running allocation'), 400)
                owner.config['tpmstate0'] = 'local-zfs:vm-701-disk-3,size=4M,version=v2.0'
                if owner.failure == 'unexpected-after-allocation':
                    owner.config['net0'] = 'virtio=BC:24:11:00:00:02,bridge=edge'
                owner.refresh_digest()
                return self.respond(None)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
        certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                       .public_key(key.public_key()).serial_number(x509.random_serial_number())
                       .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
                       .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
                       .add_extension(x509.SubjectAlternativeName([
                           x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), False)
                       .add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
                       .sign(key, hashes.SHA256()))
        self.ca = Path(directory) / 'fixture-ca.pem'
        self.ca.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        keyfile = Path(directory) / 'fixture-server.pem'
        keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                             serialization.NoEncryption()))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.ca, keyfile)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def vm(self):
        return dict(vmid=701, name=self.config['name'], node='pve01', status=self.status,
                    template=int(self.template), hastate=self.hastate, type='qemu')

    def refresh_digest(self):
        content = {key: value for key, value in self.config.items() if key != 'digest'}
        self.config['digest'] = hashlib.sha1(json.dumps(content, sort_keys=True).encode()).hexdigest()

    @property
    def endpoint(self):
        return f'https://localhost:{self.server.server_address[1]}'

    @property
    def writes(self):
        return [call for call in self.calls if call[0] != 'GET']

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
