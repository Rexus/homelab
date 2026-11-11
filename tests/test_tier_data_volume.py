"""Data-volume qualification and disposable native filesystem convergence."""

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / 'shared/ansible/roles/data_volume'
ANSIBLE = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')


class DataVolumeOwnership(TierRepositoryTestCase):
    def test_every_reference_extra_disk_matches_its_service_stable_device(self):
        import hcl2
        self.generate()
        bindings = {
            ('tier-0', 'foundation'): ('issuer', 'openxpki_data_device'),
            ('tier-0', 'syslog'): ('syslog', 'syslog_ng_data_device'),
            ('tier-1', 'intake'): ('intake', 'software_intake_data_device'),
            ('tier-1', 'observability'): ('observability', 'observability_vm_data_device'),
            ('tier-2', 'cache'): ('cache', 'cache_squid_data_device'),
        }
        roles = {'issuer': 'openxpki', 'syslog': 'syslog_ng', 'intake': 'software_intake',
                 'observability': 'observability_vm', 'cache': 'cache_proxy'}
        for base, prefix in ((UPSTREAM, ''), (self.root, 'verify-')):
            checked = set()
            for tier in ('tier-0', 'tier-1', 'tier-2'):
                owner = base / (prefix + tier)
                for example in (owner / 'terraform/deployments').glob('*/terraform.tfvars.example'):
                    values = hcl2.loads(example.read_text(), serialization_options=hcl2.SerializationOptions(
                        strip_string_quotes=True, with_comments=False))
                    for guest, settings in values.get('vm_instances', {}).items():
                        for disk in settings.get('extra_disks', []):
                            key = (tier, example.parent.name)
                            self.assertIn(key, bindings, f'Add a service-device correspondence for {example}: {guest}')
                            inputs, field = bindings[key]
                            configuration = yaml.safe_load((owner / f'ansible/roles/{roles[inputs]}/defaults/main.yml').read_text())
                            configuration |= yaml.safe_load((owner / f'ansible/group_vars/{inputs}.yml.example').read_text())
                            expected = '/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-' + disk['interface']
                            self.assertEqual(configuration[field], expected, f'{example}: {guest}')
                            checked.add(key)
            self.assertEqual(checked, set(bindings))
            backup = yaml.safe_load((base / (prefix + 'tier-0') / 'ansible/group_vars/logging_backup.yml.example').read_text())
            self.assertEqual(backup['logging_backup_repository_device'],
                             '/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1')

    def test_generated_storage_code_and_intake_call_match_source(self):
        self.generate()
        generated = self.root / 'verify-shared/ansible/roles/data_volume'
        for path in ROLE.rglob('*.yml'):
            self.assertEqual(path.read_bytes(), (generated / path.relative_to(ROLE)).read_bytes())
        for owner in [UPSTREAM / 'tier-1', self.root / 'verify-tier-1']:
            tasks = yaml.safe_load((owner / 'ansible/roles/software_intake/tasks/main.yml').read_text())
            storage = next(i for i, task in enumerate(tasks) if 'ansible.builtin.include_role' in task)
            self.assertEqual(tasks[storage]['ansible.builtin.include_role']['name'], 'data_volume')
            self.assertEqual(tasks[0]['ansible.builtin.import_tasks'], 'preflight.yml')
            self.assertLess(storage, next(i for i, task in enumerate(tasks)
                                         if task.get('ansible.builtin.import_tasks') == 'storage.yml'))
            self.assertEqual(tasks[storage]['vars']['data_volume_expected_uuid'], '{{ software_intake_data_uuid }}')


