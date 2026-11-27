"""Read-only change review against the trace snapshot, even while source edits are in progress."""

import hashlib
import json
from intake_reverse import review, select_asset, REVERSE_REPORT, path_text


def run_file_query(root, value):
    snapshot = json.loads((root / "artifacts/architecture/generated/software-intake/model-index.json").read_text(encoding="utf-8"))
    if "trace_records" not in snapshot:
        raise ValueError("Build the model once to record its reverse trace snapshot")
    records = snapshot["trace_records"]
    asset = select_asset(root, value, records)
    data = review(snapshot["model"], records, asset)
    changed = []
    for name, expected in snapshot["sources"].items():
        path = root / name
        actual = hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest() if path.is_file() else None
        if actual != expected:
            changed.append(name)
    print("Asset: " + asset)
    print("Basis: last built software-intake model and its recorded traces.")
    if changed:
        print("Current inputs differ from that snapshot: " + ", ".join(changed))
        print("Review the proposed edit against this baseline; rebuild after reconciling model and sources.")
    else:
        print("Recorded source fingerprints match the current inputs.")
    print("Scope: " + data["mode"] + "; potential review scope, not predicted failure or proof of conformance.")
    for label, field in (("Functions", "functions"), ("Scenarios", "scenarios"),
                         ("Use cases", "use_cases"), ("Guardrails to recheck", "requirements"), ("Verification cases", "verification_cases")):
        print("\n" + label + ":")
        for key, path in data[field].items():
            print("  " + path_text(key, path))
        if not data[field]:
            print("  No recorded path in this modeled slice.")
    print("\nReport: " + REVERSE_REPORT + "#" + data["id"])
    return data
