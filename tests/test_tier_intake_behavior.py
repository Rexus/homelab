"""Expected behavior remains bound to native model identities and real implementation contracts."""

import json
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from intake_model_fixture import IntakeModelFixture
from intake_sources import MODEL, VIEWS, TRACE, selected_inputs, trace_map
from intake_behavior import messages, mermaid
from intake_contracts import check_behavior_contracts, check_test_symbols
from software_intake import OUTPUTS, GUIDE
from diagram_notation import validate_model_roles
from intake_views import render


class IntakeBehaviorContracts(IntakeModelFixture):
    def contracts(self):
        check_behavior_contracts(
            self.root, selected_inputs(self.root), self.model, trace_map(self.root)
        )

    def test_http_denial_has_no_source_exchange_and_verification_follows_cache_choice(self):
        http = self.model["behaviors"]["B-HTTP"]
        self.assertEqual(http["bindings"]["H-proxy"], "L-Proxy")
        self.assertEqual(http["bindings"]["H-client"], "L-Consumers")
        choice = http["steps"][-1]
        self.assertEqual(choice["guard"], "H-admitted")
        allowed, denied = choice["branches"]
        self.assertTrue(allowed["when"])
        self.assertFalse(denied["when"])
        self.assertEqual(allowed["steps"][0]["id"], "H-lookup")
        self.assertEqual(allowed["steps"][1]["guard"], "H-fresh")
        delivery = allowed["steps"][-1]
        self.assertEqual(delivery["guard"], "H-delivered")
        self.assertEqual(delivery["branches"][0]["steps"][0]["id"], "H-verify")
        for message in messages(denied["steps"]):
            self.assertEqual((message["from"], message["to"]), ("H-proxy", "H-client"))

    def test_https_keeps_client_to_source_tls_after_connect(self):
        https = self.model["behaviors"]["B-HTTPS"]
        allowed = https["steps"][-1]["branches"][0]
        steps = list(messages(allowed["steps"]))
        keys = [m["id"] for m in steps]
        self.assertLess(keys.index("S-ready"), keys.index("S-fetch"))
        fetch = next(m for m in steps if m["id"] == "S-fetch")
        self.assertEqual((fetch["from"], fetch["to"]), ("S-client", "S-source"))
        self.assertTrue(any("No payload caching" in note for note in fetch["notes"]))

    def test_behavior_source_change_requires_regeneration(self):
        self.change(
            "architecture/models/software-intake/SoftwareIntakeBehavior.sysml",
            "'HTTP repository request'",
            "'Changed HTTP request'",
        )
        with self.assertRaisesRegex(ValueError, "needs regeneration"):
            self.check()

    def test_missing_test_selector_is_detected(self):
        records = trace_map(self.root)
        records["H-check"]["test_symbols"][0] += "_deleted"
        with self.assertRaisesRegex(ValueError, "Missing behavior test"):
            check_test_symbols(self.root, records)

    def test_unexpected_allow_rule_cannot_satisfy_admission_contract(self):
        self.change(
            "tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2",
            "http_access deny !Safe_ports",
            "http_access allow all\nhttp_access deny !Safe_ports",
        )
        with self.assertRaisesRegex(ValueError, "Admission rule order or exceptions"):
            self.contracts()

    def test_tls_interception_and_disabled_client_verification_are_detected(self):
        template = self.root / "tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2"
        original = template.read_text(encoding="utf-8")
        template.write_text(original + "\nssl_bump bump all\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "TLS interception"):
            self.contracts()
        template.write_text(original, encoding="utf-8")
        self.change(
            "shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2",
            'Acquire::https::Verify-Peer "true";',
            'Acquire::https::Verify-Peer "false";',
        )
        with self.assertRaisesRegex(ValueError, "Client verification contract"):
            self.contracts()

    def test_each_message_needs_an_evidence_owner(self):
        records = trace_map(self.root)
        del records["H-cached"]
        with self.assertRaisesRegex(ValueError, "no implementation/evidence trace"):
            check_behavior_contracts(self.root, selected_inputs(self.root), self.model, records)

    def test_view_cannot_drop_a_participant(self):
        view = json.loads((self.root / VIEWS / "sequence.json").read_text(encoding="utf-8"))
        view["participants"]["B-HTTP"].pop()
        with self.assertRaisesRegex(ValueError, "every model participant"):
            mermaid(self.model, "B-HTTP", view)

    def test_all_structural_views_preserve_function_roles_and_generic_keys(self):
        namespace = {"s": "http://www.w3.org/2000/svg"}
        paths = [
            (OUTPUTS["logical"], {"logical", "external", "information"}),
            (OUTPUTS["solution"], {"logical", "external", "information"}),
            (Path("architecture/generated/software-intake/solution/SoftwareIntakeResources.svg"), {"logical", "physical"}),
        ]
        notation = json.loads((self.root / "scripts/architecture/config/views/notation.json").read_text(encoding="utf-8"))
        for path, categories in paths:
            svg = ET.parse(self.root / path).getroot()
            validate_model_roles(svg, self.root, self.model)
            key = svg.find("s:g[@id='Legend']", namespace)
            labels = {t.text for t in key.findall("s:text", namespace)}
            for category in categories:
                self.assertIn(notation["modelCategories"][category]["label"], labels)
                self.assertIsNotNone(key.find(f"s:g[@data-category-key='{category}']/s:rect", namespace))

        linked = ET.parse(self.root / OUTPUTS["logical"]).getroot()
        storage = linked.find('.//*[@data-model="L-Cache"]')
        shape = storage.find('s:a/s:path', namespace)
        self.assertIsNotNone(shape)
        shape.tag = '{http://www.w3.org/2000/svg}rect'
        with self.assertRaisesRegex(ValueError, "Inconsistent visual shape for L-Cache"):
            validate_model_roles(linked, self.root, self.model)

        # A future view must not turn the same proxy contract into an interface.
        self.change(
            "scripts/architecture/config/views/software-intake/logical.layout.svg",
            'id="Proxy" class="edge"',
            'id="Proxy" class="traffic"',
        )
        with self.assertRaisesRegex(ValueError, "Inconsistent visual role for L-Proxy"):
            render(self.root, self.model, selected_inputs(self.root), "logical")


if __name__ == "__main__":
    unittest.main()
