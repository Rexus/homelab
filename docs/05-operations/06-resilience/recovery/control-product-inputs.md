# Prepare Vault and NetBox media recovery inputs

Prepare the `products[]` entries for Tier 0 Kubernetes Vault with a Shamir seal and NetBox media.
Use the accepted-plan workflow for infrastructure, native restoration and controlled cutover.
[Recovery sequence](platform-recovery-contract.md#figure-automated-platform-recovery),
[backup capture](../backups/control-applications.md).

## Contents

- [1. Retain the original records](#1-retain-the-original-records)
- [2. Prepare private files and stopped targets](#2-prepare-private-files-and-stopped-targets)
- [3. Collect the original Shamir quorum](#3-collect-the-original-shamir-quorum)
- [4a. Add the Vault product](#4a-add-the-vault-product)
- [4b. Add the NetBox media product](#4b-add-the-netbox-media-product)
- [5. Approve and run the completed plan](#5-approve-and-run-the-completed-plan)
- [Supported variants and qualification](#supported-variants-and-qualification)

## 1. Retain the original records

Collect these records while the original services and backup host are available. Keep the catalog
readable independently of Vault, NetBox, hosted Git and Kubernetes. Pair the NetBox database and media
recovery points in that catalog.
Retain known-secret, status-response and media-file proofs with the matching accepted backup point.

| Retain | Find the original value |
| --- | --- |
| Full `backup_id` | `restic_snapshot` in the selected successful `control_backup` receipt; retain the full 64-character ID |
| `control_backup.set_path` | Exact absolute set directory in `restic ls <full-snapshot-id>`; the receipt's `set` identifies the selected capture |
| `manifest_sha256` and native Vault snapshot checksum | Receipt fields `manifest_sha256` and `vault_sha256`; verify the selected set's `manifest.json` and `vault.snap` |
| `repository_id` and password | Independently recorded `restic cat config` ID and separately protected original repository password |
| Vault cluster ID, version and threshold | Original `vault status -format=json` or verified `/v1/sys/seal-status`; retain `cluster_id`, `version`, seal type and threshold `t` |
| Vault image, members and PVCs | Accepted Helm/native render and original StatefulSet, Pod and PVC inventory; include each data/audit claim, ordinal Pod name and Raft node ID |
| Vault original token and distinct Shamir shares | Original keyholders and token custody; the token must remain valid after restoration and authorize the known-secret read and Raft configuration read |
| Controller tool versions/paths | Original release-matched Vault CLI and restic version; retain executable artifacts/checksums independently |
| NetBox media root/marker | Actual media path in the restic snapshot and its `.control-backup-source`; manifest must have `media_selected: true` |
| Known media file and filesystem identity | A retained regular file relative to that media root, its SHA-256, and the original numeric application UID/GID |
| Runtime and source recovery inputs | Original render/values, private Secrets, stopped resource templates, source keys/CA pins, source revisions and artifact locks |

Use the backup guide's authorized repository shell and listing commands to identify the exact set.
Retain its receipt and catalog independently after each accepted backup.
[Inspect the backup set](../backups/control-applications.md#list-and-restore).

For Vault, also retain a known secret's API path, JSON key sequence and canonical value checksum.
On **the independent controller with the original Vault CLI and approved authentication**, this
example prints only the checksum of the selected value. Substitute an existing retained KV item.

```bash
vault read -format=json secret/data/recovery-proof | python3 -c '
import hashlib, json, sys
value = json.load(sys.stdin)["data"]["data"]["proof"]
encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
print(hashlib.sha256(encoded).hexdigest())
'
```

Here `known_secret.path` is `secret/data/recovery-proof` and `pointer` is
`["data", "data", "proof"]`. KV v1 or another mount uses its actual API path/key sequence.
The original token and secret response stay on the controller.

## 2. Prepare private files and stopped targets

Edit **the independently retained `<prefix>-tier-1/secrets/platform-recovery.json`**. Add the selected
objects below to `products[]` and select their Tier 0 cluster in `clusters[]`. Keep the existing plan's
original state, independent source package, native Helm/source checks and artifact-supply contracts.
[Main input contract](platform-recovery-contract.md#2-select-backups-and-isolated-targets).

| Field or retained file | Meaning |
| --- | --- |
| `namespace`, `namespace_uid` | Actual product namespace and selected target UID, or `new` for the plan-owned replacement namespace |
| `data_claims`, `claim_uids` | Every selected claim mapped to its explicit target UID or `new`; the runner records observed UIDs and rejects replacements on retry |
| `writers` | Actual StatefulSet/Deployment/CronJob names that the native workflow fences |
| `verification_workloads` | Explicit isolated consumers started after that product's native restore; keep NetBox web/worker consumers stopped until both database and media are restored |
| `clusters[].restore_resources` | Accepted namespaces, retained TLS/credentials, claims and original workload templates at zero replicas; Vault has no fresh init container |
| `verification_ca_secret` | Secret containing public `ca.pem` for the selected verified HTTPS endpoints |
| `verification_headers_secret` | NetBox's scoped verification headers, or Vault's empty `headers.json` object `{}` |
| `python_image` | Independently retained verification image by digest, included in `artifact_supply` |
| `checks[].ca_path` | Workspace-relative CA file, such as `tier-0/secrets/vault-ca.pem`, listed with SHA-256 in `automation.<repository>.private_files` |
| Other private inputs | Retained restore resources, original app/Helm inputs, repository credentials, source SSH/TLS keys and artifact locks; checksum-bind each consumed file in its owning `private_files` list |

Vault root/recovery tokens and Shamir shares **never enter Kubernetes Secrets**, verification headers,
Git or the copied automation workspace. Its custody file remains in the controller's separate
owner-only directory. General Vault checks use unauthenticated known seal-status content and a denied
request. The controller helper separately proves the original cluster identity and known secret.
Keep the controller's restic password file mode `0600`, owned by the execution user. Controller-local
CA/tool/custody paths must be absolute and available before the accepted plan runs.

Record the exact raw response SHA-256 and expected HTTP status for each `checks[]` probe while the
original service is available. `content_sha256` hashes response bytes. It differs from Vault's
`known_secret.sha256`, which hashes the selected canonical JSON value. Use an observed `401` or `403`
for the denied probe. All URLs and trust inputs must match the isolated recovery endpoint.

## 3. Collect the original Shamir quorum

For the Vault path, attending keyholders perform this step **on the independent controller before
plan approval**. Select a new canonical custody directory outside every Git checkout. Enter the
original threshold `t`, such as `3`, rather than the total number of issued shares.

Run from **the retained `<prefix>-tier-1/` repository**.

```bash
read -r -p 'Private custody directory outside Git (e.g. /var/tmp/control-recovery-custody): ' VAULT_CUSTODY_DIR
read -r -p 'Original Shamir threshold (e.g. 3): ' VAULT_QUORUM
install -d -m 0700 -- "$VAULT_CUSTODY_DIR"
python3 ansible/roles/platform_recovery/files/vault_recovery.py \
  --collect-custody "$VAULT_CUSTODY_DIR/vault-original.json" --shares "$VAULT_QUORUM"
```

The helper uses hidden `getpass` prompts for the original root or valid recovery token and each
distinct original share. It creates a new mode-`0600` file, rejects an existing filename and prints
only its SHA-256. Secrets are entered at the prompts, never as CLI arguments. Set `vault.custody`
to that exact directory/file/checksum with `mode: ephemeral-file` before approving the plan.

The collected file contains `token` and `unseal_keys_b64`. Temporary target-initialization credentials
also stay in this owner-only directory and are removed after the original leader is verified.
Keep original custody material available for the accepted run and its retry policy, then retire the
ephemeral copy through the custody procedure. The unattended workflow uses the prepared file.

## 4a. Add the Vault product

Copy this object into **`secrets/platform-recovery.json` → `products[]`**. Replace all `REPLACE_…`
strings and illustrative resource names/counts with the retained deployment values. Expand `members`,
all data/audit claims and writer replicas to match the original deployment. Cluster UUIDs always come
from the original record.

```json
{
  "name": "vault",
  "kind": "vault-raft",
  "tier": 0,
  "namespace": "vault",
  "namespace_uid": "new",
  "backup_id": "REPLACE_WITH_FULL_RESTIC_SNAPSHOT_ID",
  "data_claims": ["data-vault-0", "audit-vault-0"],
  "claim_uids": {"data-vault-0": "new", "audit-vault-0": "new"},
  "writers": [{"kind": "StatefulSet", "name": "vault", "replicas": 1}],
  "control_backup": {
    "repository": "/mnt/independent-control-backups",
    "repository_id": "REPLACE_WITH_REPOSITORY_ID",
    "password_file": "/srv/custody/control-restic-password",
    "password_sha256": "REPLACE_WITH_PASSWORD_FILE_SHA256",
    "restic_binary": "/opt/recovery/restic",
    "restic_version": "REPLACE_WITH_ORIGINAL_RESTIC_VERSION",
    "vault_binary": "/opt/recovery/vault",
    "set_path": "/var/lib/control-backup/REPLACE_WITH_RECEIPT_SET",
    "manifest_sha256": "REPLACE_WITH_MANIFEST_SHA256"
  },
  "vault": {
    "seal": "shamir",
    "version": "REPLACE_WITH_ORIGINAL_VAULT_VERSION",
    "image": "recovery.internal.example.com/vault@sha256:REPLACE_WITH_IMAGE_SHA256",
    "statefulset": "vault",
    "container": "vault",
    "tls_secret": "vault-server-tls",
    "tls_server_name": "vault.internal.example.com",
    "ca_file": "/srv/custody/vault-ca.pem",
    "ca_sha256": "REPLACE_WITH_CA_FILE_SHA256",
    "cluster_id": "REPLACE_WITH_ORIGINAL_CLUSTER_UUID",
    "shamir_threshold": 3,
    "snapshot_sha256": "REPLACE_WITH_RECEIPT_VAULT_SHA256",
    "leader_api_addr": "https://vault-0.vault-internal.vault.svc.cluster.local:8200",
    "members": [{"pod": "vault-0", "node_id": "REPLACE_WITH_ORIGINAL_NODE_ID", "data_claim": "data-vault-0"}],
    "known_secret": {
      "path": "secret/data/recovery-proof",
      "pointer": ["data", "data", "proof"],
      "sha256": "REPLACE_WITH_CANONICAL_SECRET_VALUE_SHA256"
    },
    "custody": {
      "mode": "ephemeral-file",
      "directory": "/var/tmp/control-recovery-custody",
      "file": "/var/tmp/control-recovery-custody/vault-original.json",
      "sha256": "REPLACE_WITH_COLLECTED_CUSTODY_FILE_SHA256"
    }
  },
  "python_image": "recovery.internal.example.com/python@sha256:REPLACE_WITH_IMAGE_SHA256",
  "verification_ca_secret": "vault-recovery-ca",
  "verification_headers_secret": "vault-recovery-empty-headers",
  "checks": [
    {"url": "https://vault.internal.example.com/v1/sys/seal-status", "status": 200, "authenticated": false,
     "ca_path": "tier-0/secrets/vault-ca.pem", "content_sha256": "REPLACE_WITH_KNOWN_SEAL_STATUS_BODY_SHA256"},
    {"url": "https://vault.internal.example.com/v1/secret/data/recovery-proof", "status": 403, "authenticated": false,
     "ca_path": "tier-0/secrets/vault-ca.pem"}
  ]
}
```

| Vault field | Native meaning |
| --- | --- |
| `version`, `image`, `vault_binary` | Exact original Vault version, retained server image digest and matching original controller CLI |
| `statefulset`, `container`, `members` | Original resource/container names; Pod ordinals start at zero and each member names its data claim and distinct Raft node ID |
| `tls_secret`, `tls_server_name`, `ca_file`, `ca_sha256` | Retained leaf Secret and verified server name; controller-local public CA file and checksum |
| `leader_api_addr` | Original private HTTPS leader endpoint reachable by joining members; certificate trust/SAN must match |
| `cluster_id`, `shamir_threshold` | Original cluster UUID and original Shamir threshold |
| `snapshot_sha256` | `vault_sha256` from the accepted control-backup set |
| `known_secret` | Original KV API path, response key sequence and canonical JSON value checksum |
| `custody` | Controller-only collected original token/share file and its accepted SHA-256 |

The adapter verifies the independent repository, set manifest, native snapshot and tool versions
before target mutation. It guards each empty claim, temporarily initializes only the isolated first
member, restores the snapshot, unseals with original shares and proves original identity/content.
It then joins/verifies the selected voters. An uncertain submission is observed without replaying
the overwrite; a failed or unjournaled initialized target requires an explicitly selected clean target.

## 4b. Add the NetBox media product

Add this object to **the same plan's `products[]`** beside its separate `cnpg-files` NetBox database
entry. Replace placeholder strings and illustrative names/UID/GID with the retained originals.
List the database entry first and leave its NetBox verification consumers stopped. The media entry
can then start the selected isolated web consumer after its restore; general product checks run
after all of that tier's product restorations. Keep workers and external integrations fenced until cutover.

```json
{
  "name": "netbox-media",
  "kind": "netbox-media",
  "tier": 0,
  "namespace": "netbox",
  "namespace_uid": "new",
  "backup_id": "REPLACE_WITH_FULL_RESTIC_SNAPSHOT_ID",
  "data_claims": ["netbox-media"],
  "claim_uids": {"netbox-media": "new"},
  "writers": [{"kind": "Deployment", "name": "netbox", "replicas": 1},
              {"kind": "Deployment", "name": "netbox-worker", "replicas": 1}],
  "verification_workloads": [{"kind": "Deployment", "name": "netbox", "replicas": 1}],
  "control_backup": {
    "set_path": "/var/lib/control-backup/REPLACE_WITH_RECEIPT_SET",
    "manifest_sha256": "REPLACE_WITH_MANIFEST_SHA256",
    "vault_sha256": "REPLACE_WITH_RECEIPT_VAULT_SHA256",
    "repository_id": "REPLACE_WITH_REPOSITORY_ID"
  },
  "media": {
    "claim": "netbox-media",
    "path": "/mnt/control-media/netbox",
    "source_marker": "REPLACE_WITH_ORIGINAL_MEDIA_MARKER",
    "known_file": "recovery-proof.txt",
    "known_file_sha256": "REPLACE_WITH_KNOWN_MEDIA_FILE_SHA256",
    "run_as_user": 1000,
    "run_as_group": 1000
  },
  "restic_image": "recovery.internal.example.com/restic@sha256:REPLACE_WITH_IMAGE_SHA256",
  "restic_version": "REPLACE_WITH_ORIGINAL_RESTIC_VERSION",
  "restic_secret": "netbox-media-restic",
  "python_image": "recovery.internal.example.com/python@sha256:REPLACE_WITH_IMAGE_SHA256",
  "verification_ca_secret": "netbox-recovery-ca",
  "verification_headers_secret": "netbox-recovery-reader",
  "checks": [
    {"url": "https://netbox.internal.example.com/media/recovery-proof.txt", "status": 200, "authenticated": true,
     "ca_path": "tier-0/secrets/netbox-ca.pem", "content_sha256": "REPLACE_WITH_KNOWN_MEDIA_FILE_SHA256"},
    {"url": "https://netbox.internal.example.com/api/dcim/devices/", "status": 403, "authenticated": false,
     "ca_path": "tier-0/secrets/netbox-ca.pem"}
  ]
}
```

| NetBox field | Native meaning |
| --- | --- |
| `media.claim`, `data_claims`, `claim_uids` | One selected media PVC; retain its observed UID through retries |
| `media.path` | Exact absolute original media root from `restic ls`; `known_file` is relative to it |
| `source_marker`, `known_file_sha256` | Original `.control-backup-source` value and regular-file checksum |
| `run_as_user`, `run_as_group` | Original non-root numeric media owner/application identity from retained workload/storage records |
| `control_backup.vault_sha256` | Vault snapshot checksum recorded in the same control-backup manifest; pair the NetBox database backup separately |
| `restic_image`, `restic_version` | Independently retained restore image digest and exact original restic tool version |
| `restic_secret` | Retained Secret containing `RESTIC_REPOSITORY` and `RESTIC_PASSWORD`; `RESTIC_PASSWORD_FILE` works only when its selected private path is available inside the restore container |
| Optional `repository_claim` | Separate repository PVC mounted read-only at `/repository`; select it only for the accepted file-backed repository path |

The native Job checks the repository ID, manifest, media selection, original marker and empty target.
It restores only the selected media subtree, verifies bytes/known-file identity and journals the
plan/PVC binding. The workflow restores the database through its separate product entry and verifies
the paired application before cutover. CSI-backed replacement media PVCs use this same native file path.

## 5. Approve and run the completed plan

1. Review the source package, artifact locks, original private files, product inputs and custody-file
   checksum together. Approve the resulting plan SHA-256 only after Step 3's human collection.
2. Run the accepted-plan workflow with the approved checksum. Once these inputs are available, its
   automated phases run unattended. Human Shamir collection remains the preceding custody action.
3. Retain native Job/namespace/claim UIDs, Vault cluster/content proof and media verification receipts.
   Retry using the same plan/workspace; changed targets or uncertain native operations require the
   workflow's explicit clean-target recovery path.

[Run and resume the accepted plan](platform-recovery-contract.md#3-run-restoration).

## Supported variants and qualification

The supplied Vault adapter covers Kubernetes integrated Raft with the original Shamir seal and
quorum. Transit, PKCS#11 and other seal variants require their original seal service/device and a
separate adapter. Dedicated Vault VM restoration retains its existing VM procedure; automated VM
Shamir unsealing is outside this adapter. Hardware/provider behavior needs target qualification.

NetBox media uses the selected native control-backup/restic set plus its separate CNPG database
recovery. Native API fixtures, filesystem tests and completed-UID checks require subsequent live
Vault restore/unseal, CSI, paired application and outage/RPO/RTO acceptance.

[Vault helper contract](../../../../tier-1/ansible/roles/platform_recovery/files/vault_recovery.py),
[Vault tasks](../../../../tier-1/ansible/roles/platform_recovery/tasks/vault-raft.yml),
[media tasks](../../../../tier-1/ansible/roles/platform_recovery/tasks/netbox-media.yml),
[product validator](../../../../tier-1/scripts/recovery_control.py).
