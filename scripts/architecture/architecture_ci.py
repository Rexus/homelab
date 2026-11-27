"""The same model, reporter and requirement gate used locally and by GitLab CI."""

import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[2]
    output = root / '.tmp/architecture-ci'
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(root / 'tests') + os.pathsep + env.get('PYTHONPATH', '')
    jobs = [
        ('native-model', ['scripts/architecture/software_intake.py', 'validate']),
        ('reporter-tests', ['-m', 'unittest', '-v', 'test_tier_requirement_results',
                            'test_tier_model_artifacts', 'test_tier_view_catalog',
                            'test_tier_syson_compact', 'test_tier_syson_case_views',
                            'test_tier_requirement_documentation']),
        ('requirements', ['scripts/architecture/requirements.py', 'run']),
    ]
    results = {}
    for name, command in jobs:
        with (output / (name + '.log')).open('w', encoding='utf-8') as log:
            try:
                result = subprocess.run([sys.executable, '-B', *command], cwd=root, env=env,
                                        stdout=log, stderr=subprocess.STDOUT, timeout=2700)
                results[name] = {'exit_code': result.returncode}
            except (OSError, subprocess.TimeoutExpired) as error:
                results[name] = {'exit_code': 2, 'error': str(error)}
        (output / 'jobs.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
        print(name + ': ' + ('passed' if results[name]['exit_code'] == 0 else 'failed'), flush=True)
    return int(any(r['exit_code'] for r in results.values()))


if __name__ == '__main__':
    raise SystemExit(main())
