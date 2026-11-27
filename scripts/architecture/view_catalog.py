"""Compile renderer-declared selections into the shared Git/SysON view catalogue.

SVG data attributes are emitted at the point where model-driven renderers select their
content. They are not a second hand-maintained model. Native publication consumes the
same compiled selections; presentation adapters must report unsupported relationships.
"""

import hashlib
import json
from pathlib import Path
import re
import posixpath
import xml.etree.ElementTree as ET

from diagram_notation import tag

CATALOG = Path('artifacts/architecture/catalog.json')
INDEX = Path('artifacts/architecture/Views.md')


def identity(path, fragment=''):
    base = 'architecture/models' if Path(path).is_relative_to('architecture/models') else 'architecture/generated'
    name = Path(path).relative_to(base).with_suffix('').as_posix()
    return 'VIEW-' + re.sub(r'[^a-zA-Z0-9_-]', '-', name + ('--' + fragment if fragment else ''))


def selections(svg, model):
    nodes, relationships = set(), []
    parents = {c: p for p in svg.iter() for c in p}
    for element in svg.iter():
        for attr in ('data-element', 'data-model', 'data-models', 'data-message', 'data-function', 'data-execution'):
            nodes.update(element.get(attr, '').split())
        for key in (element.get('data-relation', '') + ' ' + element.get('data-relations', '')).split():
            matches = [e for e in model['edges'] if e.get('id') == key]
            if not matches:
                raise ValueError('View refers to unknown relationship: ' + key)
            relationships.extend(matches)
        relationships.extend(json.loads(element.get('data-relationships', '[]')))
        key = element.get('data-model')
        if key:
            parent = parents.get(element)
            while parent is not None and not parent.get('data-model'):
                parent = parents.get(parent)
            if parent is not None:
                relationships.append({'from': parent.get('data-model'), 'to': key, 'kind': 'contains'})
    boundary = svg.get('data-subject')
    # The overall frame denotes the subject, not an additional top-level component.
    for e in svg.iter():
        if e.get('class') == 'subject' and e.get('data-model', '').startswith(('SYS-', 'P-')):
            boundary = e.get('data-model')
            nodes.discard(boundary)
    missing = nodes - model['elements'].keys()
    if missing:
        raise ValueError('View has unknown model elements: ' + ', '.join(sorted(missing)))
    unique = {json.dumps(r, sort_keys=True): r for r in relationships}
    for relation in unique.values():
        if relation not in model['edges']:
            raise ValueError('View invented a relationship: ' + str(relation))
    return sorted(nodes), [unique[k] for k in sorted(unique)], boundary


def compile_views(outputs, model, selection=None, identities=None):
    views = []
    selected = set(selection) if selection is not None else None
    found = set()
    for path, value in sorted(outputs.items()):
        if path.suffix != '.svg':
            continue
        if not any(path.is_relative_to(base) for base in ('architecture/generated','architecture/models')):
            raise ValueError('Architecture SVG outside views: ' + str(path))
        root = ET.fromstring(value)
        pages = [e for e in root if e.get('data-view')] or [root]
        for page in pages:
            fragment = page.get('data-view', '')
            destination = path.as_posix() + ('#' + fragment if fragment else '')
            if selected is not None and destination not in selected:
                continue
            found.add(destination)
            nodes, relations, subject = selections(page, model)
            title = next((e.text for e in page if e.tag == tag('title')), None) or path.stem
            key = page.get('data-view-id') or (identities or {}).get(destination) or identity(path, fragment)
            page.set('data-view-id', key)
            view = {'key': key, 'name': title, 'owner': path.parent.relative_to('architecture/models' if path.is_relative_to('architecture/models') else 'architecture/generated').as_posix(),
                    'svg': path.as_posix() + ('#' + fragment if fragment else ''),
                    'subject': subject, 'elements': nodes, 'relationships': relations,
                    'presentation': 'model-derived SVG; native SysON uses its own notation'}
            view['content_sha256'] = hashlib.sha256(json.dumps({k: view[k] for k in
                ('key', 'subject', 'elements', 'relationships')}, sort_keys=True).encode()).hexdigest()
            meta = ET.SubElement(page, tag('metadata'), {'data-catalog': key})
            meta.text = json.dumps(view, sort_keys=True)
            views.append(view)
        ET.indent(root, space='  ')
        outputs[path] = ET.tostring(root, encoding='unicode') + '\n'
    if selected is not None and found != selected:
        raise ValueError('Selected engineering view is missing: ' + ', '.join(sorted(selected-found)))
    # Page enumeration is presentation order, not catalogue identity.
    views.sort(key=lambda view: view['key'])
    if len({v['key'] for v in views}) != len(views):
        raise ValueError('Duplicate architecture view identity')
    outputs[CATALOG] = json.dumps({'schema': 1, 'semantic_owner': 'Git', 'views': views}, indent=2) + '\n'
    lines = ['# Architecture views', '',
             'Styled SVGs and native SysON views use the same model selections and stable view identities.',
             'Native sources live in architecture/models; generated SVGs live separately in architecture/generated.',
             'These are projections of one native model, not another authored design tree.',
             'This is the deliberately selected engineering view set.',
             'Supporting scenario details, inspection reports and evidence remain linked assets; their pages',
             'are not automatically additional native views.',
             'Git holds accepted semantics; reviewed SysON intent changes can return to the owning sources.',
             'Publication records actual',
             'element and relationship coverage and must not call an incomplete rendering equivalent.', '',
             '[System Overall](../../architecture/generated/HomelabSystemOverview.svg) · [Authoring and publication](../../docs/04-development/syson.md)', '',
             '| View | Owner | Model elements | Selected relationships |', '| --- | --- | ---: | ---: |']
    for v in views:
        lines.append(f"| [{v['name'].replace('|', ' / ')}]({posixpath.relpath(v['svg'], INDEX.parent.as_posix())}) | "
                     f"{v['owner']} | {len(v['elements'])} | {len(v['relationships'])} |")
    outputs[INDEX] = '\n'.join(lines) + '\n'
    return views
