"""Protect folder/model navigation and existing resource bindings during refinement."""

import copy
import json
import xml.etree.ElementTree as ET
from intake_model_fixture import IntakeModelFixture
from intake_model import impact
from system_overall import LAYOUT, overview_outputs, check_overviews


class SystemOverallContracts(IntakeModelFixture):
    def views(self):
        return json.loads((self.root / LAYOUT).read_text(encoding="utf-8"))["views"]

    def test_root_reuses_existing_parts_and_each_box_opens_its_child_design(self):
        outputs = overview_outputs(self.root, self.model)
        svg = ET.fromstring(outputs[next(p for p in outputs if p.name == "system-overall.svg")])
        links = svg.findall(".//{http://www.w3.org/2000/svg}a")
        self.assertEqual(len(links), 5)
        for link in links:
            target = self.root / "architecture/views" / link.get("href")
            self.assertTrue(target.is_file())
            self.assertIn("../README.md", target.read_text(encoding="utf-8"))
        affected = set(impact(self.model, "P-servers"))
        self.assertTrue(
            {"SYS-platform", "SYS-intake", "SYS-homelab", "L-Proxy", "UC-update"} <= affected
        )

    def test_overview_cannot_hide_a_main_subsystem(self):
        views = self.views()
        views[0]["nodes"].pop()
        with self.assertRaisesRegex(ValueError, "cover its direct subsystem"):
            check_overviews(self.root, self.model, views)

    def test_root_box_cannot_skip_the_child_folder_or_use_a_broken_link(self):
        views = self.views()
        views[0]["nodes"][0]["href"] = "missing/README.md"
        with self.assertRaisesRegex(ValueError, "Missing or escaping"):
            check_overviews(self.root, self.model, views)
        views[0]["nodes"][0]["href"] = "../design/software-intake/policy-proxy/README.md"
        with self.assertRaisesRegex(ValueError, "direct child design"):
            check_overviews(self.root, self.model, views)

    def test_overview_cannot_become_disconnected_from_existing_platform(self):
        model = copy.deepcopy(self.model)
        model["edges"] = [
            e for e in model["edges"] if not (e["from"] == "SYS-platform" and e["kind"] == "bound-to")
        ]
        with self.assertRaisesRegex(ValueError, "lost its existing subsystem bindings"):
            check_overviews(self.root, model, self.views())

    def test_overview_cannot_invent_or_drop_a_selected_dependency(self):
        model = copy.deepcopy(self.model)
        model["edges"] = [e for e in model["edges"] if e.get("id") != "SYS-intake-resources"]
        with self.assertRaisesRegex(ValueError, "missing or out-of-scope relationship"):
            check_overviews(self.root, model, self.views())

    def test_overview_cannot_hide_an_existing_boundary_dependency(self):
        views = self.views()
        views[0]["edges"].pop()
        with self.assertRaisesRegex(ValueError, "cover its selected boundary relationships"):
            check_overviews(self.root, self.model, views)
