# Handle data disks during a VMID change

Choose this path before [full-clone Step 5](change-vmid.md#5-create-the-full-clone).
The [cutover figure](change-vmid.md#figure-vmid-cutover) shows the normal independent-copy path.
Record each data disk's Proxmox volume ID, controller slot, filesystem UUID and mount path before stopping it.
The commands use `OLD_VMID` for the old VM and `NEW_VMID` for the new VM. Service inputs below use
`<service>` and `<volume>` placeholders; replace them with the actual keys defined by the owning role.

> [!CAUTION]
> A production data disk must remain available to the accepted replacement. Verify its contents and
> independent backup before deleting any old VM or unused volume. Never attach the original and its
> filesystem-identical copy to the same running guest, or let two guests write the same original disk.

## Choose a path

1. [Preserve the copied disks](#1-preserve-the-copied-disks): normal full-clone migration.
2. [Reassign an original data disk](#2-reassign-an-original-data-disk): transfer the existing managed volume.
3. [Recreate disposable data through IaC](#3-recreate-disposable-data-through-iac): accept data loss and start fresh.

## 1. Preserve the copied disks

1. Complete [Step 5's full clone](change-vmid.md#5-create-the-full-clone) with the source stopped.
   Attached Proxmox-managed data disks are copied along with the OS disk; no reattachment is normally needed. [1]
2. Compare both VMs' **Hardware** entries. Retain the controller slots and options expected by Terraform's
   `extra_disks`, including the service disk's `scsi1` where configured. Storage names/volume IDs can change.
3. After [Step 7's boot checks](change-vmid.md#7-start-and-verify-the-replacement), verify each mount's
   original UUID and application data. A copied filesystem retains its UUID; keep its Ansible UUID pin.

| Identity | What to retain or update |
| --- | --- |
| Proxmox volume ID, such as `<datastore>:vm-<new-vmid>-disk-<number>` | Record the new VM's actual volume; Terraform import discovers it |
| Stable guest device, such as `/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1` | Retain the path when its controller slot and exposed device identity stay the same; verify custom serials separately |
| Filesystem UUID, configured as `<service>_<volume>_uuid` | Retain the actual role's pin for the copied or reassigned filesystem |

See the [storage input contract](../../08-reference/platform-inputs.md#vm-disk-storage) for device selection
and per-host UUID pins. Clearing a pin does not reformat the filesystem or generate a new UUID.
Find the actual UUID/device keys through the [storage-input convention](../../02-conventions/iac-inputs.md#storage-identity-inputs)
and the selected service's configuration header or role defaults. Run that service's own volume-adoption checks.

External NFS/SMB mounts, raw devices, PCI/USB passthrough and detached `unusedN` volumes are not covered
by the independent VM-disk copy. Preserve their actual mapping and single-writer ownership before boot;
do not feed them into the managed-volume commands below.

Return to [Step 6](change-vmid.md#6-restore-the-original-nic-settings).

## 2. Reassign an original data disk

Use this only for a **Proxmox-managed data volume on the same host**, after cloning but before the
replacement's first boot. Keep both VMs stopped and all writers paused in the original
`vmid-maintenance>` shell. This transfers ownership of the original volume instead of using its copy.
The storage backend must support reassignment; snapshots or unsupported storage can block it. [2][3]

### 2a. Select and inspect the data disk

On **the source Proxmox host**, with `OLD_VMID`, `NEW_VMID` and `VM_RECORD` from the main guide:

```bash
test "$(qm status "$OLD_VMID")" = 'status: stopped'
test "$(qm status "$NEW_VMID")" = 'status: stopped'
read -r -p 'Data-disk controller slot to transfer (e.g. scsi1): ' DATA_SLOT
[[ "$DATA_SLOT" =~ ^(scsi|sata|virtio)[0-9]+$ ]]
qm config "$OLD_VMID" --current 1
qm config "$NEW_VMID" --current 1
```

Require the selected slot to be the recorded **data disk**, never the OS, EFI or Cloud-Init disk.
Compare volume ID, size and options with the recovery record. The target slot must be empty before reassignment.

### 2b. Detach the replacement's copied data disk, if present

Run this block **only when the replacement has a copied disk in the selected slot**.
Skip it when the slot is already empty. This detaches the copy as an unused volume without deleting it. [2]

On **the same Proxmox host**, after reviewing the replacement's selected data disk:

```bash
test "$(qm status "$OLD_VMID")" = 'status: stopped'
test "$(qm status "$NEW_VMID")" = 'status: stopped'
qm disk unlink "$NEW_VMID" --idlist "$DATA_SLOT"
qm config "$NEW_VMID" --current 1
```

Record the copied volume's new `unusedN` entry. **Do not unlink that `unusedN` entry**: doing so deletes
its volume. Keep it until cutover is accepted; it is not an independent backup. [2]

### 2c. Transfer the original volume to the replacement

On **the same Proxmox host**, with the target data slot now empty:

```bash
test "$(qm status "$OLD_VMID")" = 'status: stopped'
test "$(qm status "$NEW_VMID")" = 'status: stopped'
qm disk move "$OLD_VMID" "$DATA_SLOT" --target-vmid "$NEW_VMID" --target-disk "$DATA_SLOT"
qm config "$OLD_VMID" --current 1 > "$VM_RECORD/source-after-disk-transfer.conf"
qm config "$NEW_VMID" --current 1 > "$VM_RECORD/replacement-after-disk-transfer.conf"
cat "$VM_RECORD/replacement-after-disk-transfer.conf"
```

**Expected:** the disk is no longer attached to the old VM and is attached at the selected target slot.
Proxmox updates volume ownership/name; its filesystem contents and UUID remain intact. Do not manually
rename storage files or point both VMs at the same volume. If the task fails, stop and inspect both
configurations before retrying. [2]

Repeat for each intentionally transferred data disk, keeping both VMs stopped. Then return to
[Step 6](change-vmid.md#6-restore-the-original-nic-settings). Verify the original filesystem UUID,
mount and actual application data in Step 7, then import the replacement before any Terraform apply.
Keep the existing UUID pin and matching `extra_disks` declarations.

### Roll back a reassigned disk

1. Pause writers and stop both VMs. Record the volume's current ownership and any writes since cutover.
2. Require the original VM's target slot to be empty; detach any conflicting copy without deleting it.
3. On **the same Proxmox host**, reverse the ownership transfer:

   ```bash
   test "$(qm status "$OLD_VMID")" = 'status: stopped'
   test "$(qm status "$NEW_VMID")" = 'status: stopped'
   qm disk move "$NEW_VMID" "$DATA_SLOT" --target-vmid "$OLD_VMID" --target-disk "$DATA_SLOT"
   qm config "$OLD_VMID" --current 1
   ```

4. Verify the original disk options/UUID and application consistency, then continue the
   [main rollback procedure](change-vmid.md#roll-back-before-retiring-the-original).
   The detached clone contains only the pre-cutover copy, not writes later made to the transferred disk.

## 3. Recreate disposable data through IaC

This accepts loss of the selected VM's data and creates a **fresh guest and data disk** from its approved
template. A full clone would preserve the old filesystem and its mount declarations instead.

1. In **the owning tier**, pause writers and [back up the original state](terraform-state.md#inspect-the-original-state).
   Keep its existing binding when the old VM still exists. If it was already deleted manually,
   [remove only its confirmed stale binding](terraform-state.md#forget-a-deleted-resource).
2. Before creating or importing a clone, set a free new VMID in
   `terraform/deployments/<setup>/terraform.tfvars`. Keep the logical resource key and approved template,
   `extra_disks` slot/size/storage and the service's matching stable `<service>_<volume>_device` input.
3. In the actual service group-vars or per-host file, set **only that recreated host's** UUID pin to
   an empty string before first preparation: `<service>_<volume>_uuid: ""`.
   Substitute the role's actual public key; do not add a literal placeholder or rename an existing key.
   Preserve other hosts' pins and observe the [extra-vars precedence rules](../../08-reference/platform-inputs.md#vm-disk-storage).
4. Run the owning deployment guide's normal Terraform command with its original inputs. With the old
   binding retained, a changed VMID plans replacement of that VM, including its owned disks. This is
   **intentional destruction of the old guest and data**. Require only the selected replacement;
   reject changes to other resources. If the old binding was removed after confirmed deletion,
   require only the intended creation. Do not use a setup-wide destroy. [5]
5. Continue the owning guide's Ansible steps. The fresh guest's blank data disk is initialized,
   mounted persistently and its verified binding printed. Complete normal enrollment and service checks.
   This fresh-deployment path can assign a new MAC; update DHCP reservations if needed.
6. Save the printed UUID pin in the indicated file, per host. Keep the new recovery record and backup.

**Clearing a UUID pin alone is not a disk reset.** The guarded role refuses a blank replacement when
the existing guest still declares a data mount in `/etc/fstab`; it also rejects wrong UUIDs, foreign
mounts and unexpected data. Restore preserved storage or deliberately rebuild the guest through the
path above rather than bypassing those checks. [4]

## References

1. [Proxmox full-clone semantics](https://github.com/proxmox/pve-docs/blob/master/qm.adoc#copies-and-clones).
2. [Proxmox disk detach/reassignment API and ownership checks](https://github.com/proxmox/qemu-server/blob/master/src/PVE/API2/Qemu.pm).
3. [Native `qm disk move` and `qm disk unlink` command mapping](https://github.com/proxmox/qemu-server/blob/master/src/PVE/CLI/qm.pm).
4. [Guarded existing/blank volume validation](../../../shared/ansible/roles/data_volume/tasks/validate.yml),
   [filesystem preparation and UUID output](../../../shared/ansible/roles/data_volume/tasks/prepare.yml).
5. [Pinned provider VMID replacement rule](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/proxmoxtf/resource/vm/vm.go).
