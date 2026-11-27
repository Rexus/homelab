"""Assess every native requirement against scoped, source-bound test attempts."""

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

PLAN = Path('artifacts/architecture/evidence/software-intake/assessment.json')
INDEX = Path('artifacts/architecture/generated/software-intake/model-index.json')
MANIFEST = Path('scripts/architecture/config/build/software-intake.json')
ORDER = ('failed', 'blocked', 'uncovered', 'stale', 'incomplete', 'missing', 'passed')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def text_hash(path):
    return hashlib.sha256(path.read_text(encoding='utf-8').encode()).hexdigest()


def load_context(root):
    plan = json.loads((root / PLAN).read_text(encoding='utf-8'))
    snapshot = json.loads((root / INDEX).read_text(encoding='utf-8'))
    model = snapshot['model']
    sources = json.loads((root / MANIFEST).read_text())['sources']
    stale = [p for p in sources if snapshot['sources'].get(p) != text_hash(root / p)]
    if stale:
        raise ValueError('Rebuild the native model before assessment: ' + ', '.join(stale))
    unknown = set(plan['cases']) - model['verification'].keys()
    if unknown:
        raise ValueError('Assessment refers to absent verification cases: ' + ', '.join(sorted(unknown)))
    for case, scopes in plan['cases'].items():
        if not scopes:
            raise ValueError('Verification case has no assessment scope: ' + case)
        for scope, binding in scopes.items():
            if scope not in plan['scopes'] or not binding.get('method') or not binding.get('claim'):
                raise ValueError('Incomplete assessment scope: ' + case)
            if set(binding['checks']) - plan['checks'].keys():
                raise ValueError('Unknown executable check: ' + case)
    bound = {c for scopes in plan['cases'].values() for b in scopes.values() for c in b['checks']}
    if bound != set(plan['checks']):
        raise ValueError('Every executable check must have a verification binding')
    return model, plan


def fingerprint(root, model, plan):
    paths = {PLAN.as_posix(), MANIFEST.as_posix()}
    paths.update(json.loads((root / MANIFEST).read_text())['sources'])
    for pattern in plan['inputs']:
        found = {p.relative_to(root).as_posix() for p in root.glob(pattern) if p.is_file()}
        if not found:
            raise ValueError('Evidence input matches no files: ' + pattern)
        paths.update(found)
    return {p: text_hash(root / p) for p in sorted(paths)}


def verdict(statuses):
    return next((s for s in ORDER if s in statuses), 'uncovered')


def assess(root, evidence, scope):
    model, plan = load_context(root)
    if scope not in plan['scopes'] and scope != 'all':
        raise ValueError('Unknown gate scope: ' + scope)
    current = fingerprint(root, model, plan)
    attempts = []
    for path in sorted(evidence.glob('*/run.json')):
        run = json.loads(path.read_text(encoding='utf-8'))
        if run.get('schema') != 1:
            raise ValueError('Unsupported evidence: ' + str(path))
        attempts.append((run['started_at'], path.parent.name, run))
    attempts.sort(key=lambda item: item[:2])
    latest = {}
    for _, folder, run in attempts:
        for key, result in run['checks'].items():
            latest[key] = (folder, run, result)
    checks = {}
    for key in plan['checks']:
        if key not in latest:
            checks[key] = {'status': 'missing', 'reason': 'No recorded attempt'}
            continue
        folder, run, result = latest[key]
        status = result['status']
        if status not in ('passed', 'failed', 'blocked'):
            raise ValueError('Invalid recorded verdict: ' + str(status))
        changed = sorted(p for p in current.keys() | run['sources'].keys()
                         if current.get(p) != run['sources'].get(p))
        checks[key] = {**result, 'status': 'stale' if changed else status,
                       'previous_status': status, 'changed_inputs': changed,
                       'attempt': folder, 'record': folder + '/run.json'}
    rows = []
    for requirement in sorted(model['requirements']):
        cases = sorted(k for k, v in model['verification'].items() if requirement in v['requirements'])
        if not cases:
            rows.append({'requirement': requirement, 'case': None, 'scope': 'unassigned',
                         'status': 'uncovered', 'checks': [], 'claim': 'No native verification case'})
        for case in cases:
            bindings = plan['cases'].get(case)
            if not bindings:
                rows.append({'requirement': requirement, 'case': case, 'scope': 'unassigned',
                             'status': 'uncovered', 'checks': [], 'claim': 'No assessment binding'})
            for layer, binding in (bindings or {}).items():
                statuses = [checks[k]['status'] for k in binding['checks']]
                if binding.get('gaps'):
                    statuses.append('incomplete')
                rows.append({'requirement': requirement, 'case': case, 'scope': layer,
                             'status': verdict(statuses) if statuses else 'missing',
                             **binding, 'acceptance': model['verification'][case]['acceptance']})
    requirements = {k: {'name': model['elements'][k]['name'],
                        'status': verdict([r['status'] for r in rows if r['requirement'] == k]),
                        'scopes': {s: verdict([r['status'] for r in rows if r['requirement'] == k and r['scope'] == s])
                                   for s in sorted({r['scope'] for r in rows if r['requirement'] == k})}}
                    for k in sorted(model['requirements'])}
    selected = [r for r in rows if scope == 'all' or r['scope'] in (scope, 'unassigned')]
    gate = bool(selected) and all(r['status'] == 'passed' for r in selected)
    return {'schema': 1, 'assessed_at': datetime.now(timezone.utc).isoformat(),
            'gate_scope': scope, 'gate_passed': gate, 'scopes': plan['scopes'],
            'requirements': requirements, 'obligations': rows, 'checks': checks,
            'source_fingerprints': current,
            'freshness': 'Current declared source/configuration inputs; tool versions belong to each recorded environment.'}


