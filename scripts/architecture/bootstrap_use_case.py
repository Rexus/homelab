"""Focused bootstrap goal; native role bindings connect to separately owned designs."""

import json
from pathlib import Path
import xml.etree.ElementTree as ET
from diagram_notation import tag
from intake_case_view import use_case_view
from intake_sources import require
from bootstrap_reference import VIEW as FOUNDATION_VIEW, validate_reference
from intake_use_cases import CASE_VIEWS, CASE_GUIDES
from svg_pages import add_navigation, link, LOGICAL, SCENARIOS

VIEW = Path(CASE_VIEWS["UC-clone"])
GUIDE = CASE_GUIDES["UC-clone"]


def outputs(root, model):
    validate_reference(root)
    view = json.loads((root / Path("scripts/architecture/config/views/platform/hosting/clone-repository.json")).read_text(encoding="utf-8"))
    case = model["use_cases"][view["case"]]
    require(case["bindings"] == {"UC-clone-host": "BOOT-host", "ACT-operator": "BOOT-operator",
                                  "ACT-intake": "SYS-intake"},
            "Bootstrap use-case navigation must follow its native subject and actor bindings")
    svg = ET.fromstring(use_case_view(root, model, view))
    targets = {"ACT-intake": LOGICAL, "UC-clone": GUIDE,
               "UC-clone-host": FOUNDATION_VIEW.as_posix()}
    for group in list(svg):
        key = group.get("data-model")
        if key in targets:
            index = list(svg).index(group)
            svg.remove(group)
            anchor = link(svg, VIEW, targets[key], model["elements"][key]["name"])
            anchor.append(group)
            svg.remove(anchor)
            svg.insert(index, anchor)
    rendered = add_navigation(ET.tostring(svg, encoding="unicode"), VIEW, [
        ("HTTPS behavior", SCENARIOS + "#SC-https"),
        ("Intake use case", "architecture/generated/software-intake/SoftwareIntakeUseCases.svg"),
        ("Documentation", GUIDE),
    ])
    return {VIEW: rendered}
