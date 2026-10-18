#!/usr/bin/env bash
set -euo pipefail
# Stateless comparison is shared; test inputs and results remain Tier 0-owned.
# Guide: docs/administration/logging-drill.md
tier_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
shared_tool="$tier_dir/../shared/scripts/log-evidence.py"
if [[ ! -f "$shared_tool" ]]; then
  echo "Missing shared evidence checker: $shared_tool" >&2
  exit 1
fi
exec python3 "$shared_tool" "$@"
