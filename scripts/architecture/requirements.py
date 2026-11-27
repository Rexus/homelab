"""Execute scoped checks, retain attempts, and gate requirements from native model identities."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import uuid

from requirement_results import assess, fingerprint, load_context, write_reports, write_error


def save(path, value):
    temporary = path.with_suffix('.pending')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def environment():
    tools = {}
    for name, binary, flag in [('squid', os.environ.get('HOMELAB_SQUID'), '-v'),
                               ('apt', shutil.which('apt-get'), '--version'),
                               ('gpg', shutil.which('gpg'), '--version'),
                               ('ansible', os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook'), '--version')]:
        try:
            process = subprocess.run([binary, flag], capture_output=True, text=True, timeout=20) if binary else None
            tools[name] = process.stdout.splitlines()[0] if process and process.stdout else 'unavailable'
        except (OSError, subprocess.TimeoutExpired):
            tools[name] = 'unavailable'
    return {'platform': platform.platform(), 'python': platform.python_version(), 'tools': tools}


def execute(root, evidence, scope, only=None):
    model, plan = load_context(root)
    selected = {c for bindings in plan['cases'].values() for s, b in bindings.items()
                if scope == 'all' or s == scope for c in b['checks']}
    if only:
        if not set(only) <= selected:
            raise ValueError('Selected check is outside the declared scope')
        selected = set(only)
    if not selected:
        raise ValueError('No executable checks in this scope')
    started = datetime.now(timezone.utc).isoformat()
    folder = evidence / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    record = {'schema': 1, 'started_at': started, 'scope': scope, 'sources': fingerprint(root, model, plan),
              'environment': environment(), 'checks': {k: {'status': 'blocked', 'reason': 'Attempt started; no completed result'}
                                                       for k in sorted(selected)}}
    save(folder / 'run.json', record)
    for key in sorted(selected):
        spec = plan['checks'][key]
        output = folder / (key + '.json')
        env = os.environ.copy()
        env['INTAKE_IMPLEMENTATION_REPORT'] = str(folder / 'implementation.json')
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        with (folder / (key + '.log')).open('w', encoding='utf-8') as log:
            try:
                proc = subprocess.Popen([sys.executable, '-B', str(root / 'scripts/architecture/requirement_runner.py'),
                                         spec['selector'], str(output)], cwd=root, env=env, stdout=log,
                                        stderr=subprocess.STDOUT, start_new_session=os.name != 'nt')
                try:
                    proc.wait(timeout=spec.get('timeout', 600))
                except subprocess.TimeoutExpired:
                    # Fixture services belong to this bounded attempt; do not leave descendants alive.
                    if os.name != 'nt':
                        os.killpg(proc.pid, signal.SIGKILL)
                    else:
                        proc.kill()
                    proc.wait()
                    raise
                result = json.loads(output.read_text()) if output.exists() else {
                    'status': 'blocked', 'reason': 'Runner exited without completed assessment: ' + str(proc.returncode)}
                if proc.returncode and result['status'] == 'passed':
                    result = {'status': 'blocked', 'reason': 'Runner exit contradicts recorded pass'}
            except (OSError, subprocess.TimeoutExpired) as error:
                result = {'status': 'blocked', 'reason': str(error)}
        record['checks'][key] = {**result, 'log': key + '.log', 'finished_at': datetime.now(timezone.utc).isoformat()}
        save(folder / 'run.json', record)
        print(key + ': ' + result['status'], flush=True)
    # Edits during execution invalidate the entire attempt; never bind a mixed run to new input hashes.
    if record['sources'] != fingerprint(root, model, plan):
        for result in record['checks'].values():
            result.update(status='blocked', reason='Inputs changed during execution; rerun from stable sources')
    record['finished_at'] = datetime.now(timezone.utc).isoformat()
    save(folder / 'run.json', record)
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('run', 'report', 'gate'))
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--evidence', type=Path, default=Path('.tmp/requirement-evidence/runs'))
    parser.add_argument('--output', type=Path, default=Path('.tmp/requirement-evidence/report'))
    parser.add_argument('--scope', default='isolated')
    parser.add_argument('--only', action='append', help='Run a bound check; report/gate still assess the entire scope')
    args = parser.parse_args()
    root = args.root.resolve()
    evidence = (root / args.evidence).resolve()
    output = (root / args.output).resolve()
    try:
        if args.command == 'run':
            execute(root, evidence, args.scope, args.only)
        report = assess(root, evidence, args.scope)
        write_reports(report, output)
        print('Requirement gate ' + ('passed' if report['gate_passed'] else 'failed') + ': ' + str(output / 'requirements.md'))
        return 0 if args.command == 'report' or report['gate_passed'] else 1
    except (OSError, ValueError, KeyError) as error:
        write_error(error, output)
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
