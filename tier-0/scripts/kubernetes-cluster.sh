#!/usr/bin/env bash
set -euo pipefail
umask 077

# Kubernetes is the deployment goal; Talos is this implementation's node OS.
# Preserve existing backend, working-data, plan, and credential paths across the rename.

if [[ $# == 1 && "$1" == --help ]]; then
  echo "Usage: bash scripts/kubernetes-cluster.sh {init|plan|apply|credentials}"
  echo "Current implementation: Talos. Reference: docs/platforms/kubernetes/README.md"
  exit 0
fi

if [[ $# != 1 || ! "$1" =~ ^(init|plan|apply|credentials)$ ]]; then
  echo "Usage: bash scripts/kubernetes-cluster.sh {init|plan|apply|credentials}" >&2
  echo "Current implementation: Talos. Reference: docs/platforms/kubernetes/README.md" >&2
  exit 1
fi
action="$1"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$(pwd -P)" != "$repo_root" ]]; then
  echo "Run from the Tier 0 repository root." >&2
  exit 1
fi
root="$repo_root/terraform/deployments/kubernetes"
shared="$repo_root/../shared"
state="$repo_root/.terraform/state/talos/terraform.tfstate"
plan="$repo_root/.terraform/plans/talos.tfplan"
export TF_DATA_DIR="$repo_root/.terraform/data/talos"

if [[ "$action" == plan ]]; then
  # Never allow a failed re-plan, including a layout check, to leave an older apply target.
  rm -f "$plan"
fi
for legacy in terraform/talos terraform/deployments/talos; do
  for file in "$repo_root/$legacy/"*.tf "$repo_root/$legacy/"*.tfvars \
    "$repo_root/$legacy/"*.tf.json "$repo_root/$legacy/"*.tfvars.json; do
    [[ -f "$file" ]] || continue
    echo "Legacy Terraform deployment found: $legacy" >&2
    echo "Migrate to terraform/deployments/kubernetes before continuing." >&2
    echo "See docs/reference/generated-repository-model.md#terraform-layout-upgrade." >&2
    exit 1
  done
done

if [[ "$action" == init ]]; then
  for relative in ansible/inventory/hosts.yml ansible/group_vars/talos.yml terraform/deployments/kubernetes/terraform.tfvars; do
    if [[ ! -e "$repo_root/$relative" ]]; then
      cp -n "$repo_root/$relative.example" "$repo_root/$relative"
    fi
  done
  echo "Review Tier 0 Kubernetes inputs: Talos inventory, DHCP reservations,"
  echo "and terraform/deployments/kubernetes/terraform.tfvars."
  echo "Existing inventory is not merged: add the Talos groups from its example if missing."
  echo "Set PROXMOX_VE_ENDPOINT and PROXMOX_VE_API_TOKEN outside Git, then run plan."
  exit 0
fi

if [[ "$action" == plan ]]; then
  for path in "$repo_root/ansible/inventory/hosts.yml" "$repo_root/ansible/group_vars/talos.yml" \
    "$root/terraform.tfvars" "$shared/templates/proxmox-catalog.tfvars" "$shared/config/guest-sizes.json"; do
    if [[ ! -f "$path" ]]; then
      echo "Missing input: $path" >&2
      exit 1
    fi
  done
fi
if [[ "$action" == apply && ! -f "$plan" ]]; then
  echo "No saved Kubernetes plan. Run plan and review it first." >&2
  exit 1
fi
if [[ "$action" == credentials && ! -f "$state" ]]; then
  echo "No local Kubernetes deployment state. Restore the existing state; do not bootstrap a replacement cluster." >&2
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
    echo "Export protected client files with: bash scripts/kubernetes-cluster.sh credentials"
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
