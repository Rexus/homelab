# Log archive and retention choices

Protected logging keeps evidence outside the collector's destruction boundary.
An independent NAS is a valid storage target; cloud storage is not required.
The selected retention model determines which administrators remain trusted.
The parent [security-logging design](security-logging.md) owns intake, source
identity, segmented reads and the accepted-record durability contract.

## Contents

- [Choose the protection boundary](#choose-the-protection-boundary)
- [Roles and growth](#roles-and-growth)
- [Durability and recovery](#durability-and-recovery)
- [Review triggers](#review-triggers)
- [Realization](#realization)
- [References](#references)

## Choose the protection boundary

| Choice | A: NAS snapshots and independent backups | B: Storage-enforced retention locks |
| --- | --- | --- |
| Suitable starting point | Homelab or small trusted operator team | Environments requiring protection from privileged deletion |
| Archive | Dedicated NAS dataset/share outside the collector VM | Qualified WORM target, such as an S3 Object Lock service |
| Protection | Storage-owned snapshots plus an independently recoverable backup | Locked object versions for an approved retention period, plus independent recovery copies |
| Trusted authority | NAS/backup administrators can ultimately delete their copies | Depends on lock mode, storage operator and key/account custody |
| Principal limit | Not immutable against NAS/backup administration; snapshot/backup lag exposes a tail | Does not protect unavailable/deleted keys, every provider failure or records not yet committed |
| Reference deployment | [3c: NAS-backed archive](../../deployment/stage-1-logging/step-3c-nas-archive.md) | [3d: Retention-locked archive](../../deployment/stage-1-logging/step-3d-retention-lock.md) |

**Recommendation:** use A when trusted storage administration and a measured
recovery-point objective are acceptable. Use B when deletion by a privileged
operator must be prevented during retention. Both can coexist: a NAS can provide
local recovery while locked copies provide a stronger deletion boundary.
More users do not automatically require S3 or a cloud dependency.

For example, UniFi Drive documents snapshots that administrators can delete. [1]
They are recovery points, not evidence of WORM enforcement. S3 Object Lock instead
protects individual versions: governance mode permits an authorized bypass;
compliance mode prevents version deletion or retention shortening during its
term, subject to provider/account and key-custody limits. [3]
An S3-compatible API alone does not establish those guarantees.

## Roles and growth

| Role | Small homelab | Growing team or business |
| --- | --- | --- |
| Producer | Append to intake; no NAS/archive credentials | Same boundary, separately registered sources |
| Collector/archive writer | Dedicated service account, not the NAS owner | Per-writer scope; no snapshot, backup or retention administration |
| Reader | Explicit security-reader role; no general family/developer access | Named read scopes and independently retained access records |
| Storage/retention custodian | Same person may hold this role, using separate admin credentials | Separate administrative role/person and approval for destructive changes |
| Recovery custodian | Independently held keys and offline reader kit | Tested delegated recovery; no sole dependence on one employee or SSO |

One person holding several roles is acceptable under A's declared trust model.
Separate credentials still reduce accidental deletion and exposure through the
collector or a daily workstation. They do not protect against that person's
fully privileged actions. Ordinary user/application roles never inherit those powers.

The archive dataset and its administration remain Tier 0-owned even on a NAS that
also hosts unrelated data. General shares, developer analytics and Tier 1 search
administration receive no authority over retained security evidence.
Reader actions require an access-recording mechanism appropriate to the selected
storage; a read-only share alone does not audit its reads.

## Durability and recovery

| Boundary | Required distinction |
| --- | --- |
| Collector to NAS | A successful transfer is not proof of a completed storage snapshot or independent backup |
| Snapshot | Protects a checkpoint from share-writer changes only if that writer cannot remove the snapshot; storage administrators remain trusted under A |
| Retention lock | A completed, verified locked version is not proof that a required replica has committed |
| Independent copy | Another directory, snapshot or RAID member in the same storage pool is not a separate device/site failure domain |
| Source release | NAS main path releases native queue items on transport submission, not protected commit; retain original journals/files for the declared replay window and measure the exposed tail. A stronger replicated-intake path must explicitly gate release on its durable acknowledgement |
| Recovery | Portable records, source catalogue, integrity references and separately held keys/tools remain usable without identity services or Kubernetes |

Record checkpoint lag and the exposed unprotected tail, not only the configured
schedule. Storage snapshots do not establish zero-RPO logging, and a NAS shared
with VM disks is not independent of those disks' storage failure. UniFi Drive
supports external backup destinations; that is a separate copy, not an automatic
consequence of enabling snapshots. [2]

## Review triggers

Revisit A's trusted-admin assumption when administrator numbers, external access,
sensitive data or contractual requirements change. Split privileges before granting
new access; select B if the revised threat model includes malicious retention
administrators. Preserve old copies through migration and verify historical
coverage rather than assuming a new lock protects previously mutable records.

## Realization

Select A or B at [Stage 1, Step 3](../../deployment/stage-1-logging/README.md#step-3-protect-and-verify-retained-evidence).
[Logging administration](../../administration/security-logging.md) owns recurring
checks; the [fault/restore drill](../../administration/logging-drill.md) records the
chosen protection boundary and its demonstrated limits. Implementation coverage
is recorded in the [support map](../../reference/implementation-support.md).

## References

Sources checked 2026-10-19.

1. [UniFi Drive snapshots and administrator deletion](https://help.ui.com/hc/en-us/articles/33317752912919-Understanding-System-Data-Others-in-UniFi-Drive)
2. [UniFi Drive independent backup destinations](https://help.ui.com/hc/en-us/articles/30961935781655-Troubleshooting-UNAS-Backup-Issues)
3. [S3 Object Lock modes and version protection](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)
