"""Apply one element-kind palette across portable model views, independent of subsystem names."""

import json
import xml.etree.ElementTree as ET
from diagram_notation import tag, stick_actor
from svg_pages import text


def category(model,key,notation):
    kind=model['elements'][key]['kind']
    if kind.startswith(('Requirement','UseCase','Concern')):
        return 'intent'
    if kind.startswith('Verification'):
        return 'verification'
    if kind.startswith(('Action','Calculation','State','Analysis')):
        return 'function'
    if kind.startswith('Port'):
        return 'interface'
    if kind.startswith(('Part','Item')):
        explicit=notation['modelCategoryElements'].get(key)
        if explicit:
            return explicit
        def types_of(element):
            return {element} | {e['to'] for e in model['edges']
                                if e['from']==element and e['kind']=='typed-by'}
        types=types_of(key)
        owners={e['from'] for e in model['edges'] if e['to']==key and e['kind']=='contains'}
        # Project-reviewed realization roles select native type/ownership, never product names or ID prefixes.
        matches={r['category'] for r in notation.get('modelCategoryRules',[])
                 if kind==r['kind'] and r['type'] in types
                 and any(r['ownerType'] in types_of(owner) for owner in owners)}
        if len(matches)>1:
            raise ValueError('Conflicting model colour roles: '+key)
        if matches:
            return matches.pop()
        for name,definitions in notation['modelCategoryTypes'].items():
            if types & set(definitions):
                return name
        # A part alone does not establish software, hardware, or implementation status.
        return 'external'
    return None



def geometry(node):
    """An element's shapes may be under SVG links or glyph groups, but never under another part."""
    for child in node:
        if child.get('data-model') or child.get('data-element'):
            continue
        if child.tag in {tag('rect'),tag('path'),tag('polygon'),tag('ellipse'),tag('circle')}:
            yield child
        elif child.tag in {tag('a'),tag('g')}:
            yield from geometry(child)


def decorate(root,model,outputs):
    notation=json.loads((root/'scripts/architecture/config/views/notation.json').read_text(encoding='utf-8'))
    palette=json.loads((root/notation['palette']).read_text(encoding='utf-8'))['roles']
    categories=notation['modelCategories']
    for path,value in list(outputs.items()):
        if path.suffix!='.svg':
            continue
        svg=ET.fromstring(value)
        used=set();boundaries=set()
        for node in svg.iter():
            boundary=notation['boundaryRoles'].get(node.get('class'))
            enclosed=any(e is not node and e.get('data-model') for e in node.iter())
            if boundary and (node.get('data-context') or enclosed or boundary=='subject'):
                boundary_style=notation['boundaryStyles'][boundary]
                node.set('data-boundary-kind',boundary);boundaries.add(boundary)
                shape=next((e for e in node if e.tag==tag('rect')),None)
                if shape is not None:
                    shape.set('style',f'fill:{boundary_style["fill"]};stroke:{boundary_style["stroke"]};stroke-dasharray:{boundary_style["dash"]};')
                # Boundaries express grouping/containment; their appearance is independent of part kind.
                continue
            key=node.get('data-model') or node.get('data-element')
            if key not in model['elements']:
                # Graphviz retains the native node key in its generated id.
                key=node.get('id','').split('-model-')[-1]
            if key not in model['elements']:
                continue
            kind=category(model,key,notation)
            if kind is None:
                continue
            used.add(kind);node.set('data-category',kind)
            colours=palette[categories[kind]['paletteRole']]
            # Only the element's own geometry; nested parts and connectors keep their own meaning.
            for shape in geometry(node):
                if shape.tag not in {tag('rect'),tag('path'),tag('polygon'),tag('ellipse'),tag('circle')}:
                    continue
                if shape.get('data-relation') or shape.get('data-relationships') or shape.get('class')=='connection':
                    continue
                fill=shape.get('fill')
                fill='none' if fill=='none' else colours['fill']
                shape.set('style',shape.get('style','')+f';fill:{fill};stroke:{colours["stroke"]};')
            node.set('color',colours['color'])
            # Inline colour wins over older deployment-class CSS for currentColor text.
            node.set('style',node.get('style','')+f';color:{colours["color"]};')
        legends=[n for n in svg.iter(tag('g')) if n.get('class')=='legend']
        if not legends and svg.get('data-engineering-view')=='true':
            legends=[ET.SubElement(svg,tag('g'),{'class':'legend','data-y':str(float(svg.get('viewBox').split()[3])-82)})]
        parents={child:parent for parent in svg.iter() for child in parent}
        for legend in legends:
            scope=parents[legend]
            while scope is not svg and scope.tag!=tag('svg'):
                scope=parents[scope]
            displayed=[n for n in scope.iter() if n.get('data-category') and any(True for _ in geometry(n))]
            used={n.get('data-category') for n in displayed}
            boundaries={n.get('data-boundary-kind') for n in scope.iter() if n.get('data-boundary-kind')}
            humans=[n for n in displayed if n.find('.//*[@class="actor-symbol"]') is not None]
            if humans and all(n in humans for n in displayed if n.get('data-category')=='external'):
                used.discard('external')
            labels=[e for e in legend if e.tag==tag('text')]
            y=float(legend.get('data-y') or min(float(e.get('y','0')) for e in labels))
            for child in list(legend):legend.remove(child)
            keys=[(kind,categories[kind]['label'],palette[categories[kind]['paletteRole']],'none')
                  for kind in categories if kind in used]
            keys += [(kind,notation['boundaryStyles'][kind]['label'],notation['boundaryStyles'][kind],
                      notation['boundaryStyles'][kind]['dash']) for kind in notation['boundaryStyles'] if kind in boundaries]
            if humans:
                keys.append(('human','Human actor',palette['actor'],'none'))
            for i,(kind,label,colours,dash) in enumerate(keys):
                x,yy=30+(i%4)*230,y+(i//4)*25
                symbol=ET.SubElement(legend,tag('g'),{'fill':colours['fill'],'stroke':colours['stroke'],
                    'stroke-dasharray':dash,'data-category-key':kind})
                if kind=='human':
                    stick_actor(symbol,x+11,yy-5,.24)
                elif kind=='intent' and all(model['elements'][n.get('data-model') or n.get('data-element')]['kind'].startswith('UseCase')
                                           for n in displayed if n.get('data-category')=='intent'
                                           and (n.get('data-model') or n.get('data-element')) in model['elements']):
                    ET.SubElement(symbol,tag('ellipse'),{'cx':str(x+11),'cy':str(yy-4),'rx':'12','ry':'8'})
                else:
                    ET.SubElement(symbol,tag('rect'),{'x':str(x),'y':str(yy-12),'width':'22','height':'16'})
                text(legend,label,x+29,yy+1,12)
        ET.indent(svg,space='  ')
        outputs[path]=ET.tostring(svg,encoding='unicode')+'\n'
