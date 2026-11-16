"""Native bundle/file/crypto transactions with doubled HSM, database and systemd boundaries."""

import getpass
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import uuid

import yaml

from openxpki_recovery_fixture import ANSIBLE, NATIVE, RecoveryFixture, ROLE


spec = importlib.util.spec_from_file_location('migration_bundle', ROLE / 'files/pkcs11-migration-bundle.py')
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


def archive(path, files):
    with tarfile.open(path, 'w:gz') as stream:
        for name, value in sorted(files.items()):
            data = value.encode() if isinstance(value, str) else value
            entry = tarfile.TarInfo(name)
            entry.size, entry.mode = len(data), 0o640
            stream.addfile(entry, io.BytesIO(data))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crypto(key, library, engine):
    return yaml.safe_dump({'token': {'ca-signer': {
        'engine': 'PKCS11', 'key_store': 'ENGINE', 'key': key, 'secret': 'default',
        'engine_section': f'engine_id = pkcs11\ndynamic_path = {engine}\nMODULE_PATH = {library}\nPIN = "__PIN__"\ninit = 0\n'}}})


class BundleBoundary(unittest.TestCase):
    def test_only_same_key_provider_locator_changes_are_admitted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old, new = root / 'old.tgz', root / 'new.tgz'
            old_files = {'config.d/realm/infrastructure/crypto.yaml': crypto('pkcs11:serial=OLD;id=%01;type=private', '/old.so', '/engine.so'),
                         'config.d/system/crypto.yaml': 'secret: original', 'schemas/backend.sql': 'original schema'}
            new_files = dict(old_files, **{'config.d/realm/infrastructure/crypto.yaml': crypto('pkcs11:serial=NEW;id=%01;type=private', '/new.so', '/engine.so')})
            archive(old, old_files)
            archive(new, new_files)
            args = (old, new, 'infrastructure', 'pkcs11:serial=NEW;id=%01;type=private', '/new.so', '/engine.so')
            self.assertIn('schemas/backend.sql', bundle.validate(*args))
            for field in ('schemas/backend.sql', 'config.d/system/crypto.yaml'):
                archive(new, dict(new_files, **{field: 'unauthorized change'}))
                with self.assertRaisesRegex(ValueError, 'cannot change'):
                    bundle.validate(*args)
            archive(new, dict(new_files, **{'../escape': 'forbidden'}))
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                bundle.validate(*args)
            output = root / 'provider-revision.tgz'
            bundle.build(old, output, 'infrastructure', args[3], args[4], args[5])
            with tarfile.open(output) as revised:
                self.assertEqual(revised.extractfile('config.d/system/crypto.yaml').read(), b'secret: original')
                self.assertEqual(revised.extractfile('schemas/backend.sql').read(), b'original schema')
                signer = yaml.safe_load(revised.extractfile('config.d/realm/infrastructure/crypto.yaml'))['token']['ca-signer']
                self.assertEqual(signer['key'], args[3])
            with self.assertRaises(FileExistsError):
                bundle.build(old, output, 'infrastructure', args[3], args[4], args[5])