@unittest.skipUnless(os.name != 'nt' and ANSIBLE, 'Requires native Ansible and declared collections')
class DataVolumeGuards(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix='homelab-data-volume-')
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)

    def run_tasks(self, tasks, values):
        play, inputs = self.root / 'play.yml', self.root / 'inputs.yml'
        play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                                        'gather_facts': False, 'tasks': tasks}], sort_keys=False))
        inputs.write_text(yaml.safe_dump(values))
        return subprocess.run([ANSIBLE, '-i', 'localhost,', str(play), '-e', '@' + str(inputs)],
                              capture_output=True, text=True, timeout=120)

    def inputs(self, existing=False):
        values = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        values.update(data_volume_device='/dev/sdb', data_volume_path='/srv/intake',
                      data_volume_label='intake-data', data_volume_is_blank=not existing,
                      data_volume_realpaths={'results': [{'stdout': '/dev/sdb'}]},
                      data_volume_block={'name': '/dev/sdb', 'type': 'disk', 'size': 2147483648,
                                         'ro': False, 'maj:min': '8:16', 'fstype': None, 'uuid': None,
                                         'label': None}, data_volume_signatures=[],
                      data_volume_target_mounts=[], data_volume_device_mounts=[],
                      data_volume_target_fstab=[], data_volume_fstab=[],
                      data_volume_target_entries={'matched': 0, 'skipped_paths': {}})
        if existing:
            volume_uuid = '12345678-1234-1234-1234-123456789abc'
            values['data_volume_block'].update(fstype='xfs', uuid=volume_uuid, label='intake-data')
            values['data_volume_signatures'] = [{'type': 'xfs', 'uuid': volume_uuid}]
        return values

    def test_new_and_existing_volumes_qualify_without_host_changes(self):
        tasks = yaml.safe_load((ROLE / 'tasks/validate.yml').read_text())
        for existing in [False, True]:
            with self.subTest(existing=existing):
                result = self.run_tasks(tasks, self.inputs(existing))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('changed=0', result.stdout)

    def test_unsafe_storage_stops_before_filesystem_or_mount_changes(self):
        tasks = yaml.safe_load((ROLE / 'tasks/validate.yml').read_text())
        blank = self.inputs()
        existing = self.inputs(True)
        cases = {}

        def case(name, base, **changes):
            cases[name] = dict(copy.deepcopy(base), **changes)

        case('partitioned disk', blank, data_volume_block=dict(blank['data_volume_block'], children=[{}]))
        case('read-only disk', blank, data_volume_block=dict(blank['data_volume_block'], ro=True))
        case('OS disk', blank, data_volume_device_mounts=[{'target': '/', 'maj:min': '8:16'}])
        case('foreign target', blank, data_volume_target_mounts=[{'target': '/srv/intake', 'maj:min': '8:17', 'fsroot': '/'}])
        case('bind mount', existing, data_volume_target_mounts=[{'target': '/srv/intake', 'maj:min': '8:16', 'fsroot': '/subdir'}])
        case('hidden root data', blank, data_volume_target_entries={'matched': 1})
        case('unreadable target', blank, data_volume_target_entries={'matched': 0, 'skipped_paths': {'/srv/intake': 'denied'}})
        case('missing pinned volume', blank, data_volume_expected_uuid=existing['data_volume_block']['uuid'])
        case('missing fstab volume', blank, data_volume_target_fstab=[{'target': '/srv/intake', 'source': 'UUID=old', 'fstype': 'xfs'}])
        case('apparently blank mounted bind', blank,
             data_volume_allowed_bind_mounts=[{'path': '/var/lib/mysql', 'fsroot': '/mysql'}],
             data_volume_device_mounts=[{'target': '/var/lib/mysql', 'fsroot': '/mysql'}])
        case('wrong UUID', existing, data_volume_expected_uuid='aaaaaaaa-1234-1234-1234-123456789abc')
        case('wrong filesystem', existing, data_volume_fstype='ext4')
        case('ambiguous signatures', existing, data_volume_signatures=existing['data_volume_signatures'] + [{'type': 'gpt', 'uuid': 'other'}])
        case('unrecognized existing volume', existing, data_volume_block=dict(existing['data_volume_block'], label=None))
        case('foreign fstab identity', existing, data_volume_target_fstab=[{'target': '/srv/intake', 'source': 'UUID=old', 'fstype': 'xfs'}])
        case('unapproved bind', existing, data_volume_device_mounts=[{'target': '/var/lib/mysql', 'fsroot': '/mysql'}])
        case('wrong bind subdirectory', existing,
             data_volume_allowed_bind_mounts=[{'path': '/var/lib/mysql', 'fsroot': '/mysql'}],
             data_volume_device_mounts=[{'target': '/var/lib/mysql', 'fsroot': '/private'}])
        for name, values in cases.items():
            with self.subTest(case=name):
                result = self.run_tasks(tasks, values)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('changed=0', result.stdout, result.stdout + result.stderr)
                self.assertIn('evaluated_to', result.stdout, result.stdout + result.stderr)

    def test_device_cannot_be_repurposed_from_another_fstab_target(self):
        tasks = yaml.safe_load((ROLE / 'tasks/inspect.yml').read_text())
        gate = next(task for task in tasks if task['name'].startswith('Refuse persistent declarations'))
        for target, accepted in [('/srv/intake', True), ('/srv/other', False)]:
            values = self.inputs()
            values['data_volume_fstab'] = [{'target': target, 'source': '/dev/sdb', 'fstype': 'xfs'}]
            result = self.run_tasks([gate], values)
            self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)

    def fstab_guards(self, content, existing=False):
        """Read a real temporary fstab, then run all inspection/validation guards.

        Device metadata is synthetic; no lsblk/wipefs, devices, mounts or services
        are accessed. Udev-only tag evaluation prevents libblkid device scanning.
        """
        table = self.root / 'fixture.fstab'
        table.write_text(content)
        config = self.root / 'blkid.conf'
        config.write_text(f'EVALUATE=udev\nSEND_UEVENT=not\nCACHE_FILE={self.root / "empty-cache"}\n')
        inspection = yaml.safe_load((ROLE / 'tasks/inspect.yml').read_text())
        command = next(task for task in inspection if task['name'] ==
                       'Read current mounts and persistent storage declarations')['loop'][1]
        native = subprocess.run(command + ['--tab-file', str(table)], capture_output=True, text=True,
                                env=dict(os.environ, BLKID_CONF=str(config)), timeout=10)
        values = self.inputs(existing)
        device = self.root / 'device.img'
        device.touch(exist_ok=True)
        target = self.root / 'data'
        target.mkdir(exist_ok=True)
        values.update(data_volume_device=str(device), data_volume_path=str(target),
                      data_volume_realpaths={'results': [{'stdout': str(device)}]},
                      data_volume_lsblk={'stdout': json.dumps({'blockdevices': [values['data_volume_block']]})},
                      data_volume_wipefs={'stdout': json.dumps({'signatures': values['data_volume_signatures']})},
                      data_volume_mount_tables={'results': [
                          {'rc': 0, 'stderr': '', 'stdout': json.dumps({'filesystems': []})},
                          {'rc': native.returncode, 'stdout': native.stdout, 'stderr': native.stderr},
                      ]})
        # Extra-vars outrank set_fact: leave derived facts to the actual inspection tasks.
        for derived in ('data_volume_block', 'data_volume_signatures', 'data_volume_target_mounts',
                        'data_volume_device_mounts', 'data_volume_target_fstab', 'data_volume_fstab',
                        'data_volume_target_entries', 'data_volume_is_blank'):
            values.pop(derived, None)
        reader = copy.deepcopy(next(task for task in inspection if 'ansible.builtin.slurp' in task))
        reader['ansible.builtin.slurp']['src'] = str(table)
        start = next(i for i, task in enumerate(inspection) if task['name'].startswith('Require complete device inspection'))
        tasks = [reader] + inspection[start:] + yaml.safe_load((ROLE / 'tasks/validate.yml').read_text())
        return native, self.run_tasks(tasks, values)

    def test_malformed_fstab_never_becomes_an_empty_or_partial_authorization(self):
        device, target = self.root / 'device.img', self.root / 'data'
        for content, native_rc in [('', 1), (f'{device} {target}\n', 1),
                                   (f'{self.root / "other.img"} /fixture-other xfs defaults 0 0\n'
                                    f'{device} {target}\n', 0)]:
            with self.subTest(content=content):
                native, result = self.fstab_guards(content)
                self.assertEqual(native.returncode, native_rc, native.stderr)
                if content:
                    self.assertTrue(native.stderr.strip())
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn('incomplete storage declarations cannot authorize formatting', result.stdout)
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('changed=0', result.stdout)

    def test_native_fstab_canonicalization_catches_device_and_target_aliases(self):
        device, target = self.root / 'device.img', self.root / 'data'
        device.touch()
        target.mkdir()
        alias = self.root / 'by-id-alias'
        alias.symlink_to(device)
        native, result = self.fstab_guards(f'{alias} /fixture-other xfs defaults 0 0\n')
        self.assertEqual(json.loads(native.stdout)['filesystems'][0]['source'], str(device))
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('already assigned to another fstab target', result.stdout)
        native, result = self.fstab_guards(f'{alias} {target} xfs defaults 0 0\n', existing=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        _, result = self.fstab_guards(f'{alias} {target}/ xfs defaults 0 0\n', existing=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('An existing fstab target aliases this path', result.stdout)
        target_alias = self.root / 'target-alias'
        target_alias.symlink_to(target, target_is_directory=True)
        native, result = self.fstab_guards(f'{self.root / "old.img"} {target_alias} xfs defaults 0 0\n')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('An existing fstab target aliases this path', result.stdout)

    def test_unresolved_local_fstab_sources_block_only_blank_volume_initialization(self):
        for source, fstype in [('UUID=11111111-1111-1111-1111-111111111111', 'xfs'),
                               ('LABEL=homelab-fixture-missing', 'xfs'),
                               ('PARTUUID=11111111-1111-1111-1111-111111111111', 'xfs'),
                               ('PARTLABEL=homelab-fixture-missing', 'xfs'),
                               ('/dev/homelab-fixture-no-such-device', 'xfs'),
                               ('/dev/homelab-fixture-no-such-device', 'fuseblk')]:
            with self.subTest(source=source, fstype=fstype):
                native, result = self.fstab_guards(f'{source} /fixture-other {fstype} defaults 0 0\n')
                self.assertEqual(native.returncode, 0, native.stderr)
                self.assertIn(json.loads(native.stdout)['filesystems'][0]['source'], [source, None])
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('Unresolved local block declaration', result.stdout)
                self.assertIn('changed=0', result.stdout)
        _, result = self.fstab_guards('UUID=11111111-1111-1111-1111-111111111111 /fixture-other xfs defaults 0 0\n',
                                      existing=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_network_fuse_bind_and_pseudo_fstab_sources_do_not_block_a_new_disk(self):
        content = ('server.invalid:/export /fixture-network nfs defaults 0 0\n'
                   '//server.invalid/share /fixture-cifs cifs defaults 0 0\n'
                   'user@server.invalid:/export /fixture-fuse fuse.sshfs defaults 0 0\n'
                   'tmpfs /fixture-tmpfs tmpfs defaults 0 0\n'
                   'devpts /fixture-devpts devpts defaults 0 0\n'
                   '/srv/source /fixture-bind none bind 0 0\n')
        native, result = self.fstab_guards(content)
        self.assertEqual(native.returncode, 0, native.stderr)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('changed=0', result.stdout)


@unittest.skipUnless(os.name != 'nt' and os.environ.get('HOMELAB_DATA_VOLUME_MOUNT_TESTS') == '1',
                     'Requires root in a private mount namespace with disposable loopback storage')
class NativeDataVolume(DataVolumeGuards):
    def test_filesystem_mount_rerun_growth_and_missing_volume(self):
        self.assertEqual(os.geteuid(), 0)
        # The harness binds a private file over /etc/fstab inside its own mount namespace.
        self.assertEqual(Path('/etc/fstab').read_text(), '# isolated data-volume acceptance\n')
        image = self.root / 'disk.img'
        with image.open('wb') as stream:
            stream.truncate(2 * 1024**3)
        device = subprocess.check_output(['losetup', '--find', '--show', str(image)], text=True).strip()
        target = self.root / 'data'
        self.addCleanup(subprocess.run, ['losetup', '--detach', device], check=True)
        self.addCleanup(subprocess.run, ['umount', str(target)], check=False, capture_output=True)
        values = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        values.update(ansible_system='Linux', ansible_os_family='Debian', data_volume_device=device,
                      data_volume_path=str(target), data_volume_fstype=os.environ.get('DATA_VOLUME_TEST_FSTYPE', 'ext4'),
                      data_volume_label='intake-data',
                      data_volume_min_free_bytes=0)
        # Only the package installation is omitted: all required tools are preinstalled in this fixture.
        tasks = [task for task in yaml.safe_load((ROLE / 'tasks/inspect.yml').read_text())
                 if 'ansible.builtin.package' not in task]
        tasks += yaml.safe_load((ROLE / 'tasks/validate.yml').read_text())
        tasks += yaml.safe_load((ROLE / 'tasks/prepare.yml').read_text())
        result = self.run_tasks(tasks, values)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        uuid = subprocess.check_output(['blkid', '-s', 'UUID', '-o', 'value', device], text=True).strip()
        self.assertIn('UUID=' + uuid, Path('/etc/fstab').read_text())
        marker = target / 'retained-event'
        marker.write_text('must survive reruns and growth')
        result = self.run_tasks(tasks, values)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('changed=0', result.stdout)
        # CA-style subdirectory binds must be explicitly declared and match the inspected FSROOT.
        database = target / 'mysql'
        database.mkdir()
        binding = self.root / 'database'
        binding.mkdir()
        subprocess.run(['mount', '--bind', str(database), str(binding)], check=True)
        try:
            refused = self.run_tasks(tasks, values)
            self.assertNotEqual(refused.returncode, 0, refused.stdout + refused.stderr)
            allowed = dict(values, data_volume_allowed_bind_mounts=[{'path': str(binding), 'fsroot': '/mysql'}])
            qualified = self.run_tasks(tasks, allowed)
            self.assertEqual(qualified.returncode, 0, qualified.stdout + qualified.stderr)
        finally:
            subprocess.run(['umount', str(binding)], check=True)
        before = os.statvfs(target).f_blocks
        with image.open('r+b') as stream:
            stream.truncate(3 * 1024**3)
        subprocess.run(['losetup', '--set-capacity', device], check=True)
        result = self.run_tasks(tasks, values)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertGreater(os.statvfs(target).f_blocks, before)
        self.assertEqual(marker.read_text(), 'must survive reruns and growth')
        self.assertEqual(subprocess.check_output(['blkid', '-s', 'UUID', '-o', 'value', device], text=True).strip(), uuid)
        # An empty replacement cannot take over a persisted UUID declaration.
        subprocess.run(['umount', str(target)], check=True)
        replacement = self.root / 'replacement.img'
        with replacement.open('wb') as stream:
            stream.truncate(2 * 1024**3)
        substitute = subprocess.check_output(['losetup', '--find', '--show', str(replacement)], text=True).strip()
        self.addCleanup(subprocess.run, ['losetup', '--detach', substitute], check=True)
        result = self.run_tasks(tasks, dict(values, data_volume_device=substitute))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('A declared data volume is missing', result.stdout, result.stdout + result.stderr)
        untouched = subprocess.run(['wipefs', '--json', '--no-act', substitute], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(untouched.stdout)['signatures'], [])


if __name__ == '__main__':
    unittest.main()
