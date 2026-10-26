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
**Automation boundary:** Tier 0 supplies separate archive and independent-backup
recipes; `deploy.sh syslog` alone installs neither. NAS account/snapshot commissioning
and the independent recovery filesystem remain prerequisites, not collector privileges.

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

Permit only the selected endpoints; keep these flows separate from administration:

| Initiator | Destination | Main-path transport |
| --- | --- | --- |
| Approved producers | Tier 0 receiver address | TCP 6514 with client TLS; selected port if overridden |
| Collector transfer / independent recovery host | Dedicated NAS share endpoint | TCP 445, authenticated encrypted SMB; separate write/read identities |
| Producer, archive and backup health jobs | Named independent dead-man endpoints | TCP 443, verified HTTPS; no general outbound permission implied |

No producer receives NAS access. Restrict recovery-repository and approved reader
access independently; this role does not open gateway rules or a public query listener.

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

1. On the NAS, create `.logging-target` in the dedicated archive share with an
   independently recorded marker of 16-128 letters/digits/underscores/hyphens.
   Give the collector transfer account only this share, never NAS administration.
   Create a distinct read-only account for the recovery host. Enable SMB 3.1.1
   encryption, NAS-owned snapshots, retention and NAS-side access auditing.
2. From the Tier 0 root, copy and edit the archive inputs:

   ```bash
   cp ansible/group_vars/logging_archive.yml.example ansible/group_vars/logging_archive.yml
   read -r -e -p 'Restricted NAS transfer credential file: ' LOGGING_NAS_CREDENTIALS_FILE
   export LOGGING_NAS_CREDENTIALS_FILE
   ```

   Set the SMB source, marker, snapshot owner/runbook, required active OS source
   names, capacity/lag budgets and an **external dead-man URL** that alerts when
   successful pings stop. The credential file uses native CIFS `username=`, `password=`
   and optional `domain=` lines. It is copied root-only, not placed in inventory/Git.
   Optionally map only approved application sources to dedicated reader groups;
   security-stream classification comes from Tier 0's source catalogue.
3. After the source heartbeats are arriving and the storage contract is reviewed,
   select one collector from `foundation_logging`. Reuse its host file from
   [source setup](sources.md#1-prepare-tier-owned-streams). Explicitly load global
   settings, the collector setup/IP map, archive settings and finally host overrides:

   ```bash
   read -r -p 'Collector inventory host (for example log-1): ' LOGGING_COLLECTOR
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook \
     -i ansible/inventory/hosts.yml --limit "${LOGGING_COLLECTOR:?Select one collector}" \
     -e @ansible/group_vars/all.yml -e @ansible/group_vars/syslog.yml \
     -e @ansible/group_vars/logging_archive.yml \
     -e "@ansible/host_vars/$LOGGING_COLLECTOR.yml" \
     ansible/playbooks/deployment/logging-archive.yml
   ```

   The role mounts the selected encrypted share, checks its independent marker and
   starts `security-log-archive.timer`. Each run seals complete JSONL prefixes into
   create-only hashed chunks and manifests, then advances its local cursor. It never
   copies live queue files, mirrors deletion or removes local evidence. Linux audit
   records raw/view reads; forward `/var/log/audit/audit.log` as a security stream.
4. On a separate, Tier 0-owned Linux recovery host, prepare a mounted recovery filesystem
   outside the NAS/collector failure domain. Add that existing host to `logging_recovery`
   in Tier 0 inventory, never `foundation_logging`. Copy/edit its backup inputs:

   ```bash
   cp ansible/group_vars/logging_backup.yml.example ansible/group_vars/logging_backup.yml
   read -r -e -p 'Read-only NAS recovery credential file: ' LOGGING_BACKUP_NAS_CREDENTIALS_FILE
   read -r -e -p 'Separately held restic password file: ' LOGGING_BACKUP_PASSWORD_FILE
   export LOGGING_BACKUP_NAS_CREDENTIALS_FILE LOGGING_BACKUP_PASSWORD_FILE
   ```

   Set source/marker, independent mounted repository, schedule and a separate external
   dead-man check. Keep password/recovery keys off the collector. Approve repository
   initialization only for a deliberately new destination; otherwise use the existing
   repository/password. Create `ansible/host_vars/<recovery-host>.yml` with its
   existing `ansible_host`, SSH account/key overrides and any per-host backup settings.
   The recovery host need not belong to a Terraform setup; never borrow a collector's
   address. Deploy against that one inventory host:

   ```bash
   read -r -p 'Independent recovery inventory host: ' LOGGING_RECOVERY_HOST
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook \
     -i ansible/inventory/hosts.yml --limit "${LOGGING_RECOVERY_HOST:?Select one recovery host}" \
     -e @ansible/group_vars/all.yml -e @ansible/group_vars/logging_backup.yml \
     -e "@ansible/host_vars/$LOGGING_RECOVERY_HOST.yml" \
     ansible/playbooks/deployment/logging-backup.yml
   ```

   It verifies complete checkpoints, backs up only that fixed verified file list with
   restic, checks the encrypted repository and pings only after success. No automatic
   expiry/prune or NAS administration is granted. Native NAS backup tasks are also a
   valid independently qualified alternative; avoid two unreviewed retention owners.

For named environments, insert `all.<env>.yml` and the selected setup overlay after
the base setup map and before archive/backup settings and host overrides. Keep the
host file last and rerun separately for each collector or recovery host.

Record source-to-copy lag and the latest verified snapshot/backup checkpoint.
An asynchronous copy/snapshot interval creates an exposed tail; it is not zero RPO.
RAID and another snapshot on the same NAS do not cover loss of the whole appliance.
Protect decryption keys independently under the [backup policy](../../administration/compute/backup-restore.md#backup-policy).
The [pipeline contract](../../reference/logging-pipeline.md) defines exact paths,
failure behavior, filesystem reader views and the distinction between transport,
NAS checkpoint, NAS snapshot and independent backup. Snapshot coverage is
commissioned/checked on the NAS, not inferred from a successful transfer heartbeat.

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

Return to [Stage 2, Step 3](README.md#step-3-protect-and-verify-retained-evidence).
Select [3d: retention locks](step-3d-retention-lock.md) when privileged deletion
must be prevented. NAS backups and locked archives can coexist.

## References

Sources checked 2026-10-19.

1. [UniFi NFS squash modes and restrictions](https://help.ui.com/hc/en-us/articles/26277250895895-Accessing-Your-UniFi-Drive-from-Linux-Desktop-Using-NFS)
2. [UniFi snapshots and deletion](https://help.ui.com/hc/en-us/articles/33317752912919-Understanding-System-Data-Others-in-UniFi-Drive)
