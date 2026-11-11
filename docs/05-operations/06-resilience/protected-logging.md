# Security logging operations

**Owner:** Tier 0 for protected evidence; each tier owns its producers.
**Design:** [security logging](../../01-architecture/11-operations/01-protected-logging.md).
**Prerequisites:** accepted [receiver/archive integration](../../03-deployment/stage-2-logging/README.md)
and recorded failure, retention, access and recovery contracts.

<a id="table-of-contents"></a>

## Find a task

- [How is logging health checked?](#routine-checks)
- [What happens during an outage or maintenance window?](#maintenance-and-incidents)
- [How is fault survival demonstrated?](#fault-and-restore-evidence)
- [Can evidence be read with the platform shut down?](#offline-investigation)
- [How is receiver configuration reapplied?](#automation-boundary)
- [How is an independent NAS backup restored?](#nas-backup-restoration)

<a id="routine-checks"></a>

## How is logging health checked?

**Work on:** the Tier 0 receiver, the separate recovery host and an authorized evidence-reading path.
**Prerequisites:** the accepted source catalogue, archive/backup schedule and external watchdog.

1. On the receiver, inspect the dedicated service and archive timer; the OS logger is separate:

   Run on **the Tier 0 log receiver**.

   ```bash
   sudo systemctl status syslog-ng-receiver.service --no-pager
   sudo systemctl list-timers --all security-log-archive.timer
   sudo journalctl -u syslog-ng-receiver.service -u security-log-archive.service --since '-1 hour' --no-pager
   ```

2. On the **independent `logging_recovery` host**, inspect backup execution:

   Run on **the independent logging_recovery host**.

   ```bash
   sudo systemctl list-timers --all security-log-backup.timer
   sudo journalctl -u security-log-backup.service --since '-1 day' --no-pager
   ```

3. Check external missed-success alerts and the evidence/permissions checks below.
   Treat raw journal output as security-sensitive; do not publish it in ordinary CI artifacts.

| Check | Operator action |
| --- | --- |
| Source coverage | Compare expected sources/heartbeats with received sequence/time ranges; investigate missing streams and clock skew |
| Queues and capacity | Review rate, backlog age, disk/retention headroom, rejected traffic and archive replication; alert before exhaustion |
| Receiver and archive health | Verify durable writes, redundant paths and independent notification delivery, not only port/process health |
| Reader scopes | Review explicit security-reader/system-administrator groups; test that developers can read only their approved application copies |
| Destructive permissions | Test direct update/delete, delete-by-query, index administration and backup deletion as a query user; all must be denied |
| Investigation | Audit raw-evidence reads and exports; preserve original records and chain-of-custody metadata |
| Retention | Verify the [selected archive model](../../01-architecture/11-operations/02-log-retention.md): NAS snapshot/backup coverage and custody, or effective version locks; collector credentials cannot administer either protection |
| Keys and certificates | Rotate under a tested continuity plan; preserve trust, archived-data decryption and break-glass access |

**Expected:** current sources, bounded queues, completed independent copies and tested read denials.
**Stop:** investigate missing/stale success even when a process is running. A checkpoint ping
does not prove a NAS snapshot or independent backup completed.

<a id="maintenance-and-incidents"></a>

## What happens during an outage or maintenance window?

**Work from:** Tier 0 operations with the archive/storage custodian.
**Prerequisites:** independent recovery copies, queue/capacity budget and an approved undo procedure.

On NAS loss, the receiver retains its local data-disk path; checkpoint publication fails rather
than falling back to a local archive directory. Restore the commissioned NAS path/identity with
its custodian, then verify checkpoint progress and independent backup catch-up. Do not redirect
intake onto the NAS or delete queues to clear the incident.

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

**Stop/rollback:** stop the maintenance change if its failure budget is exceeded. Restore the
approved service/storage path; preserve spools and originals. No query user may erase protected
records, and no automated queue/evidence cleanup is supplied.

<a id="fault-and-restore-evidence"></a>

## How is fault survival demonstrated?

Use the [fault and restore drill](logging-drill.md) for numbered test batches,
controlled failures, independent restoration and the project-owned acceptance record.
Record reconciliation alone does not prove fault survival or archive protection.

<a id="offline-investigation"></a>

## Can evidence be read with the platform shut down?

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
5. Restore into a clean environment using the [tier recovery order](README.md#recovery-order).
   Rebuild Tier 1 indexes from approved copies only; never let reindexing modify originals.

Acceptance is a useful investigation with normal infrastructure shut down, followed
by the same test from an independent backup. Record the recovery time and recoverable
event range against the [backup objectives](backups/virtual-machines.md#backup-policy).
This verifies readability, not live-collector HA or protection against every physical loss.

<a id="automation-boundary"></a>

## How is receiver configuration reapplied?

**Work from:** the **Tier 0 repository root** on the approved execution host.
**Prerequisites:** existing inventory, local `syslog.yml`, approved TLS files, the original data-volume binding
and independent recovery. Review the failure/queue budget before any source or queue change.

1. Edit `ansible/group_vars/syslog.yml` and its accepted source catalogue. Preserve the
   existing inventory host keys, data mount/UUID, producer identities and queue state.
2. Reconcile the supported existing receiver configuration:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/deploy.sh syslog --recipe maintenance
   ```

3. Repeat the health, known-source-event and denied-source checks above before widening scope.

This reconciles the baseline and [isolated receiver](../../08-reference/syslog-receiver.md)
serially. It does not upgrade packages, delete evidence/queues, change retention or
prove HA. Drain backlogs and preserve persist files before source/queue changes;
remove retired firewall rules deliberately. Product operations remain project-owned procedures.
Tier 1 search-index maintenance never grants authority to alter Tier 0 evidence.

The [pipeline recipes](../../08-reference/logging-pipeline.md#ownership-and-entry-points)
reconcile producers, trust, NAS publication and independent backup separately.
Reapply the owning recipe for reviewed configuration changes; authority operations
run only on the protected signing controller. Jobs never prune or delete evidence.
Check `security-log-archive.timer`, `security-log-backup.timer` and producer health
timers as well as the independently observed dead-man status. A recent checkpoint
ping does not certify completion of NAS snapshots or a separate backup.

**Expected:** only the supported receiver/baseline configuration changes; Terraform is skipped.
**Stop/rollback:** a failed run may have applied earlier tasks. Preserve diagnostics and restore
reviewed configuration through independent access; never clear persist files or evidence to force a retry.

<a id="nas-backup-restoration"></a>

## How is an independent NAS backup restored?

**Work on:** an isolated recovery host, not the live receiver or live NAS share.
**Prerequisites:** verified restic and Python 3, independently held repository/password and recorded
repository/snapshot IDs, the offline reader kit and private encrypted recovery storage.

1. On an authorized, isolated recovery host, retrieve the independent restic
   repository, separately held password, and the offline reader kit containing
   `logging_checkpoint.py`, `logging_io.py`, `logging_health.py` and `logging_projection.py`.
   Keep all four files from the same accepted revision together; verification imports the
   projection module even when no search projections are selected. Preserve the
   source repository; select a new empty restore directory, never the live share.
2. Select the protected paths and inspect the recorded snapshots:

   Run on **the independent isolated recovery workstation**.

   ```bash
   read -r -e -p 'Independent restic repository path: ' RESTIC_REPOSITORY
   read -r -e -p 'Recovery password file path: ' RESTIC_PASSWORD_FILE
   export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
   restic cat config
   restic snapshots --tag security-logging --json
   restic check --read-data
   ```

   JSON lists the full snapshot `id` required by the restore guard; the short table ID is insufficient.
   Compare the repository ID with the independent custody record. Require readable snapshots and a
   completed integrity check; stop on mismatched identity, corruption or missing credentials. [2]

3. Choose the incident's known-good snapshot and an empty disposable target:

   Run on **the independent isolated recovery workstation**.

   ```bash
   set -euo pipefail
   umask 077
   read -r -p 'Full approved 64-character snapshot ID: ' LOGGING_SNAPSHOT
   read -r -e -p 'NEW absolute restore directory under a private existing parent: ' LOGGING_RESTORE
   [[ "$LOGGING_SNAPSHOT" =~ ^[a-f0-9]{64}$ ]]
   case "$LOGGING_RESTORE" in /*) ;; *) exit 1 ;; esac
   test "$(realpath -e "$(dirname "$LOGGING_RESTORE")")" = "$(dirname "$LOGGING_RESTORE")"
   mkdir -m 0700 "$LOGGING_RESTORE"
   restic restore "$LOGGING_SNAPSHOT" --target "$LOGGING_RESTORE" --verify
   ```

   `mkdir` must succeed on a new path outside the original archive. A failed attempt is retained for
   diagnosis; choose another new target rather than merging a retry into it. Restore keeps the saved path tree. [3]

   Restic preserves the original path tree beneath that target. Locate the restored
   archive root containing `<collector>/checkpoints/` and `<collector>/chunks/`, then
   verify using the kit's script from its own directory:

   Run on **the isolated recovery host from the retained reader kit's script directory**.

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

Restic command references checked 2026-11-08; filesystem guidance checked 2026-10-16.

1. [Linux ext4 read-only mounting and journal-replay behavior](https://www.kernel.org/doc/html/latest/admin-guide/ext4.html#options)
2. [Restic snapshot inspection and repository integrity checks](https://restic.readthedocs.io/en/stable/045_working_with_repos.html).
3. [Restic clean-target restoration and path layout](https://restic.readthedocs.io/en/stable/050_restore.html).
