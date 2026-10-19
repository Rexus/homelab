# Step 3c: NAS-backed log archive

Use an independent NAS with storage-managed snapshots and backups when trusted
NAS administrators and a measured unprotected tail are acceptable. Strict WORM
retention is not required for this selected homelab model.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Branch from:** [Step 3](README.md#step-3-protect-and-verify-retained-evidence), when trusted NAS administration is acceptable.
**Change:** Protect archive checkpoints with NAS-owned snapshots and independent backups, without claiming WORM.
**Return:** [Step 3](README.md#step-3-protect-and-verify-retained-evidence) to record the demonstrated protection boundary.
**Design:** [choice A: NAS custody](../../architecture/operations/log-retention.md).
**Prerequisites:** working collection, dedicated NAS storage, independent admin
credentials and a recovery destination outside that NAS's failure domain.
**Automation boundary:** the supplied receiver writes local records. NAS setup,
archive transfer, snapshot/backup scheduling and access auditing require product
integration; `deploy.sh syslog` does not install them.

## Contents

- [Step 1: Prepare storage and roles](#step-1-prepare-storage-and-roles)
- [Step 2: Connect collection to retained copies](#step-2-connect-collection-to-retained-copies)
- [Step 3: Verify and record the boundary](#step-3-verify-and-record-the-boundary)
- [Next](#next)
- [References](#references)

## Step 1: Prepare storage and roles

1. Create a dedicated security-log dataset/share and capacity budget on the NAS.
   Keep collector queues/local records on their prepared local volume so a NAS
   outage does not immediately stop intake. Do not replace that volume with a
   network mount or place the only archive on the VM datastore being protected.
2. Assign the roles below. One person may hold all roles; keep their credentials
   separate and keep NAS-owner/backup credentials off collectors and ordinary runners.
3. Configure NAS-owned snapshots and independent backup retention. Select intervals
   from measured event rate and acceptable loss, not an example schedule.

| Identity | Scope |
| --- | --- |
| Archive transfer account | Only its archive intake area; no NAS/snapshot/backup administration |
| Security reader | Approved read scope; no writes, deletion or storage administration |
| NAS/backup administrator | Snapshot, expiry and recovery authority; trusted under this model |
| Family, employees, app developers | No raw archive share; later scoped application views are separate |

For UniFi NAS, create a dedicated Shared Drive and file-service identity using
the [SMB setup](https://help.ui.com/hc/en-us/articles/14276882157975-Adding-UniFi-Drive-to-Your-Desktop-via-SMB).
Use supported authenticated/encrypted transport on the restricted archive network.
If NFS is selected, document its identity/network trust explicitly; do not enable
no-root-squash merely to solve client permissions. UniFi documents material
restrictions for that mode. [1]

## Step 2: Connect collection to retained copies

1. Configure the selected transfer integration for consistent checkpoints: complete
   portable records, source catalogue, event ranges and integrity metadata. Retain
   source/collector copies until the required checkpoint and backup are verified.
   Do not copy live queue files or treat TCP success as archive commitment.
2. Transfer without propagating deletion from the collector. A missing source file
   must not delete the NAS copy; ordinary mirroring with deletion is not archival.
   If the transfer identity can overwrite/delete live share files, record that limit:
   recovery then depends on a previously completed snapshot it cannot administer.
3. Schedule snapshots on the NAS and backups to a different recovery target.
   Keep completion/coverage records outside the collector. For UniFi Drive, use
   [Backup Tasks](https://help.ui.com/hc/en-us/articles/30961935781655-Troubleshooting-UNAS-Backup-Issues)
   for the selected external destination; snapshots alone do not create that copy.

Record source-to-copy lag and the latest verified snapshot/backup checkpoint.
An asynchronous copy/snapshot interval creates an exposed tail; it is not zero RPO.
RAID and another snapshot on the same NAS do not cover loss of the whole appliance.
Protect decryption keys independently under the [backup policy](../../administration/compute/backup-restore.md#backup-policy).

## Step 3: Verify and record the boundary

1. Run the [logging drill](../../administration/logging-drill.md) for this profile.
   Deny raw access/deletion to producers and query users. Test that transfer
   credentials cannot administer snapshots/backups; test live-share deletion only
   with disposable records, then restore the covered checkpoint.
2. Test NAS/network outage, bounded backlog, missed snapshot/backup alerts and
   clean-target restoration without normal SSO or Kubernetes. Verify usable records,
   not merely a successful backup job. Record observed RPO/RTO and audit coverage.
3. Record **A: NAS-backed**, the trusted administrator, exact checkpoint boundary,
   residual privileged-deletion risk and review triggers in the project's
   `docs/administration/logging-evidence.md` and architecture selection.

UniFi Drive documents administrator-deletable snapshots. [2] This path does not
claim protection against the NAS owner deleting all copies under that owner's
authority. Protecting against that threat requires separate custody or choice B.

## Next

Return to [Stage 1, Step 3](README.md#step-3-protect-and-verify-retained-evidence).
Select [3d: retention locks](step-3d-retention-lock.md) when privileged deletion
must be prevented. NAS backups and locked archives can coexist.

## References

Sources checked 2026-10-19.

1. [UniFi NFS squash modes and restrictions](https://help.ui.com/hc/en-us/articles/26277250895895-Accessing-Your-UniFi-Drive-from-Linux-Desktop-Using-NFS)
2. [UniFi snapshots and deletion](https://help.ui.com/hc/en-us/articles/33317752912919-Understanding-System-Data-Others-in-UniFi-Drive)
