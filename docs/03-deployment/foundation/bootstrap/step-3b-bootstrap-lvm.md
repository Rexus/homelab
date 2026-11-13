# Step 3b: Expand the bootstrap root with LVM

**Branch from:** [Step 3](../README.md#step-3-prepare-the-bootstrap-execution-host), option **3b**,
at bootstrap storage 3b. Choose enlargement **A** or new-PV **B** below.
**Return:** [Bootstrap Step 5](README.md#step-5-select-tool-acquisition) after root/workspace checks;
the separate-data mount and home-bind steps do not apply to this layout.

<a id="expand-bootstrap-storage-with-rocky-linux-lvm"></a>

Choose **A** to enlarge the existing disk, or **B** to add a disk to the existing volume group.
Prefer A when only more capacity is needed. Both paths grow root, including `/home` if it shares root.

**Run on `boot-1`**, using the configured SSH account and authorized sudo. Have a current VM backup
and Proxmox console access. This guide requires an ordinary LVM root filesystem; it does not apply to Talos.
Start from [bootstrap storage B](README.md#b-expand-the-existing-rocky-linux-root--lvm-alternative).

## Contents

- [Install tools](#install-tools)
- [A. Enlarge the existing disk](#a-enlarge-the-existing-disk)
- [B. Add a disk to the existing volume group](#b-add-a-disk-to-the-existing-volume-group)
- [Create the workspace and continue](#create-the-workspace-and-continue)
- [References](#references)

<a id="prepare-os-tools"></a>

## Install tools

Choose approved connected packages **or** the offline-bundle paragraph below; do not run both installation paths.
On **`boot-1`**, for connected EL10 (Rocky/Alma):

```bash
sudo dnf install -y lvm2 parted xfsprogs
```

For Debian/Ubuntu, use this block instead:

```bash
sudo apt-get update
sudo apt-get install -y lvm2 parted xfsprogs e2fsprogs
```

For an offline installation, first set the verified bundle path on **`boot-1`**:

```bash
read -r -p 'Verified extracted bundle directory on mounted media: ' BUNDLE
```

Follow [offline OS package installation](step-3e-bootstrap-offline.md#9-install-signed-os-packages) using that
bundle, then return here. The offline reference supplies EL10 RPMs; Debian/Ubuntu needs its own matching
signed package bundle.

<a id="1-identify-disks-and-the-existing-root-lv"></a>
<a id="2a-grow-the-existing-disk--preferred"></a>
<a id="steps"></a>

## A. Enlarge the existing disk

### 1. Find the root disk, partition and logical volume

On **`boot-1`**:

```bash
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS
findmnt -n -o SOURCE,FSTYPE /
sudo pvs
sudo lvs -o vg_name,lv_name,lv_path,lv_size
```

The following example uses root PV `/dev/sda4`, VG `rocky` and root LV `/dev/rocky/lvroot`.
Use the names from the output; for example, Ubuntu may use `/dev/ubuntu-vg/ubuntu-lv`.
Match the LV to `/`, not merely a familiar name. [1]

### 2. Enlarge the disk in Proxmox

Stop bootstrap jobs and shut down **`boot-1`**. In **Proxmox > VM > Hardware**, select
**Hard Disk (scsi0) > Disk Action > Resize**. Enter the increment: add `60 GiB` to grow an
`80 GiB` disk to `140 GiB`. Start the VM again. [2]

### 3. Check the new disk size

On **`boot-1`**:

```bash
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS
```

Expect `/dev/sda` to have grown while `/dev/sda4` still has its old size.
The PV partition needs free space immediately after it.

### 4. Extend the existing partition

On **`boot-1`**, for the example's disk `/dev/sda`, partition **4**:

```bash
sudo parted /dev/sda resizepart 4 100%
sudo partprobe /dev/sda
sudo udevadm settle
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS
```

If Parted asks to fix GPT metadata after the disk enlargement, select **Fix**. Confirm an
in-use-partition prompt only for the verified root PV partition. `resizepart` changes its end;
the PV and filesystem are extended in the next steps. [3]

Expect `/dev/sda4` to grow. If it has not, stop; do not remove or recreate the partition.
Reboot through the console if the kernel still reports the old size, then check again.

### 5. Extend the physical volume

On **`boot-1`**:

```bash
sudo pvresize /dev/sda4
sudo pvs
sudo vgs
```

The existing VG should now have more free space. [1]

### 6. Extend root and its filesystem

On **`boot-1`**, use the root LV identified in Step 1:

```bash
sudo lvextend -r -l +100%FREE /dev/rocky/lvroot
```

`-r` grows the filesystem too; `+100%FREE` uses all remaining free space in the VG.
Stop if filesystem resizing fails. [5]

### 7. Verify the result

On **`boot-1`**:

```bash
sudo lvs -o lv_path,lv_size,devices
df -h / /home
```

Expect the root filesystem to have grown. Continue at [Create the workspace](#create-the-workspace-and-continue).
Path B is an alternative; do not perform it as the next step.

<a id="2b-add-another-disk-to-the-vg--alternative"></a>

## B. Add a disk to the existing volume group

### 1. Add the disk in Proxmox

In **Proxmox > boot-1 > Hardware > Add > Hard Disk**, add `scsi1` on qualified live storage.
Keep **Backup** enabled. After this path, root depends on both disks; back up and restore them together.

### 2. Identify the new, empty disk

On **`boot-1`**:

```bash
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS
```

Example output:

```text
NAME                SIZE FSTYPE      TYPE MOUNTPOINTS
sda                  80G             disk
├─sda1                1M             part
├─sda2              200M vfat        part /boot/efi
├─sda3                1G xfs         part /boot
└─sda4             78.8G LVM2_member part
  ├─rocky-lvroot   69.8G xfs         lvm  /
  └─rocky-swap        9G swap        lvm  [SWAP]
sdb                  60G             disk
```

Here, `sdb` is the new disk. Use the actual device name; the next step replaces its partition table.
Confirm it contains no required data, partitions or mounts. Never use the existing root disk.

### 3. Partition the new disk

On **`boot-1`**, for the verified empty `/dev/sdb`:

```bash
sudo parted /dev/sdb --script mklabel gpt
sudo parted /dev/sdb --script mkpart primary 1MiB 100%
sudo parted /dev/sdb --script set 1 lvm on
sudo partprobe /dev/sdb
sudo udevadm settle
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS
```

Expect the new partition `/dev/sdb1`.

### 4. Create the physical volume

On **`boot-1`**:

```bash
sudo pvcreate /dev/sdb1
```

Require successful PV creation. A notice about not creating a system devices file because VGs
already exist is separate from PV creation; investigate missing/excluded-device errors before continuing. [4]

### 5. Find the existing volume group

On **`boot-1`**:

```bash
sudo vgs
```

Example output:

```text
  VG     #PV #LV #SN Attr   VSize   VFree
  rocky    1   2   0 wz--n- <78.80g     0
```

Use the existing root VG name, here `rocky`; do not create another VG.

### 6. Add the new physical volume to that group

On **`boot-1`**:

```bash
sudo vgextend rocky /dev/sdb1
```

### 7. Verify the group and find the root logical volume

On **`boot-1`**:

```bash
sudo pvs
sudo vgs
sudo lvs -o vg_name,lv_name,lv_path,lv_size
findmnt -n -o SOURCE,FSTYPE /
```

Expect two PVs in `rocky` and roughly `60 GiB` more free space. Match the root mount to its LV.
This example uses `/dev/rocky/lvroot`; use the actual path from the output. [1]

### 8. Extend root and its filesystem

On **`boot-1`**:

```bash
sudo lvextend -r -l +100%FREE /dev/rocky/lvroot
```

`-r` grows the filesystem too; `+100%FREE` uses all remaining free space in the VG.
Stop if filesystem resizing fails. [5]

### 9. Verify the result

On **`boot-1`**:

```bash
sudo lvs -o lv_path,lv_size,devices
df -h / /home
```

Expect root to have grown. `/home` gains space only if it shares that root filesystem.
The additional disk is now part of root and cannot be detached as an independent workspace.

<a id="3-extend-root-verify-and-back-up"></a>

## Create the workspace and continue

On **`boot-1`**, create the directories on the expanded root filesystem:

```bash
sudo install -d -m 0700 -o "$(id -un)" -g "$(id -gn)" \
  /srv/tier0/src /srv/tier0/artifacts /srv/tier0/offline /srv/tier0/tmp/proxmox-upload
findmnt -T /srv/tier0
df -h / /home /srv/tier0
```

Keep the existing root mount; no new `/etc/fstab` entry or `/home` bind mount is needed.
Back up all disks containing the root VG in the [bootstrap recovery set](../../../05-operations/06-resilience/backups/recovery-set.md).
Rollback uses the pre-change VM backup; shrinking root or unplugging a PV is not an undo step.

**Continue:** [Bootstrap Step 5](README.md#step-5-select-tool-acquisition), selecting connected **5a**
or offline **5b**. For 5b, transfer and verify the full bundle in the completed workspace before
restoring the kit/runtime; retain OS packages already installed from verified media.
Skip the separate-filesystem mount check and home bind mount from bootstrap storage 3a.

## References

1. [Rocky Linux filesystem and LVM administration](https://docs.rockylinux.org/books/admin_guide/07-file-systems/), checked 2026-11-09.
2. [Proxmox disk-resize increments](https://github.com/proxmox/pve-manager/blob/master/www/manager6/qemu/HDResize.js), checked 2026-11-09.
3. [GNU Parted partition resizing](https://www.gnu.org/software/parted/manual/html_node/resizepart.html), checked 2026-11-09.
4. [LVM devices-file handling for existing VGs](https://github.com/lvmteam/lvm2/blob/main/lib/device/device_id.c), checked 2026-11-09.
5. [LVM filesystem resizing and free-extent options](https://github.com/lvmteam/lvm2/blob/main/tools/args.h), checked 2026-11-09.
