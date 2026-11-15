"""Exercise backend-aware application recovery and original-device boundaries."""

import json
import shutil
import unittest

import yaml

from openxpki_recovery_fixture import NATIVE, ROLE, RecoveryFixture
from tier_repo_test_support import TierRepositoryTestCase


class RecoveryContracts(TierRepositoryTestCase):
    def test_native_runtime_prerequisites_keep_acl_and_trust_as_separate_packages(self):
        task = yaml.safe_load((ROLE / 'tasks/packages.yml').read_text())[0]['ansible.builtin.apt']
        self.assertIn('ca-certificates', task['name'])
        self.assertIn('acl', task['name'])
        self.assertTrue(all(isinstance(name, str) and not any(c.isspace() for c in name)
                            for name in task['name']))
        self.assertEqual(task['policy_rc_d'], 101)

    def test_recovery_tasks_are_shipped_with_the_owning_tier(self):
        self.generate()
        for name in ('backup', 'restore', 'restore-stage', 'recovery-signer', 'recovery-key'):
            source = ROLE / f'tasks/{name}.yml'
            generated = self.root / f'verify-tier-0/ansible/roles/openxpki/tasks/{name}.yml'
            self.assertEqual(source.read_bytes(), generated.read_bytes())


@unittest.skipUnless(NATIVE, 'Requires native Linux Ansible, OpenSSL and age')
class NativeApplicationRecovery(RecoveryFixture, unittest.TestCase):
    def test_controller_transfer_verifies_manifest_before_copy_and_keeps_guest_files_private(self):
        self.prepare('pkcs11')
        self.backup_and_prepare_restore()
        source = self.root / 'controller-recovery'
        shutil.move(str(self.recovery), source)
        self.inputs['openxpki_restore_source_directory'] = str(source)
        for changes in ({'openxpki_restore_approved': False},
                        {'openxpki_restore_manifest_sha256': 'f' * 64}):
            result = self.run_role('restore', **changes)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(self.recovery.exists())
            self.assertFalse((self.data / 'restore-attempt.json').exists())
        self.recovery.mkdir()
        retained = self.recovery / 'existing-set'
        retained.write_text('retain this pre-staged set\n')
        rejected = self.run_role('restore')
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(retained.read_text(), 'retain this pre-staged set\n')
        retained.unlink()
        self.recovery.rmdir()
        rejected = self.run_role('restore', fixture_copy_source=str(self.root / 'disappeared-source'))
        self.assertNotEqual(rejected.returncode, 0)
        self.assertFalse(self.recovery.exists())
        self.assertFalse(self.imported.exists())
        self.assertEqual(list(self.recovery.parent.glob('.recovery-stage-*')), [])
        self.assertEqual((source / 'keys/cli.pem').read_text(), 'original-cli-custody\n')
        rejected = self.run_role('restore', fixture_concurrent_publication=True)
        self.assertNotEqual(rejected.returncode, 0)
        concurrent = json.loads((self.root / 'concurrent-destination.json').read_text())
        self.assertEqual(self.recovery.stat().st_ino, concurrent['inode'])
        self.assertEqual(list(self.recovery.iterdir()), [])
        self.assertEqual(list(self.recovery.parent.glob('.recovery-stage-*')), [])
        self.assertFalse((self.data / 'restore-attempt.json').exists())
        self.recovery.rmdir()
        result = self.run_role('restore')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for path in [self.recovery] + list(self.recovery.rglob('*')):
            self.assertEqual(path.stat().st_mode & 0o077, 0, str(path))
        self.assertEqual(list(self.recovery.parent.glob('.recovery-stage-*')), [])
        self.assertEqual((self.recovery / 'recovery.json').read_bytes(), (source / 'recovery.json').read_bytes())
        self.assertTrue(self.imported.is_file())

    def test_hardware_archive_and_clean_restore_preserve_application_state_without_a_software_key(self):
        self.prepare('pkcs11')
        artifact = self.data / 'configuration.tar.gz'
        approved = artifact.read_bytes()
        artifact.write_bytes(b'corrupted installation artifact\n')
        rejected = self.run_role('backup')
        self.assertNotEqual(rejected.returncode, 0)
        self.assertFalse(any(e['action'] in ('systemd_service', 'mariadb_db') for e in self.events()))
        artifact.write_bytes(approved)
        self.backup_and_prepare_restore()
        manifest = json.loads((self.recovery / 'recovery.json').read_text())
        self.assertEqual(manifest['format'], 2)
        self.assertEqual(manifest['signer_backend'], 'pkcs11')
        self.assertEqual(manifest['pkcs11_key_uri'], self.inputs['hsm_issuer_key'])
        self.assertFalse((self.recovery / 'keys/issuer.pem').exists())
        datavault = self.recovery / ('configuration/' + self.inputs['openxpki_configuration_sha256']
                                    + '/config.d/system/crypto.yaml')
        self.assertIn('original-datavault-secret', datavault.read_text())
        self.assertEqual((self.recovery / 'configuration.tar.gz').read_bytes(),
                         (self.data / 'configuration.tar.gz').read_bytes())
        self.assertEqual(self.archive.stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(self.backups.glob('recovery-*')), [])
        result = self.run_role('restore')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.data / 'keys/issuer.pem').exists())
        self.assertEqual(self.imported.read_bytes(), (self.recovery / 'database.sql').read_bytes())
        for relative in ('keys/cli.pem', 'identity/issuer.pem', 'public/issuer.crl'):
            self.assertEqual((self.data / relative).read_bytes(), (self.recovery / relative).read_bytes())
        events = self.events()
        probe = next(event for event in events if event['action'] == 'command' and
                     event['args']['argv'][:2] == ['openssl', 'pkey'])
        self.assertIn(self.inputs['hsm_issuer_key'], probe['args']['argv'])
        queries = next(i for i, event in enumerate(events) if event['action'] == 'mariadb_query')
        stopped = [event['args']['name'] for event in events[:queries]
                   if event['action'] == 'systemd_service' and event['args']['state'] == 'stopped']
        self.assertEqual(set(stopped), {'openxpki-crl.timer', 'apache2', 'openxpki-clientd', 'openxpki-serverd'})
        self.assertTrue(all(event['args']['state'] == 'stopped' for event in events
                            if event['action'] == 'systemd_service'))
        self.assertNotIn(self.inputs['hsm_issuer_pin'], result.stdout + result.stderr)
        repeated = self.run_role('restore')
        self.assertNotEqual(repeated.returncode, 0)
        self.assertTrue((self.data / 'restore-attempt.json').is_file())

    def test_original_encrypted_software_key_restores_with_a_legacy_manifest(self):
        self.prepare('software')
        self.backup_and_prepare_restore()
        manifest_path = self.recovery / 'recovery.json'
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest['signer_backend'], 'software')
        self.assertEqual(manifest['pkcs11_key_uri'], '')
        manifest['format'] = 1
        del manifest['signer_backend'], manifest['pkcs11_key_uri']
        manifest_path.write_text(json.dumps(manifest))
        (self.recovery / 'configuration.tar.gz').unlink()
        self.authorize_manifest()
        rejected = self.run_role('restore', openxpki_signer_password='wrong-' + 'x' * 40)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertFalse(self.imported.exists())
        result = self.run_role('restore')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.data / 'keys/issuer.pem').read_bytes(),
                         (self.recovery / 'keys/issuer.pem').read_bytes())
        self.assertTrue(self.imported.is_file())

    def test_hardware_recovery_rejects_new_serial_different_key_uri_and_wrong_public_key(self):
        self.prepare('pkcs11')
        self.backup_and_prepare_restore()
        for changes in (
            {'fixture_serial': 'REPLACEMENT456'},
            {'hsm_provider_expected_serial': 'REPLACEMENT456',
             'hsm_issuer_key': self.inputs['hsm_issuer_key'].replace('ORIGINAL123', 'REPLACEMENT456')},
            {'hsm_issuer_key': self.inputs['hsm_issuer_key'].replace('%01', '%02')},
            {'fixture_public_key': 'different-public-key'},
            {'hsm_provider_custody_ready': False},
            {'hsm_issuer_pin': '648219'},
        ):
            with self.subTest(changes=changes):
                self.events_path.write_text('')
                result = self.run_role('restore', **changes)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertFalse(self.imported.exists())
                self.assertFalse((self.data / 'restore-attempt.json').exists())
                self.assertFalse(any(e['action'] == 'mariadb_query' for e in self.events()))
        self.events_path.write_text('')
        (self.data / 'identity/issuer.pem').write_bytes((self.recovery / 'identity/issuer.pem').read_bytes())
        result = self.run_role('backup', openxpki_activate_runtime=True, fixture_public_key='different-public-key')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(e['action'] == 'mariadb_db' for e in self.events()))

    def test_manifest_binding_history_and_failed_import_keep_restore_nonrepeatable(self):
        self.prepare('pkcs11')
        self.backup_and_prepare_restore()
        manifest_path = self.recovery / 'recovery.json'
        original = manifest_path.read_bytes()
        for field, value in (('signer_backend', 'software'), ('pkcs11_key_uri', 'pkcs11:serial=REPLACEMENT456;id=%01;type=private'),
                             ('issuer_fingerprint', '00:' * 31 + '00'), ('configuration_sha256', 'b' * 64), ('format', 1)):
            manifest = json.loads(original)
            manifest[field] = value
            manifest_path.write_text(json.dumps(manifest))
            self.authorize_manifest()
            result = self.run_role('restore')
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((self.data / 'restore-attempt.json').exists())
        manifest_path.write_bytes(original)
        self.authorize_manifest()
        for changes in ({'fixture_certificates': 1}, {'fixture_workflows': 1},
                        {'openxpki_restore_manifest_sha256': 'f' * 64},
                        {'openxpki_database_password': 'different-' + 'x' * 40}):
            result = self.run_role('restore', **changes)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(self.imported.exists())
            self.assertFalse((self.data / 'restore-attempt.json').exists())
        result = self.run_role('restore', fixture_import_failure=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.data / 'restore-attempt.json').is_file())
        self.assertFalse(self.imported.exists())
        repeated = self.run_role('restore')
        self.assertNotEqual(repeated.returncode, 0)
        self.assertFalse(self.imported.exists())
