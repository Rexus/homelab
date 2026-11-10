"""NAS client mount contracts and read-only native qualification; no live NAS."""

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

from tier_repo_test_support import UPSTREAM

ROLE = UPSTREAM / 'tier-1/ansible/roles/development_data'
ANSIBLE = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')


class DevelopmentDataMountContracts(unittest.TestCase):
    def test_service_requires_the_selected_host_mount_in_render_and_apply(self):
        template = Environment(undefined=StrictUndefined).from_string(
            (ROLE / 'templates/backup.service.j2').read_text())
        values = {'data_component': 'postgresql', 'development_data_backup_transport': 'filesystem',
                  'development_data_backup_timeout_seconds': 7200,
                  'development_data_backup_filesystem': {'db-1': {'mount': '/mnt/db-backup'}}}
        for host_vars in [{'inventory_hostname': 'localhost', 'data_backup_host': 'db-1'},
                          {'inventory_hostname': 'db-1'}]:
            with self.subTest(host_vars=host_vars):
                output = template.render(**values, **host_vars)
                self.assertIn('RequiresMountsFor=/mnt/db-backup\n', output)
        output = template.render(**dict(values, development_data_backup_transport='sftp'),
                                 inventory_hostname='db-1')
        self.assertNotIn('RequiresMountsFor=', output)

    def test_mounting_is_native_after_inspection_and_before_repository_probe(self):
        tasks = yaml.safe_load((ROLE / 'tasks/backup-mount.yml').read_text())
        inspection = next(n for n, task in enumerate(tasks) if task.get('ansible.builtin.include_tasks') == 'backup-mount-inspect.yml')
        identity = next(n for n, task in enumerate(tasks) if task.get('ansible.builtin.include_tasks') == 'backup-mount-identity.yml')
        mounts = [(n, task['ansible.posix.mount']) for n, task in enumerate(tasks) if 'ansible.posix.mount' in task]
        self.assertEqual([options['state'] for _, options in mounts], ['ephemeral', 'mounted'])
        self.assertLess(inspection, mounts[0][0])
        self.assertLess(mounts[0][0], identity)
        self.assertLess(identity, mounts[1][0])
        self.assertTrue(mounts[1][1]['boot'])
        credentials = next(task for task in tasks if 'ansible.builtin.copy' in task)
        self.assertTrue(credentials['no_log'])
        self.assertFalse(credentials['diff'])
        self.assertEqual(credentials['ansible.builtin.copy']['mode'], '0600')
        self.assertNotIn('password=', str(mounts))
        self.assertIn('seal', str(tasks))
        self.assertIn('hard', str(tasks))
        identity_tasks = yaml.safe_load((ROLE / 'tasks/backup-mount-identity.yml').read_text())
        self.assertFalse(any('ansible.builtin.file' in task or 'ansible.builtin.copy' in task
                             for task in identity_tasks), 'Client must not commission NAS identity or directories')


