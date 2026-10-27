# Recover original IaC state and etcd

Recover the original tier-owned inputs and state before planning infrastructure changes. Restore
Kubernetes state only after identifying whether quorum can be repaired and preserving incident data.
**Prerequisites:** [verified extraction](files.md), matching code/tool/provider/image artifacts,
independent network/storage access, original Terraform state and environment context, original Talos
machine configuration/secrets, talosconfig/kubeconfig, and a verified etcd snapshot with recorded hash.
The [input custody procedure](input-custody.md) owns transport from actual provisioning hosts into
independent backup; paths in this guide refer to that verified extracted set.

## Contents

- [Recover original state](#recover-original-state)
- [Capture an etcd recovery point](#capture-an-etcd-recovery-point)
- [Restore a clean Talos control plane](#restore-a-clean-talos-control-plane)
- [References](#references)

## Recover original state

1. Fence old automation and preserve its state/backend locks and logs. Clone the original pinned
   code into a new recovery checkout; restore **only** the approved tier/environment/deployment's
   ignored inputs from extraction. Shared owns execution helpers, never another tier's state.
2. Review state lineage/serial, backend configuration, workspace/environment, inventory/IP maps,
   local tfvars, cluster secrets/configuration, SOPS keys and exact state path. Existing local state
   lives under `.terraform/state/<setup>/<env>/terraform.tfstate`; recover the original whole state
   rather than importing known resource IDs into an empty state or regenerating secrets.
3. Use exclusive no-overwrite copy for a recovered local-state file. The destination must be the
   original tier/setup/environment path in a **new** checkout, never a live working directory:

   ```bash
   set -euo pipefail
   umask 077
   : "${RECOVERED_STATE:?Set the verified extracted terraform.tfstate}"
   : "${RECOVERY_STATE_TARGET:?Set the original relative state path in the new checkout}"
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
4. Inspect through `terraform state list` and `terraform show -json` in the original configured root
   without exposing their sensitive output. Use a reviewed plan/refresh-only plan after restoring
   backend/provider access. Stop on unexplained replacement/destruction. Do not apply merely to test
   recovery. The [Talos workflow](../../deployment/stage-4-kubernetes/procedures/talos-terraform.md)
   owns original root/input contracts; normal fresh-cluster creation is not recovery.

## Capture an etcd recovery point

On an independent workstation with original scoped Talos credentials and a healthy control plane:

```bash
set -euo pipefail
umask 077
: "${TALOSCONFIG:?Set the independent original talosconfig}"
: "${ETCD_NODE:?Set the approved healthy control-plane node}"
: "${ETCD_SET:?Set a NEW private absolute snapshot directory}"
mkdir -m 0700 "$ETCD_SET"
talosctl --talosconfig "$TALOSCONFIG" -n "$ETCD_NODE" etcd snapshot "$ETCD_SET/etcd.snapshot"
sha256sum "$ETCD_SET/etcd.snapshot" > "$ETCD_SET/etcd.snapshot.sha256"
```

Copy this set and original machine configuration/secrets outside the cluster under independent
encryption. To include it in scheduled restic copies, place the complete set in an explicitly selected
ignored input directory on the recovery host. This role does not schedule etcd API calls. Define and
qualify the snapshot schedule separately. Etcd contains Kubernetes objects/Secrets, **not PVC data**. [1]

## Restore a clean Talos control plane

First inspect `talosctl ... etcd members` and `service etcd` across surviving control planes. Prefer
repairing a recoverable quorum. Full recovery requires fencing old control planes and blocking old
API/automation/client routes. Preserve surviving disks before any reset; this recipe intentionally
does not issue `reset` or erase a live node. [1]

Prepare new replacement control planes on empty disks using the **original** machine secret material,
cluster settings and approved node addresses. Keep external controllers paused. Verify every target
has machine type `controlplane` and etcd state `Preparing` using release-matched `talosctl`. The
following native sequence was checked against the official Talos recovery guide; use its version
selector for the actual deployed release before execution. [1]

```bash
set -euo pipefail
: "${RECOVERY_BOOTSTRAP_NODE:?Set one isolated clean control-plane node}"
: "${RECOVERED_ETCD_SNAPSHOT:?Set the verified extracted native snapshot}"
: "${EXPECTED_ETCD_SHA256:?From independent custody}"
: "${TALOSCONFIG:?Set the original independently held talosconfig}"
test "${RECOVERY_ISOLATED:-}" = yes
test "${RECOVERY_APPROVE_ETCD_BOOTSTRAP:-}" = "$RECOVERY_BOOTSTRAP_NODE"
printf '%s  %s\n' "$EXPECTED_ETCD_SHA256" "$RECOVERED_ETCD_SNAPSHOT" | sha256sum -c -
talosctl --talosconfig "$TALOSCONFIG" -n "$RECOVERY_BOOTSTRAP_NODE" get machinetype
talosctl --talosconfig "$TALOSCONFIG" -n "$RECOVERY_BOOTSTRAP_NODE" service etcd
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

## References

1. [Talos native etcd snapshot and disaster recovery](https://docs.siderolabs.com/talos/v1.11/build-and-extend-talos/cluster-operations-and-maintenance/disaster-recovery.md)
