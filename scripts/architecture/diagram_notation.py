"""Reusable role key for curated architecture views; palette values remain project-owned."""

import json
import math
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"


def tag(name):
    return "{" + NS + "}" + name


def stick_actor(parent, x, y, scale=1):
    """Shared use-case actor glyph, centred at the participation line."""
    glyph = ET.SubElement(parent, tag("g"), {
        "class": "actor-symbol", "transform": f"translate({x} {y}) scale({scale})",
        "stroke-width": "1.8", "stroke-linecap": "round", "stroke-linejoin": "round",
    })
    ET.SubElement(glyph, tag("circle"), {"cx": "0", "cy": "-29", "r": "9"})
    ET.SubElement(glyph, tag("path"), {
        "d": "M0 -20 V18 M-26 0 H26 M0 18 L-24 46 M0 18 L24 46", "fill": "none",
    })
    return glyph


def legend(svg, root, height, footer_text=None):
    notation = json.loads((root / "scripts/architecture/config/views/notation.json").read_text(encoding="utf-8"))
    palette = json.loads((root / notation["palette"]).read_text(encoding="utf-8"))["roles"]
    used = set()
    for group in svg.iter(tag("g")):
        if group.get("data-model") or group.get("data-models") or group.get("data-context"):
            role = group.get("class")
            role = notation["aliases"].get(role, role)
            if role not in notation["roles"]:
                raise ValueError("No shared notation for role: " + str(role))
            used.add(role)
    rows = math.ceil(len(used) / 4)
    key = ET.SubElement(svg, tag("g"), {"class": "legend", "id": "Legend"})
    for i, role in enumerate(r for r in notation["roles"] if r in used):
        definition = notation["roles"][role]
        colours = palette[definition.get("paletteRole", role)]
        x, y = 30 + (i % 4) * 230, height - 38 - (rows - 1 - i // 4) * 25
        symbol = ET.SubElement(
            key,
            tag("g"),
            {
                "data-role": role,
                "fill": colours["fill"],
                "stroke": colours["stroke"],
                "stroke-dasharray": colours.get("stroke-dasharray", "none"),
            },
        )
        shape = definition["shape"]
        if shape == "stickFigure":
            stick_actor(symbol, x + 15, y - 8, .24)
        elif shape == "hexagon":
            ET.SubElement(
                symbol,
                tag("polygon"),
                {
                    "points": f"{x+5},{y-15} {x+25},{y-15} {x+30},{y-7} {x+25},{y+1} {x+5},{y+1} {x},{y-7}"
                },
            )
        elif shape == "cylinder":
            ET.SubElement(
                symbol,
                tag("path"),
                {
                    "d": f"M{x} {y-12} C{x} {y-19} {x+30} {y-19} {x+30} {y-12} L{x+30} {y-2} C{x+30} {y+5} {x} {y+5} {x} {y-2} Z"
                },
            )
            ET.SubElement(
                symbol,
                tag("path"),
                {"d": f"M{x} {y-12} C{x} {y-5} {x+30} {y-5} {x+30} {y-12}", "fill": "none"},
            )
        elif shape == "ellipse":
            ET.SubElement(
                symbol, tag("ellipse"), {"cx": str(x + 15), "cy": str(y - 7), "rx": "15", "ry": "9"}
            )
        elif shape == "equipment":
            ET.SubElement(
                symbol, tag("rect"), {"x": str(x), "y": str(y - 15), "width": "30", "height": "18"}
            )
            ET.SubElement(
                symbol,
                tag("rect"),
                {"x": str(x + 3), "y": str(y - 12), "width": "24", "height": "12", "fill": "none"},
            )
        elif shape in ("rectangle", "boundary"):
            ET.SubElement(
                symbol, tag("rect"), {"x": str(x), "y": str(y - 15), "width": "30", "height": "18"}
            )
        else:
            raise ValueError("Unsupported shared shape: " + shape)
        label = ET.SubElement(key, tag("text"), {"x": str(x + 117), "y": str(y)})
        label.text = definition["label"]
    footer = ET.SubElement(key, tag("text"), {"x": "480", "y": str(height - 12)})
    footer.text = (
        footer_text
        or "Solid arrows: requests / I/O | Dotted outline: grouping | Shared project notation"
    )


def validate_model_roles(svg, root, model):
    """Reject cross-view role drift using native reusable types, not product names."""
    bindings = json.loads(
        (root / "scripts/architecture/config/views/software-intake/roles.json").read_text(encoding="utf-8")
    )
    notation = json.loads((root / "scripts/architecture/config/views/notation.json").read_text(encoding="utf-8"))
    types = {e["from"]: e["to"] for e in model["edges"] if e["kind"] == "typed-by"}
    for node in svg.iter(tag("g")):
        keys = (node.get("data-model") or node.get("data-models") or "").split()
        if not keys:
            continue
        expected = {bindings[types[k]] for k in keys if types.get(k) in bindings}
        role = notation["aliases"].get(node.get("class"), node.get("class"))
        children = [c for c in node.iter(tag("g")) if c is not node and c.get("data-model")]
        # An expanded collection uses a grouping boundary; its members keep their roles.
        if role == "group" and children:
            continue
        if not expected:
            continue
        if expected != {role}:
            raise ValueError("Inconsistent visual role for " + ", ".join(keys) + ": " + str(role))
        shape = notation["roles"][role]["shape"]
        element = {
            "rectangle": "rect",
            "boundary": "rect",
            "equipment": "rect",
            "hexagon": "polygon",
            "cylinder": "path",
        }[shape]
        # Navigation may wrap this node's symbol. Do not borrow a nested model element's shape.
        own = [symbol for child in node for symbol in (list(child) if child.tag == tag("a") else [child])]
        shapes = [child for child in own if child.tag in {tag("rect"), tag("polygon"), tag("path")}]
        if not shapes or shapes[0].tag != tag(element):
            raise ValueError("Inconsistent visual shape for " + ", ".join(keys))
