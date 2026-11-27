"""Run exactly one bound unittest method using its normal fixtures and result hooks."""

import argparse
import json
from pathlib import Path
import sys
import unittest


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subtests = []

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        self.subtests.append({'id': subtest.id(), 'status': 'failed' if err else 'passed',
                             'detail': self._exc_info_to_string(err, test) if err else ''})


def run(selector):
    suite = unittest.defaultTestLoader.loadTestsFromName(selector)
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(suite)
    status = 'passed'
    if result.failures or result.errors or result.unexpectedSuccesses:
        status = 'failed'
    elif count != 1 or result.testsRun != 1 or result.skipped or result.expectedFailures:
        status = 'blocked'
    return {'status': status, 'selector': selector, 'tests_run': result.testsRun,
            'reason': 'unittest assertions and fixtures completed' if status == 'passed' else
                      'Check failed, errored, skipped, expected-failed or did not execute exactly one method; inspect log',
            'failures': [(t.id(), text) for t, text in result.failures + result.errors],
            'skips': [(t.id(), text) for t, text in result.skipped], 'subtests': result.subtests}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selector')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tests'))
    assessment = run(args.selector)
    args.output.write_text(json.dumps(assessment, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(0 if assessment['status'] == 'passed' else 1)
