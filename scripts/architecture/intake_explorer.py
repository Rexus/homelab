"""Direct navigation between focused engineering views and their supporting assets."""

from pathlib import Path
import json
import posixpath
import xml.etree.ElementTree as ET
from diagram_notation import tag
from design_context import scopes, owned_parts, relative
from intake_use_cases import connections, CASE_VIEWS
from intake_intent import case_target
from intake_reverse import asset_links
from svg_pages import (SYSTEM,INTAKE,SCENARIOS,FUNCTIONS,LOGICAL,DEPLOYMENT,RESOURCES,
    text,link,assets,page,finish,add_navigation)


def target_for(model,entries,key):
    if key in model['functions']:return FUNCTIONS+'#'+key
    if key in model['scenarios']:return SCENARIOS+'#'+key
    if key in model['use_cases']:return case_target(key, CASE_VIEWS)
    owners=[s for s in entries if key in owned_parts(model,s['roots'])]
    if owners:
        owner=max(owners,key=lambda s:len(Path(s['page']).parts))
        return owner.get('svg') or owner['page']
    if key.startswith('CONTENT-') or key=='L-cached-content':
        return 'architecture/design/software-intake/object-cache/README.md#storage-and-content'
    if key.startswith(('VM-','RUN-','DISK-','R-')):return DEPLOYMENT
    if key.startswith('REQ-'):return 'architecture/generated/software-intake/intent.md#'+key.lower()
    return LOGICAL


def realized_parts(model,parts):
    roots={t for p in parts for t in connections(model,p,'allocated-to')}
    return owned_parts(model,roots)


def source_rows(model,records,parts):
    rows=[]
    for category,selected in [('Logical implementation',parts),('Selected realization',realized_parts(model,parts))]:
        types={t for p in selected for t in connections(model,p,'typed-by')}
        for key in sorted(types & set(records)):
            rows.extend((source,category+' · '+key,source,None) for source in records[key]['sources'])
    return list({row[0]:row for row in reversed(rows)}.values())


def navigation_outputs(root,model,records,plan,existing):
    entries=scopes(root);outputs={}
    destinations={s['page']:s.get('svg') or s['page'] for s in entries}
    documents={SYSTEM:'architecture/design/README.md',
        'architecture/views/platform/overview.svg':'architecture/design/platform/README.md',
        LOGICAL:'architecture/design/software-intake/logical.md',
        DEPLOYMENT:'architecture/design/software-intake/deployment.md',
        RESOURCES:'architecture/design/software-intake/resources.md'}
    for origin,document in documents.items():
        svg=ET.fromstring(existing[Path(origin)])
        for a in svg.iter(tag('a')):
            target=posixpath.normpath((Path(origin).parent/a.get('href','').partition('#')[0]).as_posix())
            if target in destinations:a.set('href',relative(origin,destinations[target]))
        for parent in list(svg.iter()):
            for child in list(parent):
                key=child.get('data-model')
                if not key or key not in model['elements'] or parent.tag==tag('a'):continue
                if any(e is not child and (e.get('data-model') or e.tag==tag('a')) for e in child.iter()):continue
                target=target_for(model,entries,key)
                if target==origin:continue
                a=ET.Element(tag('a'),{'href':relative(origin,target),'target':'_top'})
                i=list(parent).index(child);parent.remove(child);a.append(child);parent.insert(i,a)
        if origin in (SYSTEM,LOGICAL):
            base='architecture/views/' + ('software-intake/' if origin==LOGICAL else '')
            nav=[('Use cases',base+'use-cases.svg'),('Requirements',base+'requirements.svg'),
                 ('Functions',base+'functions.svg'),('Tests','architecture/views/software-intake/tests.svg'),
                 ('System Overall',SYSTEM),('Documentation',document)]
        else:
            nav=[('System Overall',SYSTEM),('Intake design',LOGICAL),
                 ('IaC and sources','architecture/views/software-intake/sources.svg'),('Documentation',document)]
        outputs[Path(origin)]=add_navigation(ET.tostring(svg,encoding='unicode'),origin,nav)
    origin='architecture/views/software-intake/sources.svg'
    svg,y,nav=page(origin,'Software intake | Implementation assets',
        'Sources and checks attached to the modeled design; this index is supporting material.',
        'architecture/design/software-intake/deployment.md')
    parts=owned_parts(model,['SYS-intake'])
    rows=source_rows(model,records,parts)
    groups={}
    for _,group,target,_ in rows:groups.setdefault(group,[]).append(target)
    y=assets(svg,origin,y,list(groups.items()),asset_links(records))
    outputs[Path(origin)]=ET.tostring(finish(svg,origin,y,nav),encoding='unicode')+'\n'
    return outputs
