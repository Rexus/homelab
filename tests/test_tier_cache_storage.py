"""Cache storage guards with native Ansible and synthetic block/module boundaries.

Only disposable fixture files are written; no block probes, services, filesystem
tools or mounts execute. Assertions, facts, includes and conditions stay native.
"""

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import yaml

import test_tier_data_volume as volume_tests
from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


CACHE = Path('ansible/roles/cache_proxy')
PROBE = '''from ansible.module_utils.basic import AnsibleModule
import json

module = AnsibleModule(argument_spec=dict(
    operation=dict(required=True), arguments=dict(type='dict', required=True),
    fixture=dict(type='dict', required=True), log=dict(type='path', required=True)))
op, args, fixture = (module.params[key] for key in ('operation', 'arguments', 'fixture'))
with open(module.params['log'], 'a') as stream:
    stream.write(json.dumps(dict(operation=op, arguments=args)) + '\\n')
result = dict(changed=False)
if op == 'stat':
    result['stat'] = (dict(exists=True, isblk=True) if args['path'].startswith('/dev/')
                      else fixture['target'])
elif op == 'find':
    result.update(fixture['entries'])
elif op == 'slurp':
    result['content'] = ''
elif op == 'command':
    argv = args['argv']
    result.update(rc=0, stderr='')
    if argv[0] == 'realpath':
        result['stdout'] = fixture['block']['name'] if argv[-1] == fixture['selected'] else argv[-1]
    elif argv[0] == 'lsblk':
        result['stdout'] = json.dumps(dict(blockdevices=[fixture['block']]))
    elif argv[0] == 'wipefs':
        result['stdout'] = json.dumps(dict(signatures=fixture['signatures']))
    elif argv[0] == 'blkid':
        result['stdout'] = fixture['uuid']
    elif argv[0] == 'findmnt':
        table = (fixture['fstab'] if '--fstab' in argv else
                 [fixture['verified']] if '--mountpoint' in argv else fixture['mounts'])
        result['stdout'] = json.dumps(dict(filesystems=table))
    else:
        module.fail_json(msg='Unexpected probe command: ' + str(argv))
elif op not in ('package', 'wait_for', 'service', 'file', 'filesystem', 'mount'):
    module.fail_json(msg='Unexpected storage boundary: ' + op)
module.exit_json(**result)
'''


class CacheStorageSource(TierRepositoryTestCase):
    def test_generated_storage_and_defaults_keep_the_guarded_shared_contract(self):
        self.generate()
        for relative in ('tasks/storage.yml', 'defaults/main.yml'):
            self.assertEqual((UPSTREAM / 'tier-2' / CACHE / relative).read_bytes(),
                             (self.root / 'verify-tier-2' / CACHE / relative).read_bytes())
        tasks = yaml.safe_load((UPSTREAM / 'tier-2' / CACHE / 'tasks/storage.yml').read_text())
        block = tasks[0]
        self.assertEqual(block['when'], 'cache_squid_data_disk_enabled | bool')
        stages = [task['ansible.builtin.include_role']['tasks_from'] for task in block['block']
                  if task.get('ansible.builtin.include_role', {}).get('name') == 'data_volume']
        self.assertEqual(stages, ['inspect', 'validate', 'prepare'])
        self.assertEqual(block['vars']['data_volume_label'], 'cache-data')
        defaults = yaml.safe_load((UPSTREAM / 'tier-2' / CACHE / 'defaults/main.yml').read_text())
        self.assertEqual(defaults['cache_squid_data_uuid'], '')
        self.assertEqual(defaults['cache_squid_data_min_free_bytes'], 0)
        self.assertTrue({'nodev', 'nosuid', 'noexec'} <= set(defaults['cache_squid_data_mount_opts'].split(',')))


