"""Release guards for URL credentials, interrupted application and package ownership."""

from argparse import Namespace
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from intake_model_fixture import IntakeModelFixture
from test_tier_syson_changes import fixture, flat
from syson_api import SysON
from syson_change_model import Graph, compare_roots, digest
from syson_change_source import propose, record_baseline, save, sha, source_map
from syson_change_workspace import inputs
from syson_changes import apply, review
from syson import publish


class URLBoundary(unittest.TestCase):
    def test_base_paths_and_ipv6_are_preserved(self):
        for url in ("https://syson.example.invalid/model", "http://[::1]:8080/base"):
            with self.subTest(url=url), patch("syson_api.requests.Session"):
                self.assertEqual(SysON(url + "/").url, url)

    def test_unsafe_urls_fail_before_session_creation_without_echoing_values(self):
        urls = ("https://user:SYNTHETIC-SECRET@syson.example.invalid/base",
                "https://user%40name:SYNTHETIC-SECRET@syson.example.invalid",
                "https://@syson.example.invalid", "http://syson.example.invalid/?",
                "https://syson.example.invalid/base?token=SYNTHETIC-SECRET",
                "https://syson.example.invalid/base#SYNTHETIC-SECRET",
                "https://syson.example.invalid/#", "https://[SYNTHETIC-SECRET",
                "https://syson.example.invalid:SYNTHETIC-SECRET",
                "https://syson.example.invalid:65536", "https://syson.example.invalid:0")
        for url in urls:
            with self.subTest(url=url), patch("syson_api.requests.Session") as session:
                with self.assertRaisesRegex(ValueError, "without userinfo") as error:
                    SysON(url)
                session.assert_not_called()
                self.assertNotIn("SYNTHETIC-SECRET", str(error.exception))
                self.assertNotIn(url, str(error.exception))

    def test_publish_rejects_credentials_before_build_or_artifact_creation(self):
        with tempfile.TemporaryDirectory() as directory, patch("syson.run") as build:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "without userinfo"):
                publish(Namespace(root=root, url="https://user:SYNTHETIC-SECRET@host.invalid"))
            build.assert_not_called()
            self.assertFalse(list(root.iterdir()))

    def test_legacy_receipt_urls_are_rejected_before_return_evidence_is_created(self):
        for field in ("server", "url"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                receipt = {"server":"https://syson.example.invalid", "status":"verified",
                           "url":"https://syson.example.invalid/projects/one/edit/two"}
                receipt[field] = "https://user:SYNTHETIC-SECRET@syson.example.invalid"
                path = root / "receipt.json"
                save(path, receipt)
                with patch("syson_changes.SysON") as client:
                    with self.assertRaisesRegex(ValueError, "without userinfo"):
                        review(Namespace(root=root, receipt=path))
                    client.assert_not_called()
                with self.assertRaisesRegex(ValueError, "without userinfo"):
                    record_baseline(root, root, receipt)
                self.assertEqual([p.name for p in root.iterdir()], ["receipt.json"])

    def test_publish_reuse_rejects_legacy_receipt_url_before_transport_or_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / ".tmp/software-intake-model"
            build.mkdir(parents=True)
            (build / "native.json").write_text("[]", encoding="utf-8")
            (build / "combined.sysml").write_text("package SoftwareIntake {\n}\n", encoding="utf-8")
            args = Namespace(root=root, url="https://syson.example.invalid/base", name="Review")
            with patch("syson.run", return_value={"elements":{}}), \
                    patch("syson.select_views", return_value=([], None)), \
                    patch("syson.select_catalog", return_value=([], "")):
                # Stop before transport, then place an old receipt at the actual publication path.
                with patch("syson.SysON", side_effect=ValueError("fixture stop")):
                    with self.assertRaisesRegex(ValueError, "fixture stop"):
                        publish(args)
                folder, = (root / ".tmp/syson").iterdir()
                save(folder / "receipt.json", {"server":args.url, "status":"verified",
                     "url":"https://user:SYNTHETIC-SECRET@syson.example.invalid/projects/one"})
                with patch("syson.SysON") as client, patch("syson.coverage") as coverage:
                    with self.assertRaisesRegex(ValueError, "without userinfo") as error:
                        publish(args)
                    client.return_value.archive.assert_not_called()
                    coverage.assert_not_called()
                    self.assertNotIn("SYNTHETIC-SECRET", str(error.exception))
                self.assertFalse((root / "artifacts/architecture/evidence/syson-view-coverage.md").exists())


class ResumeBoundary(IntakeModelFixture):
    def setUp(self):
        super().setUp()
        self.name = "architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml"
        self.other = "architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml"
        self.folder = self.root / ".tmp/return-review"
        self.source = self.root / self.name
        self.tool = flat(fixture())
        original = self.source.read_bytes()
        candidate = self.folder / "workspace" / self.name
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(original + b"\n// Reviewed return edit\n")
        self.plan = {"schema":1, "status":"sources_applied", "root":str(self.root),
            "server":"http://localhost:8080", "project_id":"fixture-project", "runtime":{},
            "tool_model_sha256":digest(self.tool), "inputs":inputs(self.root),
            "files":{self.name:{"before":sha(self.source), "after":sha(candidate)}}}
        self.source.write_bytes(candidate.read_bytes())
        self.path = self.folder / "plan.json"

    def apply_with_mocked_transport_and_build(self):
        save(self.path, self.plan)
        client = Mock()
        client.archive.return_value = (None, self.tool, None)
        with patch("syson_changes.SysON", return_value=client), \
                patch("syson_changes.runtime_inputs", return_value={}), \
                patch("software_intake.run") as build, contextlib.redirect_stdout(io.StringIO()):
            self.build = build
            return apply(Namespace(root=self.root, plan=self.path)), build

    def test_resume_accepts_exact_reviewed_postapply_snapshot(self):
        result, build = self.apply_with_mocked_transport_and_build()
        self.assertEqual(result["status"], "applied")
        self.assertEqual([call.args[1] for call in build.call_args_list], ["build", "check"])

    def test_resume_rejects_changed_added_or_removed_nonproposed_inputs_before_build(self):
        mutations = ("change", "add", "remove")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                path = self.root / self.other
                original = path.read_bytes()
                added = self.root / "scripts/architecture/concurrent_edit.py"
                try:
                    if mutation == "change":
                        path.write_bytes(original + b"\n// Concurrent edit\n")
                    elif mutation == "add":
                        added.write_text("# Concurrent new input\n", encoding="utf-8")
                    else:
                        path.unlink()
                    with self.assertRaises((ValueError, OSError)):
                        self.apply_with_mocked_transport_and_build()
                    self.build.assert_not_called()
                    self.assertEqual(json.loads(self.path.read_text())["status"], "sources_applied")
                finally:
                    path.write_bytes(original)
                    added.unlink(missing_ok=True)

    def test_resume_rejects_unreviewed_or_reverted_proposed_content(self):
        candidate = self.source.read_bytes()
        before = candidate.removesuffix(b"\n// Reviewed return edit\n")
        for content in (before, b"// Unreviewed content\n"):
            with self.subTest(content=content):
                self.source.write_bytes(content)
                with self.assertRaisesRegex(ValueError, "Previously integrated sources changed"):
                    self.apply_with_mocked_transport_and_build()
                self.build.assert_not_called()

    def test_resume_rejects_a_before_hash_outside_the_reviewed_input_snapshot(self):
        self.plan["files"][self.name]["before"] = "unreviewed-baseline"
        with self.assertRaisesRegex(ValueError, "baseline disagrees"):
            self.apply_with_mocked_transport_and_build()
        self.build.assert_not_called()


class OwnerBoundary(unittest.TestCase):
    def test_round_trip_rejects_package_path_and_stable_owner_identity_changes(self):
        before = fixture()
        for field, value in (("declaredName", "DifferentOwner"), ("declaredShortName", "PKG-new")):
            with self.subTest(field=field):
                after = copy.deepcopy(before)
                after["data"][field] = value
                with self.assertRaisesRegex(ValueError, "semantic round trip"):
                    compare_roots(flat(before), flat(after), ["REQ-one"])

    def test_source_map_uses_nearest_native_package_span(self):
        content = "package Outer { package Inner { requirement <'REQ-one'> r; } }"
        source = "package SoftwareIntake {\n" + content + "\n}\n"
        start = source.index("requirement")
        rows = [{"kind":"Package", "qualified_name":"SoftwareIntake::Outer",
                 "start":source.index("package Outer"), "end":source.rindex(" } }") + 4},
                {"kind":"Package", "qualified_name":"SoftwareIntake::Outer::Inner",
                 "start":source.index("package Inner"), "end":source.index("; }") + 3},
                {"kind":"RequirementUsage", "key":"REQ-one", "start":start,
                 "end":source.index(";", start) + 1}]
        with patch("syson_change_source.index_source", return_value={"elements":rows, "errors":[]}):
            result = source_map(Path("."), {"architecture/requirements/one.sysml":content},
                                "SoftwareIntake", Path("unused.json"), Namespace())
        self.assertEqual(result["keys"]["REQ-one"]["package"], "SoftwareIntake::Outer::Inner")

    def test_same_file_package_move_conflicts_even_with_identical_tool_text(self):
        tool = "requirement <'REQ-one'> r;"
        row = {"file":"architecture/requirements/one.sysml", "start":0, "end":len(tool),
               "text":tool, "package":"Requirements"}
        baseline = {"keys":{"REQ-one":row}, "packages":{}}
        current = copy.deepcopy(baseline)
        current["keys"]["REQ-one"]["package"] = "OtherRequirements"
        index = {"elements":[{"key":"REQ-one", "start":0, "end":len(tool)}], "errors":[]}
        for added in ([], ["REQ-one"]):
            with self.subTest(added=added), self.assertRaisesRegex(ValueError, "package owner changed"):
                propose(baseline, current, tool, index, Graph(flat(fixture())), ["REQ-one"], added)


if __name__ == "__main__":
    unittest.main()
