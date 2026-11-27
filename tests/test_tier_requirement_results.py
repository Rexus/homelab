"""Evidence never substitutes trace coverage or an older pass for a current attempt."""

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/architecture'))
from requirement_results import PLAN, INDEX, MANIFEST, assess, fingerprint, text_hash, write_reports, write_error
from requirement_runner import run


class RequirementResults(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.evidence = self.root / 'runs'
        self.model = {'requirements': {'REQ-a': {}, 'REQ-site': {}},
                      'elements': {'REQ-a': {'name': 'A'}, 'REQ-site': {'name': 'Site'}},
                      'verification': {'VC-a': {'requirements': ['REQ-a'], 'acceptance': 'Actual assertion'},
                                       'VC-site': {'requirements': ['REQ-site'], 'acceptance': 'Observe site'}}}
        self.plan = {'inputs': ['implementation.txt'], 'scopes': {'isolated': 'fixture', 'site': 'deployed'},
                     'checks': {'check-a': {'selector': 'test_fixture.Example.test_a'}},
                     'cases': {'VC-a': {'isolated': {'checks': ['check-a'], 'method': 'test', 'claim': 'Fixture only'}},
                               'VC-site': {'site': {'checks': [], 'method': 'demonstration', 'claim': 'Site evidence needed'}}}}
        self.write('model.sysml', 'native source')
        self.write('implementation.txt', 'implementation')
        self.write(MANIFEST, {'sources': ['model.sysml']})
        self.refresh()

    def write(self, path, value):
        path = self.root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if isinstance(value, dict) else value, encoding='utf-8')

    def refresh(self):
        self.write(PLAN, self.plan)
        self.write(INDEX, {'model': self.model, 'sources': {'model.sysml': text_hash(self.root / 'model.sysml')}})

    def attempt(self, number=1, status='passed'):
        self.write(f'runs/{number}/run.json', {'schema': 1, 'started_at': str(number),
                    'sources': fingerprint(self.root, self.model, self.plan), 'checks': {'check-a': {'status': status}}})

    def report(self, scope='isolated'):
        return assess(self.root, self.evidence, scope)

    def test_missing_evidence_fails_and_site_is_visible(self):
        report = self.report()
        self.assertFalse(report['gate_passed'])
        self.assertEqual(report['requirements']['REQ-a']['status'], 'missing')
        self.assertEqual(report['requirements']['REQ-site']['status'], 'missing')

    def test_current_pass_is_scoped_and_all_scope_still_fails(self):
        self.attempt()
        self.assertTrue(self.report()['gate_passed'])
        self.assertFalse(self.report('all')['gate_passed'])

    def test_passing_checks_cannot_hide_known_acceptance_coverage_gaps(self):
        self.plan['cases']['VC-a']['isolated']['gaps'] = ['Connection refusal not exercised']
        self.refresh()
        self.attempt()
        report = self.report()
        self.assertEqual(report['checks']['check-a']['status'], 'passed')
        self.assertEqual(report['requirements']['REQ-a']['status'], 'incomplete')
        self.assertFalse(report['gate_passed'])

    def test_latest_failure_does_not_reuse_older_pass(self):
        self.attempt()
        self.attempt(2, 'failed')
        self.assertEqual(self.report()['checks']['check-a']['status'], 'failed')
        self.assertFalse(self.report()['gate_passed'])

    def test_interrupted_attempt_blocks_older_pass(self):
        self.attempt()
        self.attempt(2, 'blocked')
        self.assertEqual(self.report()['checks']['check-a']['status'], 'blocked')

    def test_changed_implementation_is_stale_until_rerun(self):
        self.attempt()
        self.write('implementation.txt', 'changed')
        self.assertEqual(self.report()['checks']['check-a']['status'], 'stale')
        self.assertFalse(self.report()['gate_passed'])
        self.attempt(2)
        self.assertTrue(self.report()['gate_passed'])

    def test_rebuilding_views_does_not_renew_or_invalidate_evidence(self):
        self.attempt()
        self.write('architecture/generated/example.svg', '<svg/>')
        self.assertTrue(self.report()['gate_passed'])
        self.write('implementation.txt', 'changed')
        self.refresh()
        self.assertEqual(self.report()['checks']['check-a']['status'], 'stale')

    def test_new_requirement_or_case_fails_even_without_test_selection(self):
        self.attempt()
        self.model['requirements']['REQ-new'] = {}
        self.model['elements']['REQ-new'] = {'name': 'New need'}
        self.refresh()
        self.assertEqual(self.report()['requirements']['REQ-new']['status'], 'uncovered')
        self.assertFalse(self.report()['gate_passed'])
        self.model['verification']['VC-new'] = {'requirements': ['REQ-new'], 'acceptance': 'New criterion'}
        self.refresh()
        self.assertEqual(self.report()['requirements']['REQ-new']['status'], 'uncovered')

    def test_changed_native_source_requires_native_rebuild(self):
        self.write('model.sysml', 'changed source')
        with self.assertRaisesRegex(ValueError, 'Rebuild the native model'):
            self.report()

    def test_environment_contract_change_stales_evidence(self):
        self.attempt()
        self.plan['scopes']['isolated'] = 'Changed tool/configuration contract'
        self.refresh()
        self.assertEqual(self.report()['checks']['check-a']['status'], 'stale')

    def test_junit_retains_scope_gaps_and_gate_failure(self):
        output = self.root / 'report'
        write_reports(self.report(), output)
        suite = ET.parse(output / 'requirements.xml').getroot()
        self.assertEqual(suite.get('failures'), '1')
        self.assertEqual(suite.get('skipped'), '1')
        self.assertEqual(len(suite.findall('testcase')), 2)

    def test_assessment_error_replaces_old_pass_summary(self):
        self.attempt()
        output = self.root / 'report'
        write_reports(self.report(), output)
        write_error(ValueError('invalid native baseline'), output)
        self.assertFalse(json.loads((output / 'requirements.json').read_text())['gate_passed'])
        self.assertEqual(ET.parse(output / 'requirements.xml').getroot().get('failures'), '1')

    def test_runner_handles_subtests_skip_expected_failure_and_setup_error(self):
        from contextlib import redirect_stderr
        module = self.root / 'evidence_fixture.py'
        module.write_text('''import unittest
class Cases(unittest.TestCase):
    def test_pass(self): self.assertTrue(True)
    def test_sub(self):
        with self.subTest(criterion="denial"): self.assertEqual(403, 200)
    @unittest.skip("missing product")
    def test_skip(self): pass
    @unittest.expectedFailure
    def test_expected(self): self.fail("known failure")
class Broken(unittest.TestCase):
    @classmethod
    def setUpClass(cls): raise RuntimeError("setup failed")
    def test_a(self): pass
''')
        sys.path.insert(0, str(self.root))
        self.addCleanup(sys.path.remove, str(self.root))
        self.addCleanup(sys.modules.pop, 'evidence_fixture', None)
        for selector, expected in [('Cases.test_pass', 'passed'), ('Cases.test_sub', 'failed'),
                                   ('Cases.test_skip', 'blocked'), ('Cases.test_expected', 'blocked'),
                                   ('Broken.test_a', 'failed')]:
            with self.subTest(selector=selector), redirect_stderr(io.StringIO()):
                self.assertEqual(run('evidence_fixture.' + selector)['status'], expected)


if __name__ == '__main__':
    unittest.main()
