"""Loopback Proxmox API fixture; no real VM, storage, or disk operations."""

from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
import threading
from urllib.parse import parse_qs, urlsplit


class TemplateDiskApiFixture:
    def __init__(self, cert, key):
        self.config = {
            'name': 'rocky-template', 'template': 1, 'ostype': 'l26',
            'scsi0': 'local-zfs:base-110-disk-1,size=10G,discard=on,iothread=1',
            'efidisk0': 'local-zfs:base-110-disk-0,efitype=4m',
            'ide2': 'local-zfs:vm-110-cloudinit,media=cdrom',
            'net0': 'virtio=02:00:00:00:00:01,bridge=vmbr0,tag=10,firewall=1,mtu=1500',
            'net1': 'virtio=02:00:00:00:00:02,bridge=vmbr1,tag=20,firewall=1',
            'cores': 2, 'memory': 2048, 'scsihw': 'virtio-scsi-single',
            'boot': 'order=scsi0', 'bios': 'ovmf', 'machine': 'q35',
            'ipconfig0': 'ip=dhcp', 'ciuser': 'automation',
        }
        self.original = deepcopy(self.config)
        self.status = 'stopped'
        self.writes = []
        self.reads = []
        self.fail_import = False
        fixture = self

        class Api(BaseHTTPRequestHandler):
            def respond(self, data, code=200):
                body = json.dumps({'data': data}).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                fixture.reads.append(self.path)
                path = urlsplit(self.path).path
                vm = dict(vmid=110, name=fixture.config['name'], node='pve01', type='qemu',
                          template=fixture.config['template'], status=fixture.status)
                if path == '/api2/json/cluster/resources':
                    self.respond([vm])
                elif path == '/api2/json/nodes':
                    self.respond([dict(node='pve01', status='online')])
                elif path == '/api2/json/nodes/pve01/qemu':
                    self.respond([vm])
                elif path.endswith('/qemu/110/config'):
                    self.respond(fixture.config)
                elif path.endswith('/qemu/110/status/current'):
                    self.respond(dict(status=fixture.status))
                elif '/tasks/' in path and path.endswith('/status'):
                    self.respond(dict(status='stopped', exitstatus='OK'))
                elif path == '/api2/json/version':
                    self.respond(dict(version='9.2', release='9.2'))
                else:
                    self.respond(None, 404)

            def parameters(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode()
                return {key: values[0] for key, values in parse_qs(body).items()}

            def do_POST(self):
                path, params = urlsplit(self.path).path, self.parameters()
                fixture.writes.append(('POST', path, params))
                if path.endswith('/qemu/110/config') and 'import-from=' in params.get('scsi0', ''):
                    if fixture.fail_import:
                        self.respond(None, 500)
                        return
                    fixture.config['unused0'] = fixture.config['scsi0'].split(',')[0]
                    options = [field for field in params['scsi0'].split(',')[1:]
                               if not field.startswith('import-from=')]
                    fixture.config['scsi0'] = 'local-zfs:base-110-disk-2,size=1M,' + ','.join(options)
                    self.respond('UPID:pve01:00000001:00000001:00000001:qmconfig:110:fixture@pve:')
                else:
                    self.respond(None, 400)

            def do_PUT(self):
                path, params = urlsplit(self.path).path, self.parameters()
                fixture.writes.append(('PUT', path, params))
                if path.endswith('/qemu/110/resize') and params.get('disk') == 'scsi0':
                    fields = [field for field in fixture.config['scsi0'].split(',') if not field.startswith('size=')]
                    fixture.config['scsi0'] = ','.join(fields + ['size=' + params['size']])
                    self.respond(None)
                else:
                    self.respond(None, 400)

            def log_message(self, *_args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Api)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
