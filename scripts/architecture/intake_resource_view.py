"""A curated resource view selecting native relationships across subsystem boundaries."""

import json
import textwrap
import xml.etree.ElementTree as ET
from diagram_notation import tag, legend, validate_model_roles
from intake_sources import VIEWS, require


def resource_view(root, model, inputs):
    view = json.loads((root / VIEWS / "resources.json").read_text(encoding="utf-8"))
    notation = json.loads((root / "architecture/views/notation.json").read_text(encoding="utf-8"))
    palette = json.loads((root / notation["palette"]).read_text(encoding="utf-8"))["roles"]
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    svg = ET.Element(
        tag("svg"), {"viewBox": "0 0 960 960", "role": "img", "aria-labelledby": "title desc"}
    )
    ET.SubElement(svg, tag("title"), {"id": "title"}).text = (
        "Software intake and its shared resource dependencies"
    )
    ET.SubElement(svg, tag("desc"), {"id": "desc"}).text = (
        "One intake design uses virtual execution, local disk storage and guest networking provided by "
        "the shared platform. Those providers map to physical servers, drives and network equipment. "
        "The optional storage network is shown as context, not a dependency of local cache disks."
    )
    ET.SubElement(svg, tag("rect"), {"width": "960", "height": "960", "fill": "white"})
    ET.SubElement(svg, tag("style")).text = (
        "text{font:16px Arial,sans-serif;fill:currentColor;stroke:none;text-anchor:middle}"
        ".heading{font-size:22px;font-weight:600}.label{font-size:13px}.note{font-size:14px}"
        ".legend text{font-size:12px}"
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
    members = sorted(inputs["members"])
    selections = {"disks": ["DISK-" + m for m in members], "vms": ["VM-" + m for m in members]}
    nodes = {}
    for spec in view["nodes"]:
        keys = selections.get(spec["key"], [spec["key"]])
        require(all(k in model["elements"] for k in keys), "Unknown resource-view identity")
        nodes[spec["key"]] = keys
    # Every selected edge must exist natively. Aggregates require coverage of every endpoint.
    for edge in view["edges"]:
        left, right = nodes[edge["from"]], nodes[edge["to"]]
        relations = [
            r
            for r in model["edges"]
            if r["from"] in left and r["to"] in right and r["kind"] == edge["kind"]
        ]
        require(
            {r["from"] for r in relations} == set(left) and {r["to"] for r in relations} == set(right),
            "Missing or reversed resource-view relationship: " + edge["from"] + " -> " + edge["to"],
        )
        attrs = {"d": edge["path"], "fill": "none", "stroke": "#627581", "stroke-width": "1.6"}
        if edge["kind"] != "connected-to":
            attrs.update({"stroke-dasharray": "6 4", "marker-end": "url(#dep)"})
        ET.SubElement(
            svg, tag("path"), {**attrs, "stroke": "white", "stroke-width": "6", "marker-end": "none"}
        )
        ET.SubElement(
            svg,
            tag("path"),
            {**attrs, "data-relations": " ".join(r["id"] for r in relations if r.get("id")), "data-relationships": json.dumps(relations)},
        )
        x, y = edge["label_at"]
        width = len(edge["label"]) * 7 + 14
        ET.SubElement(
            svg,
            tag("rect"),
            {
                "x": str(x - width / 2),
                "y": str(y - 14),
                "width": str(width),
                "height": "20",
                "fill": "white",
            },
        )
        ET.SubElement(svg, tag("text"), {"x": str(x), "y": str(y), "class": "label"}).text = edge[
            "label"
        ]
    for spec in view["nodes"]:
        key = spec["key"]
        keys = nodes[key]
        role = spec["role"]
        colours = palette[notation["roles"][role].get("paletteRole", role)]
        identity = "data-model" if len(keys) == 1 else "data-models"
        group = ET.SubElement(
            svg,
            tag("g"),
            {
                identity: " ".join(keys),
                "class": role,
                "fill": colours["fill"],
                "stroke": colours["stroke"],
                "color": colours["color"],
                "stroke-width": "1.5",
            },
        )
        x, y = spec["at"]
        width, height = 264, 76
        shape = notation["roles"][role]["shape"]
        if shape == "cylinder":
            ET.SubElement(
                group,
                tag("path"),
                {
                    "d": f"M{x} {y+12} C{x} {y-4} {x+width} {y-4} {x+width} {y+12} L{x+width} {y+height-12} C{x+width} {y+height+4} {x} {y+height+4} {x} {y+height-12} Z"
                },
            )
            ET.SubElement(
                group,
                tag("path"),
                {"d": f"M{x} {y+12} C{x} {y+28} {x+width} {y+28} {x+width} {y+12}", "fill": "none"},
            )
        else:
            ET.SubElement(
                group,
                tag("rect"),
                {
                    "x": str(x),
                    "y": str(y),
                    "width": str(width),
                    "height": str(height),
                    "stroke-dasharray": "4 3" if spec.get("optional") else "none",
                },
            )
            if shape == "equipment":
                ET.SubElement(
                    group,
                    tag("rect"),
                    {
                        "x": str(x + 4),
                        "y": str(y + 4),
                        "width": str(width - 8),
                        "height": str(height - 8),
                        "fill": "none",
                    },
                )
        value = model["elements"][keys[0]]["name"]
        if key == "vms":
            value = "Cache VMs: " + ", ".join(members)
        if key == "disks":
            value = "Per-VM virtual cache disk"
        if key == "R-Pair":
            value = "Squid + keepalived"
        lines = textwrap.wrap(value, 28)
        if spec.get("optional"):
            lines += ["Optional platform context"]
        require(len(lines) <= 3, "Resource-view label needs layout adjustment")
        start = y + (45 if shape == "cylinder" else 40) - (len(lines) - 1) * 10
        for i, line in enumerate(lines):
            ET.SubElement(group, tag("text"), {"x": str(x + 132), "y": str(start + i * 20)}).text = line
    for y, value, cls in (
        (31, "Software intake | connected design and resource providers", "heading"),
        (
            58,
            "Follow responsibilities into realization, then required resources and their physical backing.",
            "note",
        ),
        (
            869,
            "Shared platform contracts are mapped context; physical counts, ports and placement remain site-owned.",
            "note",
        ),
    ):
        ET.SubElement(svg, tag("text"), {"x": "480", "y": str(y), "class": cls}).text = value
    validate_model_roles(svg, root, model)
    legend(
        svg,
        root,
        960,
        "Dashed arrows: mappings / dependencies | Solid line: physical attachment | No request traffic shown",
    )
    ET.indent(svg, space="  ")
    return ET.tostring(svg, encoding="unicode") + "\n"
