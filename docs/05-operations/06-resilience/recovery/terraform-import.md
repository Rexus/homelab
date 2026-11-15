# Import a replacement Linux VM into Terraform

Bind a validated replacement VMID to the existing logical Terraform resource address.
Use this after a full clone or an accepted restore, with the old VM fenced and all writers paused.
The replacement must belong to this deployment alone.

**Keep this procedure open through Step 12.** A state inspection or input edit alone does not adopt a VM.
If a plan still refreshes the old VMID and shows `vm_id` forcing replacement, decline the apply and
complete Steps 9 and 10: remove the old state binding **and** import the existing replacement.
Neither command deletes a Proxmox VM. Keep the old VM stopped. [1][2]

Run on **the Linux execution host, from the owning tier's original checkout**.
Use the dedicated maintenance shell below throughout. The copyable path selects the original **local `prod` state,
Terraform `default` workspace, and inputs with `--env` omitted**. For a custom backend, workspace,
environment or input overrides, retain the exact original context throughout, including the final
plan. Explicit `--env prod` can add overlays even though it shares the `prod` state key.
See [state context](../../01-hosting/terraform-state.md#inspect-the-original-state) and
[input precedence](../../../08-reference/platform-inputs.md#loading-and-overrides).

This procedure follows the [Linux deployment wrapper](../../../../shared/scripts/deploy.sh)
and [VM resource](../../../../tier-0/terraform/modules/vm/main.tf).
Templates, LXC and Kubernetes use their own state/input contracts.

## What will I enter?

The examples below move **`iac-1` from VMID `611` to `612` on `pve01`**, in a collection
whose prefix is `homelab`. They illustrate the answers; use the actual existing deployment.
Run every command in this guide from **the tier repository that originally created the VM**,
for example **`homelab-tier-0/`**, not Shared or the Proxmox host.

| Asked value | Example answer | Find the actual value |
| --- | --- | --- |
| Deployment setup | `infrastructure-runner` | The first argument in the original `bash scripts/deploy.sh <setup>` command; Step 2 prints this repository's `.deployment-setups` |
| Setup group-vars filename | `infrastructure_runner.yml` | File under `ansible/group_vars/` used by that deployment; press Enter for the displayed default |
| Shared directory | `../homelab-shared` | Sibling checkout used by this tier's `scripts/deploy.sh`; press Enter for the displayed default |
| VM resource address | `module.vms["iac-1"].proxmox_virtual_environment_vm.this` | Copy the **whole line** for the selected VM from Step 3's `terraform state list`; Step 4 verifies it |
| Replacement import ID | `pve01/612` | New VM's **Proxmox node name** and **VMID**, shown in the Proxmox tree/Summary; not its DNS name or IP |

Type answers **at the prompt that ends in `:`**, then press Enter. Do not type the prompt itself,
shell quotes or the variable name. Blocks marked `text` show example output; only `bash` blocks run.
`IAC_*` variables hold the answers for later commands. Keep the same maintenance shell open;
never paste a later command into a new terminal with those variables unset.

## Steps

1. [Open the maintenance shell](#1-open-the-maintenance-shell).
2. [Select the original deployment](#2-select-the-original-deployment).
3. [Initialize and back up the original state](#3-initialize-and-back-up-the-original-state).
4. [Select and inspect the old VM binding](#4-select-and-inspect-the-old-vm-binding).
5. [Edit the replacement VMID](#5-edit-the-replacement-vmid).
6. [Load the deployment's `.env.local`](#6-load-the-deployments-envlocal).
7. [Prepare the Terraform input files](#7-prepare-the-terraform-input-files).
8. [Enter the new identity and preview removal](#8-enter-the-new-identity-and-preview-removal).
9. [Remove the old state binding](#9-remove-the-old-state-binding).
10. [Import the existing replacement](#10-import-the-existing-replacement).
11. [Review a fresh plan](#11-review-a-fresh-plan).
12. [Back up the new binding](#12-back-up-the-new-binding).
13. [Close the maintenance shell and return](#13-close-the-maintenance-shell-and-return).

<a id="1-select-and-back-up-the-original-state"></a>
<a id="1a-open-a-dedicated-maintenance-shell"></a>

## 1. Open the maintenance shell

Run this command **alone from the owning tier root** and wait for the `state-maintenance>` prompt:

```bash
PS1='state-maintenance> ' bash --noprofile --norc -euo pipefail
```

`PS1` only labels the command prompt; it does not configure the host or Terraform.
Strict error handling applies only inside this child shell. A failed check returns to the normal
SSH prompt, leaving the connection open. Stop there and restart at Step 1 after correcting the error;
do not paste later blocks into the parent shell. [3]

<a id="1b-select-the-original-deployment"></a>

## 2. Select the original deployment

Use the setup recorded by the original deployment. Its default group-vars filename replaces setup-name
dashes with underscores. Press Enter to accept a displayed default, or enter the actual original path.
Shared needs a **directory path**, normally `../<prefix>-shared`, rather than just its repository name.
Use the checkout referenced by this tier's `scripts/deploy.sh`; do not create another Shared directory.

Run from **the same owning tier root, at the `state-maintenance>` prompt**:

```bash
umask 077
test -f .deployment-setups || { printf '%s\n' 'Run from the original tier repository root.' >&2; exit 1; }
printf '%s\n' 'Available deployment setups:'
cat .deployment-setups
read -r -p 'Original deployment setup: ' IAC_SETUP
grep -Fxq -- "$IAC_SETUP" .deployment-setups || {
  printf 'Unknown setup: %s. Available setups:\n' "$IAC_SETUP" >&2
  cat .deployment-setups >&2
  exit 1
}
IAC_GROUP_VARS="${IAC_SETUP//-/_}.yml"
read -r -p "Setup group-vars filename [$IAC_GROUP_VARS]: " IAC_GROUP_INPUT
IAC_GROUP_VARS="${IAC_GROUP_INPUT:-$IAC_GROUP_VARS}"
test -f "$PWD/ansible/group_vars/$IAC_GROUP_VARS" || {
  printf 'Missing original group-vars file: %s/ansible/group_vars/%s\n' "$PWD" "$IAC_GROUP_VARS" >&2
  exit 1
}
IAC_TIER_NAME="${PWD##*/}"
IAC_SHARED_DEFAULT='../shared'
case "$IAC_TIER_NAME" in
  *-tier-[012]) IAC_SHARED_DEFAULT="../${IAC_TIER_NAME%-tier-[012]}-shared" ;;
esac
while true; do
  read -r -p "Shared repository directory [$IAC_SHARED_DEFAULT]: " IAC_SHARED
  IAC_SHARED="${IAC_SHARED:-$IAC_SHARED_DEFAULT}"
  if [[ -f "$IAC_SHARED/scripts/deploy.sh" ]]; then
    IAC_SHARED="$(realpath -e -- "$IAC_SHARED")"
    break
  fi
  printf 'Shared checkout not found: %s/scripts/deploy.sh\nEnter its directory path; default: %s\n' \
    "$IAC_SHARED" "$IAC_SHARED_DEFAULT" >&2
done
```

Example terminal answers (the two empty answers accept the defaults):

```text
Original deployment setup: infrastructure-runner
Setup group-vars filename [infrastructure_runner.yml]:
Shared repository directory [../homelab-shared]:
```

This selects `terraform/deployments/infrastructure-runner/terraform.tfvars` and
`ansible/group_vars/infrastructure_runner.yml`. A setup is a deployment name, **not** a VM hostname,
VMID, tier number or environment name. If its owner is unknown, look for the VM's logical key
in the tier's `terraform/deployments/*/terraform.tfvars` before continuing.

**Expected:** a valid original setup, group-vars file and Shared checkout. A mistyped Shared path
prints the expected file and asks again; Terraform has not run yet.

<a id="1c-open-and-back-up-the-existing-state"></a>

## 3. Initialize and back up the original state

Run from **the same owning tier root, at the `state-maintenance>` prompt**:

```bash
IAC_ROOT="$PWD/terraform/deployments/$IAC_SETUP"
IAC_STATE="$PWD/.terraform/state/$IAC_SETUP/prod/terraform.tfstate"
export TF_DATA_DIR="$PWD/.terraform/data/$IAC_SETUP/prod"
test -f "$IAC_ROOT/terraform.tfvars" || {
  printf 'Missing original deployment inputs: %s/terraform.tfvars\n' "$IAC_ROOT" >&2
  exit 1
}
test -s "$IAC_STATE" || {
  printf 'Original state missing or empty: %s\nRecover it before continuing.\n' "$IAC_STATE" >&2
  exit 1
}
terraform -chdir="$IAC_ROOT" init -input=false -lockfile=readonly -reconfigure \
  -backend-config="path=$IAC_STATE"
test "$(terraform -chdir="$IAC_ROOT" workspace show)" = default || {
  printf '%s\n' 'Unexpected workspace; stop and use the recorded original state context.' >&2
  exit 1
}
IAC_ARCHIVE="$PWD/.local-archive/$IAC_SETUP-prod-$(date -u +%Y%m%dT%H%M%SZ)"
test ! -e "$IAC_ARCHIVE" || {
  printf 'Archive already exists: %s\nChoose a new archive before continuing.\n' "$IAC_ARCHIVE" >&2
  exit 1
}
mkdir -p "$IAC_ARCHIVE"
terraform -chdir="$IAC_ROOT" state pull > "$IAC_ARCHIVE/before.tfstate"
test -s "$IAC_ARCHIVE/before.tfstate" || {
  printf 'State backup is empty: %s/before.tfstate\nStop and recover a valid backup.\n' "$IAC_ARCHIVE" >&2
  exit 1
}
printf 'Private state archive: %s\n' "$IAC_ARCHIVE"
terraform -chdir="$IAC_ROOT" state list
```

Example of the VM line to select from the final output:

```text
Private state archive: /home/operator/src/homelab-iac/homelab-tier-0/.local-archive/infrastructure-runner-prod-20261115T120000Z
module.vms["iac-1"].proxmox_virtual_environment_vm.this
```

Other lines may describe other VMs, containers or lookup data. Choose only the VM being replaced;
the key `iac-1` matches its entry in `vm_instances` in the deployment's `terraform.tfvars`.

Stop on a missing state, initialization error or unexpected workspace. Providers must be available
from the approved source/mirror. State contains secrets, so retain the private archive and independent backup.
Preserve all unrelated bindings and the complete state. Reserve `state mv` for logical-address changes.

## 4. Select and inspect the old VM binding

A **resource address** is Terraform's name for one managed object. For example,
`module.vms["iac-1"].proxmox_virtual_environment_vm.this` identifies the VM under the logical key
`iac-1`; it is not its VMID. Copy that entire line from Step 3, including brackets and double quotes.
Do not enter only `iac-1`, `611`, `vm_instances` or `module.vms`.

Run from **the same owning tier root**.

```bash
read -r -p 'Exact existing VM resource address from state list: ' IAC_ADDRESS
[[ "$IAC_ADDRESS" =~ (^|\.)proxmox_virtual_environment_vm\. ]] &&
  terraform -chdir="$IAC_ROOT" state list | grep -Fx -- "$IAC_ADDRESS" >/dev/null || {
    printf '%s\n' 'Copy one exact VM resource line from the state listing, then restart at Step 1.' >&2
    exit 1
  }
terraform -chdir="$IAC_ROOT" state show "$IAC_ADDRESS"
```

Example prompt and relevant parts of its output:

```text
Exact existing VM resource address from state list: module.vms["iac-1"].proxmox_virtual_environment_vm.this
id        = "611"
node_name = "pve01"
vm_id     = 611
```

**Expected:** the old VM's identity, not the replacement yet. Record its displayed disks and NIC/MAC.
Compare them with the original guest and the independently validated replacement before proceeding.

<a id="1-record-the-new-identity-in-the-owning-inputs"></a>
<a id="2-record-the-replacement-vmid"></a>

## 5. Edit the replacement VMID

Edit **the owning tier's `terraform/deployments/<setup>/terraform.tfvars`**, using the selected
deployment's `variables.tf` as its schema. Set that guest's `vm_instances` entry's `vm_id`
to the accepted replacement VMID. In the running example, edit **only `vm_instances["iac-1"].vm_id`
from `611` to `612`**. Keep the key `iac-1`. Do not run the deployment yet.
Retain its logical host key, disks, storage, network and addresses.
For renumbering, preserve the original NIC/MAC through the [full-clone procedure](../../01-hosting/change-vmid.md).

Retain the original template selection for future recreation. Current Linux VM modules preserve the
imported VM's BIOS, machine, SCSI controller, EFI disk and boot order. No per-service `firmware` block
or Shared boot-profile backfill is needed to make an import preserve those settings. Shared's profile
and an optional per-VM override initialize new guests only; see the
[catalog contract](../../../08-reference/template-catalog.md#how-consumers-use-it).

If a restore deliberately changed storage or networking, reconcile those accepted differences
in the owning inputs before import. The original Ansible inventory and setup group vars own host/IP
mapping. Keep the clone source/template settings tied to their original approved template.
For preserved data, retain the matching stable device and filesystem UUID pin; importing a new VMID
does not reattach or reset its disks. Complete the [data-disk cutover](../../01-hosting/vmid-data-disks.md) first.

<a id="2-prepare-the-same-credentials-and-inputs-as-the-wrapper"></a>
<a id="3-match-credentials-and-inputs"></a>

<a id="6-export-the-original-credentials"></a>

## 6. Load the deployment's .env.local

Load **the owning tier's `.env.local`**, the same file used for the original deployment.
The shared parser exports literal values without executing the file as shell code. It also maps
`PROXMOX_API_*` to the Terraform variables, exactly as `deploy.sh` does. No token is requested or printed.
Keep any original `TF_VAR_ssh_public_key_files` and other overrides unchanged.

Run from **the same owning tier root, at `state-maintenance>`**:

```bash
source "$IAC_SHARED/scripts/lib/provider-environment.sh"
env_file_path="$PWD/.env.local"
load_env_file
map_provider_env
check_provider_env
```

**Expected:** `==> Loading environment file .../.env.local`, with no missing-credential error.
If the original run used another `--env-file`, set `env_file_path` to that existing file instead.
For approved runner-injected credentials, set `env_file_path=''` to keep them and run the same calls.
If the library is missing, refresh the generated Shared checkout from the current kit first.

The token must be able to inspect the replacement VMID. An ACL scoped only to the old ID does not
follow a clone. For conflicting endpoint/token aliases, follow the
[provider environment contract](../../../08-reference/environment-variables.md#when-to-use-environment-variables).

<a id="7-prepare-the-original-input-layers"></a>

## 7. Prepare the Terraform input files

Build the wrapper's base input layers in order. Its Shared platform/catalog and tier common files
are loaded when present, followed by deployment inputs, inventory and `all.yml` plus the actual setup vars.
For an original deployment with overlays or custom flags, reproduce its exact layers and order
from [the wrapper](../../../../shared/scripts/deploy.sh) before continuing.

There are no questions in this block. It prepares the same file arguments for the import.
For the example, the last file is `terraform/deployments/infrastructure-runner/terraform.tfvars`.

Run from **the same owning tier root**, for default production with `--env` omitted.

```bash
for IAC_REQUIRED in \
  "$PWD/ansible/inventory/hosts.yml" \
  "$PWD/ansible/group_vars/all.yml" \
  "$PWD/ansible/group_vars/$IAC_GROUP_VARS"
do
  test -s "$IAC_REQUIRED" || {
    printf 'Missing original input: %s\nRecover it before changing state.\n' "$IAC_REQUIRED" >&2
    exit 1
  }
done
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
<a id="4-replace-the-exact-binding"></a>

## 8. Enter the new identity and preview removal

Enter the accepted replacement's actual **node/VMID** after confirming it
matches the edited input and the guest validated in the calling procedure. Preview the removal. [1][2]

Run from **the same owning tier root**.

```bash
read -r -p 'Replacement import ID, node/VMID: ' IAC_IMPORT_ID
[[ "$IAC_IMPORT_ID" =~ ^[A-Za-z0-9_.-]+/[0-9]+$ ]] || {
  printf '%s\n' 'Expected the actual Proxmox node name followed by / and the replacement VMID.' >&2
  exit 1
}
printf '%s\n' "$IAC_ADDRESS" "$IAC_IMPORT_ID" > "$IAC_ARCHIVE/rebinding.txt"
terraform -chdir="$IAC_ROOT" state rm -dry-run "$IAC_ADDRESS"
```

Example answer and preview:

```text
Replacement import ID, node/VMID: pve01/612
Would remove module.vms["iac-1"].proxmox_virtual_environment_vm.this
```

Use the Proxmox node name `pve01`, **not** `pve01.example.com` or the guest hostname `iac-1`.
The new VM's Summary/tree supplies both pieces; its address is also saved in the full-clone record.
**Expected:** the preview names only the old VM's exact resource address. Nothing has been removed yet.
Confirm the new `node/VMID` belongs to the validated replacement, then continue to Step 9.

## 9. Remove the old state binding

This is the removal command. It forgets only the selected binding in Terraform; it does **not** delete
the old VM, the replacement or their disks. There is no further confirmation prompt. [1]

Run from **the same owning tier root, in the same maintenance shell**, after reviewing Step 8:

```bash
test -s "$IAC_ARCHIVE/before.tfstate"
test "${#IAC_VARS[@]}" -gt 0
terraform -chdir="$IAC_ROOT" state rm -lock-timeout=60s "$IAC_ADDRESS"
```

Example output:

```text
Removed module.vms["iac-1"].proxmox_virtual_environment_vm.this
Successfully removed 1 resource instance(s).
```

**Expected:** exactly one resource instance is removed from state. Both VMs still exist.
The resource is temporarily unbound. Continue immediately to Step 10; do not run plan or apply yet.

## 10. Import the existing replacement

This records the already created new VM at the **same logical address**. It does not create another VM. [2][5]

Run from **the same owning tier root, in the same maintenance shell**:

```bash
if ! terraform -chdir="$IAC_ROOT" import -input=false -lock-timeout=60s \
  "${IAC_VARS[@]}" "$IAC_ADDRESS" "$IAC_IMPORT_ID"; then
  printf '%s\n' 'Import failed. Keep writers paused and stop before plan or apply.' >&2
  exit 1
fi
terraform -chdir="$IAC_ROOT" state show "$IAC_ADDRESS"
```

Example output (other attributes are omitted here):

```text
Import successful!
id        = "612"
node_name = "pve01"
vm_id     = 612
```

**Expected:** import succeeds and `state show` reports the replacement's new `id` and `vm_id`.
Verify its node, disks and original NIC/MAC against the accepted guest before Step 11.

If import fails, the maintenance shell stops. Keep writers paused. Repeat Steps 1–3 to reopen
and back up the current state. Skip Step 4's `state show` for the removed binding.
Restore `IAC_ADDRESS` and `IAC_IMPORT_ID` using the two lines saved in the original archive's
`rebinding.txt`, then repeat Steps 6–7 and Step 10. Skip Step 9: the old binding was already removed.
Do not apply while it is unbound.

<a id="5-review-the-plan-and-return-to-cutover"></a>

## 11. Review a fresh plan

Use the original wrapper inputs and matching credentials. The default production command below
uses `.env.local`; retain the original `--env-file` or injected environment when different.

Run from **the same owning tier root**, for default production with `--env` omitted.

```bash
bash scripts/deploy.sh "$IAC_SETUP" --plan-only --env-file .env.local
```

For the running example, this executes `bash scripts/deploy.sh infrastructure-runner --plan-only --env-file .env.local`.
The selected VM should refresh as:

```text
module.vms["iac-1"].proxmox_virtual_environment_vm.this: Refreshing state... [id=612]
No changes. Your infrastructure matches the configuration.
```

Require no unexpected creation, destruction, disk replacement, NIC/MAC, address or credential changes.
Resolve mismatches before any apply and replace saved plans created before the rebind.
**Expected:** refreshing the selected resource now shows the **new VMID**. Stop if it still shows
the old VMID or proposes replacement; adoption is incomplete or the wrong context was selected.

If a new `clone` block forces replacement after a successful import, update the owning
`terraform/modules/vm/main.tf` from the current kit. Its lifecycle treats clone provenance as
creation-only, because Proxmox cannot return that Terraform creation metadata during import.
It also preserves BIOS, machine, SCSI controller, EFI disk, boot order, description, OS hint and serial
ports. If an OVMF-to-SeaBIOS, controller or EFI-removal diff remains, check that the plan uses the current
owning VM module and the correct imported binding; do not change boot settings to satisfy stale code.
Do not repeat state removal/import for a VM already bound to the correct ID. [2][4]

## 12. Back up the new binding

Run from **the same owning tier root**, after the plan review passes.

```bash
terraform -chdir="$IAC_ROOT" state pull > "$IAC_ARCHIVE/after.tfstate"
test -s "$IAC_ARCHIVE/after.tfstate" || exit 1
terraform -chdir="$IAC_ROOT" state list
```

Keep the old guest fenced and retain its disks/state archive until the calling procedure accepts
cutover and authorizes the single writer to resume.

## 13. Close the maintenance shell and return

When the selected operation is complete, run **at the `state-maintenance>` prompt**:

```bash
exit
```

This closes only the maintenance shell and returns to the normal SSH prompt.

- For a full clone, return to [update jobs and records](../../01-hosting/change-vmid.md#9-update-jobs-and-records).
- For a restore, return to [review the original owner's plan and cutover](virtual-machines.md#9-review-the-original-owners-plan).

## References

1. [Terraform state removal and exact resource addressing](https://developer.hashicorp.com/terraform/cli/commands/state/rm).
2. [Pinned VM import identifier](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/resources/virtual_environment_vm.md#import).
3. [Bash invocation: child shells and startup-file options](https://tiswww.case.edu/php/chet/bash/bashref.html#Invoking-Bash).
4. [Terraform creation/update semantics of ignored attributes](https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle#ignore_changes).
5. [Terraform import arguments and variable files](https://developer.hashicorp.com/terraform/cli/commands/import), accessed 2026-11-15.
