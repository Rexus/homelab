"""Compare observable product outcomes with the same native model experiments."""

import hashlib
import json
from pathlib import Path

EVIDENCE = Path('architecture/test/software-intake/implementation.json')
VIEW = Path('architecture/views/software-intake/implementation.svg')
GUIDE = 'docs/01-architecture/07-software-intake/06-implementation-comparison.md'
INPUTS = (
    'architecture/use-cases/software-intake/use-cases.sysml',
    'architecture/functions/software-intake/behavior.sysml',
    'architecture/functions/software-intake/admission-logic.sysml',
    'architecture/functions/software-intake/retrieval-execution.sysml',
    'architecture/test/software-intake/retrieval-runs.sysml',
    'architecture/trace/software-intake-execution.sysml',
    'tier-2/ansible/roles/cache_proxy/defaults/main.yml',
    'tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2',
    'shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2',
    'tests/test_tier_cache_policy.py', 'tests/apt_repository_fixture.py',
    'tests/test_tier_intake_product.py', 'scripts/architecture/intake_product.py',
)


def product_sources(root):
    return {p: hashlib.sha256((root / p).read_text(encoding='utf-8').encode()).hexdigest() for p in INPUTS}


def compare(model, report):
    differences = []
    expected = model['execution']['runs']
    if set(report['runs']) != set(expected):
        differences.append('Measured runs do not cover exactly the modeled experiments')
    for key in set(report['runs']) & set(expected):
        run, actual = expected[key], report['runs'][key]
        for field in ('inputs', 'scenario', 'expected'):
            if actual[field] != run[field]:
                differences.append(key + ': model ' + field + ' changed')
        for field in ('accepted', 'outcome', 'sourceRequests', 'verificationChecks'):
            if type(actual['observed'].get(field)) is not type(run['expected'][field]) or actual['observed'].get(field) != run['expected'][field]:
                differences.append(key + ': ' + field + ' expected ' + str(run['expected'][field]) +
                                   ', observed ' + str(actual['observed'].get(field)))
    return sorted(differences)


def outputs(root, model):
    from svg_pages import page, grid, card, finish, book, SCENARIOS
    path = root / EVIDENCE
    report = json.loads(path.read_text()) if path.is_file() else None
    current = report and report['sources'] == product_sources(root)
    differences = compare(model, report) if current else []
    status = ('Real Squid and APT on loopback; compared with the model. No deployed network test.' if current else
              'No current implementation result. Run the isolated product comparison in the guide.')
    if differences:
        status = 'Implementation differs from the model. Open the evidence and investigate.'
    origin = VIEW.as_posix()
    svg, y, nav = page(origin, 'Software intake | implementation comparison', status, GUIDE)
    rows = []
    order = json.loads((root / 'architecture/views/software-intake/use-cases.json').read_text())['scenarios']
    for key in sorted(model['execution']['runs'], key=lambda k: order.index(model['execution']['runs'][k]['scenario'])):
        run = model['execution']['runs'][key]
        actual = report['runs'].get(key) if current else None
        labels = {'accepted': 'accepted', 'verification-failed': 'rejected by client',
                  'denied': 'denied by policy', 'source-unavailable': 'source unavailable'}
        cache_result = ('cache hit' if any('HIT' in r for r in actual['proxy_results']) else
                        'access denied' if actual['http_status'] == 403 else
                        'source error' if actual['http_status'] >= 500 else 'fetched from source') if actual else ''
        detail = ('Model: '  + labels.get(run['expected']['outcome'], run['expected']['outcome']) +
                  '; software: ' + labels.get(actual['observed']['outcome'], actual['observed']['outcome']) +
                  '. Squid: ' + cache_result + '. Source requests: ' +
                  str(actual['observed']['sourceRequests']) + '.') if actual else 'Open the expected retrieval sequence.'
        rows.append((run['name'], detail, SCENARIOS + '#' + run['scenario'], key))
    y = grid(svg, origin, y, rows)
    y += card(svg, origin, 30, y, 900, 'What this checks',
        'APT authenticates signed repository metadata, then downloads through Squid and checks package hashes. '
        'A cached response can still fail verification. Internal model steps are not claimed as product observations.', GUIDE) + 12
    y += card(svg, origin, 30, y, 900, 'Measured evidence',
        '; '.join(differences) if differences else 'Product versions, source fingerprints, Squid results and APT outcomes.',
        EVIDENCE.as_posix() if report else GUIDE) + 12
    nav[2] = ('Model execution', 'architecture/views/software-intake/execution.svg')
    return {VIEW: book([('index', finish(svg, origin, y, nav))])}
