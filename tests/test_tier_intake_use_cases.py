"""Use-case scenarios retain behavioral, functional, implementation and acceptance connections."""

import copy
from argparse import Namespace
import contextlib
import io
import json
import os
import unittest
import xml.etree.ElementTree as ET
from intake_model_fixture import IntakeModelFixture
from intake_sources import trace_map
from intake_use_cases import validate_use_cases, scenario_functions
from intake_case_view import use_case_view
from intake_model import impact
from software_intake import CASE_PLAN, CASE_VIEW, run


class IntakeUseCaseContracts(IntakeModelFixture):
    def validate(self, model=None, plan=None, records=None):
        validate_use_cases(
            model or self.model,
            records or trace_map(self.root),
            plan or json.loads((self.root / CASE_PLAN).read_text()),
        )

    def test_selected_paths_keep_hit_miss_denial_and_tls_distinct(self):
        self.check()
        scenarios = self.model["scenarios"]
        hit = scenarios["SC-http-hit"]["messages"]
        miss = scenarios["SC-http-miss"]["messages"]
        denied = scenarios["SC-https-denied"]["messages"]
        self.assertIn("H-cached", hit)
        self.assertNotIn("H-fetch", hit)
        self.assertIn("H-fetch", miss)
        self.assertNotIn("H-cached", miss)
        self.assertEqual(hit[-2:], ["H-verify", "H-accepted"])
        self.assertEqual(miss[-2:], ["H-verify", "H-accepted"])
        self.assertEqual(denied, ["S-connect", "S-check", "S-denied"])
        self.assertIn("F-verify", scenario_functions(self.model, "SC-http-hit"))
        self.assertNotIn("F-tunnel", scenario_functions(self.model, "SC-https-denied"))

    def test_use_case_subject_and_external_actors_bind_to_sequence_parts(self):
        case = self.model["use_cases"]["UC-update"]
        self.assertEqual(
            case["bindings"], {"UC-supply": "L-Proxy", "ACT-client": "L-Consumers", "ACT-source": "L-Sources"}
        )
        svg = ET.fromstring(use_case_view(self.root, self.model))
        ns = {"s": "http://www.w3.org/2000/svg"}
        self.assertIsNotNone(svg.find("s:g[@data-model='UC-update']/s:ellipse", ns))
        self.assertIsNotNone(svg.find("s:g[@id='Legend']/s:g[@data-role='goal']/s:ellipse", ns))

    def test_missing_function_allocation_is_rejected(self):
        model = copy.deepcopy(self.model)
        model["edges"] = [
            e for e in model["edges"] if not (e["from"] == "F-verify" and e["kind"] == "allocated-to")
        ]
        with self.assertRaisesRegex(ValueError, "logical part allocation"):
            self.validate(model=model)

    def test_message_without_function_is_rejected(self):
        model = copy.deepcopy(self.model)
        model["edges"] = [
            e for e in model["edges"] if not (e["from"] == "H-verify" and e["to"] == "F-verify")
        ]
        with self.assertRaisesRegex(ValueError, "functional ownership"):
            self.validate(model=model)

    def test_missing_scenario_criteria_or_runtime_gap_is_rejected(self):
        plan = json.loads((self.root / CASE_PLAN).read_text())
        del plan["SC-http-hit"]
        with self.assertRaisesRegex(ValueError, "exactly the modeled scenarios"):
            self.validate(plan=plan)
        plan = json.loads((self.root / CASE_PLAN).read_text())
        del plan["SC-https"]["manual"]
        with self.assertRaisesRegex(ValueError, "manual acceptance"):
            self.validate(plan=plan)

    def test_uncovered_behavior_is_rejected(self):
        model = copy.deepcopy(self.model)
        for scenario in model["scenarios"].values():
            if "H-cached" in scenario["messages"]:
                scenario["messages"].remove("H-cached")
        with self.assertRaisesRegex(ValueError, "cover all modeled behavior"):
            self.validate(model=model)

    def test_function_change_identifies_its_scenarios_and_implementation(self):
        affected = set(impact(self.model, "F-verify"))
        self.assertTrue(
            {"H-verify", "S-verify", "SC-http-miss", "SC-http-hit", "SC-https", "L-Consumers", "UC-update"}
            <= affected
        )

    def test_test_intent_and_use_case_view_cannot_drift(self):
        self.change(CASE_VIEW, "Retrieve and verify software", "Different goal")
        with self.assertRaisesRegex(ValueError, "Stale generated output"):
            self.check()
        self.change(CASE_VIEW, "Different goal", "Retrieve and verify software")
        self.change(CASE_PLAN, "without another origin request", "with another origin request")
        with self.assertRaisesRegex(ValueError, "Stale generated output"):
            self.check()


@unittest.skipUnless(
    all(os.environ.get("SYSML_" + n) for n in ("JAVA", "KERNEL", "LIBRARY")),
    "Native round-trip tests require SYSML_JAVA, SYSML_KERNEL and SYSML_LIBRARY",
)
class IntakeNativeUseCaseRoundTrip(IntakeModelFixture):
    def build(self):
        args = Namespace(**{n.lower(): os.environ["SYSML_" + n] for n in ("JAVA", "KERNEL", "LIBRARY")})
        with contextlib.redirect_stdout(io.StringIO()):
            return run(self.root, "build", args)

    def test_native_message_edit_updates_scenario_and_sequence_with_same_identity(self):
        before = "Fetch or conditionally revalidate"
        after = "Retrieve or conditionally revalidate accepted content"
        self.change("architecture/models/software-intake/SoftwareIntakeBehavior.sysml", before, after)
        model = self.build()
        self.assertIn("H-fetch", model["scenarios"]["SC-http-miss"]["messages"])
        self.assertEqual(
            scenario_functions(model, "SC-http-miss"), scenario_functions(self.model, "SC-http-miss")
        )
        for file in (
            "artifacts/architecture/generated/software-intake/scenarios.md",
            "artifacts/architecture/generated/software-intake/http.mmd",
            "docs/01-architecture/07-software-intake/README.md",
        ):
            self.assertIn(after, (self.root / file).read_text(encoding="utf-8"))
        self.check()

    def test_missing_native_scenario_condition_preserves_previous_export(self):
        index = self.root / "artifacts/architecture/generated/software-intake/model-index.json"
        previous = index.read_bytes()
        self.change(
            "architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml", "attribute :>> admitted = false;", ""
        )
        with self.assertRaisesRegex(ValueError, "missing scenario condition"):
            self.build()
        self.assertEqual(index.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
