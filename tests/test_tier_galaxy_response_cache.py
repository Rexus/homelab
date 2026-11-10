"""Native Galaxy bypasses corrupt response metadata without discarding local state."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

import yaml

from tier_repo_test_support import UPSTREAM


PLAY = yaml.safe_load((UPSTREAM / 'shared/ansible/playbooks/control-node.yml').read_text())[0]
NATIVE = os.name != 'nt' and all(shutil.which(cli) for cli in ('ansible-playbook', 'ansible-galaxy'))


@unittest.skipUnless(NATIVE, 'Requires Linux/WSL ansible-playbook and ansible-galaxy')
class GalaxyResponseCache(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='galaxy-response-cache-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.cache = self.root / 'cache'
        self.collections = self.root / 'collections'
        self.cache.mkdir()
        self.collections.mkdir()
        # Do not let user Galaxy servers, credentials or cache settings escape this fixture.
        self.env = {key: value for key, value in os.environ.items() if not key.startswith('ANSIBLE_')}
        self.env.update(HOME=str(self.root), ANSIBLE_HOME=str(self.root / '.ansible'),
                        ANSIBLE_CONFIG=str(self.root / 'ansible.cfg'), ANSIBLE_NOCOLOR='1',
                        ANSIBLE_COLLECTIONS_PATH=str(self.collections),
                        ANSIBLE_GALAXY_CACHE_DIR=str(self.cache))

    def run_cli(self, *argv):
        return subprocess.run(argv, cwd=self.root, env=self.env,
                              capture_output=True, text=True, timeout=60)

    def test_native_no_cache_preserves_state_proxy_and_second_run_idempotence(self):
        requests = []
        origin = 'http://127.0.0.2:9'
        collection_path = '/api/v3/collections/journey_probe/cache/'
        versions_path = collection_path + 'versions/'
        version_path = versions_path + '1.2.3/'
        modified = '2026-01-01T00:00:00Z'

        class GalaxyProxy(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                requests.append(self.path)
                # Only a proxy request can reach this server; the configured origin is closed.
                if not self.path.startswith(origin + '/'):
                    self.send_error(400)
                    return
                path = urlsplit(self.path).path
                if path == '/artifact.tar.gz':
                    content = artifact
                elif path in responses:
                    content = json.dumps(responses[path]).encode()
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)

        server = ThreadingHTTPServer(('127.0.0.1', 0), GalaxyProxy)
        self.addCleanup(server.server_close)
        proxy = f'http://127.0.0.1:{server.server_port}'
        for key in ('http_proxy', 'https_proxy', 'all_proxy'):
            self.env[key] = self.env[key.upper()] = proxy
        self.env['no_proxy'] = self.env['NO_PROXY'] = ''
        (self.root / 'ansible.cfg').write_text(
            '[galaxy]\nserver_list = fixture\n'
            f'[galaxy_server.fixture]\nurl = {origin}/api/\ntimeout = 2\ntoken =\n')

        source = self.root / 'source'
        source.mkdir()
        (source / 'galaxy.yml').write_text(yaml.safe_dump(dict(
            namespace='journey_probe', name='cache', version='1.2.3', readme='README.md',
            authors=['Offline fixture'], license=['MIT'], dependencies={})))
        (source / 'README.md').write_text('Offline collection payload.\n')
        built = self.run_cli('ansible-galaxy', 'collection', 'build', str(source),
                             '--output-path', str(self.root))
        self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        artifact = (self.root / 'journey_probe-cache-1.2.3.tar.gz').read_bytes()
        responses = {
            '/api/': {'available_versions': {'v3': 'v3/'}},
            collection_path: {'updated_at': modified},
            versions_path: {'data': [{'version': '1.2.3'}], 'links': {'next': None}},
            version_path: {
                'namespace': {'name': 'journey_probe'}, 'collection': {'name': 'cache'},
                'version': '1.2.3', 'download_url': origin + '/artifact.tar.gz',
                'artifact': {'sha256': hashlib.sha256(artifact).hexdigest()},
                'metadata': {'dependencies': {}}, 'href': origin + version_path,
            },
        }
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)

        retained = self.collections / 'ansible_collections/journey_probe/retained'
        retained.mkdir(parents=True)
        (retained / 'MANIFEST.json').write_text(json.dumps({'collection_info': dict(
            namespace='journey_probe', name='retained', version='9.0.0', dependencies={})}))
        (retained / 'README.md').write_text('Preserve the existing installed collection.\n')
        (self.cache / 'unrelated-cache').write_bytes(b'preserve other cached artifacts\n')
        expires = (datetime.now(timezone.utc) + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        # Native api.json v1: unexpired paginated metadata lacks its expected results list.
        poisoned = json.dumps({'version': 1, '127.0.0.2:9': {
            'modified': {'journey_probe.cache': modified},
            '/api/': {'expires': expires, 'paginated': False, 'results': responses['/api/']},
            versions_path: {'expires': expires, 'paginated': True},
        }})
        api_cache = self.cache / 'api.json'
        api_cache.write_text(poisoned)
        api_cache.chmod(0o600)
        requirement = dict(name='journey_probe.cache', version='>=1.0.0,<2.0.0')
        broken = self.run_cli('ansible-galaxy', 'collection', 'install',
                              requirement['name'] + ':' + requirement['version'])
        self.assertNotEqual(broken.returncode, 0, broken.stdout + broken.stderr)
        self.assertIn("'results'", broken.stdout + broken.stderr)
        self.assertIn(origin + collection_path, requests)
        self.assertFalse(any(urlsplit(url).path == versions_path for url in requests))
        self.assertNotIn(origin + '/artifact.tar.gz', requests)

        # Reset the same poison in case the failing CLI saved unrelated discovery metadata.
        api_cache.write_text(poisoned)
        # Native --no-cache can write JSON null to api.json; preserve all unrelated state.
        preserved = {path: (path.read_bytes(), path.stat().st_mtime_ns)
                     for folder in (self.cache, self.collections)
                     for path in folder.rglob('*') if path.is_file() and path != api_cache}
        task = deepcopy(next(task for task in PLAY['tasks'] if task['name'] ==
                             'Install missing or incompatible Ansible collections with native Galaxy ranges'))
        playbook = self.root / 'install.yml'
        playbook.write_text(yaml.safe_dump([dict(
            hosts='localhost', connection='local', gather_facts=False,
            vars=dict(control_node_required_collections=[requirement],
                      control_node_still_missing_collections=[],
                      ansible_python_interpreter='{{ ansible_playbook_python }}'),
            tasks=[task, {'ansible.builtin.assert': {'that': [
                "'--no-cache' in control_node_galaxy_install.results[0].cmd",
                "'--clear-response-cache' not in control_node_galaxy_install.results[0].cmd"]}}],
        )], sort_keys=False))
        installed = self.collections / 'ansible_collections/journey_probe/cache'
        for attempt in range(2):
            requests.clear()
            result = self.run_cli('ansible-playbook', '-i', 'localhost,', str(playbook))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(f'changed={1 if attempt == 0 else 0}', result.stdout)
            for path, content_and_mtime in preserved.items():
                self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), content_and_mtime, str(path))
            if attempt == 0:
                self.assertTrue(any(urlsplit(url).path == versions_path for url in requests), requests)
                self.assertIn(origin + version_path, requests)
                self.assertEqual(requests.count(origin + '/artifact.tar.gz'), 1)
                manifest = json.loads((installed / 'MANIFEST.json').read_text())
                self.assertEqual(manifest['collection_info']['version'], '1.2.3')
                self.assertEqual((installed / 'README.md').read_bytes(), (source / 'README.md').read_bytes())
                preserved.update({path: (path.read_bytes(), path.stat().st_mtime_ns)
                                  for path in self.collections.rglob('*') if path.is_file()})
            else:
                self.assertEqual(requests, [], 'Compatible installed range should need no API requests')


if __name__ == '__main__':
    unittest.main()
