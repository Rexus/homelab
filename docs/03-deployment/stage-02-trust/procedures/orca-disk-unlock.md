# Optional YubiKey/FIDO2 unlock for ORCA working storage

A compatible FIDO2 YubiKey is a useful optional convenience for repeated ORCA ceremonies when you
can retain independent passphrase recovery and qualify the actual device. This path adds native
LUKS2 disk unlock with a PIN and physical touch. Keep the existing LUKS passphrase and its keyslot.
Enrollment adds a slot; these steps never format storage, erase slots or reset the token. [1]
PIN and touch apply to the token path; the retained LUKS passphrase remains an alternative unlock.
Prefer a dedicated ceremony FIDO2 token, stored separately from the working disk. This remains an
optional path; qualify the actual token and ceremony hardware before relying on it.

ORCA still uses an **encrypted software PEM root key**, not an HSM-backed root. Its root-key
passphrase remains independent and is still required for signing after the disk opens. The age
identity is only for backup restoration; it is not a disk-unlock or root-signing credential. Keep
all three credentials in their existing separate custody.

**Start from:** the [accepted ceremony environment](ceremony-environment.md) and an existing,
closed LUKS2 working partition. For new media, first complete
[working-media preparation](offline-root.md#4-mount-custody-media-and-disconnect).
**Recovery and changes:**
[restore retained CA history](../../../05-operations/03-cryptography/offline-root.md#restore-and-test-a-copy),
[update the OS/tools](../../../05-operations/03-cryptography/offline-root.md#update-the-offline-computer-or-tools),
or [handle a lost token](#8-handle-updates-or-a-lost-token).

## Contents

- [1. Build and accept the native tools](#1-build-and-accept-the-native-tools)
- [2. Identify the retained LUKS2 volume](#2-identify-the-retained-luks2-volume)
- [3. Protect a header backup](#3-protect-a-header-backup)
- [4. Check the token and its PIN](#4-check-the-token-and-its-pin)
- [5. Enroll one token with PIN and touch](#5-enroll-one-token-with-pin-and-touch)
- [6. Unlock and mount manually](#6-unlock-and-mount-manually)
- [7. Close after the ceremony](#7-close-after-the-ceremony)
- [8. Handle updates or a lost token](#8-handle-updates-or-a-lost-token)

## 1. Build and accept the native tools

On the connected builder, use the existing [image build procedure](ceremony-environment.md#4-select-build-inputs)
with a **new `ceremony_build_revision`**. The existing seal binds both the package list and build
hook; reusing an already sealed revision after this change is refused. Do not bypass that guard.
Keep custody media, YubiKeys, PINs and private recovery material detached from the builder.

The Debian 12 Bookworm image selects `systemd`, `systemd-sysv`, `cryptsetup-bin`, `fido2-tools` and
`libfido2-1`. Bookworm's `systemd` package supplies `systemd-cryptenroll`,
`/lib/systemd/systemd-cryptsetup` and the systemd FIDO2 LUKS2 plugin; the separate
`systemd-cryptsetup` package is a later Debian packaging split. No YubiHSM SDK is needed for this
YubiKey FIDO2 path. The chroot hook checks systemd 252, compiled FIDO2 support, enrollment options,
the plugin and native CLI availability, without accessing hardware. [3][4][5]

Rehearse enrollment, PIN/touch unlock and passphrase recovery on **disposable LUKS2 test media**
before enrolling production storage. Native CLI/build checks do not qualify a real token or USB
passthrough; hardware testing has not been performed for this change.

For a VM, pass the selected key only to the selected NIC-less ORCA session using an accepted
Proxmox USB resource mapping in `ceremony_sessions["orca-1"].usb_mappings`, alongside its existing
working/transfer/backup mappings. The ceremony Terraform resource consumes these as `usb.mapping`.
Follow [VM session provisioning](ceremony-environment.md#7b-provision-optional-nic-less-vm-sessions)
while sessions are shut down; include that exact key mapping in `ceremony_access_usb_mappings`
before the scoped unlock/provisioning lease. Keep the key out of `cbuild-1` and `cadm-1`.
Physical custody remains preferred; the VM option explicitly trusts its hypervisor.

**Expected:** an accepted new public image, with no private credentials or enrolled disk in it.

## 2. Identify the retained LUKS2 volume

On **the offline ceremony computer's local Bash console**, disconnect networking and attach the
existing working device. Enter a child shell for the steps below;
an error exits this shell without closing the login. On failure, investigate and restart at this
step, checking for an already-open mapping before retrying.

```bash
bash --noprofile --norc
```

In that **same child shell**, disable history:

```bash
set -euo pipefail
export HISTFILE=/dev/null
umask 077
```

If the caller already opened/mounted working storage, first finish all CA commands and ensure no
process is using it. In this **child shell**, close that existing mapping before continuing:

```bash
cd /
sync
sudo umount /mnt/orca-work
sudo cryptsetup close orca-work
```

Skip this block if already closed; for an open but unmounted mapping, run only `cryptsetup close`.
Do not force an unmount or interrupt a CA operation.

<a id="select-working-volume"></a>

**Device/UUID selection for every visit:** inspect the devices in the **same shell**:

```bash
lsblk -p -o NAME,SIZE,MODEL,SERIAL,FSTYPE,UUID,MOUNTPOINTS
read -r -p 'Existing working partition (example /dev/disk/by-id/usb-WORK_DEVICE-part1): ' ORCA_WORK_PARTITION
sudo cryptsetup isLuks --type luks2 "$ORCA_WORK_PARTITION"
sudo cryptsetup luksDump "$ORCA_WORK_PARTITION"
```

Compare model, serial, size and LUKS UUID with the independently retained working-media record.
Require `Version: 2` and the existing passphrase slot. LUKS1 is refused; this procedure never
auto-converts it. For newly created storage, the caller's media-preparation step records the new
UUID independently before entering this procedure. Otherwise use the retained record. Do not
select the ISO, transfer or backup device or substitute a freshly discovered UUID for that record.
In the **same shell**:

```bash
read -r -p 'Independently recorded LUKS UUID (example 12345678-1234-1234-1234-123456789abc): ' ORCA_EXPECTED_UUID
ORCA_LUKS_UUID=$(sudo cryptsetup luksUUID "$ORCA_WORK_PARTITION")
test "$ORCA_LUKS_UUID" = "$ORCA_EXPECTED_UUID"
test ! -e /dev/mapper/orca-work
```

**Enrollment/recovery qualification only — skip for routine token unlock:** in the **same shell**,
verify the retained passphrase before changing enrollment:

```bash
sudo cryptsetup open --type luks2 --disable-external-tokens --test-passphrase "$ORCA_WORK_PARTITION"
```

Enter the **retained LUKS passphrase** at the native prompt. This verifies it without opening the
volume or using the FIDO2 plugin. Device paths and UUIDs are public selections; PINs/passphrases
must never enter variables, command arguments, repository files, Terraform state or the image. [6]

## 3. Protect a header backup

Use the **existing independently mounted backup medium**, which may have a plain filesystem
holding age-encrypted archives. No fourth device or encrypted-filesystem mount is required.
The native `age` CLI encrypts this separate header backup to the public `ORCA_BACKUP_RECIPIENT`
from retained `orca.conf`; no private age identity is attached. A header and a passphrase valid
when it was saved can unlock data after later slot changes, so protect its recovery custody. [7]

In the **same offline shell**, copy the existing public recipient and backup path from retained
`orca.conf`. The directory must be writable and support mode 0600 (or restrictive mount modes).

```bash
read -r -p 'Mounted backup directory from ORCA_BACKUP (example /mnt/orca-backup): ' ORCA_HEADER_DIR
read -r -p 'Public ORCA_BACKUP_RECIPIENT from retained orca.conf (age1...): ' ORCA_HEADER_RECIPIENT
test -d "$ORCA_HEADER_DIR"
findmnt --target "$ORCA_HEADER_DIR"
lsblk -s -p -o NAME,TYPE,SERIAL,MOUNTPOINTS -- "$(findmnt -n -o SOURCE --target "$ORCA_HEADER_DIR")"
```

Verify this is the independent backup device, not working storage, live overlay, ISO staging or
public transfer media. In the **same shell**, keep the plaintext header only in root-owned live
RAM; the exit trap cleans it on failure. The subshell refuses to overwrite any existing output.

```bash
test "$(findmnt -n -o FSTYPE --target /run)" = tmpfs
ORCA_HEADER_TMP=$(sudo mktemp -d /run/orca-header.XXXXXX)
trap 'sudo rm -f -- "$ORCA_HEADER_TMP/header"; sudo rmdir -- "$ORCA_HEADER_TMP"' EXIT
sudo cryptsetup luksHeaderBackup "$ORCA_WORK_PARTITION" --header-backup-file "$ORCA_HEADER_TMP/header"
sudo chmod 0600 "$ORCA_HEADER_TMP/header"
ORCA_HEADER_FILE="$ORCA_HEADER_DIR/$ORCA_LUKS_UUID-before-fido2.header.age"
(
  umask 077
  set -o noclobber
  sudo age --encrypt --recipient "$ORCA_HEADER_RECIPIENT" "$ORCA_HEADER_TMP/header" > "$ORCA_HEADER_FILE"
)
test "$(stat -c %a "$ORCA_HEADER_FILE")" = 600
sudo rm -- "$ORCA_HEADER_TMP/header"
sudo rmdir -- "$ORCA_HEADER_TMP"
trap - EXIT
sha256sum "$ORCA_HEADER_FILE"
sync
```

Record the encrypted backup's checksum in the protected custody record. If encryption fails,
retain/inspect any incomplete `.age` output and select a new filename for a retry. Never copy the
plaintext header into the backup filesystem, public transfer media, repository, builder or image.

## 4. Check the token and its PIN

Attach **only the intended FIDO2 token**. On the **offline console**, in the same shell:

```bash
sudo systemd-cryptenroll --fido2-device=list
sudo fido2-token -L
read -r -p 'Selected token device from the list (example /dev/hidraw0): ' ORCA_FIDO_DEVICE
sudo fido2-token -I "$ORCA_FIDO_DEVICE"
```

Require the `hmac-secret` extension, supported client PIN (`clientPin`) and user presence (`up`,
physical touch). An unset supported PIN may be shown as `noclientPin`; distinguish this from a
device without PIN support. A U2F-only key or a token without these capabilities does not qualify.
Inspect the actual model/firmware and capabilities, rather than assuming every YubiKey works. [1][8]

**Only if no FIDO2 PIN has been set**, use the native setup command in the **same shell**:

```bash
sudo fido2-token -S "$ORCA_FIDO_DEVICE"
sudo fido2-token -I "$ORCA_FIDO_DEVICE"
```

Enter and retain the PIN through the interactive prompt and independent custody. If a PIN already
exists, keep it; do not run setup or reset to work around a forgotten PIN. Stop on unsupported
capabilities or an unknown PIN. This PIN applies to the token's FIDO2 application. [8]

## 5. Enroll one token with PIN and touch

In the **same offline shell**, inspect existing enrollment first:

```bash
sudo systemd-cryptenroll "$ORCA_WORK_PARTITION"
```

If a FIDO2 enrollment already exists, keep it and perform the tests below rather than enrolling again.
Systemd 252 documents limitations identifying which of multiple enrolled FIDO2 tokens is present.
This bounded path uses **one enrolled token plus the retained passphrase**; it promises no spare
token auto-selection. Any multi-token extension needs separate qualification. [1]

With no existing FIDO2 enrollment, add the selected token in the **same shell**:

```bash
sudo systemd-cryptenroll --fido2-device="$ORCA_FIDO_DEVICE" \
  --fido2-with-client-pin=yes --fido2-with-user-presence=yes "$ORCA_WORK_PARTITION"
sudo systemd-cryptenroll "$ORCA_WORK_PARTITION"
sudo cryptsetup luksDump --dump-json-metadata "$ORCA_WORK_PARTITION"
```

Supply the existing LUKS passphrase, token PIN and touch at native prompts. Require the original
passphrase slot plus a `systemd-fido2` header token with `fido2-clientPin-required` and
`fido2-up-required` both `true`. These flags cannot create unsupported token capabilities;
successful unlock testing is still required. No key file, PIN environment variable or custom
crypto helper is used. [1][2]

Before accepting enrollment, in the **same offline shell**, test the token path while the volume
is closed and only the enrolled key is attached:

```bash
sudo /lib/systemd/systemd-cryptsetup attach orca-work "$ORCA_WORK_PARTITION" - fido2-device=auto
sudo cryptsetup status orca-work
sudo /lib/systemd/systemd-cryptsetup detach orca-work
test ! -e /dev/mapper/orca-work
```

Require the native FIDO2 PIN prompt, physical touch and successful mapping; entering the LUKS
passphrase instead does not qualify token unlock. If the session reused a cached PIN, reboot the
accepted live image and repeat device selection and this test before recording PIN-prompt evidence.

Remove the FIDO2 key. In the **same shell**, prove a passphrase-only reopen and mount:

```bash
sudo cryptsetup open --type luks2 --disable-external-tokens "$ORCA_WORK_PARTITION" orca-work
sudo mount /dev/mapper/orca-work /mnt/orca-work
findmnt --mountpoint /mnt/orca-work
sudo umount /mnt/orca-work
sudo cryptsetup close orca-work
test ! -e /dev/mapper/orca-work
```

Enter the retained LUKS passphrase and require the original filesystem. Keep that passphrase
independently of the token/PIN. After both paths pass, repeat step 3's header backup with a **new
`after-fido2.header.age` filename**, preserving the earlier copy. Record the image checksum, LUKS UUID,
token model/firmware and both outcomes in the protected custody record, with no PIN/passphrase.

## 6. Unlock and mount manually

For later ceremonies, boot the accepted offline image and repeat step 2's
[device/UUID selection](#select-working-volume), stopping before the separate qualification block.
The enrollment and passphrase acceptance tests are not needed for each routine unlock. Reattach
only the enrolled token. In the **offline shell**, with the working volume closed:

```bash
sudo /lib/systemd/systemd-cryptsetup attach orca-work "$ORCA_WORK_PARTITION" - fido2-device=auto
sudo cryptsetup status orca-work
sudo install -d -m 0700 /mnt/orca-work
sudo mount /dev/mapper/orca-work /mnt/orca-work
findmnt --mountpoint /mnt/orca-work
```

The `-` supplies no external key file; systemd reads the enrollment from the LUKS2 header.
Enter the **FIDO2 PIN** at the native security-token PIN prompt and physically touch the token.
During qualification, passphrase fallback is not proof of token unlock: require the PIN/touch
exchange and successful mapping. Do not supply a PIN through automation. [2][9]

**Alternative if the key is unavailable:** with the mapping closed, use the retained LUKS
passphrase in the **same offline shell** instead of the token attach block:

```bash
sudo cryptsetup open --type luks2 --disable-external-tokens "$ORCA_WORK_PARTITION" orca-work
sudo mount /dev/mapper/orca-work /mnt/orca-work
findmnt --mountpoint /mnt/orca-work
```

**Expected:** the original working filesystem mounted at `/mnt/orca-work`. Continue the caller's
[local root ceremony](ceremony-environment.md#8-perform-the-selected-ceremony-locally). Root signing
still requests the separate encrypted PEM root-key passphrase. No `/etc/crypttab` entry, boot
auto-unlock, unlock timer or unattended signing is added.

## 7. Close after the ceremony

After finishing work and the normal encrypted CA-state backup, leave the mounted directory and
close it on the **offline console**, in the same shell:

```bash
cd /
sync
sudo umount /mnt/orca-work
sudo /lib/systemd/systemd-cryptsetup detach orca-work
test ! -e /dev/mapper/orca-work
```

Remove the FIDO2 key; unmount the independent backup medium before securing it.
Exit the child shell and return to the caller's shutdown/custody steps.

## 8. Handle updates or a lost token

For an OS/image change, keep private devices detached while building a new revision. Keep the
previous accepted ISO and qualify PIN/touch and passphrase fallback on disposable storage, then
[rehearse CA restoration](../../../05-operations/03-cryptography/offline-root.md#restore-and-test-a-copy)
before production use. Use matching systemd enrollment/unlock versions: newer enrollments are not
guaranteed to work with an older runtime. Follow the existing
[OS/tool update procedure](../../../05-operations/03-cryptography/offline-root.md#update-the-offline-computer-or-tools).
[1]

For a lost, blocked or failed token, open/mount the existing volume using step 6's passphrase alternative.
If both disk unlock paths are unavailable, recover the authoritative CA history onto separate
encrypted working storage using the
[existing backup restore procedure](../../../05-operations/03-cryptography/offline-root.md#restore-and-test-a-copy)
and separately held age identity and root passphrase. Never format the original volume or create
a replacement root as a repair. A header restore is a separate reviewed recovery action, because
it rolls back the slot/token state to the backup's date.

A lost token's enrollment remains valid until explicitly retired. Arrange a separate reviewed
replacement/revocation operation using the retained passphrase and protected header backups;
preserve the passphrase slot and repeat both unlock tests. This add-only procedure deliberately
does not erase enrollments or reset tokens. Until replacement is qualified, use the passphrase
path. Preserve current CA identity/history throughout recovery.

## References

1. [systemd 252: systemd-cryptenroll, enrollment options, multiple FIDO2 tokens and compatibility](https://www.freedesktop.org/software/systemd/man/252/systemd-cryptenroll.html).
2. [systemd 252: crypttab FIDO2 options and native attach example](https://www.freedesktop.org/software/systemd/man/252/crypttab.html).
3. [Debian Bookworm: systemd package file list](https://packages.debian.org/bookworm/amd64/systemd/filelist).
4. [Debian Bookworm: fido2-tools](https://packages.debian.org/bookworm/fido2-tools) and [libfido2-1](https://packages.debian.org/bookworm/libfido2-1).
5. [Debian Trixie: systemd-cryptsetup package split](https://www.debian.org/releases/trixie/release-notes/issues.en.html#encrypted-filesystems-need-systemd-cryptsetup-package).
6. [Debian Bookworm: cryptsetup open, test-passphrase and disable-external-tokens](https://manpages.debian.org/bookworm/cryptsetup-bin/cryptsetup-open.8.en.html).
7. [Debian Bookworm: LUKS header backup and recovery consequences](https://manpages.debian.org/bookworm/cryptsetup-bin/cryptsetup-luksHeaderBackup.8.en.html).
8. [Debian Bookworm: fido2-token inspection and PIN setup](https://manpages.debian.org/bookworm/fido2-tools/fido2-token.1.en.html) and [Yubico: fido2-token manual](https://developers.yubico.com/libfido2/Manuals/fido2-token.html).
9. [systemd 252: systemd-cryptsetup and password-agent prompts](https://www.freedesktop.org/software/systemd/man/252/systemd-cryptsetup.html).
