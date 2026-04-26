#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/deploy.sh <setup> [options]

Setups:
  bootstrap
  foundation
  lab
  vault
  hsm-lab

Options:
  --env NAME        Use Terraform workspace NAME and terraform.NAME.tfvars.
  --env-file PATH   Override the deployment environment file path.
                   By default, .env.local is used when it exists.
  --var-file PATH   Override the Terraform variable file.
  --ansible-vars PATH
                   Add an Ansible vars file for the mapped playbooks.
  --plan-only       Run Terraform init and plan, then stop.
  --terraform-only  Run the precheck and Terraform only.
  --ansible-only    Run the precheck and mapped Ansible playbooks only.
  --destroy         Destroy the Terraform resources for this setup.
  --auto-approve    Pass -auto-approve to terraform apply.
  --inventory PATH  Override the Ansible inventory file.
  -h, --help        Show this help text.

Examples:
  bash scripts/deploy.sh foundation
  bash scripts/deploy.sh foundation --env-file secrets/proxmox.env
  bash scripts/deploy.sh foundation --env test --plan-only
  bash scripts/deploy.sh foundation --env prod \
    --inventory ansible/inventory/prod.yml \
    --ansible-vars ansible/group_vars/foundation.prod.yml
  bash scripts/deploy.sh foundation --env test --destroy
  bash scripts/deploy.sh vault --plan-only
  bash scripts/deploy.sh hsm-lab --auto-approve
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

setup_name="$1"
shift

plan_only=false
terraform_only=false
ansible_only=false
auto_approve=false
destroy=false
deployment_env="default"
env_file_path=""
var_file_path=""
inventory_path=""
ansible_vars_paths=()

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
    --var-file)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --var-file" >&2
        exit 1
      fi
      var_file_path="$2"
      shift 2
      ;;
    --env-file)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --env-file" >&2
        exit 1
      fi
      env_file_path="$2"
      shift 2
      ;;
    --ansible-vars)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --ansible-vars" >&2
        exit 1
      fi
      ansible_vars_paths+=("$2")
      shift 2
      ;;
    --plan-only)
      plan_only=true
      shift
      ;;
    --terraform-only)
      terraform_only=true
      shift
      ;;
    --ansible-only)
      ansible_only=true
      shift
      ;;
    --destroy)
      destroy=true
      shift
      ;;
    --auto-approve)
      auto_approve=true
      shift
      ;;
    --inventory)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --inventory" >&2
        exit 1
      fi
      inventory_path="$2"
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

if [[ "$plan_only" == true && "$ansible_only" == true ]]; then
  echo "--plan-only and --ansible-only cannot be used together." >&2
  exit 1
fi

if [[ "$terraform_only" == true && "$ansible_only" == true ]]; then
  echo "--terraform-only and --ansible-only cannot be used together." >&2
  exit 1
fi

if [[ "$destroy" == true && "$ansible_only" == true ]]; then
  echo "--destroy and --ansible-only cannot be used together." >&2
  exit 1
fi

