"""Scenario paths and function allocations rendered from the native semantic projection."""

import json
import textwrap
import xml.etree.ElementTree as ET
from diagram_notation import tag
from intake_behavior import messages
from intake_use_cases import connections, scenario_functions
from intake_explorer import target_for
from intake_reverse import asset_links
from svg_pages import (SYSTEM, INTAKE, SCENARIOS, FUNCTIONS, LOGICAL, DEPLOYMENT,
    text, link, card, grid, assets, page, finish, book)


def function_views(model, entries, records):
    pages = []
    for key, contract in model["functions"].items():
        element = model["elements"][key]
        svg, y, nav = page(FUNCTIONS, element["name"] + " | " + key,
            "Function contract → logical allocation → implementation and verification assets.",
            "architecture/functions/software-intake/README.md")
        guards = [t for t in connections(model, key, "depends-on") if t.startswith("REQ-")]
        for guard in guards:
            y += card(svg, FUNCTIONS, 30, y, 900, guard,
                "Shapes this function: " + " ".join(model["elements"][guard]["docs"]),
                "architecture/views/software-intake/requirements.svg", guard) + 12
        y += card(svg, FUNCTIONS, 180, y, 600, element["name"],
            " ".join(element["docs"]) + " Input: " + ", ".join(contract["in"]) +
            ". Output: " + ", ".join(contract["out"]), key=key) + 12
        text(svg, "Allocated to — open the logical owner", 480, y + 18, 16, "middle")
        y += 33
        owners = connections(model, key, "allocated-to")
        heights = []
        for i, owner in enumerate(owners):
            width = 900 / len(owners) - 10
            heights.append(card(svg, FUNCTIONS, 30+i*(width+10), y, width,
                model["elements"][owner]["name"],
                "External client responsibility" if owner == "L-Consumers" else "Logical responsibility",
                target_for(model, entries, owner), owner))
        y += max(heights) + 22
        selected = [e["from"] for e in model["edges"]
                    if e["to"] == key and e["kind"] == "depends-on" and e["from"] in records]
        sources = sorted({p for m in selected for p in records[m]["sources"]})
        checks = sorted({p for m in selected for p in records[m].get("test_symbols", [])})
        y = assets(svg, FUNCTIONS, y, [("Behavior source assets", sources), ("Linked checks — not pass results", checks)], asset_links(records))
        relevant = [s for s in model["scenarios"] if key in scenario_functions(model, s)]
        text(svg, "Used by these scenarios", 30, y + 20, 18, weight="bold")
        y += 36
        y = grid(svg, FUNCTIONS, y, [(model["elements"][scenario]["name"], scenario,
             SCENARIOS + "#" + scenario, scenario) for scenario in relevant])
        nav[2] = ("Deployment and IaC", DEPLOYMENT)
        svg.set("data-subject", key)
        svg.set("data-relationships", json.dumps([e for e in model["edges"]
            if e["from"] == key and (e["kind"] == "allocated-to" or e["to"] in guards)]))
        pages.append((key, finish(svg, FUNCTIONS, y, nav)))
    return book(pages)


