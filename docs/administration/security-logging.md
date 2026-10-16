# Security logging operations

**Owner:** Tier 0 for protected evidence; each tier owns its producers.
**Design:** [security logging](../architecture/operations/security-logging.md).
**Prerequisites:** accepted [receiver/archive integration](../deployment/stage-1-logging/README.md)
and recorded failure, retention, access and recovery contracts.

## Table of contents

- [Routine checks](#routine-checks)
- [Maintenance and incidents](#maintenance-and-incidents)
- [Offline investigation](#offline-investigation)
- [Automation boundary](#automation-boundary)
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
| Retention | Verify enforced locks and approved expiry; receiver credentials cannot change retention or delete evidence |
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
reconciles the host baseline only. It does not upgrade receivers, rotate evidence,
change retention or prove HA. Product operations remain project-owned procedures.
Tier 1 search-index maintenance never grants authority to alter Tier 0 evidence.

## References

Source checked 2026-10-16.

1. [Linux ext4 read-only mounting and journal-replay behavior](https://www.kernel.org/doc/html/latest/admin-guide/ext4.html#options)
