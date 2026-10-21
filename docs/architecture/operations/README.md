# Operations and workloads

Operations supplies independent visibility, inventory documentation, recovery and
workload governance. Every stateful resource has a recovery owner, regardless
of whether its monitoring is local or supplied by shared operational services.
These capabilities cover the whole [platform architecture](../README.md).

## Table of contents

- [Completed design](#completed-design)
- [Components and interfaces](#components-and-interfaces)
- [Design choices](#design-choices)
- [Design constraints](#design-constraints)
- [Detailed views](#detailed-views)
- [Realization](#realization)

## Completed design

Observability diagnoses the running system using logs, metrics and distributed
traces. Security Logging and Audit preserves protected evidence. Independent
failure detection and recovery remain usable when operational dashboards fail.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T2["Tier 2 / workloads"]
    Producers["Applications / local collection"]
  end
  subgraph T1["Tier 1 / Observability"]
    subgraph Cluster["Platform Kubernetes / separate workloads"]
      direction LR
      Collection["Telemetry gateways"]
      Backends["Metrics / log and trace search<br/>Scoped queries and UIs"]
      Collection -->|Logs / metrics / traces| Backends
    end
  end
  subgraph T0["Tier 0 / independent control visibility"]
    direction LR
    Evidence["Security Logging and Audit<br/>Protected intake / original evidence"]
    Health["Independent health checks<br/>External alert delivery"]
    Evidence ~~~ Health
  end
  T2 -->|Application telemetry| T1
  T2 -->|Security / audit submissions| T0
  T1 -->|Security / audit submissions| T0
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  class T2,T1 services
  class Cluster runtime
  class T0,Evidence,Health control
```

NetBox documents approved inventory; Headlamp supplies scoped cluster operations.
Their interfaces complement telemetry without replacing tier-local bootstrap inputs
or independent recovery records. General telemetry can be Tier 1-owned; Tier 0
control visibility has an independently recoverable path. Syslog and audit evidence
from every tier remain in protected Tier 0 custody; Observability receives only
approved copies, with application-owner read scopes separate from security readers.

## Components and interfaces

| Component | Function and boundary |
| --- | --- |
| Inventory documentation | Describe deployed infrastructure; never replace tier-local bootstrap inputs |
| Cluster interface | Expose scoped cluster operations; not blanket infrastructure administration |
| Telemetry collectors | Receive, normalize and route signals under approved access policy |
| Protected log intake | Accept all tiers' security submissions without granting archive queries, editing or deletion |
| Observability backends | Store operational logs, metrics, traces and approved evidence copies; no authority over Tier 0 originals |
| Security evidence archive | Retain original security/audit records under Tier 0 custody, independently recoverable |
| Recovery storage | Retain backups and restore evidence outside the service being recovered |
| Workload governance | Isolate consumers and authorize changes without transferring Tier 0 control |

| Boundary | Interface and connected function |
| --- | --- |
| Supplied to producers | Approved telemetry and security-event ingestion endpoints |
| Supplied to operators | Scoped inventory, cluster operations, signal queries and owned alert delivery |
| Supplied to recovery owners | Retained backups, archives and restoration evidence outside the protected service |
| Consumed from tier owners | Infrastructure records, workload scope, retention requirements and recovery responsibilities |
| Consumed from runtime and access services | Signals, backup streams, cluster APIs, authentication and service-local authorization |
| Consumed from independent arrangements | Recovery storage and failure detection outside the affected service or cluster |

## Design choices

| Decision | Alternatives | Consequence |
| --- | --- | --- |
| Observability placement | Native Kubernetes workloads; separate-role VMs or an existing service as alternatives | [Telemetry design](telemetry.md) separates resource/scaling budgets and retains Tier 0 outage independence |
| Sharing | Central platform service; isolated project collectors/backends | Isolation follows access, retention and trust requirements |
| Recovery target | Dedicated backup service; approved external target; protected offsite copy | Storage availability alone is not tested restore |
| Log retention | NAS snapshots/backups with trusted administration; qualified retention locks | [Archive choices](log-retention.md) make deletion authority and growth recommendations explicit |
| Workload runtime | Linux VMs, image-based Linux, Kubernetes applications | Definitions and inventory stay tier-local; runtime changes need explicit lifecycle ownership |
| Workload execution | Reviewed operator action; bounded self-service | The latter needs the [request contract](../compute/provisioning.md), not unrestricted CI credentials |

NetBox, Headlamp and monitoring are reference implementations, not prerequisites
for creating the infrastructure on which they run.

<a id="maturity"></a>

## Design constraints

| Concern | Required property |
| --- | --- |
| Visibility | Failure detection remains available outside the observed cluster |
| Access and retention | Signal stores enforce the sensitivity and retention requirements of their sources |
| Recovery | Backups, custodians and recovery targets remain independent of the protected service |
| Governance | Workload requests cannot bypass tier ownership or infrastructure authorization |

Hardware custody and application-state recovery remain separate responsibilities.
A central dashboard alone is insufficient for independent failure detection.

## Detailed views

- [Runtime flows](../runtime-flows.md#data-visibility-and-recovery) connects service data, visibility and recovery across domains.
- [Telemetry design](telemetry.md) expands collection, signal backends, retention and placement alternatives.
- [Security logging](security-logging.md) owns append-only submission, segmented reads and the evidence durability contract.
- [Log archive choices](log-retention.md) compares NAS-backed recovery with retention locks and explains role separation as access grows.
- [Service boundaries](../service-boundaries.md) defines shared and isolated operational services.
- [Workload request contract](../compute/provisioning.md) connects governance to privileged execution.
- [Component allocation](../reference-platform.md#service-placement) locates inventory, cluster interfaces and supporting services.

## Realization

Implementation procedures: [foundational logging](../../deployment/stage-1-logging/README.md),
[independent monitoring](../../deployment/stage-4-secrets/monitoring.md),
[Observability](../../deployment/stage-6-observability/README.md),
[operational tools](../../deployment/stage-4-secrets/README.md#step-2-add-operational-tools)
and [operational acceptance](../../deployment/stage-4-secrets/README.md#step-3-integrate-access-and-recovery).
Recurring work belongs in [administration](../../administration/README.md).
