# Inspect and reconcile Terraform state

State belongs to the deployment's tier repository and records resource identity. Keep the
original state during recovery; deliberately forgetting an object does not delete or restore it.

**Work from:** the original owning tier on the bootstrap or accepted recovery host.
**Before starting:** pause other writers and retain the [independent recovery set](backups/recovery-set.md).
The examples below select **Tier 2 cache, default `prod` environment and Terraform `default` workspace**.
Use the recorded original context for other deployments; kit `--env` is not a Terraform workspace.

## Choose the task

| Question | Procedure |
| --- | --- |
| Which state/root belongs to this deployment? | [Inspect the original state](#inspect-the-original-state) |
| A host-side deletion is intentional; how is its binding removed? | [Forget one deleted resource](#forget-a-deleted-resource) |
| All objects in one deployment are retired? | [Archive that deployment](#archive-a-retired-deployment) |
| A VM was restored from backup? | [Reconcile restored resources](#restored-resources) |
| The state itself was lost? | [Recover the original state](recovery/original-state-etcd.md#recover-original-state) |

<a id="inspect-the-original-state"></a>

## How is the original state inspected?

Default local paths, relative to the owning tier:

| Deployment | Terraform root | State file | `TF_DATA_DIR` |
| --- | --- | --- | --- |
| Linux setup | `terraform/deployments/<setup>` | `.terraform/state/<setup>/<env>/terraform.tfstate` | `.terraform/data/<setup>/<env>` |
| Kubernetes | `terraform/deployments/kubernetes` | `.terraform/state/talos/terraform.tfstate` | `.terraform/data/talos` |
| Tier 0 templates | `terraform/deployments/templates` | `.terraform/state/proxmox-templates/terraform.tfstate` | `.terraform/data/proxmox-templates` |

1. Compare the original state/backend, environment and workspace with the project record. Templates
   can use `TEMPLATE_STATE_PATH`; remote/custom backends require their own recorded recovery process.
   Do not substitute these local defaults for a different authoritative backend.
2. Initialize **against the existing file**, then inspect it. This block does not query or change VMs:

   ```bash
   # Run from <prefix>-tier-2/ for the existing default production cache state.
   set -euo pipefail
   IAC_ROOT="$PWD/terraform/deployments/cache"
   IAC_STATE="$PWD/.terraform/state/cache/prod/terraform.tfstate"
   export TF_DATA_DIR="$PWD/.terraform/data/cache/prod"
   test -s "$IAC_STATE" || { echo 'Recover the original state before continuing.' >&2; exit 1; }
   terraform -chdir="$IAC_ROOT" init -input=false -lockfile=readonly -reconfigure \
     -backend-config="path=$IAC_STATE"
   test "$(terraform -chdir="$IAC_ROOT" workspace show)" = default || exit 1
   terraform -chdir="$IAC_ROOT" state list
   ```

   Stop on initialization/workspace errors. Do not switch workspaces or initialize an empty state
   to make a missing original disappear. Providers must be available from the approved source/mirror.
3. Save a private pre-change copy; state can contain secrets. Keep the independent backup too:

   ```bash
   # Run from the same owning tier root, with IAC_ROOT and TF_DATA_DIR from above.
   umask 077
   IAC_ARCHIVE="$PWD/.local-archive/cache-prod-$(date -u +%Y%m%dT%H%M%SZ)"
   test ! -e "$IAC_ARCHIVE" || exit 1
   mkdir -p "$IAC_ARCHIVE"
   terraform -chdir="$IAC_ROOT" state pull > "$IAC_ARCHIVE/before.tfstate"
   test -s "$IAC_ARCHIVE/before.tfstate" || exit 1
   ```

Use a unique archive label for a different setup/environment. State listing/pulling needs the
backend, not a Proxmox API plan. Native commands do not load `.env.local`; wrappers load it in their own process.

<a id="forget-a-deleted-resource"></a>

## How is a manually deleted resource forgotten?

Use this only after independent host-side confirmation that the object is gone and its removal
is intended. For a VM awaiting restoration, retain its binding and use [recovery](recovery/virtual-machines.md).

1. Prepare the original state context and backup above. Select an **exact leaf resource address**
   from `state list`, not an entire module or a whole-state pattern.
2. Preview the selected binding:

   ```bash
   # Run from the owning tier root, in the prepared state-maintenance shell.
   read -r -p 'Exact resource address (e.g. module.vms["cache-1"].proxmox_virtual_environment_vm.this): ' IAC_ADDRESS
   terraform -chdir="$IAC_ROOT" state rm -dry-run "$IAC_ADDRESS"
   ```

3. Require exactly the intended match. The following command changes state immediately; it has
   no separate approval prompt and does not remove any host-side disk or VM. [1]

   ```bash
   # Run only after reviewing the exact binding and confirming host-side deletion.
   terraform -chdir="$IAC_ROOT" state rm -lock-timeout=60s "$IAC_ADDRESS"
   terraform -chdir="$IAC_ROOT" state list
   ```

4. If retiring permanently, remove that guest from the tier-owned resource definitions, inventory,
   IP map and service configuration. If intentionally recreating it, retain those inputs and
   explicitly accept the resulting creation plan. Never treat creation as recovery of its old data.
5. Review a new plan through the normal owning wrapper with the original input overrides:

   Run from `<prefix>-tier-2/` for the default production cache example.

   ```bash
   bash scripts/deploy.sh cache --plan-only --env-file .env.local
   ```

A normal plan observes remote changes; it does not by itself commit a refresh-only state update.
`apply -refresh-only` can reconcile observations but evaluates the **whole selected deployment**.
It needs matching credentials/inputs and must not commit apparent deletions while VMs await restoration. [2]

<a id="archive-a-retired-deployment"></a>

## How is a completely retired deployment reset?

1. Confirm every managed object in that **one state** is removed, not merely powered off or absent
   because of a wrong API endpoint/permission. Preserve the recorded state and independent backup.
2. Review `state list` in the prepared context. For the cache/prod example, archive only its directories:

   ```bash
   # Run from <prefix>-tier-2/, using the prepared cache/prod state context and IAC_ARCHIVE.
   test -f .deployment-setups && test -s "$IAC_ARCHIVE/before.tfstate" || exit 1
   test "$IAC_ROOT" = "$PWD/terraform/deployments/cache" || exit 1
   test "$TF_DATA_DIR" = "$PWD/.terraform/data/cache/prod" || exit 1
   test ! -e "$IAC_ARCHIVE/state" && test ! -e "$IAC_ARCHIVE/data" || exit 1
   mv -- "$PWD/.terraform/state/cache/prod" "$IAC_ARCHIVE/state"
   mv -- "$TF_DATA_DIR" "$IAC_ARCHIVE/data"
   unset TF_DATA_DIR
   ```

3. Quarantine associated saved plans, exported plan JSON and retry receipts for this deployment,
   including matching `.context`/`.applied.context` files under `.terraform/plans/`. Never apply them
   after retirement; native state edits do not invalidate those files automatically.
4. Keep other setups/environments' state intact. Retain lockfiles, input records, approved images
   and the offline provider mirror. A fresh installation uses a new collection; it is not this recovery path.

Do not move the whole tier's `.terraform/` unless **every** deployment it contains is retired.
Archiving a directory does not reset a remote backend or external state path.

<a id="restored-resources"></a>

## How is a restored VM reconciled with IaC?

| Restored identity | Action before apply |
| --- | --- |
| Same VMID, original state retained | Inspect the guest and review a plan using original inputs; the pinned provider can discover the VMID on another node [3] |
| Different VMID | Update the intended VM inputs and explicitly rebind only that resource through [VM adoption](recovery/terraform-import.md) |
| Original state missing/stale | Restore the latest accepted coherent state through [original-state recovery](recovery/original-state-etcd.md#recover-original-state) |
| Kubernetes node VMs restored | Retain original cluster state/secrets and qualify etcd/PVC recovery separately; VM adoption alone is insufficient |

For the same VMID, keep the resource binding. Linux VM `node_name` is creation-time placement;
changing it is not a migration command. Verify node, disks, inventory and service identity, then
review the complete plan. Stop if the provider cannot find the guest, API visibility is incomplete,
or Terraform proposes an unexpected creation, destruction or disk replacement.

Restore all objects intended to retain their identity **before** approving a state refresh that
would forget them. Resume one writer only after the recovery checks pass, then back up the new state.

## References

1. [Terraform state removal](https://developer.hashicorp.com/terraform/cli/commands/state/rm).
2. [Terraform normal and refresh-only planning](https://developer.hashicorp.com/terraform/cli/commands/plan#refresh-only-mode).
3. [Pinned Proxmox provider VM discovery](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/proxmoxtf/resource/vm/vm.go).
