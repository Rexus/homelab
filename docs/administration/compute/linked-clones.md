# Remove a linked clone's template dependency

A linked clone reads unchanged blocks from its original template base disk.
Replacing the template's boot disk affects future clones; it does not update
existing guests or move them to the new base. An old base shown as **Unused Disk N**
can therefore still be required by running VMs. [1]

**Execution:** Proxmox VE GUI; optional read-only checks on the storage-owning host.
**IaC ownership:** inventory, VM definitions and state remain in the VM's Tier 0, 1 or 2 repository.
**Why:** [provisioning ownership](../../architecture/hosting/provisioning.md) and
[image promotion](../../architecture/software/artifact-supply.md) separate new image selection from existing guests.

<a id="contents"></a>

## Find the task

- [Keep current data or deploy a new OS?](#choose-the-outcome)
- [Create an independent VM with a new VMID?](#option-a-full-clone-to-a-new-vmid)
- [Keep the existing VMID?](#option-b-keep-the-vmid-and-copy-its-disks)
- [Check whether a ZFS base is still required?](#verify-zfs-dependencies)
- [Delete an old base safely?](#release-the-old-base)
- [References](#references)

## Choose the outcome

| Outcome | Path |
| --- | --- |
| Keep the current OS, applications and data; change VMID | Full clone the existing VM using Option A |
| Keep the current VMID and contents; another VM datastore is available | Copy the linked disks using Option B |
| Deploy the new template's OS image | Provision a new VM from that template and migrate application data/configuration |

Do not repoint an existing clone at a different OS image by editing its backing
reference. Independent copies preserve the VM's current contents; guest updates
or replacement deployments provide the OS upgrade.

Before either copy path, take an [independent backup](backup-restore.md), check
destination capacity and arrange downtime. For IaC-managed guests, plan any
VMID/storage changes in the owning repository before execution. A GUI copy does
not automatically update inventory or Terraform state.

## Option A: Full clone to a new VMID

This needs no second datastore and produces an independent VM. [1]

1. Shut down the **existing linked-clone VM**. Select that VM, not the template.
2. Open **Clone**, select **Full Clone**, an unused VMID and qualified destination
   storage. Wait for the task to finish.
3. Keep the original off. Test the copy on an isolated network first; its copied
   guest settings can include the same IP, hostname and application identity.
   Qualify boot, networking, guest control and application data before cutover.
4. Record the new VMID and reconcile its owning IaC inputs/state before the next
   deployment. Then retire the original VM and its linked disks when recovery
   copies are accepted. Merely shutting down the original leaves its dependency.

A full clone copies current guest contents, not the source VM's complete snapshot
history. Retain any required recovery history independently. [1]

## Option B: Keep the VMID and copy its disks

Proxmox's storage-move operation makes a full disk copy and updates the existing
VM's attachment. Use another eligible datastore; a raw ZFS disk cannot be moved
to the same storage in the same format. [2]

1. Shut down the VM. In **Hardware**, record each linked disk's current volume ID.
   Review snapshots too: the move copies current contents, and old snapshots can
   retain references to the source volumes.
2. Select a linked disk, then **Disk Action > Move Storage**. Choose another
   datastore enabled for VM disks and leave **Delete source** unchecked. [3]
3. Wait for success and verify the active attachment uses the destination volume.
   Repeat for every linked disk that must become independent, including EFI disks
   where applicable. Boot and test the VM before cleanup.
4. Reconcile storage inputs in the owning repository and review its Terraform plan.
   After testing, remove only the VM's recorded unused source disks when snapshots
   no longer require them. Those retained copies still depend on the old base.
5. If required, move the independent disks back to the original datastore using
   the same procedure. Validate and clean up the intermediate copies separately.

Storage moves do not migrate the VM's snapshot history. Keep the old base while
retained snapshots or unused source disks still reference it. [2]

<a id="verify-zfs-dependencies"></a>

## How are ZFS dependencies checked?

On the Proxmox host holding the local ZFS storage, inspect dataset origins:

```bash
# Run on the selected Proxmox host as an authorized root operator.
zfs list -t filesystem,volume -o name,origin
```

An `ORIGIN` ending in `base-9101-disk-1@__base__`, for example, identifies a dependency
on that base snapshot. A clone created after a switch to `base-9101-disk-2` uses that
new base instead. `ORIGIN` of `-` means the dataset is not a ZFS clone. Inspect
retained unused volumes as well as currently attached disks. Other storage types
require their own dependency checks. [4]

<a id="release-the-old-base"></a>

## When can the old base be removed?

Keep the old base until all dependent disks are removed or independently copied,
including retained originals and snapshots. Then follow the template's
[old-disk cleanup steps](template-disk.md#retire-the-old-disk).
With no dependents, keeping that disk is an optional rollback decision, not a
required history mechanism. The maintenance receipt records volume identities;
it does not contain the disk data.

The repository's ordinary Linux VM Terraform modules already request full clones;
see the owning tier's `terraform/modules/vm/main.tf` (`clone.full = true`).

## References

Sources checked 2026-11-07.

1. [Proxmox full and linked clone semantics](https://raw.githubusercontent.com/proxmox/pve-docs/master/qm.adoc).
2. [Proxmox storage moves, full-copy mode and snapshot handling](https://raw.githubusercontent.com/proxmox/qemu-server/master/src/PVE/API2/Qemu.pm).
3. [Proxmox disk move dialog and retained-source option](https://raw.githubusercontent.com/proxmox/pve-manager/master/www/manager6/qemu/HDMove.js).
4. [OpenZFS origin and clone properties](https://openzfs.github.io/openzfs-docs/man/master/7/zfsprops.7.html).
