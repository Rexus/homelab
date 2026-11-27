"""Readable requirement and verification matrices projected from the native model."""

import json
from pathlib import Path
import re
from design_context import relative
from requirement_results import PLAN, fingerprint, verdict

REQUIREMENTS = Path('architecture/generated/software-intake/SoftwareIntakeRequirements.md')
VERIFICATION = Path('architecture/generated/software-intake/SoftwareIntakeVerification.md')
SYSTEM = Path('architecture/generated/HomelabRequirements.md')
SOURCE = 'architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml'
CASES = 'architecture/models/software-intake/SoftwareIntakeVerification.sysml'
EVIDENCE = 'artifacts/architecture/evidence/software-intake'


def name(model, key):
    value=model['elements'][key]['name']
    return re.sub(r'(?<=[a-z])(?=[A-Z])',' ',value).capitalize() if ' ' not in value else value


def cell(value):
    return value.replace('|','\\|').replace('\n',' ')


def link(origin, target, label):
    return '['+label+']('+relative(origin,target)+')'


def anchors(key):
    return '<a id="'+key+'"></a><a id="'+key.lower()+'"></a>'


def published_status(root, model):
    """Use the latest retained assessment only; missing provenance cannot establish current success."""
    reports=[(json.loads(p.read_text(encoding='utf-8')),p) for p in
             (root/EVIDENCE).glob('requirement-assessment*.json')]
    if not reports:
        return {}, {}, EVIDENCE+'/README.md', 'Missing: no retained assessment.'
    report,path=max(reports,key=lambda item:item[0]['assessed_at'])
    target=path.with_suffix('.md') if path.with_suffix('.md').is_file() else path
    target=target.relative_to(root).as_posix()
    current=fingerprint(root,model,json.loads((root/PLAN).read_text(encoding='utf-8')))
    if report.get('source_fingerprints')!=current:
        return {}, {}, target, 'Stale: retained evidence does not establish this model revision.'
    cases={k:status_summary([row for row in report['obligations'] if row['case']==k])
           for k in model['verification']}
    reqs={k:status_summary([row for row in report['obligations'] if row['requirement']==k])
          for k in model['requirements']}
    return reqs,cases,target,'Latest retained assessment: '+report['assessed_at']+'.'


def status_summary(rows):
    overall = verdict([row['status'] for row in rows])
    scopes = sorted({row['scope'] for row in rows})
    return 'Overall: ' + overall + '; ' + '; '.join(
        scope + ': ' + verdict([row['status'] for row in rows if row['scope'] == scope])
        for scope in scopes)


def navigation(origin):
    targets=[('System Overall','architecture/generated/HomelabSystemOverview.svg'),
        ('Logical design','architecture/generated/software-intake/SoftwareIntakeLogicalDesign.svg'),
        ('Use cases','architecture/generated/software-intake/SoftwareIntakeUseCases.svg'),
        ('Requirements',REQUIREMENTS),('Functions','architecture/generated/software-intake/SoftwareIntakeFunctions.svg'),
        ('Verification',VERIFICATION)]
    return ' · '.join(link(origin,str(target),label) for label,target in targets)


def sources(root):
    plan=json.loads((root/PLAN).read_text(encoding="utf-8"))
    files=set(fingerprint(root,{},plan))
    for path in (root/EVIDENCE).glob('requirement-assessment*.json'):
        files.add(path.relative_to(root).as_posix())
        if path.with_suffix('.md').is_file():files.add(path.with_suffix('.md').relative_to(root).as_posix())
    return files


def outputs(root, model):
    req_status,case_status,evidence,note=published_status(root,model)
    result={}
    for path in (SYSTEM,REQUIREMENTS):
        heading='Homelab' if path==SYSTEM else 'Software intake'
        lines=['# '+heading+' requirements','',
            'Generated from the native SysML requirements and `verify` relationships. Edit the model, then rebuild.','',
            ('Only the modeled intake guardrails are covered; other system areas remain mapped.' if path==SYSTEM else
             'Subjects retain their own responsibilities, including participating clients and independent controls.'),'',
            note+' Status covers the retained assessment; the completion gate remains authoritative.','',
            '| Requirement | Obligation / subject | Design satisfaction assertion | Verification checks | Status / evidence |',
            '| --- | --- | --- | --- | --- |']
        for key,req in sorted(model['requirements'].items()):
            checks=[k for k,v in model['verification'].items() if key in v['requirements']]
            checklinks='<br>'.join(link(path,str(VERIFICATION)+'#'+k,k) for k in checks) or 'Uncovered'
            statement=' '.join(req['constraints'])+' Subject: '+', '.join(name(model,k) for k in req['subject_types'])+'.'
            satisfying=[e['from'] for e in model['edges'] if e['kind']=='satisfies' and e['to']==key]
            assertions='<br>'.join(link(path,'architecture/generated/software-intake/SoftwareIntakeLogicalDesign.svg',name(model,k)) for k in satisfying) or 'None recorded'
            if req.get('satisfaction_review'):
                assertions += '<br>' + cell(req['satisfaction_review'])
            status=req_status.get(key,'Not verified — stale or missing evidence')
            lines.append('| '+anchors(key)+'`'+key+'`<br>'+name(model,key)+' | '+cell(statement)+' | '+assertions+' | '+checklinks+
                         ' | '+link(path,evidence,status)+' |')
        lines+=['',link(path,SOURCE,'Native requirement definitions'),'',navigation(path),'']
        result[path]='\n'.join(lines)
    path=VERIFICATION
    lines=['# Software intake verification','',
        'Generated from native verification definitions, their requirement objectives and scenario traces.',
        'Each row specifies a check; it is not an execution result. Missing, stale or failed mandatory evidence remains open.','',
        note,'','| Check / method | Setup and action | Pass criterion | Requirement / scenario | Status / evidence |',
        '| --- | --- | --- | --- | --- |']
    seen=set()
    for key,case in sorted(model['verification'].items()):
        marker=anchors(key)
        for req in case['requirements']:
            if req not in seen:marker+=anchors(req);seen.add(req)
        trace=[link(path,str(REQUIREMENTS)+'#'+k,k) for k in case['requirements']]
        trace += [link(path,'architecture/generated/software-intake/SoftwareIntakeUseCases.svg#'+k,name(model,k))
                  for k in case['scenarios']]
        status=case_status.get(key,'Not verified — stale or missing evidence')
        lines.append('| '+marker+'`'+key+'`<br>'+name(model,key)+'<br>**'+case['method']+'** | '+
            cell('Setup: '+case['setup'])+'<br>'+cell('Action: '+case['action'])+' | '+cell(case['acceptance'])+
            ' | '+'<br>'.join(trace)+' | '+link(path,evidence,status)+' |')
    lines+=['','## Verification approach','',
        'Use the requirement objectives and scenario traces above to select the applicable checks. Local HTTP fixtures',
        'do not establish deployed CONNECT/TLS, network isolation or independent recovery. Those need their own evidence.','',
        link(path,'architecture/generated/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.svg','Retrieval model execution')+
        ' explains the simulated retrieval behavior. It is supporting analysis, not measured software or site acceptance.',
        'A focused V&V plan diagram may be added when the relationship between design, criteria and analyses needs explanation;',
        'a second diagram of this test list is unnecessary.','',
        link(path,CASES,'Native verification definitions')+' · '+
        link(path,'docs/01-architecture/07-software-intake/06-implementation-comparison.md','Implementation comparison')+' · '+
        link(path,EVIDENCE+'/README.md','Evidence scope and open obligations'),'',navigation(path),'']
    result[path]='\n'.join(lines)
    return result
