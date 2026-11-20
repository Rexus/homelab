"""Mapped foundation figure: one source, one linked host identity, explicit native coverage."""

import hashlib
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
from diagram_notation import tag
from intake_sources import require

SOURCE = Path("docs/03-deployment/foundation/bootstrap/README.md")
VIEW = Path("architecture/views/platform/hosting/bootstrap-reference.svg")
RENDERER = Path("docs/08-reference/diagrams/render-bootstrap-reference.cjs")


def source_digest(root):
    match = re.search(r"```mermaid\s*([\s\S]*?)```", (root / SOURCE).read_text(encoding="utf-8"))
    require(match is not None, "Missing owning foundation diagram")
    return hashlib.sha256(match[1].strip().encode()).hexdigest()


def validate_reference(root):
    require((root / VIEW).is_file(), "Render the foundation reference: node " + RENDERER.as_posix())
    svg = ET.parse(root / VIEW).getroot()
    require(svg.get("data-source-sha256") == source_digest(root),
            "Foundation figure changed; regenerate its reference SVG")
    require(svg.get("data-reference-source") == SOURCE.as_posix(), "Wrong foundation reference source")
    require(svg.get("data-subject") == "BOOT-host" and
            any(e.get("data-model") == "BOOT-host" for e in svg.iter(tag("g"))),
            "Foundation destination must represent the bound boot-1 participant")


def prepare_reference(root):
    try:
        validate_reference(root)
    except (ValueError, ET.ParseError):
        result = subprocess.run(["node", RENDERER.as_posix()], cwd=root, check=False)
        require(result.returncode == 0, "Foundation rendering needs DIAGRAM_PLAYWRIGHT and DIAGRAM_MERMAID; see bootstrap-use-case.md")
        validate_reference(root)
