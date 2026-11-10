"""Execute native artifact gates; no host installer, accounts, services or mounts.

Set ANSIBLE_PLAYBOOK, INTAKE_CLAM_ROOT and INTAKE_CLAM_DATABASE for native runs.
An explicit INTAKE_TEST_OLD_DATABASE=1 allows the old upstream test CVD at age 10000
only in per-source fixtures. The unchanged production freshness/preflight gates
are tested separately. This limited EICAR fixture is not current-definition,
storage, systemd, network-policy or malware-coverage acceptance.
"""

import json
import os
import shutil
import stat
import unittest

from intake_pipeline_fixture import ArtifactPipelineFixture, EICAR, native_requirements, tree_bytes

if os.name != 'nt':
    import pwd


class NativeArtifactPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = native_requirements()
        if missing:
            raise unittest.SkipTest(missing)

    def setUp(self):
        self.fixture = ArtifactPipelineFixture(separate_users=os.geteuid() == 0)
        self.addCleanup(self.fixture.close)

    def accepted(self):
        source = self.fixture.source()
        result = self.fixture.run(source)
        scanner_logs = '\n'.join(path.read_text() for path in (self.fixture.data / 'quarantine').glob('*/scanner.log'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + scanner_logs)
        return source

    def rejected_after_previous(self, source, *, reason, stage, extra=None):
        before = tree_bytes(self.fixture.public)
        count = len(self.fixture.receipts())
        result = self.fixture.run(source, extra=extra)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(tree_bytes(self.fixture.public), before)
        receipts = self.fixture.receipts()
        self.assertEqual(len(receipts), count + 1, result.stdout + result.stderr)
        receipt = next(item for item in receipts if item not in getattr(self, '_previous_receipts', []))
        self._previous_receipts = receipts
        self.assertEqual(receipt['reason'], reason)
        self.assertEqual(receipt['stage'], stage)
        self.assertEqual(receipt['verdict'], 'quarantined')
        return receipt

    def test_verified_https_gpg_real_scan_publishes_read_only_and_reuses_immutable_version(self):
        source = self.accepted()
        latest = self.fixture.latest()
        version = self.fixture.public / latest['version']
        receipt = json.loads((version / 'receipt.json').read_text())
        self.assertEqual(receipt['verdict'], 'approved')
        self.assertEqual(receipt['publisher_fingerprint'], self.fixture.signer.fingerprint)
        self.assertIn('ClamAV', receipt['scanner_version'])
        self.assertEqual(json.loads((self.fixture.root / 'scan-result.json').read_text())['rc'], 0)
        self.assertEqual(receipt['definition_max_age_days'], self.fixture.max_age)
        self.assertEqual((version / 'content/fixture.txt').read_bytes(), b'known signed fixture artifact\n')
        self.assertEqual(latest['content_path'], f'/approved/fixture/{latest["version"]}/content/')
        before = tree_bytes(self.fixture.public)
        receipt_mtime = (version / 'receipt.json').stat().st_mtime_ns
        result = self.fixture.run(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(tree_bytes(self.fixture.public), before)
        self.assertEqual((version / 'receipt.json').stat().st_mtime_ns, receipt_mtime)
        self.assertEqual(len([path for path in self.fixture.public.iterdir() if path.is_dir()]), 1)
        for path in [version, *version.rglob('*'), self.fixture.public / 'latest.json']:
            self.assertEqual(stat.S_IMODE(path.stat().st_mode) & 0o222, 0, path)

    def test_wrong_checksum_and_validly_formed_wrong_signature_never_replace_previous(self):
        self.accepted()
        source = self.fixture.source(b'rejected checksum\n')
        source['sha256'] = '0' * 64
        self.rejected_after_previous(source, reason='publisher_or_integrity_failure', stage='verification')
        source = self.fixture.source(b'checksum correct, signature from another payload\n')
        other = self.fixture.artifacts / 'other.txt'
        other.write_text('different signed payload\n')
        self.fixture.signer.sign(other, self.fixture.artifacts / 'fixture.txt.sig')
        self.rejected_after_previous(source, reason='publisher_or_integrity_failure', stage='verification')

    def test_extra_undeclared_artifact_bytes_are_rejected_by_the_real_verifier(self):
        source = self.accepted()
        before = tree_bytes(self.fixture.public)
        payload = self.fixture.root / 'extra-content'
        payload.mkdir()
        for name in ('fixture.txt', 'fixture.txt.sig'):
            shutil.copyfile(self.fixture.artifacts / name, payload / name)
        (payload / 'undeclared.sh').write_text('echo unselected content\n')
        tasks = [
            {'ansible.builtin.include_tasks': 'tasks/seal.yml'},
            {'ansible.builtin.set_fact': {'intake_verification_path': '{{ intake_sealed.path }}/content'}},
            {'ansible.builtin.include_tasks': 'tasks/verify-artifact.yml'},
        ]
        result = self.fixture.run(source, tasks=tasks, extra={'intake_payload': str(payload)})
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Only the selected artifact', result.stdout)
        self.assertEqual(tree_bytes(self.fixture.public), before)

    def test_corrupt_retained_payload_cannot_be_reselected_or_silently_replaced(self):
        original_source = self.accepted()
        original_files = {name: (self.fixture.artifacts / name).read_bytes()
                          for name in ('fixture.txt', 'fixture.txt.sig')}
        original = self.fixture.latest()['version']
        result = self.fixture.run(self.fixture.source(b'newer independently approved content\n'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual(self.fixture.latest()['version'], original)
        retained = self.fixture.public / original / 'content/fixture.txt'
        retained.chmod(0o640)
        retained.write_bytes(b'storage corruption in retained history\n')
        retained.chmod(0o440)
        for name, content in original_files.items():
            (self.fixture.artifacts / name).write_bytes(content)
        self.rejected_after_previous(original_source, reason='publication_failed', stage='publication')

    def test_real_eicar_detection_quarantines_scanned_bytes_and_keeps_previous(self):
        self.accepted()
        receipt = self.rejected_after_previous(self.fixture.source(EICAR),
            reason='detection_or_scan_limit', stage='scanning')
        self.assertTrue(any('EICAR' in name for name in receipt['detections']), receipt)
        self.assertEqual(json.loads((self.fixture.root / 'scan-result.json').read_text())['rc'], 1)
        quarantined = self.fixture.data / 'quarantine'
        self.assertTrue(any(path.read_bytes() == EICAR for path in quarantined.glob('*/assessment/content/fixture.txt')))

    def test_https_outage_and_unsupported_raw_fail_before_publication(self):
        self.accepted()
        source = self.fixture.source(filename='disk.raw')
        self.rejected_after_previous(source, reason='publisher_or_integrity_failure', stage='verification')
        source = self.fixture.source()
        self.fixture.https.close()
        self.rejected_after_previous(source, reason='acquisition_failed', stage='acquisition')

    def test_missing_database_and_native_scanner_outage_fail_closed(self):
        self.accepted()
        empty = self.fixture.root / 'empty-db'
        empty.mkdir()
        self.rejected_after_previous(self.fixture.source(), reason='scanner_error_or_stale_definitions',
            stage='scanning', extra={'intake_clam_database_dir': str(empty)})
        self.rejected_after_previous(self.fixture.source(), reason='scanner_error_or_stale_definitions',
            stage='scanning', extra={'intake_clamscan_binary': str(self.fixture.root / 'absent-clamscan')})
        damaged = self.fixture.root / 'damaged-db'
        shutil.copytree(self.fixture.database, damaged)
        daily = next(path for path in (damaged / 'daily.cvd', damaged / 'daily.cld') if path.is_file())
        content = bytearray(daily.read_bytes())
        content[-1] ^= 0xff
        daily.write_bytes(content)
        self.rejected_after_previous(self.fixture.source(), reason='scanner_error_or_stale_definitions',
            stage='scanning', extra={'intake_clam_database_dir': str(damaged)})
        native = json.loads((self.fixture.root / 'scan-result.json').read_text())
        self.assertEqual(native['rc'], 2)
        self.assertRegex(native['stdout'] + native['stderr'], r'(?i)(database|CVD|signature)')

    def test_old_signed_database_is_rejected_at_real_default_freshness(self):
        old = os.environ.get('INTAKE_OLD_CLAM_DATABASE')
        if not old:
            self.skipTest('Set INTAKE_OLD_CLAM_DATABASE to an actually stale signed CVD fixture')
        self.accepted()
        stale = self.fixture.root / 'stale-db'
        shutil.copytree(old, stale)
        receipt = self.rejected_after_previous(self.fixture.source(), reason='scanner_error_or_stale_definitions',
            stage='scanning', extra={'intake_clam_database_dir': str(stale), 'intake_max_definition_age_days': 2})
        self.assertEqual(receipt['detections'], [])
        native = json.loads((self.fixture.root / 'scan-result.json').read_text())
        self.assertEqual(native['rc'], 2)
        self.assertRegex(native['stdout'] + native['stderr'], r'(?i)(older|outdated|stale)')

    def test_production_preflight_rejects_old_fixture_age_before_mount_actions(self):
        source = self.fixture.source()
        result = self.fixture.run(source, tasks=[{'ansible.builtin.include_tasks': 'tasks/preflight.yml'}],
                                  extra={'intake_max_definition_age_days': 10000})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('intake_max_definition_age_days | int <= 7', result.stdout)
        self.assertNotIn('Require the real data mount', result.stdout)

    @unittest.skipIf(os.environ.get('INTAKE_TEST_OLD_DATABASE') == '1',
                     'Current official daily definitions unavailable; old-CVD fixture does not qualify default freshness')
    def test_current_definitions_allow_the_unmodified_two_day_scan_gate(self):
        self.assertEqual(self.fixture.max_age, 2)
        self.accepted()

    def test_changed_postscan_bytes_fail_the_actual_final_publication_gate(self):
        self.accepted()
        # Exercise the unchanged gates separately so the test can inject publisher corruption
        # after a successful real scan, without editing or replacing the production tasks.
        payload = self.fixture.root / 'injected/content'
        payload.mkdir(parents=True)
        (payload / 'fixture.txt').write_text('sealed, scanned original\n')
        work = self.fixture.root / 'work'
        (work / 'scan').mkdir(parents=True)
        os.chmod(work, 0o751)
        os.chown(work / 'scan', pwd.getpwnam(self.fixture.scan_user).pw_uid,
                 pwd.getpwnam(self.fixture.scan_user).pw_gid)
        before = tree_bytes(self.fixture.public)
        tasks = [
            {'ansible.builtin.include_tasks': 'tasks/seal.yml'},
            {'ansible.builtin.set_fact': {'intake_verification_path': '{{ intake_sealed.path }}/content'}},
            {'ansible.builtin.include_tasks': 'tasks/scan.yml'},
            {'ansible.builtin.copy': {'content': 'changed after real scan\n',
                                     'dest': '{{ intake_verification_path }}/fixture.txt', 'mode': '0640'}},
            {'ansible.builtin.include_tasks': 'tasks/publish.yml'},
        ]
        result = self.fixture.run(self.fixture.source(), tasks=tasks, extra={
            'intake_payload': str(payload), 'intake_work': {'path': str(work)}, 'intake_policy_sha256': 'fixture-policy'})
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Assessed content changed', result.stdout)
        self.assertEqual(tree_bytes(self.fixture.public), before)

    def test_read_consumer_fetcher_and_scanner_cannot_modify_approved_or_read_private_incidents(self):
        if os.geteuid() != 0:
            self.skipTest('Root-only fixture uses existing nobody/daemon/www-data; creates no accounts')
        self.accepted()
        latest = self.fixture.latest()
        artifact = self.fixture.public / latest['version'] / 'content/fixture.txt'
        self.assertEqual(self.fixture.as_user(self.fixture.consumer, ['cat', str(artifact)]).returncode, 0)
        for user in (self.fixture.consumer, self.fixture.fetch_user, self.fixture.scan_user):
            attempt = self.fixture.as_user(user, ['python3', '-c', 'import sys;open(sys.argv[1],"ab").write(b"x")', str(artifact)])
            self.assertNotEqual(attempt.returncode, 0, user)
            worker = self.fixture.runtime / 'tasks/source.yml'
            attempt = self.fixture.as_user(user, ['python3', '-c', 'import sys;open(sys.argv[1],"ab").write(b"x")', str(worker)])
            self.assertNotEqual(attempt.returncode, 0, (user, 'worker code'))
            for private in ('quarantine', 'private', 'staging'):
                attempt = self.fixture.as_user(user, ['ls', str(self.fixture.data / private)])
                self.assertNotEqual(attempt.returncode, 0, (user, private))

    def test_retention_keeps_holds_unmarked_entries_and_approved_and_stays_bounded(self):
        self.accepted()
        private = self.fixture.data / 'quarantine'
        marker = {'schema': 1, 'verdict': 'quarantined'}
        for name in ('fixture-expired', 'fixture-held', 'unknown-entry'):
            (private / name).mkdir()
        for name in ('fixture-expired', 'fixture-held'):
            (private / name / 'intake-quarantine.json').write_text(json.dumps(marker))
        (private / 'fixture-held/.hold').touch()
        outside = self.fixture.root / 'outside'
        outside.mkdir()
        (outside / 'intake-quarantine.json').write_text(json.dumps(marker))
        (private / 'fixture-link').symlink_to(outside, target_is_directory=True)
        before = tree_bytes(self.fixture.public)
        # No clock/ctime mutation: select each candidate explicitly at expire.yml's boundary.
        for name in ('fixture-expired', 'fixture-held', 'unknown-entry'):
            result = self.fixture.run(self.fixture.source(), tasks=[{'ansible.builtin.include_tasks': 'tasks/expire.yml'}],
                                      extra={'intake_incident': {'path': str(private / name)}})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((private / 'fixture-expired').exists())
        self.assertTrue((private / 'fixture-held/.hold').exists())
        self.assertTrue((private / 'unknown-entry').exists())
        result = self.fixture.run(self.fixture.source(), tasks=[{'ansible.builtin.include_tasks': 'tasks/expire.yml'}],
                                  extra={'intake_incident': {'path': str(outside)}})
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((outside / 'intake-quarantine.json').exists())
        result = self.fixture.run(self.fixture.source(), tasks=[{'ansible.builtin.include_tasks': 'tasks/retention.yml'}])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((private / 'fixture-link').is_symlink())
        self.assertEqual(tree_bytes(self.fixture.public), before)


if __name__ == '__main__':
    unittest.main()
