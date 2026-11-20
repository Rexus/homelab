"""The product comparison must expose differences and historical evidence honestly."""
from copy import deepcopy
import json
import unittest
from intake_model_fixture import IntakeModelFixture
from intake_product import EVIDENCE, VIEW, compare, outputs


class IntakeComparison(IntakeModelFixture):
    def test_measured_cases_match_the_native_expectations(self):
        report = json.loads((self.root / EVIDENCE).read_text())
        self.assertEqual(compare(self.model, report), [])
        self.assertTrue(report['metadata']['unknown_key_rejected'])
        runs = report['runs']
        for key in ('RUN-hit-offline', 'RUN-cache-untrusted'):
            self.assertEqual(runs[key]['observed']['sourceRequests'], 0)
            self.assertTrue(any('HIT' in r for r in runs[key]['proxy_results']))
        self.assertTrue(runs['RUN-cache-untrusted']['hash_mismatch'])
        self.assertTrue(runs['RUN-untrusted']['hash_mismatch'])
        self.assertEqual(runs['RUN-denied']['http_status'], 403)
        self.assertEqual(runs['RUN-source-failure']['http_status'], 503)

    def test_changed_expectation_and_missing_case_are_differences(self):
        report = json.loads((self.root / EVIDENCE).read_text())
        model = deepcopy(self.model)
        model['execution']['runs']['RUN-miss']['expected']['outcome'] = 'denied'
        self.assertTrue(any('outcome' in d for d in compare(model, report)))
        del report['runs']['RUN-denied']
        self.assertTrue(any('cover' in d for d in compare(self.model, report)))

    def test_stale_evidence_does_not_present_current_product_results(self):
        path = self.root / EVIDENCE
        report = json.loads(path.read_text())
        report['sources']['tests/test_tier_intake_product.py'] = 'changed'
        path.write_text(json.dumps(report))
        result = outputs(self.root, self.model)[VIEW]
        self.assertIn('No current implementation result', result)
        self.assertNotIn('Squid: cache hit', result)
