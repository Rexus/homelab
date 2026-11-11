# Recover guests after a Proxmox host fails

Recover the affected guests onto surviving or replacement capacity. Without commissioned HA,
this is a manual outage recovery: VM backups supply the data, not automatic restart or zero data loss.

**Run on:** an independent Proxmox console/workstation, then the recovered bootstrap.
**Prerequisites:** the failed host is powered off/fenced, backups and keys are independently readable,
and the accepted [backup policy](../backups/virtual-machines.md#backup-policy) defines the possible data loss.
**Design:** [hosting boundaries](../../../01-architecture/04-hosting/01-runtime.md) and
[backup independence](../../../01-architecture/11-operations/04-backup-recovery.md).

## Steps

1. [Fence the failed host](#1-fence-the-failed-host).
2. [Record the affected guests](#2-record-the-affected-guests).
3. [Check the surviving cluster and select the path](#3-check-the-surviving-cluster-and-select-the-path).
4. [Prepare replacement capacity](#4-prepare-replacement-capacity).
5. [Reconnect the backup target](#5-reconnect-the-backup-target).
6. [Check replacement mappings and capacity](#6-check-replacement-mappings-and-capacity).
7. [Recover bootstrap access](#7-recover-bootstrap-access).
8. [Recover one guest](#8-recover-one-guest).
9. [Restore the remaining guests](#9-restore-the-remaining-guests).
10. [Reconcile each owning tier](#10-reconcile-each-owning-tier).
11. [Verify and record recovery](#11-verify-and-record-recovery).

<a id="1-fence-the-failure-and-select-the-path"></a>

## 1. Fence the failed host

Keep **the failed host** unable to boot its original guests or write shared disks. Pause competing
recovery jobs. Preserve failed media/logs; hardware repair must not start a second copy of a recovered service.

## 2. Record the affected guests

Use the retained platform record to list VMIDs, disk locations, network attachments and owners.

## 3. Check the surviving cluster and select the path

For a surviving cluster, run on **a healthy Proxmox node as an authorized root operator**:

```bash
pvecm status
ha-manager status
```

| Surviving environment | Next action |
| --- | --- |
| Commissioned HA, healthy quorum and accessible storage | Follow [HA recovery checks](../../../03-deployment/foundation/proxmox/failover.md); do not restore duplicate guests while HA is recovering them |
| No HA; original guest disks survive on accepted shared storage | Assess native guest relocation before a backup restore; shared storage alone does not start a VM |
| No HA; local disks lost or unsafe to reuse | Continue to Step 4 for backup restoration |
| No usable Proxmox host remains | Follow [whole-platform recovery](platform.md) instead |

Resolve quorum and the failed node's membership/configuration before restoring its VMIDs. Do not
force quorum, copy cluster files wholesale or erase surviving guest records as a generic recovery step.
Use the [native cluster node-removal procedure](https://github.com/proxmox/pve-docs/blob/master/pvecm.adoc#remove-a-cluster-node)
when permanently retiring a fenced node; replacement-node naming and guest records need explicit review. [1]

<a id="2-prepare-accepted-replacement-capacity"></a>

## 4. Prepare replacement capacity

Follow [Proxmox foundation](../../../03-deployment/foundation/proxmox/README.md#first-deployment-order).
Join an existing cluster while the replacement node is still **empty**, before restoring guests.
Recreate required physical bridges/VLANs or apply selected SDN configuration, then prepare live storage. [1]

## 5. Reconnect the backup target

Reconnect the existing NAS/PBS [backup target](../backups/virtual-machines.md#quick-steps) using
independent credentials. Do not initialize or format surviving Ceph/NAS data.

## 6. Check replacement mappings and capacity

Record old-to-new node, datastore and network mappings. Confirm guest capacity and current CPU/device
compatibility, including passthrough devices. A backup cannot recreate unavailable physical hardware.

## 7. Recover bootstrap access

If its host was lost, [restore the bootstrap first](bootstrap.md), then return here at Step 8.
A complete VM backup needs no cloud-image template. Keep original state and the API trust transition explicit.
If bootstrap survived, use its accepted checkout and continue to Step 8.

<a id="3-recover-guests-and-resume-operations"></a>

## 8. Recover one guest

Follow [VM recovery](virtual-machines.md) for one affected guest.
Prefer its original VMID only after it is available cluster-wide and the old host is fenced.

## 9. Restore the remaining guests

Follow [dependency order](../README.md#recovery-order), including application-native copies where required.
Keep replacement identities isolated until accepted.

## 10. Reconcile each owning tier

On **the recovered bootstrap**, review each owner's original state, actual node/storage mapping,
inventory and plan before its automation resumes. Never use fresh state merely because a host changed.

## 11. Verify and record recovery

Check service access, protected logging, expected data and scheduled backups on the replacement.
Record backup IDs, measured outage/data loss and the disposition of the failed host/media.

**Expected:** accepted guests run on recorded replacement capacity and have new independent recovery
points. Re-enabling HA or admitting a repaired host is a separate, tested maintenance operation.

## References

1. [Proxmox cluster management and node retirement](https://github.com/proxmox/pve-docs/blob/master/pvecm.adoc).