@unittest.skipUnless(ANSIBLE and shutil.which('systemctl'), 'Requires native Linux systemd tools')
class NativeTimerAdmission(unittest.TestCase):
    def test_real_active_timer_and_service_pass_but_inactive_unit_is_rejected(self):
        if os.geteuid() != 0 or not shutil.which('systemd-run'):
            self.skipTest('Requires root on an isolated systemd test OS for disposable transient units')
        prefix = 'pkcs11-test-' + uuid.uuid4().hex[:12]
        active = [prefix + '-service.service', prefix + '-timer.timer']
        for command in (
            ['systemd-run', '--unit', prefix + '-service', '--property=Type=oneshot',
             '--property=RemainAfterExit=yes', '/usr/bin/true'],
            ['systemd-run', '--unit', prefix + '-timer', '--on-active=10min', '/usr/bin/true'],
        ):
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.addCleanup(subprocess.run, ['systemctl', 'stop', *active, prefix + '-timer.service'], capture_output=True)
        source = yaml.safe_load((ROLE / 'tasks/pkcs11-migration-backup.yml').read_text())
        tasks = [task for task in source if task['name'] in (
            'Inspect current writers before the explicit outage',
            'Require the accepted running issuer before capturing its final history')]
        with tempfile.TemporaryDirectory(prefix='migration-systemd-') as directory:
            play = Path(directory) / 'play.yml'
            for units, accepted in ((active, True), (active, False)):
                if not accepted:
                    subprocess.run(['systemctl', 'stop', active[-1]], check=True, capture_output=True)
                play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                    'gather_facts': False, 'vars': {'migration_start_units': units}, 'tasks': tasks}]))
                result = subprocess.run([ANSIBLE, '-i', 'localhost,', str(play)], text=True, capture_output=True)
                self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)


DOUBLE = '''
import json
from pathlib import Path
from ansible.plugins.action import ActionBase
class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        v, args = task_vars, dict(self._task.args)
        action = self._task.action.rsplit('.', 1)[-1]
        with open(v['fixture_events'], 'a') as stream:
            stream.write(json.dumps(dict(action=action, args=args)) + '\\n')
        if action == 'package_facts':
            return dict(result, changed=False, ansible_facts={'packages': {
                key: [{'version': value}] for key, value in v['openxpki_package_versions'].items()}})
        if action == 'apt':
            return dict(result, changed=False)
        if action == 'systemd_service':
            if args.get('state') == 'started' and v.get('fixture_start_failure'):
                return dict(result, failed=True, msg='injected service-start failure')
            return dict(result, changed=True)
        if action == 'mariadb_db':
            if args['state'] != 'dump':
                return dict(result, failed=True, msg='Database mutation is forbidden')
            Path(args['target']).write_text(v.get('fixture_history', Path(v['fixture_database']).read_text()))
            return dict(result, changed=False)
        argv = args['argv']
        if argv[0] == 'ln' and v.get('fixture_backup_race'):
            destination = Path(argv[-1])
            if v['fixture_backup_race'] == 'directory':
                destination.mkdir()
            else:
                destination.write_text('concurrent recovery custody')
        if argv[:2] == ['systemctl', 'is-active']:
            status = v.get('fixture_timer_status', 'active') if argv[-1].endswith('.timer') else 'active'
            return dict(result, changed=False, rc=0 if status == 'active' else 3, stdout=status, stderr='')
        if argv[0] == 'oxi':
            if v.get('fixture_config_failure') and argv[-1] == v['fixture_active_config']:
                return dict(result, failed=True, rc=1, msg='injected native config rejection')
            return dict(result, changed=False, rc=0, stdout='1', stderr='')
        if argv[0] == 'openssl' and '-sign' in argv:
            argv = list(argv)
            for option in ('-engine', '-keyform'):
                index = argv.index(option)
                del argv[index:index + 2]
            argv[argv.index('-sign') + 1] = v['fixture_token_key']
            argv[argv.index('-passin') + 1] = 'pass:separately-custodied-fixture-software-password'
            args['argv'] = argv
        return self._execute_module(module_name='ansible.builtin.command', module_args=args, task_vars=v, tmp=tmp)
'''


