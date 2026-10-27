"""Local Linux projection/NetBox contracts; native fixtures always live outside DrvFS.

Set OTELCOL_BINARY to the pinned Collector and install the repository's Ansible
collections. DATA_PREPPER_HOME enables the real product at the final hop; otherwise
an OTLP receiver fixture checks the protocol. Use a complete distribution on Linux
storage. No host service, container, external API or managed infrastructure is used.
"""

from copy import deepcopy
from collections import defaultdict
import configparser
from datetime import datetime, timezone
import http.server
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import yaml

from tier_repo_test_support import UPSTREAM


ARCHIVE = UPSTREAM / 'tier-0/ansible/roles/logging_archive'
EXPORT = UPSTREAM / 'tier-0/ansible/roles/logging_export'
AUDIT = UPSTREAM / 'tier-0/ansible/roles/netbox_audit'
OBSERVABILITY = UPSTREAM / 'tier-1/ansible/roles/observability_platform'
NATIVE = os.name != 'nt'
COLLECTOR = os.getenv('OTELCOL_BINARY')
PREPPER = os.getenv('DATA_PREPPER_HOME')


def command(arguments, **kwargs):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=45, **kwargs)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result


def ansible_render(directory, templates, variables):
    tasks = [{'ansible.builtin.template': dict(src=str(source), dest=str(destination), mode='0600')}
             for source, destination in templates]
    play = directory / 'render.yml'
    play.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                                      vars=variables, tasks=tasks)], sort_keys=False))
    command(['ansible-playbook', '-i', 'localhost,', str(play)])


def certificate_set(directory):
    """Independent CAs and localhost-only leaves expose literal-IP name mistakes."""
    directory.mkdir()
    for authority in ['ca', 'foreign']:
        command(['openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256',
                 '-nodes', '-days', '2', '-subj', f'/CN={authority}',
                 '-keyout', str(directory / f'{authority}.key'), '-out', str(directory / f'{authority}.pem')])
    for name, authority in [('server', 'ca'), ('client', 'ca'), ('rogue', 'foreign')]:
        command(['openssl', 'req', '-new', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256',
                 '-nodes', '-subj', f'/CN={name}', '-keyout', str(directory / f'{name}.key'),
                 '-out', str(directory / f'{name}.csr')])
        extensions = directory / f'{name}.ext'
        extensions.write_text('subjectAltName=DNS:localhost\nextendedKeyUsage=serverAuth,clientAuth\n')
        command(['openssl', 'x509', '-req', '-in', str(directory / f'{name}.csr'), '-CA',
                 str(directory / f'{authority}.pem'), '-CAkey', str(directory / f'{authority}.key'),
                 '-CAcreateserial', '-days', '2', '-extfile', str(extensions), '-out', str(directory / f'{name}.pem')])


def free_port():
    with socket.socket() as candidate:
        candidate.bind(('127.0.0.1', 0))
        return candidate.getsockname()[1]


def eventually(predicate, message, timeout=20, diagnostics=None):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    detail = '\n' + diagnostics() if diagnostics else ''
    raise AssertionError(message + detail)


