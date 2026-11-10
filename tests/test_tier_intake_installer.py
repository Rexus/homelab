"""Native installer rendering and optional isolated HTTPS publication acceptance."""

import configparser
from http.client import HTTPSConnection
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ANSIBLE = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')
NGINX = os.environ.get('HOMELAB_NGINX') or shutil.which('nginx')
LOGROTATE = (os.environ.get('HOMELAB_LOGROTATE') or os.environ.get('LOGROTATE_TEST_BINARY')
             or shutil.which('logrotate'))


@unittest.skipUnless(os.name != 'nt' and ANSIBLE, 'Requires native Ansible with declared collections')
class IntakeInstaller(TierRepositoryTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='homelab-intake-installer-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name) / 'workspace with spaces'
        self.root = self.parent / 'verify-iac'

    def inputs(self, role):
        values = yaml.safe_load((role / 'defaults/main.yml').read_text())
        values.update(ansible_os_family='Debian', ansible_distribution_major_version='13',
                      ansible_service_mgr='systemd', software_intake_server_name='intake.example.test',
                      software_intake_allowed_cidrs=['127.0.0.1/32'],
                      software_intake_environment={'http_proxy': 'http://cache.example.test:3128'},
                      software_intake_sources=[{
                          'name': 'tool', 'kind': 'artifact', 'url': 'https://source.example.test/tool.rpm',
                          'sha256': 'a' * 64, 'filename': 'tool+el10.rpm',
                          'signature_url': 'https://source.example.test/tool.rpm.asc',
                          'key_file': '/controller/private/approved.asc', 'key_fingerprint': 'B' * 40,
                      }])
        return values

    def run_tasks(self, tasks, values, work):
        play, inputs = work / 'play.yml', work / 'inputs.yml'
        inputs.write_text(yaml.safe_dump(values))
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                                        'gather_facts': False, 'tasks': tasks}], sort_keys=False))
        return subprocess.run([ANSIBLE, '-i', 'localhost,', str(play), '-e', '@' + str(inputs)],
                              capture_output=True, text=True, timeout=120)

    def rendered(self):
        self.generate()
        for label, tier in [('source', UPSTREAM / 'tier-1'), ('generated', self.root / 'verify-tier-1')]:
            role = tier / 'ansible/roles/software_intake'
            output = Path(self.temp.name) / label
            output.mkdir()
            services = yaml.safe_load((role / 'tasks/services.yml').read_text())
            derivation = [task for task in services[:2]]
            tasks = derivation + derivation + [{
                'ansible.builtin.template': {'src': str(role / 'templates' / (name + '.j2')),
                                            'dest': str(output / name), 'mode': '0600'},
            } for name in ['policy.yml', 'nginx.conf', 'nginx.logrotate', 'intake.service', 'intake.timer',
                           'ansible.cfg', 'freshclam.conf']]
            result = self.run_tasks(tasks, self.inputs(role), output)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            yield role, output

    def test_source_and_generated_policy_runtime_and_service_contracts(self):
        for role, output in self.rendered():
            with self.subTest(role=role):
                play = output / 'role-syntax.yml'
                play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'gather_facts': False, 'roles': [str(role)]}]))
                syntax = subprocess.run([ANSIBLE, '-i', 'localhost,', '--syntax-check', str(play)],
                                        capture_output=True, text=True, timeout=60)
                self.assertEqual(syntax.returncode, 0, syntax.stdout + syntax.stderr)
                policy = yaml.safe_load((output / 'policy.yml').read_text())
                self.assertEqual(len(policy['intake_sources']), 1, 'Derived sources duplicated on a second role run')
                source = policy['intake_sources'][0]
                self.assertEqual(source['key_file'], '/etc/software-intake/keys/tool.asc')
                self.assertEqual(source['keyring_file'], '/etc/software-intake/keys/tool.gpg')
                self.assertNotIn('/controller/', (output / 'policy.yml').read_text())
                for key in ['intake_max_file_mb', 'intake_max_scan_mb', 'intake_min_free_bytes',
                            'intake_config_dir', 'intake_data_dir', 'intake_environment', 'intake_fetch_user',
                            'intake_scan_user', 'intake_clam_database_dir', 'intake_max_definition_age_days',
                            'intake_quarantine_days']:
                    self.assertIn(key, policy)
                config = configparser.ConfigParser()
                config.read(output / 'ansible.cfg')
                self.assertTrue(config['defaults']['local_tmp'].startswith('/srv/intake/'))
                self.assertTrue(config['defaults']['remote_tmp'].startswith('/srv/intake/'))
                self.assertIn('-k', config['privilege_escalation']['become_flags'])
                self.assertEqual(config['defaults']['collections_scan_sys_path'], 'false')
                service = (output / 'intake.service').read_text()
                self.assertIn('-e @/etc/software-intake/policy.yml', service)
                for setting in ['ProtectHome=yes', 'ProtectSystem=strict', 'NoNewPrivileges=yes',
                                'KillMode=control-group', 'ReadWritePaths=/srv/intake',
                                'AssertPathIsMountPoint=/srv/intake']:
                    self.assertIn(setting, service)
                self.assertNotIn('MemoryDenyWriteExecute', service, 'ClamAV bytecode must remain supported')
                if shutil.which('systemd-analyze'):
                    units = output / 'unit-parse'
                    units.mkdir()
                    (units / 'intake.service').write_text(service.replace('/usr/bin/ansible-playbook', sys.executable))
                    shutil.copyfile(output / 'intake.timer', units / 'intake.timer')
                    checked = subprocess.run(['systemd-analyze', 'verify', '--man=no',
                                              str(units / 'intake.service'), str(units / 'intake.timer')],
                                             capture_output=True, text=True, timeout=30)
                    self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
                self.assertIn('HTTPProxyServer cache.example.test', (output / 'freshclam.conf').read_text())
                defaults = yaml.safe_load((role / 'defaults/main.yml').read_text())
                self.assertFalse(defaults['software_intake_timer_enabled'])
                self.assertFalse(defaults['software_intake_freshclam_enabled'])
                for family in ['RedHat', 'Debian']:
                    for package in ['curl', 'file', 'sudo', 'acl', 'python3-debian', 'logrotate']:
                        self.assertIn(package, defaults['software_intake_packages'][family])

    @unittest.skipUnless(LOGROTATE and Path(LOGROTATE).is_file(), 'Requires native logrotate')
    def test_source_and_generated_log_rotation_validates_without_modifying_logs(self):
        for role, output in self.rendered():
            with self.subTest(role=role):
                config = (output / 'nginx.logrotate').read_text()
                for directive in ['daily', 'rotate 14', 'maxsize 20M', 'compress', 'missingok', 'notifempty',
                                  'sharedscripts', 'create 0640 root root']:
                    self.assertIn(directive, [line.strip() for line in config.splitlines()])
                self.assertIn('/usr/sbin/nginx -s reopen', config)
                self.assertNotIn('copytruncate', config)
                tasks = yaml.safe_load((role / 'tasks/services.yml').read_text())
                install = next(task['ansible.builtin.template'] for task in tasks
                               if task.get('ansible.builtin.template', {}).get('src') == 'nginx.logrotate.j2')
                self.assertEqual(install['dest'], '/etc/logrotate.d/software-intake-nginx')
                self.assertEqual(install['validate'], '/usr/sbin/logrotate --debug %s')
                schedule = next(task['ansible.builtin.systemd_service'] for task in tasks
                                if task.get('ansible.builtin.systemd_service', {}).get('name') == 'logrotate.timer')
                self.assertTrue(schedule['enabled'])
                self.assertEqual(schedule['state'], 'started')
                for packages in yaml.safe_load((role / 'defaults/main.yml').read_text())[
                        'software_intake_packages'].values():
                    self.assertIn('logrotate', packages)
                logs = output / 'rotation-logs'
                logs.mkdir(mode=0o700)
                logfile = logs / 'access.log'
                with logfile.open('wb') as stream:
                    stream.write(b'private test log\n')
                    stream.truncate(20 * 1024 * 1024 + 1)
                before = logfile.stat()
                private = config.replace('/var/log/software-intake-nginx', str(logs))
                private = private.replace('/run/software-intake-nginx/nginx.pid', str(output / 'absent-nginx.pid'))
                fixture, state = output / 'rotation.conf', output / 'rotation.state'
                fixture.write_text(private)
                checked = subprocess.run([LOGROTATE, '--debug', '--state', str(state), str(fixture)],
                                         capture_output=True, text=True, timeout=30)
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
                self.assertIn('log needs rotating', checked.stdout + checked.stderr)
                self.assertEqual(logfile.stat().st_size, before.st_size)
                self.assertEqual(logfile.stat().st_mtime_ns, before.st_mtime_ns)
                self.assertEqual(list(logs.iterdir()), [logfile])
                self.assertFalse(state.exists(), 'Debug validation must not write state')

    def test_invalid_sources_and_networks_stop_before_host_changes(self):
        role = UPSTREAM / 'tier-1/ansible/roles/software_intake'
        preflight = yaml.safe_load((role / 'tasks/preflight.yml').read_text())
        stop = next(i for i, task in enumerate(preflight) if 'ansible.builtin.command' in task)
        guards = preflight[:stop]
        values = self.inputs(role)
        for field, invalid in [('url', 'https://source.example.test/tool?token=private'),
                               ('url', 'https://source.example.test/tool#fragment'),
                               ('signature_url', 'https://source.example.test/signature?token=private'),
                               ('signature_url', 'https://source.example.test/signature#fragment'),
                               ('name', 'a'), ('sha256', '')]:
            with self.subTest(field=field, invalid=invalid):
                bad = dict(values, software_intake_sources=[dict(values['software_intake_sources'][0], **{field: invalid})])
                result = self.run_tasks(guards, bad, Path(self.temp.name))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('"evaluated_to": false', result.stdout, result.stdout + result.stderr)
                self.assertNotIn('Check the actual prepared mount', result.stdout)
        for network in ['0.0.0.0/0', 'not-a-cidr']:
            with self.subTest(network=network):
                result = self.run_tasks(guards, dict(values, software_intake_allowed_cidrs=[network]),
                                        Path(self.temp.name))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('explicit consumer CIDRs', result.stdout, result.stdout + result.stderr)
                self.assertNotIn('Check the actual prepared mount', result.stdout)

    def test_native_mount_and_public_key_qualification_gates(self):
        role = UPSTREAM / 'tier-1/ansible/roles/software_intake'
        preflight = yaml.safe_load((role / 'tasks/preflight.yml').read_text())
        mount = next(task for task in preflight if task['name'] == 'Reject missing, read-only or exhausted intake storage')
        flags = ['rw', 'nodev', 'nosuid', 'noexec']
        for missing in [None, *flags]:
            with self.subTest(missing_flag=missing):
                values = self.inputs(role)
                values['software_intake_mount'] = {'stdout': json.dumps({'filesystems': [{
                    'target': '/srv/intake', 'options': ','.join(flag for flag in flags if flag != missing),
                }]})}
                result = self.run_tasks([mount], values, Path(self.temp.name))
                self.assertEqual(result.returncode == 0, missing is None, result.stdout + result.stderr)
        keys = yaml.safe_load((role / 'tasks/keys.yml').read_text())
        block = next(task['block'] for task in keys if 'block' in task)
        gate = next(task for task in block if task['name'].startswith('Require exactly the pinned public primary key'))
        for validity in ['-', 'r', 'e', 'd', 'i']:
            with self.subTest(primary_key_status=validity):
                values = self.inputs(role)
                values['software_intake_key_inspection'] = {'results': [{
                    'item': {'key_fingerprint': 'B' * 40},
                    'stdout_lines': ['pub:' + validity + ':', ':'.join(['fpr'] + [''] * 8 + ['B' * 40, ''])],
                }]}
                result = self.run_tasks([gate], values, Path(self.temp.name))
                self.assertEqual(result.returncode == 0, validity == '-', result.stdout + result.stderr)

    @unittest.skipUnless(NGINX and Path(NGINX).is_file() and shutil.which('openssl'), 'Requires native nginx/OpenSSL')
    def test_source_and_generated_https_paths_match_real_publication_layout(self):
        for role, output in self.rendered():
            with self.subTest(role=role):
                self.check_publication(output)

    def check_publication(self, work):
        data, config = work / 'data', work / 'config'
        public = data / 'public/tool'
        version = 'a' * 64
        content = public / version / 'content'
        content.mkdir(parents=True)
        (content / 'tool.rpm').write_bytes(b'qualified artifact')
        (public / version / 'receipt.json').write_text('{"verdict":"approved"}')
        (public / 'latest.json').write_text(json.dumps({'content_path': '/approved/tool/' + version + '/content/'}))
        staging = data / 'staging'
        staging.mkdir()
        (staging / 'private.key').write_text('private candidate')
        (content / 'symlink.rpm').symlink_to(staging / 'private.key')
        tls = config / 'tls'
        tls.mkdir(parents=True)
        result = subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                                 '-subj', '/CN=intake.example.test', '-addext',
                                 'subjectAltName=DNS:intake.example.test,IP:127.0.0.1',
                                 '-keyout', str(tls / 'server.key'), '-out', str(tls / 'server.crt')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ['run', 'logs', 'cache']:
            (work / name).mkdir()
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        text = (work / 'nginx.conf').read_text()
        for old, new in [('/srv/intake', data), ('/etc/software-intake', config),
                         ('/run/software-intake-nginx', work / 'run'),
                         ('/var/log/software-intake-nginx', work / 'logs'),
                         ('/var/cache/software-intake-nginx', work / 'cache')]:
            text = text.replace(old, str(new))
        # Only the fixture process identity/listener/storage change, not location/access policy.
        text = text.replace('user intake-pub;', '')
        text = text.replace('listen 443 ssl;', 'listen 127.0.0.1:' + str(port) + ' ssl;')
        fixture = work / 'nginx-fixture.conf'
        fixture.write_text(text)
        result = subprocess.run([NGINX, '-t', '-p', str(work), '-c', str(fixture)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        process = subprocess.Popen([NGINX, '-p', str(work), '-c', str(fixture), '-g', 'daemon off;'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                        break
                except OSError:
                    time.sleep(0.05)
            else:
                self.fail('nginx did not start')
            context = ssl.create_default_context(cafile=str(tls / 'server.crt'))

            def get(path, method='GET', source='127.0.0.1'):
                connection = HTTPSConnection('127.0.0.1', port, context=context,
                                             source_address=(source, 0), timeout=5)
                try:
                    connection.request(method, path)
                    reply = connection.getresponse()
                    return reply.status, reply.read(), dict(reply.getheaders())
                finally:
                    connection.close()

            approved = '/approved/tool/' + version + '/'
            self.assertEqual(get(approved + 'content/tool.rpm')[:2], (200, b'qualified artifact'))
            self.assertEqual(get(approved + 'content/tool.rpm', 'HEAD')[:2], (200, b''))
            self.assertEqual(get(approved + 'receipt.json')[0], 200)
            discovery = get('/approved/tool/latest.json')
            self.assertEqual(discovery[0], 200)
            self.assertEqual(discovery[2]['Cache-Control'], 'no-store')
            for path in ['/staging/private.key', '/tool/latest.json', '/approved/tool/current.json',
                         '/approved/tool/versions/' + version + '/content/tool.rpm',
                         approved + 'content/symlink.rpm']:
                self.assertIn(get(path)[0], [403, 404])
            for method in ['POST', 'PUT', 'DELETE']:
                self.assertIn(get(approved + 'content/tool.rpm', method)[0], [403, 405])
            self.assertEqual(get(approved + 'content/tool.rpm', source='127.0.0.2')[0], 403)
            self.assertEqual((content / 'tool.rpm').read_bytes(), b'qualified artifact')
        finally:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
