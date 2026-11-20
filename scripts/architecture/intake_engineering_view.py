"""Typed engineering relationships selected from the native SysML view exposure."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import textwrap
import xml.etree.ElementTree as ET
from svg_pages import page, finish, book, assets, grid, text, link, SYSTEM, FUNCTIONS, SCENARIOS
from design_context import relative
from diagram_notation import tag
from intake_sources import require

VIEW = 'architecture/views/software-intake/engineering.svg'
REPORT = 'architecture/generated/software-intake/verification-cases.md'
GUIDE = 'docs/01-architecture/07-software-intake/04-mbse-review.md'
MODEL = 'architecture/test/software-intake/verification.sysml'


def target(key):
    if key.startswith('REQ-'):
        return VIEW + '#' + key
    if key.startswith('F-'):
        return FUNCTIONS + '#' + key
    if key.startswith('VC-'):
        return REPORT + '#' + key.lower()
    if key == 'UC-update':
        return 'architecture/views/software-intake/use-cases.svg'
    if key == 'AN-admission':
        return 'architecture/functions/software-intake/admission.sysml'
    return 'architecture/views/software-intake/policy-proxy/contract.svg'


def graph(root, model, nodes, edges):
    require(set(nodes) <= set(model['views']['VIEW-engineering']), 'Diagram selects unexposed model elements')
    require(all(e in model['edges'] for e in edges), 'Diagram invented a model relationship')
    colours=json.loads((root/'docs/08-reference/diagrams/palette.json').read_text())['roles']
    lines=['digraph Engineering {', 'graph [rankdir=LR,bgcolor="transparent",pad="0.2",nodesep="0.4",ranksep="0.8"];',
           'node [fontname="Arial",fontsize=16,shape=box,style="rounded,filled",margin="0.18,0.12"];',
           'edge [fontname="Arial",fontsize=13,color="#627581",arrowsize="0.75"];']
    kinds={'ActionUsage':'action','PartUsage':'part','UseCaseDefinition':'use case def',
        'RequirementUsage':'requirement','VerificationCaseDefinition':'verification def','AnalysisCaseDefinition':'analysis def'}
    for key in nodes:
        e=model['elements'][key]
        role='edge' if key=='L-Proxy' else 'action' if key.startswith('F-') else 'policy' if key.startswith('REQ-') else 'default'
        c=colours[role]
        label='«'+kinds.get(e['kind'],e['kind'])+'»\n'+key+'\n'+'\n'.join(textwrap.wrap(e['name'],25))
        shape='ellipse' if key=='UC-update' else 'box'
        lines.append(json.dumps(key)+' ['+','.join(f'{k}={json.dumps(v, ensure_ascii=False)}' for k,v in {
            'label':label,'fillcolor':c['fill'],'color':c['stroke'],'fontcolor':c['color'],'shape':shape,
            'URL':relative(VIEW,target(key)),'target':'_top','id':'model-'+key}.items())+'];')
    labels={'requires':'objective requires','satisfies':'satisfy\n(design assertion)',
            'verifies':'verify\n(test intent)','allocated-to':'allocate','depends-on':'dependency'}
    for e in edges:
        label=labels[e['kind']]
        if e.get('id'):
            label+='\n'+e['id']
        lines.append(json.dumps(e['from'])+' -> '+json.dumps(e['to'])+' [label='+json.dumps(label)+',style=dashed];')
    lines.append('}')
    dot='\n'.join(lines)+'\n'
    executable=os.environ.get('GRAPHVIZ_DOT') or shutil.which('dot')
    require(executable,'Engineering views need Graphviz dot; install the version in architecture/toolchain.json or set GRAPHVIZ_DOT')
    rendered=subprocess.run([executable,'-Tsvg'],input=dot,capture_output=True,text=True,encoding='utf-8',timeout=30,check=True)
    svg=ET.fromstring(rendered.stdout)
    for element in svg.iter():
        old=element.attrib.pop('{http://www.w3.org/1999/xlink}href',None)
        if old: element.set('href',old)
    svg.attrib.pop('width',None)
    svg.attrib.pop('height',None)
    svg.set("data-relationships", json.dumps(edges))
    svg.set("data-models", " ".join(nodes))
    return svg,dot


def outputs(root,model,records):
    pages=[]
    files={}
    selections=[('relationships','Admission design', ['UC-update','F-admit','F-http','L-Proxy','REQ-policy','VC-http-denied'])]
    for requirement in model['requirements']:
        if requirement not in model['views']['VIEW-engineering']:
            continue
        cases=[k for k,v in model['verification'].items() if requirement in v['requirements']]
        selections.append((requirement,requirement+' | verification intent',[requirement,*cases]))
    for key,title,nodes in selections:
        kinds={'requires','allocated-to','satisfies','verifies'}
        selected=[e for e in model['edges'] if e['from'] in nodes and e['to'] in nodes and e['kind'] in kinds]
        svg,y,nav=page(VIEW,title,'Tailored view of native SysML relationships; arrows show engineering meaning, not runtime traffic.',GUIDE)
        drawing,dot=graph(root,model,nodes,selected)
        for element in drawing.iter():
            if element.get('id'): element.set('id',key+'-'+element.get('id'))
        _,_,w,h=map(float,drawing.get('viewBox').split())
        drawing.set('x','25'); drawing.set('y',str(y)); drawing.set('width','910'); drawing.set('height',str(h*910/w))
        svg.append(drawing); y+=h*910/w+25
        files[Path('architecture/generated/software-intake/engineering-'+key+'.dot')]=dot
        if key=='relationships':
            text(svg,'Satisfy is an explicit design assertion. Verify identifies an assessment objective, not a passed result.',30,y,14)
            y+=30
            y=grid(svg,VIEW,y,[('All verification obligations','Native requirements, cases and open evidence gaps',VIEW+'#REQ-policy',None),
                ('Evaluate the admission decision','Compare policy-first admission with a rejected warm-cache shortcut',GUIDE+'#evaluate-a-design-choice',None)])
        else:
            for line in textwrap.wrap('Required: '+' '.join(model['requirements'][key]['constraints']),112):
                text(svg,line,30,y,14);y+=19
            satisfaction=[e for e in model['edges'] if e['kind']=='satisfies' and e['to']==key]
            message='Design assertion recorded; deployed acceptance remains separate.' if satisfaction else 'No satisfaction assertion is modeled for this obligation; do not infer one from a dependency.'
            y+=12
            for line in textwrap.wrap(message,112): text(svg,line,30,y,14);y+=19
            y+=12
            y=grid(svg,VIEW,y,[(k,'Subject: '+', '.join(v['subject_types'])+'. '+v['acceptance'],target(k),k)
                for k,v in model['verification'].items() if key in v['requirements']])
            record=records.get(key, {'sources': []})
            if key not in records:
                text(svg,'Implementation and test bindings are not yet recorded for this requirement.',30,y,14)
                y+=30
            y=assets(svg,VIEW,y,[('Implementation / context',record['sources']),('Available checks — not pass verdicts',record.get('checks',[]))])
        y=assets(svg,VIEW,y,[('Model sources',['architecture/views/software-intake/engineering.sysml',MODEL]),
             ('Design work and evidence',[GUIDE,'docs/01-architecture/07-software-intake/verification.md'])])
        nav=[('System Overall',SYSTEM),('Relationships',VIEW+'#relationships'),
             ('All modeled intent','architecture/generated/software-intake/intent.md'),('Documentation',GUIDE)]
        pages.append((key,finish(svg,VIEW,y,nav)))
    files[Path(VIEW)]=book(pages)
    lines=['# Native verification cases','','Generated from SysML verification definitions and their `verify` objectives.',
        'These are test specifications. Executed outcomes and their scope live in the [evidence record](../../../docs/01-architecture/07-software-intake/verification.md).','',
        '[Engineering relationships](../../views/software-intake/engineering.svg) · [Authoring source](../../test/software-intake/verification.sysml)','']
    for key,case in model['verification'].items():
        lines += ['<a id="'+key.lower()+'"></a>','## '+key,'',
            '**Verify:** '+', '.join(case['requirements'])+'. **Subject type:** '+', '.join(case['subject_types'])+'.','',
            case['acceptance'],'', '**Scenario trace:** '+(', '.join(case['scenarios']) or 'Cross-scenario / site obligation')+'.','']
    files[Path(REPORT)]='\n'.join(lines)
    return files
