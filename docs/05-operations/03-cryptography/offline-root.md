# Operate the Offline Root CA (ORCA)

ORCA is the separately controlled root in the [trust deployment figure](../../03-deployment/stage-02-trust/README.md#figure-1-offline-root-and-online-issuer).
Keep its original kit, public configuration, root fingerprint and current encrypted CA-state backup.
Normal `ca-1` issuance does not require ORCA to be running.

**Configuration:** `templates/offline-root/orca.conf` in the retained ceremony kit.
**Commands:** `bash scripts/offline-root.sh <action>`, from **that kit root on the offline computer**.
Online Tier 0 inventory and `foundation` never run root signing. The optional
[ceremony environment](../../03-deployment/stage-02-trust/procedures/ceremony-environment.md)
provisions a separate, initially stopped live runtime; root custody remains on independent media.

## Contents

- [Open a routine ceremony](#open-a-routine-ceremony)
- [Sign an issuer](#sign-an-issuer)
- [Refresh and publish the root CRL](#refresh-and-publish-the-root-crl)
- [Restore and test a copy](#restore-and-test-a-copy)
- [Update the offline computer or tools](#update-the-offline-computer-or-tools)
- [Can the ceremony run automatically?](#can-the-ceremony-run-automatically)
- [Alarm when a ceremony or publication is missed](#alarm-when-a-ceremony-or-publication-is-missed)
- [An operation failed](#an-operation-failed)

## Open a routine ceremony

1. Boot the accepted offline computer or its separate NIC-less live runtime. Verify the approved
   image checksum and correct UTC date/time; disconnect/disable physical network interfaces.
2. Unlock the original encrypted working media and mount the separate transfer/backup devices
   at the paths in `orca.conf`. For the default working-media layout, on **the offline computer**:

   ```bash
   read -r -p 'Existing encrypted working partition (stable /dev/disk/by-id/... path): ' ORCA_WORK_PARTITION
   sudo cryptsetup open "$ORCA_WORK_PARTITION" orca-work
   sudo mount /dev/mapper/orca-work /mnt/orca-work
   ```

   Skip already-open/mounted devices; never run `luksFormat`, `mkfs` or `create` here.
   For an enrolled YubiKey/FIDO2 device, use the [local token-unlock steps](../../03-deployment/stage-02-trust/procedures/orca-disk-unlock.md)
   instead of `cryptsetup open` above. That procedure also covers passphrase fallback and lost tokens.
3. From **the original kit root**:

   For a replacement live session, first restore the independently retained public `orca.conf`
   and its accepted checksum using the [ceremony guide](../../03-deployment/stage-02-trust/procedures/ceremony-environment.md#8-perform-the-selected-ceremony-locally).
   The first-visit ISO may still contain an empty root fingerprint; its temporary overlay does not
   retain the accepted fingerprint after shutdown. Restore only public configuration here, not keys.

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

ORCA signs `root.crl`; `ca-1` only serves that public file. Its own `issuer.crl` is signed by the
online issuer and covers a different set of certificates. See [publication locations and availability](certificate-authority.md#where-are-root-and-issuer-crls-served).
The default 90-day root CRL requires a ceremony within 60 days; a yearly visit does not satisfy
that policy. Publication replicas cannot extend a CRL's signed expiry.

If the retained kit predates `maintain`, refresh the upstream/Tier 0 code and build a new public
kit with the **same** accepted `orca.conf` and clca pin. Verify its manifest through the
[first-visit transfer checks](../../03-deployment/stage-02-trust/procedures/offline-root.md#3-build-and-transfer-the-pinned-kit).
Do not recreate the root or change its binding. The existing separate `crl` and `backup` actions
remain supported.

1. Open a routine ceremony. From **the retained kit root**:

   ```bash
   bash scripts/offline-root.sh maintain
   ```

   Enter the root passphrase locally when clca requests it. The command checks the retained root,
   renews and verifies the CRL, creates the encrypted backup and writes `ceremony-receipt.txt` in
   the printed public return directory. The receipt records CRL dates and backup checksums;
   publication and an independent recovery test remain separate actions.

   To request shutdown **only after successful completion**, run the alternative below from
   **a root shell on the offline ceremony system**, using the same retained kit:

   ```bash
   bash scripts/offline-root.sh maintain --poweroff
   ```

   This requires systemd. Failure leaves the system running; inspect the error before retrying.
   After shutdown, return custody media to storage and use only the public transfer device on
   the connected controller. Retain the encrypted backup and receipt independently.
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
keep them isolated and discard the test copy under the custody policy. Retain only the real
instance's current history. For actual
recovery, declare the recovered history authoritative, back it up and retire the former instance.

## Update the offline computer or tools

The ISO is reusable between ceremonies; a new signature does not require a new image. The
[live-session figure](../../03-deployment/stage-02-trust/procedures/ceremony-environment.md#understand-the-live-image)
shows which state survives. Tool interfaces, hardware libraries and encryption support can change
over time, so replacement images must pass recovery/signing tests against a disposable copy.

Keep root storage, devices and recovery secrets detached while preparing a replacement OS.
For the live-image path, follow [build and replace the ceremony image](../../03-deployment/stage-02-trust/procedures/ceremony-environment.md).
Build with the accepted package sources, record the new ISO checksum, and rehearse with a disposable
CA and separate encrypted test media before booting against original root state. Keep the previously
accepted ISO until recovery is accepted. Replacing the OS never resets the root database or counters.

For an existing physical installation, install the
[declared native dependencies](../../03-deployment/stage-02-trust/procedures/offline-root.md#1-prepare-tools-and-independent-recovery)
while custody is detached, disconnect networking, then rehearse restoration. Do not download updates
inside an active root ceremony. The live runtime's writes are temporary; update its build inputs
and rebuild the image instead of expecting an in-session package update to persist.

The current kit intentionally pins clca and the root policy. A different tool revision requires a
reviewed kit change and disposable restore/signing tests. Do not overwrite accepted tools or edit
the binding/checksum files to bypass a mismatch. Secure Boot/TPM changes follow the
[boot-maintenance guide](../01-hosting/maintenance.md#boot-maintenance) with independent recovery;
the root's passphrase/media custody remains necessary.

## Can the ceremony run automatically?

Automate public image builds, expiry reminders and the local `maintain` sequence. The optional
[single-window wake timer](../../03-deployment/foundation/proxmox/api-access.md#5-optionally-schedule-one-approved-activation-window)
starts the selected VM using only the power identity. It does not catch up after a missed window;
an operator selects another attended time. A custodian still checks the accepted runtime and its clock,
unlocks the original encrypted media and supplies the
root passphrase. The command neither boots another machine nor unlocks storage. No root credentials
are stored in Terraform, Ansible, bootstrap, the ISO or a scheduled task.

Keep the two operations separate:

| Operation | Connectivity | Root state and recovery secrets |
| --- | --- | --- |
| Build/update and test the public operating image | Accepted package route | Detached; use disposable state for rehearsal |
| Renew the root CRL, back up and shut down | Offline | Original media unlocked locally for this ceremony |

An unattended job that can start, unlock and use the root carries signing authority wherever its
unlock credentials live. That is a different custody design. This workflow deliberately retains the
custodian's local unlock, while automating repeatable work afterward. `--poweroff` is success-only;
do not schedule an independent forced stop that could interrupt signing or backup.

After a successful ceremony, select the next attended window before the accepted deadline, if using
scheduled activation. Keep the public-CRL watchdog running continuously even when no wake is scheduled.

The default CRL lasts 90 days; retain the 60-day ceremony reminder. An annual visit needs a reviewed
CRL policy and emergency revocation route, not just a yearly power-on schedule. `nextUpdate` is the
deadline for the next CRL. [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280.html#section-5.1.2.5)

## Alarm when a ceremony or publication is missed

The checker runs on an **existing independent Linux/systemd host**, outside ORCA and the observed
Proxmox clusters. It reads public objects only. No root key, HSM PIN or Proxmox token is needed.
It can be installed now; it does not wait for the later observability stack.

### 1. Create the independent alarm destination

In the independent Healthchecks-compatible service, create a **dedicated ORCA CRL check**. Its
private ping URL identifies this one check; this is not the service's dashboard URL.
The service can be self-hosted outside the observed infrastructure.

Set the period to **1 hour** and grace to **15 minutes**. Configure the duty operator and a backup
recipient through independent channels, with repeated notifications and escalation until resolved.
Use the notification service's test button to verify delivery to both recipients. Acknowledgment
records responsibility; it must not replace CRL renewal/publication or mark a stale check healthy.
Healthchecks supports both explicit failure signals and alerts for missing scheduled pings.
[Monitoring semantics](https://healthchecks.io/docs/), [failure signals](https://healthchecks.io/docs/signaling_failures/).

### 2. Select the host and public trust inputs

In **Tier 0 inventory**, put the accepted existing monitor in `infrastructure_monitoring`, reusing
its existing host entry/address. On **bootstrap**, from **`<prefix>-tier-0/`**:

```bash
bash scripts/init-local-files.sh --setup orca-crl-watch
```

Edit **`ansible/group_vars/orca_crl_watch.yml`**:

| Field | Value |
| --- | --- |
| `orca_crl_watch_outside_observed_clusters` | `true` after selecting the physically independent monitor |
| `orca_crl_watch_crl_url` | The accepted `ORCA_PUBLICATION_URL` followed by `/root.crl` |
| `orca_crl_watch_root_certificate_src` | Accepted public `root.pem` on this controller, e.g. `artifacts/pki/root.pem` relative to Tier 0 |
| `orca_crl_watch_root_fingerprint` | The independently recorded `ORCA_ROOT_FINGERPRINT`; never trust a replacement downloaded from the CRL endpoint |
| `orca_crl_watch_success_url` | The private ping URL of the dedicated check created above |
| `orca_crl_watch_failure_url` | Leave empty for the same check's `/fail` URL; set explicitly if the endpoint needs another form |
| `orca_crl_watch_crl_proxy_url` | Empty for direct access to internal CRL publication; use a proxy only if this publication route requires it |
| `orca_crl_watch_deadman_proxy_url` | Accepted outbound proxy for the independent alarm service, if required; keep that service's hostname approved on the selected route |

Retain the example's **45-day warning**, **60-day ceremony deadline** and **7-day expiry margin**
for the default 90-day CRL. The signed CRL dates determine age; restarting or reinstalling the
checker does not reset the schedule. Keep real ping URLs in private inputs/Ansible Vault.
An explicitly selected temporary bootstrap fallback is supported, with weaker failure independence.
The recipe applies the selected package-source/proxy subset before installing dependencies; it
does not change the monitor's hostname or apply the whole guest baseline.

**Temporary bootstrap alternative:** keep the independent alarm service, set these placement fields
in the same file, and select the local inventory in action 3:

```yaml
orca_crl_watch_outside_observed_clusters: false
orca_crl_watch_bootstrap_fallback_accepted: true
orca_crl_watch_hosts: localhost
```

### 3. Install the calendar timer

From **`<prefix>-tier-0/` on bootstrap**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  ansible/playbooks/deployment/orca-crl-watch.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/orca_crl_watch.yml
```

For the **temporary local bootstrap alternative**, use `-i localhost, -c local` instead of
`-i ansible/inventory/hosts.yml` in that command. Keep the same explicit variable files.

**Expected:** `orca-crl-watch.timer` checks hourly and catches a missed calendar run after restart.
Failed runs retry every five minutes. Warning, overdue, invalid signature, clock error, rollback,
near expiry and unreachable publication send failure and suppress success pings. A stopped checker
produces a missed-ping alarm at the independent service. A successful VM start is never counted as renewal.

### 4. Test alarm delivery before relying on it

Run these from **Tier 0 on bootstrap**. They target the default `infrastructure_monitoring` group;
use the explicitly selected monitor host for the temporary fallback.

1. Trigger a check and require a healthy result in the independent service:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible infrastructure_monitoring --playbook-dir ansible \
     -i ansible/inventory/hosts.yml --become -e @ansible/group_vars/all.yml \
     -m ansible.builtin.systemd_service -a 'name=orca-crl-watch.service state=started'
   ```

2. Test the independent check's failure notification without changing production CRLs or trust.
3. For a short drill, temporarily shorten the independent check's period and grace, then pause the
   timer and its retrying service together. Require the missed-ping alarm, backup-recipient delivery
   and escalation after that grace:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible infrastructure_monitoring --playbook-dir ansible \
     -i ansible/inventory/hosts.yml --become -e @ansible/group_vars/all.yml \
     -m ansible.builtin.command -a 'systemctl stop orca-crl-watch.timer orca-crl-watch.service'
   ```

4. Restore checks and require recovery notification:

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible infrastructure_monitoring --playbook-dir ansible \
     -i ansible/inventory/hosts.yml --become -e @ansible/group_vars/all.yml \
     -m ansible.builtin.command -a 'systemctl start orca-crl-watch.timer orca-crl-watch.service'
   ```

   Restore the independent check's **1-hour period / 15-minute grace**. Record the drill and
   responsible operators in the project's deployment record. Repeat after
   notification changes. Inspect failures with `journalctl -u orca-crl-watch.service` on that host.

These controls make silent failure detectable; actual delivery and operator response still need
testing. Never disable signature checks or extend validity to clear an alarm.

## An operation failed

Run `status`, retain the working media and capture the error without secrets. An incomplete
initialization/signing marker blocks later mutation. Inspect the native CA index, certificate
history and backups with the custodians before deciding whether to recover the latest history.
Never remove a key, database, pending marker or binding merely to make `create` run again.
