#!/usr/bin/env bash

set -euo pipefail

if [[ $# == 1 && ( "$1" == --help || "$1" == -h ) ]]; then
  echo "Usage: bash scripts/proxmox-templates.sh {init|plan|apply}"
  exit 0
fi
if [[ $# != 1 || ! "$1" =~ ^(init|plan|apply)$ ]]; then
  echo "Usage: bash scripts/proxmox-templates.sh {init|plan|apply}" >&2
  echo "Run from Tier 0. Reference: docs/platforms/proxmox/template-lifecycle.md" >&2
  exit 1
fi
action="$1"
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/deployment-context.sh"
terraform_dir="$repo_root/terraform/templates"
if [[ ! -f "$terraform_dir/main.tf" || ! -f "$repo_root/templates/proxmox.yml.example" ]]; then
  echo "Template publication requires the Tier 0 template root and catalog example." >&2
  exit 1
fi

catalog="${TEMPLATE_CATALOG_FILE:-$repo_root/templates/proxmox.yml}"
state="${TEMPLATE_STATE_PATH:-$repo_root/.terraform/state/proxmox-templates/terraform.tfstate}"
plan="$repo_root/.terraform/plans/proxmox-templates.tfplan"
if [[ "$action" == plan ]]; then
  # A failed re-plan must not leave a previous apply target, even if validation or init fails.
  rm -f "$plan"
fi
for path in "$catalog" "$state"; do
  if [[ "$path" != /* ]]; then
    echo "TEMPLATE_CATALOG_FILE and TEMPLATE_STATE_PATH must be absolute paths." >&2
    exit 1
  fi
done
export TF_DATA_DIR="$repo_root/.terraform/data/proxmox-templates"

if [[ "$action" == init ]]; then
  if [[ ! -e "$catalog" ]]; then
    mkdir -p "$(dirname "$catalog")"
    cp -n "$repo_root/templates/proxmox.yml.example" "$catalog"
  fi
  echo "Review $catalog, stage approved images locally, then run plan."
  exit 0
fi

if [[ "$action" == plan && ! -f "$catalog" ]]; then
  echo "Missing catalog: $catalog. Run init first." >&2
  exit 1
fi
if [[ "$action" == apply && ! -f "$plan" ]]; then
  echo "No saved template plan. Run plan and review its output before apply." >&2
  exit 1
fi

mkdir -p "$TF_DATA_DIR" "$(dirname "$state")" "$(dirname "$plan")"
terraform -chdir="$terraform_dir" init -input=false -lockfile=readonly -reconfigure -backend-config="path=$state"
terraform -chdir="$terraform_dir" validate
if [[ "$action" == plan ]]; then
  terraform -chdir="$terraform_dir" plan -input=false -lock-timeout=60s \
    -var="catalog_file=$catalog" -out="$plan"
  echo "Review the plan above. Apply publishes candidates; test clones before promoting them."
else
  terraform -chdir="$terraform_dir" apply -input=false -lock-timeout=60s "$plan"
  rm -f "$plan"
fi
