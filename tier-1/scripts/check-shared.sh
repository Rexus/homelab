#!/usr/bin/env bash
set -euo pipefail
tier_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
shared_dir="$tier_dir/../shared"
for required in config/guest-sizes.json ansible/playbooks/control-node.yml ansible/requirements.yml \
  scripts/deploy.sh scripts/init-local-files.sh scripts/lib/deployment-context.sh; do
  if [[ ! -f "$shared_dir/$required" ]]; then
    echo "Missing shared automation: $shared_dir/$required" >&2
    echo "Generate or check out shared beside this tier repository." >&2
    exit 1
  fi
done
echo "Shared automation found: $shared_dir"
