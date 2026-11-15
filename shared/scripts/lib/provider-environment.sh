#!/usr/bin/env bash

# Shared by deploy.sh and the native Terraform recovery procedure.
# Set env_file_path, then call load_env_file, map_provider_env and check_provider_env.
# Parse literal dotenv values without evaluating shell commands or printing secrets.
# Guide: docs/05-operations/06-resilience/recovery/terraform-import.md

load_env_file() {
  if [[ -z "$env_file_path" ]]; then
    return
  fi

  if [[ ! -f "$env_file_path" ]]; then
    echo "Environment file not found: $env_file_path" >&2
    exit 1
  fi

  echo "==> Loading environment file $env_file_path"

  local line_number=0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line_number=$((line_number + 1))
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"

    if [[ -z "$line" || "$line" == \#* ]]; then
      continue
    fi

    if [[ "$line" == export\ * ]]; then
      line="${line#export }"
    fi

    if [[ "$line" != *=* ]]; then
      echo "Expected KEY=value in $env_file_path:$line_number" >&2
      exit 1
    fi

    local key="${line%%=*}"
    local value="${line#*=}"

    if [[ "${IAC_REQUIRE_VAULT_PROVIDER:-false}" == true && "$key" =~ ^(TF_VAR_proxmox_api_|PROXMOX_API_) ]]; then
      echo "Privileged CI environment files must not override Vault provider credentials." >&2
      exit 1
    fi

    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"

    if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      echo "Invalid environment variable name in $env_file_path:$line_number" >&2
      exit 1
    fi

    case "$key" in
      ansible_dir|ansible_playbook_dir|automation_root|DEPLOYMENT_REPO_DIR|SHARED_REPO_DIR|\
      IAC_REQUIRE_VAULT_PROVIDER|\
      deployment_env|env_file_path|inventory_path|repo_root|setup_name|terraform_dir|\
      terraform_state_path|terraform_data_dir|var_file_path|recipe|ansible_only|\
      terraform_only|plan_only|destroy|auto_approve|ansible_playbooks|playbook_override)
        echo "Environment file uses reserved wrapper variable: $key" >&2
        echo "Rename or remove it from $env_file_path." >&2
        exit 1
        ;;
    esac

    if [[ "$value" =~ ^\".*\"$ || "$value" =~ ^\'.*\'$ ]]; then
      value="${value:1:${#value}-2}"
    fi

    export "$key=$value"
  done < "$env_file_path"

}

map_provider_env() {
  if [[ "${IAC_REQUIRE_VAULT_PROVIDER:-false}" == true && (
    "${TF_VAR_proxmox_api_url:-}" != "${PROXMOX_API_URL:-}" ||
    "${TF_VAR_proxmox_api_token_id:-}" != "${PROXMOX_API_TOKEN_ID:-}" ||
    "${TF_VAR_proxmox_api_token_secret:-}" != "${PROXMOX_API_TOKEN_SECRET:-}" ) ]]; then
    echo "Local environment conflicts with Vault-injected provider credentials." >&2
    exit 1
  fi
  export TF_VAR_proxmox_api_url="${TF_VAR_proxmox_api_url:-${PROXMOX_API_URL:-}}"
  export TF_VAR_proxmox_api_token_id="${TF_VAR_proxmox_api_token_id:-${PROXMOX_API_TOKEN_ID:-}}"
  export TF_VAR_proxmox_api_token_secret="${TF_VAR_proxmox_api_token_secret:-${PROXMOX_API_TOKEN_SECRET:-}}"
}

check_provider_env() {
  local missing_vars=()

  if [[ -z "${TF_VAR_proxmox_api_url:-}" ]]; then
    missing_vars+=("TF_VAR_proxmox_api_url or PROXMOX_API_URL")
  fi

  if [[ -z "${TF_VAR_proxmox_api_token_id:-}" ]]; then
    missing_vars+=("TF_VAR_proxmox_api_token_id or PROXMOX_API_TOKEN_ID")
  fi

  if [[ -z "${TF_VAR_proxmox_api_token_secret:-}" ]]; then
    missing_vars+=("TF_VAR_proxmox_api_token_secret or PROXMOX_API_TOKEN_SECRET")
  fi

  if [[ "${#missing_vars[@]}" -gt 0 ]]; then
    echo "Missing Proxmox provider environment values:" >&2
    for var_name in "${missing_vars[@]}"; do
      echo "  - $var_name" >&2
    done
    echo "Set them in the shell, provide them through the runner, or pass --env-file." >&2
    exit 1
  fi

  if [[ "${TF_VAR_proxmox_api_url:-}" == *"/api2/"* ]]; then
    echo "Invalid Proxmox endpoint for Terraform: $TF_VAR_proxmox_api_url" >&2
    echo "Use the Proxmox web/API root, for example https://pve.example.com:8006/." >&2
    echo "Do not append /api2/json; that path is for the Packer Proxmox plugin." >&2
    exit 1
  fi
}
