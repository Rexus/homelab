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
  --setup NAME Create local files only for one setup plus shared defaults.
               May be used more than once. Omit to create every setup.
  --overwrite  Replace existing local files from the current examples.
               Existing files are backed up first and ignored by Git.
  --clean-backups
               Remove timestamped backup files created by --overwrite and exit.
  -h, --help   Show this help text.

Examples:
  bash scripts/init-local-files.sh
  bash scripts/init-local-files.sh --setup foundation
  bash scripts/init-local-files.sh --env test
  bash scripts/init-local-files.sh --setup foundation --env test
  bash scripts/init-local-files.sh --env lab1
  bash scripts/init-local-files.sh --overwrite
  bash scripts/init-local-files.sh --clean-backups
EOF
}

deployment_env=""
overwrite=false
clean_backups=false
selected_setups=()
all_setups=(
  foundation
  edge
  cache
  development
  observability
  podman-runner
  immutable-template
  template-refresh
  lab
  vault
  hsm
)

setup_group_vars_stem() {
  case "$1" in
    podman-runner)
      echo "podman_runner"
      ;;
    immutable-template)
      echo "immutable_template"
      ;;
    template-refresh)
      echo "template_refresh"
      ;;
    *)
      echo "$1"
      ;;
  esac
}

normalize_setup_name() {
  case "$1" in
    image-template)
      echo "immutable-template"
      ;;
    *)
      echo "$1"
      ;;
  esac
}

setup_is_valid() {
  local setup_name="$1"
  local known_setup

  for known_setup in "${all_setups[@]}"; do
    if [[ "$setup_name" == "$known_setup" ]]; then
      return 0
    fi
  done

  return 1
}

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
    --setup|--path)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for $1" >&2
        exit 1
      fi
      selected_setups+=("$(normalize_setup_name "$2")")
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

for setup_name in "${selected_setups[@]}"; do
  if ! setup_is_valid "$setup_name"; then
    echo "Unknown setup for --setup: $setup_name" >&2
    echo "Known setups: ${all_setups[*]}" >&2
    exit 1
  fi
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
created=0
updated=0
last_file_changed=false
full_init=true
setups_to_create=()
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

if [[ "${#selected_setups[@]}" -gt 0 ]]; then
  full_init=false
  setups_to_create=("${selected_setups[@]}")
else
  setups_to_create=("${all_setups[@]}")
fi

create_setup_files() {
  local setup_name="$1"
  local stem
  local terraform_env_dir
  local terraform_example_path

  stem="$(setup_group_vars_stem "$setup_name")"
  create_from_example \
    "$repo_root/ansible/group_vars/$stem.yml.example" \
    "$repo_root/ansible/group_vars/$stem.yml"

  terraform_env_dir="$repo_root/terraform/environments/$setup_name"
  terraform_example_path="$terraform_env_dir/terraform.tfvars.example"
  if [[ -f "$terraform_example_path" ]]; then
    create_from_example "$terraform_example_path" "$terraform_env_dir/terraform.tfvars"
  fi
}

create_environment_setup_file() {
  local setup_name="$1"
  local stem

  stem="$(setup_group_vars_stem "$setup_name")"
  create_from_example \
    "$repo_root/ansible/group_vars/$stem.yml.example" \
    "$repo_root/ansible/group_vars/$stem.$deployment_env.yml"
}

echo "==> Initializing repo-local files"

create_from_example "$repo_root/env.local.example" "$repo_root/.env.local"
create_from_example \
  "$repo_root/terraform/common.tfvars.example" \
  "$repo_root/terraform/common.tfvars"
create_from_example \
  "$repo_root/ansible/inventory/hosts.yml.example" \
  "$repo_root/ansible/inventory/hosts.yml"
create_from_example \
  "$repo_root/ansible/group_vars/all.yml.example" \
  "$repo_root/ansible/group_vars/all.yml"

if [[ "$full_init" == true ]]; then
  create_from_example \
    "$repo_root/packer/variables.auto.pkrvars.hcl.example" \
    "$repo_root/packer/variables.auto.pkrvars.hcl"
fi

for setup_name in "${setups_to_create[@]}"; do
  create_setup_files "$setup_name"
done

if [[ -n "$deployment_env" ]]; then
  environment_vars_file="$repo_root/ansible/group_vars/all.$deployment_env.yml"

  create_from_example \
    "$repo_root/ansible/group_vars/all.env.yml.example" \
    "$environment_vars_file"
  if [[ "$last_file_changed" == true ]]; then
    sed -i "s/platform_environment: test/platform_environment: $deployment_env/" \
      "$environment_vars_file"
    sed -i "s/platform_domain: test.example.com/platform_domain: $deployment_env.example.com/" \
      "$environment_vars_file"
  fi

  for setup_name in "${setups_to_create[@]}"; do
    create_environment_setup_file "$setup_name"
  done
fi

echo "Review and edit the local files before deployment."
echo "Created $created file(s). Updated $updated file(s)."
if [[ "$overwrite" == false ]]; then
  echo "Existing files were left untouched."
else
  echo "Updated files were backed up with suffix .bak.$backup_suffix."
fi