def write_reports(report, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / 'requirements.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    lines = ['# Requirement assessment', '',
             'Gate: **' + ('passed' if report['gate_passed'] else 'failed') + '** in **' + report['gate_scope'] + '** scope.', '',
             'A scoped pass does not establish deployed acceptance. Missing site evidence remains below.', '',
             '| Requirement | Overall | By scope |', '| --- | --- | --- |']
    for key, item in report['requirements'].items():
        lines.append(f"| {key} — {item['name']} | {item['status']} | " +
                     '; '.join(k + ': ' + v for k, v in item['scopes'].items()) + ' |')
    lines += ['', '| Requirement / case | Scope | Result | Claim / evidence checks |', '| --- | --- | --- | --- |']
    for row in report['obligations']:
        lines.append(f"| {row['requirement']} / {row['case'] or 'none'} | {row['scope']} | {row['status']} | " +
                     row['claim'].replace('|', '/') + '; ' + ', '.join(row['checks']) +
                     ('; Open: ' + '; '.join(row['gaps']) if row.get('gaps') else '') + ' |')
    lines += ['', '## Executed checks', '']
    for key, check in report['checks'].items():
        lines += [f"- {key}: **{check['status']}**; attempt `{check.get('attempt', 'none')}`; " +
                  check.get('reason', '').replace('\n', ' ')[:500]]
        if check.get('changed_inputs'):
            lines += ['  Changed: ' + ', '.join(check['changed_inputs'])]
    (output / 'requirements.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    # CI test names are stable requirement/case/scope identities, never display names alone.
    suite = ET.Element('testsuite', name='requirements', tests=str(len(report['obligations'])))
    failures = skipped = 0
    for row in report['obligations']:
        case = ET.SubElement(suite, 'testcase', classname=row['requirement'],
                             name=(row['case'] or 'uncovered') + '/' + row['scope'])
        detail = json.dumps(row, sort_keys=True)
        if row['status'] != 'passed':
            selected = report['gate_scope'] == 'all' or row['scope'] in (report['gate_scope'], 'unassigned')
            if selected:
                failures += 1
                ET.SubElement(case, 'failure', type=row['status'], message=row['status']).text = detail
            else:
                skipped += 1
                ET.SubElement(case, 'skipped', message=row['status'] + '; outside selected gate').text = detail
        ET.SubElement(case, 'system-out').text = detail
    suite.set('failures', str(failures))
    suite.set('skipped', str(skipped))
    ET.ElementTree(suite).write(output / 'requirements.xml', encoding='utf-8', xml_declaration=True)


def write_error(error, output):
    """Replace previous summary files so a failed assessment cannot leave a visible old pass."""
    output.mkdir(parents=True, exist_ok=True)
    (output / 'requirements.json').write_text(json.dumps({'gate_passed': False, 'error': str(error)}, indent=2) + '\n')
    (output / 'requirements.md').write_text('# Requirement assessment blocked\n\n' + str(error) + '\n', encoding='utf-8')
    suite = ET.Element('testsuite', name='requirements', tests='1', failures='1')
    case = ET.SubElement(suite, 'testcase', classname='assessment', name='model-and-evidence-inputs')
    ET.SubElement(case, 'failure', type='blocked', message=str(error)).text = str(error)
    ET.ElementTree(suite).write(output / 'requirements.xml', encoding='utf-8', xml_declaration=True)
