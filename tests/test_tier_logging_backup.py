"""Independent logging repository routes and native mount-identity guards."""

from copy import deepcopy
import json
import os
import shutil
import subprocess
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / 'tier-0/ansible/roles/logging_backup'
UUID = '7cc21ca8-7106-46e4-95af-c63f8ac3c216'
OTHER_UUID = 'be2e92f2-aab5-440f-9f78-87060de91916'


class BackupRepository(TierRepositoryTestCase):
    def test_generated_new_disk_and_adopted_mount_routes_keep_tier_ownership(self):
        self.generate()
        for owner in [UPSTREAM / 'tier-0', self.root / 'verify-tier-0']:
            root = owner / 'ansible/roles/logging_backup'
            defaults = yaml.safe_load((root / 'defaults/main.yml').read_text())
            self.assertEqual(defaults['logging_backup_repository_device'], '')
            starter = yaml.safe_load((owner / 'ansible/group_vars/logging_backup.yml.example').read_text())
            self.assertEqual(starter['logging_backup_repository_device'], '/dev/sdb')
            self.assertEqual(starter['logging_backup_repository'], '/srv/security-log-backup')
            tasks = yaml.safe_load((root / 'tasks/main.yml').read_text())
            preparation = next(i for i, task in enumerate(tasks)
                               if task.get('ansible.builtin.import_tasks') == 'repository.yml')
            initialization = next(i for i, task in enumerate(tasks)
                                  if task.get('ansible.builtin.command', {}).get('creates'))
            self.assertLess(preparation, initialization)
            self.assertEqual(tasks[initialization]['when'], 'logging_backup_initialize | bool')
            self.assertIn('not in groups.get(\'foundation_logging\', [])', str(tasks[0]))
            archive_mount = next(task['ansible.posix.mount'] for task in tasks
                                 if 'ansible.posix.mount' in task)
            self.assertTrue(archive_mount['opts'].startswith('ro,'))
            self.assertIn('seal', archive_mount['opts'])
            self.assertIn('--source {{ logging_backup_repository_guard_source | quote }}',
                          (root / 'templates/backup.sh.j2').read_text())

    @unittest.skipUnless(os.name != 'nt' and shutil.which('ansible-playbook'), 'Requires native Ansible')
    def test_actual_repository_guards_and_shared_uuid_handoff_without_mount_changes(self):
        work = self.parent / 'repository-checks'
        stub = work / 'roles/data_volume/tasks'
        stub.mkdir(parents=True)
        shared = yaml.safe_load((UPSTREAM / 'shared/ansible/roles/data_volume/tasks/prepare.yml').read_text())
        uuid_guard = next(task for task in shared
                          if task['name'] == 'Require the expected UUID before changing mount configuration')
        (stub / 'main.yml').write_text(yaml.safe_dump([
            {'ansible.builtin.assert': {'that': [
                "data_volume_device == '/dev/sdb'", 'data_volume_path == logging_backup_repository',
                "data_volume_label == 'log-backup'", "data_volume_fstype == 'xfs'",
                'data_volume_expected_uuid == logging_backup_repository_uuid',
                'data_volume_min_free_bytes | int == 1073741824',
                'data_volume_environment == logging_backup_environment',
                'data_volume_allowed_bind_mounts == []',
            ]}},
            {'ansible.builtin.set_fact': {'volume_called': True, 'data_volume_uuid_probe': {'stdout': UUID}}},
            uuid_guard,
        ], sort_keys=False))
        # Real adapter/assertions; only discovery and device operations are replaced by supplied facts.
        tasks = [task for task in yaml.safe_load((ROLE / 'tasks/repository.yml').read_text())
                 if 'ansible.builtin.command' not in task]
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        base = dict(defaults, logging_backup_repository='/srv/security-log-backup',
                    logging_backup_mount='/mnt/security-log-recovery-source',
                    logging_backup_repository_device='/dev/sdb')
        repository = dict(target=base['logging_backup_repository'], source='/dev/sdb', fstype='xfs',
                          uuid=UUID, options='rw,nodev,nosuid,noexec', avail=2**31, **{'maj:min': '8:16'})
        archive = dict(target=base['logging_backup_mount'], source='//archive.example.test/logs',
                       fstype='cifs', uuid=None, options='ro', avail=2**31, **{'maj:min': '0:55'})
        root = dict(target='/', source='/dev/sda1', fstype='xfs', uuid=OTHER_UUID,
                    options='rw', avail=2**31, **{'maj:min': '8:1'})
        cases = [('new disk', {}, {}, {}, False),
                 ('pinned disk', {'logging_backup_repository_uuid': UUID}, {}, {}, False),
                 ('wrong local pin', {'logging_backup_repository_uuid': OTHER_UUID}, {}, {}, True),
                 ('adopt local', {'logging_backup_repository_device': '',
                                  'logging_backup_repository_uuid': UUID}, {}, {}, False),
                 ('adopt remote', {'logging_backup_repository_device': ''},
                  {'source': '//recovery.example.test/backups', 'fstype': 'cifs', 'uuid': None,
                   'maj:min': '0:66'}, {}, False),
                 ('wrong adopted pin', {'logging_backup_repository_device': '',
                                        'logging_backup_repository_uuid': OTHER_UUID}, {}, {}, True),
                 ('root filesystem', {}, {'maj:min': '8:1'}, {}, True),
                 ('archive filesystem', {}, {'maj:min': '0:55'}, {}, True),
                 ('archive source', {}, {'source': archive['source']}, {}, True),
                 ('read-only repository', {}, {'options': 'ro'}, {}, True),
                 ('writable archive input', {}, {}, {'options': 'rw'}, True),
                 ('low reserve', {}, {'avail': 0}, {}, True),
                 ('volatile repository', {}, {'fstype': 'tmpfs'}, {}, True),
                 ('wrong mount target', {}, {'target': '/different'}, {}, True),
                 ('missing mount', {}, {}, {}, True)]
        plays = []
        for name, changes, repo_changes, source_changes, rejected in cases:
            values = dict(base, **changes)
            mounts = [dict(repository, **repo_changes), dict(archive, **source_changes), root]
            values['logging_backup_mount_inspection'] = {'results': [
                {'stdout': json.dumps({'filesystems': [] if name == 'missing mount' and index == 0 else [mount]}),
                 'item': mount['target']} for index, mount in enumerate(mounts)]}
            checks = [
                {'ansible.builtin.set_fact': {'repository_rejected': False, 'volume_called': False,
                                              'logging_backup_repository_guard_source': None}},
                {'block': deepcopy(tasks), 'rescue': [
                    {'ansible.builtin.set_fact': {'repository_rejected': True}}]},
                {'ansible.builtin.assert': {'that': [
                    'repository_rejected == expected_rejection',
                    'volume_called == (logging_backup_repository_device | length > 0)',
                ]}},
            ]
            if rejected:
                checks.append({'ansible.builtin.assert': {'that':
                    'logging_backup_repository_guard_source == None'}})
            else:
                values['expected_source'] = ('UUID=' + mounts[0]['uuid']
                                             if mounts[0]['uuid'] else mounts[0]['source'])
                checks.append({'ansible.builtin.assert': {'that': [
                    'logging_backup_repository_guard_source == expected_source',
                    'logging_backup_repository_guard_fstype == logging_backup_repository_facts.fstype',
                ]}})
            values['expected_rejection'] = rejected
            plays.append(dict(name=name, hosts='localhost', connection='local', gather_facts=False,
                              vars=values, tasks=checks))
        playbook = work / 'check.yml'
        playbook.write_text(yaml.safe_dump(plays, sort_keys=False))
        result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)], cwd=work,
                                capture_output=True, text=True, timeout=120,
                                env=dict(os.environ, ANSIBLE_ROLES_PATH=str(work / 'roles')))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(os.name != 'nt' and shutil.which('findmnt'), 'Requires native util-linux')
    def test_native_findmnt_requires_both_target_and_selected_source_type(self):
        self.parent.mkdir(parents=True)
        table = self.parent / 'mounts.fixture'
        table.write_text('UUID=' + UUID + ' /srv/security-log-backup xfs rw 0 0\n')
        for source, fstype, mount, accepted in (
            ('UUID=' + UUID, 'xfs', '/srv/security-log-backup', True),
            ('UUID=' + OTHER_UUID, 'xfs', '/srv/security-log-backup', False),
            ('UUID=' + UUID, 'ext4', '/srv/security-log-backup', False),
            ('UUID=' + UUID, 'xfs', '/srv/missing', False),
        ):
            result = subprocess.run(['findmnt', '--tab-file', str(table), '--noheadings', '--output', 'TARGET',
                                     '--mountpoint', mount, '--source', source, '--types', fstype],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
