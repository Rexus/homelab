# Recover one failed VM

Recover a VM's recorded identity and data from an accepted backup. Creating a fresh VM from
a template is suitable only when the service is deliberately rebuildable and its data is protected elsewhere.

**Run on:** an accepted Proxmox host and the owning tier's original checkout on the bootstrap.
**Prerequisites:** the failed VM is fenced, a known-good [backup set](../backups/recovery-set.md)
is readable, and the backup's consistency/data-loss limits are accepted.
If the host itself is lost, start with [host recovery](host.md); if the bootstrap is unavailable,
[recover it](bootstrap.md) before reconciling IaC.

## Steps

1. [Select the recovery point](#1-select-the-recovery-point).
2. [Restore without exposing a duplicate](#2-restore-without-exposing-a-duplicate).
3. [Validate the service and reconcile its owner](#3-validate-the-service-and-reconcile-its-owner).

## 1. Select the recovery point

1. Pause the VM's Terraform, Ansible and delivery writers. Preserve failed disks and relevant logs
   before attempting repairs or overwriting anything. A repairable guest need not be restored.
2. Record the original VMID, owner/setup/environment, IPs, disks and last successful application backup.
   Choose a compatible VM/application recovery set; an older copy loses changes made after that point.
3. Confirm the destination has capacity, required bridges/VNets and storage access. Check separately
   backed-up databases, PVCs and file/object areas; they are not implied by the VM archive.

## 2. Restore without exposing a duplicate

1. Follow [list backups and restore](../backups/virtual-machines.md#restore-a-test-vm).
   Leave the restored VM stopped; choose the destination as follows:

   | Situation | Restore destination |
   | --- | --- |
   | Isolated acceptance test or original VMID still exists | Unused recovery VMID; retain the original guest and state |
   | Original VMID is free and the original VM cannot return | Original VMID on the accepted replacement host, with the recorded disk/network mapping |
   | VMID is still reserved on a failed cluster node | Stop: resolve that node/guest record through [host recovery](host.md); never overwrite another VM |

2. Disconnect production NICs or select the isolated recovery network before first boot.
   A copied IP/MAC, directory authority, timer or runner must not run alongside its original.
3. Start from the console. Verify all required disks/mounts, original credentials and expected data.
   Use [product recovery](README.md#service-data-and-identities) for application-native restore or consistency checks.
   An etcd snapshot does not restore Kubernetes persistent-volume data.

## 3. Validate the service and reconcile its owner

1. Verify service content at the selected backup time, dependent identity/TLS access, audit delivery
   and outward integrations while still isolated. Record actual data loss and restore duration.
2. Select the cutover identity. A test VM with a different VMID is not automatically the IaC resource.
   If keeping a new VMID, update the owning tier's VM definition and reconcile that **one** resource's
   state/import before any apply. Do not discard the other resources in that deployment's state.
3. Preserve the original state and inspect the restored VM's node/ID using
   [state inspection and reconciliation](../terraform-state.md#restored-resources).
   With the same VMID, provider lookup must find the restored guest; stop on a proposed creation,
   destruction, disk replacement or unexplained change. A changed placement input is not a migration command.
4. Fence the old identity, approve production network attachment, verify the replacement SSH host key
   through the console and cut over one service at a time. Restore API/SSO routes only after their checks pass.
5. Take a new accepted backup, record the restored identity/state mapping and resume the single authorized writer.

**Stop/rollback:** leave a failed replacement isolated. Retain the old disks, original state and
known-good backup; diagnose or retry on another clean target. Do not run the installer to conceal
missing data or initialize a new CA, Vault or Kubernetes identity during a restore.
