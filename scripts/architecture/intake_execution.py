"""Run native SysML actions; preserve engine evidence and compare it with modeled expectations."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
from intake_sources import MANIFEST, GENERATED, TOOLCHAIN, require, trace_map

EVIDENCE = Path('artifacts/architecture/evidence/software-intake/execution.json')
VIEW = Path('architecture/generated/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.svg')
GUIDE = 'docs/01-architecture/07-software-intake/05-retrieval-execution.md'


def runtime_command(args):
    runtime = getattr(args, 'runtime', None) or os.environ.get('SYSML_RUNTIME')
    wsl = getattr(args, 'wsl', None) or os.environ.get('SYSML_WSL')
    require(runtime, 'execute needs --runtime or SYSML_RUNTIME; see ' + GUIDE)
    return (['wsl', '--distribution', wsl, '--exec'] if wsl else []) + [runtime]


def scalar(value):
    """Decode the pinned engine's scalar value envelope, not source-language expressions."""
    parsed = json.loads(value)
    if isinstance(parsed, list):
        require(len(parsed) == 1, 'Execution output is not a scalar')
        parsed = parsed[0]
    require(type(parsed) in (bool, int, str), 'Unsupported execution output type')
    return parsed


def assess(model, key, raw):
    run = model['execution']['runs'][key]
    require(raw.get('exit') == 0 and not raw.get('errors'), key + ': native execution failed')
    require(not any(d['severity'] == 'error' for d in raw.get('diagnostics') or []), key + ': native model errors')
    checks = raw.get('checks') or []
    require(len(checks) == 1 and checks[0]['subject'] == run['qualified_name'], key + ': wrong execution subject')
    check = checks[0]
    require(any('Final state: Completed' in line for line in check.get('lines', [])), key + ': run did not complete')
    require(all(not b.get('reached') for r in check.get('results', []) for b in r.get('bounds', [])), key + ': runtime bound reached')
    observed = {v['name']: scalar(v['value']) for v in check['values']}
    for name, value in run['inputs'].items():
        require(type(observed.get(name)) is type(value) and observed[name] == value, key + ': input mismatch ' + name)
    for name, value in run['expected'].items():
        require(type(observed.get(name)) is type(value) and observed[name] == value, key + ': unexpected ' + name)
    by_name = {v['name']: (k, v) for k, v in model['execution']['actions'].items()}
    events, decisions = [], []
    for line in check['lines']:
        match = re.fullmatch(r'\[trace\] step (\d+): token \d+@(.+)', line)
        if not match:
            continue
        step, name = int(match[1]), match[2]
        if name in by_name:
            action, element = by_name[name]
            if element['message']:
                events.append({'step': step, 'action': action, 'message': element['message']})
            else:
                decisions.append({'step': step, 'action': action})
        else:
            require(name in ('start', 'done', 'assign verificationChecks', 'assign accepted'),
                    key + ': unrecognized native execution step ' + name)
    expected = model['scenarios'][run['scenario']]['messages']
    require([e['message'] for e in events] == expected, key + ': execution trace differs from the expected sequence')
    require(events, key + ': native engine emitted no recognized action trace')
    return {'inputs': run['inputs'], 'scenario': run['scenario'], 'values': observed,
            'events': events, 'decisions': decisions, 'raw': raw}


def load_evidence(root, model, sources):
    path = root / EVIDENCE
    if not path.is_file():
        return None, 'Not run yet. Execute the native model to create evidence.'
    report = json.loads(path.read_text(encoding='utf-8'))
    if report.get('sources') != sources:
        return None, 'Historical execution is stale for these sources. Run execute again.'
    require(set(report['runs']) == set(model['execution']['runs']), 'Execution evidence omits modeled experiments')
    for key, recorded in report['runs'].items():
        require(recorded == assess(model, key, recorded['raw']), 'Execution evidence projection drift: ' + key)
    return report, 'Native model execution; supplied availability and trust outcomes, no live traffic.'


def execute(root, args):
    from software_intake import run, fingerprint, expected_outputs
    from intake_sources import selected_inputs
    command = runtime_command(args)
    pin = json.loads((root / TOOLCHAIN).read_text())['execution']
    version = subprocess.run(command + ['-version'], capture_output=True, text=True, encoding='utf-8', timeout=30)
    require(version.returncode == 0 and version.stdout.splitlines()[0] == 'sysml ' + pin['version'] and
            pin['commit'] in version.stdout,
            'Use the pinned OpenSysML ' + pin['version'] + '; runtime was unavailable or had another version')
    model = run(root, 'build', args)
    manifest = json.loads((root / MANIFEST).read_text())
    require(set(manifest['execution_sources']) <= set(manifest['sources']), 'Executable sources must belong to the native model')
    work = root / '.tmp/software-intake-execution'
    work.mkdir(parents=True, exist_ok=True)
    source = work / 'executable.sysml'
    source.write_text('package ' + manifest['package'] + ' {\n' + '\n'.join(
        (root / p).read_text(encoding='utf-8') for p in manifest['execution_sources']) + '\n}\n', encoding='utf-8')
    results = {}
    for key, experiment in model['execution']['runs'].items():
        result = subprocess.run(command + ['-quiet', '-json', '-trace', '-action', experiment['qualified_name'],
            source.relative_to(root).as_posix()], cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=60)
        (work / (key + '.json')).write_text(result.stdout, encoding='utf-8')
        (work / (key + '.log')).write_text(result.stderr, encoding='utf-8')
        require(result.returncode == 0, key + ': native execution failed; inspect .tmp/software-intake-execution')
        results[key] = assess(model, key, json.loads(result.stdout))
        print(key + ': ' + results[key]['values']['outcome'])
    report = {'scope': 'Native SysML HTTP action execution; environment outcomes are inputs, not deployed observations',
        'executed_at': datetime.now(timezone.utc).isoformat(), 'engine': version.stdout.strip(),
        'sources': fingerprint(root, trace_map(root)), 'runs': results}
    # Publish evidence only after every experiment matches both its native expected values and sequence.
    outputs = expected_outputs(root, model, selected_inputs(root), trace_map(root), execution_report=report)
    outputs[EVIDENCE] = json.dumps(report, indent=2) + '\n'
    from svg_pages import validate_links
    validate_links(root, outputs)
    for path, value in outputs.items():
        (root / path).write_text(value, encoding='utf-8')
    print(f'PASS: {len(results)} native runs agree with their modeled scenarios. Open {VIEW.as_posix()}')
    return report
