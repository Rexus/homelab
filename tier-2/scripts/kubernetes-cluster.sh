#!/usr/bin/env bash
set -euo pipefail
# Shared executes the workflow; this tier owns all inputs, resources, and state.
# Reference: docs/deployment/stage-3-identity-runtime/procedures/talos-terraform.md
tier_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DEPLOYMENT_REPO_DIR="$tier_dir"
exec bash "$tier_dir/../shared/scripts/kubernetes-cluster.sh" "$@"
