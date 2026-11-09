# Recover one failed VM

Recover a VM's recorded identity and data from an accepted backup. Creating a fresh VM from
a template is suitable only when the service is deliberately rebuildable and its data is protected elsewhere.

**Run on:** an accepted Proxmox host and the owning tier's original checkout on the bootstrap.
**Prerequisites:** the failed VM is fenced, a known-good [backup set](../backups/recovery-set.md)
is readable, and the backup's consistency/data-loss limits are accepted.
If the host itself is lost, start with [host recovery](host.md); if the bootstrap is unavailable,
[recover it](bootstrap.md) before reconciling IaC.

## Steps

1. [Pause writers](#1-pause-writers).
2. [Select the recovery point](#2-select-the-recovery-point).
3. [Check the destination](#3-check-the-destination).
4. [Restore the stopped VM](#4-restore-the-stopped-vm).
5. [Isolate its network](#5-isolate-its-network).
6. [Boot and check service data](#6-boot-and-check-service-data).
7. [Verify service integrations](#7-verify-service-integrations).
8. [Select the cutover identity](#8-select-the-cutover-identity).
9. [Review the original owner's plan](#9-review-the-original-owners-plan).
10. [Approve and perform cutover](#10-approve-and-perform-cutover).
11. [Back up and resume one writer](#11-back-up-and-resume-one-writer).

<a id="1-select-the-recovery-point"></a>

## 1. Pause writers

On **the owning tier's execution host**, pause the VM's Terraform, Ansible and delivery writers.
Preserve failed disks and relevant logs before repairs or overwriting anything.
A repairable guest need not be restored.

## 2. Select the recovery point

Record the original VMID, owner/setup/environment, IPs, disks and last successful application backup.
Choose a compatible VM/application recovery set. Changes after that recovery point will be lost.

## 3. Check the destination

On **the replacement Proxmox host**, confirm capacity, required bridges/VNets and storage access.
Check separately backed-up databases, PVCs and file/object areas; they are not implied by the VM archive.

<a id="2-restore-without-exposing-a-duplicate"></a>

## 4. Restore the stopped VM

Choose the destination, then follow [list backups and restore](../backups/virtual-machines.md#restore-a-test-vm).

| Situation | Restore destination |
| --- | --- |
| Isolated acceptance test or original VMID still exists | Unused recovery VMID; retain the original guest and state |
| Original VMID is free and the original VM cannot return | Original VMID on the accepted replacement host, with the recorded disk/network mapping |
| VMID is still reserved on a failed cluster node | Stop: resolve that node/guest record through [host recovery](host.md); never overwrite another VM |

Leave the restored VM **stopped**. Return here at Step 5 before its first boot.

## 5. Isolate its network

In **Proxmox > restored VM > Hardware**, disconnect production NICs or select the isolated recovery network.
A copied IP/MAC, directory authority, timer or runner must not run alongside its original.

## 6. Boot and check service data

Start from **the VM console**. Verify required disks/mounts, original credentials and expected data.
Follow [product recovery](README.md#service-data-and-identities) for native restore or consistency checks.
An etcd snapshot does not restore Kubernetes persistent-volume data.

<a id="3-validate-the-service-and-reconcile-its-owner"></a>

## 7. Verify service integrations

While still isolated, check service content at the selected backup time, dependent identity/TLS access,
audit delivery and outward integrations. Record actual data loss and restore duration.
Continue only after those checks pass.

## 8. Select the cutover identity

| Choice | Action |
| --- | --- |
| Keep the original VMID | Retain its resource binding; continue to Step 9 |
| Keep a new VMID | Update the owning tier's VM definition and [rebind that one resource](terraform-import.md) before any apply; then continue to Step 9 |

A test VM is not automatically the IaC resource. Keep all other resources in that deployment's state.

## 9. Review the original owner's plan

On **the owning tier's bootstrap checkout**, preserve the original state and inspect the restored node/ID
using [state inspection and reconciliation](../terraform-state.md#restored-resources).
With the same VMID, provider lookup must find the restored guest. Stop on a proposed creation,
destruction, disk replacement or unexplained change. A changed placement input is not a migration command.

## 10. Approve and perform cutover

Keep the old identity fenced. Approve production network attachment, verify the replacement SSH host key
through the console and cut over one service at a time. Restore API/SSO routes only after their checks pass.

## 11. Back up and resume one writer

Take a new accepted backup and record the restored identity/state mapping.
Resume only the single authorized writer for that state.

**Stop/rollback:** leave a failed replacement isolated. Retain the old disks, original state and
known-good backup; diagnose or retry on another clean target. Do not run the installer to conceal
missing data or initialize a new CA, Vault or Kubernetes identity during a restore.
