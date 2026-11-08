# Recover guests after a Proxmox host fails

Recover the affected guests onto surviving or replacement capacity. Without commissioned HA,
this is a manual outage recovery: VM backups supply the data, not automatic restart or zero data loss.

**Run on:** an independent Proxmox console/workstation, then the recovered bootstrap.
**Prerequisites:** the failed host is powered off/fenced, backups and keys are independently readable,
and the accepted [backup policy](../backups/virtual-machines.md#backup-policy) defines the possible data loss.
**Design:** [hosting boundaries](../../architecture/hosting/runtime.md) and
[backup independence](../../architecture/operations/backup-recovery.md).

## Steps

1. [Fence the failure and select the path](#1-fence-the-failure-and-select-the-path).
2. [Prepare accepted replacement capacity](#2-prepare-accepted-replacement-capacity).
3. [Recover guests and resume operations](#3-recover-guests-and-resume-operations).

## 1. Fence the failure and select the path

1. Keep the old host unable to boot its original guests or write shared disks. Pause competing recovery
   jobs. Preserve failed media/logs; hardware repair must not start a second copy of the recovered service.
2. Record affected VMIDs, disk locations, network attachments and owners from the retained platform record.
3. Choose the path:

   | Surviving environment | Action |
   | --- | --- |
   | Commissioned HA, healthy quorum and accessible storage | Follow [HA recovery checks](../../deployment/foundation/proxmox/failover.md); do not restore duplicate guests while HA is recovering them |
   | No HA; original guest disks survive on accepted shared storage | Assess native guest relocation before a backup restore; shared storage alone does not start a VM |
   | No HA; local disks lost or unsafe to reuse | Restore accepted VM/application backups onto prepared replacement storage |
   | No usable Proxmox host remains | Follow [whole-platform recovery](platform.md) |

For a surviving cluster, inspect `pvecm status` and `ha-manager status` on a healthy node.
Resolve quorum and the failed node's membership/configuration before restoring its VMIDs. Do not
force quorum, copy cluster files wholesale or erase surviving guest records as a generic recovery step.
Use the [native cluster node-removal procedure](https://github.com/proxmox/pve-docs/blob/master/pvecm.adoc#remove-a-cluster-node)
when permanently retiring a fenced node; replacement-node naming and guest records need explicit review. [1]

## 2. Prepare accepted replacement capacity

1. Prepare the replacement with [Proxmox foundation](../../deployment/foundation/proxmox/README.md#first-deployment-order).
   Join an existing cluster while the replacement node is still empty, before restoring guests onto it.
   Recreate required physical bridges/VLANs or apply the selected SDN configuration, then prepare live storage. [1]
2. Reconnect the existing NAS/PBS [backup target](../backups/virtual-machines.md#quick-steps).
   Recover storage access using independent credentials; do not format surviving Ceph/NAS data.
3. Record old-to-new node, datastore and network mappings. Confirm guest capacity and current CPU/device
   compatibility, including any passthrough devices. A backup cannot recreate unavailable physical hardware.
4. If its host was lost, [restore the bootstrap first](bootstrap.md). It needs no cloud-image template
   when a complete VM backup is available. Keep the original state and API trust transition explicit.

## 3. Recover guests and resume operations

1. Select one affected guest and follow [VM recovery](virtual-machines.md).
   Prefer its original VMID only after it is available cluster-wide and the old host is fenced.
2. Restore the remaining guests in [dependency order](../recovery.md#recovery-order), including
   application-native copies where required. Keep replacement identities isolated until accepted.
3. Reconcile each owning tier's original state, actual node/storage mapping and inventory before its
   automation resumes. Review plans; never use a fresh state merely because a host changed.
4. Verify service access, protected logging, expected data and scheduled backups on the replacement.
   Record the backup IDs, measured outage/data loss and the disposition of the failed host/media.

**Expected:** accepted guests run on recorded replacement capacity and have new independent recovery
points. Re-enabling HA or admitting a repaired host is a separate, tested maintenance operation.

## References

1. [Proxmox cluster management and node retirement](https://github.com/proxmox/pve-docs/blob/master/pvecm.adoc).
