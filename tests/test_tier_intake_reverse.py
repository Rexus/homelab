"""Reverse review must preserve selected scenarios, external ownership and trace provenance."""

from argparse import Namespace
import contextlib
import copy
import io
from intake_model_fixture import IntakeModelFixture
from intake_sources import trace_map
from intake_reverse import review, select_asset, asset_id
from software_intake import run

TF = "tier-2/terraform/deployments/cache/main.tf"
APT = "tests/test_tier_package_policy.py"
POLICY = "tests/test_tier_cache_policy.py"


class ReverseTraceContracts(IntakeModelFixture):
    def setUp(self):
        super().setUp()
        self.records = trace_map(self.root)

    def test_terraform_reaches_proxy_functions_through_native_realization(self):
        data = review(self.model, self.records, TF)
        self.assertEqual({r["element"] for r in data["direct"]}, {"DEF-member"})
        self.assertEqual(set(data["functions"]), {"F-admit", "F-cache", "F-http", "F-tunnel"})
        self.assertEqual(set(data["scenarios"]), set(self.model["scenarios"]))
        self.assertEqual(set(data["use_cases"]), {"UC-update", "UC-clone"})
        self.assertEqual(data["use_cases"]["UC-clone"][-1],
                         {"from":"SC-https", "to":"UC-clone", "relation":"depends-on", "direction":"reverse"})
        self.assertEqual(set(data["requirements"]), {"REQ-custody", "REQ-integrity", "REQ-policy"})
        self.assertIn("typed-by", [h["relation"] for h in data["functions"]["F-http"]])
        self.assertIn("allocated-to", [h["relation"] for h in data["functions"]["F-http"]])

    def test_client_test_does_not_become_proxy_behavior_or_denial_coverage(self):
        data = review(self.model, self.records, APT)
        self.assertEqual(data["mode"], "verification")
        self.assertEqual(set(data["functions"]), {"F-verify"})
        self.assertEqual(set(data["scenarios"]), {"SC-http-hit", "SC-http-miss", "SC-http-untrusted", "SC-http-cache-untrusted", "SC-https"})
        self.assertEqual(set(data["requirements"]), {"REQ-integrity"})

    def test_exact_method_avoids_the_broader_file_contract(self):
        whole = review(self.model, self.records, POLICY)
        method = review(self.model, self.records, POLICY + "::NativeCachePolicy.test_source_policy")
        self.assertIn("F-tunnel", whole["functions"])
        self.assertNotIn("F-tunnel", method["functions"])
        self.assertEqual(set(method["functions"]), {"F-admit", "F-cache", "F-http"})
        self.assertNotIn("REQ-integrity", method["requirements"])

    def test_allocations_and_selected_messages_control_results(self):
        model = copy.deepcopy(self.model)
        model["edges"] = [e for e in model["edges"] if not
            (e["from"] == "F-http" and e["kind"] == "allocated-to")]
        self.assertNotIn("F-http", review(model, self.records, TF)["functions"])
        records = {"H-fetch": {"sources": [TF], "checks": [], "state": "implementation-source"}}
        self.assertEqual(set(review(self.model, records, TF)["scenarios"]),
                         {"SC-http-miss", "SC-http-untrusted", "SC-http-source-failure"})
        model["edges"] = [e for e in model["edges"] if not
            (e["from"] == "SC-http-miss" and e["to"] == "H-fetch" and e["kind"] == "uses-message")]
        self.assertEqual(set(review(model, records, TF)["scenarios"]),
                         {"SC-http-untrusted", "SC-http-source-failure"})

    def test_unmapped_and_outside_paths_are_explicit(self):
        with self.assertRaisesRegex(ValueError, "missing coverage does not establish no impact"):
            select_asset(self.root, "README.md", self.records)
        with self.assertRaisesRegex(ValueError, "must belong"):
            select_asset(self.root, "../outside.tf", self.records)
        self.assertEqual(select_asset(self.root, str(self.root / TF), self.records), TF)
        self.assertNotEqual(asset_id(TF), asset_id(POLICY))

    def test_file_query_uses_the_recorded_baseline_after_a_source_edit(self):
        (self.root / TF).write_text("An unfinished Terraform edit", encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            data = run(self.root, "impact", Namespace(file=TF))
        self.assertIn("Current inputs differ", output.getvalue())
        self.assertIn(TF, output.getvalue())
        self.assertIn("F-http", data["functions"])
        (self.root / TF).unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertIn("F-http", run(self.root, "impact", Namespace(file=TF))["functions"])
