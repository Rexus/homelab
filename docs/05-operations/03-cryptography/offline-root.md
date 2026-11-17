# Operate the Offline Root CA (ORCA)

ORCA is the separately controlled root in the [trust deployment figure](../../03-deployment/stage-02-trust/README.md#figure-1-offline-root-and-online-issuer).
Keep its original kit, public configuration, root fingerprint and current encrypted CA-state backup.
Normal `ca-1` issuance does not require ORCA to be running.

**Configuration:** `templates/offline-root/orca.conf` in the retained ceremony kit.
**Commands:** `bash scripts/offline-root.sh <action>`, from **that kit root on the offline computer**.
Online Tier 0 inventory and `foundation` never deploy or start the root.

## Contents

- [Open a routine ceremony](#open-a-routine-ceremony)
- [Sign an issuer](#sign-an-issuer)
- [Refresh and publish the root CRL](#refresh-and-publish-the-root-crl)
- [Restore and test a copy](#restore-and-test-a-copy)
- [Update the offline computer or tools](#update-the-offline-computer-or-tools)
- [An operation failed](#an-operation-failed)

## Open a routine ceremony

1. Boot the separate trusted offline computer. Disconnect/disable its network interfaces.
2. Unlock the original encrypted working media and mount the separate transfer/backup devices
   at the paths in `orca.conf`. For the default working-media layout, on **the offline computer**:

   ```bash
   read -r -p 'Existing encrypted working partition (stable /dev/disk/by-id/... path): ' ORCA_WORK_PARTITION
   sudo cryptsetup open "$ORCA_WORK_PARTITION" orca-work
   sudo mount /dev/mapper/orca-work /mnt/orca-work
   ```

   Skip already-open/mounted devices; never run `luksFormat`, `mkfs` or `create` here.
3. From **the original kit root**:

   ```bash
   bash scripts/offline-root.sh status
   bash scripts/offline-root.sh prepare
   ```

   Require the independently recorded root fingerprint, no pending operation and unchanged
   tools/policy. `prepare` checks the existing installation; it creates no root key.

## Sign an issuer

Use [the second-visit actions](../../03-deployment/stage-02-trust/procedures/offline-root.md#sign-a-subordinate)
for `ca-1`, a separate FreeIPA sibling CA, or a reviewed issuer renewal. Bring the CSR and an
independently approved subject/public-key record. A new signing operation does not create a new root.

The wrapper signs only the configured subordinate profile. If its intended lifetime would exceed
the remaining root lifetime, stop for an approved renewal/rollover plan; do not replace the root
or silently change retained policy to make the request pass.

## Refresh and publish the root CRL

1. Open a routine ceremony. From **the retained kit root**:

   ```bash
   bash scripts/offline-root.sh crl
   bash scripts/offline-root.sh backup
   ```

   Retain the printed public return directory, new encrypted backup and its checksum.
2. On **the protected controller**, copy the new public `root.crl` to the existing source path
   selected by `openxpki_public_root_files.root.crl` in Tier 0 `ansible/group_vars/issuer.yml`.
   Keep `root.cer`, root/issuer fingerprints and the original issuer certificate unchanged.
   From **`<prefix>-tier-0/`**:

   ```bash
   bash scripts/deploy.sh foundation --ansible-only --playbook deployment/openxpki-certificates.yml --ansible-vars ansible/group_vars/issuer.yml
   ```

3. Verify the published CRL signature and `nextUpdate` from an intended consumer; keep an independent
   reminder before expiry. For the default 90-day CRL, perform the ceremony within 60 days.
   Confirm encrypted backup recovery, unmount/lock the working volume and secure the devices.

## Restore and test a copy

Use the latest accepted encrypted archive, the original kit/configuration and separately retained
age identity. A rehearsal runs on a **separate offline computer** with separate encrypted test
working storage mounted at the original configured paths. It never becomes a second live writer.

On **the isolated recovery computer**, select the original backup and empty restore directory:

```bash
(
  set -euo pipefail
  umask 077
  read -r -p 'Encrypted archive (example /mnt/orca-backup/orca-...tar.gz.age): ' ORCA_ARCHIVE
  read -r -p 'Recovery identity file (separately held .agekey): ' ORCA_IDENTITY
  read -r -p 'Empty instance path from orca.conf (example /mnt/orca-work/root): ' ORCA_RESTORE
  test ! -e "$ORCA_RESTORE"
  ORCA_RESTORE_DEVICE=$(findmnt -n -o SOURCE --target "$(dirname "$ORCA_RESTORE")")
  lsblk -s -n -r -o TYPE -- "$ORCA_RESTORE_DEVICE" | grep -qx crypt
  ORCA_ARCHIVE_HASH=$(awk '{print $1}' "$ORCA_ARCHIVE.sha256")
  printf '%s  %s\n' "$ORCA_ARCHIVE_HASH" "$ORCA_ARCHIVE" | sha256sum --check --strict -
  mkdir -m 0700 "$ORCA_RESTORE"
  age --decrypt --identity "$ORCA_IDENTITY" "$ORCA_ARCHIVE" |
    tar -xzf - -C "$ORCA_RESTORE"
)
```

Require the archive checksum and encrypted destination before restoring. The archive contains the
key, configuration, CA database, counters and ceremony records; do not extract it onto transfer media.
The original tool kit provides the same pinned clca payload. With that kit on this offline computer:

```bash
bash scripts/offline-root.sh prepare
bash scripts/offline-root.sh status
bash scripts/offline-root.sh crl
```

Require the original independently recorded fingerprint, successful policy/tool checks and a
verifiable new CRL using the retained passphrase. **For a rehearsal, never publish its return files**;
keep them isolated and discard the test copy under your custody policy. Retain only the real
instance's current history. For actual
recovery, declare the recovered history authoritative, back it up and retire the former instance.

## Update the offline computer or tools

Keep root storage and its recovery identity detached while preparing or updating a replacement OS.
Install the [declared native dependencies](../../03-deployment/stage-02-trust/procedures/offline-root.md#1-prepare-tools-and-independent-recovery)
through the accepted package route, disconnect networking, then rehearse restoration before using
the original state. An online OS update with root state attached is not this workflow.

The current kit intentionally pins clca and the root policy. A different tool revision requires a
reviewed kit change and disposable restore/signing tests. Do not overwrite accepted tools or edit
the binding/checksum files to bypass a mismatch. Secure Boot/TPM changes follow the
[boot-maintenance guide](../01-hosting/maintenance.md#boot-maintenance) with independent recovery;
the root's passphrase/media custody remains necessary.

## An operation failed

Run `status`, retain the working media and capture the error without secrets. An incomplete
initialization/signing marker blocks later mutation. Inspect the native CA index, certificate
history and backups with the custodians before deciding whether to recover the latest history.
Never remove a key, database, pending marker or binding merely to make `create` run again.
