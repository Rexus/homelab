"""The SVG journey must follow native identities and survive manual ownership relocation."""

import copy
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from intake_model_fixture import IntakeModelFixture
from tier_repo_test_support import TierRepositoryTestCase
from design_context import scopes
from intake_sources import selected_inputs, trace_map
from software_intake import expected_outputs
from svg_pages import SCENARIOS, FUNCTIONS, tag, validate_links
from intake_scenario_views import function_views


class IntakeNavigation(IntakeModelFixture):
    def test_scenario_messages_open_their_native_function_and_sources(self):
        svg = ET.parse(self.root / SCENARIOS)
        scenario = svg.find('.//*[@data-view="SC-http-miss"]')
        links = {a.get("data-message"): a for a in scenario.iter(tag("a")) if a.get("data-message")}
        self.assertEqual(list(links), self.model["scenarios"]["SC-http-miss"]["messages"])
        self.assertEqual(links["H-fetch"].get("data-function"), "F-http")
        self.assertEqual(links["H-verify"].get("data-function"), "F-verify")
        functions = ET.parse(self.root / FUNCTIONS)
        selected = functions.find('.//*[@data-view="F-http"]')
        hrefs = [a.get("href") for a in selected.iter(tag("a"))]
        self.assertTrue(any(h.endswith("policy-proxy/contract.svg") for h in hrefs))
        self.assertTrue(any(h.endswith("cache_proxy/templates/squid.conf.j2") for h in hrefs))
        self.assertTrue(any(h.endswith("tests/test_tier_cache_policy.py") for h in hrefs))

    def test_function_allocation_changes_navigation_without_a_second_inventory(self):
        model = copy.deepcopy(self.model)
        for edge in model["edges"]:
            if edge["from"] == "F-http" and edge["kind"] == "allocated-to":
                edge["to"] = "L-Cache"
        svg = ET.fromstring(function_views(model, scopes(self.root), trace_map(self.root)))
        function = svg.find('.//*[@data-view="F-http"]')
        self.assertIsNotNone(function.find('.//*[@data-element="L-Cache"]'))
        self.assertIsNone(function.find('.//*[@data-element="L-Proxy"]'))

    def test_realization_exposes_terraform_and_ansible_via_native_allocation(self):
        path = self.root / "architecture/views/software-intake/sources.svg"
        pane = ET.parse(path).getroot()
        hrefs = [a.get("href") for a in pane.iter(tag("a"))]
        self.assertTrue(any(h.endswith("terraform/deployments/cache/main.tf") for h in hrefs))
        self.assertTrue(any(h.endswith("cache_proxy/tasks/squid.yml") for h in hrefs))
        self.assertEqual(sum(h.endswith("cache_proxy/templates/squid.conf.j2") for h in hrefs), 1)

    def test_broken_svg_fragment_is_rejected(self):
        records = trace_map(self.root)
        outputs = expected_outputs(self.root, self.model, selected_inputs(self.root), records)
        path = Path("architecture/views/system-overall.svg")
        outputs[path] = outputs[path].replace("functions.svg", "functions.svg#missing")
        with self.assertRaisesRegex(ValueError, "Missing SVG fragment"):
            validate_links(self.root, outputs)


class IntakeNavigationManual(TierRepositoryTestCase):
    def test_all_svg_and_source_links_survive_collection_relocation(self):
        self.generate()
        manual = self.root / "verify-architecture/docs/auto-docs"
        paths = list((manual / "architecture").rglob("*.svg"))

        source_links = []
        for path in paths:
            svg = ET.parse(path)
            for a in svg.iter(tag("a")):
                name, _, fragment = a.get("href").partition("#")
                target = (path.parent / name).resolve() if name else path.resolve()
                self.assertTrue(target.is_relative_to(self.root.resolve()), (path, name))
                self.assertTrue(target.is_file(), (path, name))
                if fragment and target.suffix == ".svg":
                    self.assertTrue(any(e.get("id") == fragment for e in ET.parse(target).iter()))
                source_links.append(target)
        self.assertTrue(any("verify-tier-2" in str(p) and p.name == "main.tf" for p in source_links))
        self.assertTrue(any(p == manual / "upstream/tests/test_tier_cache_policy.py" for p in source_links))
