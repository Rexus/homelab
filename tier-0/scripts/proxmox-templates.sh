#!/usr/bin/env bash

set -euo pipefail
umask 077

usage() {
  echo "Usage: bash ${BASH_SOURCE[0]} {init|plan|import|apply|verify|replace-disk} [--env-file PATH] [--platform-file PATH]"
  echo "import prepares a reviewed adoption plan; apply writes imports and any listed changes."
  echo "replace-disk --template KEY previews the operation, then prompts for execution."
  echo "apply completes fixed-RAM/account policy; verify [--template KEY] checks live settings without changes."
  echo "Use --preview for read-only inspection; use --execute with --expected-disk VOLUME and --expected-sha256 SHA in automation."
  echo "Use --env-file .env.local for local credentials; otherwise only exported credentials are used."
}
if [[ $# == 1 && ( "$1" == --help || "$1" == -h ) ]]; then
  usage
  exit 0
fi
if [[ $# == 0 || ! "$1" =~ ^(init|plan|import|apply|verify|replace-disk)$ ]]; then
  usage >&2
  echo "Run from Tier 0. Reference: docs/administration/compute/template-lifecycle.md" >&2
  exit 1
fi
action="$1"
shift
repo_root="$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ ! . -ef "$repo_root" ]]; then
  echo "Run this command from the Tier 0 repository root." >&2
  echo "Expected: $repo_root; current: $(pwd -P)" >&2
  exit 1
fi
terraform_dir="$repo_root/terraform/deployments/templates"
if [[ ! -f "$terraform_dir/main.tf" || ! -f "$repo_root/templates/proxmox.yml.example" ]]; then
  echo "Template publication requires the Tier 0 template root and catalog example." >&2
  exit 1
fi

catalog="${TEMPLATE_CATALOG_FILE:-$repo_root/templates/proxmox.yml}"
state="${TEMPLATE_STATE_PATH:-$repo_root/.terraform/state/proxmox-templates/terraform.tfstate}"
plan="$repo_root/.terraform/plans/proxmox-templates.tfplan"
if [[ "$action" == plan || "$action" == import ]]; then
  # A failed re-plan must not leave a previous apply target, even if validation or init fails.
  rm -f "$plan"
fi
env_file=""
platform_file="${TEMPLATE_PLATFORM_FILE:-}"
template_key="" expected_disk="" expected_sha256="" execute=false preview=false interactive=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file|--platform-file|--template|--expected-disk|--expected-sha256)
      if [[ $# -lt 2 || -z "$2" || "$2" == --* ]]; then
        echo "Missing path for $1" >&2
        exit 1
      fi
      case "$1" in
        --env-file) env_file="$2" ;;
        --platform-file) platform_file="$2" ;;
        --template) template_key="$2" ;;
        --expected-disk) expected_disk="$2" ;;
        --expected-sha256) expected_sha256="$2" ;;
      esac
      shift 2
      ;;
    --execute) execute=true; shift ;;
    --preview) preview=true; shift ;;
    *) usage >&2; exit 1 ;;
  esac
