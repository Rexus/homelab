# Step 3a: Bootstrap workspace disk

**Branch from:** [Step 3](../README.md#step-3-prepare-the-bootstrap-execution-host), option **3a**,
at [bootstrap Step 2, storage A](README.md#a-separate-workspace-filesystem--reference-layout).
**Return:** [Foundation Step 3](../README.md#step-3-prepare-the-bootstrap-execution-host), continuing with
[bootstrap tool acquisition](README.md#2a-install-git-terraform-and-ansible) after mount/reboot checks;
select the offline alternative there if needed.

Prepare the separate local data filesystem used by `boot-1` for repositories, state and artifacts.
This is the [bootstrap storage A](README.md#a-separate-workspace-filesystem--reference-layout) path.
For an expanded LVM root, use [storage B](step-3b-bootstrap-lvm.md) instead.

**Run on `boot-1`**, using its normal SSH account with authorized sudo and independent console access.
**Before starting:** a recoverable VM backup and a new, empty attached data disk with **Backup** enabled.
The examples use `/dev/sdb`; identify the real device before changing it.

## Contents

1. [Install the storage tools](#1-install-the-storage-tools)
2. [Identify the data disk](#2-identify-the-data-disk)
3. [Partition the empty disk](#3-partition-the-empty-disk)
4. [Create its filesystem](#4-create-its-filesystem)
5. [Record the persistent mount](#5-record-the-persistent-mount)
6. [Mount and verify](#6-mount-and-verify)
7. [Verify after reboot](#7-verify-after-reboot)
8. [Create the workspace and continue](#8-create-the-workspace-and-continue)

## 1. Install the storage tools

On **`boot-1`**, use approved repositories. For EL10:

```bash
sudo dnf install -y parted xfsprogs
```

For Debian/Ubuntu, use this block instead; the remaining XFS steps are the same:

```bash
sudo apt-get update
sudo apt-get install -y parted xfsprogs
```

For offline preparation, first select the verified extracted bundle on independently mounted media:

```bash
read -r -p 'Verified extracted bundle directory on mounted media: ' BUNDLE
```

Install its OS packages using [offline Step 7](step-3e-bootstrap-offline.md#7-install-signed-os-packages).
Return here before creating Python environments or copying the full artifact bundle.

## 2. Identify the data disk

On **`boot-1`**:

```bash
lsblk -o NAME,SIZE,FSTYPE,TYPE,UUID,MOUNTPOINTS
findmnt -n -o SOURCE /
```

Identify the newly attached disk by its size and lack of required filesystems/mounts.
**The next two steps erase its partition layout and create a filesystem. Never use the root disk or recovery media.**
If the data filesystem already exists, retain it and continue at **5**, using its actual UUID and filesystem type.
An existing workspace with data requires its own reviewed migration; do not mount over populated directories.

## 3. Partition the empty disk

On **`boot-1`**, only after verifying that `/dev/sdb` is the new, empty disk:

```bash
sudo parted /dev/sdb --script mklabel gpt
sudo parted /dev/sdb --script mkpart primary xfs 1MiB 100%
sudo partprobe /dev/sdb
sudo udevadm settle
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS
```

**Expected:** `/dev/sdb1` exists on the intended data disk.

## 4. Create its filesystem

On **`boot-1`**, format only the verified new partition:

```bash
sudo mkfs.xfs /dev/sdb1
```

**Expected:** XFS creation succeeds. Do not add a force flag to bypass an existing-filesystem warning. [1]

## 5. Record the persistent mount

On **`boot-1`**, create the empty mountpoint and read the data filesystem's UUID:

```bash
sudo install -d -m 0700 /srv/tier0
sudo blkid /dev/sdb1
sudo cp -a /etc/fstab /etc/fstab.before-bootstrap-workspace
```

Edit **`/etc/fstab` on `boot-1`**. Add one entry using the actual UUID from `blkid`:

```fstab
UUID=<data-filesystem-uuid> /srv/tier0 xfs defaults 0 0
```

Use the actual filesystem type if reusing an existing filesystem. Keep all existing root/boot entries
and retain a correct existing workspace entry instead of adding a duplicate.
UUID selection remains stable when device enumeration changes. [2]

## 6. Mount and verify

On **`boot-1`**:

```bash
sudo findmnt --verify
sudo systemctl daemon-reload
mountpoint -q /srv/tier0 || sudo mount /srv/tier0
findmnt -M /srv/tier0
df -h / /srv/tier0
```

**Expected:** `/srv/tier0` uses the intended data filesystem, not `/` as a fallback.
Stop on validation or mount errors; keep the console open and correct the mount entry before continuing.

## 7. Verify after reboot

Reboot **`boot-1`** through its independent console. Reconnect as the normal SSH account and run:

```bash
findmnt -M /srv/tier0
df -h / /srv/tier0
```

**Expected:** the data mount is present without a manual mount command. Do not copy artifacts or state
until this check passes.

## 8. Create the workspace and continue

On **`boot-1`**, as its normal SSH account:

```bash
(
  mountpoint -q /srv/tier0 || { echo 'Data filesystem is not mounted.' >&2; exit 1; }
  sudo install -d -m 0700 -o "$(id -un)" -g "$(id -gn)" \
    /srv/tier0/src /srv/tier0/artifacts /srv/tier0/offline /srv/tier0/tmp/proxmox-upload
)
```

Include both disks in the independent [bootstrap recovery set](../../../05-operations/backups/recovery-set.md).
Optionally [move home directories](step-3c-bootstrap-home.md) before creating Python environments or cloning the kit.
Then return to [Bootstrap 2a](README.md#2a-install-through-approved-sources), or
[2b offline](README.md#2b-transfer-a-prepared-bundle--offline-alternative).

If mount preparation fails, retain both disks and use the console to restore the recorded fstab configuration.
Formatting cannot be undone by removing an fstab entry; recover mistakenly overwritten data from backup.

## References

1. [XFS creation and existing-filesystem protection](https://manpages.debian.org/trixie/xfsprogs/mkfs.xfs.8.en.html), checked 2026-11-09.
2. [fstab UUID entries and systemd reload](https://manpages.debian.org/trixie/mount/fstab.5.en.html), checked 2026-11-09.
