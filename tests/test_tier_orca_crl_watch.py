"""Public-only watchdog: real ephemeral signed CRLs, mocked notifications, no live services."""

from contextlib import redirect_stdout
import configparser
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml


UPSTREAM = Path(__file__).resolve().parents[1]
ROLE = UPSTREAM / 'tier-0/ansible/roles/orca_crl_watch'
HELPER = ROLE / 'files/orca_crl_watch.py'
LINUX = os.name != 'nt' and Path('/usr/bin/openssl').is_file()
ANSIBLE = shutil.which('ansible-playbook') if os.name != 'nt' else None


class WatchdogContract(unittest.TestCase):
    def test_entrypoint_is_independent_of_observability_and_has_no_mutating_pve_scope(self):
        playbook = yaml.safe_load((UPSTREAM / 'tier-0/ansible/playbooks/deployment/orca-crl-watch.yml').read_text())
        self.assertEqual(len(playbook), 3)
        self.assertEqual(playbook[0]['ansible.builtin.import_playbook'], '../control-node.yml')
        self.assertEqual(playbook[0]['vars']['control_node_setup'], 'orca-crl-watch')
        self.assertFalse(playbook[0]['vars']['control_node_require_terraform'])
        settings = yaml.safe_load((UPSTREAM / 'tier-0/ansible/playbooks/control-node.yml').read_text())[0]['vars']
        self.assertEqual(settings['control_node_setup_collection_names']['orca-crl-watch'], ['community.general'])
        self.assertEqual(playbook[1]['hosts'], 'localhost')
        self.assertIn("default('infrastructure_monitoring')", playbook[2]['hosts'])
        self.assertEqual(playbook[2]['roles'], ['orca_crl_watch'])
        self.assertTrue(playbook[2]['gather_facts'])
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        self.assertFalse(defaults['orca_crl_watch_outside_observed_clusters'])
        self.assertFalse(defaults['orca_crl_watch_bootstrap_fallback_accepted'])
        self.assertNotIn('orca_crl_watch_deadman_policy_accepted', defaults)
        self.assertEqual(defaults['orca_crl_watch_success_url'], '')
        self.assertEqual(defaults['orca_crl_watch_crl_proxy_url'], '')
        self.assertEqual(defaults['orca_crl_watch_deadman_proxy_url'], '{{ orca_crl_watch_proxy_url }}')
        for name, expected in [('warning_after_days', 45), ('ceremony_interval_days', 60),
                               ('expiry_safety_days', 7), ('max_crl_days', 90)]:
            self.assertEqual(defaults['orca_crl_watch_' + name], expected)
        for path in ROLE.rglob('*.yml'):
            yaml.safe_load(path.read_text())
        preflight = (ROLE / 'tasks/preflight.yml').read_text()
        self.assertIn('backup recipients', preflight)
        self.assertIn('missed-ping', preflight)
        self.assertIn("groups.get('root_ca'", preflight)
        self.assertIn("groups.get('hypervisors'", preflight)

    def test_native_units_retain_retries_without_healthy_process_heartbeat(self):
        service = (ROLE / 'templates/orca-crl-watch.service.j2').read_text()
        timer = (ROLE / 'templates/orca-crl-watch.timer.j2').read_text()
        for expected in ('DynamicUser=yes', 'LoadCredential=config.json:', 'StateDirectory=orca-crl-watch',
                         'Restart=on-failure', 'RestartSec=5min', 'StartLimitIntervalSec=0',
                         'TimeoutStartSec=120', 'ProtectSystem=strict', 'CapabilityBoundingSet='):
            self.assertIn(expected, service)
        self.assertIn('UnsetEnvironment=http_proxy https_proxy HTTP_PROXY HTTPS_PROXY', service)
        self.assertIn('no_proxy NO_PROXY', service)
        self.assertIn('OnCalendar=hourly', timer)
        self.assertIn('Persistent=true', timer)
        self.assertIn('OnClockChange=true', timer)
        self.assertNotIn('curl ', service)
        self.assertNotIn('ExecStartPost=', service)
        tasks = (ROLE / 'tasks/main.yml').read_text()
        self.assertIn('ansible.builtin.package:', tasks)
        self.assertIn('ansible.builtin.systemd_service:', tasks)
        self.assertNotIn('ansible.builtin.shell:', tasks)
        self.assertNotIn('ansible.builtin.uri:', tasks)

    def test_only_package_subsets_are_dynamic_and_precede_dependency_installation(self):
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        includes = [(i, task['ansible.builtin.include_role']) for i, task in enumerate(tasks)
                    if 'ansible.builtin.include_role' in task]
        self.assertEqual([item['tasks_from'] for _, item in includes], ['repository_proxy', 'package_consumer'])
        package_index = next(i for i, task in enumerate(tasks) if 'ansible.builtin.package' in task)
        for index, include in includes:
            self.assertLess(index, package_index)
            self.assertEqual(include['name'], 'baseline')
            self.assertFalse(include['public'])


