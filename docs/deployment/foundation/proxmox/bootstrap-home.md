# Bootstrap home directories on the data disk

Place `/home` on the attached data disk before installing Python environments or
cloning repositories. A bind mount keeps `/home/automation` unchanged for SSH and
tools while storing its files under `/srv/tier0/home`. Artifact paths stay unchanged.

**Working repository:** none during this manual option; `<prefix>-tier-0` after generation.
**Run on:** `boot-1`, from a root shell in the independent Proxmox console.
**Prerequisites:** completed Cloud-Init, full-clone backup, mounted local data disk at `/srv/tier0`, and
`/home` still on the OS filesystem with no nested mounts. An existing separate
`/home` needs its own migration plan. This option formats no disk and changes no UID/GID.
Use a Linux filesystem supporting ownership, ACLs and extended attributes; the
mount must allow executing the bootstrap scripts and Python environments.

## Contents

- [1. Prepare tools and console access](#1-prepare-tools-and-console-access)
- [2. Copy existing homes](#2-copy-existing-homes)
- [3. Mount, test and reboot](#3-mount-test-and-reboot)
- [Rollback before deployment](#rollback-before-deployment)
- [References](#references)

## 1. Prepare tools and console access

Choose **1a** for approved connected sources or **1b** for offline preparation;
both continue with the root console below. These are OS packages, not Python venv dependencies.

### 1a: Approved connected sources

From the normal `automation` login, install the tools using the matching OS block.

Enterprise Linux / Fedora:

Run on **`boot-1`** as automation.

```bash
sudo dnf install -y rsync policycoreutils-python-utils
```

Debian / Ubuntu without SELinux:

Run on **`boot-1`** as automation.

```bash
sudo apt-get install -y rsync
```

### 1b: Offline bundle

Complete [bundle preparation, transfer and OS installation through Step 3a](bootstrap-offline.md#3a-install-signed-os-packages).
It includes the Enterprise Linux tools above. Return here before its Step 3b creates
Python environments or clones the kit; do not run networked package installs offline.

### Both paths: Open the console

Open the **Proxmox console**, obtain a root shell, stop deployment jobs and close
other user sessions. Keep this console open until SSH and reboot checks pass.
Do not perform the cutover from the only SSH session.

Run on **`boot-1`** from its independent console; enter the root shell first.

```bash
sudo -i
```

Run on **`boot-1`** as root from the independent console.

```bash
cd /root
findmnt -T /home
findmnt -T /srv/tier0
findmnt -rn -o TARGET
```

Require the intended data disk, with `/home` on the OS filesystem and no mount at
or below `/home`. Stop if those prerequisites differ. Use the actual data mount
consistently if it is not `/srv/tier0`.

## 2. Copy existing homes

**Run as root from the console.** Require a new destination and preserve the
existing homes, numeric owners, hidden files, permissions, hard links, ACLs and
extended attributes. The dry run must show no differences before continuing. [1]

Run on **`boot-1`** as root from the independent console.

```bash
set -e
mountpoint -q /srv/tier0
test ! -e /srv/tier0/home
mkdir /srv/tier0/home
rsync -aHAX --numeric-ids /home/ /srv/tier0/home/
rsync -aHAXnc --numeric-ids --itemize-changes /home/ /srv/tier0/home/
cp -a /etc/fstab /root/fstab.before-bootstrap-home
```

Stop on errors or differences; do not mount an incomplete copy. The original
`/home` stays on the OS disk as the initial rollback copy.

For **enabled SELinux**, add a persistent home-context equivalence and relabel
only the new home subtree. Keep SELinux enabled; do not relabel all artifacts/state
as home data. Skip this block when SELinux is disabled. [2]

Run on **`boot-1`** as root from the independent console.

```bash
semanage fcontext -a -e /home /srv/tier0/home
restorecon -RFv /srv/tier0/home
```

## 3. Mount, test and reboot

Edit `/etc/fstab` as root. Keep the existing UUID-based `/srv/tier0` entry and add
this **one** line; the dependency makes the data mount precede `/home`. Do not add
`nofail`: a missing home disk must require console recovery, not silently use stale
homes on the OS disk. [3]

```text
# Edit on boot-1 as root (OS configuration).
/etc/fstab # Retain the UUID data mount; add the single bind entry below without nofail.
```

```fstab
/srv/tier0/home /home none bind,x-systemd.requires-mounts-for=/srv/tier0 0 0
```

Validate and activate the mount:

Run on **`boot-1`** as root from the independent console.

```bash
findmnt --verify
systemctl daemon-reload
mount /home
findmnt -M /home
df -h / /home /srv/tier0
ls -ldZ /home /home/automation /home/automation/.ssh
```

Require `/home` on the data filesystem with the original owners and private SSH
permissions. From an approved workstation, open a **new** SSH login as `automation`,
then check `sudo -v`. Repeat for the other approved keys. Reboot from the console
and repeat the mount/login checks before proceeding.

**Result:** home data, including `.ssh` and user Python environments, uses the
attached disk. Root's `/root` and OS packages still use the OS disk. Repository,
artifact and upload paths remain under `/srv/tier0`; no account-path changes are needed.
Include **both disks** and the SELinux/fstab configuration in the independent VM backup.
Return as `automation` to [Bootstrap Step 2a](bootstrap.md#2a-install-through-approved-sources),
or [offline Step 3b](bootstrap-offline.md#3b-restore-the-kit-and-install-the-isolated-pythonansible-environment)
if the bundle's OS packages were already installed.

## Rollback before deployment

If mount, SSH or reboot checks fail, use the retained root console:

1. Stop user jobs and close other sessions. Preserve new home files independently.
2. Run `cd /root` and `umount /home` if the bind mount is active. The untouched
   original homes become visible again; do not use a forced or lazy unmount.
3. Remove only this option's bind-mount line from `/etc/fstab`, then run
   `findmnt --verify` and `systemctl daemon-reload`.
4. If this option added the equivalence, remove it with
   `semanage fcontext -d -e /home /srv/tier0/home`. Retain the data copy.
5. Recheck SSH/sudo and reboot with console access available.

This rollback does not merge files written after cutover. After deployment has
started, restore a current consistent full-VM backup with its original state/inputs,
or plan a deliberate migration; do
not copy a growing data-disk home blindly onto the smaller OS disk.

## References

1. [Rsync options for metadata and checksum comparison](https://download.samba.org/pub/rsync/rsync.1).
2. [SELinux file-context equivalence](https://github.com/SELinuxProject/selinux/blob/main/python/semanage/semanage-fcontext.8).
3. [systemd mount dependencies and fstab behavior](https://www.freedesktop.org/software/systemd/man/262/systemd.mount.html).
