"""GitLab recovery fencing against a paginated, verified local HTTPS v4 API double.

No hosted GitLab or production cluster is contacted. Tests exercise real HTTP,
TLS, JSON parsing, native request shapes and private receipt/retry behaviour.
The asynchronous fixture models Sidekiq completion, not an actual GitLab worker.
"""

import copy
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import shutil
import ssl
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import yaml


ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'tier-1/ansible/roles/platform_recovery'
HELPER = ROLE / 'files/gitlab_recovery_fence.py'
SPEC = importlib.util.spec_from_file_location('gitlab_recovery_fence', HELPER)
FENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FENCE)
NATIVE = os.name == 'posix' and shutil.which('openssl')


class GitLabDouble:
    def __init__(self, certificate, key):
        self.token = secrets.token_hex(24)
        self.calls = []
        self.failures = {}
        self.admin = True
        self.version = '18.6.0'
        self.async_cancel = False
        self.worker_enabled = False
        self.worker_polls = 0
        self.cancel_submitted = False
        self.keep_bridge = False
        self.noop_put = False
        self.next_page = None
        self.omit_page_headers = False
        self.raw = None
        self.records = {
            '/runners/1': {'id': 1, 'paused': False, 'description': 'old-instance-runner'},
            '/runners/2': {'id': 2, 'paused': True, 'description': 'old-project-runner'},
            '/projects/1': {'id': 1, 'path_with_namespace': 'retained/first'},
            '/projects/2': {'id': 2, 'path_with_namespace': 'retained/second'},
            '/projects/1/pipeline_schedules/11': {'id': 11, 'active': True, 'cron': '0 * * * *',
                'owner': {'id': 7, 'username': 'original-owner'}},
            '/projects/2/pipeline_schedules/21': {'id': 21, 'active': False, 'cron': '0 1 * * *'},
            '/projects/1/hooks/31': {'id': 31, 'url': 'https://private-sink.invalid/' + secrets.token_hex(12),
                'push_events': True, 'pipeline_events': True, 'enable_ssl_verification': True},
            '/projects/1/pipelines/101': {'id': 101, 'status': 'running', 'source': 'push'},
            '/projects/1/pipelines/102': {'id': 102, 'status': 'manual', 'source': 'parent_pipeline'},
            '/projects/2/pipelines/201': {'id': 201, 'status': 'success', 'source': 'push'},
            '/projects/1/pipelines/101/jobs/41': {'id': 41, 'status': 'running'},
            '/projects/1/pipelines/101/jobs/42': {'id': 42, 'status': 'scheduled'},
            '/projects/1/pipelines/102/jobs/43': {'id': 43, 'status': 'manual'},
            '/projects/2/pipelines/201/jobs/44': {'id': 44, 'status': 'manual', 'allow_failure': True},
            '/projects/2/pipelines/201/bridges/51': {'id': 51, 'status': 'manual'},
        }
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def reply(self, value, status=200, next_page=None, raw=None, location=None):
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                if next_page is not None:
                    self.send_header('X-Next-Page', next_page)
                if location:
                    self.send_header('Location', location)
                self.end_headers()
                self.wfile.write(raw if raw is not None else json.dumps(value).encode())

            def dispatch(self):
                url = urlsplit(self.path)
                path = url.path.removeprefix('/api/v4')
                query = parse_qs(url.query)
                length = int(self.headers.get('Content-Length', '0'))
                body = json.loads(self.rfile.read(length)) if length else None
                fixture.calls.append((self.command, path, query, body))
                if self.headers.get('PRIVATE-TOKEN') != fixture.token:
                    return self.reply({'secret': fixture.token}, 403)
                failure = fixture.failures.get((self.command, path))
                if failure:
                    return self.reply({'secret': fixture.token}, failure, location=fixture.redirect if failure == 302 else None)
                if fixture.raw is not None and path == '/projects':
                    return self.reply(None, raw=fixture.raw)
                if self.command == 'GET':
                    if path == '/user':
                        return self.reply({'id': 1, 'is_admin': fixture.admin})
                    if path == '/version':
                        return self.reply({'version': fixture.version})
                    if fixture.async_cancel and fixture.worker_enabled and fixture.cancel_submitted:
                        fixture.worker_polls += 1
                        if fixture.worker_polls >= 3:
                            for key, value in fixture.records.items():
                                if FENCE.kind(key) in ('pipelines', 'jobs', 'bridges') and value['status'] not in FENCE.TERMINAL:
                                    value['status'] = 'canceled'
                    if path in fixture.records:
                        return self.reply(fixture.records[path])
                    prefix = '/runners/' if path == '/runners/all' else path + '/'
                    values = [value for key, value in fixture.records.items()
                              if key.startswith(prefix) and '/' not in key[len(prefix):]]
                    if path.endswith('/pipelines'):
                        child = query.get('source') == ['parent_pipeline']
                        values = [value for value in values if (value['source'] == 'parent_pipeline') == child]
                    page = int(query.get('page', ['1'])[0])
                    selected = values[page - 1:page]
                    next_page = str(page + 1) if page < len(values) else ''
                    if fixture.next_page is not None:
                        next_page = fixture.next_page
                    if fixture.omit_page_headers:
                        next_page = None
                    return self.reply(selected, next_page=next_page)
                if self.command == 'PUT' and path in fixture.records:
                    if not fixture.noop_put:
                        fixture.records[path].update(body)
                    return self.reply(fixture.records[path])
                if self.command == 'POST' and path.endswith('/cancel'):
                    fixture.cancel_submitted = True
                    target = path.removesuffix('/cancel')
                    if '/pipelines/' in target:
                        for key, value in fixture.records.items():
                            if key != target and not key.startswith(target + '/'):
                                continue
                            if FENCE.kind(key) == 'bridges' and fixture.keep_bridge:
                                continue
                            if value['status'] not in FENCE.TERMINAL:
                                value['status'] = 'canceling' if fixture.async_cancel else 'canceled'
                        return self.reply(fixture.records[target])
                    for key, value in fixture.records.items():
                        if FENCE.kind(key) == 'jobs' and key.split('/')[2] == target.split('/')[2] and key.split('/')[-1] == target.split('/')[-1]:
                            value['status'] = 'canceling' if fixture.async_cancel else 'canceled'
                            return self.reply(value)
                return self.reply({}, 404)

            do_GET = dispatch
            do_PUT = dispatch
            do_POST = dispatch

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificate, key)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'https://127.0.0.1:' + str(self.server.server_port)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


