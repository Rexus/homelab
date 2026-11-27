"""A compact tailored use-case view; native membership owns boundary and associations."""

import json
import textwrap
import xml.etree.ElementTree as ET
from diagram_notation import tag, legend, stick_actor
from intake_sources import VIEWS, require


def use_case_view(root, model, view=None):
    if view is None:
        view = json.loads((root / VIEWS / "use-cases.json").read_text(encoding="utf-8"))
    case = model["use_cases"][view["case"]]
    actors = view["actors"]
    require(
        len(actors) == 2 and len(set(actors)) == 2 and set(actors) == set(case["actors"]),
        "Use-case view must show both external actors exactly once; adapt layout for more actors",
    )
    require(view["width"] == 960 and view["height"] == 430, "Use-case layout supports a 960 by 430 canvas")
    notation = json.loads((root / "scripts/architecture/config/views/notation.json").read_text(encoding="utf-8"))
    human_types = set(notation.get("humanActorTypes", []))
    human_actors = {actor for actor in actors if any(
        edge["from"] == case["bindings"][actor] and edge["kind"] == "typed-by"
        and edge["to"] in human_types for edge in model["edges"]
    )}
    palette = json.loads((root / notation["palette"]).read_text(encoding="utf-8"))["roles"]
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    svg = ET.Element(tag("svg"), {"viewBox": "0 0 960 430", "role": "img", "aria-labelledby": "title desc"})
    ET.SubElement(svg, tag("title"), {"id": "title"}).text = view.get("title", model["elements"][view["case"]]["name"])
    svg.set("data-subject", case["subject"])
    ET.SubElement(svg, tag("desc"), {"id": "desc"}).text = view.get("description", (
        "External update client and approved source participate in a controlled-supply use case. "
        "Associations show participation, not network routes. Consumer verification remains external."
    ))
    ET.SubElement(svg, tag("rect"), {"width": "960", "height": "430", "fill": "#ffffff"})
    ET.SubElement(svg, tag("style")).text = (
        "text{font-family:Arial,sans-serif;font-size:17px;text-anchor:middle;fill:#1f2937}"
        ".legend text{font-size:13px}.caption{font-size:15px}"
    )

    def group(key, role):
        colours = palette[notation["roles"][role].get("paletteRole", role)]
        return ET.SubElement(
            svg,
            tag("g"),
            {
                "data-model": key,
                "class": role,
                "fill": colours["fill"],
                "stroke": colours["stroke"],
                "stroke-width": "1.6",
            },
        )

    def label(parent, value, x, y, width):
        lines = textwrap.wrap(value, width=width, break_long_words=False)
        require(len(lines) <= 3, "Use-case label exceeds the curated layout; adapt its view")
        for i, line in enumerate(lines):
            ET.SubElement(
                parent,
                tag("text"),
                {"x": str(x), "y": str(y + i * 23 - (len(lines) - 1) * 11.5), "stroke": "none"},
            ).text = line

    subject = group(case["subject"], "subject")
    subject.set("data-relationships", json.dumps([{ "from": view["case"], "to": case["subject"], "kind": "has-subject" }]))
    ET.SubElement(subject, tag("rect"), {"x": "260", "y": "62", "width": "440", "height": "248", "rx": "5"})
    label(subject, model["elements"][case["subject"]]["name"], 480, 95, 36)
    for index, actor in enumerate(actors):
        left, right = ((156 if actor in human_actors else 220, 295) if index == 0
                       else (665, 804 if actor in human_actors else 740))
        ET.SubElement(
            svg,
            tag("line"),
            {
                "data-relationships": json.dumps([{ "from": view["case"], "to": actor, "kind": "has-actor" }]),
                "x1": str(left),
                "x2": str(right),
                "y1": "195",
                "y2": "195",
                "stroke": "#627581",
                "stroke-width": "1.6",
            },
        )
    goal = group(view["case"], "goal")
    ET.SubElement(goal, tag("ellipse"), {"cx": "480", "cy": "195", "rx": "185", "ry": "74"})
    label(goal, model["elements"][view["case"]]["name"], 480, 190, 29)
    for actor, x in zip(actors, (40, 740)):
        if actor in human_actors:
            block = group(actor, "useCaseActor")
            stick_actor(block, x + 90, 195)
            label(block, model["elements"][actor]["name"], x + 90, 270, 20)
        else:
            block = group(actor, "useCaseSystemActor")
            ET.SubElement(block, tag("rect"), {
                "x": str(x), "y": "152", "width": "180", "height": "86", "rx": "5",
            })
            label(block, "«actor»", x + 90, 177, 20)
            label(block, model["elements"][actor]["name"], x + 90, 209, 20)
    ET.SubElement(svg, tag("text"), {"x": "480", "y": "345", "class": "caption"}).text = view.get(
        "caption", "Expected use · Consumer verification remains outside the supply boundary"
    )
    legend(svg, root, 430, "Solid line: participation · Tailored model-derived use-case view")
    return ET.tostring(svg, encoding="unicode") + "\n"