def checkpoint_fixture(root):
    import grp

    sys.path.insert(0, str(ARCHIVE / 'files'))
    try:
        spec = importlib.util.spec_from_file_location('native_projection_checkpoint', ARCHIVE / 'files/logging_checkpoint.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(ARCHIVE / 'files'))
    records = root / 'evidence/records/pve01'
    records.mkdir(parents=True)
    (root / 'evidence/source-catalogue.json').write_text(json.dumps({
        'tls_sources': [dict(name='pve01', tier=0, kind='security')], 'legacy_udp_sources': []}))
    config = dict(mount=str(root / 'nas'), marker='unused-offline', collector='log-1', data=str(root / 'evidence'),
                  state=str(root / 'checkpoint/state.json'), max_bytes=65536,
                  projection_root=str(root / 'approved'), projections={'operations': dict(
                      group=grp.getgrgid(os.getgid()).gr_name, sources=['pve01'],
                      fields=['source', 'source_tier', 'received_at'], approval='SEC-test')})
    source = records / '2026-10-26.jsonl'
    source.write_text('')
    return module, config, source


def append_record(source, number):
    row = dict(source='pve01', source_tier=0, received_at=datetime.now(timezone.utc).isoformat(),
               raw=f'secret-{number}', scope='forged-other-tenant')
    with source.open('a') as output:
        output.write(json.dumps(row) + '\n')


@unittest.skipUnless(NATIVE, 'Requires Linux filesystem durability and groups')
class ProjectionDurability(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='logging-projection-native-', dir='/tmp')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.module, self.config, self.source = checkpoint_fixture(self.root)

    def test_same_scope_policy_change_is_rejected_with_an_existing_cursor(self):
        append_record(self.source, 1)
        self.module.checkpoint(self.config, check_mount=False)
        previous = Path(self.config['state']).read_bytes()
        self.config['projections']['operations']['fields'].append('raw')
        self.config['projections']['operations']['content_approved'] = True
        append_record(self.source, 2)
        with self.assertRaises(ValueError):
            self.module.checkpoint(self.config, check_mount=False)
        self.assertEqual(Path(self.config['state']).read_bytes(), previous)

    def test_crash_after_publication_replays_without_advancing_or_duplicate_copy(self):
        append_record(self.source, 1)
        original = self.source.read_bytes()
        with patch.object(self.module.os, 'replace', side_effect=OSError('simulated pre-cursor crash')):
            with self.assertRaises(OSError):
                self.module.checkpoint(self.config, check_mount=False)
        self.assertFalse(Path(self.config['state']).exists())
        files = list((self.root / 'approved/operations').glob('*.jsonl'))
        self.assertEqual(len(files), 1)
        published = files[0].read_bytes()
        self.module.checkpoint(self.config, check_mount=False)
        self.assertEqual(files[0].read_bytes(), published)
        self.assertEqual(len(list(files[0].parent.glob('*.jsonl'))), 1)
        self.assertEqual(self.source.read_bytes(), original)
        row = json.loads(published)
        self.assertEqual(row['scope'], 'operations')
        self.assertNotIn('secret-', published.decode())

    @unittest.skipUnless(NATIVE and os.geteuid() == 0, 'Run as root only to drop a fixture child to nobody')
    def test_projection_reader_can_read_but_not_write_delete_or_read_originals(self):
        append_record(self.source, 1)
        self.module.checkpoint(self.config, check_mount=False)
        self.root.chmod(0o711)
        (self.root / 'approved').chmod(0o711)
        (self.root / 'evidence').chmod(0o700)
        published = next((self.root / 'approved/operations').glob('*.jsonl'))

        def reader_identity():
            os.setgroups([published.stat().st_gid])
            os.setgid(65534)
            os.setuid(65534)

        script = '''
from pathlib import Path
import sys
published, original = map(Path, sys.argv[1:])
assert published.read_bytes()
for operation in [lambda: published.open('ab'), lambda: published.unlink(), lambda: original.read_bytes()]:
    try:
        operation()
    except PermissionError:
        continue
    raise AssertionError('Reader exceeded approved read-only access')
'''
        command([sys.executable, '-c', script, str(published), str(self.source)], preexec_fn=reader_identity)


class AuditEndpoint(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        fixture = self.server.fixture
        fixture.requests.append((self.command, self.path, self.headers.get('Authorization')))
        offset = int(parse_qs(urlsplit(self.path).query)['offset'][0])
        if fixture.redirect:
            self.send_response(302)
            self.send_header('Location', fixture.redirect)
            self.end_headers()
            return
        if offset == fixture.fail_offset:
            self.send_error(503)
            return
        rows = fixture.rows[offset:offset + 1]
        data = json.dumps(dict(results=rows, count=len(fixture.rows),
                               next='https://never-follow.invalid/steal-token' if offset + 1 < len(fixture.rows) else None)).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@unittest.skipUnless(NATIVE and shutil.which('openssl'), 'Requires native Python TLS and OpenSSL')
class NetBoxHTTPS(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='netbox-audit-native-', dir='/tmp')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        certificate_set(self.root / 'tls')
        self.requests, self.redirect, self.fail_offset = [], None, None
        self.rows = [dict(id=number, action='create', postchange_data={'name': f'host-{number}'}) for number in [2, 3]]
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), AuditEndpoint)
        self.server.fixture = self
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.root / 'tls/server.pem', self.root / 'tls/server.key')
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        credentials = self.root / 'credentials'
        credentials.mkdir()
        (credentials / 'token').write_text('test-view-only-token\n')
        self.config = dict(state=str(self.root / 'state'), instance='netbox-main', auth_scheme='Bearer',
                           endpoint=f'https://localhost:{self.server.server_port}/api/core/object-changes/',
                           ca_file=str(self.root / 'tls/ca.pem'), max_records=100)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def collect(self):
        path = self.root / 'config.json'
        path.write_text(json.dumps(self.config))
        return subprocess.run([sys.executable, str(AUDIT / 'files/netbox_audit.py'), '--config', str(path)],
                              env=dict(os.environ, CREDENTIALS_DIRECTORY=str(self.root / 'credentials'),
                                       NO_PROXY='localhost,127.0.0.1', no_proxy='localhost,127.0.0.1'),
                              capture_output=True, text=True, timeout=15)

    def test_real_get_token_failed_page_retry_and_late_committing_event(self):
        self.fail_offset = 1
        result = self.collect()
        self.assertNotEqual(result.returncode, 0)
        first = next((self.root / 'state/events').glob('*.jsonl'))
        content = first.read_bytes()
        self.fail_offset = None
        result = self.collect()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['exported'], 1)
        self.assertEqual(first.read_bytes(), content)
        self.rows.insert(0, dict(id=1, action='update'))
        self.rows.sort(key=lambda row: row['id'])
        result = self.collect()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['exported'], 1)
        self.assertEqual({request[0] for request in self.requests}, {'GET'})
        self.assertTrue(all(request[2] == 'Bearer test-view-only-token' for request in self.requests))
        self.assertTrue(all(urlsplit(request[1]).path == '/api/core/object-changes/' for request in self.requests))
        self.assertTrue(all(parse_qs(urlsplit(request[1]).query)['ordering'] == ['id'] for request in self.requests))

    def test_redirect_and_untrusted_server_or_wrong_hostname_are_rejected(self):
        self.redirect = '/api/redirected/'
        result = self.collect()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('redirects are forbidden', result.stderr)
        self.assertEqual(len(self.requests), 1)
        self.redirect = None
        for index, changes in enumerate([dict(ca_file=str(self.root / 'tls/foreign.pem')),
                        dict(endpoint=self.config['endpoint'].replace('localhost', '127.0.0.1'))]):
            config = self.config
            self.config = dict(config, **changes, state=str(self.root / f'bad-{index}'))
            result = self.collect()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('CERTIFICATE_VERIFY_FAILED', result.stderr)
            self.assertEqual(len(self.requests), 1)
            self.config = config


