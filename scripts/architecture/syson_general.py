"""Ownership and geometry checks for the installed SysON General View renderer."""

from pathlib import PurePosixPath


def verify_view_owners(views, objects):
    """Check actual package ancestry, not just the generated bundle or view title."""
    by_id = {o['id']: o for o in objects}
    parents = {}
    for obj in objects:
        for field in ('ownedRelationship', 'ownedRelatedElement'):
            for child in obj.get('data', {}).get(field, []):
                if isinstance(child, dict):
                    parents[child['id']] = obj['id']
    by_key = {o.get('data', {}).get('declaredShortName'): o for o in objects}
    for view in views:
        identity = by_key[view['key']]['id']
        names, visited = [], set()
        while identity in parents and identity not in visited:
            visited.add(identity)
            identity = parents[identity]
            obj = by_id[identity]
            if obj.get('eClass') == 'sysml:Package':
                name = obj['data'].get('declaredName')
                if name == 'Views':
                    break
                names.append(name)
        else:
            raise ValueError('View has no Views package owner: ' + view['key'])
        if tuple(reversed(names)) != PurePosixPath(view['owner']).parts:
            raise ValueError('View ownership mismatch: ' + view['key'])


def verify_general_geometry(view, diagram, keys):
    saved = diagram.get('layoutData', {}).get('nodeLayoutData', {})
    bounds = []
    for node in (n for n in diagram['nodes'] if n.get('state', 'Normal') == 'Normal'):
        key = keys.get(node['targetObjectId'])
        if key not in view['boxes']:
            continue
        x, y, width, height = view['boxes'][key]
        # SysON 2026.11's actor.svg is 41:92. The browser preserves this ratio;
        # a 300x100 seed becomes 300x673, even though a headless archive looks correct.
        if node.get('type') == 'node:image' and node.get('style', {}).get('imageURL') == 'images/actor.svg':
            if abs(height - width * 92 / 41) > 1:
                raise ValueError('Actor aspect ratio mismatch: ' + view['key'] + ' / ' + key)
        cell = saved.get(node['id'], {})
        pos, size = cell.get('position', {}), cell.get('size', {})
        if any(abs(actual - expected) > 1 for actual, expected in (
                (pos.get('x', -10000), x), (pos.get('y', -10000), y),
                (size.get('width', 0), width), (size.get('height', 0), height))):
            raise ValueError('General saved layout mismatch: ' + view['key'] + ' / ' + key)
        bounds.append((key, x, y, width, height))
    labels = diagram.get('layoutData', {}).get('labelLayoutData', {})
    for expected in actor_labels(view, diagram, keys):
        actual = labels.get(expected['id'], {})
        if actual.get('position') != expected['position'] or not actual.get('movedByUser'):
            raise ValueError('Actor label position mismatch: ' + view['key'])
    for i, (key, x, y, width, height) in enumerate(bounds):
        for other, ox, oy, ow, oh in bounds[i + 1:]:
            if min(x + width, ox + ow) > max(x, ox) and min(y + height, oy + oh) > max(y, oy):
                raise ValueError('Overlapping General View nodes: ' + key + ' / ' + other)


def actor_labels(view, diagram, keys):
    labels = []
    for node in diagram['nodes']:
        offset = view.get('actor_label_offsets', {}).get(keys.get(node['targetObjectId']))
        if offset is None or node.get('state', 'Normal') != 'Normal':
            continue
        if node.get('style', {}).get('imageURL') != 'images/actor.svg':
            raise ValueError('Actor label offset applied to another symbol')
        x, y = offset
        labels.extend({'id': label['id'], 'position': {'x': x, 'y': y},
                       'size': {'width': 0, 'height': 0}, 'resizedByUser': False, 'movedByUser': True}
                      for label in node.get('outsideLabels', []))
    return labels


def facing_handles(view, diagram, indexed):
    """Route each endpoint toward its neighbour, retaining semantic edge direction."""
    by_object = {indexed[k]['id']: box for k, box in view['boxes'].items()}
    boxes = {n['id']: by_object[n['targetObjectId']] for n in diagram['nodes']
             if n['targetObjectId'] in by_object and n.get('state', 'Normal') == 'Normal'}
    groups = {}
    for edge in diagram['edges']:
        if edge.get('state', 'Normal') != 'Normal':
            continue
        for field, other, kind in (('sourceId', 'targetId', 'source'), ('targetId', 'sourceId', 'target')):
            if edge[field] not in boxes or edge[other] not in boxes:
                continue
            x, y, w, h = boxes[edge[field]]
            ox, oy, ow, oh = boxes[edge[other]]
            side = 'right' if ox + ow / 2 > x + w / 2 else 'left'
            groups.setdefault((edge[field], side), []).append((oy + oh / 2, edge['id'], kind))
    handles = {identity: [] for identity in boxes}
    for (identity, side), endpoints in groups.items():
        _, _, width, height = boxes[identity]
        for i, (_, edge, kind) in enumerate(sorted(endpoints)):
            handles[identity].append({'edgeId': edge, 'handlePosition': side, 'type': kind,
                                      'position': {'x': width if side == 'right' else 0,
                                                   'y': height * (i + 1) / (len(endpoints) + 1)}})
    return handles
