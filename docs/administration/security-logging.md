# Security logging operations

**Owner:** Tier 0 for protected evidence; each tier owns its producers.
**Design:** [security logging](../architecture/operations/security-logging.md).
**Prerequisites:** accepted [receiver/archive integration](../deployment/stage-2-logging/README.md)
and recorded failure, retention, access and recovery contracts.

## Table of contents

- [Routine checks](#routine-checks)
- [Maintenance and incidents](#maintenance-and-incidents)
- [Fault and restore evidence](#fault-and-restore-evidence)
- [Offline investigation](#offline-investigation)
- [Automation boundary](#automation-boundary)
- [NAS backup restoration](#nas-backup-restoration)
- [References](#references)

## Routine checks

| Check | Operator action |
| --- | --- |
| Source coverage | Compare expected sources/heartbeats with received sequence/time ranges; investigate missing streams and clock skew |
| Queues and capacity | Review rate, backlog age, disk/retention headroom, rejected traffic and archive replication; alert before exhaustion |
| Receiver and archive health | Verify durable writes, redundant paths and independent notification delivery, not only port/process health |
| Reader scopes | Review explicit security-reader/system-administrator groups; test that developers can read only their approved application copies |
| Destructive permissions | Test direct update/delete, delete-by-query, index administration and backup deletion as a query user; all must be denied |
| Investigation | Audit raw-evidence reads and exports; preserve original records and chain-of-custody metadata |
| Retention | Verify the [selected archive model](../architecture/operations/log-retention.md): NAS snapshot/backup coverage and custody, or effective version locks; collector credentials cannot administer either protection |
| Keys and certificates | Rotate under a tested continuity plan; preserve trust, archived-data decryption and break-glass access |

## Maintenance and incidents

1. Check independent copies, queue headroom and the active failure budget before
   draining one receiver or storage member. Do not simultaneously remove all required copies.
2. During downstream outages, preserve sender spools and retained evidence. Do not
   delete backlog, shorten retention or silently discard events to clear capacity alarms.
3. Reconcile numbered events after failover/replay. Account for duplicates and
   document gaps; do not rewrite originals to make counts appear complete.
4. Test an unauthorized source, forged ownership label, cross-application read,
   overwrite/delete request and raw-archive access by an ordinary platform operator.
5. Restore protected records from an independent copy and verify integrity, reader
   scope and key availability without Tier 1, the control cluster or normal SSO.

When outage duration exceeds the declared buffer/failure envelope, follow the
approved backpressure or fail-closed policy and record the incident. No finite
buffer makes all sources lossless indefinitely.

Under the NAS model, one homelab operator may hold reader and storage-administrator
roles using separate credentials. Keep ordinary work and collector services out of
the administrative role. Reassess this trust when granting another person access;
separate storage/retention custody if needed, and use retention locks when privileged
deletion itself must be prevented. Review snapshot lag, external backup completion
and access-recording gaps explicitly; a read-only share does not audit its reads.

## Fault and restore evidence

Use the [fault and restore drill](logging-drill.md) for numbered test batches,
controlled failures, independent restoration and the project-owned acceptance record.
Record reconciliation alone does not prove fault survival or archive protection.

## Offline investigation

**Prerequisites:** authorized recovery custodian, trusted isolated recovery host,
surviving data volume or backup, and the independently held reader/key kit.
Rehearse with a copy; do not test failure recovery on the only surviving evidence.

1. Preserve surviving disks, local source logs and archive copies before rebuilding.
   Record identifiers, time and custody; image the media where practical and verify
   the image. Do not boot the old collector or run repair/rotation against originals.
2. Retrieve the documented volume layout, reader tools and separately protected keys.
   Unlock and attach a working copy using the selected filesystem's tested read-only,
   no-journal-replay procedure. For example, ext4 can replay its journal even on a
   read-only mount. [1] If recovery needs replay/repair, use a separate disposable copy.
3. Read the retained text/JSON Lines with offline tools. Use the local source catalogue
   and source/receive timestamps to reconstruct events without SSO, an inventory service,
   Vault, Kubernetes or a search database. Verify manifests where available; document
   truncated final segments, clock uncertainty and gaps rather than repairing originals.
4. Record access and findings in a separate protected case log. Keep decryption keys and
   exports off ordinary workstations, shared query accounts and Git repositories.
5. Restore into a clean environment using the [tier recovery order](recovery.md#recovery-order).
   Rebuild Tier 1 indexes from approved copies only; never let reindexing modify originals.

Acceptance is a useful investigation with normal infrastructure shut down, followed
by the same test from an independent backup. Record the recovery time and recoverable
event range against the [backup objectives](compute/backup-restore.md#backup-policy).
This verifies readability, not live-collector HA or protection against every physical loss.

## Automation boundary

Tier 0 `bash scripts/deploy.sh syslog --ansible-only --recipe maintenance` currently
reconciles the baseline and [isolated receiver](../reference/syslog-receiver.md)
serially. It does not upgrade packages, delete evidence/queues, change retention or
prove HA. Drain backlogs and preserve persist files before source/queue changes;
remove retired firewall rules deliberately. Product operations remain project-owned procedures.
Tier 1 search-index maintenance never grants authority to alter Tier 0 evidence.

The [pipeline recipes](../reference/logging-pipeline.md#ownership-and-entry-points)
reconcile producers, trust, NAS publication and independent backup separately.
Reapply the owning recipe for reviewed configuration changes; authority operations
run only on the protected signing controller. Jobs never prune or delete evidence.
Check `security-log-archive.timer`, `security-log-backup.timer` and producer health
timers as well as the independently observed dead-man status. A recent checkpoint
ping does not certify completion of NAS snapshots or a separate backup.

## NAS backup restoration

1. On an authorized, isolated recovery host, retrieve the independent restic
   repository, separately held password, and the offline reader kit containing
   `logging_checkpoint.py`, `logging_io.py` and `logging_health.py`. Preserve the
   source repository; select a new empty restore directory, never the live share.
2. Select the protected paths and inspect the recorded snapshots:

   ```bash
   read -r -e -p 'Independent restic repository path: ' RESTIC_REPOSITORY
   read -r -e -p 'Recovery password file path: ' RESTIC_PASSWORD_FILE
   export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
   restic snapshots --tag security-logging
   restic check --read-data
   ```

3. Choose the incident's known-good snapshot and an empty disposable target:

   ```bash
   read -r -p 'Approved snapshot ID: ' LOGGING_SNAPSHOT
   read -r -e -p 'New empty restore directory: ' LOGGING_RESTORE
   restic restore "$LOGGING_SNAPSHOT" --target "$LOGGING_RESTORE"
   ```

   Restic preserves the original path tree beneath that target. Locate the restored
   archive root containing `<collector>/checkpoints/` and `<collector>/chunks/`, then
   verify using the kit's script from its own directory:

   ```bash
   read -r -e -p 'Restored archive root containing collector directories: ' LOGGING_ARCHIVE_ROOT
   python3 logging_checkpoint.py verify --root "$LOGGING_ARCHIVE_ROOT"
   ```

4. Reconcile the covered numbered batches using the [logging drill](logging-drill.md),
   inspect the source catalogue in manifests and read JSONL without a search service.
   Record the last independently protected checkpoint, missing tail, duplicates and
   measured RPO/RTO. Hash verification alone does not prove coverage or authorized custody.

The default backup job does not initialize existing repositories, delete snapshots,
prune, or restore automatically. NAS snapshot restoration is a separate custodian
operation; perform it on a copy and verify with the same reader kit.

## References

Source checked 2026-10-16.

1. [Linux ext4 read-only mounting and journal-replay behavior](https://www.kernel.org/doc/html/latest/admin-guide/ext4.html#options)
