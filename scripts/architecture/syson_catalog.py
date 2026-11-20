"""Publish an explicit subset of shared views and measure native graphical coverage."""

import json
from pathlib import PurePosixPath
from syson_model import named_elements
from syson_annotations import read_annotations, annotation_text, annotation_gaps
from syson_style import shared_colours, palette_gaps


def select_catalog(root, raw, model, curated):
    catalog=json.loads((root/'architecture/views/catalog.json').read_text(encoding='utf-8'))
    config=json.loads((root/'architecture/views/syson.json').read_text(encoding='utf-8'))
    selection=config.get('publication_views', [])
    available={v['key'] for v in catalog['views']}
    if not selection or len(set(selection)) != len(selection) or set(selection)-available:
        raise ValueError('SysON publication needs an explicit, unique selection of known views')
    presets={v['key']:v for v in curated}
    names=named_elements(raw)
    views=[]
    # Canonical order keeps snapshot hashes stable across renderer enumeration.
    for entry in sorted(catalog['views'], key=lambda view: view['key']):
        if entry['key'] not in selection:
            continue
        view=dict(entry)
        view.update({'compact':True, 'boxes':{key:[40+(i%2)*520,60+(i//2)*160,460,120]
                     for i,key in enumerate(entry['elements'])},
                     'edges':[r['id'] for r in entry['relationships'] if r.get('id')]})
        if view['key'] in presets:
            view.update(presets[view['key']])
            view['compact']=presets[view['key']].get('compact',False)
            if set(view['boxes']) != set(entry['elements']):
                raise ValueError('Native preset differs from shared SVG selection: '+view['key'])
        view['view_definition']='GeneralView'
        view['representation_description']='General View'
        nested=config.get('interconnection_views', {}).get(view['key'])
        if nested:
            if set(nested['boxes']) != set(entry['elements']):
                raise ValueError('Nested layout differs from shared SVG selection: '+view['key'])
            known_gaps=nested.get('rendering_gaps', {})
            for key,gap in known_gaps.items():
                if (key not in entry['elements'] or gap.get('kind') != 'ItemUsage'
                        or model['elements'][key]['kind'] != gap['kind'] or not gap.get('reason')):
                    raise ValueError('Invalid scoped native item gap: ' + key)
            view['rendering_gaps']=known_gaps
            children={r['to'] for r in entry['relationships'] if r['kind']=='contains'}
            view.update({'compact':False, 'nested_boxes':nested['boxes'], 'ports':nested['ports'],
                         'boxes':{k:b for k,b in nested['boxes'].items() if k not in children},
                         'view_definition':'InterconnectionView',
                         'representation_description':'Interconnection View'})
            source=root/view['svg'].partition('#')[0]
            if source.is_file():
                view['annotations']=read_annotations(source, view, nested.get('annotations', {}))
                profile=nested.get('colour_profile')
                if profile and profile != 'shared-notation':
                    raise ValueError('Unknown native colour profile: ' + profile)
                if profile:
                    view['colours']=shared_colours(root, source, view)
        views.append(view)
    # The hierarchy is presentation ownership; exposed elements retain their original semantic owner.
    tree={}
    for view in views:
        branch=tree
        for part in PurePosixPath(view['owner']).parts:
            branch=branch.setdefault(part,{})
        branch.setdefault('_views',[]).append(view)
    def emit(branch):
        lines=[]
        siblings=branch.get('_views',[])
        for view in siblings:
            lines += annotation_text(view)
            title=view['name']
            if sum(v['name']==title for v in siblings)>1:
                title += ' ['+view['svg'].partition('#')[2]+']'
            lines += [f"view <'{view['key']}'> '{title.replace(chr(39), '')}' : StandardViewDefinitions::{view['view_definition']} {{",
                      'doc /* Git-owned view: '+view['svg']+'; selection '+view['content_sha256']+'. */']
            for key in view['elements']:
                if key in view.get('rendering_gaps', {}):
                    continue  # Imported in the full model; omission remains explicit in coverage.
                if not names.get(key,{}).get('qualifiedName'):
                    raise ValueError('Missing native view element: '+key)
                lines.append('expose '+names[key]['qualifiedName']+';')
            lines.append('}')
        for name,child in branch.items():
            if name!='_views': lines += ["package '"+name+"' {",*emit(child),'}']
        return lines
    return views,'package Views {\n'+'\n'.join(emit(tree))+'\n}\n'


def index_objects(objects):
    by_key={o.get('data',{}).get('declaredShortName',o.get('data',{}).get('reqId')):o
            for o in objects if o.get('data')}
    return {k:v for k,v in by_key.items() if k}


def diagram_nodes(diagram):
    def walk(node):
        if node.get('state','Normal')!='Normal': return
        yield node
        for child in node.get('childNodes',[])+node.get('borderNodes',[]):
            yield from walk(child)
    return [n for node in diagram['nodes'] for n in walk(node)]


def verify_representation_set(views, diagrams, representations):
    if (set(representations) != {v['key'] for v in views}
            or set(diagrams) != {r['id'] for r in representations.values()}):
        raise ValueError('Native representations differ from the explicit publication selection')


def coverage(views, objects, diagrams, representations, model):
    indexed=index_objects(objects)
    keys={v['id']:k for k,v in indexed.items()}
    records=[]
    for view in views:
        diagram=diagrams[representations[view['key']]['id']]
        nodes=diagram_nodes(diagram)
        node_keys={n['id']:keys.get(n['targetObjectId']) for n in nodes}
        shown={key for key in node_keys.values() if key in model['elements']}
        # Owned port/documentation compartments belong to the contract's declared details.
        details={view.get('documentation')} if view.get('documentation') else set()
        expected=set(view['elements'])
        missing=sorted(expected-shown)
        extra=sorted(shown-expected-details)
        edges=[e for e in diagram['edges'] if e.get('state','Normal')=='Normal']
        kind_map={'Dependency':'depends-on','FeatureTyping':'typed-by','AllocationUsage':'allocated-to',
                  'ConnectionUsage':'connected-to','FlowUsage':'flow','Subclassification':'typed-by',
                  'PartUsage':'contains','Redefinition':'redefines'}
        endpoint_keys={}
        def endpoints(node,owner=None):
            key=keys.get(node['targetObjectId']) or owner
            endpoint_keys[node['id']]=key
            for child in node.get('childNodes',[])+node.get('borderNodes',[]): endpoints(child,key)
        for node in diagram['nodes']: endpoints(node)
        triples={(endpoint_keys.get(e['sourceId']),endpoint_keys.get(e['targetId']),
                  kind_map.get(e.get('targetObjectKind','').split('entity=')[-1])) for e in edges}
        def containment(node, owner=None):
            if node.get('state','Normal') != 'Normal': return
            key=keys.get(node['targetObjectId'])
            if key in expected and key != owner:
                if owner: triples.add((owner,key,'contains'))
                owner=key
            for child in node.get('childNodes',[]): containment(child,owner)
        for node in diagram['nodes']: containment(node)
        unsupported=[]
        for relation in view['relationships']:
            pair=(relation['from'],relation['to'])
            matched=any(keys.get(e['targetObjectId'])==relation.get('id') and relation.get('id')
                        and (endpoint_keys.get(e['sourceId']),endpoint_keys.get(e['targetId']))==pair for e in edges)
            matched |= (*pair,relation['kind']) in triples
            if relation['kind']=='typed-by':
                # Native typing may be displayed in the usage label rather than as an edge.
                label=model['elements'][relation['to']]['name']
                matched |= any(node_keys.get(n['id'])==relation['from'] and
                               (': '+label) in (n.get('insideLabel') or {}).get('text','') for n in nodes)
            if relation['kind']=='typed-by' and not matched:
                reached={relation['from']}
                for _ in range(len(nodes)):
                    more={b for a,b,k in triples if a in reached and k in ('redefines','typed-by')}
                    if more <= reached: break
                    reached |= more
                matched = relation['to'] in reached
            if not matched: unsupported.append(relation)
        gaps=[]
        if not expected:
            gaps.append('SVG navigation/assets page has no native diagram content')
        if missing: gaps.append('Selected element kinds are not rendered')
        if unsupported: gaps.append('Selected relationships are not rendered')
        if extra: gaps.append('Native rendering exposes additional elements')
        content_status='matched' if not gaps else 'gap'
        colours=palette_gaps(view, diagram, indexed, nodes)
        if colours: gaps.append('Native colours differ from the shared SVG palette')
        annotations=annotation_gaps(view, diagram, indexed)
        if annotations: gaps.append('Explanatory SVG enclosures have no native annotation frame')
        records.append({'key':view['key'],'svg':view['svg'], 'representation':representations[view['key']]['id'],
                        'missing_elements':missing,'extra_elements':extra,'unrendered_relationships':unsupported,
                        'unrendered_annotations':annotations, 'model_content_status':content_status,
                        'palette_mismatches':colours, 'declared_rendering_gaps':view.get('rendering_gaps', {}),
                        'issues':gaps, 'status':'matched' if not gaps else 'gap'})
    return {'scope':'Selected model elements and relationships; SVG styling/navigation/evidence are separate.',
            'views':records,'matched':sum(r['status']=='matched' for r in records),
            'gaps':sum(r['status']=='gap' for r in records)}


def unwanted_details(view,diagram,objects):
    indexed=index_objects(objects)
    names={v['id']:k for k,v in indexed.items()}
    selected_ids={r.get('id') for r in view['relationships'] if r.get('id')}
    selected_kinds={r['kind'] for r in view['relationships']}
    allowed_classes={'typed-by':{'FeatureTyping','Redefinition','Subclassification'},
                     'contains':{'OwningMembership','FeatureMembership','PartUsage'},'flow':{'FlowUsage'},
                     'connected-to':{'ConnectionUsage'},'allocated-to':{'AllocationUsage'}}
    allowed=set().union(*(allowed_classes.get(k,set()) for k in selected_kinds))
    return [e['id'] for e in diagram['edges'] if names.get(e['targetObjectId']) not in selected_ids
            and e.get('targetObjectKind','').split('entity=')[-1] not in allowed]
