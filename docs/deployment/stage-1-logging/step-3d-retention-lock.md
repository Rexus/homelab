# Step 3d: Retention-locked log archive

Use qualified storage-enforced retention when retained versions must survive
privileged deletion attempts. This can supplement the [NAS path](step-3c-nas-archive.md)
or supply the primary archive; it does not require moving Tier 0 intake into a cloud.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Branch from:** [Step 3](README.md#step-3-protect-and-verify-retained-evidence), when protected versions must survive privileged deletion attempts.
**Change:** Qualify storage-enforced version retention and its custody/recovery boundary.
**Return:** [Step 3](README.md#step-3-protect-and-verify-retained-evidence) to record actual lock and replica evidence.
**Design:** [choice B: locked retention](../../architecture/operations/log-retention.md).
**Prerequisites:** working collection, independently administered WORM storage,
approved retention/cost policy and separately protected recovery keys.
**Automation boundary:** storage provisioning/policies, archive publication,
replication verification and data-access auditing remain selected product integration.
The supplied receiver does not upload or lock objects.

## Contents

- [Step 1: Qualify storage and privileges](#step-1-qualify-storage-and-privileges)
- [Step 2: Define the archive checkpoint](#step-2-define-the-archive-checkpoint)
- [Step 3: Prove enforcement and restoration](#step-3-prove-enforcement-and-restoration)
- [Next](#next)
- [References](#references)

## Step 1: Qualify storage and privileges

1. Select the actual product and lock mode. For S3 Object Lock, enable versioning
   and approved default retention; inspect each written version's protection.
   Governance permits an authorized bypass. Choose compliance when the requirement
   excludes such bypass during the protected period. Test with disposable objects
   and short approved retention before creating long-lived, non-deletable test data. [1]
2. Separate writer, reader and retention/custody identities. Writers cannot delete
   retained versions, bypass locks, change bucket retention or administer recovery
   keys. Give readers only approved scopes; protect access records outside their control.
3. Configure independent recovery and key custody. Qualify a compatible on-premises
   service against the same contract rather than assuming S3 API compatibility
   proves enforcement. Record storage-provider/account destruction as a residual risk.

## Step 2: Define the archive checkpoint

1. Select and configure the archive publisher for portable records, source catalogue
   and segment manifests. Verify checksums, version IDs, effective mode and retain-until
   dates. A successful socket write or multipart part upload is not a completed object.
2. If another copy is required before acceptance, verify that specific replica and
   its protection before releasing source/collector copies. S3 replication is
   asynchronous; configuring it does not prove a particular version has replicated. [2]
3. Enable object-level read/write access recording to independent custody. For AWS,
   explicitly configure CloudTrail data events; do not rely on the default management
   event history for object reads. Qualify the equivalent mechanism for other products. [3]

Retain local collection and backlogs through storage outages. The publisher must
retry safely without deleting uncommitted data; alarm on age, capacity, failed
publication/replication and missing audit delivery. Locks do not replace backups
or protect records that never reached a completed archive checkpoint.

## Step 3: Prove enforcement and restoration

1. Follow the [logging drill](../../administration/logging-drill.md). Test writer,
   reader and privileged identities against version deletion, replacement and
   retention shortening. New versions/delete markers must not hide the retained
   version from the recovery procedure. Test the actual lock mode, not only IAM denial.
2. Restore recorded object versions, manifests and keys on an isolated target.
   Reconcile covered events and independent access records; measure RPO/RTO.
3. Record **B: Retention-locked**, exact provider/mode, retained version identifiers,
   required replica proof and key/account custody in the project's
   `docs/administration/logging-evidence.md` and architecture selection.

## Next

Return to [Stage 1, Step 3](README.md#step-3-protect-and-verify-retained-evidence).
Retain [NAS-backed recovery](step-3c-nas-archive.md) where useful; migrating to locks
does not retroactively protect old mutable copies or justify deleting them early.

## References

Sources checked 2026-10-19.

1. [S3 Object Lock version protection and modes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)
2. [Object Lock replication, checksums and key limitations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-managing.html)
3. [S3 object-level CloudTrail data events](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging.html)
