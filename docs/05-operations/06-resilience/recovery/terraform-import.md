# Rebind a Linux VM after a full clone or restore

Bind a validated replacement VMID to the existing logical Terraform resource address.
Use this after a full clone or an accepted restore, with the old VM fenced and all writers paused.
The replacement must belong to this deployment alone.

Run in **Bash on the Linux execution host, from the owning tier's original checkout**.
Keep the same shell throughout. The copyable path selects the original **local `prod` state,
Terraform `default` workspace, and inputs with `--env` omitted**. For a custom backend, workspace,
environment or input overrides, retain the exact original context throughout, including the final
plan. Explicit `--env prod` can add overlays even though it shares the `prod` state key.
See [state context](../../01-hosting/terraform-state.md#inspect-the-original-state) and
[input precedence](../../../08-reference/platform-inputs.md#loading-and-overrides).

This procedure follows the [Linux deployment wrapper](../../../../shared/scripts/deploy.sh)
and [VM resource](../../../../tier-0/terraform/modules/vm/main.tf).
Templates, LXC and Kubernetes use their own state/input contracts.

## Steps

1. [Select and back up the original state](#1-select-and-back-up-the-original-state).
2. [Record the replacement VMID](#2-record-the-replacement-vmid).
3. [Match credentials and inputs](#3-match-credentials-and-inputs).
4. [Replace the exact binding](#4-replace-the-exact-binding).
5. [Review the plan and return to cutover](#5-review-the-plan-and-return-to-cutover).

## 1. Select and back up the original state

Use the setup and group-vars filename recorded by the original deployment. For example,
Tier 0 `syslog` uses `syslog.yml` for `log-1`. Tier 2 `cache` uses `cache.yml` for `cache-1`.
The wrapper converts setup-name dashes to underscores for the group-vars filename.
Enter the actual Shared checkout used by this tier, such as `../<prefix>-shared`.

Run from **the owning `<prefix>-tier-N/` root on Linux**.

```bash
set -euo pipefail
umask 077
read -r -p 'Original setup (e.g. syslog or cache): ' IAC_SETUP
read -r -p 'Setup group-vars filename (e.g. syslog.yml or cache.yml): ' IAC_GROUP_VARS
read -r -p 'Shared repository path used by this tier: ' IAC_SHARED
IAC_SHARED="$(realpath -- "$IAC_SHARED")"
test -f "$IAC_SHARED/scripts/deploy.sh" || exit 1
grep -Fxq -- "$IAC_SETUP" .deployment-setups || exit 1
test -f "$PWD/ansible/group_vars/$IAC_GROUP_VARS" || exit 1
IAC_ROOT="$PWD/terraform/deployments/$IAC_SETUP"
IAC_STATE="$PWD/.terraform/state/$IAC_SETUP/prod/terraform.tfstate"
export TF_DATA_DIR="$PWD/.terraform/data/$IAC_SETUP/prod"
test -s "$IAC_STATE" || { echo 'Recover the original state before continuing.' >&2; exit 1; }
terraform -chdir="$IAC_ROOT" init -input=false -lockfile=readonly -reconfigure \
  -backend-config="path=$IAC_STATE"
test "$(terraform -chdir="$IAC_ROOT" workspace show)" = default || exit 1
IAC_ARCHIVE="$PWD/.local-archive/$IAC_SETUP-prod-$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$IAC_ARCHIVE" || exit 1
mkdir -p "$IAC_ARCHIVE"
terraform -chdir="$IAC_ROOT" state pull > "$IAC_ARCHIVE/before.tfstate"
test -s "$IAC_ARCHIVE/before.tfstate" || exit 1
terraform -chdir="$IAC_ROOT" state list
```

Stop on a missing state, initialization error or unexpected workspace. Providers must be available
from the approved source/mirror. State contains secrets, so retain the private archive and independent backup.
Preserve all unrelated bindings and the complete state. Reserve `state mv` for logical-address changes.

Select the exact existing **leaf resource address** from that listing. Examples are
`module.vms["log-1"].proxmox_virtual_environment_vm.this` and
`module.vms["cache-1"].proxmox_virtual_environment_vm.this`.

Run from **the same owning tier root**.

```bash
read -r -p 'Exact existing VM resource address from state list: ' IAC_ADDRESS
terraform -chdir="$IAC_ROOT" state show "$IAC_ADDRESS"
```

Record the displayed old `id`, `vm_id`, `node_name`, disks and NIC/MAC. Compare them with the
original guest and the independently validated replacement before proceeding.

<a id="1-record-the-new-identity-in-the-owning-inputs"></a>

## 2. Record the replacement VMID

Edit **the owning tier's `terraform/deployments/<setup>/terraform.tfvars`**, using the selected
deployment's `variables.tf` as its schema. Change only that guest's `vm_instances` entry's `vm_id`
to the accepted replacement VMID. Retain its logical host key, disks, storage, network and addresses.
For renumbering, preserve the original NIC/MAC through the [full-clone procedure](../../01-hosting/change-vmid.md).

If a restore deliberately changed storage or networking, reconcile those accepted differences
in the owning inputs before import. The original Ansible inventory and setup group vars own host/IP
mapping. Keep the clone source/template settings tied to their original approved template.

<a id="2-prepare-the-same-credentials-and-inputs-as-the-wrapper"></a>

## 3. Match credentials and inputs

Native Terraform commands require exported credentials. `.env.local` is loaded by the wrapper
in its own process. Retain an existing approved environment that provides matching `TF_VAR_proxmox_api_*`
and `PROXMOX_API_*` values, or enter the original values below with the secret hidden.
Use the Proxmox web/API root, such as `https://pve.example.com:8006/`.
The selected identity must already have the required access to the replacement VMID;
an ACL scoped only to the old ID does not follow a clone.

Run from **the same owning tier root**, when credentials need to be exported.

```bash
read -r -p 'Verified Proxmox API URL: ' PROXMOX_API_URL
read -r -p 'Scoped API token ID: ' PROXMOX_API_TOKEN_ID
read -r -s -p 'API token secret: ' PROXMOX_API_TOKEN_SECRET
printf '\n'
export PROXMOX_API_URL PROXMOX_API_TOKEN_ID PROXMOX_API_TOKEN_SECRET
export TF_VAR_proxmox_api_url="$PROXMOX_API_URL"
export TF_VAR_proxmox_api_token_id="$PROXMOX_API_TOKEN_ID"
export TF_VAR_proxmox_api_token_secret="$PROXMOX_API_TOKEN_SECRET"
```

Retain `TF_VAR_ssh_public_key_files` and every other original environment override.
For SDN lookup, align endpoint/token aliases with the
[provider environment contract](../../../08-reference/environment-variables.md#when-to-use-environment-variables).

Build the wrapper's base input layers in order. Its Shared platform/catalog and tier common files
are loaded when present, followed by deployment inputs, inventory and `all.yml` plus the actual setup vars.
For an original deployment with overlays or custom flags, reproduce its exact layers and order
from [the wrapper](../../../../shared/scripts/deploy.sh) before continuing.

Run from **the same owning tier root**, for default production with `--env` omitted.

```bash
IAC_VARS=()
for IAC_FILE in \
  "$IAC_SHARED/config/platform.tfvars" \
  "$IAC_SHARED/templates/proxmox-catalog.tfvars" \
  "$PWD/terraform/common.tfvars"
do
  if [[ -f "$IAC_FILE" ]]; then
    IAC_VARS+=("-var-file=$IAC_FILE")
  fi
done
IAC_VARS+=(
  "-var-file=$IAC_ROOT/terraform.tfvars"
  "-var=ansible_inventory_path=$PWD/ansible/inventory/hosts.yml"
  "-var=ansible_group_vars_paths=[\"$PWD/ansible/group_vars/all.yml\",\"$PWD/ansible/group_vars/$IAC_GROUP_VARS\"]"
)
```

<a id="3-rebind-only-the-restored-vm"></a>

## 4. Replace the exact binding

Enter the accepted replacement's actual **node/VMID**, such as `pve01/501`, after confirming it
matches the edited input and the guest validated in the calling procedure. Preview the removal. [1][2]

Run from **the same owning tier root**.

```bash
read -r -p 'Replacement import ID, node/VMID: ' IAC_IMPORT_ID
[[ "$IAC_IMPORT_ID" =~ ^[A-Za-z0-9_.-]+/[0-9]+$ ]] || exit 1
terraform -chdir="$IAC_ROOT" state rm -dry-run "$IAC_ADDRESS"
```

Require exactly the reviewed old VM binding. The next block removes that binding immediately
and imports the replacement at the **same address**. The private pre-change state is in `IAC_ARCHIVE`. [1][2]

Run from **the same owning tier root**, after reviewing the dry run and replacement identity.

```bash
terraform -chdir="$IAC_ROOT" state rm -lock-timeout=60s "$IAC_ADDRESS"
if ! terraform -chdir="$IAC_ROOT" import -input=false -lock-timeout=60s \
  "${IAC_VARS[@]}" "$IAC_ADDRESS" "$IAC_IMPORT_ID"; then
  printf '%s\n' 'Import failed. Keep writers paused and stop before plan or apply.' >&2
  exit 1
fi
terraform -chdir="$IAC_ROOT" state show "$IAC_ADDRESS"
```

On import failure, correct the context and complete import at that same address before proceeding.
Keep the original backup and writers paused. After success, verify the replacement `id`, `vm_id`,
node, disks and original NIC/MAC against the accepted guest.

## 5. Review the plan and return to cutover

Use the original wrapper inputs and matching credentials. The default production command below
uses `.env.local`; retain the original `--env-file` or injected environment when different.

Run from **the same owning tier root**, for default production with `--env` omitted.

```bash
bash scripts/deploy.sh "$IAC_SETUP" --plan-only --env-file .env.local
```

Require no unexpected creation, destruction, disk replacement, NIC/MAC, address or credential changes.
Resolve mismatches before any apply and replace saved plans created before the rebind.
Back up the accepted binding and review the deployment's resource list.

Run from **the same owning tier root**, after the plan review passes.

```bash
terraform -chdir="$IAC_ROOT" state pull > "$IAC_ARCHIVE/after.tfstate"
test -s "$IAC_ARCHIVE/after.tfstate" || exit 1
terraform -chdir="$IAC_ROOT" state list
```

- For a full clone, return to [update jobs and records](../../01-hosting/change-vmid.md#9-update-jobs-and-records).
- For a restore, return to [review the original owner's plan and cutover](virtual-machines.md#9-review-the-original-owners-plan).

Keep the old guest fenced and retain its disks/state archive until the calling procedure accepts
cutover and authorizes the single writer to resume.

## References

1. [Terraform state removal and exact resource addressing](https://developer.hashicorp.com/terraform/cli/commands/state/rm).
2. [Pinned VM import identifier](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/resources/virtual_environment_vm.md#import).
