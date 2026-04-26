#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/init-local-files.sh [options]

Options:
  --env NAME   Also create environment-specific local files, such as
               terraform.NAME.tfvars and ansible/inventory/NAME.yml.
  -h, --help   Show this help text.

Examples:
  bash scripts/init-local-files.sh
  bash scripts/init-local-files.sh --env test
EOF
}

deployment_env=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --env" >&2
        exit 1
      fi
      deployment_env="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -n "$deployment_env" && ! "$deployment_env" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "--env may only contain letters, numbers, underscores, and dashes." >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
created=0

create_from_example() {
  local source_path="$1"
  local target_path="$2"

  if [[ -f "$target_path" ]]; then
    echo "exists  $target_path"
    return
  fi

  if [[ ! -f "$source_path" ]]; then
    echo "Missing example file: $source_path" >&2
    exit 1
  fi

  mkdir -p "$(dirname "$target_path")"
  cp "$source_path" "$target_path"
  echo "created $target_path"
  created=$((created + 1))
}

echo "==> Initializing repo-local files"

create_from_example "$repo_root/env.local.example" "$repo_root/.env.local"
create_from_example \
  "$repo_root/packer/variables.auto.pkrvars.hcl.example" \
  "$repo_root/packer/variables.auto.pkrvars.hcl"
create_from_example \
  "$repo_root/ansible/inventory/hosts.yml.example" \
  "$repo_root/ansible/inventory/hosts.yml"
create_from_example \
  "$repo_root/ansible/group_vars/all.yml.example" \
  "$repo_root/ansible/group_vars/all.yml"
create_from_example \
  "$repo_root/ansible/group_vars/foundation.yml.example" \
  "$repo_root/ansible/group_vars/foundation.yml"
create_from_example \
  "$repo_root/ansible/group_vars/vault.yml.example" \
  "$repo_root/ansible/group_vars/vault.yml"

for terraform_env_dir in "$repo_root"/terraform/environments/*; do
  if [[ ! -d "$terraform_env_dir" ]]; then
    continue
  fi

  example_path="$terraform_env_dir/terraform.tfvars.example"
  if [[ ! -f "$example_path" ]]; then
    continue
  fi

  create_from_example "$example_path" "$terraform_env_dir/terraform.tfvars"

  if [[ -n "$deployment_env" ]]; then
    create_from_example "$example_path" \
      "$terraform_env_dir/terraform.$deployment_env.tfvars"
  fi
done

if [[ -n "$deployment_env" ]]; then
  create_from_example \
    "$repo_root/ansible/inventory/hosts.yml.example" \
    "$repo_root/ansible/inventory/$deployment_env.yml"
  create_from_example \
    "$repo_root/ansible/group_vars/foundation.yml.example" \
    "$repo_root/ansible/group_vars/foundation.$deployment_env.yml"
  create_from_example \
    "$repo_root/ansible/group_vars/vault.yml.example" \
    "$repo_root/ansible/group_vars/vault.$deployment_env.yml"
fi

echo "Review and edit the local files before deployment."
echo "Created $created file(s). Existing files were left untouched."
