# Extract control recovery files

Run on an independent isolated recovery workstation, using verified restic and Python 3.9+.
Obtain the repository, password, full known-good snapshot ID and expected Vault/manifest digests
from independently protected custody. Preserve the incident copies before extraction.

## Contents

- [Extract into a new target](#extract-into-a-new-target)
- [Verify and hand off](#verify-and-hand-off)
- [References](#references)

## Extract into a new target

The installed helper is also available at
`tier-0/ansible/roles/control_backup/files/restore_files.py` in this source repository. Keep its
`control_backup_io.py` sibling beside it when using an offline recovery kit.
Use independent local credentials, not a Vault/SSO fetch from the unavailable platform:

```bash
set -euo pipefail
umask 077
: "${RESTIC_REPOSITORY:?Set the independent repository}"
: "${RESTIC_PASSWORD_FILE:?Set the independently held password file}"
: "${RECOVERY_SNAPSHOT:?Set the full known-good 64-character restic ID}"
: "${RECOVERY_TARGET:?Set a new absolute directory under an existing private parent}"
restic snapshots --tag control-recovery --json
python3 /usr/local/lib/control-backup/restore_files.py \
  --snapshot "$RECOVERY_SNAPSHOT" --target "$RECOVERY_TARGET" --approve-clean-target
```

The helper creates the target exclusively, rejects `latest`, existing paths and symlink parents,
runs `restic check --read-data`, then native `restic restore --verify`. It never writes into a live
application, state root or source repository. A failed attempt remains available for diagnosis;
select another new target after investigating. Restic recreates original absolute paths below
the target, so inspect the resulting tree before product use. [1]

For a bounded dataset, inspect `restic ls "$RECOVERY_SNAPSHOT"` and pass `--subfolder /exact/tree/path`
to extract only that subtree into another new target. This is useful for media or a state directory;
use snapshot-tree paths as displayed by restic, including the drive prefix for Windows snapshots.

## Verify and hand off

1. Compare repository identity and restic ID with the independently recorded receipt. Do not take
   an incident-modified local `last-success.json` as the only source of truth.
2. Locate the selected set's `manifest.json` and `vault.snap` in the restored tree. Verify both against
   the expected independently held digests, then compare the snapshot to `vault_sha256` in the manifest:

   ```bash
   : "${RESTORED_SET:?Set the extracted timestamped set directory}"
   : "${EXPECTED_MANIFEST_SHA256:?From independent custody}"
   : "${EXPECTED_VAULT_SHA256:?From independent custody}"
   printf '%s  %s\n' "$EXPECTED_MANIFEST_SHA256" "$RESTORED_SET/manifest.json" | sha256sum -c -
   printf '%s  %s\n' "$EXPECTED_VAULT_SHA256" "$RESTORED_SET/vault.snap" | sha256sum -c -
   vault operator raft snapshot inspect "$RESTORED_SET/vault.snap"
   ```

3. Reconcile the manifest input list with the actual recovery tree, including the optional media
   selection. It records selected paths, not a complete inventory of all critical platform data.
4. Continue with [Vault](vault.md), [original state](original-state-etcd.md), or [NetBox](netbox.md).
   Keep plaintext on encrypted recovery storage with restricted access. Never commit extracted state,
   credentials or private keys. Restic decryption/integrity does not validate product consistency.

## References

1. [Restic native restoration and verification](https://restic.readthedocs.io/en/stable/050_restore.html)
