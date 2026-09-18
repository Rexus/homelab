#!/usr/bin/env bash
set -euo pipefail
tier_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DEPLOYMENT_REPO_DIR="$tier_dir"
if [[ ! -f "$tier_dir/../shared/scripts/init-local-files.sh" ]]; then
  echo "Missing shared automation: $tier_dir/../shared/scripts/init-local-files.sh" >&2
  exit 1
fi
exec bash "$tier_dir/../shared/scripts/init-local-files.sh" "$@"
