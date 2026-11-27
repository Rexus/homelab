"""Small engineering views projected from native goals, obligations, allocations and cases."""

import json
from pathlib import Path
import re
import textwrap
import xml.etree.ElementTree as ET

from diagram_notation import tag
from design_context import relative, scopes
from intake_explorer import target_for
from intake_case_view import use_case_view
from intake_use_cases import CASE_VIEWS
from svg_pages import text, link, toolbar, book, SYSTEM, LOGICAL, SCENARIOS, FUNCTIONS

BASE = 'architecture/generated/Homelab'
INTAKE = 'architecture/generated/software-intake/SoftwareIntake'


def title(model, key):
    name = model['elements'][key]['name']
    return re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name).capitalize() if ' ' not in name else name


def start(path, heading, note, height, subject):
    svg = ET.Element(tag('svg'), {'viewBox': f'0 0 960 {height}', 'role': 'img',
        'data-subject': subject, 'data-engineering-view': 'true'})
    ET.SubElement(svg, tag('title')).text = heading
    ET.SubElement(svg, tag('rect'), {'width': '960', 'height': str(height), 'fill': 'white'})
    ET.SubElement(svg, tag('style')).text = 'a{cursor:pointer}a:hover rect,a:focus rect{stroke-width:2.5}'
    defs = ET.SubElement(svg, tag('defs'))
    marker = ET.SubElement(defs, tag('marker'), {'id': 'relationship', 'markerWidth': '8',
        'markerHeight': '8', 'refX': '7', 'refY': '4', 'orient': 'auto'})
    ET.SubElement(marker, tag('path'), {'d': 'M0 0 L7 4 L0 8', 'fill': 'none', 'stroke': '#627581'})
    text(svg, heading, 30, 36, 24, weight='bold')
    for i, line in enumerate(textwrap.wrap(note, 114)):
        text(svg, line, 30, 66 + 20*i, 14)
    return svg


def box(svg, model, origin, key, x, y, w, h, kind, target, detail='', shape='rect'):
    owner = link(svg, origin, target, title(model, key)) if target else svg
    g = ET.SubElement(owner, tag('g'), {'data-model': key, 'class': 'model-node'})
    if shape == 'ellipse':
        ET.SubElement(g, tag('ellipse'), {'cx': str(x+w/2), 'cy': str(y+h/2),
            'rx': str(w/2), 'ry': str(h/2), 'fill': '#f8fafc', 'stroke': '#64748b'})
    else:
        ET.SubElement(g, tag('rect'), {'x': str(x), 'y': str(y), 'width': str(w),
            'height': str(h), 'rx': '8' if kind == 'action' else '3',
            'fill': '#f8fafc', 'stroke': '#64748b'})
    text(g, '«'+kind+'»', x+w/2, y+19, 12, 'middle')
    lines = textwrap.wrap(title(model, key), max(18, int((w-24)/8.4)))
    yy = y+42
    for line in lines:
        text(g, line, x+w/2, yy, 16, 'middle', 'bold'); yy += 21
    for line in textwrap.wrap(detail, max(20, int((w-26)/7.4))):
        text(g, line, x+14, yy+3, 13); yy += 18
    if yy-15 > y+h-3:
        raise ValueError('Focused view text exceeds node: '+key)
    return g


def edge(svg, relation, path, label, x, y):
    ET.SubElement(svg, tag('path'), {'d': path, 'fill': 'none', 'stroke': '#627581',
        'stroke-width': '1.4', 'stroke-dasharray': '5 3', 'marker-end': 'url(#relationship)',
        'data-relationships': json.dumps([relation])})
    if label:
        text(svg, label, x, y, 12, 'middle')


def navigation(svg, path, height, scope, document):
    base = BASE if scope == 'system' else INTAKE
    entries = [('System Overall' if scope == 'system' else 'Logical design', SYSTEM if scope == 'system' else LOGICAL),
        ('Use cases', base+'UseCases.svg'), ('Requirements', base+'Requirements.md'),
        ('Functions', base+'Functions.svg'), ('Tests', INTAKE+'Verification.md'), ('Documentation', document)]
    toolbar(svg, path, height-56, entries)
    ET.indent(svg, space='  ')
    return ET.tostring(svg, encoding='unicode')+'\n'


def system_cases(root, model):
    path = BASE+'UseCases.svg'
    svg = start(path, 'Homelab | Use cases',
        'Modeled goals at their actual subject boundaries. Other subsystem goals remain mapped.', 970, 'SYS-homelab')
    cases = [('UC-clone', 'scripts/architecture/config/views/platform/hosting/clone-repository.json'),
             ('UC-update', 'scripts/architecture/config/views/software-intake/use-cases.json')]
    for n, (key, config) in enumerate(cases):
        view = json.loads((root/config).read_text(encoding='utf-8'))
        drawing = ET.fromstring(use_case_view(root, model, view))
        # Shared definitions keep their own subjects, actors and associations; no artificial include edge.
        targets = {key: CASE_VIEWS[key]}
        case = model['use_cases'][key]
        targets[case['subject']] = ('architecture/generated/platform/hosting/Boot1FoundationReference.svg'
            if key == 'UC-clone' else LOGICAL)
        targets.update({a: LOGICAL for a in case['actors'] if case['bindings'][a] == 'SYS-intake'})
        for group in list(drawing):
            target = targets.get(group.get('data-model'))
            if not target:
                continue
            position = list(drawing).index(group)
            drawing.remove(group)
            a = ET.Element(tag('a'), {'href': relative(path, target), 'target': '_top'})
            a.append(group); drawing.insert(position, a)
        for element in drawing.iter():
            if element.get('id'):
                element.set('id', key+'-'+element.get('id'))
        drawing.attrib.pop('aria-labelledby', None)
        drawing.set('x','15');drawing.set('y',str(105+n*395))
        drawing.set('width','930');drawing.set('height','380')
        svg.append(drawing)
    return navigation(svg,path,970,'system','architecture/README.md')


