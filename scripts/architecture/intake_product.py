"""Compare observable product outcomes with the same native model experiments."""

import hashlib
import json
from pathlib import Path

EVIDENCE = Path('artifacts/architecture/evidence/software-intake/implementation.json')
GUIDE = 'docs/01-architecture/07-software-intake/06-implementation-comparison.md'
REPORT = Path(GUIDE)
INPUTS = (
    'architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml',
    'architecture/models/software-intake/SoftwareIntakeBehavior.sysml',
    'architecture/models/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml',
    'architecture/models/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml',
    'architecture/models/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml',
    'architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml',
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
    from design_context import relative
    from svg_pages import SCENARIOS
    path=root/EVIDENCE
    report=json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None
    current=report and report['sources']==product_sources(root)
    differences=compare(model,report) if current else []
    status=('Current isolated Squid/APT comparison; no deployed network acceptance.' if current
            else 'No current implementation result. Retained results are historical; rerun the comparison.')
    if differences:status='Implementation differs from the model: '+'; '.join(differences)
    rows=[status,'','| Experiment | Expected outcome | Observed outcome |','| --- | --- | --- |']
    for key,run in model['execution']['runs'].items():
        actual=report['runs'].get(key) if current else None
        observed=actual['observed']['outcome'] if actual else 'Not current'
        rows.append('| ['+run['name']+']('+relative(GUIDE,SCENARIOS)+'#'+run['scenario']+') | '+
                    run['expected']['outcome']+' | '+observed+' |')
    document=(root/REPORT).read_text(encoding='utf-8')
    begin,end='<!-- BEGIN MODEL COMPARISON -->','<!-- END MODEL COMPARISON -->'
    a,b=document.index(begin)+len(begin),document.index(end)
    return {REPORT:document[:a]+'\n'+'\n'.join(rows)+'\n'+document[b:]}