@unittest.skipUnless(NATIVE and shutil.which('ansible-playbook'), 'Requires native Ansible and containers.podman')
class QuadletContract(unittest.TestCase):
    def test_real_module_generator_preserves_sections_identity_readonly_and_bind_mounts(self):
        paths = os.getenv('ANSIBLE_COLLECTIONS_PATH', os.path.expanduser('~/.ansible/collections')).split(os.pathsep)
        sys.path[:0] = paths
        try:
            from ansible_collections.containers.podman.plugins.module_utils.podman.quadlet import ContainerQuadlet
        finally:
            del sys.path[:len(paths)]
        tasks = yaml.safe_load((EXPORT / 'tasks/scope.yml').read_text())
        params = next(task['containers.podman.podman_container'] for task in tasks
                      if 'containers.podman.podman_container' in task)
        with tempfile.TemporaryDirectory(prefix='logging-quadlet-native-', dir='/tmp') as temporary:
            root = Path(temporary)
            source, target = root / 'params.json.j2', root / 'params.json'
            source.write_text('{{ quadlet_parameters | to_json }}')
            values = yaml.safe_load((EXPORT / 'defaults/main.yml').read_text())
            values.update(logging_export_scope=dict(name='operations'), logging_export_user=dict(uid=1234, group=1234),
                          logging_export_view=dict(stat=dict(gid=5678)), quadlet_parameters=params)
            ansible_render(root, [(source, target)], values)
            rendered = json.loads(target.read_text())
        self.assertEqual(rendered['state'], 'quadlet')
        self.assertEqual(rendered['user'], '1234:1234')
        self.assertEqual([str(group) for group in rendered['group_add']], ['5678'])
        self.assertIs(rendered['read_only'], True)
        self.assertIn('/srv/approved-log-projections/operations:/approved:ro,z', rendered['volume'])
        self.assertEqual(len(rendered['volume']), 3)
        content = ContainerQuadlet(defaultdict(lambda: None, rendered)).create_quadlet_content()
        sections = configparser.ConfigParser(strict=False, interpolation=None)
        sections.read_string(content)
        self.assertNotIn('restart', sections['Container'], content)
        self.assertNotIn('wantedby', sections['Container'], content)
        self.assertEqual(sections['Service']['Restart'], 'on-failure', content)
        self.assertEqual(sections['Install']['WantedBy'], 'multi-user.target', content)
        self.assertEqual(sections['Container']['ReadOnly'], 'true', content)

    def test_retirement_stops_service_before_removing_only_its_quadlet(self):
        tasks = yaml.safe_load((EXPORT / 'tasks/retire.yml').read_text())
        self.assertEqual(tasks[0]['ansible.builtin.systemd_service']['state'], 'stopped')
        removed = [task['ansible.builtin.file'] for task in tasks if 'ansible.builtin.file' in task]
        self.assertEqual(removed, [dict(path='{{ item.path }}', state='absent')])
        main = yaml.safe_load((EXPORT / 'tasks/main.yml').read_text())
        retirement = next(task for task in main if task.get('ansible.builtin.include_tasks') == 'retire.yml')
        self.assertIn('not in', retirement['when'])
        self.assertIn('logging_export_scopes', retirement['when'])


