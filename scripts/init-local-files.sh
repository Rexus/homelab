#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/init-local-files.sh [options]

Options:
  --env NAME   Also create environment-specific Ansible files, such as
               all.NAME.yml and setup vars like foundation.NAME.yml.
               Omit for the base production files.
  --overwrite  Replace existing local files from the current examples.
               Existing files are backed up first and ignored by Git.
  --clean-backups
               Remove timestamped backup files created by --overwrite and exit.
  -h, --help   Show this help text.

Examples:
  bash scripts/init-local-files.sh
  bash scripts/init-local-files.sh --env test
  bash scripts/init-local-files.sh --env lab1
  bash scripts/init-local-files.sh --overwrite
  bash scripts/init-local-files.sh --clean-backups
EOF
}

deployment_env=""
overwrite=false
clean_backups=false

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
    --overwrite)
      overwrite=true
      shift
      ;;
    --clean-backups|--cleanup-backups)
      clean_backups=true
      shift
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

if [[ -n "$deployment_env" && ! "$deployment_env" =~ ^[A-Za-z0-9-]+$ ]]; then
  echo "--env may only contain letters, numbers, and dashes." >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
created=0
updated=0
last_file_changed=false
backup_suffix="$(date +%Y%m%d%H%M%S)"
backup_name_pattern="*.bak.[0-9][0-9][0-9][0-9][0-9][0-9]"
backup_name_pattern+="[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]"

clean_timestamped_backups() {
  local removed=0
  local backup_path

  while IFS= read -r -d '' backup_path; do
    rm -f "$backup_path"
    echo "removed $backup_path"
    removed=$((removed + 1))
  done < <(
    find "$repo_root" \
      -path "$repo_root/.git" -prune -o \
      -type f -name "$backup_name_pattern" -print0
  )

  echo "Removed $removed backup file(s)."
}

if [[ "$clean_backups" == true ]]; then
  echo "==> Cleaning timestamped init-file backups"
  clean_timestamped_backups
  exit 0
fi

create_from_example() {
  local source_path="$1"
  local target_path="$2"
  local backup_path

  if [[ ! -f "$source_path" ]]; then
    echo "Missing example file: $source_path" >&2
    exit 1
  fi

  if [[ -f "$target_path" ]]; then
    if [[ "$overwrite" == false ]]; then
      echo "exists  $target_path"
      last_file_changed=false
      return
    fi

    backup_path="$target_path.bak.$backup_suffix"
    cp "$target_path" "$backup_path"
    cp "$source_path" "$target_path"
    echo "updated $target_path"
    echo "backup  $backup_path"
    updated=$((updated + 1))
    last_file_changed=true
    return
  fi

  mkdir -p "$(dirname "$target_path")"
  cp "$source_path" "$target_path"
  echo "created $target_path"
  created=$((created + 1))
  last_file_changed=true
}

echo "==> Initializing repo-local files"

create_from_example "$repo_root/env.local.example" "$repo_root/.env.local"
create_from_example \
  "$repo_root/packer/variables.auto.pkrvars.hcl.example" \
  "$repo_root/packer/variables.auto.pkrvars.hcl"
create_from_example \
  "$repo_root/terraform/common.tfvars.example" \
  "$repo_root/terraform/common.tfvars"
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
done

if [[ -n "$deployment_env" ]]; then
  environment_vars_file="$repo_root/ansible/group_vars/all.$deployment_env.yml"

  create_from_example \
    "$repo_root/ansible/group_vars/all.env.yml.example" \
    "$environment_vars_file"
  if [[ "$last_file_changed" == true ]]; then
    sed -i "s/platform_environment: lab1/platform_environment: $deployment_env/" \
      "$environment_vars_file"
    sed -i "s/platform_hostname_prefix: lab1-/platform_hostname_prefix: $deployment_env-/" \
      "$environment_vars_file"
    sed -i "s/platform_domain: lab1.example.com/platform_domain: $deployment_env.example.com/" \
      "$environment_vars_file"
  fi
  create_from_example \
    "$repo_root/ansible/group_vars/foundation.yml.example" \
    "$repo_root/ansible/group_vars/foundation.$deployment_env.yml"
  create_from_example \
    "$repo_root/ansible/group_vars/vault.yml.example" \
    "$repo_root/ansible/group_vars/vault.$deployment_env.yml"
fi

echo "Review and edit the local files before deployment."
echo "Created $created file(s). Updated $updated file(s)."
if [[ "$overwrite" == false ]]; then
  echo "Existing files were left untouched."
else
  echo "Updated files were backed up with suffix .bak.$backup_suffix."
fi
