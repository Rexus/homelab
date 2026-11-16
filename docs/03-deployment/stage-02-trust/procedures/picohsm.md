# Commission the first PicoHSM

Prepare one **blank** Pico for [single USB custody](../step-1d-single-usb.md), retaining a key that
can later be restored onto additional boards. The [issuer view](../README.md#figure-1-offline-root-and-online-issuer)
shows where this key will be used.

This device protects **`ca-1`'s online issuing key**. It does not create the offline root CA.
Prepare that separate authority in [Stage 2 Step 1](../README.md#step-1-prepare-issuer-and-key-custody);
it later signs this issuer's CSR.

**Working repository:** `<prefix>-tier-0` on the protected controller.
**Ceremony host:** preferably a dedicated trusted Linux workstation. The existing manual bootstrap VM
`boot-1` is an explicit learning/constrained-site choice, not an automatic ceremony host.
See [host responsibilities](../../../01-architecture/08-cryptography/04-usb-hsm.md#ceremony-and-deployment-hosts).
The board runs PicoHSM firmware; it does not run Debian, Rocky or AlmaLinux. Those are host OS choices.
Firmware, initialization and key creation are explicit physical custody operations. Ansible prepares
middleware; Terraform owns the later issuer/provider VM attachment.

> **Danger:** initialization erases a device's keys. This first-device path is for a blank board only.
> For an initialized device or another board in the same key domain, use
> [restore the original wrapped key](../../../05-operations/03-cryptography/picohsm-replica.md).

## Contents

- [1. Select the board and firmware](#1-select-the-board-and-firmware)
- [2. Connect the ceremony host](#2-connect-the-ceremony-host)
- [3. Flash the blank board](#3-flash-the-blank-board)
- [4. Prepare middleware through Ansible](#4-prepare-middleware-through-ansible)
- [5. Select the device and recovery directory](#5-select-the-device-and-recovery-directory)
- [6. Create the retained DKEK share](#6-create-the-retained-dkek-share)
- [7. Initialize this blank board](#7-initialize-this-blank-board)
- [8. Load the DKEK](#8-load-the-dkek)
- [9. Create the first signing key](#9-create-the-first-signing-key)
- [10. Record and wrap the original key](#10-record-and-wrap-the-original-key)
- [11. Retain custody and attach the issuer](#11-retain-custody-and-attach-the-issuer)
- [References](#references)

## 1. Select the board and firmware

From the official [PicoHSM downloads](https://www.picokeys.com/getting-started/), select **Pico HSM**
and the exact board, **Pico / RP2040** or **Pico 2 / RP2350**. Keep the exact release, board model,
firmware file and checksum in the private build record. Prefer an approved release over a nightly build. [1]

Do not enable irreversible OTP/secure-boot fuses as part of this walkthrough. The board-specific
[security model](../../../01-architecture/08-cryptography/03-hsm-selection.md) and recovery must be
qualified first. A Pico is not a certified tamper-resistant enterprise HSM.

## 2. Connect the ceremony host

Choose one path:

- **Physical workstation:** temporarily connect the Pico directly to the protected Linux workstation.
- **Existing `boot-1`, board remaining on Proxmox:** in the Proxmox GUI, open **boot-1 → Hardware →
  Add → USB Device → Use USB Port**, then select the board's exact physical port. Record the node/port.
  This temporary attachment is part of the manual bootstrap/device ceremony; remove it before the
  Terraform-owned issuer claims that port. Never attach one device to two VMs. [2]

Only the board being commissioned should be available to the ceremony host.
When choosing `boot-1`, also accept trust in its Proxmox host and administrators. This procedure
commissions the **online issuer's device**; keep offline root signing on its separate custody host.

## 3. Flash the blank board

Hold **BOOTSEL** while reconnecting the board to the same port. A physical desktop workstation can
copy the approved UF2 file onto the new BOOTSEL drive with its file manager. For a Linux CLI, run on
**the ceremony host**, with the downloaded file available locally:

```bash
lsblk -o NAME,PATH,SIZE,FSTYPE,LABEL,MOUNTPOINTS
read -r -e -p 'Approved PicoHSM UF2 file: ' PICO_UF2
sha256sum "$PICO_UF2"
```

Compare that digest with the accepted firmware record. Find the **BOOTSEL** volume, commonly
labelled `RPI-RP2` or `RP2350`; it is not the host's OS/data disk. Mount that specific volume:

```bash
read -r -p 'BOOTSEL partition path from lsblk (for example /dev/sdc1): ' PICO_BOOT_DEVICE
sudo install -d -m 0755 /mnt/picohsm-boot
sudo mount "$PICO_BOOT_DEVICE" /mnt/picohsm-boot
cat /mnt/picohsm-boot/INFO_UF2.TXT
```

The information file must identify the intended Pico board. Copy only the approved matching firmware:

```bash
sudo cp -- "$PICO_UF2" /mnt/picohsm-boot/firmware.uf2
sync
sudo umount /mnt/picohsm-boot
```

The board reboots and the BOOTSEL drive disappears. If it has already been unmounted by the host,
verify that state rather than copying again. Current PicoHSM firmware uses USB ID `2e8a:10fd`. [1]

## 4. Prepare middleware through Ansible

When using a separate workstation, transfer the reviewed generated **Tier 0** and sibling **Shared**
repositories together, retaining their relative directory names. Prepare its Linux/Ansible tools through
[bootstrap tool setup](../../foundation/bootstrap/README.md#step-6-install-os-tools), Steps 6–10,
using that workstation's actual checkout path. The local preparation below uses no Proxmox credentials
and provisions no VM. The existing `boot-1` path already has these tools and repositories.

Initialize the input files from **`<prefix>-tier-0/`**:

```bash
bash scripts/init-local-files.sh --setup foundation --setup hsm
```

In **`ansible/group_vars/hsm.yml`**, select the ceremony host's OS block below. Keep
`hsm_provider_custody_ready: false`. Leave the serial empty until discovery; no application access
is granted by this preparation.

For **Rocky/Alma EL10**, use:

```yaml
hsm_provider: picohsm
hsm_provider_mode: usb
hsm_provider_packages: [opensc]
hsm_provider_library: /usr/lib64/opensc-pkcs11.so
hsm_provider_expected_serial: ""
```

For **Debian 12 amd64**, use this block instead:

```yaml
hsm_provider: picohsm
hsm_provider_mode: usb
hsm_provider_packages: [opensc]
hsm_provider_library: /usr/lib/x86_64-linux-gnu/opensc-pkcs11.so
hsm_provider_expected_serial: ""
```

Run locally on **the ceremony host, from `<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, -c local \
  -e @ansible/group_vars/hsm.yml -e hsm_prepare_group=all \
  ansible/playbooks/deployment/hsm-prepare.yml
```

Ansible installs native tools/PCSC, registers the official Pico USB ID when the packaged CCID list
predates it, and prints public reader/token details. No PIN, key initialization or application policy
is changed. Debian 12's older CCID package needs this registration. [3]
Add `--ask-become-pass` when this local account's accepted sudo access requires a password.

## 5. Select the device and recovery directory

After installing tools, pause deployment jobs and restrict unnecessary connectivity and logins for
the ceremony. Keep the required administrative connection. A network-restricted bootstrap VM is
still not an independent offline workstation.

Open a **temporary root shell on the ceremony host** for headless PCSC access. This is not a login
to a newly deployed service VM. Exit this child shell in action 11:

```bash
sudo -i
```

In that same ceremony shell:

```bash
umask 077
PICO_CUSTODY="$HOME/.local/share/picohsm/issuer"
install -d -m 0700 "$PICO_CUSTODY"
opensc-tool --list-readers
read -r -p 'Reader number for this Pico (for example 0): ' PICO_READER
read -r -p 'Installed PKCS#11 library path printed by preparation: ' PICO_MODULE
pkcs11-tool --module "$PICO_MODULE" --list-slots
read -r -p 'PKCS#11 slot ID for this Pico (for example 0x0): ' PICO_SLOT
```

Reader number and PKCS#11 slot ID are different selectors. Compare the displayed device identity
with the physical board. Record its token serial and exact reader name; do not infer them from `0`.

## 6. Create the retained DKEK share

This example uses **one encrypted DKEK share and one custodian**. The DKEK protects wrapped backups;
it is not the signing key. Use the same original share on later replicas. More custodians require
selecting that share policy before initialization. [4]

Choose this recovery/replication policy now, before generating the original issuer key. Retain the
original share material as well as the wrapped key: a new DKEK domain cannot open an old backup.
Wrapped recovery does not require a plaintext private-key export or relaxing the signing key's
normal sensitive/non-extractable attributes. Keep DKEK/SO custody separate from application signing.

Run **once**, in the same ceremony shell:

```bash
if [ -e "$PICO_CUSTODY/dkek.pbe" ]; then
  printf '%s\n' 'Existing DKEK share retained; do not create a replacement.'
else
  sc-hsm-tool --reader "$PICO_READER" --create-dkek-share "$PICO_CUSTODY/dkek.pbe"
fi
```

The tool asks twice for the share-encryption password. Retain the encrypted share and its password
under separate recovery custody. Recreating this file later creates a different key domain.

## 7. Initialize this blank board

> **Danger:** execute this only on the selected blank board. Do not initialize an installed device
> to fix a connection or PIN error.

Run in the ceremony shell. Choose a new **16-hex-character SO-PIN** and a distinct **6–16-character
user PIN**. The child shell discards the injected values after this command; native `env:` references
keep their values out of argv. [5]

```bash
(
  read -r -s -p 'New SO-PIN (16 hexadecimal characters): ' PICO_SO_PIN; printf '\n'
  read -r -s -p 'New user PIN (6-16 characters): ' PICO_USER_PIN; printf '\n'
  export PICO_SO_PIN PICO_USER_PIN
  sc-hsm-tool --reader "$PICO_READER" --initialize --dkek-shares 1 \
    --label issuer --so-pin env:PICO_SO_PIN --pin env:PICO_USER_PIN
)
```

Retain both credentials independently. Keep the SO-PIN separate from normal signing access.
Do not use the factory example values from upstream documentation.

## 8. Load the DKEK

In the same ceremony shell:

```bash
sc-hsm-tool --reader "$PICO_READER" --import-dkek-share "$PICO_CUSTODY/dkek.pbe"
sc-hsm-tool --reader "$PICO_READER"
```

Enter the retained share password when asked. Record the resulting **DKEK key-check value**.
Continue only when the expected share has been imported and none remain pending. [4]

## 9. Create the first signing key

First list objects. Preserve an existing issuer key and continue at action 10:

```bash
pkcs11-tool --module "$PICO_MODULE" --slot "$PICO_SLOT" --login --list-objects
```

For a new key, this example selects **ECDSA P-384**, PKCS#11 ID `01`, label `issuer`.
Confirm the [approved algorithm](../../../01-architecture/08-cryptography/02-algorithm-selection.md).
Run once; the tool asks for the new user PIN:

```bash
pkcs11-tool --module "$PICO_MODULE" --slot "$PICO_SLOT" --login \
  --keypairgen --key-type EC:secp384r1 --usage-sign --id 01 --label issuer
```

The private key is generated on the board. Verify its reported ID, signing usage and sensitive/
non-extractable attributes; the DKEK-wrapped backup is the separate recovery path. Never repeat
generation to add a replica. [4][6]

## 10. Record and wrap the original key

Export only the public key and retain its fingerprint:

```bash
pkcs11-tool --module "$PICO_MODULE" --slot "$PICO_SLOT" \
  --read-object --type pubkey --id 01 --output-file "$PICO_CUSTODY/issuer-spki.der"
openssl dgst -sha256 "$PICO_CUSTODY/issuer-spki.der"
pkcs15-tool --reader "$PICO_READER" --dump
```

In the dump, find **ID `01`** and copy its **decimal `Key ref`**, for example `1`.
That internal reference can differ from the PKCS#11 ID. Then wrap that exact key:

```bash
read -r -p 'Decimal Key ref for issuer ID 01 (for example 1): ' PICO_KEY_REFERENCE
sc-hsm-tool --reader "$PICO_READER" --wrap-key "$PICO_CUSTODY/issuer.wrapped" \
  --key-reference "$PICO_KEY_REFERENCE"
```

The tool requests the user PIN. The output is a DKEK-wrapped private key, not a plaintext export. [4]

## 11. Retain custody and attach the issuer

Retain `dkek.pbe`, `issuer.wrapped`, `issuer-spki.der`, the fingerprint, firmware record and DKEK
check value outside this controller. Keep passwords/PINs in separate protected custody, outside Git.
Qualify restoration and sign/verify on an additional board using the
[recovery procedure](../../../05-operations/03-cryptography/picohsm-replica.md) before production acceptance.
With only one blank board, that procedure also describes a destructive **pre-production** round trip;
it tests the wrapped backup, not availability after physical device loss. Until restoration succeeds,
record recovery as unqualified rather than setting custody readiness true.

After independently verifying the retained copies, remove temporary recovery files and unmount/remove
custody media from the ceremony host. Keep the DKEK password and SO-PIN out of bootstrap inputs and
VM backups. Deleting files does not erase copies already captured in snapshots/backups; select a
dedicated ceremony workstation when that exposure is unacceptable.

Exit the temporary root shell:

```bash
exit
```

If boot-1 held the board temporarily, remove **only its USB attachment** in Proxmox. Create the
approved physical-node USB mapping for the issuer. Return to
[single USB action 2](../step-1d-single-usb.md#2-declare-usb-attachment-and-install-the-inactive-issuer)
to declare it in Terraform. Use the Debian profile on `ca-1`, even when this ceremony ran on EL10.
The issuer's serial/key URI must name the recorded device and key ID.

For later growth, follow [single device to provider pool](../../../05-operations/03-cryptography/usb-hsm.md#single-device-to-pool).

## References

Sources checked 2026-11-15. Hardware flashing, initialization and restoration still require live qualification.

1. [PicoHSM firmware and board selection](https://github.com/polhenarejos/pico-hsm#download).
2. [Proxmox native USB port and mapping inputs](https://github.com/proxmox/pve-docs/blob/master/generated/qm.1-synopsis.adoc).
3. [CCID reader registration format](https://github.com/LudovicRousseau/CCID/blob/1.5.2/src/Info.plist.src).
4. [PicoHSM DKEK and wrapped-key backup](https://github.com/polhenarejos/pico-hsm/blob/master/doc/backup-and-restore.md).
5. [OpenSC native environment PIN references](https://github.com/OpenSC/OpenSC/blob/0.23.0/src/tools/util.c#L480).
6. [PicoHSM key generation](https://docs.picokeys.com/picohsm/key-generation/).
