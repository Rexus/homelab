"""Opted-in SysON views consume the same notation roles and palette as the SVGs."""

import json
import xml.etree.ElementTree as ET


def shared_colours(root, source, view):
    notation = json.loads((root / 'architecture/views/notation.json').read_text(encoding='utf-8'))
    palette = json.loads((root / notation['palette']).read_text(encoding='utf-8'))
    svg = ET.fromstring(source.read_text(encoding='utf-8'))

    def colours(node):
        boundary = node.get('data-boundary-kind')
        if boundary:
            style = notation['boundaryStyles'][boundary]
            foreground = palette['roles'][node.get('class')]['color']
        else:
            category = notation['modelCategories'][node.get('data-category')]
            style = palette['roles'][category['paletteRole']]
            # SVG class CSS still owns inherited text colour; the category decorator overrides
            # shape fills/borders. Preserve the actual SVG, including its existing text treatment.
            foreground = palette['roles'].get(node.get('class'), style)['color']
        return {'fill': style['fill'], 'stroke': style['stroke'], 'color': foreground}

    selected = {node.get('data-model'): colours(node) for node in svg.iter()
                if node.get('data-model') in view['elements']}
    if set(selected) != set(view['elements']):
        raise ValueError('Shared palette lacks a selected SVG element: ' + view['key'])
    frames = {node.get('id'): node for node in svg.iter() if node.get('data-explanatory') == 'true'}
    for annotation in view.get('annotations', []):
        if 'frame_key' in annotation:
            annotation['colours'] = colours(frames[annotation['id']])
            annotation['border_color'] = annotation['colours']['stroke']
    return {'elements': selected, 'links': palette['links'],
            'link_label_color': palette['roles']['default']['color']}


def styled_nodes(view, diagram, indexed, nodes):
    colours = view.get('colours', {}).get('elements', {})
    by_object = {indexed[key]['id']: value for key, value in colours.items()}
    # Compartments inherit their selected owner's colour; nested parts keep their own category.
    return [(node, by_object[node['targetObjectId']]) for node in nodes
            if node.get('type') == 'node:rectangle' and not node.get('borderNode')
            and node['targetObjectId'] in by_object]


def style_palette(client, context, diagram, view, indexed, nodes):
    if not view.get('colours'):
        return
    for node, colours in styled_nodes(view, diagram, indexed, nodes):
        client.mutate('editRectangularNodeAppearance', 'EditRectangularNodeAppearanceInput', {
            'editingContextId': context, 'representationId': diagram['id'], 'nodeIds': [node['id']],
            'appearance': {'background': colours['fill'], 'borderColor': colours['stroke']}})
        label = node.get('insideLabel')
        if label:
            client.mutate('editLabelAppearance', 'EditLabelAppearanceInput', {
                'editingContextId': context, 'representationId': diagram['id'],
                'diagramElementIds': [node['id']], 'labelIds': [label['id']],
                'appearance': {'color': colours['color']}})
    edges = [e for e in diagram['edges'] if e.get('state', 'Normal') == 'Normal']
    if edges:
        client.mutate('editEdgeAppearance', 'EditEdgeAppearanceInput', {
            'editingContextId': context, 'representationId': diagram['id'],
            'edgeIds': [e['id'] for e in edges], 'appearance': {'color': view['colours']['links']['stroke']}})
        client.mutate('editLabelAppearance', 'EditLabelAppearanceInput', {
            'editingContextId': context, 'representationId': diagram['id'],
            'diagramElementIds': [e['id'] for e in edges],
            'labelIds': [e['centerLabel']['id'] for e in edges if e.get('centerLabel')],
            'appearance': {'color': view['colours']['link_label_color'],
                           'background': view['colours']['links']['labelBackground']}})


def palette_gaps(view, diagram, indexed, nodes):
    if not view.get('colours'):
        return []
    gaps = []
    for node, colours in styled_nodes(view, diagram, indexed, nodes):
        style = node.get('style', {})
        label = node.get('insideLabel') or {}
        if (style.get('background') != colours['fill'] or style.get('borderColor') != colours['stroke']
                or label.get('style', {}).get('color') != colours['color']):
            gaps.append(node['id'])
    for edge in diagram['edges']:
        if edge.get('state', 'Normal') != 'Normal':
            continue
        label = (edge.get('centerLabel') or {}).get('style', {})
        if (edge.get('style', {}).get('color') != view['colours']['links']['stroke']
                or label.get('background') != view['colours']['links']['labelBackground']
                or label.get('color') != view['colours']['link_label_color']):
            gaps.append(edge['id'])
    return gaps