def functions(model,scope,entries=(),views=None):
    path = (BASE if scope=='system' else INTAKE)+'Functions.svg'
    # Layout order groups allocations; it does not prescribe execution order.
    rows={'F-admit':125,'F-http':257,'F-tunnel':389,'F-cache':521,'F-verify':685}
    targets={'L-Proxy':(263,126,'architecture/generated/software-intake/policy-proxy/PolicyProxyContract.svg'),
             'L-Cache':(557,74,LOGICAL),'L-Consumers':(703,74,LOGICAL)}
    allocations=[e for e in model['edges'] if e['kind']=='allocated-to' and e['from'] in rows]
    unknown={e['to'] for e in allocations}-set(targets)
    if unknown:
        raise ValueError('Function view needs placement for allocated components: '+', '.join(sorted(unknown)))
    height=910
    svg=start(path,('Homelab' if scope=='system' else 'Software intake')+' | Functions',
        ('Modeled intake slice. ' if scope=='system' else '') +
        'Each component appears once. Dashed arrows show allocations, not execution order.',
        height,'SYS-homelab' if scope=='system' else 'SYS-intake')
    text(svg,'Function / action',30,105,14,weight='bold')
    text(svg,'Allocated component',620,105,14,weight='bold')
    for key,y in rows.items():
        if key=='F-verify':
            ET.SubElement(svg,tag('path'),{'d':f'M30 {y-22} H930','stroke':'#89939e','stroke-dasharray':'3 3'})
            text(svg,'External client responsibility',30,y-7,12)
        box(svg,model,path,key,30,y,420,110,'action',FUNCTIONS+'#'+key,
            'Input: '+', '.join(model['functions'][key]['in']))
        if not any(e['from']==key for e in allocations):
            text(svg,'Allocation missing',465,y+45,14)
    for key,(y,h,href) in targets.items():
        if any(e['to']==key for e in allocations):
            box(svg,model,path,key,620,y,310,h,'part',target_for(model,entries,key,views=views))
    for key,y in rows.items():
        outgoing=sorted((e for e in allocations if e['from']==key),
                        key=lambda e:(targets[e['to']][0],e.get('id','')))
        for n,relation in enumerate(outgoing):
            target=relation['to'];ty,th,_=targets[target]
            incoming=sorted((e for e in allocations if e['to']==target),
                            key=lambda e:(rows[e['from']],e.get('id','')))
            sy=y+110*(n+1)/(len(outgoing)+1)
            ey=ty+th*(incoming.index(relation)+1)/(len(incoming)+1)
            # Align nearly level attachments instead of adding a tiny dogleg. Otherwise,
            # stagger vertical lanes: longer routes run outside shorter routes, never merge.
            if abs(ey-sy)<2:
                route=f'M450 {sy} H620';label_x=535
            else:
                rank=incoming.index(relation) if ey<sy else len(incoming)-1-incoming.index(relation)
                lane=505+70*rank/max(1,len(incoming)-1)
                route=f'M450 {sy} H{lane} V{ey} H620';label_x=(450+lane)/2
            edge(svg,relation,route,'allocate',label_x,sy-12)
    return navigation(svg,path,height,scope,'architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml')


def intake_cases(root,model):
    path=INTAKE+'UseCases.svg'
    svg=ET.fromstring(use_case_view(root,model))
    svg.set('viewBox','0 0 960 825')
    next(e for e in svg if e.tag==tag('rect')).set('height','825')
    text(svg,'Scenarios of this goal',30,458,19,weight='bold')
    keys=[k for k,v in model['scenarios'].items() if v['use_case']=='UC-update']
    for i,key in enumerate(keys):
        a=link(svg,path,SCENARIOS+'#'+key,title(model,key))
        a.set('data-model',key)
        a.set('data-relationships',json.dumps([e for e in model['edges']
            if e['from']=='UC-update' and e['to']==key and e['kind']=='contains']))
        x,y=30+(i%2)*465,495+(i//2)*51
        ET.SubElement(a,tag('rect'),{'x':str(x-5),'y':str(y-20),'width':'440','height':'46','fill':'transparent'})
        text(a,title(model,key)+' →',x,y,15)
        text(a,'HTTP' if model['scenarios'][key]['behavior']=='B-HTTP' else 'HTTPS',x,y+20,12)
    related=[key for key,case in model['use_cases'].items()
             if key!='UC-update' and 'SYS-intake' in case['bindings'].values()]
    for i,key in enumerate(related):
        if i>0:raise ValueError('Adapt the use-case related-goal layout for more consumers')
        a=link(svg,path,CASE_VIEWS[key],'Operator goal: '+title(model,key))
        text(a,'Operator goal: '+title(model,key)+' →',30,738,15)
    return navigation(svg,path,825,'intake','architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml')


def outputs(root,model,views=None):
    result={Path(BASE+'UseCases.svg'):system_cases(root,model),
            Path(INTAKE+'UseCases.svg'):intake_cases(root,model)}
    for scope in ('system','intake'):
        base=BASE if scope=='system' else INTAKE
        result[Path(base+'Functions.svg')]=functions(model,scope,scopes(root),views)
    if views:
        for path in (Path(INTAKE+'UseCases.svg'),Path(INTAKE+'Functions.svg')):
            overview=ET.fromstring(result[path])
            detailed=ET.fromstring(views[path])
            pages=[('overview',overview)]+[(page.get('data-view'),page) for page in detailed
                if page.get('data-view')]
            result[path]=book(pages)
    return result
