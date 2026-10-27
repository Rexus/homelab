"""NetBox action values are immutable evidence; translated display labels are not."""

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from tier_repo_test_support import UPSTREAM


@unittest.skipIf(os.name == "nt", "Native Linux durable ledger uses flock and directory fsync")
class NetBoxActionValues(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        path = UPSTREAM / "tier-0/ansible/roles/netbox_audit/files/netbox_audit.py"
        spec = importlib.util.spec_from_file_location("netbox_action_values_test", path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.config = {"state": str(self.root), "instance": "netbox-main", "max_records": 100,
                       "endpoint": "https://netbox.test/api/core/object-changes/"}
        self.rows = [{"id": 1, "time": "2026-10-26T10:00:00Z", "user_name": "operator",
                      "request_id": "fixture-request", "action": {"value": "create", "label": "Created"},
                      "changed_object_type": "dcim.device", "changed_object_id": 5,
                      "object_repr": "host-a", "prechange_data": None,
                      "postchange_data": {"name": "host-a"}, "message": ""}]

    def fetch(self, offset):
        return {"results": self.rows[offset:], "count": len(self.rows), "next": None}

    def collect(self):
        return self.module.collect(self.config, self.fetch)

    def event(self, number=1):
        return self.root / "events" / f"{number:020d}.jsonl"

    def test_label_changes_do_not_rewrite_or_block_later_events(self):
        self.assertEqual(self.collect(), {"exported": 1, "scanned": 1})
        original = self.event().read_bytes()
        timestamp = self.event().stat().st_mtime_ns
        self.assertEqual(json.loads(original)["change"]["action"], "create")
        self.rows[0]["action"]["label"] = "Skapad"
        self.rows.append(dict(deepcopy(self.rows[0]), id=2))
        self.assertEqual(self.collect(), {"exported": 1, "scanned": 2})
        self.assertEqual(self.event().read_bytes(), original)
        self.assertEqual(self.event().stat().st_mtime_ns, timestamp)
        self.assertEqual(self.rows[0]["action"], {"value": "create", "label": "Skapad"})
        self.assertEqual(self.collect()["exported"], 0)

    def test_changed_action_value_fails_closed_even_with_the_same_label(self):
        self.collect()
        original = self.event().read_bytes()
        self.rows[0]["action"]["value"] = "delete"
        self.rows.append(dict(deepcopy(self.rows[0]), id=2))
        with self.assertRaisesRegex(ValueError, "audit event changed"):
            self.collect()
        self.assertEqual(self.event().read_bytes(), original)
        self.assertFalse(self.event(2).exists())

    def test_other_event_changes_still_fail_closed(self):
        self.collect()
        original = self.event().read_bytes()
        self.rows[0]["postchange_data"]["name"] = "different-host"
        with self.assertRaisesRegex(ValueError, "audit event changed"):
            self.collect()
        self.assertEqual(self.event().read_bytes(), original)

    def test_scalar_and_choice_object_representations_have_the_same_value(self):
        self.rows[0]["action"] = "create"
        self.collect()
        original = self.event().read_bytes()
        self.rows[0]["action"] = {"value": "create", "label": "Skapad"}
        self.assertEqual(self.collect()["exported"], 0)
        self.assertEqual(self.event().read_bytes(), original)

    def test_legacy_choice_object_ledger_is_compared_without_rewriting(self):
        self.collect()
        legacy = json.loads(self.event().read_bytes())
        legacy["change"]["action"] = {"value": "create", "label": "Created"}
        original = (json.dumps(legacy, sort_keys=True, separators=(",", ":")) + "\n").encode()
        self.event().write_bytes(original)
        timestamp = self.event().stat().st_mtime_ns
        self.rows[0]["action"]["label"] = "Skapad"
        self.assertEqual(self.collect()["exported"], 0)
        self.assertEqual(self.event().read_bytes(), original)
        self.assertEqual(self.event().stat().st_mtime_ns, timestamp)
        self.rows[0]["action"]["value"] = "delete"
        with self.assertRaisesRegex(ValueError, "audit event changed"):
            self.collect()
        self.assertEqual(self.event().read_bytes(), original)

    def test_malformed_or_missing_action_values_are_not_published(self):
        for action in ({"label": "Created"}, {"value": None}, {"value": ""}, {"value": []},
                       {"value": False}, None, "", False, 1, []):
            with self.subTest(action=action):
                self.rows[0]["action"] = action
                with self.assertRaisesRegex(ValueError, "action.*value"):
                    self.collect()
                self.assertFalse(self.event().exists())
        del self.rows[0]["action"]
        with self.assertRaisesRegex(ValueError, "action.*value"):
            self.collect()
        self.assertFalse(self.event().exists())


if __name__ == "__main__":
    unittest.main()