@unittest.skipUnless(os.name != 'nt' and volume_tests.ANSIBLE, 'Requires native Ansible')
class NativeCacheStorage(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.generate()

    def fixture(self, existing=False, mounted=False):
        # Reuse the shared guard fixture, with this incident's sda data/sdb OS layout.
        values = volume_tests.DataVolumeGuards.inputs(self, existing)
        block = values['data_volume_block']
        block.update(name='/dev/sda', size=250 * 1024**3, **{'maj:min': '8:0'})
        if existing:
            block['label'] = None  # Legacy cache filesystems need not have a label.
        uuid = '12345678-1234-1234-1234-123456789abc'
        mounts = [dict(target='/', source='/dev/mapper/os-root', uuid='os-root-uuid',
                       fsroot='/', **{'maj:min': '253:0'}),
                  dict(target='/boot', source='/dev/sdb2', fsroot='/', **{'maj:min': '8:18'}),
                  dict(target='/boot/efi', source='/dev/sdb1', fsroot='/', **{'maj:min': '8:17'})]
        return dict(block=block, selected='/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1', uuid=uuid,
                    signatures=values['data_volume_signatures'], mounts=mounts, fstab=[],
                    target=dict(exists=True, isdir=True, islnk=False),
                    entries=dict(matched=1 if mounted else 0, skipped_paths={}), mounted=mounted)

    def run_storage(self, owner, fixture, **overrides):
        work = Path(self.temp.name) / 'probe'
        work.mkdir(exist_ok=True)
        target = work / 'cache'
        target.mkdir(exist_ok=True)
        marker = target / 'retained-cache'
        marker.write_text('existing cache')
        fixture = copy.deepcopy(fixture)
        if fixture.pop('mounted'):
            fixture['mounts'].append(dict(target='/var/spool/squid', source=fixture['block']['name'],
                                          uuid=fixture['uuid'], fsroot='/',
                                          **{'maj:min': fixture['block']['maj:min']}))
        fixture['verified'] = dict(target='/var/spool/squid', uuid=fixture['uuid'], fstype='xfs',
                                   options='rw,noatime,nodev,nosuid,noexec', avail=0, fsroot='/',
                                   **{'maj:min': fixture['block']['maj:min']})
        log = work / 'calls.jsonl'
        log.write_text('')
        module = work / 'library/cache_storage_probe.py'
        module.parent.mkdir(exist_ok=True)
        module.write_text(PROBE)
        roles = work / 'roles'
        shared = owner.parent / ('verify-shared' if owner.name.startswith('verify-') else 'shared')
        sources = [owner / CACHE / 'tasks/storage.yml',
                   *sorted((shared / 'ansible/roles/data_volume/tasks').glob('*.yml')),
                   shared / 'ansible/roles/shared/tasks/packages.yml']
        boundaries = {'package', 'wait_for', 'stat', 'command', 'slurp', 'find',
                      'service', 'file', 'filesystem', 'mount'}

        def probe_tasks(tasks):
            for task in tasks:
                if 'block' in task:
                    probe_tasks(task['block'])
                    continue
                action = next(key for key in task if key.startswith(('ansible.', 'community.')))
                operation = action.rsplit('.', 1)[1]
                if operation in boundaries:
                    task['cache_storage_probe'] = dict(operation=operation, arguments=task.pop(action),
                                                       fixture='{{ cache_storage_fixture }}', log=str(log))
                else:
                    self.assertIn(action, ('ansible.builtin.assert', 'ansible.builtin.set_fact',
                                           'ansible.builtin.include_role', 'ansible.builtin.import_tasks'))

        for source in sources:
            destination = roles / source.relative_to(source.parents[2])
            destination.parent.mkdir(parents=True, exist_ok=True)
            tasks = yaml.safe_load(source.read_text())
            probe_tasks(tasks)
            destination.write_text(yaml.safe_dump(tasks, sort_keys=False))
        defaults = roles / 'data_volume/defaults/main.yml'
        defaults.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(shared / 'ansible/roles/data_volume/defaults/main.yml', defaults)
        inputs = yaml.safe_load((owner / CACHE / 'defaults/main.yml').read_text())
        inputs.update(ansible_system='Linux', ansible_os_family='Debian',
                      cache_squid_data_disk_enabled=True, cache_squid_cache_dir='/var/spool/squid',
                      cache_squid_data_device=fixture['selected'], cache_storage_fixture=fixture,
                      cache_squid_data_device_wait_timeout=7, cache_squid_data_mount_opts='defaults,noatime')
        inputs.update(overrides)
        play = work / 'play.yml'
        play.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                                             vars=inputs, tasks=[{'ansible.builtin.include_role': dict(
                                                 name='cache_proxy', tasks_from='storage')}])], sort_keys=False))
        result = subprocess.run([volume_tests.ANSIBLE, '-i', 'localhost,', str(play)],
                                cwd=work, env=dict(os.environ, ANSIBLE_NOCOLOR='1'),
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(marker.read_text(), 'existing cache')
        return result, [json.loads(line) for line in log.read_text().splitlines()]

    def test_os_disk_children_and_current_root_fail_before_stop_or_prepare(self):
        fixture = self.fixture()
        fixture['selected'] = '/dev/sdb'
        fixture['block'].update(name='/dev/sdb', size=32 * 1024**3, **{'maj:min': '8:16'}, children=[
            dict(name='/dev/sdb1', type='part', fstype='vfat'),
            dict(name='/dev/sdb2', type='part', fstype='xfs'),
            dict(name='/dev/sdb3', type='part', fstype='LVM2_member', children=[
                dict(name='/dev/mapper/os-root', type='lvm', fstype='xfs', **{'maj:min': '253:0'})])])
        fixture['signatures'] = [dict(type='gpt', uuid='os-partition-table')]
        root = self.fixture(existing=True)
        root['selected'] = '/dev/mapper/os-root'
        root['block'].update(name=root['selected'], type='lvm', **{'maj:min': '253:0'})
        for owner in (UPSTREAM / 'tier-2', self.root / 'verify-tier-2'):
            for name, invalid, message in (
                    ('partitioned sdb', fixture, 'Refuse an OS/partitioned/read-only device'),
                    ('current root LV', root, 'This device is mounted outside its declared data root'),
                    ('nonempty unmounted cache', dict(self.fixture(), entries=dict(matched=1)),
                     'The unmounted target contains files')):
                with self.subTest(owner=owner.name, target=name):
                    result, calls = self.run_storage(owner, invalid)
                    output = result.stdout + result.stderr
                    self.assertNotEqual(result.returncode, 0, output)
                    self.assertIn('evaluated_to', output)
                    self.assertIn(message, output)
                    self.assertTrue(all(call['operation'] not in ('service', 'filesystem', 'mount', 'file')
                                        for call in calls), calls)
                    self.assertNotIn('TASK [data_volume : Read the persistent filesystem identity]', output)

    def test_existing_mounted_cache_keeps_identity_without_stopping_or_reformatting(self):
        for owner, device, identity in ((UPSTREAM / 'tier-2', '/dev/sda', '8:0'),
                                        (self.root / 'verify-tier-2', '/dev/sdb', '8:16')):
            fixture = self.fixture(existing=True, mounted=True)
            fixture['block'].update(name=device, **{'maj:min': identity})
            if device == '/dev/sdb':
                fixture['mounts'][1].update(source='/dev/sda2', **{'maj:min': '8:2'})
                fixture['mounts'][2].update(source='/dev/sda1', **{'maj:min': '8:1'})
            result, calls = self.run_storage(owner, fixture)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(any(call['operation'] == 'service' for call in calls))
            filesystems = [call['arguments'] for call in calls if call['operation'] == 'filesystem']
            self.assertEqual(len(filesystems), 1)
            self.assertIs(filesystems[0]['force'], False)
            self.assertIs(filesystems[0]['resizefs'], True)
            self.assertEqual(filesystems[0]['dev'], device)
            mount = next(call['arguments'] for call in calls if call['operation'] == 'mount')
            self.assertEqual(mount['src'], 'UUID=' + self.fixture()['uuid'])
            self.assertEqual(mount['state'], 'mounted')
            self.assertIs(mount['boot'], True)
            self.assertEqual(mount['opts'], 'defaults,noatime,nodev,nosuid,noexec')

    def test_new_volume_stops_only_after_guards_and_uses_shared_uuid_preparation(self):
        result, calls = self.run_storage(UPSTREAM / 'tier-2', self.fixture(),
                                         cache_squid_data_fstype_package='custom-xfs-tools')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        operations = [call['operation'] for call in calls]
        self.assertLess(operations.index('find'), operations.index('service'))
        self.assertLess(operations.index('service'), operations.index('filesystem'))
        self.assertLess(operations.index('mount'), operations.index('file'))
        timeout = next(c['arguments']['timeout'] for c in calls if c['operation'] == 'wait_for')
        self.assertEqual(int(timeout), 7)
        self.assertTrue(any(c['arguments']['name'] == ['custom-xfs-tools'] for c in calls
                            if c['operation'] == 'package'))
        create = next(c['arguments'] for c in calls if c['operation'] == 'filesystem')
        self.assertEqual(create['opts'], '-L cache-data')
        self.assertEqual(create['dev'], '/dev/sda')
        self.assertIs(create['force'], False)
        mount = next(c['arguments'] for c in calls if c['operation'] == 'mount')
        self.assertEqual(mount['src'], 'UUID=' + self.fixture()['uuid'])
        self.assertEqual(calls[-1]['arguments']['owner'], 'proxy')
        self.assertEqual(calls[-1]['arguments']['group'], 'proxy')
        self.assertEqual(calls[-1]['arguments']['mode'], '0750')

    def test_uuid_pin_reuses_unmounted_legacy_cache_and_refuses_a_blank_replacement(self):
        uuid = self.fixture()['uuid']
        for existing, accepted in ((True, True), (False, False)):
            result, calls = self.run_storage(UPSTREAM / 'tier-2', self.fixture(existing=existing),
                                             cache_squid_data_uuid=uuid)
            self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)
            self.assertFalse(any(c['operation'] == 'filesystem' and not c['arguments'].get('resizefs')
                                 for c in calls))
            if not accepted:
                self.assertIn('A declared data volume is missing', result.stdout)
                self.assertFalse(any(c['operation'] in ('service', 'mount', 'file') for c in calls))

    def test_root_disk_mode_only_sets_final_directory_ownership(self):
        result, calls = self.run_storage(UPSTREAM / 'tier-2', self.fixture(),
                                         cache_squid_data_disk_enabled=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([c['operation'] for c in calls], ['file'])
        self.assertEqual(calls[0]['arguments']['owner'], 'proxy')
        self.assertEqual(calls[0]['arguments']['mode'], '0750')


if __name__ == '__main__':
    unittest.main()
