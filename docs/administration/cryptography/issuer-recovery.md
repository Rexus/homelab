# Back up and restore the software issuer

Preserve the signing identity **and** its latest database, revocations, workflows,
DataVault material and immutable runtime binding. A VM snapshot or private-key
copy alone is not a qualified recovery set.

**Prerequisites:** accepted software issuer, prepared encrypted backup working
volume, independent offline age recipient key, authorized custodians and an
isolated clean replacement host. Never rehearse against the only surviving copy.

## Contents

- [Capture a recovery set](#capture-a-recovery-set)
- [Prepare and restore a clean target](#prepare-and-restore-a-clean-target)
- [Accept recovery](#accept-recovery)
- [References](#references)

## Capture a recovery set

Generate an age recipient/key pair on the trusted recovery system using
`age-keygen`. Only the public `age1...` recipient reaches the issuer.
Keep the private identity offline and separately custodied. The current recipient
format is classical X25519 key wrapping, not a post-quantum backup claim. [1]

Add these values to protected issuer inputs:

| Input | Meaning |
| --- | --- |
| `openxpki_backup_directory` | Dedicated protected path such as /srv/pki-backups; prepare encrypted storage first |
| `openxpki_backup_recipient` | Independently verified public age recipient |
| `openxpki_backup_id` | Unique recovery identifier, never reused |
| Existing issuer binding/secrets | Same active runtime configuration, package pins and expected issuer fingerprint |

```bash
bash scripts/deploy.sh foundation --recipe maintenance --playbook maintenance/openxpki-backup.yml \
  --ansible-vars ansible/group_vars/issuer.yml
```

The recipe validates the binding/issuer, pauses application writers, takes a native
logical MariaDB dump, archives software custody/configuration state and encrypts
it. Plaintext staging is removed before services resume. Do not assume file deletion
securely erases an SSD: use encrypted working storage. Allow a maintenance window.

Transfer the encrypted archive and recorded SHA-256 to independent off-host storage.
Record its manifest hash after trusted decryption, retention, recovery recipient,
issuer fingerprint, package artifacts, controller secrets and portal TLS recovery.
The issuer archive does not include the offline root, FreeIPA or controller's
external TLS files. Back up those under their own recovery procedures.
An interrupted encryption can leave an incomplete output: verify it before
retention; use a new backup ID for a retry, never overwrite an accepted set.

## Prepare and restore a clean target

1. Fence the failed/old issuer. No second active writer may use this identity.
   Build a clean isolated host with the exact approved packages/configuration and
   prepared encrypted data/mysql mounts. Use the ordinary install with explicit
   first schema initialization and activation **false**. Do not create a new
   issuer key, import tokens or issue any certificate.
2. On a trusted recovery system verify the encrypted archive hash against the
   independently retained record. Decrypt with `age --decrypt --identity` to
   protected encrypted working storage. Check the archive listing before extracting:
   only the documented configuration, keys, identity, public objects, binding,
   schema receipt, `database.sql` and `recovery.json` belong in the set.
   Reject absolute/traversal paths, links escaping the tree or unexpected payloads.
3. Place the verified decrypted set at a protected replacement-host path such as
   `/srv/pki-restore/recovery`, outside the live data mount. Keep parent
   directories root-only, 0700. Preserve source permissions.
4. Restore the exact controller database/session/signer secrets and approved archive.
   Set `openxpki_restore_approved: true`, `openxpki_restore_directory`,
   independently recorded `openxpki_restore_manifest_sha256`, original issuer
   fingerprint and `openxpki_managed_cli: true`. Keep activation false.

```bash
bash scripts/deploy.sh foundation --recipe maintenance --playbook maintenance/openxpki-restore.yml \
  --ansible-vars ansible/group_vars/issuer.yml
```

The recipe rejects existing signing material/history, prior restore attempts,
changed bindings, wrong manifest identity and a mismatched recovered private key.
It imports the logical database through the native module and restores key/public
state, leaving application writers stopped. The already-installed immutable bundle
provides matching DataVault/authentication configuration.

A failure is not permission to delete `restore-attempt.json`: preserve diagnostics
and investigate. Rehearse again on another clean target. After success, remove
plaintext staging under the encrypted-volume policy and return restore approval
and schema initialization to false.

## Accept recovery

Before ordinary activation, compare the recovered identity, latest issuance and
revocation records, token aliases and expected public objects with independent
records. Then use explicit normal activation, never fresh token import.

Prove portal approval, same-key signing, CRL freshness/revoked serials, DataVault
readability, protected audit delivery and independent alerts with later tiers,
normal SSO and Vault unavailable. Verify new issuance cannot reuse/regress serial
history. Measure recovery time and recovered event range against RPO/RTO.
Only one restored issuer can return to service.

Test this before production and after package/schema/provider changes. These
recipes are recovery mechanisms; passing static or controller-only tests does not
establish a successful live restore.

## References

Sources checked 2026-10-18.

1. [age encryption and recipient/key handling](https://github.com/FiloSottile/age)
2. [MariaDB logical backup/import module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/mariadb/mariadb_db_module.html)
3. [OpenXPKI DataVault and native state requirements](https://github.com/openxpki/openxpki-config/blob/community/QUICKSTART.md)
