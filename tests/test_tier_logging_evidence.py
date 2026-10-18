"""Offline drill-tool checks are not live collector fault or restore evidence."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from tier_repo_test_support import TierRepositoryTestCase, UPSTREAM


class LoggingEvidence(TierRepositoryTestCase):
    def setUp(self):
        super().setUp()
        self.tool = UPSTREAM / "shared/scripts/log-evidence.py"
        self.expected = Path(self.temp.name) / "expected.jsonl"
        self.observed = Path(self.temp.name) / "observed.jsonl"
        result = self.run_tool("generate", "--source", "lab", "--count", "3", "--output", self.expected)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.events = [json.loads(line) for line in self.expected.read_text().splitlines()]

    def run_tool(self, *args, tool=None):
        return subprocess.run([sys.executable, str(tool or self.tool), *map(str, args)],
                              capture_output=True, text=True)

    def write_observed(self, events):
        self.observed.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")

    def verify(self, *args):
        return self.run_tool("verify", "--expected", self.expected, "--observed", self.observed, *args)

    def test_generation_is_unique_protected_and_never_overwrites_a_manifest(self):
        self.assertEqual([event["sequence"] for event in self.events], [1, 2, 3])
        before = self.expected.read_bytes()
        result = self.run_tool("generate", "--source", "lab", "--output", self.expected)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.expected.read_bytes(), before)
        another = Path(self.temp.name) / "another.jsonl"
        result = self.run_tool("generate", "--source", "lab", "--count", "1", "--output", another)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(json.loads(another.read_text())["run_id"], self.events[0]["run_id"])
        if os.name != "nt":
            self.assertEqual(self.expected.stat().st_mode & 0o777, 0o600)

    def test_matching_export_counts_retries_without_claiming_acceptance(self):
        self.write_observed([{"message": json.dumps(event)} for event in [*reversed(self.events), self.events[0]]])
        before = self.observed.read_bytes()
        result = self.verify("--message-field", "message")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["records_match"])
        self.assertEqual(report["scope"], "synthetic_record_reconciliation_only")
        self.assertEqual(report["fault_restore_acceptance"], "not_assessed")
        self.assertEqual(report["expected_unique"], 3)
        self.assertEqual(report["observed_unique"], 3)
        self.assertEqual(report["duplicates"][0]["extra_copies"], 1)
        self.assertEqual(report["observed_files"][0]["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(self.observed.read_bytes(), before)

    def test_missing_altered_conflicting_and_unexpected_records_fail(self):
        changed = dict(self.events[0], payload="altered")
        cases = (
            (self.events[1:], "missing"),
            ([changed, *self.events[1:]], "changed"),
            ([*self.events, changed], "changed"),
            ([*self.events, dict(self.events[0], sequence=999)], "unexpected"),
            ([], "missing"),
        )
        for events, failure in cases:
            with self.subTest(failure=failure, count=len(events)):
                self.write_observed(events)
                result = self.verify()
                self.assertEqual(result.returncode, 1, result.stderr)
                report = json.loads(result.stdout)
                self.assertFalse(report["records_match"])
                self.assertTrue(report[failure])

    def test_malformed_exports_and_invalid_expected_inputs_stop_with_error(self):
        duplicate_key = json.dumps(self.events[0]).replace('"sequence": 1', '"sequence": 99, "sequence": 1')
        for content in ("{", "\n", "[]\n", duplicate_key + "\n",
                        json.dumps(dict(self.events[0], sequence=True)) + "\n"):
            with self.subTest(content=content):
                self.observed.write_text(content)
                self.assertEqual(self.verify().returncode, 2)
        self.write_observed(self.events)
        original = self.expected.read_text()
        for content in ("", original + original.splitlines()[0] + "\n"):
            self.expected.write_text(content)
            self.assertEqual(self.verify().returncode, 2)
        self.expected.write_text(original)
        result = self.run_tool("verify", "--expected", self.expected, "--observed", self.expected)
        self.assertEqual(result.returncode, 2)
        self.assertIn("independent files", result.stderr)

    def test_reconciliation_accepts_multiple_batches_and_a_preserved_fixture_copy(self):
        second = Path(self.temp.name) / "second.jsonl"
        result = self.run_tool("generate", "--source", "other-lab", "--count", "2", "--output", second)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.observed.write_bytes(self.expected.read_bytes() + second.read_bytes())
        preserved = Path(self.temp.name) / "preserved-fixture.jsonl"
        shutil.copyfile(self.observed, preserved)
        self.observed.unlink()
        result = self.run_tool("verify", "--expected", self.expected, second, "--observed", preserved)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["expected_unique"], 5)

    def test_generated_tool_and_owned_record_survive_refresh_without_shipping_evidence(self):
        self.generate()
        tier = self.root / "verify-tier-0"
        shared = self.root / "verify-shared"
        copied = shared / "scripts/log-evidence.py"
        self.assertEqual(copied.read_bytes(), self.tool.read_bytes())
        result = self.run_tool("--help", tool=copied)
        self.assertEqual(result.returncode, 0, result.stderr)
        if shutil.which("bash"):
            result = subprocess.run(["bash", "scripts/log-evidence.sh", "--help"],
                                    cwd=tier, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("verify-shared/scripts/log-evidence.py", (tier / "scripts/log-evidence.sh").read_text())
        record = tier / "docs/administration/logging-evidence.md"
        self.assertIn("Not tested", record.read_text())
        self.assertIn("Project evidence record", (tier / "docs/administration/README.md").read_text())
        self.assertIn(".logging-evidence/", (tier / ".gitignore").read_text())
        self.assertFalse((shared / "docs/administration/logging-evidence.md").exists())
        record.write_text("# Locally reviewed logging evidence\n")
        self.generate("--refresh")
        self.assertEqual(record.read_text(), "# Locally reviewed logging evidence\n")
        record.unlink()
        self.generate("--refresh")
        self.assertFalse(record.exists())
