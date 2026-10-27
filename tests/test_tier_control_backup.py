"""Independent control recovery boundaries and real encrypted file restoration."""

import importlib
from contextlib import nullcontext
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / 'tier-0/ansible/roles/control_backup'
sys.path.insert(0, str(ROLE / 'files'))
backup = importlib.import_module('control_backup')
io = importlib.import_module('control_backup_io')
vault = importlib.import_module('vault_snapshot')
restore = importlib.import_module('restore_files')
RESTIC = os.environ.get('CONTROL_BACKUP_RESTIC') or shutil.which('restic')


class RecoveryBoundaries(unittest.TestCase):
    def setUp(self):
        previous_umask = os.umask(0o077)
        self.addCleanup(os.umask, previous_umask)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repo = self.root / 'inputs'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '--quiet', str(self.repo)], check=True)
        (self.repo / '.gitignore').write_text('local/\ntracked.yml\n')
        (self.repo / 'local').mkdir()
        (self.repo / 'local/state').write_bytes(b'original sensitive state')
        self.selection = [{'repo': str(self.repo), 'path': 'local'}]

    def test_inputs_are_existing_ignored_bounded_and_untracked(self):
        self.assertEqual(io.selected_inputs(self.selection), [self.repo / 'local'])
        with self.assertRaisesRegex(ValueError, 'transport mounts'):
            io.selected_inputs(self.selection, [self.root / 'other-custodian'])
        for relative in ['.', '../escape', 'missing', '.gitignore']:
            with self.subTest(relative=relative), self.assertRaises((ValueError, RuntimeError)):
                io.selected_inputs([{'repo': str(self.repo), 'path': relative}])
        (self.repo / 'tracked.yml').write_text('tracked')
        subprocess.run(['git', '-C', str(self.repo), 'add', '-f', 'tracked.yml'], check=True)
        with self.assertRaises(ValueError):
            io.selected_inputs([{'repo': str(self.repo), 'path': 'tracked.yml'}])

    def test_token_rejects_root_broad_inherited_periodic_and_unbounded(self):
        good = dict(policies=['control-raft-snapshot'], ttl=900, explicit_max_ttl=900, type='service')
        vault.validate_token(good, 'control-raft-snapshot')
        for change in [dict(policies=['root']), dict(policies=['control-raft-snapshot', 'default']),
                       dict(identity_policies=['extra']), dict(ttl=0), dict(ttl=7200),
                       dict(explicit_max_ttl=0), dict(period=900), dict(type='batch')]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                vault.validate_token({**good, **change}, 'control-raft-snapshot')
        with self.assertRaisesRegex(ValueError, 'CIDRs'):
            vault.validate_token(good, 'control-raft-snapshot', ['192.0.2.10/32'])

    def test_native_snapshot_inspect_failure_and_short_lived_auth(self):
        config = dict(binary='vault', address='https://vault.example.com', ca_file='/ca.pem',
                      server_name='vault.example.com', auth='approle', mount='approle',
                      role_id='/role-id', secret_id='/secret-id', policy='control-raft-snapshot',
                      client_cert='/client.pem', client_key='/client.key', cert_mount='control-backup-cert',
                      cert_role='control-raft-snapshot', cert_min_seconds=604800,
                      bound_cidrs=['192.0.2.10/32'])
        for field in ['role_id', 'secret_id']:
            path = self.root / field
            path.write_text('test-secret\n')
            config[field] = str(path)
        calls = []

        def native(argv, env, input_data=None):
            calls.append(argv)
            self.assertNotIn('VAULT_SKIP_VERIFY', env)
            if config['auth'] == 'cert':
                self.assertEqual(env['VAULT_CLIENT_CERT'], '/client.pem')
                self.assertEqual(env['VAULT_CLIENT_KEY'], '/client.key')
            if argv[0] == 'openssl':
                return b''
            if 'write' in argv:
                if config['auth'] == 'approle':
                    self.assertEqual(json.loads(input_data)['secret_id'], 'test-secret')
                else:
                    self.assertEqual(argv[-1], 'name=control-raft-snapshot')
                return json.dumps({'auth': {'client_token': 'test-secret'}}).encode()
            self.assertEqual(env['VAULT_TOKEN'], 'test-secret')
            if 'lookup' in argv:
                return json.dumps({'data': dict(policies=['control-raft-snapshot'], ttl=900,
                                                explicit_max_ttl=900, type='service',
                                                bound_cidrs=['192.0.2.10/32'])}).encode()
            if 'save' in argv:
                Path(argv[-1]).write_bytes(b'mocked native Raft snapshot')
            if 'inspect' in argv:
                raise RuntimeError('invalid snapshot')
            return b''

        with patch.dict(os.environ, {'VAULT_SKIP_VERIFY': 'true', 'VAULT_TOKEN': 'root'}):
            for method in ['approle', 'cert']:
                config['auth'] = method
                with patch.object(vault, 'run', side_effect=native), self.assertRaises(RuntimeError):
                    vault.save(config, self.root / 'raft.snap')
        self.assertEqual(calls[-1], ['vault', 'token', 'revoke', '-self'])
        self.assertNotIn('test-secret', repr(calls))

    def test_media_requires_exact_readonly_mount_and_repository_identity(self):
        result = {'filesystems': [{'target': str(self.root), 'options': 'rw,nosuid'}]}
        with patch.object(io, 'run', return_value=json.dumps(result).encode()):
            with self.assertRaisesRegex(ValueError, 'read-only'):
                io.require_mount(self.root, readonly=True)
        with patch.object(io, 'require_mount'), patch.object(io, 'run', return_value=b'{"id":"other"}'):
            with self.assertRaisesRegex(ValueError, 'identity'):
                io.require_repository({'repository': str(self.root), 'repository_id': 'expected'}, {})
        (self.root / '.control-backup-source').write_text('source-owner-marker')
        source = {'mount': str(self.root), 'marker': 'source-owner-marker'}
        with patch.object(io, 'require_mount', return_value=self.root) as mount:
            self.assertEqual(io.require_input_sources([source]), [self.root])
            mount.assert_called_with(str(self.root), readonly=True)
            with self.assertRaisesRegex(ValueError, 'source marker'):
                io.require_input_sources([{**source, 'marker': 'wrong'}])

    def test_restore_never_reuses_existing_target_or_latest(self):
        with patch.object(restore, 'run') as native:
            with self.assertRaises(FileExistsError):
                restore.restore('a' * 64, self.root)
            with self.assertRaises(ValueError):
                restore.restore('latest', self.root / 'new')
            native.assert_not_called()

    @unittest.skipUnless(os.name == 'posix', 'production manual CLI locking uses Linux flock')
    def test_manual_cli_lock_rejects_overlap_without_mutating_health(self):
        config = self.root / 'lock-config.json'
        config.write_text(json.dumps({'directory': str(self.root)}))
        with io.job_lock(self.root):
            result = subprocess.run([sys.executable, str(ROLE / 'files/control_backup.py'), str(config)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('concurrent invocation rejected', result.stderr)
        self.assertFalse((self.root / 'health.json').exists())


@unittest.skipUnless(RESTIC, 'install restic or set CONTROL_BACKUP_RESTIC for the native round trip')
class NativeEncryptedRecovery(unittest.TestCase):
    def setUp(self):
        previous_umask = os.umask(0o077)
        self.addCleanup(os.umask, previous_umask)

    setUp = RecoveryBoundaries.setUp

    def native(self, argv, env=None, timeout=3600):
        if argv[0] == 'restic':
            argv = [RESTIC, *argv[1:]]
        return io.run(argv, env, timeout)

    def test_backup_restore_hashes_and_no_success_after_partial_failure(self):
        staging = self.root / 'staging'
        staging.mkdir()
        repository = self.root / 'repository'
        password = self.root / 'password'
        password.write_text('independent-test-only-encryption-password')
        config = dict(directory=str(staging), repository=str(repository), password_file=str(password),
                      inputs=self.selection, media={'enabled': False}, vault={}, health_config='unused',
                      input_sources=[{'source': '//test/inputs', 'mount': str(self.repo)}])
        env = io.restic_environment(config)
        self.native(['restic', 'init'], env)
        config['repository_id'] = json.loads(self.native(['restic', 'cat', 'config'], env))['id']

        def snapshot(_config, target):
            target.write_bytes(b'Raft product CLI mock; restic encryption and restore are real')

        def job_native(argv, env=None, timeout=3600):
            return b'' if argv[0] == 'curl' else self.native(argv, env, timeout)

        with patch.object(backup, 'require_repository'), patch.object(backup, 'save', side_effect=snapshot), \
                patch.object(backup, 'require_input_sources', return_value=[self.repo]):
            with patch.object(backup, 'run', side_effect=job_native):
                receipt = backup.backup(config)
                restored = self.root / 'restored'
                with patch.dict(os.environ, env, clear=True), patch.object(restore, 'run', side_effect=self.native):
                    # Scoped native extraction avoids restoring Windows system-parent ACLs.
                    source = str(staging / receipt['set']).replace('\\', '/').replace(':', '')
                    source = '/' + source if os.name == 'nt' else source
                    restore.restore(receipt['restic_snapshot'], restored, source)
                    input_target = self.root / 'restored-inputs'
                    source = str(self.repo / 'local').replace('\\', '/').replace(':', '')
                    source = '/' + source if os.name == 'nt' else source
                    restore.restore(receipt['restic_snapshot'], input_target, source)
                manifests = list(restored.rglob('manifest.json'))
                self.assertEqual(len(manifests), 1)
                manifest = json.loads(manifests[0].read_text())
                self.assertEqual(io.digest(manifests[0].parent / 'vault.snap'), manifest['vault_sha256'])
                self.assertEqual((input_target / 'state').read_bytes(), b'original sensitive state')
                with patch.object(backup, 'save', side_effect=RuntimeError('snapshot transport failure')):
                    with self.assertRaises(RuntimeError):
                        backup.backup(config)
                self.assertEqual(json.loads((staging / 'last-success.json').read_text()), receipt)
                with patch.object(backup, 'run', side_effect=RuntimeError('restic partial exit 3')):
                    with self.assertRaises(RuntimeError):
                        backup.backup(config)
                self.assertEqual(json.loads((staging / 'last-success.json').read_text()), receipt)
                settings = self.root / 'config.json'
                settings.write_text(json.dumps(config))
                with patch.object(sys, 'argv', ['control_backup.py', str(settings)]):
                    with patch.object(backup, 'backup', side_effect=RuntimeError('failed transport')), \
                            patch.object(backup, 'job_lock', return_value=nullcontext()):
                        self.assertEqual(backup.main(), 1)
                self.assertFalse(json.loads((staging / 'health.json').read_text())['ok'])
                self.assertEqual(json.loads((staging / 'last-success.json').read_text()), receipt)


class AutomationContract(unittest.TestCase):
    def test_native_schedule_and_no_repository_lifecycle_mutations(self):
        plays = yaml.safe_load((ROOT / 'tier-0/ansible/playbooks/maintenance/control-backup.yml').read_text())
        play = next(play for play in plays if play.get('hosts') == 'control_recovery')
        self.assertEqual(play['hosts'], 'control_recovery')
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        self.assertTrue(any('ansible.posix.mount' in task for task in tasks))
        self.assertTrue(any('ansible.builtin.systemd_service' in task for task in tasks))
        runtime = (ROLE / 'files/control_backup.py').read_text()
        for forbidden in ["'init'", "'forget'", "'prune'", "'restore'", 'pg_dump']:
            self.assertNotIn(forbidden, runtime)
        self.assertIn('ProtectSystem=strict', (ROLE / 'templates/service.j2').read_text())


if __name__ == '__main__':
    unittest.main()
