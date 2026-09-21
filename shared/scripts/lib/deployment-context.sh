#!/usr/bin/env bash

# Resolve reusable automation separately from the repository that owns inputs.
# Reference: docs/reference/generated-repository-model.md
automation_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -n "${DEPLOYMENT_REPO_DIR:-}" ]]; then
  repo_root="$DEPLOYMENT_REPO_DIR"
elif [[ -f "$PWD/.deployment-setups" ]]; then
  repo_root="$PWD"
else
  echo "Run this shared script from a tier repository root." >&2
  exit 1
fi
repo_root="$(cd "$repo_root" && pwd)"
ansible_dir="$repo_root/ansible"
ansible_playbook_dir="$ansible_dir/playbooks"

if [[ ! -f "$repo_root/.deployment-setups" ]]; then
  echo "Missing tier setup list: $repo_root/.deployment-setups" >&2
  exit 1
fi
mapfile -t all_setups < "$repo_root/.deployment-setups"
bash "$repo_root/scripts/check-shared.sh"

require_owned_setup() {
  local candidate="$1"
  local allowed

  for allowed in "${all_setups[@]}"; do
    if [[ "$candidate" == "$allowed" ]]; then
      return
    fi
  done
  echo "Setup $candidate is not owned by $repo_root." >&2
  echo "Available setups: ${all_setups[*]}" >&2
  exit 1
}
