"""Compact native part nesting and port-to-port flows in Interconnection View."""

from syson_catalog import index_objects, diagram_nodes, coverage
from syson_annotations import annotation_gaps


def nested_layout(view, diagram, objects):
    keys = {v['id']: k for k, v in index_objects(objects).items()}
    boxes, ports = view['nested_boxes'], view['ports']
    containers = {r['from'] for r in view['relationships']
                  if r['kind'] == 'contains' and r['to'] not in view.get('rendering_gaps', {})}
    positions, hidden = {}, []

    def walk(node):
        key = keys.get(node['targetObjectId'])
        if key not in boxes or node.get('state', 'Normal') != 'Normal':
            return
        positions[node['id']] = boxes[key]
        for child in node.get('childNodes', []):
            if (child.get('insideLabel') or {}).get('text') == 'interconnection':
                if key not in containers:
                    hidden.append(child['id'])
                    continue
                if child.get('state', 'Normal') != 'Normal':
                    raise ValueError('Nested part compartment is hidden: ' + key)
                width, height = boxes[key][2:]
                positions[child['id']] = [1, 60, width - 2, height - 61]
                for part in child.get('childNodes', []):
                    walk(part)
            else:
                hidden.append(child['id'])
        for port in node.get('borderNodes', []):
            box = ports.get(key, {}).get(port['targetObjectLabel'])
            if box:
                positions[port['id']] = box
            else:
                hidden.append(port['id'])

    for node in diagram['nodes']:
        walk(node)
    return positions, hidden


def style_nested(client, context, diagram):
    # Ports retain their identity and arrows; repeated captions add no information here.
    ports = [n for n in diagram_nodes(diagram) if n.get('borderNode')]
    if ports:
        client.mutate('editLabelAppearance', 'EditLabelAppearanceInput', {
            'editingContextId': context, 'representationId': diagram['id'],
            'diagramElementIds': [n['id'] for n in ports],
            'labelIds': [label['id'] for n in ports for label in n.get('outsideLabels', [])],
            'appearance': {'visibility': 'hidden'},
        })
    edges = [e for e in diagram['edges'] if e.get('state', 'Normal') == 'Normal']
    if edges:
        client.mutate('editLabelAppearance', 'EditLabelAppearanceInput', {
            'editingContextId': context, 'representationId': diagram['id'],
            'diagramElementIds': [e['id'] for e in edges],
            'labelIds': [e['centerLabel']['id'] for e in edges if e.get('centerLabel')],
            'appearance': {'fontSize': 12, 'background': '#ffffff'},
        })


def verify_nested(views, objects, diagrams, representations, model):
    keys = {v['id']: k for k, v in index_objects(objects).items()}
    for view in (v for v in views if v.get('nested_boxes')):
        diagram = diagrams[representations[view['key']]['id']]
        report = coverage([view], objects, diagrams, representations, model)
        record = report['views'][0]
        declared = set(view.get('rendering_gaps', {}))
        # Keep the omission visible in coverage. This release exception accepts only the exact
        # declared item and its containment; it cannot excuse a missing part or flow.
        expected_missing = [r for r in view['relationships']
                            if r['kind'] == 'contains' and r['to'] in declared]
        if (set(record['missing_elements']) != declared or record['extra_elements']
                or record['unrendered_relationships'] != expected_missing):
            raise ValueError('Nested content mismatch: ' + str(report['views']))
        if report['views'][0]['palette_mismatches']:
            raise ValueError('Native shared palette mismatch: ' + view['name'])
        configured = [a for a in annotation_gaps(view, diagram, index_objects(objects)) if 'frame_key' in a]
        if configured:
            raise ValueError('Native annotation mismatch: ' + str(configured))
        edges = [e for e in diagram['edges'] if e.get('state', 'Normal') == 'Normal']
        if {keys.get(e['targetObjectId']) for e in edges} != set(view['edges']):
            raise ValueError('Nested flow selection mismatch: ' + view['name'])
        positions, hidden = nested_layout(view, diagram, objects)
        visible = {n['id']: n for n in diagram_nodes(diagram)}
        if any(identity in visible for identity in hidden):
            raise ValueError('Nested detail visibility mismatch: ' + view['name'])
        saved = diagram.get('layoutData', {}).get('nodeLayoutData', {})
        for identity, (x, y, width, height) in positions.items():
            cell = saved.get(identity, {})
            pos, size = cell.get('position', {}), cell.get('size', {})
            if (abs(pos.get('x', -10000) - x) > 1 or abs(pos.get('y', -10000) - y) > 1
                    or size.get('width', 0) < width - 1 or size.get('height', 0) < height - 1):
                raise ValueError('Nested saved layout mismatch: ' + view['name'])
        # A child can have the right model owner but still be drawn outside its container.
        for parent in visible.values():
            parent_size = saved.get(parent['id'], {}).get('size', {})
            for child in parent.get('childNodes', []):
                if child['id'] not in visible:
                    continue
                cell = saved.get(child['id'], {})
                pos, size = cell.get('position', {}), cell.get('size', {})
                if (pos.get('x', -1) < 0 or pos.get('y', -1) < 0
                        or pos.get('x', 0) + size.get('width', 0) > parent_size.get('width', 0) + 1
                        or pos.get('y', 0) + size.get('height', 0) > parent_size.get('height', 0) + 1):
                    raise ValueError('Nested content exceeds its container: ' + view['name'])
