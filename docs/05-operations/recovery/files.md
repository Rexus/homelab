# Extract control recovery files

**Run on:** an independent isolated recovery workstation with verified restic, Python 3.9+,
`sha256sum` and the release-matched Vault CLI for snapshot inspection.
**Prepare:** independent repository/password, full known-good snapshot ID and recorded
Vault/manifest hashes. Preserve incident copies; use encrypted private extraction storage.
**Design:** [recovery custody](../../01-architecture/24-operations/04-backup-recovery.md).

<a id="contents"></a>

## Operator tasks

- [How to extract a known recovery point into a new target?](#extract-into-a-new-target)
- [How to verify extracted files before product recovery?](#verify-and-hand-off)
- [References](#references)

<a id="extract-into-a-new-target"></a>

## How to extract a known recovery point into a new target?

Select the verified helper from the recovery kit **before extraction**. An installed recovery host uses
`/usr/local/lib/control-backup/restore_files.py`; a recovered Tier 0 checkout supplies
`ansible/roles/control_backup/files/restore_files.py`. Keep its `control_backup_io.py` sibling beside it.
Do not assume the installed path exists on a new workstation.
1. Supply the repository/password from independent custody, not a fetch from failed Vault/SSO.
2. List snapshots and compare repository identity/full snapshot ID with the retained receipt.
3. Choose a **new absolute target** under an existing canonical private parent, then run:

Run on **the independent isolated recovery workstation**.

```bash
set -euo pipefail
umask 077
read -r -p "Independent restic repository path or URI: " RESTIC_REPOSITORY
read -r -p "Independent restic password-file path: " RESTIC_PASSWORD_FILE
export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
restic cat config
restic snapshots --tag control-recovery --json
```

Compare the repository ID and full snapshot ID with the independent receipt. Stop on a mismatch.
Only after that review, run on **the same isolated workstation**:

```bash
read -r -e -p "Verified restore_files.py path from the retained kit: " RECOVERY_HELPER
test -f "$RECOVERY_HELPER" && test -f "$(dirname "$RECOVERY_HELPER")/control_backup_io.py"
read -r -p "Full known-good 64-character restic snapshot ID: " RECOVERY_SNAPSHOT
read -r -p "NEW absolute extraction target under a private parent: " RECOVERY_TARGET
python3 "$RECOVERY_HELPER" --snapshot "$RECOVERY_SNAPSHOT" --target "$RECOVERY_TARGET" --approve-clean-target
```

The helper creates the target exclusively, rejects `latest`, existing paths and symlink parents,
runs `restic check --read-data`, then native `restic restore --verify`. It never writes into a live
application, state root or source repository. A failed attempt remains available for diagnosis;
select another new target after investigating. Restic recreates original absolute paths below
the target, so inspect the resulting tree before product use. [1]

For a bounded dataset, inspect `restic ls "$RECOVERY_SNAPSHOT"` and pass `--subfolder /exact/tree/path`
to extract only that subtree into another new target. This is useful for media or a state directory;
use exact snapshot-tree paths as displayed by restic. The helper rejects relative, parent-traversal
and colon-containing subfolder selectors; use full extraction when that bounded selector cannot apply.

<a id="verify-and-hand-off"></a>

## How to verify extracted files before product recovery?

1. Compare repository identity and restic ID with the independently recorded receipt. Do not take
   an incident-modified local `last-success.json` as the only source of truth.
2. Locate the selected set's `manifest.json` and `vault.snap` in the restored tree. Verify both against
   the expected independently held digests, then compare the snapshot to `vault_sha256` in the manifest:

   Run on **the independent isolated recovery workstation**.

   ```bash
   read -r -p "Extracted timestamped set directory: " RESTORED_SET
   read -r -p "Independently recorded manifest SHA-256: " EXPECTED_MANIFEST_SHA256
   read -r -p "Independently recorded Vault SHA-256: " EXPECTED_VAULT_SHA256
   printf '%s  %s\n' "$EXPECTED_MANIFEST_SHA256" "$RESTORED_SET/manifest.json" | sha256sum -c -
   printf '%s  %s\n' "$EXPECTED_VAULT_SHA256" "$RESTORED_SET/vault.snap" | sha256sum -c -
   vault operator raft snapshot inspect "$RESTORED_SET/vault.snap"
   ```

3. Reconcile the manifest input list with the actual recovery tree, including the optional media
   selection. It records selected paths, not a complete inventory of all critical platform data.
4. Continue with [Vault](vault.md), [original state](original-state-etcd.md), or [NetBox](netbox.md).
   Keep plaintext on encrypted recovery storage with restricted access. Never commit extracted state,
   credentials or private keys. Restic decryption/integrity does not validate product consistency.

**Stop/rollback:** on any ID/hash/read-data failure, preserve the extracted target and source backup.
Do not reuse the target, overwrite incident files or fall back to `latest`. Diagnose, select another
known-good recovery point and extract into another new directory.

## References

1. [Restic native restoration and verification](https://restic.readthedocs.io/en/stable/050_restore.html)
