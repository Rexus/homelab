"""Offline definition imports using disposable files and installed tools; no downloads or services.

Positive engine fixtures reuse an unchanged old signed upstream test payload; no new release is claimed.
Their test-only age allowance is 10000 days. A separate test retains the real two-day policy.
These tests establish file-management/loading behavior, never current definitions or AV coverage.
"""

import getpass
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


ROLE = UPSTREAM / 'tier-1/ansible/roles/software_intake'
ANSIBLE = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')
CLAM_ROOT = Path(os.environ.get('INTAKE_CLAM_ROOT', '/nonexistent'))
SIGTOOL = str(CLAM_ROOT / 'usr/bin/sigtool') if (CLAM_ROOT / 'usr/bin/sigtool').is_file() else shutil.which('sigtool')
CLAMSCAN = str(CLAM_ROOT / 'usr/bin/clamscan') if (CLAM_ROOT / 'usr/bin/clamscan').is_file() else shutil.which('clamscan')


class DefinitionFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='intake-definition-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.role = self.root / 'role'
        shutil.copytree(ROLE / 'tasks', self.role / 'tasks')
        self.values = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        self.database = self.root / 'active'
        self.database.mkdir()
        self.values.update(
            ansible_python_interpreter='/usr/bin/python3', ansible_os_family='Debian',
            software_intake_clam_database_dir=str(self.database),
            software_intake_scan_user=getpass.getuser(),
            software_intake_clam_users={'RedHat': getpass.getuser(), 'Debian': getpass.getuser()},
        )
        # Change only fixed executable locations and process ownership for the local fixture.
        for path in (self.role / 'tasks').glob('definitions*.yml'):
            text = path.read_text().replace('owner: root', 'owner: ' + getpass.getuser())
            text = text.replace('group: root', 'group: ' + self.group())
            if SIGTOOL:
                text = text.replace('/usr/bin/sigtool', SIGTOOL)
            if CLAMSCAN:
                text = text.replace('/usr/bin/clamscan', CLAMSCAN)
            path.write_text(text)

    @staticmethod
    def group():
        import grp
        return grp.getgrgid(os.getgid()).gr_name

    def entry(self, file, name=None):
        return {'name': name or file.name, 'src': str(file),
                'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}

    def run_import(self, files, *, install=True, extra=None, check=False, before_import=None):
        values = self.values | {'software_intake_definition_files': files} | (extra or {})
        tasks = [{'ansible.builtin.import_tasks': str(self.role / 'tasks/definitions-preflight.yml')}]
        tasks += before_import or []
        if install:
            tasks += [{'ansible.builtin.include_tasks': str(self.role / 'tasks/definitions.yml'),
                       'when': 'software_intake_definition_files | length > 0'}]
        return self.run_tasks(tasks, values, check=check)

    def run_tasks(self, tasks, values=None, *, check=False):
        play = self.root / 'play.yml'
        play.write_text(yaml.safe_dump([{
            'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': self.values | (values or {}), 'tasks': tasks,
        }], sort_keys=False))
        env = dict(os.environ, ANSIBLE_NOCOLOR='1')
        env.pop('ANSIBLE_CONFIG', None)
        result = subprocess.run([ANSIBLE, '-i', 'localhost,', str(play)] + (['--check'] if check else []),
                                capture_output=True, text=True, env=env, timeout=120)
        return result

    def assert_result(self, result, success):
        output = result.stdout + result.stderr
        if success:
            self.assertEqual(result.returncode, 0, output)
        else:
            self.assertNotEqual(result.returncode, 0, output)
        return output


@unittest.skipUnless(os.name != 'nt' and ANSIBLE, 'Requires installed native Linux Ansible')
class DefinitionPreflight(DefinitionFixture, unittest.TestCase):
    def test_empty_import_is_a_noop_and_allows_the_online_writer(self):
        existing = self.database / 'daily.cld'
        existing.write_bytes(b'untouched existing definition')
        before = existing.stat()
        result = self.run_import([], extra={'software_intake_freshclam_enabled': True})
        self.assert_result(result, True)
        self.assertEqual(existing.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(list(self.database.iterdir()), [existing])

    def test_bad_inputs_fail_before_import_and_leave_installed_files_untouched(self):
        source = self.root / 'daily.cvd'
        source.write_bytes(b'x' * 600)
        valid = self.entry(source)
        cases = [([valid | {'src': 'https://publisher.test/daily.cvd'}], {}),
                 ([valid | {'name': '../daily.cvd'}], {}),
                 ([valid | {'name': 'daily.cud'}], {}),
                 ([valid | {'name': 'daily.cvd\n'}], {}),
                 ([valid | {'sha256': '0' * 64}], {}),
                 ([valid | {'src': str(self.root / 'missing')}], {}),
                 ([valid, valid | {'name': 'daily.cld'}], {}),
                 ([valid], {'software_intake_freshclam_enabled': True}),
                 ('not-a-list', {})]
        for files, extra in cases:
            with self.subTest(files=files, extra=extra):
                result = self.run_import(files, install=False, extra=extra)
                self.assert_result(result, False)
                self.assertEqual(list(self.database.iterdir()), [])
        link = self.root / 'linked.cvd'
        link.symlink_to(source)
        self.assert_result(self.run_import([self.entry(link, 'daily.cvd')], install=False), False)
        self.assert_result(self.run_import([valid], install=False, check=True), False)

    def test_changed_source_after_preflight_is_rejected_by_the_transferred_digest(self):
        source = self.root / 'daily.cvd'
        source.write_bytes(b'x' * 600)
        approved = self.entry(source)
        result = self.run_import([approved], before_import=[{
            'ansible.builtin.copy': {'dest': str(source), 'content': 'different bytes' * 60, 'mode': '0644'},
        }])
        output = self.assert_result(result, False)
        self.assertIn('The staged database differs from its approved sha256', output)
        self.assertEqual(list(self.database.iterdir()), [])

    def test_revision_decision_rejects_rollback_and_conflicts_but_accepts_newer_or_identical(self):
        # Exercise the decision with controlled metadata; this is not native database qualification.
        task = yaml.safe_load((self.role / 'tasks/definitions-check.yml').read_text())[-1]
        cases = [(5, 'a', False), (6, 'b', False), (6, 'a', True), (7, 'b', True)]
        for revision, digest, accepted in cases:
            values = {
                'definition_candidate': {'stdout': f'Version: {revision}\n',
                                         'item': {'name': 'daily.cvd', 'sha256': digest * 64}},
                'software_intake_installed_definition_info': {'results': [{
                    'stdout': 'Version: 6\n', 'item': {'stat': {'checksum': 'a' * 64}},
                }]},
            }
            self.assert_result(self.run_tasks([task], values), accepted)

    def test_normal_installer_preflights_before_storage_and_stops_updater_before_import(self):
        main = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        validation = next(i for i, task in enumerate(main)
                          if task.get('ansible.builtin.import_tasks') == 'definitions-preflight.yml')
        storage = next(i for i, task in enumerate(main) if 'ansible.builtin.include_role' in task)
        self.assertLess(validation, storage)
        services = yaml.safe_load((ROLE / 'tasks/services.yml').read_text())
        updater = next(i for i, task in enumerate(services) if task.get('ansible.builtin.systemd_service', {}).get(
            'name') == 'clamav-freshclam.service' and 'state' in task['ansible.builtin.systemd_service'])
        imports = next(i for i, task in enumerate(services)
                       if task.get('ansible.builtin.include_tasks') == 'definitions.yml')
        self.assertLess(updater, imports)
        self.assertEqual(services[imports]['when'], 'software_intake_definition_files | length > 0')


@unittest.skipUnless(os.name != 'nt' and ANSIBLE and SIGTOOL and CLAMSCAN,
                     'Requires installed native Ansible, sigtool and clamscan')
class NativeDefinitionImport(DefinitionFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        old = os.environ.get('INTAKE_OLD_CLAM_DATABASE')
        self.signed_fixture = Path(old or '/nonexistent') / 'daily.cvd'
        if not self.signed_fixture.is_file():
            self.skipTest('Set INTAKE_OLD_CLAM_DATABASE to an existing signed test daily.cvd; no downloads')
        self.values['software_intake_max_definition_age_days'] = 10000

    def definition_fixture(self, name='daily', label='first'):
        build = self.root / f'fixture-{name}-{label}'
        build.mkdir()
        path = build / (name + '.cld')
        shutil.copyfile(self.signed_fixture, path)
        return path

    def test_native_cld_import_is_persistent_idempotent_and_preserves_unselected_files(self):
        selected = self.definition_fixture()
        extra = self.database / 'local.ndb'
        extra.write_text('Fixture.Other:0:*:6f74686572666978747572656279746573\n')
        output = self.assert_result(self.run_import([self.entry(selected)]), True)
        self.assertIn('This loading probe does not establish malware coverage', output)
        installed = self.database / 'daily.cld'
        self.assertEqual(installed.read_bytes(), selected.read_bytes())
        self.assertEqual(installed.stat().st_mode & 0o777, 0o644)
        self.assertEqual(installed.stat().st_uid, os.getuid())
        before = installed.stat().st_mtime_ns
        self.assert_result(self.run_import([self.entry(selected)]), True)
        self.assertEqual(installed.stat().st_mtime_ns, before)
        self.assertEqual(len(list(self.database.iterdir())), 2)
        self.assertEqual(extra.read_text(), 'Fixture.Other:0:*:6f74686572666978747572656279746573\n')

    def test_native_activation_copy_keeps_replaced_bytes_and_native_owner_mode_contract(self):
        # Isolate the activation copy with already verified bytes; revision decisions are tested separately.
        current = self.definition_fixture()
        original = b'previous bytes retained by the copy module'
        (self.database / 'daily.cld').write_bytes(original)
        self.values['ansible_os_family'] = 'RedHat'
        tasks = yaml.safe_load((self.role / 'tasks/definitions.yml').read_text())[1]['block']
        activate = next(task for task in tasks if task['name'].startswith('Activate only qualified'))
        workspace = self.root / 'qualified'
        (workspace / 'database').mkdir(parents=True)
        shutil.copyfile(current, workspace / 'database/daily.cld')
        values = {'software_intake_definition_workspace': {'path': str(workspace)},
                  'software_intake_definition_files': [self.entry(current)]}
        self.assert_result(self.run_tasks([activate], values), True)
        installed = self.database / 'daily.cld'
        backups = list(self.database.glob('daily.cld.*~'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual(installed.read_bytes(), current.read_bytes())
        self.assertEqual(installed.stat().st_uid, os.getuid())
        self.assertEqual(installed.stat().st_mode & 0o777, 0o644)

    def test_all_selected_files_qualify_before_any_activation(self):
        original = self.definition_fixture()
        shutil.copyfile(original, self.database / 'daily.cld')
        newer = self.definition_fixture(label='replacement')
        broken = self.root / 'main.cvd'
        broken.write_bytes(b'not a database' * 60)
        self.assert_result(self.run_import([self.entry(newer), self.entry(broken)]), False)
        self.assertEqual((self.database / 'daily.cld').read_bytes(), original.read_bytes())
        self.assertFalse((self.database / 'main.cvd').exists())
        self.assertEqual(len(list(self.database.iterdir())), 1)

    def test_cvd_requires_native_signature_and_import_does_not_convert_existing_formats(self):
        candidate = self.definition_fixture()
        corrupted = self.root / 'daily.cvd'
        content = bytearray(candidate.read_bytes())
        content[-1] ^= 0xff
        corrupted.write_bytes(content)
        self.assert_result(self.run_import([self.entry(corrupted)]), False)
        self.assertEqual(list(self.database.iterdir()), [])
        (self.database / 'daily.cvd').write_bytes(b'existing representation is preserved')
        output = self.assert_result(self.run_import([self.entry(candidate)]), False)
        self.assertIn('Keep the existing representation', output)
        self.assertEqual((self.database / 'daily.cvd').read_bytes(), b'existing representation is preserved')
        self.assertFalse((self.database / 'daily.cld').exists())

    def test_bad_engine_load_or_missing_daily_fails_before_activation(self):
        candidate = self.definition_fixture()
        (self.database / 'broken.ndb').write_text('This is not a valid signature\n')
        self.assert_result(self.run_import([self.entry(candidate)]), False)
        self.assertFalse((self.database / 'daily.cld').exists())
        (self.database / 'broken.ndb').unlink()
        main = self.definition_fixture(name='main')
        output = self.assert_result(self.run_import([self.entry(main)]), False)
        self.assertIn('Include an approved daily.cvd/daily.cld', output)
        self.assertEqual(list(self.database.iterdir()), [])

    def test_native_stale_signed_cvd_fails_at_the_real_freshness_policy(self):
        old = os.environ.get('INTAKE_OLD_CLAM_DATABASE')
        candidate = Path(old or '/nonexistent') / 'daily.cvd'
        if not candidate.is_file():
            self.skipTest('Set INTAKE_OLD_CLAM_DATABASE to an existing stale signed daily.cvd fixture')
        result = self.run_import([self.entry(candidate)], extra={'software_intake_max_definition_age_days': 2})
        output = self.assert_result(result, False)
        self.assertIn('Verify each staged container with native sigtool', output)
        self.assertIn('Load the proposed database', output)
        self.assertRegex(output, r'(?i)(outdated|older|age)')
        self.assertEqual(list(self.database.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
