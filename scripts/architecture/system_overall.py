"""Curated overviews selected from the native system and shared-provider model."""

import json
from pathlib import Path
import textwrap
import xml.etree.ElementTree as ET
from diagram_notation import tag, legend, validate_model_roles
from intake_sources import require

LAYOUT = Path("scripts/architecture/config/views/system-overall.json")
OVERVIEW_OUTPUTS = [
    Path("architecture/generated/HomelabSystemOverview.svg"),
    Path("architecture/generated/platform/SharedPlatformOverview.svg"),
]


def overview_sources(root):
    return {LAYOUT.as_posix(), "architecture/README.md"} | {
        p.relative_to(root).as_posix() for p in (root / "architecture/models").rglob("*.sysml")
    }


def check_overviews(root, model, views):
    elements, edges = model["elements"], model["edges"]
    for view in views:
        keys = {node["key"] for node in view["nodes"]}
        children = {
            e["to"]
            for e in edges
            if e["from"] == view["subject"]
            and e["kind"] == "contains"
            and elements[e["to"]]["kind"] == "PartUsage"
        }
        require(keys == children, "Overview must cover its direct subsystem parts: " + view["subject"])
        require(len(keys) == len(view["nodes"]), "Duplicate overview part selection")
        relationships = {
            e["to"]
            for e in edges
            if e["from"] == view["subject"]
            and e["kind"] == "contains"
            and elements[e["to"]]["kind"] in ("Dependency", "ConnectionUsage")
        }
        require(
            {e["id"] for e in view["edges"]} == relationships,
            "Overview must cover its selected boundary relationships",
        )
        output = root / view["output"]
        for node in view["nodes"]:
            target = (output.parent / node["href"]).resolve()
            require(
                target.is_relative_to((root / "architecture/models").resolve()) and target.is_file(),
                "Missing or escaping overview link: " + node["href"],
            )
            # A root box must open its direct child folder, matching design composition.
            if view["subject"] == "SYS-homelab":
                require(
                    target.suffix == ".sysml" and target.parent.parent == (root / 'architecture/models').resolve(),
                    "Root overview must open a direct child design: " + node["href"],
                )
                require(bool(target.read_text(encoding="utf-8").strip()), "Empty native subsystem owner")
        for selection in view["edges"]:
            matches = [
                e
                for e in edges
                if e.get("id") == selection["id"] and e["kind"] in ("depends-on", "connected-to")
            ]
            require(
                len(matches) == 1 and matches[0]["from"] in keys and matches[0]["to"] in keys,
                "Overview selects missing or out-of-scope relationship: " + selection["id"],
            )
    expected = {
        ("SYS-intake-proxy", "L-Proxy"),
        ("SYS-intake-cache", "L-Cache"),
        ("SYS-platform", "P-context"),
    }
    actual = {(e["from"], e["to"]) for e in edges if e["kind"] == "bound-to"}
    require(expected <= actual, "System overview lost its existing subsystem bindings")


