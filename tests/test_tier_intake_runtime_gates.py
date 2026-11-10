"""Focused native runtime boundaries; no installer, services or live infrastructure."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from intake_pipeline_fixture import ArtifactPipelineFixture, RUNTIME, native_requirements, tree_bytes


@unittest.skipUnless(os.name != 'nt' and (os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')),
                     'Requires native Linux Ansible')
class NativeRuntimeGates(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='intake-gates-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.runtime = self.root / 'runtime'
        shutil.copytree(RUNTIME, self.runtime)

    def run_tasks(self, tasks, values):
        play = self.runtime / 'test.json'
        play.write_text(json.dumps([{
            'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
            'vars': {'ansible_python_interpreter': '/usr/bin/python3'} | values, 'tasks': tasks,
        }]))
        env = dict(os.environ, ANSIBLE_NOCOLOR='1')
        env.pop('ANSIBLE_CONFIG', None)
        return subprocess.run([os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook'),
                               '-i', 'localhost,', str(play)], cwd=self.runtime, env=env,
                              capture_output=True, text=True, timeout=60)

    def test_artifact_gate_requires_the_exact_declared_file_set(self):
        gate = yaml.safe_load((self.runtime / 'tasks/verify-artifact.yml').read_text())[0]
        source = {'name': 'fixture', 'filename': 'fixture.txt'}
        for signed in (False, True):
            selected = source | ({'signature_url': 'https://publisher.test/fixture.sig'} if signed else {})
            valid = {'fixture.txt': 'a' * 64} | ({'fixture.txt.sig': 'b' * 64} if signed else {})
            for manifest, accepted in ((valid, True), (valid | {'extra.sh': 'c' * 64}, False), ({}, False)):
                with self.subTest(signed=signed, manifest=manifest):
                    result = self.run_tasks([gate], {'intake_source': selected, 'intake_manifest': manifest})
                    self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)

    def test_native_stat_manifest_rejects_links_and_special_files(self):
        payload = self.root / 'payload'
        payload.mkdir()
        (payload / 'artifact').write_bytes(b'checked bytes')
        expected = {'artifact': hashlib.sha256(b'checked bytes').hexdigest()}
        tasks = [{'ansible.builtin.include_tasks': 'tasks/manifest.yml'},
                 {'ansible.builtin.assert': {'that': 'intake_inventory_manifest == expected'}}]
        result = self.run_tasks(tasks, {'intake_inventory_path': str(payload), 'expected': expected})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for kind in ('link', 'fifo'):
            bad = payload / kind
            bad.symlink_to(payload / 'artifact') if kind == 'link' else os.mkfifo(bad)
            result = self.run_tasks(tasks, {'intake_inventory_path': str(payload), 'expected': expected})
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            bad.unlink()
        for path in (self.runtime / 'tasks').glob('*.yml'):
            for task in yaml.safe_load(path.read_text()):
                self.assertNotIn('checksum_algorithm', task.get('ansible.builtin.find', {}), path)

    def test_curl_version_gate_rejects_unknown_or_unbounded_versions(self):
        gate = yaml.safe_load((self.runtime / 'tasks/curl.yml').read_text())[1]
        for version, accepted in (('7.88.1', False), ('8.3.0', False), ('8.4.0', True),
                                  ('8.12.1', True), ('unknown', False)):
            with self.subTest(version=version):
                result = self.run_tasks([gate], {'intake_curl_version': {'stdout': f'curl {version} libcurl'}})
                self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)
        result = self.run_tasks([{'ansible.builtin.include_tasks': 'tasks/curl.yml'}], {})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unsafe_source_policy_is_rejected_before_mount_or_quarantine(self):
        values = {'intake_data_dir': '/srv/intake', 'intake_max_definition_age_days': 2,
                  'intake_min_free_bytes': 1073741824, 'intake_quarantine_days': 14}
        for source in ({'name': '../escape', 'kind': 'artifact'}, {'name': 'fixture\n', 'kind': 'artifact'},
                       {'name': 'fixture', 'kind': '../adapter'}, {'kind': 'artifact'}):
            result = self.run_tasks([{'ansible.builtin.include_tasks': 'tasks/preflight.yml'}],
                                    values | {'intake_sources': [source]})
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('Every source needs a safe unique name', result.stdout)
            self.assertNotIn('TASK [Require the real data mount', result.stdout)

    def test_repeat_assessment_event_has_sanitized_current_scanner_evidence(self):
        event = yaml.safe_load((self.runtime / 'tasks/event.yml').read_text())[0]['community.general.syslogger']['msg']
        output = self.root / 'event.json'
        values = {'intake_source': {'name': 'fixture', 'kind': 'artifact',
                  'url': 'https://vendor.test/private/candidate?not-for-events'},
                  'intake_policy_sha256': 'a' * 64, 'intake_phase': 'publication',
                  'intake_verdict': 'approved', 'intake_committed': True, 'intake_published': True,
                  'intake_version': 'b' * 64, 'intake_max_definition_age_days': 2}
        version = 'ClamAV 1.5.4/10000/Mon Nov 10 12:00:00 2026'
        for scanner, expected in (({'stdout': version}, version), ({}, ''),
                                  ({'stdout': 'ClamAV /private/candidate https://private.test'}, '')):
            result = self.run_tasks([{'ansible.builtin.copy': {'dest': str(output), 'content': event}}],
                                    values | {'intake_scanner_version': scanner})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            record = json.loads(output.read_text())
            self.assertEqual(record['scanner.version'], expected)
            self.assertEqual(record['definition.max_age_days'], 2)
            self.assertNotIn('/private/', output.read_text())
            self.assertNotIn('https://', output.read_text())

    def test_receipt_preserves_native_repository_limits_without_private_fields(self):
        receipt_task = next(task for task in yaml.safe_load((self.runtime / 'tasks/publish.yml').read_text())
                            if task['name'] == 'Write the approval receipt beside the private payload')
        sealed = self.root / 'sealed'
        sealed.mkdir()
        evidence = {'kind': 'apt', 'packages_verified': 7, 'metadata_signature': False,
                    'architectures': ['amd64'], 'components': ['main'], 'release_valid_until': None,
                    'release_expiry_enforced': False, 'private_path': '/private/candidate',
                    'source_url': 'https://private.test/unapproved'}
        values = {'intake_source': {'name': 'fixture', 'url': 'https://vendor.test/repository'},
                  'intake_sealed': {'path': str(sealed)}, 'intake_owner': str(os.getuid()),
                  'intake_scan_group': str(os.getgid()), 'intake_version': 'b' * 64,
                  'intake_policy_sha256': 'a' * 64, 'intake_manifest': {'file': 'c' * 64},
                  'intake_scanner_version': {'stdout': 'ClamAV 1.5.4'}, 'intake_max_definition_age_days': 2}
        for kind, output in (('artifact', evidence), ('rpm', evidence | {'kind': 'rpm'}), ('apt', evidence), ('apt', None)):
            result = self.run_tasks([receipt_task], values | {
                'intake_source': values['intake_source'] | {'kind': kind},
                'intake_repository_verification': {'stdout': json.dumps(output)} if output else {},
            })
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads((sealed / 'receipt.json').read_text())
            if kind == 'artifact' or not output:
                self.assertNotIn('repository_verification', receipt)
            else:
                recorded = receipt['repository_verification']
                self.assertFalse(recorded['metadata_signature'])
                self.assertFalse(recorded['release_expiry_enforced'])
                self.assertEqual(recorded['packages_verified'], 7)
                self.assertNotIn('private_path', recorded)
                self.assertNotIn('source_url', recorded)


class NativePublicationRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = native_requirements()
        if missing:
            raise unittest.SkipTest(missing)
        if os.geteuid() != 0:
            raise unittest.SkipTest('Production root publisher semantics require the disposable root fixture')

    def setUp(self):
        self.fixture = ArtifactPipelineFixture(separate_users=True)
        self.addCleanup(self.fixture.close)

    def test_corrupted_retained_payload_is_not_reselected_or_replaced(self):
        source = self.fixture.source()
        result = self.fixture.run(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        artifact = self.fixture.public / self.fixture.latest()['version'] / 'content/fixture.txt'
        artifact.chmod(0o640)
        artifact.write_bytes(b'corrupt retained bytes')
        artifact.chmod(0o440)
        before = tree_bytes(self.fixture.public)
        result = self.fixture.run(source)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Retained payload differs', result.stdout)
        self.assertEqual(tree_bytes(self.fixture.public), before)
        self.assertEqual(self.fixture.receipts()[-1]['stage'], 'publication')

    def test_reporting_failure_after_selection_is_not_a_rejected_candidate(self):
        # Inject a native failure at the copied fixture's decision sink; AV/GPG stay real.
        (self.fixture.runtime / 'tasks/event.yml').write_text(yaml.safe_dump([{
            'ansible.builtin.fail': {'msg': 'Injected decision sink outage'},
            'when': "intake_verdict == 'approved'",
        }]))
        state = self.fixture.root / 'state.json'
        result = self.fixture.run(self.fixture.source(), tasks=[
            {'ansible.builtin.include_tasks': 'tasks/source.yml'},
            {'ansible.builtin.copy': {'dest': str(state), 'content':
                "{{ {'rejected': intake_failed_sources, 'reporting': intake_reporting_errors, "
                "'published': intake_published, 'selected': intake_committed} | to_json }}"}},
            {'ansible.builtin.assert': {'that': 'intake_reporting_errors | length == 0'}},
        ])
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(state.read_text()), {
            'rejected': [], 'reporting': ['fixture'], 'published': True, 'selected': True,
        })
        self.assertTrue((self.fixture.public / self.fixture.latest()['version'] / 'content/fixture.txt').is_file())
        self.assertEqual(self.fixture.receipts(), [])

    def test_discovery_write_error_after_rename_reconciles_the_selected_version(self):
        # Simulate the copy module reporting failure after writing its valid record.
        path = self.fixture.runtime / 'tasks/publish.yml'
        tasks = yaml.safe_load(path.read_text())
        selection = next(task for task in tasks if task['name'] == 'Atomically select the approved discovery record')
        selection['failed_when'] = True
        path.write_text(yaml.safe_dump(tasks, sort_keys=False))
        state = self.fixture.root / 'state.json'
        result = self.fixture.run(self.fixture.source(), tasks=[
            {'ansible.builtin.include_tasks': 'tasks/source.yml'},
            {'ansible.builtin.copy': {'dest': str(state), 'content':
                "{{ {'rejected': intake_failed_sources, 'reporting': intake_reporting_errors, "
                "'published': intake_published, 'selected': intake_committed} | to_json }}"}},
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(state.read_text()), {
            'rejected': [], 'reporting': ['fixture'], 'published': True, 'selected': True,
        })
        self.assertTrue((self.fixture.public / self.fixture.latest()['version'] / 'content/fixture.txt').is_file())
        self.assertEqual(self.fixture.receipts(), [])


if __name__ == '__main__':
    unittest.main()
