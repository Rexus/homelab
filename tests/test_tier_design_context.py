"""Scoped context must preserve allocation, ownership and evidence boundaries."""

import copy
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from intake_model_fixture import IntakeModelFixture
from intake_sources import trace_map
from design_context import scopes, context


class DesignContextContracts(IntakeModelFixture):
    def setUp(self):
        super().setUp()
        self.scopes = {s["key"]: s for s in scopes(self.root)}
        self.records = trace_map(self.root)
        self.plan = json.loads(
            (self.root / "artifacts/architecture/evidence/software-intake/cases.json").read_text(encoding="utf-8")
        )

    def project(self, key, model=None):
        return context(model or self.model, self.scopes[key], self.records, self.plan)

    def test_cache_selects_its_function_and_scenarios_without_claiming_actor_obligations(self):
        data = self.project("cache")
        self.assertEqual(data["functions"], ["F-cache"])
        self.assertEqual(data["scenarios"], ["SC-http-cache-untrusted", "SC-http-hit", "SC-http-miss", "SC-http-source-failure", "SC-http-untrusted"])
        self.assertEqual(data["requirements"], ["REQ-custody"])
        self.assertEqual(data["actor_functions"], ["F-verify"])
        self.assertIn("REQ-egress", data["related_requirements"])
        self.assertNotIn("P-storage-network", data["resource_providers"])
        self.assertEqual(data["interacting_parts"], ["L-Proxy"])
        self.assertEqual(self.project("system")["interacting_parts"], ["L-Consumers", "L-Sources"])

    def test_provider_keeps_supported_functions_separate_from_owned_allocations(self):
        data = self.project("platform")
        self.assertEqual(data["functions"], [])
        self.assertEqual(data["requirements"], [])
        self.assertIn("F-admit", data["supported_functions"])
        self.assertIn("REQ-policy", data["related_requirements"])

    def test_mapped_subsystem_does_not_acquire_unrelated_intake_requirements(self):
        data = self.project("trust")
        for key in [
            "functions",
            "requirements",
            "supported_functions",
            "use_cases",
            "scenarios",
            "implementation",
        ]:
            self.assertEqual(data[key], [])

    def test_changing_native_allocation_changes_the_component_context(self):
        changed = copy.deepcopy(self.model)
        changed["edges"] = [
            e
            for e in changed["edges"]
            if not (e["from"] == "F-cache" and e["to"] == "L-Cache" and e["kind"] == "allocated-to")
        ]
        data = self.project("cache", changed)
        self.assertEqual(data["functions"], [])
        self.assertEqual(data["scenarios"], [])

    def test_focused_views_replace_repeated_context_frames(self):
        for name in ("HomelabSystemOverview.svg", "software-intake/SoftwareIntakeLogicalDesign.svg"):
            svg = ET.parse(self.root / "architecture/generated" / name)
            labels = {a.get("aria-label") for a in svg.findall(".//{http://www.w3.org/2000/svg}a")}
            self.assertTrue({"Use cases", "Requirements", "Functions", "Tests"} <= labels)
            self.assertFalse(svg.findall('.//*[@data-concern]'))
        self.assertNotIn("svg", self.scopes["trust"])
        self.assertEqual(self.project("trust")["requirements"], [])

    def test_design_folder_rejects_non_native_documentation(self):
        page = self.root / "architecture/models/new-subsystem/README.md"
        page.parent.mkdir()
        page.write_text("# New subsystem\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Native-only"):
            scopes(self.root)

    def test_unlisted_native_source_cannot_escape_validation(self):
        source = self.root / "architecture/models/NewSubsystem.sysml"
        source.write_text("package NewSubsystem { }\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Every authored SysML source"):
            scopes(self.root)


    def test_engineering_views_keep_the_owner_file_budget_without_report_diagrams(self):
        from software_intake import expected_outputs
        from intake_sources import selected_inputs, trace_map
        rendered=expected_outputs(self.root,self.model,selected_inputs(self.root),trace_map(self.root))
        groups={}
        for path in rendered:
            if path.is_relative_to('architecture/generated'):
                groups.setdefault(path.parent,set()).add(path.name)
        for owner,names in groups.items():self.assertLessEqual(len(names),5,str(owner))
        self.assertEqual(groups[Path('architecture/generated/software-intake')],{
            'SoftwareIntakeLogicalDesign.svg','SoftwareIntakeUseCases.svg','SoftwareIntakeFunctions.svg',
            'SoftwareIntakeRequirements.md','SoftwareIntakeVerification.md'})
        for name in ('ImplementationSources','ImplementationComparison','Relationships','ChangeImpact'):
            self.assertFalse(any(name in str(path) for path in rendered if path.suffix=='.svg'))


from tier_repo_test_support import TierRepositoryTestCase


class DesignContextManualIntegration(TierRepositoryTestCase):
    def test_scoped_svg_links_survive_generated_manual_copy(self):
        self.generate()
        manual = self.root / "verify-architecture/docs/auto-docs"
        registry = json.loads(
            (manual / "upstream/scripts/architecture/config/views/design-context.json").read_text(encoding="utf-8")
        )
        for scope in registry["scopes"]:
            if not scope.get("svg"):
                continue
            path = manual / scope["svg"]
            for link in ET.parse(path).findall(".//{http://www.w3.org/2000/svg}a"):
                name, _, fragment = link.get("href").partition("#")
                target = (path.parent / name).resolve()
                self.assertTrue(target.is_relative_to(manual.resolve()))
                self.assertTrue(target.is_file(), (scope["key"], name))
                if fragment and target.suffix == ".svg":
                    self.assertTrue(any(e.get("id") == fragment for e in ET.parse(target).iter()))
                elif fragment and target.suffix == ".md":
                    headings=re.findall(r"^#{1,6}\s+(.+)$",target.read_text(encoding="utf-8"),re.M)
                    anchors={re.sub(r"[^\w -]","",h.lower()).replace(" ","-") for h in headings}
                    anchors.update(re.findall(r'<a\s+(?:id|name)=["\x27]([^"\x27]+)',target.read_text(encoding="utf-8")))
                    self.assertIn(fragment,anchors,(scope["key"],name))
