# Step 3c: Bootstrap home directories on the data disk

**Branch from:** [Step 3](../README.md#step-3-prepare-the-bootstrap-execution-host), option **3c**,
after storage path 3a and before installing tools or copying repositories/keys.
**Return:** [Bootstrap Step 5](README.md#step-5-select-tool-acquisition) after reboot/SSH checks;
the storage and home-placement decisions are then complete.

Move `/home` to the attached data disk before installing Python environments or cloning repositories.
A bind mount keeps `/home/automation` unchanged while storing its files under `/srv/tier0/home`.

**Run on `boot-1`**, with independent Proxmox console access.
**Before starting:** completed Cloud-Init, a full-clone backup, a mounted data disk at `/srv/tier0`,
and `/home` still on root with no nested mounts. Use a Linux filesystem supporting ownership,
ACLs, extended attributes and executable files. This option formats no disk or changes account IDs.

## Contents

1. [Install the OS tools](#1-install-the-os-tools)
2. [Open the independent root console](#2-open-the-independent-root-console)
3. [Check the current mounts](#3-check-the-current-mounts)
4. [Copy the existing homes](#4-copy-the-existing-homes)
5. [Verify the copy](#5-verify-the-copy)
6. [Set SELinux contexts when enabled](#6-set-selinux-contexts-when-enabled)
7. [Add the persistent mount](#7-add-the-persistent-mount)
8. [Activate and check the mount](#8-activate-and-check-the-mount)
9. [Test a new SSH login](#9-test-a-new-ssh-login)
10. [Reboot and repeat the checks](#10-reboot-and-repeat-the-checks)
11. [Back up and continue](#11-back-up-and-continue)

- [Rollback before deployment](#rollback-before-deployment)

<a id="1-prepare-tools-and-console-access"></a>

## 1. Install the OS tools

Choose **1a** or **1b**; both continue at **2**. These are OS packages, separate from Python environments.

### 1a: Approved connected sources

On **`boot-1`**, from the normal SSH account, use the matching package block.

Enterprise Linux / Fedora:

```bash
sudo dnf install -y rsync policycoreutils-python-utils
```

Debian / Ubuntu without SELinux:

```bash
sudo apt-get install -y rsync
```

### 1b: Offline bundle

Use the verified bundle already selected for workspace preparation; it contains the Enterprise Linux tools above.
If those packages are not installed, complete [offline OS installation](step-3e-bootstrap-offline.md#9-install-signed-os-packages)
from the independently mounted media. Return here before restoring the kit or creating Python environments;
do not restart bundle acquisition/transfer when an accepted copy already exists.

<a id="both-paths-open-the-console"></a>

## 2. Open the independent root console

Open the **Proxmox console**, stop deployment jobs and close other user sessions.
Keep this console open until the SSH and reboot checks pass.

On **`boot-1`**, enter the root shell from that console:

```bash
sudo -i
```

## 3. Check the current mounts

On **`boot-1`**, as root in the console:

```bash
cd /root
findmnt -T /home
findmnt -T /srv/tier0
findmnt -rn -o TARGET
```

Require the intended data filesystem, `/home` on root, and no mounts at or below `/home`.
Stop if the layout differs. Substitute the actual data mount consistently if it is not `/srv/tier0`.

<a id="2-copy-existing-homes"></a>

## 4. Copy the existing homes

On **`boot-1`**, as root in the console:

```bash
set -e
mountpoint -q /srv/tier0
test ! -e /srv/tier0/home
mkdir /srv/tier0/home
rsync -aHAX --numeric-ids /home/ /srv/tier0/home/
```

This requires a new destination and preserves hidden files, numeric owners, permissions,
hard links, ACLs and extended attributes. The original homes stay on the OS disk. [1]

## 5. Verify the copy

On **`boot-1`**, as root in the console:

```bash
rsync -aHAXnc --numeric-ids --itemize-changes /home/ /srv/tier0/home/
```

**Expected:** no differences. Stop on errors or listed differences; do not mount an incomplete copy. [1]

## 6. Set SELinux contexts when enabled

On **`boot-1`**, as root in the console, apply this only when SELinux is enabled:

```bash
semanage fcontext -a -e /home /srv/tier0/home
restorecon -RFv /srv/tier0/home
```

Keep SELinux enabled; relabel only the new home subtree. Skip this step when SELinux is disabled. [2]

<a id="3-mount-test-and-reboot"></a>

## 7. Add the persistent mount

On **`boot-1`**, as root in the console, save the original configuration:

```bash
cp -a /etc/fstab /root/fstab.before-bootstrap-home
```

Edit `/etc/fstab` on **`boot-1`**. Keep its existing UUID-based `/srv/tier0` mount and add
this single line:

```fstab
/srv/tier0/home /home none bind,x-systemd.requires-mounts-for=/srv/tier0 0 0
```

The dependency mounts the data disk before `/home`. Omit `nofail`: a missing disk must require
console recovery instead of silently exposing stale homes on root. [3]

## 8. Activate and check the mount

On **`boot-1`**, as root in the console:

```bash
findmnt --verify
systemctl daemon-reload
mount /home
findmnt -M /home
df -h / /home /srv/tier0
ls -ldZ /home /home/automation /home/automation/.ssh
```

**Expected:** `/home` uses the data filesystem with the original owners and private SSH permissions.
Use the configured account name if it is not `automation`.

## 9. Test a new SSH login

From **each approved workstation**, open a new SSH login to `boot-1` using its approved key.
Keep the independent console open. In the new login, run:

```bash
sudo -v
```

**Expected:** login and authorized sudo both work.

## 10. Reboot and repeat the checks

Reboot **`boot-1`** from the Proxmox console. In its root console after reboot, run:

```bash
findmnt -M /home
df -h / /home /srv/tier0
ls -ldZ /home /home/automation /home/automation/.ssh
```

**Expected:** the persistent mount and permissions are correct without a manual mount command.
Repeat **9**'s new SSH login and sudo check.

## 11. Back up and continue

Include both disks and the SELinux/fstab configuration in the independent
[bootstrap recovery set](../../../05-operations/06-resilience/backups/recovery-set.md).
Home data uses the attached disk; root's `/root` and OS packages remain on the OS disk.
Repository and artifact paths remain under `/srv/tier0`.

Return as the normal SSH account to [Bootstrap Step 5](README.md#step-5-select-tool-acquisition).
For offline acquisition, reuse the verified bundle and installed OS packages. Transfer/verify its full
workspace copy if still on media, then resume [offline kit restoration](step-3e-bootstrap-offline.md#10-restore-the-kit-checkout).

## Rollback before deployment

Use the retained **root console on `boot-1`** if a mount, SSH or reboot check fails.

1. Stop user jobs, close other sessions and preserve any new home files independently.
2. If the bind mount is active, run:

   ```bash
   cd /root
   umount /home
   ```

   The untouched original homes become visible again. Do not force or lazily unmount.
3. Remove only the added bind-mount line from `/etc/fstab`, then run:

   ```bash
   findmnt --verify
   systemctl daemon-reload
   ```

4. If **6** added the SELinux equivalence, remove it; retain the data copy:

   ```bash
   semanage fcontext -d -e /home /srv/tier0/home
   ```

5. Recheck SSH/sudo and reboot with console access available.

This initial rollback does not merge files written after cutover. After deployment starts, restore a current
consistent full-VM backup with its original inputs/state, or plan a migration; do not copy a growing
data-disk home blindly onto the smaller OS disk.

## References

1. [Rsync options for metadata and checksum comparison](https://download.samba.org/pub/rsync/rsync.1).
2. [SELinux file-context equivalence](https://github.com/SELinuxProject/selinux/blob/main/python/semanage/semanage-fcontext.8).
3. [systemd mount dependencies and fstab behavior](https://www.freedesktop.org/software/systemd/man/262/systemd.mount.html).
