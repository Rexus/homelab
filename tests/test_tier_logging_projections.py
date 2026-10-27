"""Protected evidence remains local; only approved immutable copies cross tiers."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

if os.name != 'nt':
    import grp

from jinja2 import Environment, FileSystemLoader, StrictUndefined
import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ARCHIVE = UPSTREAM / 'tier-0/ansible/roles/logging_archive'
EXPORT = UPSTREAM / 'tier-0/ansible/roles/logging_export'
AUDIT = UPSTREAM / 'tier-0/ansible/roles/netbox_audit'


@unittest.skipIf(os.name == 'nt', 'Native Linux groups, fsync and flock')
class SearchProjectionTests(unittest.TestCase):
    def setUp(self):
        previous_umask = os.umask(0o077)
        self.addCleanup(os.umask, previous_umask)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        sys.path.insert(0, str(ARCHIVE / 'files'))
        self.addCleanup(sys.path.remove, str(ARCHIVE / 'files'))
        spec = importlib.util.spec_from_file_location('projection_test_checkpoint', ARCHIVE / 'files/logging_checkpoint.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        (self.root / 'data/records/pve01').mkdir(parents=True)
        (self.root / 'data/source-catalogue.json').write_text(json.dumps({
            'tls_sources': [{'name': 'pve01', 'tier': 0, 'kind': 'security'}], 'legacy_udp_sources': []}))
        self.record = self.root / 'data/records/pve01/2026-10-26.jsonl'
        self.original = json.dumps({'source': 'pve01', 'source_tier': 0, 'raw': 'secret-value',
                                    'received_at': '2026-10-26', 'kind': 'application', 'scope': 'forged'}) + '\n'
        self.record.write_text(self.original)
        self.policy = {'sources': ['pve01'], 'fields': ['source', 'received_at'],
                       'group': grp.getgrgid(os.getgid()).gr_name, 'approval': 'SEC-001'}
        self.config = {'mount': str(self.root / 'nas'), 'marker': 'commissioned', 'collector': 'log-1',
                       'data': str(self.root / 'data'), 'state': str(self.root / 'state/checkpoint.json'),
                       'max_bytes': 65536, 'projections': {'operations': self.policy},
                       'projection_root': str(self.root / 'projections')}

    def test_field_allowlist_does_not_trust_producer_scope_or_copy_raw(self):
        self.module.checkpoint(self.config, check_mount=False)
        copied = next((self.root / 'projections/operations').glob('*.jsonl'))
        row = json.loads(copied.read_text())
        self.assertEqual(row['scope'], 'operations')
        self.assertEqual(set(row['record']), {'source', 'received_at'})
        self.assertNotIn('secret-value', copied.read_text())
        self.assertEqual(self.record.read_text(), self.original)
        self.assertEqual(len(row['event_id']), 64)
        self.assertEqual(copied.stat().st_mode & 0o777, 0o640)
        Path(self.config['state']).unlink()
        self.module.checkpoint(self.config, check_mount=False)
        self.assertEqual(json.loads(copied.read_text())['event_id'], row['event_id'])

    def test_content_export_and_unknown_sources_require_approval(self):
        self.policy['fields'].append('raw')
        with self.assertRaisesRegex(ValueError, 'sensitive-content approval'):
            self.module.checkpoint(self.config, check_mount=False)
        self.policy['content_approved'] = True
        self.policy['sources'] = ['not-catalogued']
        with self.assertRaisesRegex(ValueError, 'receiver-owned catalogue'):
            self.module.checkpoint(self.config, check_mount=False)
        self.assertFalse(Path(self.config['state']).exists())

    def test_changed_policy_does_not_overwrite_existing_copies(self):
        self.module.checkpoint(self.config, check_mount=False)
        Path(self.config['state']).unlink()
        self.policy['fields'].append('source_tier')
        with self.assertRaisesRegex(ValueError, 'collision'):
            self.module.checkpoint(self.config, check_mount=False)


@unittest.skipIf(os.name == 'nt', 'Native Linux durable audit ledger')
class NetBoxAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        spec = importlib.util.spec_from_file_location('netbox_audit_test', AUDIT / 'files/netbox_audit.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.config = {'state': self.temp.name, 'instance': 'netbox-main',
                       'endpoint': 'https://netbox.test/api/core/object-changes/', 'max_records': 100}
        self.rows = [{'id': 1, 'time': '2026-10-26', 'user_name': 'admin',
                      'action': 'create', 'postchange_data': {'name': 'host-a'}}]

    def fetch(self, offset):
        return {'results': self.rows[offset:], 'count': len(self.rows), 'next': None}

    def test_replay_late_commit_and_change_detection(self):
        self.rows[0]['id'] = 2
        self.assertEqual(self.module.collect(self.config, self.fetch)['exported'], 1)
        self.rows.insert(0, dict(self.rows[0], id=1))
        self.assertEqual(self.module.collect(self.config, self.fetch)['exported'], 1)
        self.assertEqual(self.module.collect(self.config, self.fetch)['exported'], 0)
        self.rows[0]['action'] = 'delete'
        with self.assertRaisesRegex(ValueError, 'audit event changed'):
            self.module.collect(self.config, self.fetch)

    def test_page_failure_and_identity_replacement_do_not_erase_history(self):
        def failure(offset):
            if offset:
                raise OSError('temporary API failure')
            return {'results': self.rows, 'count': 2, 'next': 'ignored-untrusted-url'}
        with self.assertRaises(OSError):
            self.module.collect(self.config, failure)
        self.assertEqual(len(list(Path(self.temp.name).glob('events/*.jsonl'))), 1)
        self.assertEqual(self.module.collect(self.config, self.fetch)['exported'], 0)
        self.config['endpoint'] = 'https://other.test/api/core/object-changes/'
        with self.assertRaisesRegex(ValueError, 'audit event changed'):
            self.module.collect(self.config, self.fetch)

    def test_unordered_or_unbounded_history_fails(self):
        self.rows.extend([dict(self.rows[0], id=1)])
        with self.assertRaisesRegex(ValueError, 'ordering=id'):
            self.module.collect(self.config, self.fetch)
        self.config['max_records'] = 1
        with self.assertRaisesRegex(ValueError, 'polling budget'):
            self.module.collect(self.config, self.fetch)


class ExportConfigurationTests(TierRepositoryTestCase):
    def test_checkpoint_sandbox_allows_only_the_approved_copy_root(self):
        defaults = yaml.safe_load((ARCHIVE / 'defaults/main.yml').read_text())
        environment = Environment(undefined=StrictUndefined)
        unit = environment.from_string((ARCHIVE / 'templates/archive.service.j2').read_text()).render(defaults)
        writable = next(line.split('=', 1)[1].split() for line in unit.splitlines()
                        if line.startswith('ReadWritePaths='))
        self.assertIn(defaults['logging_archive_projection_root'], writable)
        self.assertNotIn('/srv', writable)
        self.assertIn('UMask=0077', unit)
        self.assertIn('ProtectSystem=strict', unit)

    def test_native_collector_configuration_and_no_raw_mount(self):
        defaults = yaml.safe_load((EXPORT / 'defaults/main.yml').read_text())
        environment = Environment(loader=FileSystemLoader(EXPORT / 'templates'), undefined=StrictUndefined)
        environment.filters['to_json'] = json.dumps
        rendered = environment.get_template('collector.yml.j2').render(
            **defaults, logging_export_scope={'endpoint': 'localhost:4317'})
        config = yaml.safe_load(rendered)
        self.assertTrue(config['extensions']['file_storage']['fsync'])
        self.assertFalse(config['receivers']['filelog']['delete_after_read'])
        self.assertNotIn('batch', config.get('processors', {}))
        native = os.environ.get('OTELCOL_BINARY')
        if native:
            path = Path(self.temp.name) / 'collector.yml'
            path.write_text(rendered)
            subprocess.run([native, 'validate', '--config', str(path)], check=True, capture_output=True)
        task = (EXPORT / 'tasks/scope.yml').read_text()
        self.assertIn(':/approved:ro,z', task)
        self.assertNotIn('security-logging:/', task)
        self.assertNotIn('privileged:', task)

    def test_generated_ownership(self):
        self.generate()
        tier = self.root / 'verify-tier-0'
        self.assertTrue((tier / 'ansible/roles/logging_export/tasks/main.yml').is_file())
        self.assertTrue((tier / 'ansible/roles/netbox_audit/files/netbox_audit.py').is_file())
        self.assertFalse((self.root / 'verify-tier-1/ansible/roles/netbox_audit').exists())
