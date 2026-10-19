"""Create-only NAS checkpoints, offline integrity, projection and backup boundaries."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM

ROLE = UPSTREAM / 'tier-0/ansible/roles/logging_archive'


@unittest.skipIf(os.name == 'nt', 'Native Linux filesystem and flock semantics')
class ArchiveCheckpoints(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='logging-archive-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        sys.path.insert(0, str(ROLE / 'files'))
        self.addCleanup(sys.path.remove, str(ROLE / 'files'))
        spec = importlib.util.spec_from_file_location('logging_checkpoint', ROLE / 'files/logging_checkpoint.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.data = self.root / 'data'
        (self.data / 'records/producer').mkdir(parents=True)
        self.record = self.data / 'records/producer/2026-10-19.jsonl'
        self.catalogue = self.data / 'source-catalogue.json'
        self.catalogue.write_text(json.dumps({'tls_sources': [dict(name='producer', tier=0)],
                                             'legacy_udp_sources': []}))
        self.config = dict(mount=str(self.root / 'nas'), marker='commissioned-archive', collector='receiver',
                           data=str(self.data), state=str(self.root / 'state/checkpoint.json'), max_bytes=65536)

    def row(self, number, **fields):
        return (json.dumps(dict(source='producer', source_tier=0, raw=f'event-{number}', **fields)) + '\n').encode()

    def run_checkpoint(self):
        return self.module.checkpoint(self.config, check_mount=False)

    def test_partial_tail_retry_and_offline_restore(self):
        self.record.write_bytes(self.row(1) + b'{"partial":')
        first = self.run_checkpoint()
        self.assertEqual(first['chunks'], 1)
        self.record.write_bytes(self.row(1) + self.row(2))
        self.assertEqual(self.run_checkpoint()['chunks'], 1)
        self.assertEqual(self.run_checkpoint()['chunks'], 0)
        restored = self.root / 'restored'
        shutil.copytree(self.root / 'nas', restored)
        shutil.rmtree(self.data)
        self.assertEqual(self.module.verify(restored)['referenced_records'], 2)
        chunks = list(restored.glob('*/chunks/*/*.jsonl'))
        chunks[0].write_text('tampered\n')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            self.module.verify(restored)

    def test_collision_rewrite_symlink_and_missing_mount_fail_closed(self):
        self.record.write_bytes(self.row(1))
        with self.assertRaisesRegex(ValueError, 'mount missing'):
            self.module.checkpoint(self.config)
        self.run_checkpoint()
        self.record.write_bytes(self.row(2))
        with self.assertRaisesRegex(ValueError, 'rewritten'):
            self.run_checkpoint()
        self.record.unlink()
        self.record.symlink_to(self.catalogue)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.run_checkpoint()

    def test_completed_chunk_retry_after_cursor_loss_and_collision_protection(self):
        self.record.write_bytes(self.row(1))
        self.run_checkpoint()
        Path(self.config['state']).unlink()
        self.run_checkpoint()
        self.assertEqual(len(list((self.root / 'nas').glob('*/chunks/*/*.jsonl'))), 1)
        chunk = next((self.root / 'nas').glob('*/chunks/*/*.jsonl'))
        chunk.write_bytes(b'partial crash write')
        Path(self.config['state']).unlink()
        with self.assertRaisesRegex(ValueError, 'collision'):
            self.run_checkpoint()

    def test_application_projection_uses_catalogue_not_producer_labels(self):
        import grp
        self.record.write_bytes(self.row(1, kind='application', owner='developer'))
        self.config.update(views={'producer': grp.getgrgid(os.getgid()).gr_name},
                           view_root=str(self.root / 'views'))
        with self.assertRaisesRegex(ValueError, 'catalogue-approved'):
            self.run_checkpoint()
        self.catalogue.write_text(json.dumps({'tls_sources': [dict(name='producer', tier=0, kind='application')],
                                             'legacy_udp_sources': []}))
        self.run_checkpoint()
        projected = next((self.root / 'views/producer').glob('*.jsonl'))
        self.assertEqual(projected.read_bytes(), self.row(1, kind='application', owner='developer'))
        self.assertEqual(projected.stat().st_mode & 0o777, 0o640)

    def test_missing_source_and_low_capacity_fail_health_after_preserving_checkpoint(self):
        self.record.write_bytes(self.row(1))
        self.config['required_sources'] = ['missing']
        with self.assertRaisesRegex(ValueError, 'not catalogued'):
            self.run_checkpoint()
        self.assertTrue(Path(self.config['state']).exists())
        self.assertEqual(self.module.verify(self.root / 'nas')['referenced_records'], 1)
        self.config.update(required_sources=[], min_free_bytes=2 ** 70)
        with self.assertRaisesRegex(ValueError, 'headroom'):
            self.run_checkpoint()

    def test_independent_native_encrypted_backup_and_clean_restore(self):
        restic = os.environ.get('RESTIC_TEST_BINARY') or shutil.which('restic')
        if not restic:
            self.skipTest('Set RESTIC_TEST_BINARY for native encrypted backup/restore')
        self.record.write_bytes(self.row(1))
        self.run_checkpoint()
        files = self.root / 'verified-files'
        self.module.verify(self.root / 'nas', files)
        password = self.root / 'password'
        password.write_text('isolated-test-not-a-deployment-secret')
        env = dict(os.environ, RESTIC_REPOSITORY=str(self.root / 'repo'), RESTIC_PASSWORD_FILE=str(password))
        for args in (['init'], ['backup', '--files-from-verbatim', str(files)], ['check', '--read-data'],
                     ['restore', 'latest', '--target', str(self.root / 'recovery')]):
            subprocess.run([restic, *args], env=env, check=True, capture_output=True, timeout=60)
        restored = self.root / 'recovery' / (self.root / 'nas').relative_to('/')
        shutil.rmtree(self.root / 'nas')
        shutil.rmtree(self.data)
        self.assertEqual(self.module.verify(restored)['referenced_records'], 1)


class GeneratedLoggingPayload(TierRepositoryTestCase):
    @unittest.skipUnless(shutil.which('bash'), 'Requires Bash for native shell syntax validation')
    def test_native_job_scripts_parse_and_keep_health_capabilities_out_of_arguments(self):
        from jinja2 import Environment, StrictUndefined

        environment = Environment(undefined=StrictUndefined)
        cases = [
            (UPSTREAM / 'shared/ansible/roles/log_forwarder/templates/health.sh.j2',
             dict(log_forwarder_streams=[dict(name='producer')],
                  log_forwarder_state='/var/lib/rsyslog/forwarder', log_forwarder_config='/etc/log-forwarder',
                  log_forwarder_queue_bytes=16777216, log_forwarder_min_free_bytes=16777216)),
            (UPSTREAM / 'tier-0/ansible/roles/logging_backup/templates/backup.sh.j2',
             dict(logging_backup_repository='/mnt/recovery', logging_backup_mount='/mnt/security-logs',
                  logging_backup_marker='commissioned-archive')),
        ]
        self.parent.mkdir(parents=True)
        for index, (path, values) in enumerate(cases):
            content = environment.from_string(path.read_text()).render(**values)
            script = self.parent / f'job-{index}.sh'
            script.write_text(content)
            result = subprocess.run(['bash', '-n', str(script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--config ', content)
            self.assertNotIn('https://', content)

    def test_executable_mechanisms_follow_ownership_without_seeding_live_inputs(self):
        self.generate()
        for name in ('logging_checkpoint.py', 'logging_io.py', 'logging_health.py'):
            self.assertEqual((ROLE / 'files' / name).read_bytes(),
                             (self.root / 'verify-tier-0/ansible/roles/logging_archive/files' / name).read_bytes())
        for tier in (0, 1, 2):
            root = self.root / f'verify-tier-{tier}'
            self.assertTrue((root / 'ansible/playbooks/deployment/logging-producers.yml').is_file())
            self.assertFalse((root / 'ansible/group_vars/logging_producers.yml').exists())
            if tier:
                self.assertFalse((root / 'ansible/roles/logging_authority').exists())
        self.assertTrue((self.root / 'verify-shared/ansible/roles/log_forwarder/tasks/main.yml').is_file())
        self.assertFalse((self.root / 'verify-shared/ansible/inventory').exists())
