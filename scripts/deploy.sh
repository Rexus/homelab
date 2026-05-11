#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/deploy.sh <setup> [options]

Setups:
  foundation
  edge
  cache
  development
  observability
  podman-runner
  image-template
  template-refresh
  lab
  vault
  hsm

Options:
  --env NAME        Use ansible/group_vars/all.NAME.yml, matching setup vars,
                   and separate local state. Optional terraform.NAME.tfvars
                   files are layered only when present. Omit for production.
  --env-file PATH   Override the deployment environment file path.
                   By default, .env.local is used when it exists.
  --var-file PATH   Override the base setup Terraform variable file.
  --common-var-file PATH
                   Override the shared Terraform variable file.
  --ansible-vars PATH
                   Add an extra Ansible vars file after automatic vars.
  --plan-only       Run Terraform init and plan, then stop.
  --terraform-only  Run the precheck and Terraform only.
  --ansible-only    Run the precheck and mapped Ansible playbooks only.
  --destroy         Destroy the Terraform resources for this setup.
  --auto-approve    Pass -auto-approve to terraform apply.
  --reset-known-hosts
                   Remove local SSH known_hosts entries for this setup's
                   static IPs before Ansible runs.
  --inventory PATH  Override the Ansible inventory file.
  -h, --help        Show this help text.

Examples:
  bash scripts/deploy.sh foundation
  bash scripts/deploy.sh foundation --env test --plan-only
  bash scripts/deploy.sh foundation --env-file secrets/proxmox.env
  bash scripts/deploy.sh foundation --env lab1
  bash scripts/deploy.sh foundation --env test --reset-known-hosts
  bash scripts/deploy.sh foundation --env test --destroy
  bash scripts/deploy.sh edge --env test --plan-only
  bash scripts/deploy.sh cache --env test --plan-only
  bash scripts/deploy.sh vault --plan-only
  bash scripts/deploy.sh development --env test --plan-only
  bash scripts/deploy.sh observability --env test --plan-only
  bash scripts/deploy.sh podman-runner --env test --plan-only
  bash scripts/deploy.sh image-template --env test --plan-only
  bash scripts/deploy.sh template-refresh --env test --plan-only
  bash scripts/deploy.sh hsm --auto-approve
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
reset_known_hosts=false
deployment_env="prod"
explicit_env=false
env_file_path=""
var_file_path=""
common_var_file_path=""
environment_var_file_path=""
environment_common_var_file_path=""
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
      explicit_env=true
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
    --common-var-file)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --common-var-file" >&2
        exit 1
      fi
      common_var_file_path="$2"
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
    --reset-known-hosts)
      reset_known_hosts=true
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

if [[ ! "$deployment_env" =~ ^[A-Za-z0-9-]+$ ]]; then
  echo "--env may only contain letters, numbers, and dashes." >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ansible_dir="$repo_root/ansible"
ansible_group_vars_paths=("$ansible_dir/group_vars/all.yml")
environment_ansible_vars_path=""
setup_ansible_vars_base_path=""
environment_setup_ansible_vars_path=""
setup_ansible_vars_required=false
setup_ansible_vars_env_stem="$setup_name"

if [[ "$explicit_env" == true ]]; then
  environment_ansible_vars_path="$ansible_dir/group_vars/all.$deployment_env.yml"
fi

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

if [[ -z "$common_var_file_path" && -f "$repo_root/terraform/common.tfvars" ]]; then
  common_var_file_path="$repo_root/terraform/common.tfvars"
