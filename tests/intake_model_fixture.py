"""Model/IaC drift, reusable contracts, diagram relationships and generated manual ownership."""

from argparse import Namespace
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM

sys.path.insert(0, str(UPSTREAM / "scripts/architecture"))
from intake_sources import MODEL, VIEWS, GENERATED
from intake_model import impact, validate_trace
from intake_views import render
from software_intake import run, OUTPUTS, CASE_PLAN
from system_overall import OVERVIEW_OUTPUTS


class IntakeModelFixture(unittest.TestCase):
    def setUp(self):
        (UPSTREAM / ".tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="intake-contract-", dir=UPSTREAM / ".tmp")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        snapshot = json.loads((UPSTREAM / GENERATED / "model-index.json").read_text())
        self.model = snapshot["model"]
        files = set(snapshot["sources"]) | {
            str(p.relative_to(UPSTREAM)) for p in (UPSTREAM / GENERATED).rglob("*") if p.is_file()
        }
        files.update(p.relative_to(UPSTREAM).as_posix() for p in (UPSTREAM / "architecture/views").rglob("*") if p.is_file())
        files.add(str(CASE_PLAN))
        files.update(str(p) for p in OUTPUTS.values())
        files.update(str(p) for p in OVERVIEW_OUTPUTS)
        scopes = json.loads(
            (UPSTREAM / "architecture/views/design-context.json").read_text(encoding="utf-8")
        )["scopes"]
        files.update(scope["svg"] for scope in scopes if scope.get("svg"))
        files.add("architecture/generated/design-context.json")
        # The fixture owns the same navigable bundle, including supporting document assets.
        for name in list(files):
            path = UPSTREAM / name
            if path.suffix != ".svg":
                continue
            for anchor in ET.parse(path).iter("{http://www.w3.org/2000/svg}a"):
                target = (path.parent / anchor.get("href").split("#")[0]).resolve()
                if target.is_file() and target.is_relative_to(UPSTREAM):
                    files.add(target.relative_to(UPSTREAM).as_posix())
        for name in files:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(UPSTREAM / name, target)

    def change(self, name, before, after):
        path = self.root / name
        source = path.read_text(encoding="utf-8")
        self.assertIn(before, source)
        path.write_text(source.replace(before, after), encoding="utf-8")

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return run(self.root, "check", Namespace())
