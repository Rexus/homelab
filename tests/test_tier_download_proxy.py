"""Native artifact downloads use configured intake without an interactive login shell."""

from copy import deepcopy
import hashlib
import http.server
import os
from pathlib import Path
import shutil
import subprocess
import threading
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


CONTENT = b'approved local artifact fixture\n'


class Proxy(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.requests.append(self.path)
        self.send_response(200)
        self.send_header('Content-Length', str(len(CONTENT)))
        self.end_headers()
        self.wfile.write(CONTENT)


@unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires Linux Ansible')
class ArtifactIntake(TierRepositoryTestCase):
    def test_source_and_generated_downloads_use_proxy_checksum_and_native_idempotence(self):
        self.generate()
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Proxy)
        server.requests = []
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        digest = hashlib.sha256(CONTENT).hexdigest()
        url = 'http://intake-fixture.invalid/approved-artifact'
        tasks = []
        for collection, prefix in ((UPSTREAM, ''), (self.root, 'verify-')):
            for tier, role in (('tier-1', 'development_data'),):
                source = collection / f'{prefix}{tier}/ansible/roles/{role}/tasks/host.yml'
                task = deepcopy(next(item for item in yaml.safe_load(source.read_text())
                                     if 'ansible.builtin.get_url' in item))
                task['ansible.builtin.get_url']['dest'] = str(Path(self.temp.name) / f'{prefix}{role}')
                tasks.append(task)
                tasks.append({
                    'name': 'Disabled intake does not force a proxy onto the task',
                    'ansible.builtin.assert': {'that': ['download_environment == {}']},
                    'vars': {'repository_proxy_enabled': False, 'download_environment': task['environment']},
                })
        playbook = Path(self.temp.name) / 'artifact-intake.yml'
        playbook.write_text(yaml.safe_dump([{
            'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': {
                'ansible_python_interpreter': '{{ ansible_playbook_python }}',
                'repository_proxy_enabled': True,
                'repository_proxy_url': f'http://127.0.0.1:{server.server_port}',
                'development_data_package_url': url, 'development_data_package_sha256': digest,
                'development_data_package_version': 'fixture',
            },
            'tasks': tasks,
        }]))
        environment = {key: value for key, value in os.environ.items()
                       if key.lower() not in ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')}
        for attempt in range(2):
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)],
                                    env=environment, capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            if attempt:
                self.assertIn('changed=0', result.stdout)
        self.assertEqual(server.requests, [url] * 2)
        for task in tasks[::2]:
            self.assertEqual(Path(task['ansible.builtin.get_url']['dest']).read_bytes(), CONTENT)


if __name__ == '__main__':
    unittest.main()
