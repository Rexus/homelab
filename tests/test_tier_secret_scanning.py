"""Local and CI secret detection stays unprivileged and does not disclose matches."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml

from tier_repo_test_support import UPSTREAM


class SecretScanning(unittest.TestCase):
    def test_ci_scanner_has_no_privileged_runner_or_secret_outputs(self):
        job = yaml.safe_load((UPSTREAM / 'shared/ci/gitlab-secrets.yml.example').read_text())['secret-scan']
        self.assertFalse(job['allow_failure'])
        self.assertEqual(job['variables']['GIT_DEPTH'], '0')
        self.assertIn(':v8.30.1', job['image']['name'])
        self.assertNotIn('artifacts', job)
        self.assertNotIn('id_tokens', job)
        self.assertEqual(job['tags'], ['tier1-build'])
        self.assertIn('--redact', job['script'][0])

    @unittest.skipIf(os.name == 'nt', 'Native Bash/Git/CLI checks')
    def test_staged_history_and_artifact_scans_detect_without_disclosing(self):
        binary = os.environ.get('GITLEAKS_BINARY') or shutil.which('gitleaks')
        if not binary:
            self.skipTest('Set GITLEAKS_BINARY to run the pinned native scanner')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'tools').mkdir()
            (root / 'tools/gitleaks').symlink_to(binary)
            env = dict(os.environ, PATH=str(root / 'tools') + os.pathsep + os.environ['PATH'])
            run = lambda args: subprocess.run(args, cwd=root, env=env, capture_output=True, text=True)
            self.assertEqual(run(['git', 'init', '-q']).returncode, 0)
            token = 'ghp_' + 'A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0'
            (root / 'application.conf').write_text('access_token=' + token + '\n')
            self.assertEqual(run(['git', 'add', 'application.conf']).returncode, 0)
            helper = UPSTREAM / 'shared/scripts/check-secrets.sh'
            for mode in [('staged',), ('artifacts', str(root))]:
                result = run(['bash', str(helper), *mode])
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertNotIn(token, result.stdout + result.stderr)
            self.assertEqual(run(['git', '-c', 'user.name=fixture', '-c', 'user.email=fixture@example.invalid',
                                  '-c', 'commit.gpgsign=false', 'commit', '-qm', 'synthetic detector fixture']).returncode, 0)
            result = run(['bash', str(helper), 'history'])
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertNotIn(token, result.stdout + result.stderr)
