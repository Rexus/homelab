# Restore FreeIPA and CA identity

Recover a CA-enabled FreeIPA server with its original realm, host identity, CA keys and directory
history before recreating replicas. **Prerequisites:** independent DNS/time/console access, a protected
full native `ipa-backup` set or qualified stopped-VM backup, original FQDN, matching OS/FreeIPA packages,
Directory Manager credential and backup-decryption material. Preserve the external identity-CA chain.

## Contents

- [Select the recovery branch](#select-the-recovery-branch)
- [Restore a full native backup](#restore-a-full-native-backup)
- [Validate identity and CA](#validate-identity-and-ca)
- [References](#references)

## Select the recovery branch

| Situation | Action |
| --- | --- |
| Healthy surviving directory and CA | Prefer native replica replacement from the surviving authority; review topology/renewal/CRL ownership first [1] |
| Total loss or corruption propagated to all replicas | Fence all old authorities; restore one known-good CA-enabled server in isolation |
| Qualified stopped-VM copy | Restore to a new VM ID/disks with disconnected production NICs; follow [VM restore validation](../compute/backup-restore.md) |
| Only LDAP/data-only backup | Treat as incomplete for rebuilding the host/CA; recover the missing full set or use a surviving CA authority |
| OpenXPKI infrastructure issuer | Use the existing [guarded issuer recovery recipe](../cryptography/issuer-recovery.md) |
| Offline root or USB/HSM keys | Follow [root custody](../../deployment/stage-3-trust/procedures/offline-root.md), [issuer custody](../cryptography/certificate-authority.md) and the selected device's independent recovery procedure |

The FreeIPA CA is a sibling of the infrastructure issuer in the reference design. Reinstalling a
fresh realm or signing a new sibling certificate does not restore the original identity CA/history.
Do not run the ordinary [identity deployment](../../deployment/stage-5-identity/procedures/freeipa.md)
CSR/key-generation path as a restoration step.

Native full backups include a header recording hostname, software version and services, and are
host/version specific. Schedule full backups during an approved service interruption using
`ipa-backup`; copy the complete resulting directory off-host under encrypted independent custody.
The control backup role does not schedule FreeIPA backups or copy live LDAP/Dogtag database files. [2]

## Restore a full native backup

1. Preserve the original hosts/disks. Prepare a **new isolated replacement VM**, original FQDN,
   matching packages/roles and working independent name resolution/time. Do not enroll a fresh realm.
   Block all old replicas and clients until the selected authority is accepted.
2. Extract the full backup onto private encrypted recovery storage. Compare the header and all
   content digests to independent custody records. Check full type, original FQDN, package version
   and CA role; a data-only backup cannot satisfy this path. Follow the installed `ipa-restore(1)`
   for the matching release; it restores system files as well as service data. [2][3]
3. On that new VM, as root, run the following guarded operation. The exclusive attempt directory
   prevents retries into a partially restored host; build another replacement after a failed attempt.

   ```bash
   set -euo pipefail
   umask 077
   : "${IPA_FULL_BACKUP:?Set the extracted full native backup directory}"
   : "${IPA_ORIGINAL_FQDN:?From the original backup header}"
   test "${RECOVERY_ISOLATED:-}" = yes
   test "${RECOVERY_APPROVE_IPA_RESTORE:-}" = "$IPA_ORIGINAL_FQDN"
   test "$(hostname -f)" = "$IPA_ORIGINAL_FQDN"
   test -f "$IPA_FULL_BACKUP/header"
   test ! -e /etc/ipa/default.conf
   instances=$(find /var/lib/dirsrv -mindepth 1 -maxdepth 1 -name 'slapd-*' -print -quit)
   test -z "$instances"
   mkdir -m 0700 /root/ipa-recovery-attempt
   ipa-restore "$IPA_FULL_BACKUP"
   ```

   Supply Directory Manager/decryption credentials interactively when prompted, never on a shared
   command line. If package installation did not create `/var/lib/dirsrv`, create that empty directory
   as part of VM preparation; the guard deliberately fails on missing/unreadable paths. Do not delete
   an existing IPA configuration, directory database or attempt marker to force these checks to pass.

## Validate identity and CA

Run `ipactl status`, then authenticate through an independent recovery credential and run `ipa ping`.
Check LDAP objects, Kerberos, DNS records and both directory/CA state against the chosen backup time.
Verify the original CA certificate/key identity, chain to the offline root, issuance, CRL publication,
renewal authority and revocation visibility before allowing clients. Confirm an existing certificate
and a revoked certificate behave as expected; service startup alone is insufficient.

Recreate other replicas from the accepted authority with explicit CA replication. Do not reconnect
stale directory databases blindly; review/reinitialize replication according to the product's
topology recovery procedure. Test authentication and CA operation with either replica unavailable,
then reconnect Keycloak and other consumers. Record backup identity, package/CA fingerprints,
replication decisions, acceptance evidence and observed RPO/RTO. Take a new full independent copy.

For issuer/root recovery, preserve issuance/revocation history and signing identities through the
linked authoritative guides. Never run two recovered copies of the same issuing authority online.

## References

1. [FreeIPA server-loss and topology recovery](https://www.freeipa.org/page/Backup_and_Restore)
2. [FreeIPA native backup manual](https://raw.githubusercontent.com/freeipa/freeipa/master/install/tools/man/ipa-backup.1)
3. [FreeIPA native restore manual](https://raw.githubusercontent.com/freeipa/freeipa/master/install/tools/man/ipa-restore.1)
