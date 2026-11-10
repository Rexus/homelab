"""Issuer storage ownership, read-only recovery checks and disposable native mount evidence."""

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


ROLE = UPSTREAM / 'tier-0/ansible/roles/openxpki'
SHARED = UPSTREAM / 'shared/ansible/roles/data_volume'
NATIVE = os.name != 'nt' and bool(shutil.which('ansible-playbook'))
MOUNTS = NATIVE and os.geteuid() == 0 and all(shutil.which(tool) for tool in ('losetup', 'mkfs.ext4', 'findmnt', 'wipefs'))


def tasks(name):
    return yaml.safe_load((ROLE / f'tasks/{name}.yml').read_text())


class IssuerStorage(TierRepositoryTestCase):
    def test_installation_owns_storage_and_recovery_preflight_is_read_only(self):
        self.generate()
        for owner in (UPSTREAM / 'tier-0', self.root / 'verify-tier-0'):
            source = owner / 'ansible/roles/openxpki'
            main = yaml.safe_load((source / 'tasks/main.yml').read_text())
            sequence = [task.get('ansible.builtin.import_tasks') for task in main]
            self.assertLess(sequence.index('preflight-inputs.yml'), sequence.index('storage.yml'))
            self.assertLess(sequence.index('portal-preflight.yml'), sequence.index('storage.yml'))
            self.assertLess(sequence.index('storage.yml'), sequence.index('packages.yml'))
            self.assertLess(sequence.index('preflight-storage.yml'), sequence.index('signer.yml'))
            self.assertLess(sequence.index('signer.yml'), sequence.index('packages.yml'))
            binding = next(i for i, task in enumerate(main) if 'ansible.builtin.copy' in task)
            self.assertLess(binding, sequence.index('packages.yml'))
            storage = yaml.safe_load((source / 'tasks/storage.yml').read_text())
            shared = next(task for task in storage if 'ansible.builtin.include_role' in task)
            self.assertEqual(shared['ansible.builtin.include_role']['name'], 'data_volume')
            self.assertEqual(shared['vars']['data_volume_expected_uuid'], '{{ openxpki_data_uuid }}')
            self.assertEqual(shared['vars']['data_volume_allowed_bind_mounts'],
                             [{'path': '/var/lib/mysql', 'fsroot': '/mysql'}])
            for recipe in ('backup', 'restore', 'bootstrap'):
                recipe_tasks = yaml.safe_load((source / f'tasks/{recipe}.yml').read_text())
                self.assertEqual(recipe_tasks[0]['ansible.builtin.import_tasks'], 'preflight.yml')
            allowed = {'ansible.builtin.assert', 'ansible.builtin.command', 'ansible.builtin.set_fact',
                       'ansible.builtin.setup', 'ansible.builtin.stat', 'ansible.builtin.slurp',
                       'ansible.builtin.find', 'ansible.builtin.import_tasks'}
            for name in ('preflight', 'preflight-inputs', 'preflight-storage', 'storage-inspect', 'binding'):
                for task in yaml.safe_load((source / f'tasks/{name}.yml').read_text()):
                    self.assertTrue(any(module in task for module in allowed), task)
                    self.assertNotIn('storage.yml', task.values())
                    if 'ansible.builtin.command' in task:
                        self.assertIs(task['changed_when'], False)

    @unittest.skipUnless(NATIVE, 'Requires Linux Ansible and the declared collections')
    def test_native_source_and_generated_recipe_syntax(self):
        self.generate()
        for owner in (UPSTREAM / 'tier-0', self.root / 'verify-tier-0'):
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '--syntax-check',
                                     'ansible/playbooks/deployment/openxpki.yml'], cwd=owner,
                                    env=dict(os.environ, ANSIBLE_CONFIG=str(owner / 'ansible/ansible.cfg')),
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(MOUNTS, 'Requires Linux root, loop devices and native mount/filesystem tools')
    def test_native_empty_pin_mounts_persists_and_preserves_database_state(self):
        fixture = tempfile.TemporaryDirectory(prefix='openxpki-storage-', dir='/tmp')
        self.addCleanup(fixture.cleanup)
        directory = Path(fixture.name)
        image = directory / 'volume.img'
        with image.open('wb') as stream:
            stream.truncate(2 * 1024**3)
        attached = subprocess.run(['losetup', '--find', '--show', str(image)], capture_output=True, text=True)
        if attached.returncode:
            self.skipTest('A disposable loop device is unavailable: ' + attached.stderr)
        device = attached.stdout.strip()
        self.addCleanup(subprocess.run, ['losetup', '--detach', device], check=True)
        volume, database = directory / 'volume', directory / 'mysql'
        self.addCleanup(subprocess.run, ['umount', str(volume)], capture_output=True)
        self.addCleanup(subprocess.run, ['umount', str(database)], capture_output=True)
        fstab = directory / 'fstab'
        fstab.write_text('')
        roles = directory / 'roles'
        # Relocate fixed guest paths and fstab only in disposable role copies.
        # Storage commands/modules stay native; no package installation touches the execution host.
        for name, original in (('openxpki', ROLE), ('data_volume', SHARED)):
            copied = roles / name
            shutil.copytree(original, copied)
            for path in (copied / 'tasks').glob('*.yml'):
                content = path.read_text().replace('/var/lib/mysql', str(database))
                content = content.replace('/etc/openxpki', str(directory / 'etc-openxpki'))
                content = content.replace('/etc/fstab', str(fstab))
                configured = yaml.safe_load(content)
                for task in configured:
                    if 'ansible.posix.mount' in task:
                        task['ansible.posix.mount']['fstab'] = str(fstab)
                    if task.get('register') in ('openxpki_mount_tables', 'data_volume_mount_tables'):
                        task['loop'][1].extend(['--tab-file', str(fstab)])
                if name == 'data_volume' and path.name == 'inspect.yml':
                    configured = [task for task in configured if 'ansible.builtin.package' not in task]
                path.write_text(yaml.safe_dump(configured, sort_keys=False))
        values = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        values.update(openxpki_data_device=device, openxpki_data_mount=str(volume),
                      openxpki_data_fstype='ext4', openxpki_min_free_mb=0,
                      openxpki_data_uuid='', openxpki_deployment_id='fixture-ca',
                      openxpki_configuration_sha256='a' * 64, ansible_system='Linux', ansible_os_family='Debian',
                      openxpki_database_password='x' * 40, openxpki_session_password='y' * 40,
                      openxpki_session_secret='z' * 40,
                      ansible_remote_tmp=str(directory / 'module-temp'))
        inputs = directory / 'inputs.yml'
        inputs.write_text(yaml.safe_dump(values))
        receipt = next(task for task in tasks('main') if 'ansible.builtin.copy' in task)
        playbook = directory / 'storage.yml'
        playbook.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False, tasks=[
            {'ansible.builtin.include_role': {'name': 'openxpki', 'tasks_from': 'storage'}},
            {'ansible.builtin.include_role': {'name': 'openxpki', 'tasks_from': 'preflight-storage'}},
            receipt,
            {'ansible.builtin.assert': {'that': [
                "openxpki_data_uuid == ''", 'openxpki_effective_data_uuid == data_volume_result.uuid',
            ]}},
        ])], sort_keys=False))
        environment = dict(os.environ, ANSIBLE_ROLES_PATH=str(roles), ANSIBLE_NOCOLOR='1',
                           ANSIBLE_LOCAL_TEMP=str(directory / 'controller-temp'))
        def run(success=True):
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook), '-e', '@' + str(inputs)],
                                    env=environment, capture_output=True, text=True, timeout=150)
            self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
            return result

        # Existing root-disk data and linked targets fail before the blank device is formatted.
        database.mkdir()
        hidden = database / '.existing-database'
        hidden.write_text('retain')
        run(False)
        signatures = subprocess.check_output(['wipefs', '--json', '--no-act', device], text=True)
        self.assertEqual(json.loads(signatures)['signatures'], [])
        hidden.unlink()
        database.rmdir()
        alternate = directory / 'alternate'
        alternate.mkdir()
        database.symlink_to(alternate, target_is_directory=True)
        run(False)
        database.unlink()

        # A retained database bind declaration is not permission to replace its missing data volume.
        fstab.write_text(f'{volume}/mysql {database} none bind,nodev,nosuid,noexec 0 0\n')
        run(False)
        signatures = subprocess.check_output(['wipefs', '--json', '--no-act', device], text=True)
        self.assertEqual(json.loads(signatures)['signatures'], [])
        fstab.write_text('')

        run()
        uuid = subprocess.check_output(['blkid', '-s', 'UUID', '-o', 'value', device], text=True).strip()
        self.assertIn('UUID=' + uuid, fstab.read_text())
        source = volume / 'mysql'
        sentinel = source / 'existing-state'
        sentinel.write_text('preserve database bytes')
        source.chmod(0o700)
        os.chown(source, 12345, 12345)
        repeated = run()
        self.assertRegex(repeated.stdout, r'changed=0\s+')
        self.assertEqual(sentinel.read_text(), 'preserve database bytes')
        self.assertEqual(source.stat().st_uid, 12345)
        self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o700)
        self.assertEqual(subprocess.check_output(['blkid', '-s', 'UUID', '-o', 'value', device], text=True).strip(), uuid)

        subprocess.run(['mount', '-t', 'tmpfs', '-o', 'size=4m,nodev,nosuid,noexec', 'tmpfs', str(source)], check=True)
        try:
            rejected = run(False)
            self.assertIn('The database source must be an ordinary directory on the verified issuer volume', rejected.stdout)
            self.assertEqual((database / sentinel.name).read_text(), 'preserve database bytes')
        finally:
            subprocess.run(['umount', str(source)], check=True)
        self.assertEqual(sentinel.read_text(), 'preserve database bytes')

        original = fstab.read_text()
        for conflicting in ('malformed-row\n',
                            f'/dev/foreign {volume}/../mysql none bind 0 0\n'):
            fstab.write_text(original + conflicting)
            declared = fstab.read_text()
            run(False)
            self.assertEqual(fstab.read_text(), declared)
            self.assertEqual(sentinel.read_text(), 'preserve database bytes')
        for target in (database, volume):
            aliased = original.replace(str(target) + ' ', str(target) + '/ ')
            self.assertNotEqual(aliased, original)
            fstab.write_text(aliased)
            rejected = run(False)
            self.assertIn('Normalize the existing aliased issuer mount declaration', rejected.stdout)
            self.assertEqual(fstab.read_text(), aliased)
        fstab.write_text(original)

    @unittest.skipUnless(NATIVE, 'Requires Linux Ansible and native findmnt/realpath')
    def test_native_raw_fstab_retains_uuid_and_rejects_single_target_aliases(self):
        with tempfile.TemporaryDirectory(prefix='openxpki-fstab-', dir='/tmp') as temporary:
            directory = Path(temporary)
            volume, database = directory / 'volume', directory / 'mysql'
            (volume / 'mysql').mkdir(parents=True)
            database.mkdir()
            fstab = directory / 'fstab'
            uuid = '11111111-1111-1111-1111-111111111111'
            original = (f'UUID={uuid} {volume} ext4 defaults,nodev,nosuid,noexec 0 2\n'
                        f'{volume}/mysql {database} none bind,nodev,nosuid,noexec 0 0\n')
            inspected = yaml.safe_load(yaml.safe_dump(tasks('storage-inspect')).replace('/var/lib/mysql', str(database)))
            for task in inspected:
                if task.get('register') == 'openxpki_mount_tables':
                    task['loop'][1].extend(['--tab-file', str(fstab)])
                if 'ansible.builtin.slurp' in task:
                    task['ansible.builtin.slurp']['src'] = str(fstab)
            inspected.append({'ansible.builtin.assert': {'that': [
                f"openxpki_data_fstab[0].source == 'UUID={uuid}'",
            ]}})
            playbook = directory / 'inspect.yml'
            playbook.write_text(yaml.safe_dump([dict(hosts='localhost', connection='local', gather_facts=False,
                vars=dict(openxpki_data_mount=str(volume), openxpki_data_fstype='ext4',
                          ansible_remote_tmp=str(directory / 'module-temp')), tasks=inspected)], sort_keys=False))
            for declaration, success in ((original, True),
                    (original.replace(str(database) + ' ', str(database) + '/ '), False),
                    (original.replace(str(volume) + ' ', str(volume) + '/ '), False)):
                fstab.write_text(declaration)
                result = subprocess.run(['ansible-playbook', '-i', 'localhost,', str(playbook)],
                    env=dict(os.environ, ANSIBLE_NOCOLOR='1', ANSIBLE_LOCAL_TEMP=str(directory / 'controller-temp')),
                    capture_output=True, text=True, timeout=90)
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
                if not success:
                    self.assertIn('Normalize the existing aliased issuer mount declaration', result.stdout)
                self.assertEqual(fstab.read_text(), declaration)


if __name__ == '__main__':
    unittest.main()