@unittest.skipUnless(NATIVE, 'Requires POSIX private file modes and native OpenSSL')
class GitLabRecoveryFence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.certificates = tempfile.TemporaryDirectory()
        folder = Path(cls.certificates.name)
        cls.certificate, cls.key = folder / 'ca.pem', folder / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-keyout', str(cls.key), '-out', str(cls.certificate), '-subj', '/CN=gitlab-recovery-fixture.invalid',
                        '-addext', 'subjectAltName=IP:127.0.0.1'], capture_output=True, check=True, timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.certificates.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'receipts').mkdir(mode=0o700)
        self.api = GitLabDouble(self.certificate, self.key)
        self.addCleanup(self.api.close)
        self.headers = self.root / 'headers.json'
        self.headers.write_text(json.dumps({'PRIVATE-TOKEN': self.api.token}))
        self.headers.chmod(0o600)
        ca = self.root / 'ca.pem'
        ca.write_bytes(self.certificate.read_bytes())
        self.config = {'workspace': str(self.root), 'plan_sha256': 'a' * 64, 'namespace_uid': 'restored-namespace-uid',
            'product': {'name': 'gitlab', 'namespace': 'gitlab', 'backup_id': 'retained-native-backup',
                'gitlab_recovery': {'api_url': self.api.url, 'ca_file': 'ca.pem', 'ca_sha256': FENCE.digest(ca.read_bytes()),
                    'admin_headers_file': 'headers.json', 'admin_headers_sha256': FENCE.digest(self.headers.read_bytes()),
                    'timeout_seconds': 3, 'cancel_attempts': 2, 'poll_seconds': 0}}}
        self.receipt = self.root / 'receipts/gitlab-gitlab-fence.json'

    def run_fence(self, operation='fence'):
        return FENCE.run(self.config, operation)

    def read_receipt(self):
        return json.loads(self.receipt.read_text())

    def writes(self):
        return [item for item in self.api.calls if item[0] != 'GET']

    def test_paginated_instance_fence_child_manual_delayed_and_original_intent(self):
        result = self.run_fence()
        self.assertTrue(result['changed'])
        self.assertTrue(FENCE.paused(self.api.records))
        self.assertTrue(FENCE.terminal(self.api.records))
        receipt = self.read_receipt()
        self.assertTrue(receipt['verified'])
        self.assertFalse(receipt['original']['/runners/1']['paused'])
        self.assertTrue(receipt['original']['/projects/1/pipeline_schedules/11']['active'])
        self.assertEqual(receipt['original']['/projects/1/pipeline_schedules/11']['owner']['id'], 7)
        self.assertTrue(receipt['original']['/projects/1/hooks/31']['push_events'])
        self.assertEqual(stat.S_IMODE(self.receipt.stat().st_mode), 0o600)
        self.assertTrue(any(path == '/projects' and query.get('page') == ['2'] for _, path, query, _ in self.api.calls))
        self.assertTrue(any(query.get('source') == ['parent_pipeline'] for _, _, query, _ in self.api.calls))
        self.assertTrue(any(query.get('include_retried') == ['true'] for _, _, query, _ in self.api.calls))
        self.assertIn(('POST', '/projects/2/pipelines/201/cancel', {}, None), self.writes())
        self.assertEqual(self.api.records['/projects/2/pipelines/201']['status'], 'success')
        self.assertFalse(any('take_ownership' in path or '/play' in path or '/retry' in path for _, path, _, _ in self.api.calls))

    def test_pause_triggers_then_asynchronous_child_completion_under_caller_worker(self):
        self.api.async_cancel = True
        self.run_fence('pause-triggers')
        self.assertTrue(FENCE.paused(self.api.records))
        self.assertFalse(FENCE.terminal(self.api.records))
        self.assertFalse(self.read_receipt()['verified'])
        self.assertFalse(any(method == 'POST' for method, _, _, _ in self.api.calls))
        self.api.worker_enabled = True  # Parent starts the accepted isolated Sidekiq workload.
        self.run_fence()
        self.assertTrue(self.read_receipt()['verified'])
        self.assertEqual(self.api.records['/projects/1/pipelines/102']['status'], 'canceled')

    def test_cancel_http_200_without_actual_terminal_state_blocks_cutover(self):
        self.api.async_cancel = True
        with self.assertRaisesRegex(FENCE.FenceError, 'remain nonterminal'):
            self.run_fence()
        self.assertFalse(self.read_receipt()['verified'])
        self.assertTrue(FENCE.paused(self.api.records))
        self.assertTrue(any(body == {'force': True} for method, _, _, body in self.writes() if method == 'POST'))

    def test_terminal_parent_with_uncancelled_manual_bridge_remains_blocked(self):
        self.api.keep_bridge = True
        with self.assertRaisesRegex(FENCE.FenceError, 'remain nonterminal'):
            self.run_fence()
        self.assertIn(('POST', '/projects/2/pipelines/201/cancel', {}, None), self.writes())
        self.assertFalse(self.read_receipt()['verified'])

    def test_interrupted_retry_retains_original_intent_and_never_reopens_ci(self):
        self.api.failures['PUT', '/projects/1/pipeline_schedules/11'] = 403
        with self.assertRaisesRegex(FENCE.FenceError, 'HTTP 403'):
            self.run_fence()
        self.assertTrue(self.api.records['/runners/1']['paused'])
        original = self.read_receipt()['original']
        self.api.failures.clear()
        self.run_fence()
        self.assertEqual(original, self.read_receipt()['original'])
        writes = len(self.writes())
        self.assertFalse(self.run_fence()['changed'])
        self.assertEqual(writes, len(self.writes()))
        self.assertFalse(any(body and (body.get('active') is True or body.get('paused') is False) for _, _, _, body in self.writes()))

    def test_readonly_audit_reobserves_states_and_refuses_drift(self):
        self.run_fence()
        before = self.receipt.read_bytes()
        writes = len(self.writes())
        self.run_fence('verify')
        self.assertEqual(before, self.receipt.read_bytes())
        self.assertEqual(writes, len(self.writes()))
        self.api.records['/projects/1/pipeline_schedules/11']['active'] = True
        with self.assertRaisesRegex(FENCE.FenceError, 'Live GitLab'):
            self.run_fence('verify')
        self.assertEqual(writes, len(self.writes()))

    def test_changed_plan_target_backup_or_credentials_reject_receipt_reuse(self):
        self.run_fence()
        original = copy.deepcopy(self.config)
        for mutate in [lambda value: value.update(plan_sha256='b' * 64),
                       lambda value: value.update(namespace_uid='replacement-namespace'),
                       lambda value: value['product'].update(backup_id='different-backup'),
                       lambda value: value['product']['gitlab_recovery'].update(poll_seconds=1)]:
            self.config = copy.deepcopy(original)
            mutate(self.config)
            before = len(self.api.calls)
            with self.assertRaisesRegex(FENCE.FenceError, 'accepted custody changed'):
                self.run_fence()
            self.assertEqual(before, len(self.api.calls))

    def test_redirect_is_refused_without_forwarding_credentials(self):
        self.api.redirect = 'https://127.0.0.1:1/stolen'
        self.api.failures['GET', '/user'] = 302
        with self.assertRaisesRegex(FENCE.FenceError, 'HTTP 302'):
            self.run_fence()
        self.assertEqual(len(self.api.calls), 1)

    def test_proxy_environment_is_ignored_and_ca_verification_is_required(self):
        with patch.dict(os.environ, {'HTTPS_PROXY': 'http://127.0.0.1:1', 'https_proxy': 'http://127.0.0.1:1'}):
            self.run_fence('pause-triggers')
        self.config['product']['gitlab_recovery']['ca_sha256'] = '0' * 64
        calls = len(self.api.calls)
        with self.assertRaisesRegex(FENCE.FenceError, 'checksum changed'):
            self.run_fence()
        self.assertEqual(calls, len(self.api.calls))

    def test_actual_tls_hostname_failure_prevents_authenticated_api_calls(self):
        self.config['product']['gitlab_recovery']['api_url'] = self.api.url.replace('127.0.0.1', 'localhost')
        with self.assertRaisesRegex(FENCE.FenceError, 'verified HTTPS request'):
            self.run_fence()
        self.assertFalse(self.api.calls)

    def test_private_credentials_hash_modes_and_impersonation_rejected_before_http(self):
        self.headers.chmod(0o644)
        with self.assertRaisesRegex(FENCE.FenceError, 'mode 0600'):
            self.run_fence()
        self.headers.chmod(0o600)
        self.headers.write_text(json.dumps({'PRIVATE-TOKEN': self.api.token, 'Sudo': '1'}))
        with self.assertRaisesRegex(FENCE.FenceError, 'checksum changed'):
            self.run_fence()
        self.config['product']['gitlab_recovery']['admin_headers_sha256'] = FENCE.digest(self.headers.read_bytes())
        with self.assertRaisesRegex(FENCE.FenceError, 'without impersonation'):
            self.run_fence()
        self.assertFalse(self.api.calls)

    def test_nonadmin_unsupported_api_and_missing_schedule_owner_permission_fail_closed(self):
        self.api.admin = False
        with self.assertRaisesRegex(FENCE.FenceError, 'instance administrator'):
            self.run_fence()
        self.assertFalse(self.writes())
        self.api.admin = True
        self.api.version = '19.6.0'
        with self.assertRaisesRegex(FENCE.FenceError, 'system-hook scope'):
            self.run_fence()
        self.assertFalse(self.writes())

    def test_pagination_errors_malformed_json_and_unsupported_hook_flags_fail_closed(self):
        self.api.next_page = '1'
        with self.assertRaisesRegex(FENCE.FenceError, 'pagination'):
            self.run_fence()
        self.api.next_page = None
        self.api.raw = b'<html>proxy failure</html>'
        with self.assertRaisesRegex(FENCE.FenceError, 'JSON parsing failed'):
            self.run_fence()
        self.api.raw = None
        self.api.records['/projects/1/hooks/31']['future_events'] = True
        with self.assertRaisesRegex(FENCE.FenceError, 'unsupported webhook'):
            self.run_fence()
        self.assertFalse(self.writes())

    def test_missing_pagination_headers_still_read_every_page(self):
        self.api.omit_page_headers = True
        self.run_fence()
        self.assertIn('/runners/2', self.read_receipt()['original'])
        self.assertIn('/projects/2', self.read_receipt()['original'])

    def test_unsupported_system_hook_intent_retained_and_no_mutation(self):
        self.api.records['/hooks/8'] = {'id': 8, 'url': 'https://hook.invalid', 'push_events': True}
        with self.assertRaisesRegex(FENCE.FenceError, 'no native complete pause'):
            self.run_fence('pause-triggers')
        self.assertIn('/hooks/8', self.read_receipt()['original'])
        self.assertFalse(self.writes())

    def test_noop_pause_update_cannot_pass_as_a_trigger_fence(self):
        self.api.noop_put = True
        with self.assertRaisesRegex(FENCE.FenceError, 'fence was not observed'):
            self.run_fence('pause-triggers')
        self.assertFalse(self.read_receipt()['verified'])
        self.assertFalse(any(method == 'POST' for method, _, _, _ in self.api.calls))

    def test_cli_diagnostics_do_not_print_credentials_response_or_hook_urls(self):
        config = self.root / 'inputs.json'
        config.write_text(json.dumps(self.config))
        config.chmod(0o600)
        self.api.failures['GET', '/user'] = 403
        result = subprocess.run([sys.executable, str(HELPER), '--config', str(config)], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assertIn('HTTP 403', result.stderr)
        self.assertNotIn(self.api.token, result.stdout + result.stderr)
        self.assertNotIn(self.api.records['/projects/1/hooks/31']['url'], result.stdout + result.stderr)


class GitLabFenceTaskContract(unittest.TestCase):
    def test_native_task_contract_and_readonly_input_handling(self):
        tasks = yaml.safe_load((ROLE / 'tasks/gitlab-fence.yml').read_text(encoding='utf-8'))
        copy_task = next(task for task in tasks if 'ansible.builtin.copy' in task)
        self.assertEqual(copy_task['ansible.builtin.copy']['mode'], '0600')
        self.assertEqual(copy_task['when'], "platform_recovery.phase != 'verify'")
        command = next(task for task in tasks if 'ansible.builtin.command' in task)
        self.assertTrue(command['no_log'])
        self.assertIn('gitlab_recovery_fence.py', ' '.join(command['ansible.builtin.command']['argv']))
        self.assertTrue(any('retained_inputs.product == recovery_product' in str(task) for task in tasks))

    @unittest.skipUnless(os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook'), 'Requires native Ansible')
    def test_native_ansible_task_syntax(self):
        with tempfile.TemporaryDirectory() as folder:
            playbook = Path(folder) / 'play.yml'
            playbook.write_text(yaml.safe_dump([{'hosts': 'localhost', 'gather_facts': False,
                'tasks': [{'ansible.builtin.import_tasks': str(ROLE / 'tasks/gitlab-fence.yml')}]}]))
            result = subprocess.run([os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook'),
                                     '-i', 'localhost,', str(playbook), '--syntax-check'],
                                    capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
