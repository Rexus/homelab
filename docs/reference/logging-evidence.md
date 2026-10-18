# Logging evidence checker

Generate synthetic markers and compare their exported/restored contents. The tool
sends no events, injects no faults and never writes to a receiver or archive.
Use the [fault/restore drill](../administration/logging-drill.md) for acceptance.

**Working repository:** Tier 0, using `bash scripts/log-evidence.sh`.
The shortcut runs Shared's [scripts/log-evidence.py](../../shared/scripts/log-evidence.py).
Python 3 standard library only; no inventory, credentials, state or evidence lives in Shared.

## Contents

- [Commands](#commands)
- [Input format](#input-format)
- [Results](#results)

## Commands

| Command / option | Contract |
| --- | --- |
| `generate --source NAME --output FILE` | Create 1,000 numbered JSON Lines records with a fresh run UUID; refuse an existing file |
| `--count N` | Generate 1 to 1,000,000 records; default 1,000 |
| `verify --expected FILE... --observed FILE...` | Read all inputs and compare event IDs and full original message content |
| `--message-field NAME` | Read the observed record's named top-level JSON field, containing a JSON object or JSON message string |
| `--help` | Command-specific usage is also available after `generate` or `verify` |

`generate` requires an existing output directory and creates its file with owner-only
permissions on POSIX. Protect the directory and use `umask 077` for redirected reports.
Keep raw records/reports in ignored Tier 0 `.logging-evidence/` or independent protected
storage, not Git. `verify` only reads inputs and writes its JSON report to stdout.

## Input format

Expected files are the unmodified generated manifests. Each event has `drill`,
`run_id`, `source`, `sequence`, `created_at` and `payload` fields. IDs are
`(run_id, source, sequence)`; creation time is not a send or durable-commit timestamp.
Preserve the expected manifests/digests outside the collector before testing.

Observed files are UTF-8 JSON Lines containing only the selected original drill
messages, with one event per line. Use product-native read-only export/filtering;
retain the raw archive separately. No prefixes, blank lines, mixed ordinary messages
or duplicate JSON fields are accepted. For an archive envelope, `--message-field message` accepts:

```json
{"message":{"drill":"homelab-log-drill-v1","run_id":"example","source":"lab","sequence":1}}
```

That abbreviated shape only illustrates field extraction; verification still requires
the full original message content to match. A synthetic `source` label proves no
authenticated identity. Source attribution, committed copies, retention and read
authorization require independent tests.

## Results

| Exit | Meaning |
| --- | --- |
| `0` | All expected unique records match, no unexpected IDs; identical duplicate copies reported |
| `1` | Missing, altered or unexpected records; empty observed data cannot pass |
| `2` | Invalid input/arguments, empty or duplicate expected IDs, inaccessible files or attempted manifest overwrite |

Expected and observed cannot name the same file, including hard links. The tool
cannot detect a copied manifest falsely presented as received data; custody and
independent witness are mandatory. A tool match alone is never fault/restore evidence.

The report contains UTC check time, unique counts, missing/unexpected/changed IDs,
extra duplicate-copy counts and SHA-256 digests of every input file. Conflicting
copies of one ID fail even if a matching copy also exists. Input order does not
matter and no input is deduplicated or edited on disk.

`scope` is always `synthetic_record_reconciliation_only` and
`fault_restore_acceptance` is always `not_assessed`. Hashes bind the report to its
inputs, not to a trusted signer or actual storage history. Whole-data-volume integrity,
WORM enforcement, RPO/RTO and live failure results remain outside this tool's scope.