done
if [[ "$action" == replace-disk ]]; then
  [[ "$template_key" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || { echo "Select one catalog key with --template KEY." >&2; exit 1; }
  if [[ "$execute" == true && "$preview" == true ]]; then
    echo "Choose --preview or --execute, not both." >&2; exit 1
  fi
  if [[ "$execute" == true ]]; then
    [[ "$expected_disk" =~ ^[A-Za-z0-9_.-]+:[A-Za-z0-9_./-]+$ && "$expected_sha256" =~ ^[a-f0-9]{64}$ ]] || {
      echo "Execution requires the reviewed --expected-disk VOLUME and --expected-sha256 SHA." >&2; exit 1;
    }
  elif [[ -n "$expected_disk$expected_sha256" ]]; then
    echo "Expected disk/hash flags require --execute." >&2; exit 1
  elif [[ "$preview" == false ]]; then
    interactive=true
  fi
elif [[ "$action" == verify ]]; then
  if [[ -n "$expected_disk$expected_sha256" || "$execute" == true || "$preview" == true ]]; then
    echo "verify accepts only an optional --template KEY selection." >&2; exit 1
  fi
  [[ -z "$template_key" || "$template_key" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || exit 1
elif [[ -n "$template_key$expected_disk$expected_sha256" || "$execute" == true || "$preview" == true ]]; then
  echo "Disk-maintenance flags are valid only with replace-disk." >&2; exit 1
fi
for path in "$catalog" "$state"; do
  if [[ "$path" != /* ]]; then
    echo "TEMPLATE_CATALOG_FILE and TEMPLATE_STATE_PATH must be absolute paths." >&2
    exit 1
  fi
done
export TF_DATA_DIR="$repo_root/.terraform/data/proxmox-templates"

for file in "$repo_root/terraform/templates/"*.tf "$repo_root/terraform/templates/"*.tfvars \
  "$repo_root/terraform/templates/"*.tf.json "$repo_root/terraform/templates/"*.tfvars.json; do
  [[ -f "$file" ]] || continue
  echo "Legacy Terraform deployment found: terraform/templates" >&2
  echo "Migrate to terraform/deployments/templates before continuing." >&2
  echo "See docs/development/generated-repositories.md#terraform-layout-upgrade." >&2
  exit 1
done

if [[ "$action" == init ]]; then
  if [[ ! -e "$catalog" ]]; then
    mkdir -p "$(dirname "$catalog")"
    cp -n "$repo_root/templates/proxmox.yml.example" "$catalog"
  fi
  if [[ ! -e "$repo_root/.env.local" ]]; then
    cp -n "$repo_root/env.local.example" "$repo_root/.env.local"
    chmod 600 "$repo_root/.env.local"
  fi
  echo "Review $catalog and .env.local, stage approved images, then run plan --env-file .env.local."
  exit 0
fi

# Parse literal assignments, never execute a local environment file as shell code.
if [[ -n "$env_file" ]]; then
  [[ -f "$env_file" ]] || { echo "Missing environment file: $env_file" >&2; exit 1; }
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
    if [[ ! "$line" =~ ^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      echo "Use literal KEY=value assignments in the environment file." >&2
      exit 1
    fi
    key="${BASH_REMATCH[2]}" value="${BASH_REMATCH[3]}"
    if [[ ! "$key" =~ ^(PROXMOX_[A-Z0-9_]+|PM_VE_INSECURE|TF_VAR_[A-Za-z0-9_]+|FREEIPA_[A-Z0-9_]+|ANSIBLE_VAULT_PASSWORD_FILE)$ ]]; then
      echo "Unsupported template environment key: $key" >&2
      exit 1
    fi
    if [[ "$value" =~ ^\".*\"$ || "$value" =~ ^\'.*\'$ ]]; then value="${value:1:${#value}-2}"; fi
    export "$key=$value"
  done < "$env_file"
fi

if [[ -n "${PROXMOX_API_URL:-}" ]]; then
  if [[ -n "${PROXMOX_VE_ENDPOINT:-}" && "$PROXMOX_VE_ENDPOINT" != "$PROXMOX_API_URL" ]]; then
    echo "Conflicting native and alias Proxmox endpoints; supply one credential set." >&2; exit 1
  fi
  export PROXMOX_VE_ENDPOINT="$PROXMOX_API_URL"
fi
if [[ -n "${PROXMOX_VE_ENDPOINT:-}" && ! "$PROXMOX_VE_ENDPOINT" =~ ^https://[^/]+/?$ ]]; then
  echo "Use an HTTPS Proxmox root endpoint without /api2/json." >&2
  exit 1
fi
if [[ -n "${PROXMOX_API_TOKEN_ID:-}" || -n "${PROXMOX_API_TOKEN_SECRET:-}" ]]; then
  if [[ -z "${PROXMOX_API_TOKEN_ID:-}" || -z "${PROXMOX_API_TOKEN_SECRET:-}" ]]; then
    echo "Both PROXMOX_API_TOKEN_ID and PROXMOX_API_TOKEN_SECRET are required." >&2; exit 1
  fi
  token="$PROXMOX_API_TOKEN_ID=$PROXMOX_API_TOKEN_SECRET"
  if [[ -n "${PROXMOX_VE_API_TOKEN:-}" && "$PROXMOX_VE_API_TOKEN" != "$token" ]]; then
    echo "Conflicting native and alias Proxmox tokens; supply one credential set." >&2; exit 1
  fi
  export PROXMOX_VE_API_TOKEN="$token"
  unset token
fi

# This bootstrap entry point intentionally works without the Shared repository.
for tls_option in PROXMOX_VE_INSECURE PM_VE_INSECURE; do
  case "${!tls_option:-}" in
    ''|0|f|F|false|False|FALSE) ;;
    *)
      echo "Refusing Proxmox TLS bypass: unset $tls_option and install approved API trust." >&2
      echo "See docs/administration/compute/proxmox-tls.md." >&2
      exit 1
      ;;
  esac
done

if [[ ( "$action" == plan || "$action" == import || "$action" == replace-disk ) && ! -f "$catalog" ]]; then
  echo "Missing catalog: $catalog. Run init first." >&2
  exit 1
fi

var_args=("-var=catalog_file=$catalog")
if [[ -z "$platform_file" && -f "$repo_root/../shared/config/platform.tfvars" ]]; then
  platform_file="$repo_root/../shared/config/platform.tfvars"
fi
if [[ -n "$platform_file" ]]; then
  [[ -f "$platform_file" ]] || { echo "Missing platform profile: $platform_file" >&2; exit 1; }
  platform_file="$(cd "$(dirname "$platform_file")" && pwd)/$(basename "$platform_file")"
  var_args=("-var-file=$platform_file" "${var_args[@]}")
fi
if [[ "$action" == apply && ! -f "$plan" ]]; then
  echo "No saved template plan. Run plan and review its output before apply." >&2
  exit 1
fi

if [[ "$action" == replace-disk || "$action" == apply || "$action" == verify ]]; then
  export ANSIBLE_CONFIG="$repo_root/ansible/ansible.cfg"
  export ANSIBLE_COLLECTIONS_ON_ANSIBLE_VERSION_MISMATCH=error
  template_tools=(ansible-playbook ansible-doc python3)
  template_modules=(community.proxmox.proxmox_vm_info community.proxmox.proxmox_kvm)
  if [[ "$action" == replace-disk ]]; then
    template_tools+=(qemu-img)
    template_modules+=(community.proxmox.proxmox_disk)
  fi
  for tool in "${template_tools[@]}"; do
    command -v "$tool" >/dev/null || {
      echo "Template apply/verification/maintenance requires $tool. See docs/administration/compute/template-lifecycle.md#prerequisites." >&2
      if [[ "$tool" == qemu-img ]]; then
        echo "Install on the execution host: sudo dnf install -y /usr/bin/qemu-img (Alma/Rocky/RHEL)" >&2
        echo "or sudo apt-get install -y qemu-utils (Debian/Ubuntu). This is an OS package, not a pip package." >&2
      fi
      exit 1
    }
  done
  # ansible-doc can return zero for missing plugins; verify its structured result instead.
  if ! ansible-doc --json -t module "${template_modules[@]}" | python3 -c '
import json, sys
try:
    modules = json.load(sys.stdin)
except ValueError:
    sys.exit("Cannot inspect Ansible modules; see the ansible-doc error above.")
missing = [name for name in sys.argv[1:] if not modules.get(name, {}).get("doc")]
if missing:
    print("Missing template modules: " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)
' "${template_modules[@]}"; then
    echo "Use ansible-core >=2.17 and community.proxmox >=2.1.0,<3.0.0 in the same accepted environment." >&2
    echo "Runtime setup: docs/development/local-setup.md#ansible-environment." >&2
    echo "Run: ansible-galaxy collection install 'community.proxmox:>=2.1.0,<3.0.0' --force" >&2
    echo "Python dependencies: ansible/requirements.txt. Guide: docs/administration/compute/template-disk.md#prerequisites." >&2
    exit 1
  fi
fi

mkdir -p "$TF_DATA_DIR" "$(dirname "$state")" "$(dirname "$plan")"
terraform -chdir="$terraform_dir" init -input=false -lockfile=readonly -reconfigure -backend-config="path=$state"
terraform -chdir="$terraform_dir" validate
if [[ "$action" == verify ]]; then
  policy_inputs="$repo_root/.terraform/plans/template-policy-inputs.json"
  terraform -chdir="$terraform_dir" output -json > "$policy_inputs"
  ansible-playbook -i localhost, -c local "$repo_root/ansible/playbooks/maintenance/template-policy.yml" \
    --extra-vars "@$policy_inputs" --extra-vars template_policy_apply=false --extra-vars "template_policy_key=$template_key"
  exit 0
fi
if [[ "$action" == replace-disk ]]; then
  disk_inputs="$repo_root/.terraform/plans/template-disk-inputs.json"
  terraform -chdir="$terraform_dir" output -json > "$disk_inputs"
  disk_result="$(mktemp "$repo_root/.terraform/plans/template-disk-result.XXXXXX")"
  trap 'rm -f "$disk_result"' EXIT
  result_args="$(python3 -c 'import json, sys; print(json.dumps({"template_disk_result_file": sys.argv[1]}))' "$disk_result")"
  ansible-playbook -i localhost, -c local "$repo_root/ansible/playbooks/maintenance/template-disk.yml" \
    --extra-vars "@$disk_inputs" --extra-vars "template_disk_key=$template_key" \
    --extra-vars "template_disk_execute=$execute" --extra-vars "template_disk_interactive=$interactive" \
    --extra-vars "template_disk_expected_disk=$expected_disk" \
    --extra-vars "template_disk_expected_sha256=$expected_sha256" --extra-vars "$result_args"
  disk_changed="$(python3 -c '
import json, sys
result = json.load(open(sys.argv[1]))
if not isinstance(result.get("changed"), bool):
    sys.exit("Missing verified maintenance outcome; inspect recovery receipts before continuing.")
print("true" if result["changed"] else "false")
' "$disk_result")"
  if [[ "$disk_changed" == true ]]; then
    rm -f "$plan"
    # Refresh records the new volume identity; it does not reconcile or apply VM settings.
    terraform -chdir="$terraform_dir" apply -refresh-only -auto-approve -input=false \
      -lock-timeout=60s "${var_args[@]}"
  elif [[ "$preview" == true ]]; then
    echo "Preview only. No disk changed. Rerun without --preview to review and confirm execution."
  else
    echo "Replacement declined. No disk changed."
  fi
  exit 0
fi
if [[ "$action" == plan || "$action" == import ]]; then
  adopt=false
  [[ "$action" == import ]] && adopt=true
  terraform -chdir="$terraform_dir" plan -input=false -lock-timeout=60s \
    "${var_args[@]}" -var="adopt_existing=$adopt" -out="$plan"
  if [[ "$action" == import ]]; then
    echo "Adoption plan only: review imports AND changes. State is not imported until apply."
    echo "Stop on unexpected updates/replacements. Back up existing state before apply."
  fi
  echo "Review the plan above. Apply publishes candidates; test clones before promoting them."
else
  apply_status=0
  # Serialize image uploads/imports to bound temporary storage use on the bootstrap host and Proxmox.
  terraform -chdir="$terraform_dir" apply -input=false -lock-timeout=60s -parallelism=1 "$plan" || apply_status=$?
  # A partial apply may already have recorded imports or created resources in state.
  rm -f "$plan"
  if [[ "$apply_status" != 0 ]]; then
    echo "Template apply failed; the saved plan was discarded. Keep the existing state." >&2
    echo "Resolve the reported error, rerun import --env-file .env.local (or plan), and review before apply." >&2
    echo "Reference: docs/administration/compute/template-lifecycle.md#interrupted-publication" >&2
    exit "$apply_status"
  fi
  policy_inputs="$repo_root/.terraform/plans/template-policy-inputs.json"
  terraform -chdir="$terraform_dir" output -json > "$policy_inputs"
  if ! ansible-playbook -i localhost, -c local "$repo_root/ansible/playbooks/maintenance/template-policy.yml" \
    --extra-vars "@$policy_inputs" --extra-vars template_policy_apply=true; then
    echo "Terraform publication completed, but template policy verification failed. Keep the existing state." >&2
    echo "Resolve the reported problem, then rerun plan/apply; do not replace disks to clear account or memory settings." >&2
    exit 1
  fi
  terraform -chdir="$terraform_dir" apply -refresh-only -auto-approve -input=false \
    -lock-timeout=60s "${var_args[@]}"
  echo "Template settings verified: ballooning disabled; CloudInit accounts cleared; media and networking preserved."
fi
