#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $# == 1 && "$1" == --help ]]; then
  echo "Usage: bash scripts/talos-cluster.sh {init|plan|apply|credentials}"
  echo "Reference: docs/platforms/talos/terraform.md"
  exit 0
fi

if [[ $# != 1 || ! "$1" =~ ^(init|plan|apply|credentials)$ ]]; then
  echo "Usage: bash scripts/talos-cluster.sh {init|plan|apply|credentials}" >&2
  echo "Reference: docs/platforms/talos/terraform.md" >&2
  exit 1
fi
action="$1"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$(pwd -P)" != "$repo_root" ]]; then
  echo "Run from the Tier 0 repository root." >&2
  exit 1
fi
root="$repo_root/terraform/talos"
shared="$repo_root/../shared"
state="$repo_root/.terraform/state/talos/terraform.tfstate"
plan="$repo_root/.terraform/plans/talos.tfplan"
export TF_DATA_DIR="$repo_root/.terraform/data/talos"

if [[ "$action" == init ]]; then
  for relative in ansible/inventory/hosts.yml ansible/group_vars/talos.yml terraform/talos/terraform.tfvars; do
    if [[ ! -e "$repo_root/$relative" ]]; then
      cp -n "$repo_root/$relative.example" "$repo_root/$relative"
    fi
  done
  echo "Review Tier 0 Talos inventory, DHCP reservations, and terraform/talos/terraform.tfvars."
  echo "Existing inventory is not merged: add the Talos groups from its example if missing."
  echo "Set PROXMOX_VE_ENDPOINT and PROXMOX_VE_API_TOKEN outside Git, then run plan."
  exit 0
fi

if [[ "$action" == plan ]]; then
  # Never allow a failed re-plan to leave an older apply target.
  rm -f "$plan"
  for path in "$repo_root/ansible/inventory/hosts.yml" "$repo_root/ansible/group_vars/talos.yml" \
    "$root/terraform.tfvars" "$shared/templates/proxmox-catalog.tfvars" "$shared/config/guest-sizes.json"; do
    if [[ ! -f "$path" ]]; then
      echo "Missing input: $path" >&2
      exit 1
    fi
  done
fi
if [[ "$action" == apply && ! -f "$plan" ]]; then
  echo "No saved Talos plan. Run plan and review it first." >&2
  exit 1
fi
if [[ "$action" == credentials && ! -f "$state" ]]; then
  echo "No local Talos state. Restore the existing state; do not bootstrap a replacement cluster." >&2
  exit 1
fi

mkdir -p "$TF_DATA_DIR" "$(dirname "$state")" "$(dirname "$plan")"
terraform -chdir="$root" init -input=false -lockfile=readonly -reconfigure -backend-config="path=$state"
case "$action" in
  plan)
    terraform -chdir="$root" validate
    if ! terraform -chdir="$root" plan -input=false -lock-timeout=60s \
      -var-file="$shared/templates/proxmox-catalog.tfvars" -out="$plan"; then
      rm -f "$plan"
      exit 1
    fi
    echo "Review the saved plan. This creates and bootstraps a new cluster, not an adoption or recovery."
    ;;
  apply)
    terraform -chdir="$root" apply -input=false -lock-timeout=60s "$plan"
    rm -f "$plan"
    echo "Export protected client files with: bash scripts/talos-cluster.sh credentials"
    ;;
  credentials)
    directory="$repo_root/secrets/talos"
    mkdir -p "$directory"
    temporary="$(mktemp -d "$directory/.export.XXXXXX")"
    trap 'rm -rf "$temporary"' EXIT
    terraform -chdir="$root" output -raw talosconfig > "$temporary/talosconfig"
    terraform -chdir="$root" output -raw kubeconfig > "$temporary/kubeconfig"
    terraform -chdir="$root" output -json machine_configurations > "$temporary/machine-configurations.json"
    mv "$temporary/"* "$directory/"
    echo "Credentials and recovery configurations written to $directory; back them up securely outside the cluster."
    ;;
esac
