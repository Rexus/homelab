"""Question-led SysON view selection and saved-representation checks."""

import json
import textwrap

from syson_model import named_elements


def select_views(root, raw, model):
    names = named_elements(raw)
    overall = json.loads((root / "scripts/architecture/config/views/system-overall.json").read_text(encoding="utf-8"))
    overview = next(v for v in overall["views"] if v["subject"] == "SYS-homelab")
    config = json.loads((root / "scripts/architecture/config/views/syson.json").read_text(encoding="utf-8"))
    views = [{"key": "VIEW-system-overall", "name": "System Overall", "subject": overview["subject"],
              "boxes": {n["key"]: n["box"] for n in overview["nodes"]},
              "edges": [e["id"] for e in overview["edges"]]}]
    contract = config["contract"]
    documentation = config["contract_documentation"]
    if (names[documentation]["@type"] != "Documentation"
            or (names[documentation].get("owner") or {}).get("@id") != names[contract]["@id"]):
        raise ValueError("Contract text must be owned by the selected definition")
    consumers = sorted(e["from"] for e in model["edges"]
                       if e["kind"] == "typed-by" and e["to"] == contract)
    views.append({"key": "VIEW-proxy-contract", "name": "Policy proxy contract",
                  "subject": contract, "question": config["contract_question"],
                  "boxes": config["contract_boxes"], "edges": [],
                  "documentation": documentation,
                  "ports": sorted(e['declaredName'] for e in raw if e['@type'] == 'PortUsage'
                                  and (e.get('owner') or {}).get('@id') == names[contract]['@id'])})
    if set(views[-1]["boxes"]) != {contract}:
        raise ValueError("Contract view must contain its definition with owned obligations only")
    objects = {e['@id']: e for e in raw}
    parent = {k: objects[r['@id']]['redefinedFeature']['@id'] for k in consumers
              for r in names[k].get('ownedRedefinition', [])}
    secondary = {k: next((p for p in consumers if names[p]['@id'] == identity), None)
                 for k, identity in parent.items()}
    primary = [k for k in consumers if not secondary.get(k)]
    impact_boxes = {contract: [40, max(40, (len(primary) - 1) * 65 + 40), 320, 100]}
    impact_boxes.update({k: [520, 40 + i * 130, 500, 110] for i, k in enumerate(primary)})
    for owner in primary:
        for i, key in enumerate(k for k in consumers if secondary.get(k) == owner):
            impact_boxes[key] = [1180, impact_boxes[owner][1] + i * 130, 320, 100]
    if set(impact_boxes) != {contract, *consumers}:
        raise ValueError('Impact layout needs an additional redefinition level')
    views.append({"key": "VIEW-proxy-impact", "name": "Proxy change impact - typed uses",
                  "subject": contract, "question": config["impact_question"], "compact": True,
                  "boxes": impact_boxes, "edges": [], "consumers": consumers})
    lines = ["package SysONViews {"]
    for view in views:
        lines.append(f"view <'{view['key']}'> '{view['name']}' : StandardViewDefinitions::GeneralView {{")
        purpose = view.get("question", f"Repository review snapshot; subject {view['subject']}.")
        lines.append(f"doc /* {purpose} */")
        for key in view["boxes"]:
            if key not in names or not names[key].get("qualifiedName"):
                raise ValueError("View selection has no native qualified name: " + key)
            lines.append("expose " + names[key]["qualifiedName"] + ";")
        lines.append("}")
    lines.append("}")
    return views, "\n".join(lines) + "\n"


def hidden_details(view, diagram, archive_objects):
    """Hide presentation details without deleting model elements or changing other views."""
    if not view.get("compact") and not view.get("documentation"):
        return []
    classes = {o["id"]: o["eClass"] for o in archive_objects}
    hidden = [child["id"] for node in diagram["nodes"] for child in node["childNodes"]
              if view.get("compact") or child.get("insideLabel", {}).get("text") not in ("doc", "ports")]
    hidden.extend(border["id"] for node in diagram["nodes"] for border in node.get("borderNodes", []))
    hidden.extend(edge["id"] for edge in diagram["edges"]
                  if classes.get(edge["targetObjectId"]) == "sysml:AllocationUsage")
    return hidden


def visible_details(view, diagram):
    """The contract exposes its own interfaces and obligations in native compartments."""
    if not view.get("documentation"):
        return []
    return [item["id"] for node in diagram["nodes"] for compartment in node["childNodes"]
            if compartment.get("insideLabel", {}).get("text") in ("doc", "ports")
            for item in [compartment, *compartment["childNodes"]]]


def detail_boxes(view, diagram):
    """Seed native compartment geometry; root-only placement leaves children at zero."""
    if not view.get("documentation"):
        return {}
    width = view['boxes'][view['subject']][2] - 2
    boxes, y = {}, 60
    for name in ('doc', 'ports'):
        compartment = next(c for n in diagram['nodes'] for c in n['childNodes']
                           if c.get('insideLabel', {}).get('text') == name)
        child_y = 34
        for child in compartment['childNodes']:
            text = child['insideLabel']['text']
            lines = sum(max(1, len(textwrap.wrap(line.strip(), max(20, int((width - 60) / 8)))))
                        for line in text.splitlines() if line.strip())
            height = max(42, 24 * lines + 24) if name == 'doc' else 42
            boxes[child['id']] = [0, child_y, width, height]
            child_y += height
        height = child_y + 10
        boxes[compartment['id']] = [1, y, width, height]
        y += height
    return boxes


