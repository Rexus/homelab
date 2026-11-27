"""Script-free linked SVG pages; native named views keep related concerns in one asset."""

from pathlib import Path
import textwrap
import xml.etree.ElementTree as ET
from diagram_notation import tag
from design_context import relative

SYSTEM = "architecture/generated/HomelabSystemOverview.svg"
INTAKE = "architecture/generated/software-intake/SoftwareIntakeLogicalDesign.svg"
SCENARIOS = "architecture/generated/software-intake/SoftwareIntakeUseCases.svg"
FUNCTIONS = "architecture/generated/software-intake/SoftwareIntakeFunctions.svg"
LOGICAL = "architecture/generated/software-intake/SoftwareIntakeLogicalDesign.svg"
SOLUTION = "architecture/generated/software-intake/solution/SoftwareIntakeSolutionDesign.svg"
RESOURCES = "architecture/generated/software-intake/solution/SoftwareIntakeResources.svg"


def slug(label):
    return label.lower().replace(" ", "-")



def text(parent, label, x, y, size=16, anchor="start", weight="normal"):
    ET.SubElement(parent, tag("text"), {
        "x": str(x), "y": str(y), "style": f"font:{weight} {size}px Arial,sans-serif;"
        f"text-anchor:{anchor};fill:#1f2937;stroke:none",
    }).text = label


def link(parent, origin, target, label=None):
    a = ET.SubElement(parent, tag("a"), {"href": relative(origin, target), "target": "_top"})
    if label:
        a.set("aria-label", label)
        ET.SubElement(a, tag("title")).text = label
    return a


def card(parent, origin, x, y, width, title, detail="", target=None, key=None, colour=None):
    lines = textwrap.wrap(detail, max(20, int((width - 30) / 8)), break_long_words=True)
    titles = textwrap.wrap(title, max(18, int((width - 30) / 9)), break_long_words=True)
    height = 22 + 22 * len(titles) + 20 * len(lines) + 12
    owner = link(parent, origin, target, title) if target else parent
    g = ET.SubElement(owner, tag("g"), {"class": "explorer-card"})
    if key:
        g.set("data-asset" if "/" in key else "data-element", key)
    fill, stroke = colour or ("#f8fafc", "#64748b")
    ET.SubElement(g, tag("rect"), {"x": str(x), "y": str(y), "width": str(width),
        "height": str(height), "rx": "4", "fill": fill, "stroke": stroke})
    for n, value in enumerate(titles):
        text(g, value, x + 15, y + 25 + 22*n, 17, weight="bold")
    for n, value in enumerate(lines):
        text(g, value, x + 15, y + 27 + 22*len(titles) + 20*n, 15)
    return height


def grid(parent, origin, y, rows):
    for start in range(0, len(rows), 2):
        heights = [card(parent, origin, 30 + i*460, y, 440, *row)
                   for i, row in enumerate(rows[start:start+2])]
        y += max(heights) + 12
    return y


def assets(parent, origin, y, groups, impact_links=None):
    """Asset links are compact attachments, not a row of runtime component boxes."""
    for start in range(0, len(groups), 2):
        heights = []
        for column, (heading, values) in enumerate(groups[start:start+2]):
            x = 30 + column*460
            group = ET.SubElement(parent, tag("g"), {"class": "explorer-card"})
            box = ET.SubElement(group, tag("rect"), {"x": str(x), "y": str(y), "width": "440",
                "height": "80", "fill": "#f8fafc", "stroke": "#64748b", "rx": "4"})
            text(group, heading, x+15, y+26, 17, weight="bold")
            yy = y+52
            for value in values:
                path, _, symbol = value.partition("::")
                label = symbol or "/".join(Path(path).parts[-3:])
                a = link(group, origin, path, value)
                impact_target = (impact_links or {}).get(value)
                if impact_target:
                    jump = link(group, origin, impact_target, "Impact: " + value)
                    jump.set("data-impact", value)
                    ET.SubElement(jump, tag("rect"), {"x": str(x+355), "y": str(yy-15),
                        "width": "72", "height": "22", "fill": "transparent"})
                    text(jump, "Impact", x+390, yy, 13, "middle")
                for line in textwrap.wrap(label, 39 if impact_target else 48, break_long_words=True):
                    text(a, line, x+15, yy, 14)
                    yy += 18
                yy += 9
            height = yy-y+6
            box.set("height", str(height))
            heights.append(height)
        y += max(heights) + 12
    return y


