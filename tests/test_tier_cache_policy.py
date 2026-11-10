"""Native Squid policy/cache/privacy acceptance, never a host service installation.

Set HOMELAB_SQUID or SQUID_TEST_BINARY to an installed or unpacked Squid binary.
An unpacked Debian/Ubuntu package must include its usr/lib and usr/share payloads.
Only localhost high ports and private temporary state are used; origin traffic
is sent to the fixture parent, never to the documentation-only destination IPs.
"""

from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from urllib.parse import urlsplit

from jinja2 import Environment, StrictUndefined
import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


SQUID = os.environ.get('HOMELAB_SQUID') or os.environ.get('SQUID_TEST_BINARY')
ANSIBLE = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')
MAX_AGE = 4


@contextmanager
def squid_fixture(role):
    """Run the actual rendered policy with a recording, HTTP-only parent proxy."""
    import pwd

    calls = []
    lock = threading.Lock()

    class Origin(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def do_CONNECT(self):
            with lock:
                calls.append((self.path, dict(self.headers.items())))
            self.send_error(501, 'The fixture does not open tunnels')

        def do_GET(self):
            path = urlsplit(self.path).path
            with lock:
                calls.append((path, {key.lower(): value for key, value in self.headers.items()}))
                count = sum(entry[0] == path for entry in calls)
            policies = {
                '/private.rpm': 'private, max-age=600',
                '/no-store.rpm': 'no-store, max-age=600',
                '/no-cache.rpm': 'no-cache, max-age=600',
                '/authenticated.rpm': 'private, no-store',
                '/repodata/repomd.xml': 'public, max-age=0, must-revalidate',
            }
            metadata = path == '/repodata/repomd.xml'
            unchanged = metadata and self.headers.get('If-None-Match') == '"metadata-v1"'
            body = (path + ':' + str(1 if metadata else count)).encode()
            self.send_response(304 if unchanged else 200)
            self.send_header('Cache-Control', policies.get(path, 'public, max-age=' + str(MAX_AGE)))
            if metadata:
                self.send_header('ETag', '"metadata-v1"')
            if not unchanged:
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            if not unchanged:
                self.wfile.write(body)

    with tempfile.TemporaryDirectory(prefix='homelab-squid-policy-') as temporary:
        work = Path(temporary)
        parent = ThreadingHTTPServer(('127.0.0.1', 0), Origin)
        thread = threading.Thread(target=parent.serve_forever, daemon=True)
        thread.start()
        try:
            binary = Path(SQUID).resolve()
            package = binary.parents[2]
            common = package / 'usr/share/squid'
            errors = common / 'errors'
            for language in ('templates', 'en'):
                if (errors / language / 'ERR_ACCESS_DENIED').is_file():
                    errors /= language
                    break
            if not errors.is_dir():
                # Some unpacked squid-common payloads have a dangling squid-langpack link.
                # Error-page bodies are not under test; status/admission still come from Squid.
                errors = work / 'errors'
                errors.mkdir()
                (errors / 'ERR_ACCESS_DENIED').write_text('<html><body>Fixture denial</body></html>')
            environment = dict(os.environ)
            libraries = str(package / 'usr/lib/x86_64-linux-gnu')
            environment['LD_LIBRARY_PATH'] = libraries + os.pathsep + environment.get('LD_LIBRARY_PATH', '')
            with socket.socket() as reservation:
                reservation.bind(('127.0.0.1', 0))
                port = reservation.getsockname()[1]
            hosts = work / 'hosts'
            hosts.write_text('192.0.2.99 repo.example.test\n192.0.2.98 unknown.example.test\n'
                             '192.0.2.97 example.test\n192.0.2.96 updates.example.test\n'
                             '192.0.2.95 mirror.updates.example.test\n'
                             '127.0.0.1 loop.example.test\n169.254.169.254 link.example.test\n')
            cache = work / 'cache'
            cache.mkdir()
            inputs = yaml.safe_load((role / 'defaults/main.yml').read_text())
            inputs.update(
                platform_fqdn='cache.fixture.test',
                cache_squid_http_port='127.0.0.1:' + str(port),
                cache_squid_cache_mem='8 MB', cache_squid_cache_mb=16,
                cache_squid_cache_dir=str(cache), cache_squid_l1_dirs=2, cache_squid_l2_dirs=2,
                cache_squid_allowed_cidrs=['127.0.0.2/32'],
                cache_squid_allowed_domains=['example.test', 'repo.example.test',
                                             '.updates.example.test', 'updates.example.test',
                                             'mirror.updates.example.test', 'loop.example.test', 'link.example.test'],
                cache_squid_upstream_proxy='127.0.0.1', cache_squid_upstream_port=parent.server_port,
                cache_squid_extra_options=[
                    'pid_filename ' + str(work / 'squid.pid'),
                    'cache_effective_user ' + pwd.getpwuid(os.getuid()).pw_name,
                    'logfile_daemon ' + str(package / 'usr/lib/squid/log_file_daemon'),
                    'unlinkd_program ' + str(package / 'usr/lib/squid/unlinkd'),
                    'mime_table ' + str(common / 'mime.conf'),
                    'icon_directory ' + str(common / 'icons'),
                    'error_directory ' + str(errors),
                    'hosts_file ' + str(hosts),
                    'dns_nameservers 127.0.0.1',
                    'pinger_enable off', 'netdb_filename none',
                    'buffered_logs off', 'shutdown_lifetime 0 seconds',
                ],
            )
            rendered = Environment(undefined=StrictUndefined).from_string(
                (role / 'templates/squid.conf.j2').read_text()).render(inputs)
            # Only fixed runtime log paths are relocated; ACLs/log format/freshness stay production-owned.
            config = work / 'squid.conf'
            config.write_text(rendered.replace('/var/log/squid/', str(work) + '/'))
            for flags in (['-k', 'parse'], ['-N', '-z']):
                result = subprocess.run([str(binary), '-f', str(config), *flags], env=environment,
                                        cwd=work, capture_output=True, text=True, timeout=15)
                if result.returncode:
                    raise AssertionError(result.stdout + result.stderr)
            with (work / 'process.log').open('w+') as output:
                process = subprocess.Popen([str(binary), '-N', '-d', '1', '-f', str(config)],
                                           env=environment, cwd=work, stdout=output, stderr=subprocess.STDOUT)
                try:
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline and process.poll() is None:
                        try:
                            with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                                break
                        except OSError:
                            time.sleep(0.05)
                    else:
                        output.seek(0)
                        raise AssertionError('Squid did not start:\n' + output.read())
                    yield port, calls, work / 'access.log'
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
        finally:
            parent.shutdown()
            parent.server_close()
            thread.join(timeout=5)


def request(port, target, method='GET', headers=None, source='127.0.0.1'):
    connection = HTTPConnection('127.0.0.1', port, timeout=5, source_address=(source, 0))
    try:
        connection.request(method, target, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


class PrivateCollection(TierRepositoryTestCase):
    def setUp(self):
        # Keep generated payload/cache I/O on native temporary storage, also for WSL checkouts.
        self.temp = tempfile.TemporaryDirectory(prefix='homelab-cache-policy-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name) / 'workspace with spaces'
        self.root = self.parent / 'verify-iac'


@unittest.skipUnless(os.name != 'nt' and SQUID and Path(SQUID).is_file(),
                     'Set HOMELAB_SQUID or SQUID_TEST_BINARY to a native Squid binary')
class NativeCachePolicy(PrivateCollection):
    def test_source_policy(self):
        self.exercise_policy(UPSTREAM / 'tier-2/ansible/roles/cache_proxy')

    def test_generated_policy(self):
        self.generate()
        self.exercise_policy(self.root / 'verify-tier-2/ansible/roles/cache_proxy')

    def exercise_policy(self, role):
        with squid_fixture(role) as (port, calls, access_log):
            denied = [
                # Intentionally absent from hosts: admission must reject before DNS/destination lookup.
                ('GET', 'http://software-intake-denied.invalid/'),
                ('CONNECT', 'software-intake-denied.invalid:443'),
                ('GET', 'http://unknown.example.test/unknown.rpm'),
                ('CONNECT', 'unknown.example.test:443'),
                ('GET', 'http://repo.example.test:81/forbidden-port.rpm'),
                ('CONNECT', 'repo.example.test:80'),
                ('GET', 'http://192.0.2.99/ip-literal.rpm'),
                ('GET', 'http://loop.example.test/local.rpm'),
                ('GET', 'http://link.example.test/metadata'),
            ]
            for method, target in denied:
                with self.subTest(method=method, target=target):
                    self.assertEqual(request(port, target, method)[0], 403)
                    self.assertEqual(calls, [], 'Denied traffic reached the fixture parent')

            with self.subTest(client='outside-allowed-cidr'):
                self.assertEqual(request(port, 'http://repo.example.test/forbidden-client.rpm',
                                         source='127.0.0.3')[0], 403)
                self.assertEqual(calls, [], 'An unapproved client reached the fixture parent')

            for host in ('example.test', 'updates.example.test', 'mirror.updates.example.test'):
                with self.subTest(allowed_domain=host):
                    self.assertEqual(request(port, 'http://' + host + '/domain-check')[0], 200)

            target = 'http://repo.example.test/package.rpm'
            first = request(port, target, source='127.0.0.2')
            self.assertEqual(first[0], 200)
            self.assertEqual(request(port, target), first)
            self.assertEqual(sum(path == '/package.rpm' for path, _ in calls), 1,
                             'A fresh public response did not produce a cache hit')
            time.sleep(MAX_AGE + 0.2)
            expired = request(port, target)
            self.assertEqual(expired[0], 200)
            self.assertNotEqual(expired[1], first[1])
            self.assertEqual(sum(path == '/package.rpm' for path, _ in calls), 2,
                             'Origin max-age expiry was overridden')

            for path in ('/private.rpm', '/no-store.rpm', '/no-cache.rpm'):
                with self.subTest(cache_control=path):
                    for _ in range(2):
                        self.assertEqual(request(port, 'http://repo.example.test' + path)[0], 200)
                    self.assertEqual(sum(entry[0] == path for entry in calls), 2,
                                     'A privacy/revalidation directive was overridden')

            metadata = 'http://repo.example.test/repodata/repomd.xml'
            original = request(port, metadata)
            self.assertEqual(original[0], 200)
            self.assertEqual(request(port, metadata), original)
            validations = [headers for path, headers in calls if path == '/repodata/repomd.xml']
            self.assertEqual(len(validations), 2)
            self.assertEqual(validations[1].get('if-none-match'), '"metadata-v1"',
                             'Repository metadata was not conditionally revalidated')

            query_marker, auth_marker = 'fixture-query-marker', 'fixture-auth-marker'
            headers = {'Authorization': 'Bearer ' + auth_marker,
                       'Proxy-Authorization': 'Basic ' + auth_marker}
            for _ in range(2):
                result = request(port, 'http://repo.example.test/authenticated.rpm?token=' + query_marker,
                                 headers=headers)
                self.assertEqual(result[0], 200)
            self.assertEqual(sum(path == '/authenticated.rpm' for path, _ in calls), 2)

            expected = len(denied) + 1 + 3 + 3 + 6 + 2 + 2
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                lines = access_log.read_text().splitlines() if access_log.exists() else []
                if len(lines) >= expected:
                    break
                time.sleep(0.05)
            self.assertGreaterEqual(len(lines), expected, 'Access log was not flushed')
            records = [json.loads(line) for line in lines]
            raw = '\n'.join(lines)
            for marker in (query_marker, auth_marker, '/authenticated.rpm', '?token=', 'Bearer ', 'Basic '):
                self.assertNotIn(marker, raw)
            fields = {'event.type', 'timestamp', 'client.ip', 'destination.domain', 'http.request.method',
                      'http.response.status_code', 'proxy.result', 'error.code'}
            for record in records:
                self.assertEqual(set(record), fields)
                self.assertEqual(record['event.type'], 'software_intake.proxy')
                self.assertIsInstance(record['http.response.status_code'], int)
            self.assertTrue(any('HIT' in record['proxy.result'] for record in records))
            self.assertTrue(any(record['destination.domain'] == 'unknown.example.test'
                                and record['http.request.method'] == 'CONNECT'
                                and record['http.response.status_code'] == 403 for record in records))


@unittest.skipUnless(os.name != 'nt' and ANSIBLE, 'Requires native Ansible with ansible.utils/netaddr')
class NativeCachePreflight(PrivateCollection):
    def test_unsafe_inputs_stop_before_render_in_source_and_generated_payload(self):
        self.generate()
        work = Path(self.temp.name)
        inventory = work / 'hosts.ini'
        inventory.write_text('[cache]\nlocalhost ansible_connection=local\n')
        cases = [
            ('vip-without-prefix', {'cache_keepalived_vip_cidr': '192.0.2.50'},
             'A missing or /0 prefix is not accepted'),
            ('vip-zero-prefix', {'cache_keepalived_vip_cidr': '192.0.2.50/0'},
             'A missing or /0 prefix is not accepted'),
            ('vip-placeholder-marker', {'cache_keepalived_vip_cidr': '192.0.2.50/<27'},
             'A missing or /0 prefix is not accepted'),
            ('vip-invalid-prefix', {'cache_keepalived_vip_cidr': '192.0.2.50/33'},
             'A missing or /0 prefix is not accepted'),
            ('dot-domain', {'cache_squid_allowed_domains': ['.']}, 'Use a source hostname or .domain suffix'),
            ('url-domain', {'cache_squid_allowed_domains': ['https://repo.example.test']},
             'Use a source hostname or .domain suffix'),
            ('unrestricted-cidr', {'cache_squid_allowed_cidrs': ['0.0.0.0/0']},
             'Select explicit permitted client CIDRs'),
            ('private-override', {'cache_squid_refresh_patterns': ['. 0 20% 4320 ignore-private']},
             'Remove forced-cache refresh options'),
        ]
        for label, tier in (('source', UPSTREAM / 'tier-2'), ('generated', self.root / 'verify-tier-2')):
            role = tier / 'ansible/roles/cache_proxy'
            defaults = yaml.safe_load((role / 'defaults/main.yml').read_text())
            # Execute every native assertion, without the package-installation task.
            assertions = [task for task in yaml.safe_load((role / 'tasks/preflight.yml').read_text())
                          if 'ansible.builtin.assert' in task]
            for name, invalid, message in cases:
                with self.subTest(owner=label, invalid=name):
                    output = work / (label + '-' + name + '.conf')
                    inputs = dict(defaults, ansible_os_family='Debian',
                                  cache_keepalived_vip_cidr='192.0.2.50/24',
                                  platform_host_ips={'localhost': '192.0.2.1'},
                                  cache_squid_allowed_cidrs=['192.0.2.0/24'],
                                  cache_squid_allowed_domains=['repo.example.test'])
                    inputs.update(invalid)
                    tasks = assertions + [{'name': 'Render only after valid source policy',
                                           'ansible.builtin.template': {
                                               'src': str(role / 'templates/squid.conf.j2'),
                                               'dest': str(output), 'mode': '0600'}}]
                    play = work / 'preflight.yml'
                    play.write_text(yaml.safe_dump([{
                        'hosts': 'cache', 'gather_facts': False, 'vars': inputs, 'tasks': tasks,
                    }]))
                    environment = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(work / 'ansible-local'))
                    result = subprocess.run([ANSIBLE, '-i', str(inventory), str(play)], env=environment,
                                            capture_output=True, text=True, timeout=60)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(message, result.stdout, result.stdout + result.stderr)
                    self.assertNotIn('TASK [Render only after valid source policy]', result.stdout)
                    self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
