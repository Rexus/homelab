# Recover original IaC state and etcd

Recover the original tier-owned inputs and state before planning infrastructure changes. Restore
Kubernetes state only after identifying whether quorum can be repaired and preserving incident data.
**Prerequisites:** [verified extraction](files.md), matching code/tool/provider/image artifacts,
independent network/storage access, original Terraform state and environment context, original Talos
machine configuration/secrets, talosconfig/kubeconfig, and a verified etcd snapshot with recorded hash.
The [input custody procedure](input-custody.md) owns transport from actual provisioning hosts into
independent backup; paths in this guide refer to that verified extracted set.

<a id="contents"></a>

## Operator tasks

- [How to recover original Terraform inputs and state?](#recover-original-state)
- [How to capture and retain an etcd recovery point?](#capture-an-etcd-recovery-point)
- [How to restore a clean Talos control plane?](#restore-a-clean-talos-control-plane)
- [References](#references)

<a id="recover-original-state"></a>

## How to recover original Terraform inputs and state?

1. Fence old automation and preserve its state/backend locks and logs. Clone the original pinned
   code into a new recovery checkout; restore **only** the approved tier/environment/deployment's
   ignored inputs from extraction. Shared owns execution helpers, never another tier's state.
2. Review state lineage/serial, backend configuration, workspace/environment, inventory/IP maps,
   local tfvars, cluster secrets/configuration, SOPS keys and exact state path. Existing local state
   lives under `.terraform/state/<setup>/<env>/terraform.tfstate`; recover the original whole state
   rather than importing known resource IDs into an empty state or regenerating secrets.
3. Use exclusive no-overwrite copy for a recovered local-state file. The destination must be the
   original tier/setup/environment path in a **new** checkout, never a live working directory:

   Run on **the independent isolated recovery workstation**.

   ```bash
   set -euo pipefail
   umask 077
   read -r -p "Verified extracted terraform.tfstate: " RECOVERED_STATE
   read -r -p "Original relative state destination in the NEW checkout: " RECOVERY_STATE_TARGET
   read -r -p "Approve that exact destination path: " RECOVERY_APPROVE_STATE_COPY
   test "${RECOVERY_APPROVE_STATE_COPY:-}" = "$RECOVERY_STATE_TARGET"
   python3 - "$RECOVERED_STATE" "$RECOVERY_STATE_TARGET" <<'PY'
   import json, pathlib, sys
   source, target = map(pathlib.Path, sys.argv[1:])
   state = json.loads(source.read_bytes())
   assert state['lineage'] and isinstance(state['serial'], int) and state['resources']
   assert target.parent.is_dir() and target.parent.resolve() == target.parent.absolute()
   with target.open('xb') as stream:
       stream.write(source.read_bytes())
   PY
   ```

   Existing parents must be prepared privately after path review. An empty resources array requires
   investigation, not bypassing the guard. For remote backends, restore through that backend's
   supported version/snapshot mechanism; do not push local state over a live backend automatically.
4. Reestablish the **original** backend/root configuration through its existing workflow.
   Then inspect on the recovery host, keeping sensitive state output private:

   Run on **the independent isolated recovery workstation**.

   ```bash
   read -r -p "Original initialized Terraform root in the recovery checkout: " RECOVERY_TERRAFORM_ROOT
   terraform -chdir="$RECOVERY_TERRAFORM_ROOT" state list
   ```

5. Restore the resources whose original identities must survive before approving a state refresh
   that would forget them. A normal plan can propose creation while a VM still awaits restore;
   committing refresh-only at that point can remove its binding. Confirm endpoint/token visibility
   and review through [state reconciliation](../terraform-state.md#restored-resources).
   Stop on unexplained creation/replacement/destruction; do not apply merely to test recovery. The
   [cluster workflow](../../03-deployment/stage-4-kubernetes/procedures/talos-terraform.md)
   owns its original state/input contract. Fresh creation is not recovery.

<a id="capture-an-etcd-recovery-point"></a>

## How to capture and retain an etcd recovery point?

On an independent workstation with original scoped Talos credentials and a healthy control plane:

Run on **the independent isolated recovery workstation**.

```bash
set -euo pipefail
umask 077
read -r -p "Original independently held talosconfig: " TALOSCONFIG
read -r -p "Approved healthy control-plane node: " ETCD_NODE
read -r -p "NEW private absolute etcd snapshot directory: " ETCD_SET
mkdir -m 0700 "$ETCD_SET"
talosctl --talosconfig "$TALOSCONFIG" -n "$ETCD_NODE" etcd snapshot "$ETCD_SET/etcd.snapshot"
sha256sum "$ETCD_SET/etcd.snapshot" > "$ETCD_SET/etcd.snapshot.sha256"
```

1. Copy the set and original machine configuration/secrets outside the cluster under independent encryption.
2. For scheduled restic transport, stage it on an **actual input custodian** within a marked read-only
   export, and add its ignored directory to `control_backup_inputs`. An arbitrary recovery-host
   directory is not an accepted input source; see [input custody](input-custody.md).
3. Qualify the capture schedule separately. **No supplied job schedules etcd API calls.** The copy timer
   only transports already captured sets; monitor snapshot age independently.

Etcd contains Kubernetes objects/Secrets, **not PVC data**. [1]

<a id="restore-a-clean-talos-control-plane"></a>

## How to restore a clean Talos control plane?

1. If any control plane survives, inspect it with original scoped credentials selected for this
   restore. A snapshot-capture session is not a prerequisite. If none survives, continue at Step 2
   without these probes:

   Run on **the independent isolated recovery workstation**.

   ```bash
   read -r -e -p "Original independently held talosconfig: " TALOSCONFIG
   read -r -p "Surviving control-plane node to inspect: " ETCD_NODE
   talosctl --talosconfig "$TALOSCONFIG" -n "$ETCD_NODE" etcd members
   talosctl --talosconfig "$TALOSCONFIG" -n "$ETCD_NODE" service etcd
   ```

2. Prefer repairing recoverable quorum. Full recovery requires fencing old control planes and blocking old
API/automation/client routes. Preserve surviving disks before any reset; this recipe intentionally
does not issue `reset` or erase a live node. [1]

3. Prepare new replacement control planes on empty disks using the **original** machine secret material,
cluster settings and approved node addresses. Keep external controllers paused. Verify every target
has machine type `controlplane` and etcd state `Preparing` using release-matched `talosctl`. The
following native sequence was checked against the official Talos recovery guide; use its version
selector for the actual deployed release before execution. [1]

Run on **the independent isolated recovery workstation**.

```bash
set -euo pipefail
read -r -e -p "Original independently held talosconfig: " TALOSCONFIG
read -r -p "Isolated clean control-plane node selected for recovery: " RECOVERY_BOOTSTRAP_NODE
read -r -e -p "Verified extracted native etcd snapshot: " RECOVERED_ETCD_SNAPSHOT
read -r -p "Independently recorded snapshot SHA-256: " EXPECTED_ETCD_SHA256
read -r -p "Target isolation verified (yes): " RECOVERY_ISOLATED
test "${RECOVERY_ISOLATED:-}" = yes
printf '%s  %s\n' "$EXPECTED_ETCD_SHA256" "$RECOVERED_ETCD_SNAPSHOT" | sha256sum -c -
talosctl --talosconfig "$TALOSCONFIG" -n "$RECOVERY_BOOTSTRAP_NODE" get machinetype
talosctl --talosconfig "$TALOSCONFIG" -n "$RECOVERY_BOOTSTRAP_NODE" service etcd
```

Inspect **every** intended replacement control plane: machine type must be `controlplane`, etcd
must be `Preparing`, and its selected disks must be empty. Do not infer other nodes from this one
response. Keep old control planes fenced. After that review, run on **the same recovery workstation**:

```bash
read -r -p "All intended targets independently checked empty and Preparing (yes): " RECOVERY_ALL_TARGETS_EMPTY_AND_PREPARING
read -r -p "Approve recovery bootstrap of the exact selected node: " RECOVERY_APPROVE_ETCD_BOOTSTRAP
test "${RECOVERY_ISOLATED:-}" = yes
test "${RECOVERY_APPROVE_ETCD_BOOTSTRAP:-}" = "$RECOVERY_BOOTSTRAP_NODE"
test "${RECOVERY_ALL_TARGETS_EMPTY_AND_PREPARING:-}" = yes
talosctl --talosconfig "$TALOSCONFIG" -n "$RECOVERY_BOOTSTRAP_NODE" \
  bootstrap --recover-from="$RECOVERED_ETCD_SNAPSHOT"
```

The last acknowledgement follows inspection of **all** targets; it cannot be inferred from one API
response. Never run plain `bootstrap` on this recovery path or skip snapshot hash validation.
Check restored revision, membership, API TLS, node readiness and expected objects/Secrets. Reconcile
controllers before allowing them to write to external systems. Restore product volumes/databases
through [their procedures](README.md), verify storage attachments and take a new independent etcd
snapshot. Record actual RPO/RTO; a working API does not imply recovered application data.

**Stop/rollback:** preserve all original state, locks, snapshots and node disks. On failed lineage/hash,
quorum or empty-target checks, keep automation fenced and diagnose. A failed etcd bootstrap is not
permission to reset retained nodes or bootstrap again without the recorded snapshot. Use another
reviewed clean replacement target; no destructive reset or automated rollback is supplied.

## References

1. [Talos native etcd snapshot and disaster recovery](https://docs.siderolabs.com/talos/v1.11/build-and-extend-talos/cluster-operations-and-maintenance/disaster-recovery.md)