def toolbar(svg, origin, height, entries):
    ET.SubElement(svg, tag("rect"), {"x": "0", "y": str(height), "width": "960",
        "height": "56", "fill": "#eef2f6"})
    for i, (label, target) in enumerate(entries):
        a = link(svg, origin, target, label)
        x = (i + .5) * 960 / len(entries)
        width = min(200, 960 / len(entries) - 10)
        ET.SubElement(a, tag("rect"), {"x": str(x - width/2), "y": str(height+7),
            "width": str(width), "height": "42", "fill": "transparent"})
        text(a, label, x, height+33, 15, "middle")


def page(origin, title, subtitle, documentation, up=INTAKE):
    svg = ET.Element(tag("svg"), {"viewBox": "0 0 960 800", "role": "img"})
    ET.SubElement(svg, tag("title")).text = title
    ET.SubElement(svg, tag("style")).text = "a{cursor:pointer}a:hover rect,a:focus rect{stroke-width:2.5px}"
    ET.SubElement(svg, tag("rect"), {"width": "960", "height": "800", "fill": "white"})
    text(svg, title, 30, 35, 24, weight="bold")
    y = 65
    for line in textwrap.wrap(subtitle, 110):
        text(svg, line, 30, y, 15)
        y += 20
    return svg, y + 15, [("System Overall", SYSTEM), ("Logical design" if up == INTAKE else "Up to overview", up),
                         ("HTTP example", SCENARIOS + "#SC-http-miss"), ("Documentation", documentation)]


def finish(svg, origin, y, navigation):
    height = y + 10
    toolbar(svg, origin, height, navigation)
    height += 56
    svg.set("viewBox", f"0 0 960 {height}")
    next(e for e in svg if e.tag == tag("rect")).set("height", str(height))
    return svg


def book(pages):
    """Each fragment selects its own viewport, with navigation inside that viewport."""
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    first = pages[0][1].get("viewBox")
    svg = ET.Element(tag("svg"), {"viewBox": first, "role": "img"})
    ET.SubElement(svg, tag("style")).text = (
        "svg[data-view]{visibility:hidden}view:target+svg[data-view]{visibility:visible}"
        "svg:not(:has(>view:target))>svg[data-view]:first-of-type{visibility:visible}"
    )
    offset = 0
    for key, content in pages:
        height = float(content.get("viewBox").split()[3])
        ET.SubElement(svg, tag("view"), {"id": key, "viewBox": f"0 {offset:g} 960 {height:g}"})
        content.set("x", "0")
        content.set("y", str(offset))
        content.set("width", "960")
        content.set("height", str(height))
        content.set("data-view", key)
        svg.append(content)
        offset += height + 30
    ET.indent(svg, space="  ")
    return ET.tostring(svg, encoding="unicode") + "\n"


def add_navigation(source, origin, entries, related=(), caption=None):
    svg = ET.fromstring(source)
    height = float(svg.get("viewBox").split()[3])
    width = float(svg.get("viewBox").split()[2])
    # Existing intake figures share a 960-wide view grammar.
    if width != 960:
        raise ValueError("Adapt navigation to the diagram width: " + str(origin))
    if caption:
        ET.SubElement(svg, tag("rect"), {"y": str(height), "width": "960", "height": "30", "fill": "#eef2f6"})
        text(svg, caption, 24, height+21, 14, weight="bold")
        height += 30
    toolbar(svg, origin, height, entries)
    height += 56
    if related:
        toolbar(svg, origin, height, related)
        height += 56
    svg.set("viewBox", f"0 0 960 {height:g}")
    ET.indent(svg, space="  ")
    return ET.tostring(svg, encoding="unicode") + "\n"


def validate_links(root, outputs):
    """Reject stale diagram destinations before writing a partly navigable bundle."""
    for path, value in outputs.items():
        if path.suffix != ".svg":
            continue
        svg = ET.fromstring(value)
        for a in svg.iter(tag("a")):
            if any(e is not a and e.tag == tag("a") for e in a.iter()):
                raise ValueError("Nested SVG link: " + str(path))
            href = a.get("href", "")
            name, _, fragment = href.partition("#")
            destination = (root / path.parent / name).resolve() if name else (root / path).resolve()
            if not destination.is_relative_to(root.resolve()):
                raise ValueError("Escaping SVG destination: " + href)
            key = destination.relative_to(root.resolve())
            if key not in outputs and not destination.is_file():
                raise ValueError("Missing SVG destination: " + href)
            if fragment and destination.suffix == ".svg":
                target = ET.fromstring(outputs[key]) if key in outputs else ET.parse(destination).getroot()
                if not any(e.get("id") == fragment for e in target.iter()):
                    raise ValueError("Missing SVG fragment: " + href)
