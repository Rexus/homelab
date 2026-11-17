# Create and operate the Offline Root CA (ORCA)

Prepare the kit once, create ORCA on a separate offline computer, then reopen that same instance
for issuer signing or root CRL updates. The kit automates tool/policy preparation; native clca
creates the key and signs. Root keys and CA history stay offline.

**Expected result:** the [trust figure](../README.md#figure-1-offline-root-and-online-issuer) shows
ORCA below the connected issuer. The first visit returns public root files; the second returns
`ca-1`'s signed certificate. The issuer's HSM choice does not change ORCA's key.

**Work from:** Tier 0 on the connected preparation host for actions 2–3; the copied kit root on
the separate offline Linux computer for ceremonies. Keep `root_ca` empty in connected inventory.
A VM on the ordinary connected Proxmox cluster is not offline root custody.

> [!TIP]
> **Recovery and maintenance:** [Reopen, restore or update ORCA](../../../05-operations/03-cryptography/offline-root.md).
> Existing pre-kit clca instances retain [their original native workflow](offline-software-root.md).

## Contents

- [First visit: create ORCA](#first-visit)
- [1. Prepare tools and independent recovery](#1-prepare-tools-and-independent-recovery)
- [2. Initialize public configuration](#2-initialize-public-configuration)
- [3. Build and transfer the pinned kit](#3-build-and-transfer-the-pinned-kit)
- [4. Mount custody media and disconnect](#4-mount-custody-media-and-disconnect)
- [5. Prepare and create the root](#5-prepare-and-create-the-root)
- [6. Export public files and back up](#6-export-public-files-and-back-up)
- [Second visit: sign a subordinate](#sign-a-subordinate)
- [References](#references)

<a id="first-visit"></a>
<a id="step-1-prepare-and-rehearse-custody"></a>

## 1. Prepare tools and independent recovery

Use a separately controlled **Linux computer** and three separate physical devices: encrypted
working storage, public transfer media and backup media. The last two need existing writable
filesystems; prepare blank removable media with your normal disk utility. The kit verifies distinct
physical backing. No Ansible or Galaxy installation is needed on the ceremony computer.

**Before attaching root storage**, prepare its OS and tools through an accepted package source.
For **Rocky/AlmaLinux 10**, with the approved EPEL source available for `age`:

```bash
sudo dnf install -y bash coreutils findutils openssl perl util-linux iproute tar age cryptsetup e2fsprogs
```

For **Debian 12+ / Ubuntu**:

```bash
sudo apt-get update
sudo apt-get install -y bash coreutils findutils openssl perl util-linux iproute2 tar age cryptsetup e2fsprogs
```

On **the recovery custodian's separate offline system**, in its private recovery directory:

```bash
umask 077
age-keygen -o orca-recovery.agekey
age-keygen -y orca-recovery.agekey
```

Retain `orca-recovery.agekey` separately from the root and its backup archives. Copy only the printed
`age1...` public recipient to the preparation host. Keep the root passphrase separately too.

## 2. Initialize public configuration

On **bootstrap / the connected preparation host**, from **`<prefix>-tier-0/`**:

```bash
bash scripts/offline-root.sh init
```

Edit **`templates/offline-root/orca.conf`**. `init` preserves an existing file.

| Field | Set |
| --- | --- |
| `ORCA_ORGANIZATION`, `ORCA_COMMON_NAME` | Approved organization and stable root name, e.g. `Example Organization` / `Example Offline Root CA` |
| `ORCA_PUBLICATION_URL` | Future public-object base URL, e.g. `http://ca.internal.example.com/download`, without a trailing slash |
| `ORCA_BACKUP_RECIPIENT` | Recovery custodian's public `age1...` recipient |
| `ORCA_INSTANCE`, `ORCA_TOOLS` | Separate directories on encrypted working storage; defaults `/mnt/orca-work/root` and `/mnt/orca-work/tools` |
| `ORCA_TRANSFER`, `ORCA_BACKUP` | Separately mounted transfer and backup paths; defaults `/mnt/orca-transfer` and `/mnt/orca-backup` |
| `ORCA_ROOT_DAYS`, `ORCA_ISSUER_DAYS`, `ORCA_CRL_DAYS` | Approve the 3650 / 1825 / 90 day defaults, or set the intended policy before creation |

Retain the supplied exact clca revision. Leave `ORCA_CLCA_SOURCE` empty for the checked official
archive, or select an approved clean checkout of that exact revision. The builder checks the revision
and native payload hash. No private keys or passphrases belong in this public configuration.

## 3. Build and transfer the pinned kit

On **the connected preparation host**, from **`<prefix>-tier-0/`**:

```bash
bash scripts/offline-root.sh bundle .local-archive/orca-kit
```

**Expected:** a new public kit with native clca, policy templates, configuration, source pins and
`manifest.sha256`. An existing destination is refused. Record the printed manifest hash independently,
then transfer the entire kit directory on the public media.

On **the offline computer**, from **the copied kit root**:

```bash
sha256sum manifest.sha256
sha256sum --check --strict manifest.sha256
```

Require the independently recorded manifest hash and successful file checks. Retain this original
kit and public configuration for later ceremonies/recovery. It contains tools, not root state.

## 4. Mount custody media and disconnect

On **the ceremony computer**, identify the actual devices:

```bash
lsblk -o NAME,PATH,SIZE,FSTYPE,TYPE,MOUNTPOINTS,MODEL
```

For **existing encrypted working storage**, unlock and mount the retained volume. For **a blank
working partition only**, the example below creates LUKS2 and ext4. Choose an identified removable
partition, such as a stable `/dev/disk/by-id/usb-WORK_DEVICE-part1` path.

> [!CAUTION]
> This action erases the selected working partition. For retained root storage, unlock its existing
> LUKS volume instead; never format or regenerate a root to recover it.

Run on **the ceremony computer**, before CA state exists on that new partition:

```bash
(
  set -e
  read -r -p 'Blank working partition: ' ORCA_WORK_PARTITION
  test -b "$ORCA_WORK_PARTITION"
  lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS "$ORCA_WORK_PARTITION"
  read -r -p "Type ERASE $ORCA_WORK_PARTITION to format it: " ORCA_ERASE
  test "$ORCA_ERASE" = "ERASE $ORCA_WORK_PARTITION"
  sudo cryptsetup luksFormat --type luks2 "$ORCA_WORK_PARTITION"
  sudo cryptsetup open "$ORCA_WORK_PARTITION" orca-work
  sudo mkfs.ext4 /dev/mapper/orca-work
  sudo install -d /mnt/orca-work
  sudo mount /dev/mapper/orca-work /mnt/orca-work
  sudo chown "$(id -u):$(id -g)" /mnt/orca-work
)
```

Mount the **existing** transfer and backup filesystems through your normal removable-media workflow.
Set their actual mount paths in the kit's **`templates/offline-root/orca.conf`** if different from the
defaults. The current user needs write access. Working, transfer and backup storage must be on three
different physical devices; partitions on one disk do not qualify.

Disconnect Ethernet, disable Wi-Fi/Bluetooth networking and remove other network paths. Confirm on
**the offline computer**:

```bash
ip -br link
ip -4 route show table all default
ip -6 route show table all default
```

**Expected:** only loopback is up; no default routes. The wrapper enforces these checks before root
changes. Physical custody also excludes a connected hypervisor or other online administrator.

## 5. Prepare and create the root

From **the copied kit root on the offline computer**:

```bash
bash scripts/offline-root.sh prepare
```

**Expected:** pinned tools and rendered policy on encrypted working storage; no key or certificate.
Repeating `prepare` verifies and preserves the existing accepted instance. clca does not support concurrent writers;
the wrapper locks each complete operation on this instance. [1]

For **a new, explicitly approved root only**, from **the same kit root**:

```bash
bash scripts/offline-root.sh create
```

Type the exact confirmation shown and answer native OpenSSL/clca prompts. Independently retain the
new strong passphrase. A repeated creation, existing key or partial initialization is refused.
Recover original state after a failed creation; do not delete it and try again.

**Expected:** encrypted RSA-4096 key, root certificate, CA database and policy. Independently record
the printed root SHA256, then copy it to **`ORCA_ROOT_FINGERPRINT`** in the kit configuration.
Later signing and CRL operations require this same identity.

## 6. Export public files and back up

From **the copied kit root on the offline computer**:

```bash
bash scripts/offline-root.sh crl
bash scripts/offline-root.sh backup
```

**Expected:** a new public return directory with `root.pem`, `root.cer`, `root.crl`, `root-crl.pem`
and checksums; a separate encrypted `.tar.gz.age` archive on backup media. Only public objects enter
transfer media. Native clca's backup is not encrypted; the wrapper creates it temporarily on encrypted
working storage and encrypts it before export. [1]

With the recovery custodian, [verify a restored copy](../../../05-operations/03-cryptography/offline-root.md#restore-and-test-a-copy)
before accepting custody. Schedule the next ceremony within 60 days for the 90-day CRL policy.
Unmount/lock working storage, secure the backup and take the root offline again.

**First visit complete:** return to [Stage 2 Step 2](../README.md#step-2-initialize-the-issuer-inputs).
Keep the public files until Step 12 publishes them. No subordinate CSR exists yet.

<a id="sign-a-subordinate"></a>
<a id="step-2-authorize-subordinate-signing"></a>

## Second visit: sign a subordinate

1. On **the protected controller**, in the directory holding the returned CSR, inspect it and
   calculate its public-key fingerprint:

   ```bash
   openssl req -in ca-1-issuer.csr -verify -noout -subject
   openssl req -in ca-1-issuer.csr -pubkey -noout | openssl pkey -pubin -outform DER | sha256sum
   ```

   For FreeIPA use its actual CSR filename. Approve subject/key through an independent record.
   Put only the CSR on public transfer media.

2. On **the offline computer**, reopen the original kit and mounted custody media. From **the kit root**:

   ```bash
   bash scripts/offline-root.sh status
   ```

   Compare the original root fingerprint with the independent record; require no incomplete
   operation. Retain that value in `ORCA_ROOT_FINGERPRINT`. Do not run `create` again.

3. From **the kit root on the offline computer**, select the received CSR and approved hash:

   ```bash
   read -r -p 'CSR on transfer media (example /mnt/orca-transfer/ca-1-issuer.csr): ' ORCA_REQUEST
   read -r -p 'Approved public-key SHA256 (64 hex digits from requester record): ' ORCA_REQUEST_KEY
   bash scripts/offline-root.sh sign "$ORCA_REQUEST" "$ORCA_REQUEST_KEY"
   ```

   Review the displayed subject/key/root and enter the exact approval requested.
   **Expected:** a subordinate with `CA:true`, `pathlen:0`, the approved key and a valid chain,
   returned as `issuer.pem` with public root objects. A repeated CSR is refused.

4. Run **action 6** to refresh the CRL and back up the changed history. Return the signed `issuer.pem`
   and matching root objects to [Stage 2 Step 12](../README.md#step-12-install-public-certificates-and-start-the-prepared-backend),
   or [FreeIPA completion](../../stage-05-identity/procedures/freeipa.md#step-3-complete-the-primary-and-replica).
   Use the signing command's return directory for `issuer.pem`; `crl` prints a later root-only
   directory. Preserve both public results, never the root key, passphrase or CA database.

<a id="step-3-publish-and-close-the-ceremony"></a>

The publication URL receives signed public objects only. Independently distribute the accepted
root fingerprint/trust anchor, then verify certificate/CRL retrieval before accepting issuance.
Later ceremonies and host/tool updates follow [ORCA operations](../../../05-operations/03-cryptography/offline-root.md).

## References

Source checked 2026-11-17.

1. [Native clca lifecycle, offline use, profiles and backup](https://github.com/openxpki/clca/blob/d560135cf4bbdc1916fa4c5545012085b96d4a21/README.md).
