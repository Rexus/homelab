# Issuer backup and recovery

<a id="back-up-and-restore-the-software-issuer"></a>


Recover the same signing identity with its latest issuance, revocation, workflow
and DataVault state. A VM snapshot or key copy alone is not a recovery set.

**Run from:** generated Tier 0 on the independent execution host unless stated otherwise.
**Before starting:** accepted software issuer, encrypted working storage, independent
age recovery identity, original credentials/artifacts and authorized custodians.
Hardware providers need their separate qualified device recovery procedure.

<a id="contents"></a>

## Tasks

- [How is a recovery set captured?](#capture-a-recovery-set)
- [How is an archive verified before restoration?](#how-is-an-archive-verified-before-restoration)
- [How is the issuer restored onto a clean host?](#prepare-and-restore-a-clean-target)
- [What must pass before service resumes?](#accept-recovery)
- [What happens after a failed backup or restore?](#what-happens-after-a-failed-backup-or-restore)
- [References](#references)

<a id="capture-a-recovery-set"></a>

## How is a recovery set captured?

1. On the trusted recovery system, retain the existing age private identity offline.
   For first commissioning only, create a new identity at a protected unused path: [1]

   Run on **the offline credential-custody system**.

   ```bash
   umask 077
   read -r -e -p 'New absolute offline age identity file path: ' AGE_IDENTITY
   age-keygen --output "$AGE_IDENTITY"
   ```

   Record/independently verify its public `age1...` recipient. Only that public
   recipient reaches the issuer. Do not generate a replacement for a missing key.
2. In Tier 0 **`ansible/group_vars/issuer.yml`**, edit:

   | Field | Enter |
   | --- | --- |
   | `openxpki_backup_directory` | Dedicated encrypted working path matching `/srv/NAME`, distinct from the live data mount |
   | `openxpki_backup_recipient` | Independently verified public age recipient |
   | `openxpki_backup_id` | New unique 3-64 character letters/digits/underscore/hyphen ID; never overwrite/reuse |
   | `openxpki_activate_runtime`, `openxpki_managed_cli` | `true` for the accepted running software issuer |
   | Existing binding/secrets | Original archive/hash, package set, realm, database/session/signer secrets and issuer fingerprint |

3. Reserve a maintenance window, then capture the consistent encrypted set:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/deploy.sh foundation --recipe maintenance --playbook maintenance/openxpki-backup.yml --ansible-vars ansible/group_vars/issuer.yml
   ```

   Retain the original `--env NAME` when used. The role pauses portal/CA writers,
   dumps MariaDB, encrypts the software custody/configuration set and removes
   plaintext staging before resuming services. It never overwrites a prior archive. [2]
4. Check [issuer health](certificate-authority.md#routine-controls). Transfer the
   reported `.tar.gz.age` archive and SHA256 to independent off-host retention.
   Verify decryption below before accepting the backup.

Record package artifacts, original binding/schema receipt, controller secrets,
portal TLS and recipient custody separately. The archive includes the live
configuration, software keys, identity/public state and database; it excludes
external controller TLS files, offline root and FreeIPA. The age recipient in this
recipe is classical X25519, not a post-quantum protection claim. [1]

## How is an archive verified before restoration?

On a trusted recovery system with **encrypted working storage**, outside Git:

1. Compare the archive SHA256 with the independent backup record:

   Run on **the offline recovery system with encrypted working storage**.

   ```bash
   read -r -e -p 'Encrypted issuer archive path: ' ISSUER_BACKUP
   sha256sum "$ISSUER_BACKUP"
   ```

   Stop on a mismatch or missing independent record. Preserve the only surviving copy.
2. Choose a new protected working directory; decrypt with the separately held identity: [1]

   Run on **the offline recovery system with encrypted working storage**.

   ```bash
   umask 077
   read -r -e -p 'Existing offline age identity file path: ' AGE_IDENTITY
   read -r -e -p 'New directory on encrypted recovery storage: ' RESTORE_WORK
   mkdir -m 0700 "$RESTORE_WORK" && age --decrypt --identity "$AGE_IDENTITY" --output "$RESTORE_WORK/recovery.tar.gz" "$ISSUER_BACKUP"
   tar -tvzf "$RESTORE_WORK/recovery.tar.gz"
   ```

3. Before extraction, reject absolute/traversal paths, unexpected files and links
   escaping the set. Expected contents: `configuration`, `keys`, `identity`, `public`,
   `deployment.json`, `schema-initialized`, `database.sql`, `recovery.json`.
   After review, extract into a new subdirectory and record the manifest hash:

   Run on **the offline recovery system with encrypted working storage**.

   ```bash
   mkdir -m 0700 "$RESTORE_WORK/recovery" && tar -xzf "$RESTORE_WORK/recovery.tar.gz" -C "$RESTORE_WORK/recovery"
   sha256sum "$RESTORE_WORK/recovery/recovery.json"
   ```

   Preserve permissions and independently record that manifest SHA256. This inspection
   does not prove a complete restore. Keep plaintext only under encrypted-volume custody.

<a id="prepare-and-restore-a-clean-target"></a>

## How is the issuer restored onto a clean host?

1. Fence the old/failed issuer before any activation. Use an isolated Tier 0 recovery
   working copy with the intended target in `ansible/inventory/hosts.yml` and
   `platform_host_ips.ca-1` in `ansible/group_vars/foundation.yml`. Retain the other
   host entries; do not run Terraform or the identity recipe against this recovery map.
2. Prepare the exact approved Debian runtime and dedicated data/mysql mounts using
   [issuer installation](../../03-deployment/stage-3-trust/procedures/issuer.md#step-2-install-the-runtime).
   Initialize the empty schema once; keep activation **false**. Create no issuer key,
   token or certificate and preserve the original immutable bundle/binding. [3]
   The normal installer prepares storage; the restore recipe only checks existing mounts.
   Select the new isolated target's device and filesystem explicitly. Leave the optional UUID pin
   empty only when commissioning that genuinely new disk; retain it when recovering the original volume.
   Provide approved storage encryption separately; filesystem preparation does not encrypt the disk.
3. Transfer the verified decrypted set to **`/srv/pki-restore/recovery` on the isolated
   target**, outside its live data mount, with root-only `0700` parent directories.
   Keep the verified source and independent encrypted archive intact.
4. In that recovery copy's **`ansible/group_vars/issuer.yml`**, restore the original
   controller secrets/binding and set:

   ```yaml
   openxpki_restore_approved: true
   openxpki_restore_directory: /srv/pki-restore/recovery
   openxpki_restore_manifest_sha256: REPLACE_WITH_INDEPENDENTLY_RECORDED_RECOVERY_JSON_SHA256
   openxpki_managed_cli: true
   openxpki_activate_runtime: false
   openxpki_initialize_database: false
   ```

5. Run only the restore recipe:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/deploy.sh foundation --recipe maintenance --playbook maintenance/openxpki-restore.yml --ansible-vars ansible/group_vars/issuer.yml
   ```

   It rejects existing signing/history, prior attempts and mismatched secrets,
   manifest or key identity. It imports the database and restores key/public state;
   **application writers remain stopped**. Do not import a new token afterward.

<a id="accept-recovery"></a>

## What must pass before service resumes?

1. Compare the recovered fingerprint, token aliases, latest issued/revoked serials,
   public objects and DataVault readability with independent records.
2. Return restore approval to `false`; leave schema initialization false. After
   authorized identity/history acceptance, set `openxpki_activate_runtime: true`
   and run the normal issuer recipe against the same isolated target:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/deploy.sh foundation --ansible-only --playbook deployment/openxpki.yml --ansible-vars ansible/group_vars/issuer.yml
   ```

3. Verify [CA acceptance](certificate-authority.md#acceptance-evidence), audit and
   independent alerts with Tier 1/2, SSO and Vault unavailable. Measure RPO/RTO.
   Allow only this accepted writer to resume service; preserve any new history.
4. Remove plaintext staging under the encrypted-volume policy after acceptance.
   Retain encrypted recovery copies and separately held keys.

## What happens after a failed backup or restore?

- **Backup:** check service resumption and logs, quarantine incomplete output,
  verify the last accepted off-host copy, then retry with a new backup ID.
- **Restore:** stop. Preserve `restore-attempt.json` and diagnostics; investigate
  and use another clean target. Never delete the receipt/history to force a rerun.
- **Rollback:** return to an old writer only after proving no newer issuance or
  revocation history would be lost. Otherwise recover the latest authoritative set;
  never start both copies or use an older VM snapshot as a shortcut.
- Rehearse after relevant package/schema/provider changes. Static checks and a
  successful decrypt do not establish operational recovery.

## References

Native interfaces checked 2026-11-08.

1. [age identity generation, encryption and decryption](https://github.com/FiloSottile/age).
2. [Native MariaDB logical dump/import module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/mariadb/mariadb_db_module.html).
3. [OpenXPKI native state, token and DataVault requirements](https://github.com/openxpki/openxpki-config/blob/community/QUICKSTART.md).