def draw(root, model, view):
    notation = json.loads((root / "scripts/architecture/config/views/notation.json").read_text(encoding="utf-8"))
    palette = json.loads((root / notation["palette"]).read_text(encoding="utf-8"))["roles"]
    height = view["height"]
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    svg = ET.Element(
        tag("svg"), {"viewBox": f"0 0 960 {height}", "role": "img", "aria-labelledby": "title desc"}
    )
    if view.get("view_id"):
        svg.set("data-view-id", view["view_id"])
    ET.SubElement(svg, tag("title"), {"id": "title"}).text = view["title"]
    ET.SubElement(svg, tag("desc"), {"id": "desc"}).text = view["description"]
    ET.SubElement(svg, tag("rect"), {"width": "960", "height": str(height), "fill": "white"})
    ET.SubElement(svg, tag("style")).text = (
        "text{font:16px Arial,sans-serif;fill:currentColor;stroke:none;text-anchor:middle}"
        ".title{font-size:23px;font-weight:600}.node-title{font-size:18px;font-weight:600}"
        ".note{font-size:14px}.label{font-size:13px}.legend text{font-size:12px}"
        "a:focus rect,a:hover rect{stroke-width:3px}"
    )
    defs = ET.SubElement(svg, tag("defs"))
    marker = ET.SubElement(
        defs,
        tag("marker"),
        {
            "id": "dep",
            "markerWidth": "8",
            "markerHeight": "8",
            "refX": "7",
            "refY": "4",
            "orient": "auto",
        },
    )
    ET.SubElement(marker, tag("path"), {"d": "M0 0 L8 4 L0 8 Z", "fill": "#627581"})
    boundary = ET.SubElement(
        svg, tag("g"), {"data-model": view["subject"], "class": "subject", "color": "#1f2937"}
    )
    ET.SubElement(
        boundary,
        tag("rect"),
        {
            "x": "15",
            "y": "78",
            "width": "930",
            "height": str(height - 202),
            "rx": "5",
            "fill": "#f8fafc",
            "stroke": "#8b857c",
        },
    )
    for y, text, cls in [(32, view["title"], "title"), (59, view["subtitle"], "note")]:
        ET.SubElement(
            svg, tag("text"), {"x": "480", "y": str(y), "class": cls, "color": "#1f2937"}
        ).text = text
    for selection in view["edges"]:
        edge = next(
            e
            for e in model["edges"]
            if e.get("id") == selection["id"] and e["kind"] in ("depends-on", "connected-to")
        )
        attrs = {
            "d": selection["path"],
            "fill": "none",
            "stroke": "#627581",
            "stroke-width": "1.6",
            "data-relation": edge["id"],
        }
        if edge["kind"] == "depends-on":
            attrs.update({"stroke-dasharray": "6 4", "marker-end": "url(#dep)"})
        ET.SubElement(boundary, tag("path"), attrs)
        label = model["elements"][edge["id"]]["name"]
        x, y = selection["label_at"]
        width = len(label) * 7 + 12
        ET.SubElement(
            boundary,
            tag("rect"),
            {
                "x": str(x - width / 2),
                "y": str(y - 14),
                "width": str(width),
                "height": "20",
                "fill": "#f8fafc",
            },
        )
        ET.SubElement(boundary, tag("text"), {"x": str(x), "y": str(y), "class": "label"}).text = label
    for node in view["nodes"]:
        role = node["role"]
        colours = palette[notation["roles"][role].get("paletteRole", role)]
        key = node["key"]
        link = ET.SubElement(
            boundary,
            tag("a"),
            {
                "href": node["href"],
                "target": "_top",
                "aria-label": "Open " + model["elements"][key]["name"] + " overview",
            },
        )
        group = ET.SubElement(
            link,
            tag("g"),
            {
                "data-model": key,
                "class": role,
                "fill": colours["fill"],
                "stroke": colours["stroke"],
                "color": colours["color"],
                "stroke-width": "1.5",
            },
        )
        x, y, width, box_height = node["box"]
        ET.SubElement(
            group,
            tag("rect"),
            {"x": str(x), "y": str(y), "width": str(width), "height": str(box_height)},
        )
        if notation["roles"][role]["shape"] == "equipment":
            ET.SubElement(
                group,
                tag("rect"),
                {
                    "x": str(x + 4),
                    "y": str(y + 4),
                    "width": str(width - 8),
                    "height": str(box_height - 8),
                    "fill": "none",
                },
            )
        lines = textwrap.wrap(model["elements"][key]["name"], max(20, int(width / 11)))
        require(len(lines) <= 2, "Overview label needs layout adjustment: " + key)
        for i, line in enumerate(lines):
            ET.SubElement(
                group,
                tag("text"),
                {"x": str(x + width / 2), "y": str(y + 28 + i * 21), "class": "node-title"},
            ).text = line
        ET.SubElement(
            group,
            tag("text"),
            {"x": str(x + width / 2), "y": str(y + box_height - 15), "class": "note"},
        ).text = node["note"]
    ET.SubElement(
        svg, tag("text"), {"x": "480", "y": str(height - 93), "class": "note", "color": "#1f2937"}
    ).text = view["coverage"]
    validate_model_roles(svg, root, model)
    legend(svg, root, height, view["footer"])
    ET.indent(svg, space="  ")
    return ET.tostring(svg, encoding="unicode") + "\n"


def overview_outputs(root, model):
    views = json.loads((root / LAYOUT).read_text(encoding="utf-8"))["views"]
    require(
        {v["output"] for v in views} == {p.as_posix() for p in OVERVIEW_OUTPUTS},
        "Unexpected overview output ownership",
    )
    check_overviews(root, model, views)
    return {Path(v["output"]): draw(root, model, v) for v in views}
