#!/usr/bin/env python3
"""Generate synthetic markers and reconcile exported records; never operate a collector."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

SCHEMA = "homelab-log-drill-v1"


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def positive_count(value):
    count = int(value)
    if not 1 <= count <= 1000000:
        raise argparse.ArgumentTypeError("count must be between 1 and 1000000")
    return count


def generate(args):
    if not args.source.strip():
        raise ValueError("source must not be empty")
    run_id = str(uuid.uuid4())
    digest = hashlib.sha256()
    created = datetime.now(timezone.utc).isoformat()
    # Exclusive creation protects earlier manifests, including existing symlinks.
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        for sequence in range(1, args.count + 1):
            event = {"drill": SCHEMA, "run_id": run_id, "source": args.source,
                     "sequence": sequence, "created_at": created, "payload": "synthetic acceptance event"}
            line = (encoded(event) + "\n").encode("utf-8")
            stream.write(line)
            digest.update(line)
    return {"path": str(args.output), "sha256": digest.hexdigest(),
            "run_id": run_id, "records": args.count}, 0


def read_records(paths, message_field=None):
    versions, counts, files = defaultdict(set), Counter(), []
    for path in paths:
        digest, lines = hashlib.sha256(), 0
        with path.open("rb") as stream:
            for lines, line in enumerate(stream, 1):
                digest.update(line)
                try:
                    event = json.loads(line.decode("utf-8"), object_pairs_hook=unique_object)
                    if message_field:
                        event = event[message_field]
                        if isinstance(event, str):
                            event = json.loads(event, object_pairs_hook=unique_object)
                    if not isinstance(event, dict) or event.get("drill") != SCHEMA:
                        raise ValueError("not a synthetic drill record")
                    for field in ("run_id", "source"):
                        if not isinstance(event.get(field), str) or not event[field].strip():
                            raise ValueError(f"invalid {field}")
                    sequence = event.get("sequence")
                    if type(sequence) is not int or sequence < 1:
                        raise ValueError("sequence must be a positive integer")
                    key = (event["run_id"], event["source"], sequence)
                    versions[key].add(hashlib.sha256(encoded(event).encode("utf-8")).hexdigest())
                    counts[key] += 1
                except (ValueError, KeyError, TypeError) as error:
                    raise ValueError(f"Invalid record at {path}:{lines}") from error
        files.append({"path": str(path), "sha256": digest.hexdigest(), "records": lines})
    return versions, counts, files


def verify(args):
    for expected in args.expected:
        for observed in args.observed:
            if expected.samefile(observed):
                raise ValueError("expected and observed must be independent files, not the same file")
    expected, expected_counts, manifests = read_records(args.expected)
    if not expected or any(count != 1 for count in expected_counts.values()):
        raise ValueError("expected manifests must be nonempty with unique event IDs")
    observed, observed_counts, exports = read_records(args.observed, args.message_field)
    missing = sorted(expected.keys() - observed.keys())
    unexpected = sorted(observed.keys() - expected.keys())
    changed = sorted(key for key in expected.keys() & observed.keys() if expected[key] != observed[key])
    duplicates = [{"id": key, "extra_copies": count - 1}
                  for key, count in sorted(observed_counts.items()) if count > 1]
    matches = not (missing or unexpected or changed)
    return {"scope": "synthetic_record_reconciliation_only", "records_match": matches,
            "fault_restore_acceptance": "not_assessed", "checked_at": datetime.now(timezone.utc).isoformat(),
            "expected_unique": len(expected), "observed_unique": len(observed),
            "missing": missing, "unexpected": unexpected, "changed": changed,
            "duplicates": duplicates, "expected_files": manifests, "observed_files": exports}, 0 if matches else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("generate", help="Create a new synthetic JSON Lines manifest; send nothing")
    create.add_argument("--source", required=True, help="Test label, not authenticated source identity")
    create.add_argument("--count", type=positive_count, default=1000)
    create.add_argument("--output", type=Path, required=True, help="New file in an existing protected directory")
    check = commands.add_parser("verify", help="Read manifests and exports; never modify evidence")
    check.add_argument("--expected", type=Path, nargs="+", required=True)
    check.add_argument("--observed", type=Path, nargs="+", required=True)
    check.add_argument("--message-field", help="Top-level export field containing the original JSON message")
    args = parser.parse_args()
    try:
        report, status = generate(args) if args.command == "generate" else verify(args)
    except (OSError, ValueError) as error:
        parser.exit(2, f"log-evidence: {error}\n")
    print(json.dumps(report, indent=2))
    return status


if __name__ == "__main__":
    sys.exit(main())
