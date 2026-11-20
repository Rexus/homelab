"""SVG classification enclosures rendered with native comments, never model parts."""

import xml.etree.ElementTree as ET


def read_annotations(source, view, layout):
    svg = ET.fromstring(source.read_text(encoding='utf-8'))
    parents = {child: parent for parent in svg.iter() for child in parent}
    frames = [e for e in svg.iter() if e.get('data-explanatory') == 'true']
    if layout and set(layout) != {e.get('id') for e in frames}:
        raise ValueError('Native annotation layout differs from SVG enclosures: ' + view['key'])
    result = []
    for element in frames:
        identity = element.get('id')
        annotation = {'id': identity,
                      'label': next((c.text for c in element if c.tag.endswith('}text')), '')}
        if identity in layout:
            if any(layout[identity][role][3] < 70 for role in ('frame', 'caption')):
                raise ValueError('SysON native notes require a minimum height of 70: ' + str(identity))
            members = sorted({e.get('data-model') for e in element.iter() if e.get('data-model')})
            if not members or not set(members) <= set(view['elements']):
                raise ValueError('Annotation members differ from selected model: ' + str(identity))
            parent = parents.get(element)
            while parent is not None and parent not in frames:
                parent = parents.get(parent)
            annotation.update(layout[identity])
            annotation.update(members=members, parent=parent.get('id') if parent is not None else None,
                              frame_key=view['key'] + '-annotation-' + identity,
                              caption_key=view['key'] + '-caption-' + identity)
        result.append(annotation)
    return result


def annotation_text(view):
    # SysON 2026.11 can reveal imported comments in the view's owning presentation package.
    # No `about` links: this release misimports explicit multi-target Annotation references.
    # The SVG owns membership; frames and captions only annotate the presentation namespace.
    lines = []
    for item in view.get('annotations', []):
        if 'frame_key' not in item:
            continue
        body = item['label'].replace('*/', '* /')
        for role in ('frame_key', 'caption_key'):
            lines.append("comment <'" + item[role] + "'> /* " + body + " */")
    return lines


def show_annotations(client, context, diagram, view, indexed):
    ids = [indexed[a[role]]['id'] for a in view.get('annotations', [])
           if 'frame_key' in a for role in ('frame_key', 'caption_key')]
    if ids:
        client.mutate('dropOnDiagram', 'DropOnDiagramInput', {
            'editingContextId': context, 'representationId': diagram['id'],
            'diagramTargetElementId': diagram['id'], 'objectIds': ids,
            'startingPositionX': 0, 'startingPositionY': 0})


def annotation_boxes(view, indexed):
    return {indexed[a[role + '_key']]['id']: a[role] for a in view.get('annotations', [])
            if 'frame_key' in a for role in ('frame', 'caption')}


def style_annotations(client, context, diagram, view, indexed):
    nodes = {n['targetObjectId']: n for n in diagram['nodes']}
    for item in view.get('annotations', []):
        if 'frame_key' not in item:
            continue
        for role in ('frame', 'caption'):
            node = nodes[indexed[item[role + '_key']]['id']]
            frame = role == 'frame'
            colours = item.get('colours', {})
            client.mutate('editSysMLNoteNodeAppearance', 'EditSysMLNoteNodeAppearanceInput', {
                'editingContextId': context, 'representationId': diagram['id'], 'nodeIds': [node['id']],
                'appearance': {'background': colours.get('fill', 'transparent') if frame else 'transparent', 'borderColor': item['border_color'],
                               'borderSize': 2 if frame else 0}})
            # The native note centers its text vertically. A separate borderless comment caption
            # keeps it above the selected parts; both are view annotations with no owned parts.
            client.mutate('editLabelAppearance', 'EditLabelAppearanceInput', {
                'editingContextId': context, 'representationId': diagram['id'],
                'diagramElementIds': [node['id']], 'labelIds': [node['insideLabel']['id']],
                'appearance': {'visibility': 'hidden' if frame else 'visible', 'fontSize': 12,
                               **({'color': colours['color']} if colours else {})}})


def annotation_gaps(view, diagram, indexed):
    """Check native annotation kind, captions, saved geometry and exact visual membership."""
    saved = diagram.get('layoutData', {}).get('nodeLayoutData', {})
    roots = {n['targetObjectId']: n for n in diagram['nodes'] if n.get('state', 'Normal') == 'Normal'}

    def box(node):
        cell = saved.get(node['id'], {})
        pos, size = cell.get('position', {}), cell.get('size', {})
        return [pos.get('x', -10000), pos.get('y', -10000), size.get('width', 0), size.get('height', 0)]

    def inside(outer, inner):
        x, y, w, h = outer
        a, b, c, d = inner
        return a >= x - 1 and b >= y - 1 and a + c <= x + w + 1 and b + d <= y + h + 1

    absolute = {}
    def walk(node, ox=0, oy=0):
        if node.get('state', 'Normal') != 'Normal':
            return
        x, y, w, h = box(node)
        absolute.setdefault(node['targetObjectId'], [ox + x, oy + y, w, h])
        for child in node.get('childNodes', []):
            walk(child, ox + x, oy + y)
    for node in diagram['nodes']:
        walk(node)

    gaps = []
    by_id = {a['id']: a for a in view.get('annotations', [])}
    for item in by_id.values():
        valid = 'frame_key' in item
        for role in ('frame', 'caption') if valid else ():
            obj = indexed.get(item[role + '_key'], {})
            node = roots.get(obj.get('id'))
            if (obj.get('eClass') != 'sysml:Comment' or obj.get('data', {}).get('body') != item['label']
                    or not node or node.get('childNodes') or not node.get('type', '').endswith('sysmlnote')):
                valid = False
                continue
            style = node.get('style', {})
            label = node.get('insideLabel') or {}
            valid &= all(abs(a - b) <= 1 for a, b in zip(box(node), item[role]))
            colours = item.get('colours', {})
            valid &= style.get('background') == (colours.get('fill', 'transparent') if role == 'frame' else 'transparent')
            valid &= style.get('borderSize') == (2 if role == 'frame' else 0)
            valid &= style.get('borderColor') == item['border_color']
            valid &= label.get('style', {}).get('visibility') == ('hidden' if role == 'frame' else 'visible')
            if role == 'caption':
                valid &= item['label'] in label.get('text', '') and inside(item['frame'], box(node))
                if colours:
                    valid &= label.get('style', {}).get('color') == colours['color']
        if valid:
            enclosed = {key for key in view['elements'] if indexed.get(key, {}).get('id') in absolute
                        and inside(item['frame'], absolute[indexed[key]['id']])}
            # A declared renderer omission remains a content gap; check the frame against
            # the members this release can actually draw without inventing replacement parts.
            valid &= enclosed == set(item['members']) - set(view.get('rendering_gaps', {}))
            parent = by_id.get(item.get('parent'))
            if parent:
                valid &= inside(parent['frame'], item['frame'])
        if not valid:
            gaps.append(item)
    return gaps
