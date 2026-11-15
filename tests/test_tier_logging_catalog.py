"""Native catalog selection and local health probes without network or guest deployment."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


ROLE = UPSTREAM / 'shared/ansible/roles/log_forwarder'
NATIVE = os.name != 'nt' and shutil.which('ansible-playbook') and shutil.which('openssl')


@unittest.skipUnless(NATIVE, 'Requires Linux native Ansible and OpenSSL')
class ProducerCatalog(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='logging-catalog-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.role = self.root / 'roles/log_forwarder'
        shutil.copytree(ROLE, self.role)
        # Exercise the real playbook, catalog, defaults, validation and result. Guest
        # package/key installation has separate tests and must never run on this controller.
        for name in ('requests', 'install'):
            (self.role / f'tasks/{name}.yml').write_text(yaml.safe_dump([
                {'ansible.builtin.debug': {'msg': f'{name} guest mutation excluded from selection check'}}]))
        main = yaml.safe_load((self.role / 'tasks/main.yml').read_text())
        main.append({'ansible.builtin.copy': {
            'dest': str(self.root / '{{ inventory_hostname }}.json'),
            'content': '{{ {"result": log_forwarder_result, "peer": log_forwarder_peer, '
                       '"target": log_forwarder_target, "address": ansible_host, '
                       '"user": ansible_user, "watchdog": log_forwarder_watchdog_url | length > 0} | to_json }}',
            'mode': '0600'}, 'no_log': True})
        (self.role / 'tasks/main.yml').write_text(yaml.safe_dump(main, sort_keys=False))
        self.env = dict(os.environ, ANSIBLE_ROLES_PATH=str(self.root / 'roles'),
                        ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local'),
                        ANSIBLE_NOCOLOR='1')
        self.inventory = {
            'all': {'vars': {
                'platform_domain': 'corp.example.test',
                'platform_internal_domain': 'internal.example.test',
                'platform_host_ips': {'node-a': '192.0.2.10', 'node-b': '192.0.2.11'},
                'ansible_host': '{{ platform_host_ips.get(inventory_hostname, inventory_hostname) }}',
                'ansible_user': '{{ inventory_hostname }}-operator'},
                'children': {
                    'existing': {'hosts': {
                        'untouched': {'ansible_host': 'must-never-connect.invalid'},
                        'node-a': {'ansible_connection': 'local'},
                        'node-b': {'ansible_connection': 'local'}}},
                    'logging_producers': {'hosts': {'untouched': {}}}}}}

    def run_recipe(self, values, *, tier=0, limit=None, mode='prepare', success=True):
        repo = self.root / f'tier-{tier}/ansible'
        recipe = repo / 'playbooks/deployment/logging-producers.yml'
        variables = repo / 'group_vars'
        inventory = repo / 'inventory/hosts.yml'
        for directory in (recipe.parent, variables, inventory.parent):
            directory.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(UPSTREAM / f'tier-{tier}/ansible/playbooks/deployment/logging-producers.yml', recipe)
        inventory.write_text(yaml.safe_dump(self.inventory, sort_keys=False))
        if values is not None:
            (variables / 'logging_producers.yml').write_text(yaml.safe_dump(values, sort_keys=False))
        args = ['ansible-playbook', '-i', str(inventory), str(recipe), '-e', json.dumps({
            'ansible_become': False, 'ansible_service_mgr': 'systemd', 'log_forwarder_mode': mode,
            'log_forwarder_requests': str(self.root / 'requests'),
            'log_forwarder_credentials': str(self.root / 'public')})]
        if limit:
            args += ['--limit', limit]
        result = subprocess.run(args, env=self.env, capture_output=True, text=True, timeout=100)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def receipt(self, name):
        return json.loads((self.root / f'{name}.json').read_text())

    def test_all_three_real_entry_points_select_existing_hosts_and_reuse_connections(self):
        for tier in (0, 1, 2):
            with self.subTest(tier=tier):
                result = self.run_recipe({'logging_producer_hosts': {
                    'node-a': {}, 'node-b': {'setup': 'cache'}}}, tier=tier)
                for name, address in (('node-a', '192.0.2.10'), ('node-b', '192.0.2.11')):
                    receipt = self.receipt(name)
                    self.assertEqual(receipt['peer'], 'logs.internal.example.test')
                    self.assertEqual(receipt['target'], receipt['peer'])
                    self.assertEqual(receipt['address'], address)
                    self.assertEqual(receipt['user'], name + '-operator')
                    self.assertEqual(receipt['result'], {
                        'mode': 'prepare',
                        'streams': [{'name': name + '-os', 'kind': 'security', 'input': 'journal'}],
                        'public_request_paths': [str(self.root / f'requests/{name}-os.csr')]})
                    (self.root / f'{name}.json').unlink()
                self.assertFalse((self.root / 'untouched.json').exists())
                self.assertNotIn('UNREACHABLE', result.stdout)

    def test_host_limit_does_not_require_localhost_and_does_not_contact_other_producers(self):
        self.run_recipe({'logging_producer_hosts': {'node-a': {}, 'node-b': {}}}, limit='node-b')
        self.assertTrue((self.root / 'node-b.json').exists())
        self.assertFalse((self.root / 'node-a.json').exists())
        self.assertFalse((self.root / 'untouched.json').exists())

    def test_explicit_streams_common_peer_and_private_host_watchdog(self):
        endpoint = 'https://monitor.example.test/heartbeat/catalog-private-capability'
        streams = [{'name': 'accepted-os', 'kind': 'security', 'input': 'journal'},
                   {'name': 'accepted-app', 'kind': 'application', 'input': 'files',
                    'files': ['/var/log/example-app/events.log']}]
        result = self.run_recipe({
            'log_forwarder_peer': 'logs.accepted.example.test',
            'log_forwarder_target': '192.0.2.30',
            'logging_producer_hosts': {'node-a': {'streams': streams, 'watchdog_url': endpoint},
                                       'node-b': {}}}, mode='install')
        receipt = self.receipt('node-a')
        self.assertEqual(receipt['result']['streams'], [{key: stream[key] for key in ('name', 'kind', 'input')}
                                                        for stream in streams])
        self.assertEqual(receipt['result']['mode'], 'install')
        self.assertEqual(receipt['peer'], 'logs.accepted.example.test')
        self.assertEqual(receipt['target'], '192.0.2.30')
        self.assertTrue(receipt['watchdog'])
        self.assertFalse(self.receipt('node-b')['watchdog'])
        self.assertNotIn(endpoint, result.stdout + result.stderr)
        self.assertNotIn('watchdog_url', json.dumps(receipt['result']))

    def test_legacy_group_and_host_vars_keep_existing_identities_without_catalog(self):
        self.inventory['all']['children']['logging_producers']['hosts'] = {'node-a': {}}
        host_vars = self.root / 'tier-0/ansible/inventory/host_vars'
        host_vars.mkdir(parents=True)
        (host_vars / 'node-a.yml').write_text(yaml.safe_dump({
            'log_forwarder_streams': [{'name': 'trusted-identity', 'kind': 'security', 'input': 'journal'}],
            'log_forwarder_watchdog_url': 'https://monitor.example.test/retained-private-capability'}))
        result = self.run_recipe({'log_forwarder_peer': 'logs.legacy.example.test'})
        self.assertEqual(self.receipt('node-a')['result']['streams'][0]['name'], 'trusted-identity')
        self.assertTrue(self.receipt('node-a')['watchdog'])
        self.assertEqual(self.receipt('node-a')['peer'], 'logs.legacy.example.test')
        self.assertFalse((self.root / 'node-b.json').exists())
        self.assertNotIn('retained-private-capability', result.stdout + result.stderr)

    def test_catalog_retains_issued_legacy_identity_when_no_stream_override_is_given(self):
        self.inventory['all']['children']['existing']['hosts']['node-a']['log_forwarder_streams'] = [
            {'name': 'retained-os', 'kind': 'security', 'input': 'journal'}]
        self.run_recipe({'logging_producer_hosts': {'node-a': {}}})
        self.assertEqual(self.receipt('node-a')['result']['streams'][0]['name'], 'retained-os')

    def test_omitted_file_preserves_legacy_selection_and_domain_fallback(self):
        del self.inventory['all']['vars']['platform_internal_domain']
        self.inventory['all']['children']['logging_producers']['hosts'] = {'node-a': {}}
        self.inventory['all']['children']['existing']['hosts']['node-a']['log_forwarder_streams'] = [
            {'name': 'retained-os', 'kind': 'security', 'input': 'journal'}]
        self.run_recipe(None)
        self.assertEqual(self.receipt('node-a')['peer'], 'logs.corp.example.test')

    def test_empty_catalog_contacts_no_hosts_even_with_legacy_group_members(self):
        self.run_recipe({'logging_producer_hosts': {}})
        self.assertEqual(list(self.root.glob('*.json')), [])

    def test_unknown_host_and_malformed_catalog_fail_before_any_target_work(self):
        for catalog in ({'missing': {}}, ['node-a'], {'node-a': None},
                        {'node-a': {'streams': []}}, {'node-a': {'setup': '../../escape'}}):
            with self.subTest(catalog=catalog):
                self.run_recipe({'logging_producer_hosts': catalog}, success=False)
                self.assertEqual(list(self.root.glob('*.json')), [])

    def test_all_three_entry_points_parse_before_controller_selection_has_run(self):
        inventory = self.root / 'syntax-hosts.yml'
        inventory.write_text(yaml.safe_dump(self.inventory, sort_keys=False))
        for tier in (0, 1, 2):
            with self.subTest(tier=tier):
                recipe = UPSTREAM / f'tier-{tier}/ansible/playbooks/deployment/logging-producers.yml'
                result = subprocess.run(['ansible-playbook', '--syntax-check', '-i', str(inventory), str(recipe)],
                                        env=dict(self.env, ANSIBLE_ROLES_PATH=str(UPSTREAM / 'shared/ansible/roles')),
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(list(self.root.glob('*.json')), [])


@unittest.skipUnless(NATIVE, 'Requires Linux native Ansible and OpenSSL')
class OptionalWatchdog(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='logging-health-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = self.root / 'config'
        self.config.mkdir()
        self.env = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(self.root / 'ansible-local'), ANSIBLE_NOCOLOR='1')

    def configure(self, *, success=True, **values):
        # Run the actual watchdog configuration tasks. Exclude unit installation/start
        # because this test process is not a systemd-managed guest.
        tasks = yaml.safe_load((ROLE / 'tasks/health.yml').read_text())
        boundary = next(i for i, task in enumerate(tasks) if 'ansible.builtin.template' in task)
        configuration_tasks = deepcopy(tasks[:boundary])
        for task in configuration_tasks:
            if 'ansible.builtin.copy' in task:
                # Keep the same private-file operation under the unprivileged test owner.
                task['ansible.builtin.copy'].pop('owner', None)
                task['ansible.builtin.copy'].pop('group', None)
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        defaults.update(log_forwarder_config=str(self.config), **values)
        play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False, 'vars': defaults,
                 'tasks': [{'ansible.builtin.import_tasks': str(ROLE / 'tasks/watchdog-inputs.yml')},
                           *configuration_tasks]}]
        path = self.root / 'configure.yml'
        path.write_text(yaml.safe_dump(play, sort_keys=False))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(path)], env=self.env,
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_optional_local_only_and_required_missing_url(self):
        result = self.configure()
        self.assertIn('Independent missed-heartbeat alerting is not commissioned', result.stdout)
        self.assertFalse((self.config / 'watchdog.curl').exists())
        missing = self.configure(log_forwarder_watchdog_required=True, success=False)
        self.assertIn('independent monitoring service', missing.stdout)

    def test_only_https_and_no_config_injection_is_accepted(self):
        for endpoint in ('http://monitor.example.test/token', 'https:///missing-host',
                         'https://monitor.example.test/token\noutput = /tmp/leak',
                         'https://user:secret@monitor.example.test/token'):
            with self.subTest(endpoint=endpoint):
                result = self.configure(log_forwarder_watchdog_url=endpoint, success=False)
                self.assertNotIn(endpoint, result.stdout + result.stderr)
                self.assertFalse((self.config / 'watchdog.curl').exists())

    def test_private_capability_rotation_and_explicit_retirement(self):
        endpoint = 'https://monitor.example.test/token/private-watchdog-capability'
        result = self.configure(log_forwarder_watchdog_url=endpoint, log_forwarder_watchdog_required=True)
        path = self.config / 'watchdog.curl'
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.read_text(), f'url = "{endpoint}"\n')
        self.assertNotIn(endpoint, result.stdout + result.stderr)
        self.configure(success=False)
        self.assertEqual(path.read_text(), f'url = "{endpoint}"\n')
        replacement = endpoint + '-rotated'
        self.configure(log_forwarder_watchdog_url=replacement)
        self.assertEqual(path.read_text(), f'url = "{replacement}"\n')
        self.configure(log_forwarder_watchdog_disable=True)
        self.assertFalse(path.exists())


@unittest.skipUnless(NATIVE, 'Requires Linux native filesystem and OpenSSL probes')
class NativeProducerHealth(unittest.TestCase):
    def setUp(self):
        from jinja2 import Environment, StrictUndefined

        self.temporary = tempfile.TemporaryDirectory(prefix='producer-health-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = self.root / 'config/producer'
        self.state = self.root / 'state/producer'
        self.bin = self.root / 'bin'
        for directory in (self.config, self.state, self.bin):
            directory.mkdir(parents=True)
        self.values = dict(log_forwarder_streams=[{'name': 'producer'}],
                           log_forwarder_config=str(self.config.parent),
                           log_forwarder_state=str(self.state.parent),
                           log_forwarder_queue_bytes=16777216, log_forwarder_min_free_bytes=16777216)
        self.template = Environment(undefined=StrictUndefined).from_string(
            (ROLE / 'templates/health.sh.j2').read_text())
        self.certificate()
        (self.bin / 'systemctl').write_text('#!/bin/sh\nexit "${HEALTH_TEST_SERVICE_RC:-0}"\n')
        (self.bin / 'curl').write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$HEALTH_TEST_CURL_LOG"\n'
                                     'exit "${HEALTH_TEST_CURL_RC:-0}"\n')
        for path in self.bin.iterdir():
            path.chmod(0o700)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        HEALTH_TEST_CURL_LOG=str(self.root / 'curl-args'))

    def certificate(self, *, revoked=False, expired=False):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

        now = datetime.now(timezone.utc)
        key = ec.generate_private_key(ec.SECP384R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Test CA')])
        ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
              .serial_number(1).not_valid_before(now - timedelta(days=10)).not_valid_after(now + timedelta(days=10))
              .add_extension(x509.BasicConstraints(ca=True, path_length=None), True).sign(key, hashes.SHA256()))
        leaf = (x509.CertificateBuilder()
                .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'producer')]))
                .issuer_name(name).public_key(key.public_key()).serial_number(2)
                .not_valid_before(now - timedelta(days=2))
                .not_valid_after(now + timedelta(days=-1 if expired else 3))
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), False)
                .sign(key, hashes.SHA256()))
        crl = x509.CertificateRevocationListBuilder().issuer_name(name).last_update(now - timedelta(minutes=1))
        crl = crl.next_update(now + timedelta(days=1))
        if revoked:
            crl = crl.add_revoked_certificate(x509.RevokedCertificateBuilder().serial_number(2)
                                              .revocation_date(now - timedelta(minutes=1)).build())
        crl = crl.sign(key, hashes.SHA256())
        for filename, value in (('ca.pem', ca), ('client.pem', leaf), ('revoked.pem', crl)):
            (self.config / filename).write_bytes(value.public_bytes(serialization.Encoding.PEM))

    def probe(self, *, success=True, **environment):
        script = self.root / 'health.sh'
        script.write_text(self.template.render(**self.values))
        result = subprocess.run(['sh', str(script)], env=dict(self.env, **environment),
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_local_health_executes_native_certificate_and_capacity_probes_without_url(self):
        self.probe()
        self.assertFalse((self.root / 'curl-args').exists())

    def test_inactive_service_full_queue_or_low_space_blocks_health(self):
        self.probe(HEALTH_TEST_SERVICE_RC='3', success=False)
        queued = self.state / 'outbound'
        with queued.open('wb') as handle:
            handle.truncate(15 * 1024 * 1024)
        self.probe(success=False)
        queued.unlink()
        self.values['log_forwarder_min_free_bytes'] = 2 ** 62
        self.probe(success=False)
        self.assertFalse((self.root / 'curl-args').exists())

    def test_native_openssl_rejects_revoked_and_expired_certificates(self):
        self.certificate(revoked=True)
        self.probe(success=False)
        self.certificate(expired=True)
        self.probe(success=False)

    def test_external_failure_blocks_heartbeat_success_and_url_stays_out_of_arguments(self):
        endpoint = 'https://monitor.example.test/private-capability'
        (self.config.parent / 'watchdog.curl').write_text(f'url = "{endpoint}"\n')
        self.probe(HEALTH_TEST_CURL_RC='22', success=False)
        self.probe()
        arguments = (self.root / 'curl-args').read_text()
        self.assertIn('--config', arguments)
        self.assertNotIn(endpoint, arguments)
        self.assertNotIn(endpoint, (self.root / 'health.sh').read_text())