def scenario_views(root, model, entries, records, plan, *, origin=SCENARIOS, order=None, observed=None, return_pages=False):
    order = order or json.loads((root / "architecture/views/software-intake/use-cases.json").read_text(encoding="utf-8"))["scenarios"]
    notation = json.loads((root / "architecture/views/notation.json").read_text(encoding="utf-8"))
    palette = json.loads((root / notation["palette"]).read_text(encoding="utf-8"))["roles"]
    observed = observed or {}
    pages = []
    for key in order:
        scenario = model["scenarios"][key]
        behavior = model["behaviors"][scenario["behavior"]]
        if len(behavior["participants"]) != 3:
            raise ValueError("Adapt the scenario layout to the native participant count")
        svg, y, nav = page(origin, model["elements"][key]["name"],
            key + (" · Observed native action trace; click a message to follow its function." if key in observed else " · Expected selected path; click a message to follow its function."),
            "docs/01-architecture/07-software-intake/05-retrieval-execution.md" if key in observed else
            "architecture/generated/software-intake/scenarios.md#" + key.lower())
        y += card(svg, origin, 30, y, 900, "Trigger and preconditions",
            scenario["docs"]["Trigger"] + " " + scenario["docs"]["Preconditions"]) + 16
        mapping = {m["id"]: m for m in messages(behavior["steps"])}
        positions = dict(zip(behavior["participants"], (130, 460, 790)))
        start = y + 100
        end = start + len(scenario["messages"])*105
        defs = ET.SubElement(svg, tag("defs"))
        marker_id = "arrow-" + key
        marker = ET.SubElement(defs, tag("marker"), {"id": marker_id, "viewBox": "0 0 10 10",
            "refX": "9", "refY": "5", "markerWidth": "7", "markerHeight": "7", "orient": "auto-start-reverse"})
        ET.SubElement(marker, tag("path"), {"d": "M0 0 L10 5 L0 10 Z", "fill": "#627581"})
        for participant, x in positions.items():
            owner = behavior["bindings"][participant]
            role = "edge" if owner == "L-Proxy" else "actor"
            colours = palette[role]
            card(svg, origin, x-110, y, 220, model["elements"][owner]["name"],
                owner, target_for(model, entries, owner), owner, (colours["fill"], colours["stroke"]))
            ET.SubElement(svg, tag("line"), {"x1": str(x), "x2": str(x), "y1": str(start),
                "y2": str(end), "stroke": "#89939e", "stroke-dasharray": "4 4"})
        for i, message in enumerate(scenario["messages"]):
            m = mapping[message]
            functions = [f for f in connections(model, message, "depends-on") if f in model["functions"]]
            if len(functions) != 1:
                raise ValueError("Sequence message needs a single navigable function: " + message)
            a = link(svg, origin, FUNCTIONS + "#" + functions[0], message + " → " + functions[0])
            a.set("data-message", message)
            a.set("data-function", functions[0])
            x1, x2 = positions[m["from"]], positions[m["to"]]
            yy = start + i*105
            center = (x1+x2)/2 if x1 != x2 else x1+145
            left, right = min(x1, x2, center-150), max(x1, x2, center+150)
            ET.SubElement(a, tag("rect"), {"x": str(left), "y": str(yy),
                "width": str(right-left), "height": "100", "fill": "transparent"})
            lines = textwrap.wrap(m["label"], 37)
            for n, line in enumerate(lines):
                text(a, line, center, yy+18+n*18, 14, "middle")
            identity = message + " · " + functions[0]
            if key in observed:
                event = next(e for e in observed[key]["events"] if e["message"] == message)
                identity = event["action"] + " → " + identity
                a.set("data-execution", event["action"])
            a.set("aria-label", m["label"] + " · " + identity)
            a.find(tag("title")).text = m["label"] + " · " + identity
            text(a, model["elements"][functions[0]]["name"], center, yy+18+len(lines)*18, 12, "middle")
            arrow_y = yy+80
            path = (f"M{x1} {arrow_y} H{x1+38} V{arrow_y+16} H{x1}" if x1 == x2
                    else f"M{x1} {arrow_y} H{x2}")
            attrs = {"d": path, "stroke": "#627581", "stroke-width": "1.6", "fill": "none",
                     "marker-end": "url(#"+marker_id+")"}
            if m["kind"] == "response":
                attrs["stroke-dasharray"] = "6 4"
            ET.SubElement(a, tag("path"), attrs)
        y = end + 18
        text(svg, "Solid: request / process · Dashed: response · Time runs downward", 480, y, 14, "middle")
        y += 22
        y += card(svg, origin, 30, y, 900, "Observed outcome" if key in observed else "Expected outcome", scenario["docs"]["Outcome"]) + 12
        y += card(svg, origin, 30, y, 900, "Acceptance and linked checks", plan[key]["acceptance"],
            "architecture/views/software-intake/tests.svg") + 12
        if key in observed:
            y += card(svg, origin, 30, y, 900, "Compare with expected sequence", model["elements"][observed[key]["scenario"]]["name"],
                SCENARIOS + "#" + observed[key]["scenario"]) + 12
            nav[2] = ("All execution runs", origin)
        else:
            y += card(svg, origin, 30, y, 900, "Native execution evidence", "Run the HTTP refinement and compare observed actions with this sequence.",
                "architecture/views/software-intake/execution.svg") + 12
        if scenario["behavior"] == "B-HTTP":
            y += card(svg, origin, 30, y, 900, "Compare with real software",
                "See what Squid and APT actually did for these retrieval cases.",
                "architecture/views/software-intake/implementation.svg") + 12
        nav[1] = ("Use cases", "architecture/views/software-intake/use-cases.svg")
        if key not in observed:
            nav[2] = ("Logical design", LOGICAL)
        svg.set("data-subject", key)
        svg.set("data-relationships", json.dumps([e for e in model["edges"]
            if e["from"] in scenario["messages"] and e["to"] in scenario["messages"] and e["kind"] == "before"]))
        pages.append((key, finish(svg, origin, y, nav)))
    return pages if return_pages else book(pages)
