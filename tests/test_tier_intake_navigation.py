"""The SVG journey must follow native identities and survive manual ownership relocation."""

import copy
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from intake_model_fixture import IntakeModelFixture
from tier_repo_test_support import TierRepositoryTestCase
from design_context import scopes, relative
from intake_sources import selected_inputs, trace_map
from software_intake import expected_outputs
from svg_pages import SCENARIOS, FUNCTIONS, LOGICAL, SOLUTION, RESOURCES, tag, validate_links
from intake_explorer import target_for
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
        self.assertTrue(any(h.endswith("solution/SoftwareIntakeSolutionDesign.svg") for h in hrefs))
        proxy = next(a for a in scenario.iter(tag("a")) if a.find('.//*[@data-element="L-Proxy"]') is not None)
        self.assertEqual(proxy.get("href"), relative(SCENARIOS, SOLUTION))
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
        path = self.root / "artifacts/architecture/generated/software-intake/trace.md"
        import re
        hrefs = re.findall(r"\]\(([^)]+)\)",path.read_text(encoding="utf-8"))
        self.assertTrue(any(h.endswith("terraform/deployments/cache/main.tf") for h in hrefs))
        self.assertTrue(any(h.endswith("cache_proxy/tasks/squid.yml") for h in hrefs))
        self.assertTrue(any(h.endswith("cache_proxy/templates/squid.conf.j2") for h in hrefs))

    def test_logical_roles_open_realization_only_when_native_allocation_is_displayed(self):
        entries=scopes(self.root)
        views={Path(SOLUTION):(self.root/SOLUTION).read_text(encoding='utf-8')}
        for key in ('L-Proxy','L-Cache'):
            self.assertEqual(target_for(self.model,entries,key,LOGICAL,views),SOLUTION)
            model=copy.deepcopy(self.model)
            model['edges']=[e for e in model['edges'] if not
                            (e['from']==key and e['kind']=='allocated-to')]
            self.assertNotEqual(target_for(model,entries,key,LOGICAL,views),SOLUTION)
        self.assertTrue(target_for(self.model,entries,'L-Proxy').endswith('policy-proxy/PolicyProxyContract.svg'))
        for origin in (SCENARIOS, FUNCTIONS, 'architecture/generated/software-intake/SoftwareIntakeFunctions.svg'):
            self.assertEqual(target_for(self.model,entries,'L-Proxy',origin,views),SOLUTION)
        self.assertNotEqual(target_for(self.model,entries,'L-Proxy',LOGICAL,
            {Path(SOLUTION):'<svg xmlns="http://www.w3.org/2000/svg"/>'}),SOLUTION)

    def test_cache_container_and_content_keep_separate_non_nested_links(self):
        svg=ET.parse(self.root/LOGICAL)
        storage=svg.find('.//*[@data-model="L-Cache"]')
        self.assertEqual(storage.find(tag('a')).get('href'),relative(LOGICAL,SOLUTION))
        content=storage.find('.//*[@data-model="L-cached-content"]')
        self.assertIsNotNone(content)
        self.assertEqual(len(svg.findall('.//*[@data-model="L-Cache"]')),1)
        self.assertEqual(len(svg.findall('.//*[@data-model="L-cached-content"]')),1)
        for a in svg.iter(tag('a')):
            self.assertFalse(any(n is not a and n.tag==tag('a') for n in a.iter()))

    def test_realization_views_retain_scoped_intent_and_return_paths(self):
        for path in (LOGICAL,SOLUTION,RESOURCES):
            svg=ET.parse(self.root/path)
            nav={a.get('aria-label'):a.get('href') for a in svg.iter(tag('a')) if a.get('aria-label')}
            for label,target in [('Use cases','SoftwareIntakeUseCases.svg'),('Requirements','SoftwareIntakeRequirements.md'),
                                 ('Functions','SoftwareIntakeFunctions.svg'),('Tests','SoftwareIntakeVerification.md'),
                                 ('Proxy contract','policy-proxy/PolicyProxyContract.svg')]:
                full = 'architecture/generated/software-intake/' + target
                self.assertEqual(nav[label],relative(path,full))
            if path!=LOGICAL:self.assertEqual(nav['Logical design'],relative(path,LOGICAL))
            if path!=SOLUTION:self.assertEqual(nav['Solution design'],relative(path,SOLUTION))

    def test_intake_links_to_human_led_use_case_without_retyping_software_actors(self):
        intake=ET.parse(self.root/'architecture/generated/software-intake/SoftwareIntakeUseCases.svg')
        self.assertTrue(any(a.get('href')=='../platform/hosting/Boot1CloneRepository.svg' for a in intake.iter(tag('a'))))
        for key in ('ACT-client','ACT-source'):
            actor=intake.find('.//*[@data-model="'+key+'"]')
            self.assertIsNone(actor.find('.//*[@class="actor-symbol"]'))
        clone=ET.parse(self.root/'architecture/generated/platform/hosting/Boot1CloneRepository.svg')
        self.assertIsNotNone(clone.find('.//*[@data-model="ACT-operator"]//*[@class="actor-symbol"]'))

    def test_broken_svg_fragment_is_rejected(self):
        records = trace_map(self.root)
        outputs = expected_outputs(self.root, self.model, selected_inputs(self.root), records)
        path = Path("architecture/generated/HomelabSystemOverview.svg")
        outputs[path] = outputs[path].replace("HomelabFunctions.svg", "HomelabFunctions.svg#missing")
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
        # Supporting indexes are Markdown now; follow their links as part of the same journey.
        import re
        for document in {p for p in source_links if p.suffix == ".md"}:
            for href in re.findall(r"\]\(([^)]+)\)",document.read_text(encoding="utf-8")):
                name=href.partition("#")[0]
                if not name or "://" in name:continue
                target=(document.parent/name).resolve()
                self.assertTrue(target.is_file(),(document,name))
                source_links.append(target)
        self.assertTrue(any("verify-tier-2" in str(p) and p.name == "main.tf" for p in source_links))
        self.assertTrue(any(p == manual / "upstream/tests/test_tier_cache_policy.py" for p in source_links))