def edge_handles(view, diagram, indexed):
    if view.get('general_layout'):
        from syson_general import facing_handles
        return facing_handles(view, diagram, indexed)
    if not view.get('compact'):
        return {}
    nodes = {n['id']: n for n in diagram['nodes']}
    heights_by_object = {indexed[key]['id']: box[3] for key, box in view['boxes'].items()}
    heights = {n['id']: heights_by_object[n['targetObjectId']] for n in diagram['nodes']}
    handles = {identity: [] for identity in nodes}
    for identity in nodes:
        for field, side, kind in (('sourceId', 'left', 'source'), ('targetId', 'right', 'target')):
            edges = [e for e in diagram['edges'] if e[field] == identity and e['state'] == 'Normal']
            for i, edge in enumerate(edges):
                handles[identity].append({'edgeId': edge['id'], 'handlePosition': side, 'type': kind,
                                          'position': {'x': 0, 'y': heights[identity] * (i + 1) / (len(edges) + 1)}})
    return handles


def verify_diagrams(views, archive_objects, diagrams, representations, *, layout=False):
    indexed = {o["data"].get("declaredShortName"): o for o in archive_objects
               if o.get("data", {}).get("declaredShortName")}
    for view in views:
        diagram = diagrams[representations[view["key"]]["id"]]
        displayed = {n["targetObjectId"] for n in diagram["nodes"] if n.get('state', 'Normal') == 'Normal'}
        required = {indexed[k]["id"] for k in view["boxes"]}
        if displayed != required:
            raise ValueError("Diagram selection mismatch: " + view["name"])
        edges = {e["targetObjectId"] for e in diagram["edges"] if e.get('state', 'Normal') == 'Normal'}
        if not {indexed[k]["id"] for k in view["edges"]} <= edges:
            raise ValueError("Missing diagram relationship: " + view["name"])
        if layout:
            if view.get('documentation'):
                children = [c for n in diagram['nodes'] for compartment in n['childNodes']
                            for c in compartment['childNodes'] if c.get('state') == 'Normal']
                if indexed[view['documentation']]['id'] not in {c['targetObjectId'] for c in children}:
                    raise ValueError('Contract documentation is not visible')
                stored = {o['id']: o for o in archive_objects}
                ports = sorted(stored[c['targetObjectId']]['data']['declaredName'] for c in children
                               if stored[c['targetObjectId']]['eClass'] == 'sysml:PortUsage')
                if ports != view['ports']:
                    raise ValueError('Contract interfaces are not visible')
            visibility = {item["id"]: item.get("state") for node in diagram["nodes"]
                          for item in [node, *node.get("childNodes", []), *node.get("borderNodes", [])]
                          }
            for node in diagram["nodes"]:
                for child in node.get("childNodes", []):
                    visibility.update({item["id"]: item.get("state") for item in child.get("childNodes", [])})
            visibility.update({e["id"]: e.get("state") for e in diagram["edges"]})
            if (any(visibility[i] != "Hidden" for i in hidden_details(view, diagram, archive_objects))
                    or any(visibility[i] != "Normal" for i in visible_details(view, diagram))):
                raise ValueError("Diagram detail visibility mismatch: " + view["name"])
            compartments = {c['id']: c for n in diagram['nodes'] for c in n.get('childNodes', [])}
            for identity, (x, y, width, height) in detail_boxes(view, diagram).items():
                saved = diagram.get('layoutData', {}).get('nodeLayoutData', {}).get(identity, {})
                if identity not in compartments:
                    continue
                # The browser measures its header fractionally and reflows text rows.
                # Retain compartment placement and verify content containment, not seed row heights.
                position, size = saved.get('position', {}), saved.get('size', {})
                if (abs(position.get('x', -100) - x) > 1 or abs(position.get('y', -100) - y) > 1
                        or size.get('width', 0) < width - 1 or size.get('height', 0) < height - 1):
                    raise ValueError('Diagram compartment layout mismatch: ' + view['name'])
                bottom = 34
                for child in compartments[identity]['childNodes']:
                    cell = diagram['layoutData']['nodeLayoutData'].get(child['id'], {})
                    pos, dim = cell.get('position', {}), cell.get('size', {})
                    if (abs(pos.get('x', -100)) > 1 or pos.get('y', 0) < bottom - 1
                            or dim.get('width', 0) < width - 1 or dim.get('height', 0) < 20
                            or pos['y'] + dim['height'] > size['height'] - 8):
                        raise ValueError('Diagram content layout mismatch: ' + view['name'])
                    bottom = pos['y'] + dim['height']
            for identity, handles in edge_handles(view, diagram, indexed).items():
                saved = diagram.get('layoutData', {}).get('nodeLayoutData', {}).get(identity, {})
                keyed = lambda values: {(h['edgeId'], h['type']): h for h in values}
                if keyed(saved.get('handleLayoutData', [])) != keyed(handles):
                    raise ValueError('Diagram edge routing mismatch: ' + view['name'])
            boxes = {indexed[k]["id"]: box for k, box in view["boxes"].items()}
            for node in diagram["nodes"]:
                saved = diagram.get("layoutData", {}).get("nodeLayoutData", {}).get(node["id"], {})
                x, y, width, height = boxes[node["targetObjectId"]]
                # The browser may grow a box to its minimum label/compartment size.
                if (saved.get("position") != {"x": x, "y": y}
                        or saved.get("size", {}).get("width", 0) < width
                        or saved.get("size", {}).get("height", 0) < height):
                    raise ValueError("Diagram layout mismatch: " + view["name"])
    return indexed