def otlp_bodies(path):
    bodies = []
    if not path.exists():
        return bodies

    def value(item):
        if 'kvlistValue' in item:
            return {pair['key']: value(pair['value']) for pair in item['kvlistValue'].get('values', [])}
        if 'arrayValue' in item:
            return [value(child) for child in item['arrayValue'].get('values', [])]
        return next(iter(item.values()), None)

    for line in path.read_text().splitlines():
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        for resource in message.get('resourceLogs', []):
            for scope in resource.get('scopeLogs', []):
                bodies.extend(value(row['body']) for row in scope.get('logRecords', []))
        if 'body' in message:
            body = message['body']
            bodies.append(json.loads(body) if isinstance(body, str) else body)
    return bodies


@unittest.skipUnless(NATIVE and COLLECTOR and shutil.which('ansible-playbook'),
                     'Set OTELCOL_BINARY and install native Ansible collections')
class NativeCollector(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='projection-collector-native-', dir='/tmp')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        certificate_set(self.root / 'tls')
        self.processes = []
        self.addCleanup(self.stop_all)
        module, config, source = checkpoint_fixture(self.root)
        for number in range(8):
            append_record(source, number)
        module.checkpoint(config, check_mount=False)
        self.approved = self.root / 'approved/operations'
        self.original = source.read_bytes()
        self.ids = {json.loads(row)['event_id'] for file in self.approved.glob('*.jsonl')
                    for row in file.read_text().splitlines()}

    def stop(self, process, kill=False):
        if process.poll() is None:
            process.kill() if kill else process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def stop_all(self):
        for process, handle in reversed(self.processes):
            self.stop(process)
            handle.close()

    def process_logs(self):
        return '\n'.join(f'{path.name}:\n{path.read_text()[-3000:]}'
                         for path in sorted(self.root.glob('*.log')))

    def start(self, name, config, env=None):
        path = self.root / f'{name}.yml'
        path.write_text(yaml.safe_dump(config, sort_keys=False))
        environment = dict(os.environ, **(env or {}))
        command([COLLECTOR, 'validate', '--config', str(path)], env=environment)
        handle = (self.root / f'{name}.log').open('w')
        process = subprocess.Popen([COLLECTOR, '--config', str(path)], stdout=handle,
                                   stderr=subprocess.STDOUT, env=environment)
        self.processes.append((process, handle))
        return process

    def receiver(self, name, port, require_client=True):
        output = self.root / f'{name}.jsonl'
        config = dict(receivers=dict(otlp=dict(protocols=dict(grpc=dict(
            endpoint=f'127.0.0.1:{port}', tls=dict(cert_file=str(self.root / 'tls/server.pem'),
                key_file=str(self.root / 'tls/server.key'), client_ca_file=str(self.root / 'tls/ca.pem')))))),
            exporters=dict(file=dict(path=str(output), flush_interval='100ms')),
            service=dict(telemetry=dict(metrics=dict(level='none')),
                         pipelines=dict(logs=dict(receivers=['otlp'], exporters=['file']))))
        if not require_client:
            del config['receivers']['otlp']['protocols']['grpc']['tls']['client_ca_file']
        process = self.start(name, config)

        def listening():
            if process.poll() is not None:
                raise AssertionError((self.root / f'{name}.log').read_text())
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                    return True
            except OSError:
                return False

        eventually(listening, 'Native OTLP receiver did not start')
        return output

    def sender_config(self, endpoint, state='sender-state'):
        values = yaml.safe_load((EXPORT / 'defaults/main.yml').read_text())
        # Pin fixture transport without relying on external DNS; still verify the leaf's DNS SAN.
        values['logging_export_scope'] = dict(endpoint=endpoint.replace('localhost:', '127.0.0.1:', 1))
        rendered = self.root / 'sender-rendered.yml'
        ansible_render(self.root, [(EXPORT / 'templates/collector.yml.j2', rendered)], values)
        config = yaml.safe_load(rendered.read_text())
        config['extensions']['file_storage']['directory'] = str(self.root / state)
        config['receivers']['filelog']['include'] = [str(self.approved / '*.jsonl')]
        config['exporters']['otlp']['tls'] = dict(ca_file=str(self.root / 'tls/ca.pem'),
                                                cert_file=str(self.root / 'tls/client.pem'),
                                                key_file=str(self.root / 'tls/client.key'),
                                                server_name_override='localhost')
        config['service']['telemetry'] = dict(metrics=dict(level='none'))
        return config

    def prepper(self, pipelines, ports):
        """Keep rendered TLS/basic-auth OTLP sources; substitute only terminal local file sinks."""
        home = Path(PREPPER)
        java = Path(os.environ['DATA_PREPPER_JAVA']) if os.getenv('DATA_PREPPER_JAVA') else next(home.glob('openjdk/*/bin/java'))
        native = deepcopy(pipelines)
        outputs = []
        for (name, pipeline), port in zip(native.items(), ports):
            source = pipeline['source']['otel_logs_source']
            source.update(port=port, sslKeyCertChainFile=str(self.root / 'tls/server.pem'),
                          sslKeyFile=str(self.root / 'tls/server.key'))
            output = self.root / f'prepper-{name}.jsonl'
            pipeline['sink'] = [dict(file=dict(path=str(output), append=True))]
            outputs.append(output)
        path, settings = self.root / 'native-prepper.yml', self.root / 'native-prepper-config.yml'
        path.write_text(yaml.safe_dump(native))
        settings.write_text(yaml.safe_dump(dict(ssl=False, serverPort=free_port(), metricRegistries=[],
            authentication=dict(http_basic=dict(username='fixture', password='fixture')),
            processorShutdownTimeout='1s', sinkShutdownTimeout='1s',
            peer_forwarder=dict(discovery_mode='local_node', port=free_port(), ssl=False))))
        log_config = self.root / 'log4j2.xml'
        log_config.write_text('<Configuration><Appenders><Console name="stdout" target="SYSTEM_OUT">'
                              '<PatternLayout pattern="%d %p %c %m%n"/></Console></Appenders>'
                              '<Loggers><Root level="info"><AppenderRef ref="stdout"/></Root></Loggers></Configuration>')
        handle = (self.root / 'native-prepper.log').open('w')
        process = subprocess.Popen([str(java), '-Xms64m', '-Xmx384m', f'-Ddata-prepper.dir={self.root}',
            f'-Dlog4j.configurationFile={log_config}', '-cp', str(home / 'lib/*'),
            'org.opensearch.dataprepper.DataPrepperExecute', str(path), str(settings)],
            cwd=self.root, stdout=handle, stderr=subprocess.STDOUT)
        self.processes.append((process, handle))

        def listening():
            if process.poll() is not None:
                raise AssertionError((self.root / 'native-prepper.log').read_text())
            try:
                with socket.create_connection(('127.0.0.1', ports[0]), timeout=0.2):
                    return True
            except OSError:
                return False

        eventually(listening, 'Native Data Prepper did not start', timeout=45)
        return outputs

    def wait_error(self, name):
        log = self.root / f'{name}.log'
        eventually(lambda: 'will retry' in log.read_text().lower(),
                   f'No retry observed: {log.read_text()}', timeout=20)

    def test_real_mtls_queue_survives_sigkill_without_input_and_offsets_survive_restart(self):
        port = free_port()
        config = self.sender_config(f'localhost:{port}')
        sender = self.start('sender-outage', config)
        self.wait_error('sender-outage')
        eventually(lambda: any((self.root / 'sender-state').glob('*')), 'No persistent queue or cursor files')
        self.stop(sender, kill=True)
        saved = next(self.approved.glob('*.jsonl'))
        saved.rename(saved.with_suffix('.held'))
        output = self.receiver('destination', port)
        replay = self.start('sender-replay', config)
        eventually(lambda: len(otlp_bodies(output)) >= len(self.ids),
                   'Persistent queue failed to replay while all matching input files were absent',
                   diagnostics=self.process_logs)
        delivered = otlp_bodies(output)
        self.assertEqual({row['event_id'] for row in delivered}, self.ids)
        self.assertTrue(all(row['scope'] == 'operations' for row in delivered))
        self.assertNotIn('secret-', output.read_text())
        self.stop(replay)
        saved.with_suffix('.held').rename(saved)
        restarted = self.start('sender-offset-restart', config)
        time.sleep(2)
        self.stop(restarted)
        self.assertEqual(len(otlp_bodies(output)), len(self.ids), 'Restart reread already acknowledged input')
        self.assertEqual((self.root / 'evidence/records/pve01/2026-10-26.jsonl').read_bytes(), self.original)

    def test_real_mtls_refuses_wrong_ca_hostname_and_client_identity(self):
        port = free_port()
        output = self.receiver('tls-destination', port)
        for name in ['wrong-ca', 'wrong-hostname', 'wrong-client']:
            config = self.sender_config(f'localhost:{port}', state=name + '-state')
            tls = config['exporters']['otlp']['tls']
            if name == 'wrong-ca':
                tls['ca_file'] = str(self.root / 'tls/foreign.pem')
            elif name == 'wrong-hostname':
                tls['server_name_override'] = 'not-localhost.invalid'
            else:
                tls.update(cert_file=str(self.root / 'tls/rogue.pem'), key_file=str(self.root / 'tls/rogue.key'))
            sender = self.start(name, config)
            self.wait_error(name)
            self.stop(sender)
            self.assertEqual(otlp_bodies(output), [], f'{name} was accepted by the authenticated receiver')

    def test_native_tier1_gateway_routes_projection_grpc_to_a_fixed_data_prepper_scope(self):
        self.gateway_roundtrip(expect_parsed_record=False)

    @unittest.skipUnless(PREPPER, 'Set DATA_PREPPER_HOME to verify the actual parse_json processor')
    def test_native_parse_json_restores_nested_record_without_changing_publisher(self):
        self.gateway_roundtrip(expect_parsed_record=True)

    def gateway_roundtrip(self, expect_parsed_record):
        operation_port, other_port, backend_port, other_backend = [free_port() for _ in range(4)]
        values = yaml.safe_load((OBSERVABILITY / 'defaults/main.yml').read_text())
        values['observability_prepper_auth'] = dict(username='prepper', password='fixture')
        values['observability_log_scopes'] = [dict(name='operations', kind='projection', port=operation_port),
                                             dict(name='other', kind='projection', port=other_port)]
        rendered, pipelines = self.root / 'gateway.yml', self.root / 'prepper.yml'
        ansible_render(self.root, [(OBSERVABILITY / 'templates/collector-config.yml.j2', rendered),
                                  (OBSERVABILITY / 'templates/prepper-pipelines.yml.j2', pipelines)], values)
        prepper = yaml.safe_load(pipelines.read_text())
        self.assertEqual(prepper['operations-logs']['sink'][0]['opensearch']['index'],
                         'projection-operations-logs-%{yyyy.MM.dd}')
        self.assertEqual(prepper['operations-logs']['source']['otel_logs_source']['port'], 21890)
        expected_processors = [dict(parse_json=dict(
            source=field, destination=field, overwrite_if_destination_exists=True,
            tags_on_failure=['projection_record_parse_failure'])) for field in ['body', 'body/record']]
        for scope in values['observability_log_scopes']:
            self.assertEqual(prepper[f'{scope["name"]}-logs'].get('processor'), expected_processors)
        if PREPPER:
            approved_output, other_output = self.prepper(prepper, [backend_port, other_backend])
        else:
            approved_output = self.receiver('fixed-operations-backend', backend_port, require_client=False)
            other_output = self.receiver('fixed-other-backend', other_backend, require_client=False)
        config = yaml.safe_load(rendered.read_text())
        config['receivers'] = {key: item for key, item in config['receivers'].items() if item is not None}
        config['exporters'] = {key: item for key, item in config['exporters'].items() if item is not None}
        config['service']['pipelines'] = {key: item for key, item in config['service']['pipelines'].items()
                                          if item is not None}
        for name, receiver in config['receivers'].items():
            receiver['protocols'] = {key: item for key, item in receiver['protocols'].items() if item is not None}
            grpc = receiver['protocols']['grpc']
            if name == 'otlp':
                grpc['endpoint'] = f'127.0.0.1:{free_port()}'
            else:
                grpc['endpoint'] = grpc['endpoint'].replace('0.0.0.0', '127.0.0.1')
            grpc['tls'] = dict(cert_file=str(self.root / 'tls/server.pem'), key_file=str(self.root / 'tls/server.key'),
                               client_ca_file=str(self.root / ('tls/foreign.pem' if name == 'otlp/other' else 'tls/ca.pem')))
        for name, exporter in config['exporters'].items():
            exporter['tls'] = dict(ca_file=str(self.root / 'tls/ca.pem'))
            if name == 'otlp/operations-logs':
                exporter['endpoint'] = f'127.0.0.1:{backend_port}'
                exporter['tls']['server_name_override'] = 'localhost'
            elif name == 'otlp/other-logs':
                exporter['endpoint'] = f'127.0.0.1:{other_backend}'
                exporter['tls']['server_name_override'] = 'localhost'
        config['extensions']['file_storage']['directory'] = str(self.root / 'gateway-state')
        config['extensions']['health_check']['endpoint'] = f'127.0.0.1:{free_port()}'
        config['service']['telemetry'] = dict(metrics=dict(level='none'))
        self.start('native-gateway', config, env=dict(VM_USERNAME='vm', VM_PASSWORD='fixture',
                                                    DP_USERNAME='prepper', DP_PASSWORD='fixture'))
        forged = dict(event_id='forged-scope-event', scope='other', record=dict(source='pve01'))
        (self.approved / 'forged.jsonl').write_text(json.dumps(forged) + '\n')
        sender = self.start('to-native-gateway', self.sender_config(f'localhost:{operation_port}'))
        eventually(lambda: len(otlp_bodies(approved_output)) >= len(self.ids) + 1,
                   'Native Tier 1 gateway failed to deliver OTLP/gRPC projection logs', timeout=25,
                   diagnostics=self.process_logs)
        self.stop(sender)
        delivered_forged = next(row for row in otlp_bodies(approved_output) if row['event_id'] == forged['event_id'])
        self.assertEqual(delivered_forged['scope'], 'other')
        record = delivered_forged['record']
        if expect_parsed_record:
            self.assertIsInstance(record, dict, approved_output.read_text()[:4000])
            self.assertTrue(all(isinstance(row['record'], dict) for row in otlp_bodies(approved_output)))
            native_rows = [json.loads(line) for line in approved_output.read_text().splitlines()]
            self.assertTrue(all(isinstance(row['body'], dict) for row in native_rows))
            self.assertNotIn('projection_record_parse_failure', approved_output.read_text())
        self.assertEqual(json.loads(record) if isinstance(record, str) else record, forged['record'])
        self.assertEqual(otlp_bodies(other_output), [])
        sender = self.start('cross-scope-denied', self.sender_config(f'localhost:{other_port}', state='cross-scope-state'))
        self.wait_error('cross-scope-denied')
        self.stop(sender)
        self.assertEqual(otlp_bodies(other_output), [], 'A certificate for operations entered the other scope')


if __name__ == '__main__':
    unittest.main()