if [[ ! "$deployment_env" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "--env may only contain letters, numbers, underscores, and dashes." >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ansible_dir="$repo_root/ansible"

if [[ -z "$inventory_path" ]]; then
  inventory_path="$ansible_dir/inventory/hosts.yml"
elif [[ "$inventory_path" != /* ]]; then
  inventory_path="$repo_root/$inventory_path"
fi

if [[ -z "$env_file_path" && -f "$repo_root/.env.local" ]]; then
  env_file_path="$repo_root/.env.local"
elif [[ -n "$env_file_path" && "$env_file_path" != /* ]]; then
  env_file_path="$repo_root/$env_file_path"
fi

case "$setup_name" in
  bootstrap)
    terraform_dir="$repo_root/terraform/environments/bootstrap"
    ansible_playbooks=("bootstrap.yml")
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  foundation)
    terraform_dir="$repo_root/terraform/environments/foundation"
    ansible_playbooks=("foundation.yml")
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  lab)
    terraform_dir="$repo_root/terraform/environments/lab"
    ansible_playbooks=("site.yml")
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  vault)
    terraform_dir="$repo_root/terraform/environments/vault"
    ansible_playbooks=("vault.yml")
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
      "$ansible_dir/group_vars/vault.yml"
    )
    ;;
  hsm-lab)
    terraform_dir="$repo_root/terraform/environments/hsm-lab"
    ansible_playbooks=("site.yml" "ingress.yml")
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  *)
    echo "Unknown setup: $setup_name" >&2
    usage
    exit 1
    ;;
esac

if [[ -z "$var_file_path" ]]; then
  if [[ "$deployment_env" == "default" ]]; then
    var_file_path="$terraform_dir/terraform.tfvars"
  else
    var_file_path="$terraform_dir/terraform.$deployment_env.tfvars"
  fi
elif [[ "$var_file_path" != /* ]]; then
  var_file_path="$repo_root/$var_file_path"
fi

required_files=("$var_file_path" "${required_files[@]}")

resolved_ansible_vars_paths=()
for ansible_vars_path in "${ansible_vars_paths[@]}"; do
  if [[ "$ansible_vars_path" != /* ]]; then
    ansible_vars_path="$repo_root/$ansible_vars_path"
  fi

  resolved_ansible_vars_paths+=("$ansible_vars_path")
  required_files+=("$ansible_vars_path")
done

if [[ "$setup_name" == "foundation" && "${#resolved_ansible_vars_paths[@]}" -eq 0 ]]; then
  required_files+=("$ansible_dir/group_vars/foundation.yml")
fi

load_env_file() {
  if [[ -z "$env_file_path" ]]; then
    return
  fi

  if [[ ! -f "$env_file_path" ]]; then
    echo "Environment file not found: $env_file_path" >&2
    exit 1
  fi

  echo "==> Loading environment file $env_file_path"

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"

    if [[ -z "$line" || "$line" == \#* ]]; then
      continue
    fi

    if [[ "$line" == export\ * ]]; then
      line="${line#export }"
    fi

    if [[ "$line" != *=* ]]; then
      echo "Invalid environment file line: $line" >&2
      exit 1
    fi

    local key="${line%%=*}"
    local value="${line#*=}"

    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"

    if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      echo "Invalid environment variable name: $key" >&2
      exit 1
    fi

    if [[ "$value" =~ ^\".*\"$ || "$value" =~ ^\'.*\'$ ]]; then
      value="${value:1:${#value}-2}"
    fi

    export "$key=$value"
  done < "$env_file_path"

}

map_provider_env() {
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
}

check_required_files() {
  local missing_files=()

  for file_path in "${required_files[@]}"; do
    if [[ ! -f "$file_path" ]]; then
      missing_files+=("$file_path")
    fi
  done

  if [[ "${#missing_files[@]}" -gt 0 ]]; then
    echo "Missing required local configuration files for $setup_name ($deployment_env):" >&2
    for file_path in "${missing_files[@]}"; do
      echo "  - $file_path" >&2
    done
    echo "Run scripts/init-local-files.sh, then edit the generated files before deployment." >&2
    if [[ "$deployment_env" != "default" ]]; then
      echo "For this environment, use scripts/init-local-files.sh --env $deployment_env." >&2
    fi
    exit 1
  fi
}

run_control_node_precheck() {
  echo "==> Running deployment control-node precheck"
  (
    cd "$ansible_dir"
    ansible-playbook playbooks/control-node.yml
  )
}

run_terraform() {
  echo "==> Running Terraform for $setup_name"
  (
    cd "$terraform_dir"
    terraform init

    if [[ "$deployment_env" != "default" ]]; then
      terraform workspace select "$deployment_env" || terraform workspace new "$deployment_env"
    fi

    terraform_args=("-var-file=$var_file_path")

    if [[ "$destroy" == true ]]; then
      terraform plan -destroy "${terraform_args[@]}"

      if [[ "$plan_only" == true ]]; then
        exit 0
      fi

      if [[ "$auto_approve" == true ]]; then
        terraform destroy -auto-approve "${terraform_args[@]}"
      else
        terraform destroy "${terraform_args[@]}"
      fi

      exit 0
    fi

    terraform plan "${terraform_args[@]}"

    if [[ "$plan_only" == true ]]; then
      exit 0
    fi

    if [[ "$auto_approve" == true ]]; then
      terraform apply -auto-approve "${terraform_args[@]}"
    else
      terraform apply "${terraform_args[@]}"
    fi
  )
}

run_ansible_playbooks() {
  echo "==> Running Ansible playbooks for $setup_name"
  (
    cd "$ansible_dir"
    ansible_args=("-i" "$inventory_path")
    for vars_file in "${resolved_ansible_vars_paths[@]}"; do
      ansible_args+=("-e" "@$vars_file")
    done

    for playbook in "${ansible_playbooks[@]}"; do
      ansible-playbook "${ansible_args[@]}" "playbooks/$playbook"
    done
  )
}

if ! command -v ansible-playbook >/dev/null 2>&1; then
  echo "ansible-playbook is not installed on this deployment machine." >&2
  exit 1
fi

check_required_files
load_env_file
map_provider_env
run_control_node_precheck

if [[ "$ansible_only" == false ]]; then
  check_provider_env
  run_terraform
fi

if [[ "$plan_only" == true || "$terraform_only" == true ]]; then
  exit 0
fi

if [[ "$destroy" == true ]]; then
  exit 0
fi

run_ansible_playbooks