@unittest.skipUnless(LINUX, 'Uses native Linux OpenSSL and signal deadlines')
class PublicCRLRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='orca-crl-tests-')
        cls.base = Path(cls.directory.name)
        spec = importlib.util.spec_from_file_location('orca_public_watch', HELPER)
        cls.watch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.watch)
        cls.now = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=2)
        for name in ('root', 'wrong'):
            cls.command('req', '-new', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-keyout', str(cls.base / f'{name}.key'), '-out', str(cls.base / f'{name}.pem'),
                        '-subj', '/CN=Ephemeral Watch Root', '-days', '7300',
                        '-addext', 'basicConstraints=critical,CA:TRUE',
                        '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
        der = cls.command('x509', '-in', str(cls.base / 'root.pem'), '-outform', 'DER')
        cls.fingerprint = hashlib.sha256(der).hexdigest().upper()

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    @staticmethod
    def command(*args):
        return subprocess.run(['/usr/bin/openssl', *args], capture_output=True, check=True,
                              timeout=15).stdout

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='observation-', dir=self.base)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.state = self.work / 'observation.json'
        self.config = {
            'crl_url': 'http://publication.invalid/root.crl',
            'root_certificate': str(self.base / 'root.pem'),
            'root_fingerprint': self.fingerprint,
            'success_url': 'https://deadman.invalid/unique-test-id',
        }
        self.calls = []
        self.stdout = io.StringIO()
        clock = mock.patch.object(self.watch, 'clock_synchronized')
        clock.start()
        self.addCleanup(clock.stop)

    def load(self):
        path = self.work / 'config.json'
        path.write_text(json.dumps(self.config))
        return self.watch.load_config(path)

    def crl(self, *, issued=None, expires=None, signer='root', number=1, der=False):
        issued = issued or self.now
        expires = expires or issued + timedelta(days=90)
        (self.work / 'index').write_text('')
        (self.work / 'number').write_text(f'{number:02X}\n')
        config = self.work / 'openssl.cnf'
        config.write_text(f'''[ca]
default_ca = test
[test]
database = {self.work}/index
crlnumber = {self.work}/number
private_key = {self.base}/{signer}.key
certificate = {self.base}/{signer}.pem
default_md = sha256
default_crl_days = 90
''')
        path = self.work / 'signed.pem'
        self.command('ca', '-gencrl', '-batch', '-config', str(config), '-out', str(path),
                     '-crl_lastupdate', issued.strftime('%Y%m%d%H%M%SZ'),
                     '-crl_nextupdate', expires.strftime('%Y%m%d%H%M%SZ'))
        return self.command('crl', '-in', str(path), '-outform', 'DER') if der else path.read_bytes()

    def run_check(self, payload=None, *, now=None, offline=False, reply=b'OK'):
        config = self.load()

        def transport(url, values, body=None):
            self.calls.append((url, body))
            if body is None:
                if offline:
                    raise self.watch.WatchError('Publication unreachable')
                return payload
            return reply

        with redirect_stdout(self.stdout):
            return self.watch.run_once(config, self.state, now or self.now, transport)

    def assert_failed_without_success(self, code=2):
        self.assertNotEqual(code, 0)
        pings = [(url, body) for url, body in self.calls if body is not None]
        self.assertTrue(pings)
        self.assertTrue(all(url.endswith('/fail') for url, _ in pings), pings)

    def test_current_signed_crl_sends_only_healthy_and_persists_identity(self):
        self.assertEqual(self.run_check(self.crl()), 0)
        self.assertEqual(self.calls[-1][0], self.config['success_url'])
        observation = json.loads(self.state.read_text())
        self.assertEqual(observation['number'], 1)
        self.assertEqual(observation['root_fingerprint'], self.fingerprint)
        self.assertEqual(observation['this_update'], self.now.timestamp())

    def test_der_and_pem_are_same_observed_crl(self):
        self.assertEqual(self.run_check(self.crl()), 0)
        self.assertEqual(self.run_check(self.crl(der=True)), 0)

    def test_advance_warning_suppresses_success_before_expiry_and_due_date(self):
        code = self.run_check(self.crl(), now=self.now + timedelta(days=45))
        self.assertEqual(code, 1)
        self.assertIn('WARNING', self.stdout.getvalue())
        self.assert_failed_without_success(code)

    def test_overdue_even_with_thirty_days_of_crl_validity_remaining(self):
        code = self.run_check(self.crl(), now=self.now + timedelta(days=60))
        self.assertIn('interval missed', self.stdout.getvalue())
        self.assert_failed_without_success(code)

    def test_expiry_safety_window_and_already_expired_crl_fail(self):
        for remaining in (7, -1):
            with self.subTest(remaining=remaining):
                self.calls.clear()
                self.state.unlink(missing_ok=True)
                # At age eight days, neither the ceremony warning nor due date has arrived.
                code = self.run_check(self.crl(expires=self.now + timedelta(days=8 + remaining)),
                                      now=self.now + timedelta(days=8))
                self.assertIn('expiry safety', self.stdout.getvalue())
                self.assert_failed_without_success(code)

    def test_wrong_signature_fails_on_openssl_versions_returning_zero(self):
        code = self.run_check(self.crl(signer='wrong'))
        self.assertIn('signature', self.stdout.getvalue())
        self.assert_failed_without_success(code)

    def test_wrong_fingerprint_fails_before_publication_fetch(self):
        self.config['root_fingerprint'] = '00' * 32
        self.assert_failed_without_success(self.run_check(self.crl()))
        self.assertEqual(len(self.calls), 1)
        self.assertIn('fingerprint mismatch', self.stdout.getvalue())

    def test_corrupt_or_unreachable_publication_never_sends_success(self):
        for payload, offline in ((b'not a CRL', False), (None, True)):
            with self.subTest(offline=offline):
                self.calls.clear()
                self.assert_failed_without_success(self.run_check(payload, offline=offline))

    def test_future_crl_and_unsynchronized_clock_fail(self):
        self.assert_failed_without_success(self.run_check(self.crl(issued=self.now + timedelta(hours=1))))
        self.calls.clear()
        with mock.patch.object(self.watch, 'clock_synchronized', side_effect=self.watch.WatchError('Wrong clock')):
            self.assert_failed_without_success(self.run_check(self.crl()))

    def test_clock_rollback_and_replayed_crl_fail(self):
        payload = self.crl(number=10)
        self.assertEqual(self.run_check(payload, now=self.now + timedelta(days=2)), 0)
        self.calls.clear()
        self.assert_failed_without_success(self.run_check(payload, now=self.now))
        self.calls.clear()
        self.assert_failed_without_success(self.run_check(self.crl(number=9), now=self.now + timedelta(days=3)))

    def test_state_corruption_and_write_failure_cannot_report_health(self):
        self.state.write_text('{invalid-json')
        self.assert_failed_without_success(self.run_check(self.crl()))
        self.state.unlink()
        self.calls.clear()
        self.state = self.work / 'missing-directory' / 'observation.json'
        self.assert_failed_without_success(self.run_check(self.crl()))

    def test_success_delivery_error_is_not_a_successful_process_exit(self):
        code = self.run_check(self.crl(), reply=b'OK (not found)')
        self.assertEqual(code, 2)
        self.assertIn('delivery failed', self.stdout.getvalue())

    def test_failure_delivery_error_retains_critical_status(self):
        code = self.run_check(None, offline=True, reply=b'OK (not found)')
        self.assertEqual(code, 2)
        self.assert_failed_without_success(code)

    def test_long_crl_validity_cannot_hide_the_ceremony_schedule(self):
        self.assert_failed_without_success(self.run_check(self.crl(expires=self.now + timedelta(days=365))))
        self.assertIn('maximum', self.stdout.getvalue())

    def test_explicit_separate_failure_route_and_colon_fingerprint(self):
        self.config['failure_url'] = 'https://deadman.invalid/separate-private-failure-route'
        self.config['root_fingerprint'] = ':'.join(self.fingerprint[i:i + 2] for i in range(0, 64, 2))
        self.assertEqual(self.run_check(self.crl(), now=self.now + timedelta(days=46)), 1)
        self.assertEqual(self.calls[-1][0], self.config['failure_url'])

    def test_missing_endpoint_and_unsafe_routes_are_actionable(self):
        for changes in ({'success_url': ''}, {'success_url': 'https://deadman.invalid/'},
                        {'success_url': 'https://deadman.invalid/id/fail'},
                        {'success_url': 'http://deadman.invalid/id'},
                        {'success_url': 'https://user:secret@deadman.invalid/id'},
                        {'success_url': 'https://deadman.invalid/id?key=value'},
                        {'failure_url': self.config['success_url']},
                        {'root_fingerprint': 'not-a-sha256'}, {'warning_after_days': 61}):
            with self.subTest(changes=changes):
                original = dict(self.config)
                self.config.update(changes)
                with self.assertRaises(self.watch.WatchError):
                    self.load()
                self.config = original

    def test_validation_only_uses_no_transport_and_has_no_secret_argv(self):
        self.load()
        result = subprocess.run([sys.executable, str(HELPER), '--config', str(self.work / 'config.json'),
                                 '--validate-only'], capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_copy_validation_refuses_private_material_and_certificate_bundles(self):
        for suffix in ((self.base / 'root.key').read_bytes(), (self.base / 'wrong.pem').read_bytes()):
            path = self.work / 'unacceptable.pem'
            path.write_bytes((self.base / 'root.pem').read_bytes() + suffix)
            result = subprocess.run([sys.executable, str(HELPER), '--validate-root', str(path)],
                                    capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b'one PUBLIC', result.stdout)

    @unittest.skipUnless(shutil.which('systemd-analyze'), 'Requires native systemd unit verifier')
    def test_native_systemd_verifier_accepts_timer_and_service(self):
        paths = []
        for name in ('orca-crl-watch.service', 'orca-crl-watch.timer'):
            path = self.work / name
            path.write_text((ROLE / f'templates/{name}.j2').read_text())
            paths.append(str(path))
        result = subprocess.run(['systemd-analyze', 'verify', '--man=no', *paths],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bounded_http_transport_rejects_redirect_and_oversized_response(self):
        config = self.load()
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = b'x' * (4 * 1024 * 1024 + 1)
        response.__enter__.return_value = response
        opener = mock.Mock()
        opener.open.return_value = response
        with mock.patch.object(self.watch.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaisesRegex(self.watch.WatchError, 'bounded'):
                self.watch.http_request(config['crl_url'], config)
            response.read.assert_called_once_with(4 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(self.watch.WatchError, 'redirect'):
            self.watch.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.invalid')

    def test_tls_context_verifies_certificates_and_proxy_is_explicit(self):
        response = mock.MagicMock()
        response.status = 200
        response.read.return_value = b'OK'
        response.__enter__.return_value = response
        opener = mock.Mock()
        opener.open.return_value = response
        with mock.patch.object(self.watch.urllib.request, 'build_opener', return_value=opener) as build:
            config = self.load()
            self.watch.http_request(config['success_url'], config, b'OK')
            proxy_handler, _, tls_handler = build.call_args.args
            self.assertEqual(proxy_handler.proxies, {})
            self.assertTrue(tls_handler._context.check_hostname)
            self.assertEqual(tls_handler._context.verify_mode, self.watch.ssl.CERT_REQUIRED)

    def test_legacy_proxy_is_alert_only_and_explicit_direct_overrides_it(self):
        self.config['proxy_url'] = 'http://legacy-egress.invalid:3128'
        config = self.load()
        self.assertEqual(config['crl_proxy_url'], '')
        self.assertEqual(config['deadman_proxy_url'], self.config['proxy_url'])
        self.config['deadman_proxy_url'] = ''
        self.config['crl_proxy_url'] = 'http://accepted-crl-proxy.invalid:3128'
        config = self.load()
        self.assertEqual(config['deadman_proxy_url'], '')
        self.assertEqual(config['crl_proxy_url'], self.config['crl_proxy_url'])

    def test_notification_urls_and_bodies_cannot_target_the_public_crl_path(self):
        original = dict(self.config)
        for field in ('success_url', 'failure_url'):
            with self.subTest(field=field):
                self.config = dict(original, allow_http_deadman=True,
                                   failure_url='https://deadman.invalid/independent-failure')
                self.config[field] = self.config['crl_url'] + '?private-check=secret-token'
                with self.assertRaisesRegex(self.watch.WatchError, 'publication path'):
                    self.load()
        self.config = original
        config = self.load()
        with mock.patch.object(self.watch.urllib.request, 'build_opener') as build:
            with self.assertRaisesRegex(self.watch.WatchError, 'credentials or status'):
                self.watch.http_request(config['crl_url'], config, b'private-alert-body')
            build.assert_not_called()

    def test_internal_crl_is_direct_and_only_alerts_use_the_outbound_proxy(self):
        self.config['deadman_proxy_url'] = 'http://accepted-egress.invalid:3128'
        payload = self.crl()
        config = self.load()
        for age_days, fail_alert, expected in ((0, False, 0), (46, False, 1), (0, True, 2)):
            with self.subTest(age_days=age_days, fail_alert=fail_alert):
                self.state.unlink(missing_ok=True)
                self.stdout = io.StringIO()
                requests = []

                def build_opener(*handlers):
                    proxies = handlers[0].proxies

                    def open_request(request, timeout):
                        requests.append((request, proxies))
                        if request.data is not None and fail_alert:
                            raise self.watch.urllib.error.URLError('Private deadman token must not reach logs')
                        response = mock.MagicMock()
                        response.status = 200
                        response.read.return_value = payload if request.data is None else b'OK'
                        response.__enter__.return_value = response
                        return response

                    return mock.Mock(open=open_request)

                with mock.patch.object(self.watch.urllib.request, 'build_opener', side_effect=build_opener):
                    with redirect_stdout(self.stdout):
                        code = self.watch.run_once(config, self.state, self.now + timedelta(days=age_days))
                self.assertEqual(code, expected, self.stdout.getvalue())
                self.assertEqual(len(requests), 2)
                public_request, public_proxies = requests[0]
                self.assertEqual(public_request.full_url, config['crl_url'])
                self.assertIsNone(public_request.data)
                self.assertNotIn('Authorization', public_request.headers)
                self.assertNotIn('unique-test-id', str(public_request.headers))
                self.assertEqual(public_proxies, {})
                alert_request, alert_proxies = requests[1]
                self.assertEqual(alert_request.full_url, config['failure_url'] if age_days else config['success_url'])
                self.assertEqual(alert_proxies, {'http': self.config['deadman_proxy_url'],
                                               'https': self.config['deadman_proxy_url']})
                if fail_alert:
                    self.assertIn('CRITICAL', self.stdout.getvalue())
                    self.assertNotIn('<6>OK', self.stdout.getvalue())
                    self.assertNotIn('Private deadman token', self.stdout.getvalue())


@unittest.skipUnless(ANSIBLE, 'Requires a local Ansible installation; never connects to a target')
class WatchdogAnsible(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='watchdog-ansible-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        (self.work / 'ansible.cfg').write_text('[defaults]\nretry_files_enabled=False\n')
        self.environment = {**os.environ, 'ANSIBLE_ROLES_PATH': os.pathsep.join([
                                str(ROLE.parent), str(UPSTREAM / 'shared/ansible/roles')]),
                            'ANSIBLE_LOCAL_TEMP': str(self.work / 'ansible-tmp'),
                            'ANSIBLE_CONFIG': str(self.work / 'ansible.cfg')}

    def test_production_entrypoint_syntax_without_running_the_role(self):
        result = subprocess.run([ANSIBLE, '--syntax-check', '-i', 'localhost,',
                                 str(UPSTREAM / 'tier-0/ansible/playbooks/deployment/orca-crl-watch.yml')],
                                capture_output=True, text=True, env=self.environment, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_preflight_rejects_missing_endpoint_before_any_mutation(self):
        play = [{'hosts': 'localhost', 'gather_facts': False, 'connection': 'local',
                 'vars': {'ansible_facts': {'os_family': 'RedHat', 'service_mgr': 'systemd'},
                          'orca_crl_watch_outside_observed_clusters': True,
                          'orca_crl_watch_crl_url': 'https://publication.invalid/root.crl',
                          'orca_crl_watch_root_certificate_src': 'root.pem',
                          'orca_crl_watch_root_fingerprint': '00' * 32},
                 'tasks': [{'ansible.builtin.include_role': {'name': 'orca_crl_watch', 'tasks_from': 'preflight'}}]}]
        path = self.work / 'preflight.yml'
        path.write_text(yaml.safe_dump(play))
        result = subprocess.run([ANSIBLE, '-i', 'localhost,', str(path)], capture_output=True, text=True,
                                env=self.environment, timeout=40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Create a unique Healthchecks-compatible check', result.stdout + result.stderr)
        self.assertIn('changed=0', result.stdout)

    def test_empty_production_inventory_fails_instead_of_silently_skipping(self):
        result = subprocess.run([ANSIBLE, '-i', 'localhost,',
                                 str(UPSTREAM / 'tier-0/ansible/playbooks/deployment/orca-crl-watch.yml')],
                                capture_output=True, text=True, env=self.environment, timeout=40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Add ONE existing independent Linux host', result.stdout + result.stderr)

    def test_shared_deadman_selection_fails_before_connecting_to_either_host(self):
        inventory = self.work / 'hosts.yml'
        inventory.write_text(yaml.safe_dump({'all': {'children': {'infrastructure_monitoring': {
            'hosts': {'first': {'ansible_connection': 'local'},
                      'second': {'ansible_connection': 'local'}}}}}}))
        result = subprocess.run([ANSIBLE, '-i', str(inventory),
                                 str(UPSTREAM / 'tier-0/ansible/playbooks/deployment/orca-crl-watch.yml')],
                                capture_output=True, text=True, env=self.environment, timeout=40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Add ONE existing independent Linux host', result.stdout + result.stderr)
        self.assertNotIn('Gathering Facts', result.stdout)

    def test_root_or_observed_cluster_inventory_overlap_is_rejected(self):
        for forbidden in ('root_ca', 'issuing_ca', 'hypervisors', 'talos', 'ceremony_builders'):
            with self.subTest(group=forbidden):
                inventory = self.work / 'hosts.yml'
                inventory.write_text(yaml.safe_dump({'all': {'children': {
                    'infrastructure_monitoring': {'hosts': {'localhost': {}}},
                    forbidden: {'hosts': {'localhost': {}}}}}}))
                play = [{'hosts': 'localhost', 'gather_facts': False, 'connection': 'local',
                         'vars': {'ansible_facts': {'os_family': 'Debian', 'service_mgr': 'systemd'},
                                  'orca_crl_watch_outside_observed_clusters': True},
                         'tasks': [{'ansible.builtin.include_role': {
                             'name': 'orca_crl_watch', 'tasks_from': 'preflight'}}]}]
                path = self.work / 'preflight.yml'
                path.write_text(yaml.safe_dump(play))
                result = subprocess.run([ANSIBLE, '-i', str(inventory), str(path)], capture_output=True,
                                        text=True, env=self.environment, timeout=40)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('outside ORCA', result.stdout + result.stderr)
                self.assertIn('changed=0', result.stdout)

    def test_native_package_route_is_configured_before_any_metadata_refresh(self):
        repositories = self.work / 'yum.repos.d'
        repositories.mkdir()
        repo = repositories / 'rocky.repo'
        repo.write_text('[baseos]\nname=Fixture\nenabled=1\ngpgcheck=1\n'
                        'mirrorlist=https://unapproved.invalid/list\n')
        dnf_conf = self.work / 'dnf.conf'
        dnf_conf.write_text('[main]\nproxy=http://old.invalid:3128\n')
        bin_directory = self.work / 'bin'
        bin_directory.mkdir()
        marker = self.work / 'refresh.json'
        dnf = bin_directory / 'dnf'
        # The real Shared tasks run against temporary configuration files. Only the external
        # DNF refresh executable is replaced, so no native package manager/network is contacted.
        dnf.write_text('#!/usr/bin/python3\nimport configparser,json\n'
                       'from pathlib import Path\n'
                       'parser=configparser.ConfigParser(interpolation=None)\n'
                       f'parser.read({str(dnf_conf)!r})\n'
                       "assert parser['main']['proxy']=='http://accepted.invalid:3128'\n"
                       "assert parser['main']['gpgcheck']=='True'\n"
                       "assert parser['main']['sslverify']=='True'\n"
                       f'parser.read({str(repo)!r})\n'
                       "assert parser['baseos']['baseurl']=='https://dl.rockylinux.org/pub/rocky/$releasever/BaseOS/$basearch/os/'\n"
                       "assert 'mirrorlist' not in parser['baseos']\n"
                       f'Path({str(marker)!r}).write_text(json.dumps(dict(refreshed=True)))\n')
        dnf.chmod(0o755)
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        selected = [task for task in tasks if 'ansible.builtin.include_role' in task]
        play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                 'vars': {
                     'ansible_python_interpreter': sys.executable, 'ansible_os_family': 'RedHat',
                     'ansible_distribution': 'Rocky', 'baseline_package_source_profile': 'official',
                     'repository_proxy_enabled': True, 'repository_proxy_url': 'http://accepted.invalid:3128',
                     'repository_proxy_manage_hosts_entry': False,
                     'repository_proxy_dnf_conf_path': str(dnf_conf),
                     'repository_proxy_dnf_repo_dir': str(repositories)},
                 'environment': {'PATH': str(bin_directory) + os.pathsep + os.environ['PATH']},
                 'tasks': selected}]
        path = self.work / 'package-route.yml'
        path.write_text(yaml.safe_dump(play))
        result = subprocess.run([ANSIBLE, '-i', 'localhost,', str(path)], capture_output=True,
                                text=True, env=self.environment, timeout=70)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(marker.read_text()), {'refreshed': True})
        configured = configparser.ConfigParser(interpolation=None)
        configured.read(dnf_conf)
        self.assertEqual(configured['main']['proxy'], 'http://accepted.invalid:3128')


if __name__ == '__main__':
    unittest.main()