@unittest.skipUnless(os.name != 'nt' and ANSIBLE, 'Requires native Linux Ansible and findmnt')
class DevelopmentDataMountGuards(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='development-data-mount-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.mount = self.root / 'nas'
        self.repository = self.mount / 'db-1'
        self.fstab = self.root / 'fstab'
        self.fstab.write_text('# Private read-only fstab fixture\n')
        self.values = {
            'data_backup_filesystem': {'mount': str(self.mount), 'source': 'nas.example:/backup/db-1',
                                       'fstype': 'nfs4', 'marker': 'independent-target-marker-0123456789',
                                       'uid': os.getuid(), 'gid': os.getgid()},
            'data_backup_repository': str(self.repository), 'data_backup_manage_mount': True,
        }

    def run_tasks(self, tasks, values=None):
        play = self.root / 'play.json'
        play.write_text(json.dumps([{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                                    'vars': values or self.values, 'tasks': tasks}]))
        result = subprocess.run([ANSIBLE, '-i', 'localhost,', str(play)], cwd=self.root,
                                env=dict(os.environ, ANSIBLE_NOCOLOR='1', ANSIBLE_STDOUT_CALLBACK='default'),
                                capture_output=True, text=True, timeout=120)
        return result

    def inspect(self):
        tasks = yaml.safe_load((ROLE / 'tasks/backup-mount-inspect.yml').read_text())
        for task in tasks:
            if 'ansible.builtin.command' in task:
                argv = task['ansible.builtin.command']['argv']
                if '--fstab' in argv:
                    argv.extend(['--tab-file', str(self.fstab)])
            if 'ansible.builtin.slurp' in task:
                task['ansible.builtin.slurp']['src'] = str(self.fstab)
        return self.run_tasks(tasks)

    def test_native_inspection_accepts_empty_targets_and_matching_persistent_assignment(self):
        result = self.inspect()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.mount.mkdir()
        for content in ('# comments only\n', f'nas.example:/backup/db-1 {self.mount} nfs4 rw,hard 0 0\n'):
            with self.subTest(fstab=content):
                self.fstab.write_text(content)
                result = self.inspect()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse(self.repository.exists())

    def test_foreign_duplicate_malformed_and_unreadable_fstab_never_authorize_changes(self):
        self.mount.mkdir()
        matching = f'nas.example:/backup/db-1 {self.mount} nfs4 rw,hard 0 0\n'
        for content in (f'other.example:/foreign {self.mount} nfs4 defaults 0 0\n', matching * 2,
                        'malformed entry\n', matching + 'malformed entry\n'):
            with self.subTest(fstab=content):
                self.fstab.write_text(content)
                result = self.inspect()
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse(self.repository.exists())
        self.fstab.unlink()
        self.assertNotEqual(self.inspect().returncode, 0)

    def test_local_files_nondirectory_and_symlink_targets_fail_closed(self):
        self.mount.write_text('preserve local file')
        self.assertNotEqual(self.inspect().returncode, 0)
        self.mount.unlink()
        self.mount.mkdir()
        local = self.mount / '.hidden-local-backup'
        local.write_text('preserve hidden data')
        result = self.inspect()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Preserve local files', result.stdout)
        self.assertEqual(local.read_text(), 'preserve hidden data')
        local.unlink()
        self.mount.rmdir()
        self.mount.symlink_to(self.root, target_is_directory=True)
        self.assertNotEqual(self.inspect().returncode, 0)

    def test_foreign_persistent_target_alias_is_resolved_before_mounting(self):
        self.mount.mkdir()
        alias = self.root / 'target-alias'
        alias.symlink_to(self.mount, target_is_directory=True)
        for source in ['other.example:/foreign', self.values['data_backup_filesystem']['source']]:
            with self.subTest(source=source):
                self.fstab.write_text(f'{source} {alias} nfs4 rw,hard 0 0\n')
                result = self.inspect()
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('aliased storage', result.stdout)
                self.assertFalse(self.repository.exists())

    def test_skipped_directory_inspection_and_foreign_active_mount_fail_before_mutation(self):
        tasks = yaml.safe_load((ROLE / 'tasks/backup-mount-inspect.yml').read_text())
        guard = next(task for task in tasks if task['name'].startswith('Refuse unreadable targets'))
        values = dict(self.values, data_backup_existing_mount={'rc': 1},
                      data_backup_target_stat={'stat': {'isdir': True}},
                      data_backup_local_entries={'matched': 0, 'skipped_paths': {str(self.mount): 'denied'}})
        self.assertNotEqual(self.run_tasks([guard], values).returncode, 0)
        active = next(task for task in tasks if task['name'].startswith('Refuse a foreign mount'))
        values.update(data_backup_existing_mount={'rc': 0, 'stdout': f'{self.mount} other.example:/wrong nfs4'})
        self.assertNotEqual(self.run_tasks([active], values).returncode, 0)

    def test_independent_marker_and_repository_are_checked_but_never_created(self):
        self.mount.mkdir()
        tasks = yaml.safe_load((ROLE / 'tasks/backup-mount-identity.yml').read_text())[1:]
        marker = self.mount / '.development-data-backup-target'
        self.assertNotEqual(self.run_tasks(tasks).returncode, 0)
        self.assertFalse(marker.exists())
        marker.write_text('wrong-independent-marker\n')
        self.assertNotEqual(self.run_tasks(tasks).returncode, 0)
        self.assertEqual(marker.read_text(), 'wrong-independent-marker\n')
        marker.write_text(self.values['data_backup_filesystem']['marker'] + '\n')
        self.assertNotEqual(self.run_tasks(tasks).returncode, 0)
        self.assertFalse(self.repository.exists())
        self.repository.mkdir()
        result = self.run_tasks(tasks)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_safe_options_and_legacy_cifs_adoption(self):
        source = yaml.safe_load((ROLE / 'tasks/backup-mount.yml').read_text())
        selected = source[:2] + [next(task for task in source
                                     if task['name'].startswith('Compose safe NAS options'))]
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        contract = self.values['data_backup_filesystem']
        common = ['rw', 'noexec', 'nosuid', 'nodev']
        cases = [
            (contract, True, common + ['hard', 'vers=4.1', 'proto=tcp']),
            (dict(contract, fstype='cifs', source='//nas.example/backup', credentials_src='/private/smb'),
             True, common + ['seal', 'sec=ntlmssp', 'forceuid', 'forcegid', 'vers=3.1.1',
                            'credentials=/etc/development-data/backup-smb.credentials']),
            (dict(contract, fstype='cifs', source='//nas.example/backup'), False, []),
            (dict(contract, manage_mount=False), False, []),
        ]
        tasks = []
        for item, managed, flags in cases:
            tasks.append({
                'name': 'Exercise actual selection and option tasks without mounting',
                'vars': {'development_data_backup_filesystem': {'localhost': item},
                         'development_data_backup_repository': {'localhost': str(self.repository)}},
                'block': copy.deepcopy(selected) + [{
                    'ansible.builtin.assert': {'that': [
                        f'data_backup_manage_mount == {str(managed).lower()}',
                        f'{json.dumps(flags)} | difference(data_backup_mount_options.split(",")) | length == 0'
                        if managed else 'not data_backup_manage_mount',
                    ]},
                }],
            })
        result = self.run_tasks(tasks, defaults)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_option_guard_rejects_unsafe_and_inline_credential_overrides(self):
        tasks = yaml.safe_load((ROLE / 'tasks/backup-inputs.yml').read_text())
        guard = next(task for task in tasks if task['name'].startswith('Reject unsafe or secret-bearing'))
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        for option, fstype in [('soft', 'nfs4'), ('ro', 'nfs4'),
                               ('password=unsafe-inline', 'cifs'), ('credentials=/foreign', 'cifs')]:
            with self.subTest(option=option):
                contract = dict(self.values['data_backup_filesystem'], fstype=fstype, options=[option])
                values = dict(defaults, development_data_backup_transport='filesystem',
                              development_data_backup_filesystem={'localhost': contract})
                result = self.run_tasks([guard], values)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('supported protocol/performance', result.stdout)


if __name__ == '__main__':
    unittest.main()
