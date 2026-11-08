# Adopt a restored Linux VM with a different VMID

Bind an accepted restored VM to its existing logical resource address. Preserve the whole
original state and replace only the reviewed VM binding; this does not restore guest data.

**Work from:** the owning tier's original checkout on the protected bootstrap.
**Scope:** native Linux VM modules; the example is Tier 2 `cache-1`, default `prod`, Terraform `default` workspace.
**Before starting:** complete [isolated VM validation](virtual-machines.md), fence the old identity,
pause writers and prepare the [original state context and backup](../terraform-state.md#inspect-the-original-state).
Templates and Kubernetes have different inputs/state contracts; do not use this recipe for them.

## Steps

1. [Record the new identity](#1-record-the-new-identity-in-the-owning-inputs).
2. [Prepare credentials and matching inputs](#2-prepare-the-same-credentials-and-inputs-as-the-wrapper).
3. [Rebind only the restored VM](#3-rebind-only-the-restored-vm).

## 1. Record the new identity in the owning inputs

Edit these files, retaining the original logical `cache-1` key:

```text
# Edit in <prefix>-tier-2/
terraform/deployments/cache/terraform.tfvars # Set cache-1's restored VMID and actual disk/storage choices.
ansible/group_vars/cache.yml                # Retain or deliberately change its accepted IP/host mapping.
terraform/common.tfvars                    # Update tier-local network references only if the target changed.
# Edit in <prefix>-shared/ only if common placement/storage references changed.
config/platform.tfvars
```

The destination VM must not already be owned by another Terraform state. Preserve the old VM's
records/disks separately until cutover is accepted. A new VMID is not discovered as the old resource automatically.

## 2. Prepare the same credentials and inputs as the wrapper

Native `terraform import` does not load `.env.local`. If an approved credential environment already
provides the matching `TF_VAR_proxmox_api_*` and `PROXMOX_API_*` values, retain it. Otherwise enter
the accepted values without putting the token secret in command history:

```bash
# Run from the owning tier root in the prepared state-maintenance shell.
read -r -p 'Verified Proxmox API URL: ' PROXMOX_API_URL
read -r -p 'Scoped API token ID: ' PROXMOX_API_TOKEN_ID
read -r -s -p 'API token secret: ' PROXMOX_API_TOKEN_SECRET
printf '\n'
export PROXMOX_API_URL PROXMOX_API_TOKEN_ID PROXMOX_API_TOKEN_SECRET
export TF_VAR_proxmox_api_url="$PROXMOX_API_URL"
export TF_VAR_proxmox_api_token_id="$PROXMOX_API_TOKEN_ID"
export TF_VAR_proxmox_api_token_secret="$PROXMOX_API_TOKEN_SECRET"
```

Also retain required `TF_VAR_ssh_public_key_files` and other original environment overrides.
For SDN, clear conflicting endpoint/token aliases through the
[provider environment contract](../../reference/environment-variables.md); lookup and provider must target the same cluster.

Use the prepared `IAC_ROOT`, `TF_DATA_DIR` and private `IAC_ARCHIVE` from the state guide.
This input array matches the default production cache wrapper:

```bash
# Run from <prefix>-tier-2/ in the prepared state-maintenance shell.
IAC_VARS=(
  "-var-file=$PWD/../<prefix>-shared/config/platform.tfvars"
  "-var-file=$PWD/../<prefix>-shared/templates/proxmox-catalog.tfvars"
  "-var-file=$PWD/terraform/common.tfvars"
  "-var-file=$IAC_ROOT/terraform.tfvars"
  '-var=ansible_inventory_path=../../../ansible/inventory/hosts.yml'
  '-var=ansible_group_vars_paths=["../../../ansible/group_vars/all.yml","../../../ansible/group_vars/cache.yml"]'
)
```

For a different setup or environment, preserve the wrapper's exact layer order and original
overrides. Explicit `--env prod` can select overlays even though omitted `--env` also uses the
`prod` state key. See [input precedence](../../reference/platform-inputs.md); do not silently drop overlays.

## 3. Rebind only the restored VM

1. Inspect `state list` and select its exact leaf address. Record both the old and restored node/VMID.

   ```bash
   # Run from <prefix>-tier-2/ in the prepared state-maintenance shell.
   read -r -p 'Exact existing address (e.g. module.vms["cache-1"].proxmox_virtual_environment_vm.this): ' IAC_ADDRESS
   read -r -p 'Restored VM import ID, node/VMID (e.g. pve02/2313): ' IAC_IMPORT_ID
   [[ "$IAC_IMPORT_ID" =~ ^[A-Za-z0-9_.-]+/[0-9]+$ ]] || exit 1
   terraform -chdir="$IAC_ROOT" state rm -dry-run "$IAC_ADDRESS"
   ```

2. Require exactly the intended old binding and the independently verified restored guest.
   Remove that binding, then import the restored VM at the **same address**. [1][2]

   ```bash
   # Execute only after reviewing the exact old binding and restored guest identity.
   terraform -chdir="$IAC_ROOT" state rm -lock-timeout=60s "$IAC_ADDRESS"
   terraform -chdir="$IAC_ROOT" import -input=false -lock-timeout=60s \
     "${IAC_VARS[@]}" "$IAC_ADDRESS" "$IAC_IMPORT_ID"
   ```

   If import fails, keep writers paused and correct the import context; do not run apply into the
   now-unbound address. Keep the original state backup and all unrelated resource bindings intact.
3. Review the normal plan with the owning wrapper, including the same original input overrides:

   ```bash
   # Run from <prefix>-tier-2/ for the default production cache example.
   bash scripts/deploy.sh cache --plan-only --env-file .env.local
   ```

   Require no unexpected create/destroy, disk replacement or credential/network changes.
   Do not apply merely to resolve a mismatch between a restored guest and starter settings.
4. Complete [VM cutover](virtual-machines.md#3-validate-the-service-and-reconcile-its-owner),
   back up the reconciled state and retire the old identity under the accepted retention policy.

## References

1. [Terraform state removal and exact resource addressing](https://developer.hashicorp.com/terraform/cli/commands/state/rm).
2. [Pinned VM import identifier](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/resources/virtual_environment_vm.md#import).
