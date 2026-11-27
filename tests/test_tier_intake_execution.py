"""Native retrieval evidence must match the model's scenarios, inputs and observable outcomes."""

from argparse import Namespace
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tier_repo_test_support import UPSTREAM
sys.path.insert(0, str(UPSTREAM / 'scripts/architecture'))
from intake_execution import EVIDENCE, assess, load_evidence, runtime_command
from intake_sources import GENERATED, trace_map
from software_intake import fingerprint


class IntakeExecutionContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = json.loads((UPSTREAM / GENERATED / 'model-index.json').read_text())['model']
        cls.report = json.loads((UPSTREAM / EVIDENCE).read_text())

    def test_observed_failure_and_verification_paths(self):
        for key, run in self.report['runs'].items():
            self.assertEqual(assess(self.model, key, run['raw']), run)
        runs = self.report['runs']
        hit = runs['RUN-hit-offline']
        self.assertFalse(hit['inputs']['sourceAvailable'])
        self.assertEqual(hit['values']['sourceRequests'], 0)
        self.assertEqual(hit['values']['verificationChecks'], 1)
        for key in ('RUN-source-failure', 'RUN-denied'):
            self.assertFalse(runs[key]['values']['accepted'])
            self.assertNotIn('H-verify', [e['message'] for e in runs[key]['events']])
        self.assertEqual(runs['RUN-denied']['values']['cacheLookups'], 0)
        for key in ('RUN-untrusted', 'RUN-cache-untrusted'):
            self.assertEqual(runs[key]['events'][-1]['message'], 'H-rejected')
            self.assertEqual(runs[key]['values']['verificationChecks'], 1)

    def test_missing_reordered_or_unknown_engine_steps_are_rejected(self):
        raw = self.report['runs']['RUN-miss']['raw']
        for mutation in ('missing', 'reordered', 'unknown'):
            altered = deepcopy(raw)
            lines = altered['checks'][0]['lines']
            at = next(i for i, line in enumerate(lines) if ': token 1@admission' in line)
            if mutation == 'missing':
                del lines[at]
            elif mutation == 'unknown':
                lines[at] = lines[at].replace('@admission', '@unmodeledAction')
            else:
                request = next(i for i, line in enumerate(lines) if ': token 1@request' in line)
                lines[at], lines[request] = lines[request], lines[at]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                assess(self.model, 'RUN-miss', altered)

    def test_input_output_and_incomplete_run_cannot_claim_success(self):
        for name in ('clientAllowed', 'accepted', 'outcome'):
            raw = deepcopy(self.report['runs']['RUN-miss']['raw'])
            item = next(v for v in raw['checks'][0]['values'] if v['name'] == name)
            item['value'] = '["denied"]' if name == 'outcome' else '[false]'
            with self.subTest(name=name), self.assertRaises(ValueError):
                assess(self.model, 'RUN-miss', raw)
        raw = deepcopy(self.report['runs']['RUN-miss']['raw'])
        raw['checks'][0]['lines'] = [x for x in raw['checks'][0]['lines'] if 'Final state: Completed' not in x]
        with self.assertRaisesRegex(ValueError, 'did not complete'):
            assess(self.model, 'RUN-miss', raw)

    def test_evidence_is_current_and_source_edits_make_it_stale(self):
        sources = fingerprint(UPSTREAM, trace_map(UPSTREAM))
        self.assertIsNotNone(load_evidence(UPSTREAM, self.model, sources)[0])
        changed = dict(sources)
        changed['architecture/models/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml'] = 'changed'
        result, message = load_evidence(UPSTREAM, self.model, changed)
        self.assertIsNone(result)
        self.assertIn('stale', message)

    @unittest.skipUnless(os.environ.get('SYSML_RUNTIME'), 'Native execution runtime is not configured')
    def test_native_admission_mutation_is_detected_by_expected_scenario(self):
        original = (UPSTREAM / EVIDENCE).read_bytes()
        with tempfile.TemporaryDirectory(prefix='intake-execution-', dir=UPSTREAM / '.tmp') as directory:
            source = Path(directory) / 'changed.sysml'
            text = (UPSTREAM / '.tmp/software-intake-execution/executable.sysml').read_text()
            self.assertIn('if admitted then lookup;', text)
            source.write_text(text.replace('if admitted then lookup;', 'if true then lookup;'), encoding='utf-8')
            run = self.model['execution']['runs']['RUN-denied']
            process = subprocess.run(runtime_command(Namespace()) + ['-quiet', '-json', '-trace', '-action',
                run['qualified_name'], source.relative_to(UPSTREAM).as_posix()], cwd=UPSTREAM,
                capture_output=True, text=True, encoding='utf-8', timeout=60)
            self.assertEqual(process.returncode, 0, process.stderr + process.stdout[:500])
            with self.assertRaisesRegex(ValueError, 'unexpected'):
                assess(self.model, 'RUN-denied', json.loads(process.stdout))
        self.assertEqual((UPSTREAM / EVIDENCE).read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
