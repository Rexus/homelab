"""Apply model identities to the two established SVG layouts; preserve their visual grammar."""

import copy
import json
import xml.etree.ElementTree as ET
from intake_sources import VIEWS, require
from diagram_notation import legend, validate_model_roles

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def tag(name):
    return "{" + NS + "}" + name


def text(parent, x, y, value, **attrs):
    ET.SubElement(parent, tag("text"), {"x": str(x), "y": str(y), **attrs}).text = value


def render(root, model, inputs, kind):
    svg = ET.parse(root / VIEWS / (kind + ".layout.svg")).getroot()
    nodes = {e.get("id"): e for e in svg.iter() if e.get("id")}
    palette = json.loads((root / "docs/08-reference/diagrams/palette.json").read_text(encoding="utf-8"))[
        "roles"
    ]
    style = svg.find(".//" + tag("style"))
    style.text = "\n".join(
        [
            "svg {font:15px Arial,sans-serif;background:#fff;}",
            "text {fill:currentColor;stroke:none;text-anchor:middle;}",
            *[
                "." + name + " {" + ";".join(k + ":" + v for k, v in r.items()) + ";}"
                for name, r in palette.items()
            ],
            ",".join("." + name for name, r in palette.items() if "stroke-dasharray" not in r)
            + " {stroke-dasharray:none;}",
            ".connection {fill:none;stroke:#627581;stroke-width:1.5;marker-end:url(#arrow);}",
            ".edge-label {fill:#1f2937;font-size:13px;}",
            ".mount {font-size:12px;}",
            ".legend {fill:#1f2937;font-size:12px;}",
        ]
    )
    if kind == "solution":
        prototype = nodes["CacheA"]
        pair = nodes["Pair"]
        pair.remove(prototype)
        members = sorted(
            k for k, e in model["elements"].items() if k.startswith("VM-") and e["kind"] == "PartUsage"
        )
        require(
            {k[3:] for k in members} == set(inputs["members"]),
            "Model realization and selected IaC members disagree",
        )
        for i, key in enumerate(members):
            member = copy.deepcopy(prototype)
            name = model["elements"][key]["name"]
            suffix = chr(65 + i)
            aliases = {"CacheA": "Cache" + suffix, "S1": "S" + str(i + 1), "D1": "D" + str(i + 1), "Content1": "Content" + str(i + 1)}
            semantic = {"CacheA": key, "S1": "RUN-" + name, "D1": "DISK-" + name, "Content1": "CONTENT-" + name}
            for e in member.iter():
                old = e.get("id")
                if old in aliases:
                    e.set("id", aliases[old])
                    e.set("data-model", semantic[old])
                for attr in ("data-from", "data-to"):
                    if e.get(attr) in aliases:
                        e.set(attr, aliases[e.get(attr)])
                if e.get("data-relation"):
                    e.set("data-relation", "IO-" + name)
                if e.text:
                    e.text = (
                        e.text.replace("{{member}}", name)
                        .replace("{{disk}}", inputs["members"][name]["_cache_disk"]["interface"])
                        .replace("{{mount}}", inputs["config"]["cache_squid_cache_dir"])
                    )
            if i:
                member.set("transform", f"translate(0 {i*175})")
            pair.append(member)
        delta = (len(members) - 2) * 175
        for key in ("T2", "Edge", "Pair"):
            rect = nodes[key].find(tag("rect"))
            rect.set("height", str(float(rect.get("height")) + delta))
        nodes["Consumers"].set("transform", f"translate(0 {delta})")
        # Keep the listener beside the member stack. Requests still enter from below.
        request = next(e for e in svg.iter() if e.get("data-relation") == "R-request")
        request.set("d", f"M400 {590+delta} L400 425")
        height = 800 + delta
        # Move the incoming request annotation with its consumers when the stack grows.
        for e in svg:
            if e.tag in (tag("rect"), tag("text")) and float(e.get("y", "0")) in (540, 556):
                e.set("y", str(float(e.get("y")) + delta))
        nodes["Edge"].find(tag("text")).text = "Network membership / " + inputs["network"]
    else:
        height = 800
        for e in svg.iter(tag("g")):
            key = e.get("data-model")
            if not key:
                continue
            labels = [label for label in e.findall(tag("text")) if label.get("class") not in ("edge-label", "kind-label")]
            name = model["elements"][key]["name"]
            if len(labels) == 1:
                labels[0].text = name
            elif len(labels) == 2:
                words = name.split()
                split = min(
                    range(1, len(words)),
                    key=lambda n: abs(len(" ".join(words[:n])) - len(" ".join(words[n:]))),
                )
                labels[0].text = " ".join(words[:split])
                labels[1].text = " ".join(words[split:])
    if kind == "logical":
        text(nodes["Sources"], 125, 146, "«external source role»", **{"font-size": "10px", "class": "kind-label"})
    svg.set("height", str(height))
    svg.set("viewBox", f"0 0 960 {height}")
    parents = {child: parent for parent in svg.iter() for child in parent}
    element_ids = {e.get("id"): e.get("data-model") for e in svg.iter() if e.get("data-model")}
    owners = {(e["from"], e["to"]) for e in model["edges"] if e["kind"] == "contains"}
    relations = {e.get("id"): e for e in model["edges"] if e["kind"] == "flow"}
    for e in svg.iter():
        key = e.get("data-model")
        if key:
            require(key in model["elements"], f"Unknown diagram model identity {key}")
            ancestor = parents.get(e)
            while ancestor is not None and not ancestor.get("data-model"):
                ancestor = parents.get(ancestor)
            if ancestor is not None:
                require((ancestor.get("data-model"), key) in owners, f"Wrong model containment for {key}")
        if e.get("data-relation"):
            relation = relations.get(e.get("data-relation"))
            require(relation is not None, f'Missing model flow {e.get("data-relation")}')
            require(
                (relation["from"], relation["to"])
                == (element_ids[e.get("data-from")], element_ids[e.get("data-to")]),
                f'Drawing reverses or invents model flow {e.get("data-relation")}',
            )
    validate_model_roles(svg, root, model)
    legend(svg, root, height)
    svg.insert(
        0, ET.Comment(" Generated by scripts/architecture/software_intake.py; edit model/layout sources. ")
    )
    ET.indent(svg, space="  ")
    return ET.tostring(svg, encoding="unicode") + "\n"
