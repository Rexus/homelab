# Protected security logging

Syslog, audit and security events are a Tier 0 evidence capability, not an ordinary
Tier 1 dashboard service. All tiers submit approved records through restricted
intake. Only explicitly authorized system-administrator/security-reader roles
can investigate raw evidence. Producers cannot read, edit or delete it.

**Security Logging and Audit** provides traceability and recoverable evidence.
[Observability](03-observability.md) diagnoses the running system using logs, metrics
and distributed traces. Request tracing is not audit traceability, and searchable
copies do not replace retained originals.

## Table of contents

- [Authority and flow](#authority-and-flow)
- [Segmented access](#segmented-access)
- [Offline-readable evidence](#offline-readable-evidence)
- [Durability and availability](#durability-and-availability)
- [Protected retention](#protected-retention)
- [Realization](#realization)
- [References](#references)

## Authority and flow

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":16,"rankSpacing":20,"padding":10},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T2["Tier 2 / workloads"]
    direction LR
    Sources["Local producers<br/>Queued submissions"]
    Developer["Application owner<br/>Approved app view only"]
    Sources ~~~ Developer
  end
  subgraph T1["Tier 1 / Observability"]
    direction LR
    Search["Scoped searchable<br/>copies"]
    Query["Authorized queries<br/>No raw-evidence authority"]
    Query ~~~ Search
  end
  subgraph T0["Tier 0 / Security Logging and Audit"]
    direction LR
    Logging["Protected intake<br/>Original evidence"]
    Readers["Audited readers<br/>Producers submit only"]
    Retention["Independent<br/>retained copies"]
    Custodians["Separate retention<br/>custody"]
    Readers ~~~ Logging ~~~ Retention ~~~ Custodians
  end
  T2 ~~~ T1 ~~~ T0
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class Sources,Developer,Query,Readers actor
  class Logging control
  class Retention data
  class Custodians custody
  class Search services
  classDef tier0 fill:#d8cbb9,stroke:#83715a,color:#352a1e
  class T0 tier0
  classDef tier1 fill:#e9e2d8,stroke:#968976,color:#44382a
  class T1 tier1
  classDef tier2 fill:#f6f3ef,stroke:#aca59b,color:#4b443c
  class T2 tier2
```

*Figure: Producers submit, application owners read approved copies, and security readers
investigate originals. Independent retention custody remains inside Tier 0 ownership.*

Every tier submits approved security records to Tier 0. Tier 1 receives only
approved projections; application owners read their own scope there. This is an
authority map, not a prescribed VM count, storage product or connectivity allow rule.

Submission rights are not filesystem, database or object-store credentials.
Receivers validate authenticated source identity, stamp tier/project ownership,
and reject attempts to claim another source's identity. Client-provided labels
alone never authorize a read scope. Rate/size limits and separate queues prevent
a compromised workload from exhausting the privileged evidence path.

System, authentication, infrastructure-change and audit records from every tier
follow this protected path. Application-log retention is selected per stream;
approved developer copies can be published without granting raw-archive access.
Operational logs, metrics and distributed traces use the separate [telemetry design](03-observability.md).
Offline custody has no online logging route; authorized evidence transfer is a ceremony operation.

## Segmented access

| Principal | Allowed operation | Explicitly denied |
| --- | --- | --- |
| Registered producer / local relay | Append new records to its assigned intake | Archive queries, changing existing records, deletion, another producer's namespace |
| Receiver / archive writer | Create retained records through a narrow service identity | Retention-policy administration, broad query access, modifying retained versions |
| Authorized system administrator / security reader | Read the approved security scope; export under policy | Routine modification/deletion of evidence; unlogged investigation |
| Application owner / developer | Read approved copies of that application's logs | Other applications, raw infrastructure/audit records and archive administration |
| Retention custodian | Govern approved retention/expiry under the selected custody model | Undocumented destructive authority; lock bypass where the chosen model forbids it |
| Tier 1 analytics administrator | Operate searchable copies | Authority over the Tier 0 evidence archive |

The reference publishes separately routed/indexed copies to Tier 1, with redaction
where required. [Search read boundaries](03-observability.md#read-boundaries) define the
OpenSearch permission model, dashboard separation and cross-tenant checks. [1][2]
SSO authenticates the user; application authorization grants the selected scope.

A Tier 1 administrator may damage searchable copies,
but has no credentials or storage path that can erase the Tier 0 originals or their backups.
Reader roles remain separate from retention custodians even when one person holds both roles.

## Offline-readable evidence

The evidence format must survive loss of the running environment. An intact log-data
volume and an independently held recovery kit are sufficient for authorized inspection;
FreeIPA, the identity provider, Kubernetes, Vault and OpenSearch are not required.

| Retained material | Required property |
| --- | --- |
| Records | UTF-8 JSON Lines or documented syslog text segments, preserving original messages, authenticated source identity, tier/project scope and source/receive timestamps |
| Interpretation | Schema, source catalogue, timezone/clock notes and available sequence ranges stored with the records; no inventory service required |
| Verification | Segment manifests and integrity metadata; trusted verification material retained independently of the evidence volume |
| Recovery kit | Offline runbook, filesystem/volume layout, reader/decompression tools and separately protected decryption/recovery keys |

The receiver writes this portable representation as part of its durable evidence path,
not as an occasional export from a search database. Binary queues and search indexes
are not the only retained copy. Use native text/JSON templates and supported escaping
rather than constructing records from untrusted strings. [6]

Encryption remains required where the storage policy calls for it; offline readability
does not mean an unencrypted disk or unrestricted physical access. Recovery keys cannot
exist only inside the system being recovered. The contract covers an intact logical
volume, not an arbitrary member disk from a RAID or distributed storage pool.

[Backup policy](../../05-operations/06-resilience/backups/virtual-machines.md#backup-policy) owns independent
copies and recovery objectives. [Offline investigation](../../05-operations/06-resilience/protected-logging.md#offline-investigation)
owns preservation and read-only inspection. Tier 1 search indexes are rebuildable projections.

## Durability and availability

The objective is **no loss of accepted records within a declared failure envelope**,
not an unconditional promise that every emitted event can always be recovered.
The contract names where an event becomes accepted and which durable copies survive
before its sender may release it. Transport acknowledgement alone does not prove
replicated archive commitment. Duplicates may occur; preservation takes priority
over claiming exactly-once delivery.

The initial NAS profile is intentionally asynchronous and bounded-loss: native
forwarders release on transport submission, while protected acceptance applies only
to the checkpoint covered by the required snapshot/independent copy. The interval
before that boundary is exposed. This simpler profile is not the replicated-intake
objective below; select that stronger contract when its residual risk is unacceptable.

The sequence follows one published checkpoint. Snapshot and independent-backup schedules
are separate operations; transport submission does not wait for either of them.

```mermaid
sequenceDiagram
  participant Producer as Producer / local queue
  participant Receiver as Protected receiver
  participant Recovery as Independent backup host
  participant NAS as Independent NAS archive
  Producer->>Receiver: Submit authenticated records
  Note over Producer,Receiver: Native queue releases on transport submission
  Receiver->>Receiver: Write portable local records / fsync
  Receiver->>NAS: Publish complete chunks and checkpoint
  NAS-->>Receiver: Filesystem write / flush returns
  Note over Receiver,NAS: Qualify actual NAS persistence separately
  par Commissioned storage schedule
    NAS->>NAS: Complete storage-owned snapshot
  and Independent backup schedule
    Recovery->>NAS: Read and verify checkpoint files
    NAS-->>Recovery: Records, manifests and catalogue
    Recovery->>Recovery: Encrypted restic<br/>backup and check
  end
  Note over NAS,Recovery: Protected acceptance covers only the required snapshot / copy
```

*Figure: Sender release, local persistence, NAS publication and protected acceptance are
different boundaries. Independently scheduled snapshots and backups expose a measurable tail.*

The [checkpoint writer](../../../tier-0/ansible/roles/logging_archive/files/logging_checkpoint.py)
publishes complete prefixes; the [backup job](../../../tier-0/ansible/roles/logging_backup/templates/backup.sh.j2)
pulls verified files from an independent host. NAS snapshot commissioning remains
storage-owned work. The [pipeline contract](../../08-reference/logging-pipeline.md#commit-and-failure-boundaries)
defines each completion boundary and its limits.

The following table describes that stronger objective, not the acceptance criteria for
the single-receiver NAS main path.

| Boundary | Required property |
| --- | --- |
| Producer | Durable local spool, stable identity/sequence where supported, retry and measurable gaps; no premature acknowledgement of an unprotected event |
| Receiver | Redundant hosts and independent storage/power failure domains; authenticated transport, persistent queues and tested crash recovery |
| Commit | Explicit durability/flush/replication semantics; if a required copy is unavailable, retain the upstream event or apply the declared backpressure/fail-closed policy |
| Retention | Independently protected archive copies and recovery keys; receiver failover is not a backup |
| Capacity | Spool/archive sizing for peak rate and tolerated outage; alarms before exhaustion; per-source isolation |
| Detection | Missing-source/heartbeat, queue depth, write/replication failure, clock skew and restore checks; independent alert path |

A single receiver VM is the Stage 2 main-path choice with declared failure limits;
it is **not the HA acceptance state**.
Two receivers alone are also insufficient: a VIP changes routing, not acknowledgement,
replication or storage durability. Supported source failover or dual submission needs
end-to-end sequence/count verification, including retries and duplicates.

UDP syslog cannot detect or repair datagram loss. [3] Plain TCP and disk-assisted
queues do not by themselves guarantee audit-grade crash durability; orderly-shutdown
queue persistence is distinct from protection against sudden power loss. [4]
Legacy sources use a nearby supported relay where possible, with the unprotected
first hop explicitly accepted as a residual gap. No downstream receiver can restore
an event that a source never emitted or persisted.

## Protected retention

Select [NAS-backed retention or storage-enforced locks](02-log-retention.md#choose-the-protection-boundary)
according to the trusted-administrator boundary. The archive design owns
[role separation as access grows](02-log-retention.md#roles-and-growth) and
[checkpoint and recovery limits](02-log-retention.md#durability-and-recovery).

Append-only permissions do not make a VM disk or ordinary NAS share immutable
against its administrators; the selected retention model defines privileged
deletion protection. [5] Hashes/signatures detect alteration but do not prevent deletion.
Independent backups, offline readability and denied producer/query deletion remain
required under either choice. Failure and privilege limits must be recorded explicitly.

## Realization

[Foundational syslog](../../03-deployment/stage-2-logging/README.md) owns
bootstrap, receiver integration and acceptance. The initial implementation is a
dedicated syslog-ng OSE network receiver, alongside the untouched OS logger, with
independent trust, raw messages and portable local JSON records. rsyslog is a valid
alternative under the same contract; the choice does not establish reliability superiority.
The [receiver contract](../../08-reference/syslog-receiver.md) and
[pipeline contract](../../08-reference/logging-pipeline.md) distinguish local collection,
asynchronous NAS custody and stronger HA integration. [Monitoring](../../03-deployment/stage-6-secrets/procedures/independent-monitoring.md)
adds critical health and alerts; [Observability](../../03-deployment/stage-8-observability/README.md)
adds approved search copies. [Logging administration](../../05-operations/06-resilience/protected-logging.md)
owns recurring access, gap, capacity and restore checks. The receiver does not
claim a lossless or immutable archive.

## References

Sources checked 2026-10-16.

1. [OpenSearch users, roles and index/document permissions](https://docs.opensearch.org/latest/security/access-control/users-roles/)
2. [OpenSearch Dashboards tenant scope](https://docs.opensearch.org/latest/security/multi-tenancy/tenant-index/)
3. [RFC 5426: UDP syslog reliability](https://www.rfc-editor.org/info/rfc5426/)
4. [rsyslog reliable forwarding and crash-durability limits](https://docs.rsyslog.com/doc/tutorials/reliable_forwarding.html)
5. [S3 Object Lock retention modes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)
6. [rsyslog text/JSON templates and safe encoding](https://docs.rsyslog.com/doc/configuration/templates.html)