elif [[ -n "$common_var_file_path" && "$common_var_file_path" != /* ]]; then
  common_var_file_path="$repo_root/$common_var_file_path"
fi

if [[ -z "$common_var_file_path" && "$explicit_env" == true \
  && -f "$repo_root/terraform/common.$deployment_env.tfvars" ]]; then
  common_var_file_path="$repo_root/terraform/common.$deployment_env.tfvars"
elif [[ -n "$common_var_file_path" && "$explicit_env" == true \
  && -f "$repo_root/terraform/common.$deployment_env.tfvars" ]]; then
  environment_common_var_file_path="$repo_root/terraform/common.$deployment_env.tfvars"
fi

case "$setup_name" in
  foundation)
    terraform_dir="$repo_root/terraform/environments/foundation"
    ansible_playbooks=("foundation.yml")
    setup_ansible_vars_base_path="$ansible_dir/group_vars/foundation.yml"
    setup_ansible_vars_required=true
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  edge)
    terraform_dir="$repo_root/terraform/environments/edge"
    ansible_playbooks=("edge.yml")
    setup_ansible_vars_base_path="$ansible_dir/group_vars/edge.yml"
    setup_ansible_vars_required=true
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  cache)
    terraform_dir="$repo_root/terraform/environments/cache"
    ansible_playbooks=("cache.yml")
    setup_ansible_vars_base_path="$ansible_dir/group_vars/cache.yml"
    setup_ansible_vars_required=true
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  development)
    terraform_dir="$repo_root/terraform/environments/development"
    ansible_playbooks=("development.yml")
    setup_ansible_vars_base_path="$ansible_dir/group_vars/development.yml"
    setup_ansible_vars_required=true
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  observability)
    terraform_dir="$repo_root/terraform/environments/observability"
    ansible_playbooks=("observability.yml")
    setup_ansible_vars_base_path="$ansible_dir/group_vars/observability.yml"
    setup_ansible_vars_required=true
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  podman-runner)
    terraform_dir="$repo_root/terraform/environments/podman-runner"
    ansible_playbooks=("podman-runner.yml")
    setup_ansible_vars_base_path="$ansible_dir/group_vars/podman_runner.yml"
    setup_ansible_vars_env_stem="podman_runner"
    setup_ansible_vars_required=true
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  image-template)
    terraform_dir="$repo_root/terraform/environments/image-template"
    ansible_playbooks=("image-template.yml")
    setup_ansible_vars_base_path="$ansible_dir/group_vars/image_template.yml"
    setup_ansible_vars_env_stem="image_template"
    setup_ansible_vars_required=true
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  template-refresh)
    terraform_dir="$repo_root/terraform/environments/template-refresh"
    ansible_playbooks=("template-refresh.yml")
    setup_ansible_vars_base_path="$ansible_dir/group_vars/template_refresh.yml"
    setup_ansible_vars_env_stem="template_refresh"
    setup_ansible_vars_required=true
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  lab)
    terraform_dir="$repo_root/terraform/environments/lab"
    ansible_playbooks=("lab.yml")
    setup_ansible_vars_base_path="$ansible_dir/group_vars/lab.yml"
    setup_ansible_vars_required=true
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  vault)
    terraform_dir="$repo_root/terraform/environments/vault"
    ansible_playbooks=("vault.yml")
    setup_ansible_vars_base_path="$ansible_dir/group_vars/vault.yml"
    setup_ansible_vars_required=true
    required_files=(
      "$inventory_path"
      "$ansible_dir/group_vars/all.yml"
    )
    ;;
  hsm)
    terraform_dir="$repo_root/terraform/environments/hsm"
    ansible_playbooks=("hsm.yml" "ingress.yml")
    setup_ansible_vars_base_path="$ansible_dir/group_vars/hsm.yml"
    setup_ansible_vars_required=true
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
  var_file_path="$terraform_dir/terraform.tfvars"
elif [[ "$var_file_path" != /* ]]; then
  var_file_path="$repo_root/$var_file_path"
fi

if [[ "$explicit_env" == true \
  && -f "$terraform_dir/terraform.$deployment_env.tfvars" \
  && "$var_file_path" == "$terraform_dir/terraform.tfvars" ]]; then
  environment_var_file_path="$terraform_dir/terraform.$deployment_env.tfvars"
fi

if [[ "$explicit_env" == true ]]; then
  setup_env_candidate_path="$ansible_dir/group_vars/$setup_ansible_vars_env_stem.$deployment_env.yml"
  if [[ "$setup_ansible_vars_required" == true || -f "$setup_env_candidate_path" ]]; then
    environment_setup_ansible_vars_path="$setup_env_candidate_path"
  fi
fi

required_files=("$var_file_path" "${required_files[@]}")
if [[ "$setup_ansible_vars_required" == true ]]; then
  required_files=("$setup_ansible_vars_base_path" "${required_files[@]}")
fi
if [[ -n "$environment_ansible_vars_path" ]]; then
  required_files=("$environment_ansible_vars_path" "${required_files[@]}")
fi
if [[ -n "$environment_setup_ansible_vars_path" ]]; then
  required_files=("$environment_setup_ansible_vars_path" "${required_files[@]}")
fi
if [[ -n "$common_var_file_path" ]]; then
  required_files=("$common_var_file_path" "${required_files[@]}")
fi
if [[ -n "$environment_common_var_file_path" ]]; then
  required_files=("$environment_common_var_file_path" "${required_files[@]}")
fi
if [[ -n "$environment_var_file_path" ]]; then
  required_files=("$environment_var_file_path" "${required_files[@]}")
fi

resolved_ansible_vars_paths=("$ansible_dir/group_vars/all.yml")
if [[ "$setup_ansible_vars_required" == true && -n "$setup_ansible_vars_base_path" ]]; then
  resolved_ansible_vars_paths+=("$setup_ansible_vars_base_path")
fi
if [[ -n "$environment_ansible_vars_path" ]]; then
  resolved_ansible_vars_paths+=("$environment_ansible_vars_path")
fi
if [[ -n "$environment_setup_ansible_vars_path" ]]; then
  resolved_ansible_vars_paths+=("$environment_setup_ansible_vars_path")
fi

ansible_group_vars_paths=("$ansible_dir/group_vars/all.yml")
if [[ "$setup_ansible_vars_required" == true && -n "$setup_ansible_vars_base_path" ]]; then
  ansible_group_vars_paths+=("$setup_ansible_vars_base_path")
fi
if [[ -n "$environment_ansible_vars_path" ]]; then
  ansible_group_vars_paths+=("$environment_ansible_vars_path")
fi
if [[ -n "$environment_setup_ansible_vars_path" ]]; then
  ansible_group_vars_paths+=("$environment_setup_ansible_vars_path")
fi

for ansible_vars_path in "${ansible_vars_paths[@]}"; do
  if [[ "$ansible_vars_path" != /* ]]; then
    ansible_vars_path="$repo_root/$ansible_vars_path"
  fi

  resolved_ansible_vars_paths+=("$ansible_vars_path")
  required_files+=("$ansible_vars_path")
done

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

    case "$key" in
      ansible_dir|deployment_env|env_file_path|inventory_path|repo_root|setup_name|terraform_dir|terraform_state_path|terraform_data_dir|var_file_path)
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
    echo "Run scripts/init-local-files.sh --setup $setup_name, then edit the generated files." >&2
    if [[ "$explicit_env" == true ]]; then
      echo "For this environment, use scripts/init-local-files.sh --setup $setup_name --env $deployment_env." >&2
    fi
    exit 1
  fi
}

run_control_node_precheck() {
  echo "==> Running deployment control-node precheck"
  (
    cd "$ansible_dir"
    ansible-playbook -i localhost, playbooks/control-node.yml
  )
}

collect_static_host_ips() {
  local vars_file

  for vars_file in "${resolved_ansible_vars_paths[@]}"; do
    if [[ ! -f "$vars_file" ]]; then
      continue
    fi

    awk '
      /^[[:space:]]*platform_host_ips:[[:space:]]*$/ {
        in_map = 1
        next
      }
      in_map && /^[^[:space:]#]/ {
        in_map = 0
      }
      in_map && /^[[:space:]]+[A-Za-z0-9_.-]+:[[:space:]]*[^#[:space:]]+/ {
        line = $0
        sub(/#.*/, "", line)
        sub(/^[[:space:]]+[A-Za-z0-9_.-]+:[[:space:]]*/, "", line)
        gsub(/["\047]/, "", line)
        gsub(/[[:space:]]+$/, "", line)
        if (line != "" && line != "dhcp") {
          print line
        }
      }
    ' "$vars_file"
  done | sort -u
}

reset_known_host_entries() {
  local known_hosts_file="${HOME}/.ssh/known_hosts"
  local target
  local removed=0

  if [[ "$reset_known_hosts" == false ]]; then
    return
  fi

  if [[ ! -f "$known_hosts_file" ]]; then
    echo "==> No SSH known_hosts file found at $known_hosts_file"
    return
  fi

  if ! command -v ssh-keygen >/dev/null 2>&1; then
    echo "ssh-keygen is required for --reset-known-hosts." >&2
    exit 1
  fi

  echo "==> Removing SSH known_hosts entries for $setup_name ($deployment_env)"

  while IFS= read -r target; do
    if [[ -z "$target" ]]; then
      continue
    fi

    ssh-keygen -R "$target" -f "$known_hosts_file" >/dev/null 2>&1 || true
    ssh-keygen -R "[$target]:22" -f "$known_hosts_file" >/dev/null 2>&1 || true
    echo "removed known_hosts entries for $target"
    removed=$((removed + 1))
  done < <(collect_static_host_ips)

  echo "Removed known_hosts entries for $removed static host target(s)."
}

run_terraform() {
  echo "==> Running Terraform for $setup_name"
  (
    echo "==> Terraform directory $terraform_dir"
    cd "$terraform_dir"
    terraform_state_path="$repo_root/.terraform/state/$setup_name/$deployment_env/terraform.tfstate"
    terraform_data_dir="$repo_root/.terraform/data/$setup_name/$deployment_env"
    mkdir -p "$(dirname "$terraform_state_path")"
    mkdir -p "$terraform_data_dir"
    echo "==> Using Terraform state $terraform_state_path"
    export TF_DATA_DIR="$terraform_data_dir"
    if [[ -d "$TF_DATA_DIR/modules" ]]; then
      echo "==> Refreshing Terraform module cache"
      rm -rf "$TF_DATA_DIR/modules"
    fi
    terraform init -reconfigure -backend-config="path=$terraform_state_path"

    terraform_args=()
    if [[ -n "$common_var_file_path" ]]; then
      terraform_args+=("-var-file=$common_var_file_path")
    fi
    if [[ -n "$environment_common_var_file_path" ]]; then
      terraform_args+=("-var-file=$environment_common_var_file_path")
    fi
    terraform_group_vars_arg="["
    terraform_group_vars_separator=""
    for group_vars_path in "${ansible_group_vars_paths[@]}"; do
      escaped_group_vars_path="${group_vars_path//\\/\\\\}"
      escaped_group_vars_path="${escaped_group_vars_path//\"/\\\"}"
      terraform_group_vars_arg+="$terraform_group_vars_separator\"$escaped_group_vars_path\""
      terraform_group_vars_separator=","
    done
    terraform_group_vars_arg+="]"

    terraform_args+=("-var=ansible_inventory_path=$inventory_path")
    terraform_args+=("-var=ansible_group_vars_paths=$terraform_group_vars_arg")
    terraform_args+=("-var-file=$var_file_path")
    if [[ -n "$environment_var_file_path" ]]; then
      terraform_args+=("-var-file=$environment_var_file_path")
    fi

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

reset_known_host_entries
run_ansible_playbooks
