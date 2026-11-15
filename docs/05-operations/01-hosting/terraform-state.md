# Inspect and reconcile Terraform state

State belongs to the deployment's owning repository and records resource identity. Keep the
original state during recovery; deliberately forgetting an object does not delete or restore it.

**Work from:** the original owning repository root on the bootstrap or accepted recovery host.
**Before starting:** pause other writers and retain the [independent recovery set](../06-resilience/backups/recovery-set.md).
Select the actual deployment and its original backend, state and workspace. These tasks apply to any
deployment; repository ownership does not change the native state commands.
Kit `--env` and Terraform workspaces are different selections.

**Choose one task below; these sections are alternatives, not successive steps.**
For a VMID change with an existing clone, follow [VM state rebinding](../06-resilience/recovery/terraform-import.md)
through its final plan review. Inspection/backup alone does not adopt the clone.

## Choose the task

| Question | Procedure |
| --- | --- |
| A full clone replaces an existing VM under another ID? | [VM adoption: back up, rebind and verify](../06-resilience/recovery/terraform-import.md) |
| Which state/root belongs to this deployment? | [Inspect the original state](#inspect-the-original-state) |
| A host-side deletion is intentional; how is its binding removed? | [Forget one deleted resource](#forget-a-deleted-resource) |
| All objects in one deployment are retired? | [Archive that deployment](#archive-a-retired-deployment) |
| A VM was restored from backup? | [Reconcile restored resources](#restored-resources) |
| The state itself was lost? | [Recover the original state](../06-resilience/recovery/original-state-etcd.md#recover-original-state) |

<a id="inspect-the-original-state"></a>

## How is the original state inspected?

### 1. Open the maintenance shell

Run this command **alone from the owning repository root** and wait for `state-maintenance>`:

```bash
PS1='state-maintenance> ' bash --noprofile --norc -euo pipefail
```

`PS1` only labels the command prompt; it does not configure the host or Terraform.
Keep the selected state task inside this child shell. A failed check returns to the normal
SSH prompt with the connection open; stop and restart the task after correcting it.
When finished, type `exit` only at `state-maintenance>` to return to the parent shell.

### 2. Identify the original context

Use the original deployment record or wrapper to identify all three paths. Kit defaults are relative
to **whichever repository owns the deployment**, not to the upstream checkout or Shared:

| Deployment | Terraform root | State file | `TF_DATA_DIR` |
| --- | --- | --- | --- |
| VM/container setup | `terraform/deployments/<setup>` | `.terraform/state/<setup>/<environment>/terraform.tfstate` | `.terraform/data/<setup>/<environment>` |
| Kubernetes | `terraform/deployments/kubernetes` | `.terraform/state/talos/terraform.tfstate` | `.terraform/data/talos` |
| Template publication | `terraform/deployments/templates` | `.terraform/state/proxmox-templates/terraform.tfstate` | `.terraform/data/proxmox-templates` |

`<setup>` is the original setup name; `<environment>` is its original environment (`prod` when
`deploy.sh` ran without `--env`). Other roots and custom paths use their own recorded locations.
Templates can override the state path through `TEMPLATE_STATE_PATH`.
Check the owning wrapper before accepting any default. Do not invent a new state because the old one is missing.

For example, an `infrastructure-runner` deployment run from **`homelab-tier-0/`** without `--env`
has the following answers. This is one example; use the setup/environment that owns the selected object.

| Prompt in Step 3 | Example answer | Where to find it |
| --- | --- | --- |
| `Original Terraform root directory:` | `terraform/deployments/infrastructure-runner` | Existing folder under this repository's `terraform/deployments/`; its name is the original setup |
| `Original local state file:` | `.terraform/state/infrastructure-runner/prod/terraform.tfstate` | Existing file under `.terraform/state/`, using the recorded setup/environment |
| `Original TF_DATA_DIR directory:` | `.terraform/data/infrastructure-runner/prod` | Same setup/environment under `.terraform/data/`; working files, separate from the state |

Type only the answer after each prompt, then press Enter. Do not type `<setup>` literally.
If the paths do not exist or the original run used another backend/workspace, recover that context first.

### 3. Select and initialize the existing local state

For the recorded **local backend and Terraform `default` workspace**, enter the three paths from
Step 2. Relative paths start at the current repository root; absolute paths are also accepted.
This block inspects state without querying or changing the deployed resources.

Run from **the owning repository root, at `state-maintenance>`**:

```bash
read -r -p 'Original Terraform root directory: ' IAC_ROOT
IAC_ROOT="$(realpath -e -- "$IAC_ROOT")"
test -d "$IAC_ROOT" || { printf '%s\n' 'The Terraform root must be an existing directory.' >&2; exit 1; }
read -r -p 'Original local state file: ' IAC_STATE
test -f "$IAC_STATE" && test -s "$IAC_STATE" || {
  printf 'State missing or empty: %s\nRecover the original state before continuing.\n' "$IAC_STATE" >&2
  exit 1
}
IAC_STATE="$(realpath -e -- "$IAC_STATE")"
read -r -p 'Original TF_DATA_DIR directory: ' IAC_DATA
test ! -e "$IAC_DATA" || test -d "$IAC_DATA" || {
  printf 'Working-data path is not a directory: %s\n' "$IAC_DATA" >&2
  exit 1
}
TF_DATA_DIR="$(realpath -m -- "$IAC_DATA")"
export TF_DATA_DIR
terraform -chdir="$IAC_ROOT" init -input=false -lockfile=readonly -reconfigure \
  -backend-config="path=$IAC_STATE"
test "$(terraform -chdir="$IAC_ROOT" workspace show)" = default || {
  printf '%s\n' 'Unexpected workspace; stop and use the recorded original context.' >&2
  exit 1
}
terraform -chdir="$IAC_ROOT" state list
```

Example final output:

```text
module.vms["iac-1"].proxmox_virtual_environment_vm.this
```

This **resource address** is the whole line, including brackets and quotes. It identifies the object
under the logical key `iac-1`; it is neither its VMID nor a filename. Keep it for the selected task.

Stop on initialization/workspace errors. Providers must be available from the approved source/mirror.
Initialization can rebuild missing working-data files; the original infrastructure state must already exist.
For a **remote backend or non-default workspace**, retain its recorded initialization, working-data
directory and workspace instead of the local block above. Do not pass a local `path` override or
switch to `default`. Set `IAC_ROOT` and `TF_DATA_DIR` to that original context, then continue with
the same state listing, private backup and exact-address tasks. [4][5]

### 4. Back up the selected state

State can contain secrets. Save a private pre-change copy and retain the independent backup too.

Run from **the same owning repository root, in the prepared maintenance shell**:

```bash
umask 077
mkdir -p "$PWD/.local-archive"
IAC_ARCHIVE="$(mktemp -d "$PWD/.local-archive/$(basename -- "$IAC_ROOT")-state-$(date -u +%Y%m%dT%H%M%SZ).XXXXXX")"
terraform -chdir="$IAC_ROOT" state pull > "$IAC_ARCHIVE/before.tfstate"
test -s "$IAC_ARCHIVE/before.tfstate" || { printf '%s\n' 'State backup is empty; stop here.' >&2; exit 1; }
printf 'Private state archive: %s\n' "$IAC_ARCHIVE"
```

State listing/pulling needs the backend, not a Proxmox API plan. Native commands do not load
`.env.local`; wrappers load it in their own process. Keep this context for the selected task below.

**After inspection/backup, return to the task that requested it.** For a cloned replacement, continue
with [VM state rebinding](../06-resilience/recovery/terraform-import.md) from Step 1 to prepare its complete
import context. Do not continue into the deleted-resource task or apply a VMID change before adoption.

<a id="forget-a-deleted-resource"></a>

## How is a manually deleted resource forgotten?

Use this only after independent host-side confirmation that the object is gone and its removal
is intended. For a VM awaiting restoration, retain its binding and use [recovery](../06-resilience/recovery/virtual-machines.md).
For an existing clone under a new VMID, use [VM adoption](../06-resilience/recovery/terraform-import.md)
instead: its old-binding removal must be followed by import of the validated replacement before any plan/apply.

1. Prepare the original state context and backup above. Select an **exact leaf resource address**
   from `state list`, not an entire module or a whole-state pattern.
2. Preview the selected binding:

   Run from **the owning repository root, in the prepared state-maintenance shell**.

   ```bash
   read -r -p 'Exact leaf resource address from state list: ' IAC_ADDRESS
   terraform -chdir="$IAC_ROOT" state list | grep -Fx -- "$IAC_ADDRESS" >/dev/null || {
     printf '%s\n' 'Copy one exact resource line from state list; do not select a whole module.' >&2
     exit 1
   }
   terraform -chdir="$IAC_ROOT" state show "$IAC_ADDRESS"
   terraform -chdir="$IAC_ROOT" state rm -dry-run "$IAC_ADDRESS"
   ```

   Example answer: `module.vms["iac-1"].proxmox_virtual_environment_vm.this`.
   Copy the selected object's whole line from the earlier listing. Expected preview:
   `Would remove module.vms["iac-1"].proxmox_virtual_environment_vm.this`.

3. Require exactly the intended match. The following command changes state immediately; it has
   no separate approval prompt and does not remove any host-side disk or VM. [1]

   Run only after reviewing the exact binding and confirming host-side deletion.

   ```bash
   terraform -chdir="$IAC_ROOT" state rm -lock-timeout=60s "$IAC_ADDRESS"
   terraform -chdir="$IAC_ROOT" state list
   ```

4. If retiring permanently, remove that resource from the owning definitions, inventory,
   IP map and service configuration. If intentionally recreating it, retain those inputs and
   explicitly accept the resulting creation plan. Never treat creation as recovery of its old data.
5. Review a new plan using the **original deployment's entry point and inputs**, retaining its backend,
   state, environment, workspace, credentials and overrides. VM/container setups use
   `scripts/deploy.sh <setup> --plan-only` with their original flags; Kubernetes uses
   `scripts/kubernetes-cluster.sh plan`; template publication uses
   `scripts/proxmox-templates.sh plan`. For other roots, use their owning guide's plan command.

A normal plan observes remote changes; it does not by itself commit a refresh-only state update.
`apply -refresh-only` can reconcile observations but evaluates the **whole selected deployment**.
It needs matching credentials/inputs and must not commit apparent deletions while VMs await restoration. [2]

<a id="archive-a-retired-deployment"></a>

## How is a completely retired deployment reset?

1. Confirm every managed object in that **one state** is removed, not merely powered off or absent
   because of a wrong API endpoint/permission. Preserve the recorded state and independent backup.
2. Review `state list` in the prepared context. For a **local backend in the default workspace**, archive
   only the selected state file. Enter its verified absolute path, matching the context initialized above.

   Run from **the same owning repository root**, using `IAC_STATE` and `IAC_ARCHIVE` from above.

   ```bash
   test -s "$IAC_ARCHIVE/before.tfstate" || exit 1
   printf 'Selected state file: %s\n' "$IAC_STATE"
   read -r -p 'Verified absolute state-file path to archive: ' IAC_CONFIRM_STATE
   test "$IAC_CONFIRM_STATE" = "$IAC_STATE" || exit 1
   test "$(terraform -chdir="$IAC_ROOT" workspace show)" = default || exit 1
   test -f "$IAC_STATE" && test ! -e "$IAC_ARCHIVE/terraform.tfstate" || exit 1
   mv -- "$IAC_STATE" "$IAC_ARCHIVE/terraform.tfstate"
   ```

   At the prompt, copy the **full absolute path** printed by `Selected state file:`, for example
   `/home/operator/src/homelab-iac/homelab-tier-0/.terraform/state/infrastructure-runner/prod/terraform.tfstate`.
   Do not enter the archive directory or another setup's state.

3. Quarantine associated saved plans, exported plan JSON and retry receipts for this deployment,
   including matching `.context`/`.applied.context` files under `.terraform/plans/`. Never apply them
   after retirement; native state edits do not invalidate those files automatically.
4. Keep other setups/environments' state intact. Retain lockfiles, input records, approved images
   and the offline provider mirror. A fresh installation uses a new collection; it is not this recovery path.

Do not move the whole tier's `.terraform/` unless **every** deployment it contains is retired.
Keep any adjacent state backup/lock files in the recovery record; no other state directory is moved.
The working-data directory can remain: retain its downloaded providers/modules for later initialization.
Remote backends and non-default workspaces retain their own retirement process; do not use the local
archive block for them. Archiving local files does not reset remote state.

<a id="restored-resources"></a>

## How is a restored VM reconciled with IaC?

| Restored identity | Action before apply |
| --- | --- |
| Same VMID, original state retained | Inspect the guest and review a plan using original inputs; the pinned provider can discover the VMID on another node [3] |
| Different VMID | Update the intended VM inputs and explicitly rebind only that resource through [VM adoption](../06-resilience/recovery/terraform-import.md) |
| Original state missing/stale | Restore the latest accepted coherent state through [original-state recovery](../06-resilience/recovery/original-state-etcd.md#recover-original-state) |
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
4. [Terraform backend initialization and reconfiguration](https://developer.hashicorp.com/terraform/cli/commands/init#backend-initialization).
5. [Local backend state paths and non-default workspaces](https://developer.hashicorp.com/terraform/language/backend/local).
