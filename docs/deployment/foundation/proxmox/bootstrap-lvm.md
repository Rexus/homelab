# Expand bootstrap storage with Rocky Linux LVM

For more root/home capacity, **grow the existing Proxmox disk first**. Add another disk to the
root volume group only when that layout is intentional. Both paths expand the existing filesystem;
neither creates a new mount at `/srv/tier0`.

**Run on:** `boot-1` as `automation`, with authorized sudo and independent Proxmox console access.
**Before starting:** accepted VM backup, an existing ordinary LVM root filesystem and approved OS tools.
**Branch from:** [Bootstrap storage B](bootstrap.md#b-expand-the-existing-rocky-linux-root--lvm-alternative).
Use the actual disk, PV partition, VG and root LV found below; example names are not Rocky defaults.

## Steps

1. [Identify disks and the existing root LV](#1-identify-disks-and-the-existing-root-lv).
2. Choose **[2a: grow the existing disk](#2a-grow-the-existing-disk--preferred)** or
   **[2b: add another disk](#2b-add-another-disk-to-the-vg--alternative)**.
3. [Extend root, verify and back up](#3-extend-root-verify-and-back-up).

## Prepare OS tools

On `boot-1` as automation, install OS packages through approved repositories, outside any Python environment:

```bash
sudo dnf install -y lvm2 cloud-utils-growpart parted xfsprogs
```

For disconnected setup, these packages are included in the
[offline RPM acquisition list](bootstrap-offline.md#1a-download-os-packages-and-reviewed-source).
If storage is not ready yet, use a verified bundle on independently mounted media and complete
[OS package installation](bootstrap-offline.md#3a-install-signed-os-packages), setting `BUNDLE` to
that actual media path. Return here before copying the full image bundle or creating tool environments.

Offline only: set this before the linked OS-install block, in the same Bash session.

```bash
read -r -p 'Verified extracted bundle directory on mounted media: ' BUNDLE
```

## 1. Identify disks and the existing root LV

Run on **`boot-1`** as automation. Read-only discovery.

```bash
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS
findmnt -n -o SOURCE,FSTYPE /
findmnt -T /home
sudo pvs
sudo vgs
sudo lvs -o vg_name,lv_name,lv_path,lv_size
```

Illustrative output; `sdb` appears only after adding the second disk for **2b**:

```text
NAME                SIZE FSTYPE      TYPE MOUNTPOINTS
sda                  80G             disk
├─sda1                1G xfs         part /boot
└─sda2               79G LVM2_member part
  ├─rocky-lvroot     70G xfs         lvm  /
  └─rocky-swap        9G swap        lvm  [SWAP]
sdb                  60G             disk
```

The example's root PV is `/dev/sda2`, VG is `rocky`, and root LV is `/dev/rocky/lvroot`.
`findmnt` may show the equivalent `/dev/mapper/rocky-lvroot` path. An installation using
`rl/root` must use `/dev/rl/root` instead. Match the LV to `/`, not merely a familiar name. [1]
Root growth gives `/home` more space only when `/home` is on that root filesystem.

## 2a. Grow the existing disk — preferred

1. Stop bootstrap jobs and shut down the VM. In **Proxmox > VM > Hardware**, select the existing
   **Hard Disk (scsi0) > Disk Action > Resize**. Enter the **increment**, not the final size:
   for example, add `60 GiB` to grow an `80 GiB` disk to `140 GiB`. Start the VM again. [2]
2. Repeat `lsblk` and confirm `/dev/sda` grew while `/dev/sda2` still has its previous size.
   This example requires the PV partition to have free space immediately after it.
3. Grow partition **2**, then check its size before resizing the PV:

   Run on **`boot-1`**. Example only: /dev/sda, partition 2 is the verified root PV.

   ```bash
   sudo growpart /dev/sda 2
   sudo udevadm settle
   lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS
   ```

   `growpart` preserves the existing partition's contents and extends its boundary. If the
   partition has not grown, stop; do not remove/recreate it. Reboot through the console if the
   kernel still reports the old size, then check again. Optional preview: `growpart -N /dev/sda 2`. [3]
4. Enlarge the **existing PV** to use the partition's new capacity:

   Run on **`boot-1`**. Preserve the existing root PV and VG.

   ```bash
   sudo pvresize /dev/sda2
   sudo pvs
   sudo vgs
   ```

   The existing VG now has additional free space. Continue at **Step 3**; `pvcreate`, `vgextend`
   and a new partition table are not needed on this path. [1]

## 2b. Add another disk to the VG — alternative

1. In **Proxmox > VM > Hardware > Add > Hard Disk**, add `scsi1` on qualified live storage and
   enable **Backup**. Identify the new guest device again with `lsblk`; do not assume it is `sdb`.
2. For the example's **new, empty `/dev/sdb` only**, inspect signatures:

   Run on **`boot-1`**. Read-only check of the proposed NEW disk.

   ```bash
   sudo wipefs --no-act /dev/sdb
   ```

   Require the intended blank disk with no required data, partitions or mounts. **The next block
   replaces its partition table. Never run it on the existing root disk.**

   Run on **`boot-1`** only after identifying /dev/sdb as the new empty disk.

   ```bash
   sudo parted /dev/sdb --script mklabel gpt
   sudo parted /dev/sdb --script mkpart primary 1MiB 100%
   sudo parted /dev/sdb --script set 1 lvm on
   sudo partprobe /dev/sdb
   sudo udevadm settle
   lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS
   ```

3. Require the new partition `/dev/sdb1`, initialize its physical volume and inspect the existing VG:

   Run on **`boot-1`**. Initialize only the new partition.

   ```bash
   sudo pvcreate /dev/sdb1
   sudo pvs
   sudo vgs
   ```

   Example existing VG before extension:

   ```text
     VG     #PV #LV #SN Attr   VSize   VFree
     rocky    1   2   0 wz--n- <79.00g     0
   ```

   A message such as `Not creating system devices file due to existing VGs` concerns LVM's
   device-discovery file, not creation of the PV or VG. Require successful PV creation and
   visibility in `pvs`; stop on missing/excluded-device errors. Do not disable device filtering
   or create another VG as a workaround. [4]
4. Add that PV to the **existing root VG**, then verify its new capacity:

   Run on **`boot-1`**. Example root VG verified in Step 1: rocky.

   ```bash
   sudo vgextend rocky /dev/sdb1
   sudo pvs
   sudo vgs
   ```

   Expect two PVs in `rocky` and roughly `60 GiB` of new free space. Continue below. [1]

## 3. Extend root, verify and back up

For the example's verified root LV:

Run on **`boot-1`**. Replace the path if discovery showed a different root LV.

```bash
sudo lvextend -r -l +100%FREE /dev/rocky/lvroot
sudo lvs -o lv_path,lv_size,devices
df -h / /home
```

`-r` grows the filesystem too; `+100%FREE` consumes **all** remaining free extents in the VG,
including any free space that existed before this change. Stop if filesystem resizing fails. [1][5]

Create the bootstrap directories on the expanded root filesystem:

Run on **`boot-1`** as automation; /srv/tier0 is a directory on root for this layout.

```bash
sudo install -d -m 0700 -o "$(id -un)" -g "$(id -gn)" \
  /srv/tier0/src /srv/tier0/artifacts /srv/tier0/offline /srv/tier0/tmp/proxmox-upload
findmnt -T /srv/tier0
df -h / /home /srv/tier0
```

Keep the existing root mount; no new `/etc/fstab` entry or `/home` bind mount is needed here.
For **2b**, root now depends on **both physical volumes/disks**: back up and restore both together;
the extra disk cannot be detached as an independent workspace. For **2a**, retain every disk
already required by the selected layout. Reboot with console access, recheck LVM/mounts and qualify
the [bootstrap backup/recovery set](../../../administration/backups/recovery-set.md).
Rollback uses the accepted pre-change VM backup; shrinking root or unplugging a PV is not an undo step.

**Rejoin:** [Bootstrap 2a](bootstrap.md#2a-install-through-approved-sources) or
[2b offline](bootstrap.md#2b-transfer-a-prepared-bundle--offline-alternative).
The separate-filesystem `mountpoint -q /srv/tier0` gate does not apply to this root-LVM layout.

## References

1. [Rocky Linux filesystem and LVM administration](https://docs.rockylinux.org/books/admin_guide/07-file-systems/).
2. [Proxmox disk-resize increments](https://github.com/proxmox/pve-manager/blob/master/www/manager6/qemu/HDResize.js).
3. [Native growpart behavior and dry run](https://github.com/canonical/cloud-utils/blob/main/man/growpart.1).
4. [LVM devices-file handling for existing VGs](https://github.com/lvmteam/lvm2/blob/main/lib/device/device_id.c).
5. [Enterprise Linux LV/filesystem growth and devices-file policy](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html-single/configuring_and_managing_logical_volumes/configuring_and_managing_logical_volumes).
