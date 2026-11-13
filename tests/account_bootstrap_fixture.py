"""Isolated NetBox 4.5+/4.7-shaped TLS API for native collection tests; no external services."""

from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import ssl
import threading
from urllib.parse import parse_qs, urlsplit


class NetBoxFixture:
    def __init__(self, certificate, private_key):
        self.admin = secrets.token_hex(20)
        self.secret = secrets.token_urlsafe(24).replace('-', 'a').replace('_', 'b')
        self.key = 'AuditKey0001'
        self.rows = {'users': [], 'permissions': [], 'tokens': []}
        self.writes = []
        self.superuser = False
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, body, code=200):
                payload = json.dumps(body).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('API-Version', '4.7')
                self.end_headers()
                self.wfile.write(payload)

            def authorized(self):
                scheme = 'Bearer ' if fixture.admin.startswith('nbt_') else 'Token '
                return self.headers.get('Authorization') == scheme + fixture.admin

            def do_GET(self):
                url = urlsplit(self.path)
                if url.path == '/api/core/object-changes/':
                    expected = 'Bearer nbt_' + fixture.key + '.' + fixture.secret
                    return self.respond({'count': 0, 'results': [], 'next': None},
                                        200 if self.headers.get('Authorization') == expected else 403)
                if not self.authorized():
                    return self.respond({'detail': 'Unauthorized fixture request'}, 403)
                if url.path == '/api/':
                    return self.respond({})
                if url.path == '/api/status/':
                    return self.respond({'netbox-version': '4.7.3'})
                parts = url.path.strip('/').split('/')
                if len(parts) < 3 or parts[2] not in fixture.rows:
                    return self.respond({'detail': 'Unknown fixture route'}, 404)
                kind = parts[2]
                rows = deepcopy(fixture.rows[kind])
                params = parse_qs(url.query)
                if 'username' in params:
                    rows = [r for r in rows if r['username'] == params['username'][0]]
                if 'is_superuser' in params:
                    rows = rows if fixture.superuser else []
                if 'name' in params:
                    rows = [r for r in rows if r['name'] == params['name'][0]]
                if 'q' in params:
                    rows = [r for r in rows if params['q'][0] in r.get('name', r.get('username', ''))]
                if 'user_id' in params:
                    rows = [r for r in rows if str(r['user']['id']) == params['user_id'][0]]
                if 'description' in params:
                    rows = [r for r in rows if r['description'] == params['description'][0]]
                for row in rows:
                    row.pop('token', None)
                    if kind == 'permissions':
                        row['users'] = [{'id': u['id'], 'username': u['username']}
                                        for u in fixture.rows['users'] if row['id'] in
                                        [p['id'] for p in u['permissions']]]
                if len(parts) == 4:
                    rows = [r for r in rows if str(r['id']) == parts[3]]
                    return self.respond(rows[0] if rows else {}, 200 if rows else 404)
                return self.respond({'count': len(rows), 'results': rows, 'next': None, 'previous': None})

            def do_POST(self):
                if not self.authorized():
                    return self.respond({'detail': 'Read-only credential'}, 403)
                kind = self.path.strip('/').split('/')[2]
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                fixture.writes.append(('POST', kind, deepcopy(body)))
                row = dict(body, id=len(fixture.rows[kind]) + 1)
                row['url'] = fixture.url + '/api/users/' + kind + '/' + str(row['id']) + '/'
                if kind == 'permissions':
                    row.update(groups=[], users=[])
                elif kind == 'users':
                    assert 'password' in row
                    row.pop('password')
                    row['permissions'] = [deepcopy(p) for p in fixture.rows['permissions']
                                          if p['id'] in body['permissions']]
                elif kind == 'tokens':
                    assert body['write_enabled'] is False
                    row.update(key=fixture.key, token=fixture.secret, version=2, enabled=True,
                               user=dict(id=1, username='audit'), allowed_ips=[])
                fixture.rows[kind].append(deepcopy(row))
                self.respond(row, 201)

            def do_PATCH(self):
                fixture.writes.append(('PATCH', self.path, {}))
                self.respond({'detail': 'Unexpected update in fixture'}, 400)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificate, private_key)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.url = 'https://localhost:' + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
