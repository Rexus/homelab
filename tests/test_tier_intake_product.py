"""Compare modeled HTTP retrieval outcomes with real Squid and APT, on loopback only."""

from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest

from apt_repository_fixture import AptRepository, command
from test_tier_cache_policy import SQUID, squid_fixture, request
from tier_repo_test_support import UPSTREAM

sys.path.insert(0, str(UPSTREAM / 'scripts/architecture'))
from intake_product import compare, product_sources


def log_records(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


@unittest.skipUnless(os.name != 'nt' and SQUID and Path(SQUID).is_file()
                    and all(shutil.which(x) for x in ('apt-get', 'gpg', 'gpgconf', 'dpkg-deb')),
                    'Requires Linux/WSL, Squid, APT, GnuPG and dpkg-deb')
class NativeIntakeScenarios(unittest.TestCase):
    def test_signed_package_retrieval_matches_model(self):
        snapshot = json.loads((UPSTREAM / 'architecture/generated/software-intake/model-index.json').read_text())
        model = snapshot['model']
        runs = model['execution']['runs']
        for path, digest in product_sources(UPSTREAM).items():
            if path.endswith('.sysml'):
                self.assertEqual(snapshot['sources'][path], digest, 'Rebuild the model before testing: ' + path)
        report = {'scope': 'Isolated Squid/APT implementation comparison; no deployed network or package installation',
            'executed_at': datetime.now(timezone.utc).isoformat(), 'sources': product_sources(UPSTREAM),
            'tools': {name: command([binary, flag]).stdout.splitlines()[0] for name, binary, flag in
                      (('squid', SQUID, '-v'), ('apt', 'apt-get', '--version'), ('gpg', 'gpg', '--version'))},
            'runs': {}}
        with ExitStack() as cleanup:
            temporary = cleanup.enter_context(tempfile.TemporaryDirectory(prefix='intake-product-'))
            repo = AptRepository(Path(temporary), UPSTREAM, runs)
            cleanup.callback(repo.close)
            control = {}
            with squid_fixture(UPSTREAM / 'tier-2/ansible/roles/cache_proxy',
                               origin_handler=repo.handler(), control=control) as (port, _, log):
                client = repo.client(port)
                update = repo.apt(client, 'update')
                self.assertEqual(update.returncode, 0, update.stdout + update.stderr)
                unknown = repo.apt(repo.client(port, name='unknown-key', trusted=False), 'update')
                self.assertNotEqual(unknown.returncode, 0, unknown.stdout + unknown.stderr)
                self.assertIn('NO_PUBKEY', unknown.stdout + unknown.stderr)
                report['metadata'] = {'trusted_exit': update.returncode, 'unknown_key_exit': unknown.returncode,
                    'unknown_key_rejected': 'NO_PUBKEY' in unknown.stdout + unknown.stderr}
                domains = ['repo.example.test']
                for key, run in runs.items():
                    inputs = run['inputs']
                    # This fixture refines the six checked single-object experiments. No port/client-policy variant is implied.
                    self.assertTrue(inputs['clientAllowed'] and inputs['portAllowed'])
                    name, path = repo.packages[key]
                    target = 'http://repo.example.test' + path
                    repo.available, repo.corrupt = True, not inputs['contentVerified']
                    control['set_domains'](domains)
                    self.wait_policy(port, allowed=True)
                    warm = None
                    if inputs['eligibleFreshResponse']:
                        warm = request(port, target)
                        self.assertEqual(warm[0], 200)
                        # Confirm a real cache hit before disabling the source.
                        at = len(repo.calls)
                        self.assertEqual(request(port, target), warm)
                        self.assertEqual(len(repo.calls), at)
                    if not inputs['destinationAllowed']:
                        control['set_domains'](['unknown.example.test'])
                        self.wait_policy(port, allowed=False)
                    repo.available = inputs['sourceAvailable']
                    # Synchronize logging before taking the measured request's baseline.
                    time.sleep(0.15)
                    before, log_start = len(repo.calls), len(log_records(log))
                    result = repo.apt(client, 'download', name, folder=key)
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline and len(log_records(log)) == log_start:
                        time.sleep(0.05)
                    records = log_records(log)[log_start:]
                    self.assertTrue(records, result.stdout + result.stderr)
                    source_calls = repo.calls[before:]
                    self.assertTrue(all(c['path'] == path for c in source_calls), source_calls)
                    output = result.stdout + result.stderr
                    rejected = 'Hash Sum mismatch' in output
                    accepted = result.returncode == 0
                    status = records[-1]['http.response.status_code']
                    outcome = ('accepted' if accepted else 'verification-failed' if rejected else
                               'denied' if status == 403 else 'source-unavailable' if status >= 500 else 'unexpected-error')
                    files = list((client[0] / 'downloads' / key).glob('*.deb'))
                    digest = hashlib.sha256(files[0].read_bytes()).hexdigest() if accepted and len(files) == 1 else None
                    expected_digest = hashlib.sha256(repo.files[path]).hexdigest()
                    if accepted:
                        self.assertEqual(digest, expected_digest)
                    report['runs'][key] = {'scenario': run['scenario'], 'name': run['name'], 'inputs': inputs,
                        'expected': run['expected'], 'observed': {'accepted': accepted, 'outcome': outcome,
                            'sourceRequests': len(source_calls), 'verificationChecks': int(accepted or rejected)},
                        'http_status': status, 'proxy_results': [r['proxy.result'] for r in records],
                        'source_calls': source_calls, 'apt_exit': result.returncode, 'hash_mismatch': rejected,
                        'download_sha256': digest, 'expected_sha256': expected_digest,
                        'cache_prepared': warm is not None,
                        'stdout': result.stdout.replace(temporary, '<fixture>'),
                        'stderr': result.stderr.replace(temporary, '<fixture>')}
                    print(key + ': ' + outcome + ' / ' + ', '.join(report['runs'][key]['proxy_results']), flush=True)
        report['differences'] = compare(model, report)
        target = os.environ.get('INTAKE_IMPLEMENTATION_REPORT')
        if target:
            path = Path(target)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2) + '\n')
        self.assertEqual(report['differences'], [], json.dumps(report['differences'], indent=2))

    def wait_policy(self, port, allowed):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                status, _ = request(port, 'http://repo.example.test/admission-probe')
            except OSError:
                time.sleep(0.1)
                continue
            if (status != 403) == allowed:
                return
            time.sleep(0.1)
        self.fail('Squid did not apply the selected destination policy')


if __name__ == '__main__':
    unittest.main()
