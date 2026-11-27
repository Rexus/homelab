"""Direct navigation between focused engineering views and their supporting assets."""

from pathlib import Path
import json
import posixpath
import xml.etree.ElementTree as ET
from diagram_notation import tag
from design_context import scopes, owned_parts, relative
from intake_use_cases import connections, CASE_VIEWS
from intake_intent import case_target
from svg_pages import (SYSTEM,INTAKE,SCENARIOS,FUNCTIONS,LOGICAL,SOLUTION,RESOURCES,
    add_navigation)


def target_for(model,entries,key,origin=None,views=None):
    # A logical role opens its selected realization when the native allocation is shown there.
    # The same role keeps this destination across use cases, functions and logical views.
    for scope in entries:
        target=scope.get('realization_svg')
        if not target or not views or Path(target) not in views or key not in owned_parts(model,scope['roots']):
            continue
        selected={n.get('data-model') for n in ET.fromstring(views[Path(target)]).iter()}
        if set(connections(model,key,'allocated-to')) & selected:
            return target
    if key in model['functions']:return FUNCTIONS+'#'+key
    if key in model['scenarios']:return SCENARIOS+'#'+key
    if key in model['use_cases']:return case_target(key, CASE_VIEWS)
    owners=[s for s in entries if key in owned_parts(model,s['roots'])]
    if owners:
        owner=max(owners,key=lambda s:len(Path(s['page']).parts))
        return owner.get('svg') or owner['page']
    if key.startswith('CONTENT-') or key=='L-cached-content':
        return 'architecture/models/software-intake/object-cache/ObjectCache.sysml'
    if key.startswith(('VM-','RUN-','DISK-','R-')):return SOLUTION
    if key.startswith('REQ-'):return 'artifacts/architecture/generated/software-intake/intent.md#'+key.lower()
    return LOGICAL


def realized_parts(model,parts):
    roots={t for p in parts for t in connections(model,p,'allocated-to')}
    return owned_parts(model,roots)


def navigation_outputs(root,model,records,plan,existing):
    entries=scopes(root);outputs={}
    destinations={s['page']:s.get('svg') or s['page'] for s in entries}
    documents={SYSTEM:'architecture/README.md',
        'architecture/generated/platform/SharedPlatformOverview.svg':'architecture/models/platform/SharedPlatform.sysml',
        LOGICAL:'architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml',
        SOLUTION:'architecture/models/software-intake/solution/SoftwareIntakeSolutionDesign.sysml',
        RESOURCES:'architecture/models/software-intake/solution/SoftwareIntakeSolutionDesign.sysml'}
    for origin,document in documents.items():
        svg=ET.fromstring(existing[Path(origin)])
        for a in svg.iter(tag('a')):
            target=posixpath.normpath((Path(origin).parent/a.get('href','').partition('#')[0]).as_posix())
            if target in destinations:a.set('href',relative(origin,destinations[target]))
        for parent in list(svg.iter()):
            for child in list(parent):
                key=child.get('data-model')
                if not key or key not in model['elements'] or parent.tag==tag('a'):continue
                target=target_for(model,entries,key,origin,existing)
                if target==origin:continue
                a=ET.Element(tag('a'),{'href':relative(origin,target),'target':'_top'})
                if any(e is not child and (e.get('data-model') or e.tag==tag('a')) for e in child.iter()):
                    # Link the container's own symbol without enclosing its children's links.
                    own=[n for n in child if n.tag in {tag(t) for t in
                         ('rect','ellipse','circle','path','polygon','text')} and not n.get('data-model')]
                    if not own:continue
                    i=list(child).index(own[0])
                    for n in own:child.remove(n);a.append(n)
                    child.insert(i,a)
                else:
                    i=list(parent).index(child);parent.remove(child);a.append(child);parent.insert(i,a)
        related=[];caption=None
        if origin in (LOGICAL,SOLUTION,RESOURCES):
            base='architecture/generated/software-intake/SoftwareIntake'
            designs=[('Logical design',LOGICAL),('Solution design',SOLUTION),('Resources',RESOURCES)]
            current=next(label for label,path in designs if path==origin)
            caption='Software intake Â· '+current
            nav=[('System Overall',SYSTEM)]+[(label,path) for label,path in designs if path!=origin]
            nav += [('Proxy contract','architecture/generated/software-intake/policy-proxy/PolicyProxyContract.svg'),('IaC and sources','artifacts/architecture/generated/software-intake/trace.md')]
            related=[('Use cases',base+'UseCases.svg'),('Requirements',base+'Requirements.md'),
                     ('Functions',base+'Functions.svg'),('Tests',base+'Verification.md'),('Documentation',document)]
        elif origin==SYSTEM:
            base='architecture/generated/Homelab'
            nav=[('Use cases',base+'UseCases.svg'),('Requirements',base+'Requirements.md'),
                 ('Functions',base+'Functions.svg'),('Tests','architecture/generated/software-intake/SoftwareIntakeVerification.md'),
                 ('System Overall',SYSTEM),('Documentation',document)]
        else:
            nav=[('System Overall',SYSTEM),('Intake logical design',LOGICAL),
                 ('IaC and sources','artifacts/architecture/generated/software-intake/trace.md'),('Documentation',document)]
        outputs[Path(origin)]=add_navigation(ET.tostring(svg,encoding='unicode'),origin,nav,related,caption)
    return outputs