@unittest.skipUnless(NATIVE, 'Requires native Ansible, OpenSSL and age')
class NativeProviderMigration(RecoveryFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.prepare('pkcs11')
        import grp
        group = grp.getgrgid(os.getgid()).gr_name
        self.etc = self.root / 'etc'
        self.old_provider = {key: self.inputs[key] for key in (
            'hsm_issuer_key', 'hsm_provider_library', 'hsm_issuer_engine_library', 'hsm_provider_expected_serial')}
        original_release = self.data / ('configuration/' + self.inputs['openxpki_configuration_sha256'])
        old_files = {'config.d/realm/infrastructure/crypto.yaml': crypto(self.inputs['hsm_issuer_key'], self.inputs['hsm_provider_library'], self.inputs['hsm_issuer_engine_library']),
                     'config.d/system/crypto.yaml': yaml.safe_dump({'secret': {'default': {'value': self.inputs['hsm_issuer_pin']}, 'svault': {'value': 'original DataVault'}}}),
                     'config.d/system/database.yaml': 'original rendered database',
                     'client.d/service/webui/default.yaml': 'original rendered webui',
                     'schemas/backend.sql': 'original schema', 'log.conf': 'original log configuration'}
        self.old_archive, self.new_archive = self.root / 'old.tgz', self.root / 'new.tgz'
        self.old_sha = archive(self.old_archive, old_files)
        self.old_release = self.data / ('configuration/' + self.old_sha)
        original_release.rename(self.old_release)
        for name, value in old_files.items():
            path = self.old_release / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
        (self.old_release / '.extracted').write_text(self.old_sha + '\n')
        self.inputs['openxpki_required_state_paths'] = [str(self.data / 'identity/issuer.pem')]
        self.inputs.update(openxpki_configuration_sha256=self.old_sha, openxpki_configuration_src=str(self.old_archive))
        shutil.copyfile(self.old_archive, self.data / 'configuration.tar.gz')
        original_binding = json.loads((self.data / 'deployment.json').read_text())
        original_binding['configuration_sha256'] = self.old_sha
        (self.data / 'deployment.json').write_text(json.dumps(original_binding))
        self.original_binding = original_binding
        self.inputs.update(hsm_issuer_key='pkcs11:serial=DESTINATION456;id=%01;type=private',
                           hsm_provider_expected_serial='DESTINATION456', fixture_serial='DESTINATION456')
        new_files = dict(old_files)
        new_files['config.d/realm/infrastructure/crypto.yaml'] = crypto(self.inputs['hsm_issuer_key'], self.inputs['hsm_provider_library'], self.inputs['hsm_issuer_engine_library'])
        self.new_sha = archive(self.new_archive, new_files)
        self.new_release = self.data / ('configuration/' + self.new_sha)
        # Binary SPKI is hashed without a text codec.
        import subprocess
        public_der = subprocess.run(['openssl', 'pkey', '-pubin', '-outform', 'DER'], input=self.inputs['fixture_public_key'].encode(), capture_output=True, check=True).stdout
        custody = self.root / 'controller-custody'
        custody.mkdir(mode=0o700)
        self.inputs.update(openxpki_pkcs11_migration_approved=True,
                           ansible_architecture='x86_64', openxpki_pkcs11_migration_resume_accepted=True,
                           openxpki_pkcs11_migration_expected_old_sha256=self.old_sha,
                           openxpki_pkcs11_migration_new_src=str(self.new_archive),
                           openxpki_pkcs11_migration_new_sha256=self.new_sha,
                           openxpki_pkcs11_migration_spki_sha256=hashlib.sha256(public_der).hexdigest(),
                           openxpki_pkcs11_migration_backup_dest=str(custody / 'migration.age'),
                           openxpki_token_alias='ca-signer-1', fixture_token_key=str(self.root / 'outside-token-fixture.key'),
                           fixture_active_config=str(self.etc / 'openxpki/config.d'))
        self.database = self.root / 'history.sql'
        self.database.write_text('original complete history')
        self.inputs['fixture_database'] = str(self.database)
        for path in (self.roles / 'openxpki/tasks').glob('pkcs11-migration*.yml'):
            value = path.read_text().replace('/etc/systemd/system', str(self.etc / 'systemd/system')).replace('/etc/openxpki', str(self.etc / 'openxpki'))
            value = value.replace('group: openxpkiclient', 'group: ' + group).replace('group: ' + getpass.getuser() + 'client', 'group: ' + group)
            value = value.replace('become_user: openxpki', 'become_user: ' + getpass.getuser())
            for action in ('command', 'package_facts'):
                value = value.replace('ansible.builtin.' + action + ':', 'fixture.migration.' + action + ':')
            for action in ('apt', 'systemd_service', 'mariadb_db'):
                value = value.replace('fixture.recovery.' + action + ':', 'fixture.migration.' + action + ':')
            path.write_text(value)
        (self.roles / 'openxpki/tasks/pkcs11-migration-storage.yml').write_text(
            '- ansible.builtin.debug: {msg: "Fixture uses temporary directories; mounted-volume checks are tested separately"}\n')
        plugin = self.root / 'collections/ansible_collections/fixture/migration/plugins'
        for action in ('command', 'package_facts', 'apt', 'systemd_service', 'mariadb_db'):
            (plugin / 'action').mkdir(parents=True, exist_ok=True)
            (plugin / 'modules').mkdir(exist_ok=True)
            (plugin / f'action/{action}.py').write_text(DOUBLE)
            (plugin / f'modules/{action}.py').write_text('')
        env_path = self.etc / 'systemd/system/openxpki-serverd.service.d/hsm-provider.conf'
        env_path.parent.mkdir(parents=True)
        env_path.write_text('original hardware environment\n')
        active = self.etc / 'openxpki'
        active.mkdir()
        for name in ('config.d', 'client.d', 'log.conf'):
            (active / name).symlink_to(self.old_release / name)
        self.transaction = self.data / ('pkcs11-migration-' + self.new_sha)

    def prepare_migration(self):
        result = self.run_role('pkcs11-migration')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads((self.transaction / 'transaction.json').read_text())
        self.assertEqual(record['phase'], 'prepared')
        self.assertTrue((self.data / 'pkcs11-migration-inhibit').exists())
        backup = Path(self.inputs['openxpki_pkcs11_migration_backup_dest'])
        recovered = self.root / 'verified-recovery.tgz'
        self.run_native(['age', '--decrypt', '--identity', str(self.root / 'age.key'), '--output', str(recovered), str(backup)])
        with tarfile.open(recovered) as retained:
            self.assertEqual(retained.extractfile('database.sql').read(), self.database.read_bytes())
            self.assertEqual(json.load(retained.extractfile('deployment.json')), self.original_binding)
        self.inputs.update(openxpki_pkcs11_migration_backup_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),
                           openxpki_pkcs11_migration_backup_retained=True)
        return record

    def test_prepare_apply_and_latest_history_rollback_keep_ordinary_binding_strict(self):
        self.prepare_migration()
        rejected = self.run_role('binding', openxpki_configuration_sha256=self.new_sha)
        self.assertNotEqual(rejected.returncode, 0)
        applied = self.run_role('pkcs11-migration', openxpki_pkcs11_migration_operation='apply')
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertEqual(json.loads((self.data / 'deployment.json').read_text())['configuration_sha256'], self.new_sha)
        self.assertFalse((self.data / 'pkcs11-migration-inhibit').exists())
        self.old_archive.write_text('changed controller artifact must not become rollback custody')
        rejected = self.run_role('binding')
        self.assertNotEqual(rejected.returncode, 0)
        wrong = self.run_role('pkcs11-migration', openxpki_pkcs11_migration_operation='rollback')
        self.assertNotEqual(wrong.returncode, 0)
        self.old_archive.unlink()
        self.database.write_text('latest post-cutover history')
        for path in (self.old_release / 'config.d/system/database.yaml',
                     self.old_release / 'client.d/service/webui/default.yaml',
                     self.transaction / 'old-hsm-provider.conf'):
            retained = path.read_bytes()
            path.write_text('changed old custody must block rollback')
            rejected = self.run_role('pkcs11-migration', openxpki_pkcs11_migration_operation='rollback',
                                     fixture_serial='ORIGINAL123', **self.old_provider)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(json.loads((self.data / 'deployment.json').read_text())['configuration_sha256'], self.new_sha)
            path.write_bytes(retained)
        rolled = self.run_role('pkcs11-migration', openxpki_pkcs11_migration_operation='rollback',
                               fixture_serial='ORIGINAL123', **self.old_provider)
        self.assertEqual(rolled.returncode, 0, rolled.stdout + rolled.stderr)
        self.assertEqual(json.loads((self.data / 'deployment.json').read_text()), self.original_binding)
        self.assertEqual(self.database.read_text(), 'latest post-cutover history')
        self.assertFalse(any(event['action'] == 'mariadb_db' and event['args']['state'] != 'dump' for event in self.events()))

    def test_fresh_backup_guard_and_frozen_history_reject_unsafe_apply(self):
        destination = Path(self.inputs['openxpki_pkcs11_migration_backup_dest'])
        destination.write_text('retain existing recovery')
        rejected = self.run_role('pkcs11-migration')
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(destination.read_text(), 'retain existing recovery')
        self.assertFalse(self.transaction.exists())
        destination.unlink()
        self.prepare_migration()
        rejected = self.run_role('pkcs11-migration', openxpki_pkcs11_migration_operation='apply', openxpki_session_secret='changed-secret')
        self.assertNotEqual(rejected.returncode, 0)
        rejected = self.run_role('pkcs11-migration', openxpki_pkcs11_migration_operation='apply', fixture_history='unexpected write')
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(json.loads((self.data / 'deployment.json').read_text()), self.original_binding)
        self.assertTrue((self.data / 'pkcs11-migration-inhibit').exists())

    def test_failed_backend_start_keeps_committed_identity_inhibited_and_can_roll_back(self):
        self.prepare_migration()
        failed = self.run_role('pkcs11-migration', openxpki_pkcs11_migration_operation='apply', fixture_start_failure=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(json.loads((self.transaction / 'transaction.json').read_text())['phase'], 'committed')
        self.assertTrue((self.data / 'pkcs11-migration-inhibit').exists())
        self.assertTrue((self.data / 'pkcs11-migration-traffic-inhibit').exists())
        rolled = self.run_role('pkcs11-migration', openxpki_pkcs11_migration_operation='rollback',
                               fixture_serial='ORIGINAL123', **self.old_provider)
        self.assertEqual(rolled.returncode, 0, rolled.stdout + rolled.stderr)

    def assert_backup_publication_race(self, kind):
        failed = self.run_role('pkcs11-migration', fixture_backup_race=kind)
        self.assertNotEqual(failed.returncode, 0)
        destination = Path(self.inputs['openxpki_pkcs11_migration_backup_dest'])
        if kind == 'directory':
            self.assertTrue(destination.is_dir())
            self.assertEqual(list(destination.iterdir()), [])
        else:
            self.assertEqual(destination.read_text(), 'concurrent recovery custody')
        self.assertTrue((self.data / 'pkcs11-migration-inhibit').exists())
        self.assertEqual(list(destination.parent.glob('.pkcs11-backup-*')), [])

    def test_exclusive_backup_publication_preserves_concurrent_file(self):
        self.assert_backup_publication_race('file')

    def test_exclusive_backup_publication_rejects_concurrent_directory(self):
        self.assert_backup_publication_race('directory')

    def test_timer_activity_and_start_failure_leave_a_rollback_journal(self):
        rejected = self.run_role('pkcs11-migration', fixture_timer_status='inactive')
        self.assertNotEqual(rejected.returncode, 0)
        self.assertFalse((self.data / 'pkcs11-migration-inhibit').exists())
        # This rejected prepare has made no active-state change; use its explicit rollback.
        rolled = self.run_role('pkcs11-migration', openxpki_pkcs11_migration_operation='rollback',
                               fixture_serial='ORIGINAL123', **self.old_provider)
        self.assertEqual(rolled.returncode, 0, rolled.stdout + rolled.stderr)
