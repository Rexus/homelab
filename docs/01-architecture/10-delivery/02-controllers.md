# Release orchestration and reconciliation

Delivery must answer two questions: which release may advance, and how the running system stays
aligned with that accepted choice. Separate these responsibilities and their authority.

<a id="authority-and-ownership"></a>

```mermaid
%%{init: {"theme":"base","fontFamily":"Arial, sans-serif","themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc","fontFamily":"Arial, sans-serif","fontSize":"14px"},"flowchart":{"nodeSpacing":16,"rankSpacing":24,"padding":10,"subGraphTitleMargin":{"top":4,"bottom":12}}}}%%
flowchart BT
  subgraph T2["Tier 2"]
    Workload["Application runtimes"]
  end
  subgraph T1["Tier 1"]
    direction LR
    Platform["Managed<br/>services"]
    D["Release<br/>orchestration"]
    PF["Reconciliation"]
    Release["Accepted state<br/>Platform / apps"]
    Platform ~~~ PF
    PF -- "Apply state" --> Platform
    PF -- "Read state" --> Release
    D -- "Promote app" --> Release
  end
  subgraph T0["Tier 0"]
    direction LR
    Control["Control services"]
    F["Control<br/>reconciliation"]
    Approved["Independent<br/>accepted state"]
    Control ~~~ F
    F -- "Apply state" --> Control
    F -- "Read state" --> Approved
  end
  T0 ~~~ T1
  T1 -. "Optional approved integration" .-> T2
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef action fill:#fcebdc,stroke:#a16c43,color:#5b3921
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  class Workload,Platform,PF services
  class D action
  class F,Control control
  class Release,Approved data
  classDef tier0 fill:#c8c8c8,stroke:#707070,color:#262626
  class T0 tier0
  classDef tier1 fill:#e0e0e0,stroke:#8c8c8c,color:#363636
  class T1 tier1
  classDef tier2 fill:#f2f2f2,stroke:#a6a6a6,color:#404040
  class T2 tier2
```

*Figure: Release orchestration advances application intent. Reconciliation reads that intent and
controls its authorized resources. Platform and application state have separate write permissions;
Tier 0 retains independent reconciliation and recovery. The boxes are logical roles, not products.*

## Contents

- [Responsibilities](#responsibilities)
- [Dependency ordering](#dependency-ordering)
- [Failure and recovery](#failure-and-recovery)
- [Selection criteria](#selection-criteria)
- [Realization](#realization)

## Responsibilities

| Capability | Responsibility | Authority boundary |
| --- | --- | --- |
| Release orchestration | Coordinate a release request, policy/evidence checks, required approval, promotion and outcome verification | Submit only the accepted application change; no infrastructure or platform administration |
| Desired-state reconciliation | Observe accepted state, compare it with runtime state, apply scoped changes and correct drift continuously | One active owner per resource; separate platform and application identities |
| Dependency ordering | Hold a component until declared prerequisites and lifecycle checks are ready | Operates within the reconciliation scope; readiness does not authorize a release |
| Change authorization | Bind an authenticated decision to the exact artifact, configuration, destination and proposed change | The credential holder rejects unapproved or changed operations, including direct API calls |
| Infrastructure lifecycle and bootstrap | Provision hosts/clusters and establish the minimum reconciliation runtime | Independent protected execution and recovery authority |

These are responsibilities, not a requirement for five services. A product may implement several
roles if their permissions and guarantees remain enforceable. The selected design uses accepted
state as the handoff: the release workflow publishes intent, and the reconciler owns runtime writes.
The [release sequence](README.md#application-delivery) shows that handoff;
[approval controls](04-approval-controls.md) define which changes may cross it.

## Dependency ordering

Continuous reconciliation includes dependency coordination: controllers must exist before their
custom resources, storage before databases, and restored compatible data before application writers.
File order alone establishes none of those conditions.

```mermaid
%%{init: {"fontFamily":"Arial, sans-serif","themeVariables":{"fontFamily":"Arial, sans-serif","fontSize":"14px"}}}%%
sequenceDiagram
  participant Reconcile as Reconciliation
  participant State as Accepted state
  participant Data as Data service
  participant App as Application
  Reconcile->>State: Read selected revision<br/>Dependencies / checks
  Reconcile->>Data: Apply accepted data-service configuration
  Data-->>Reconcile: Not ready<br/>Restore incomplete
  Note over Reconcile,App: Dependent application remains held
  Reconcile->>Data: Reobserve readiness<br/>and restore evidence
  Data-->>Reconcile: Accepted generation<br/>Data checks passed
  Reconcile->>App: Apply accepted consumer configuration
  App-->>Reconcile: Observed revision / health
  loop While accepted state remains active
    Reconcile->>App: Compare desired / observed state<br/>Correct drift
  end
```

*Figure: Dependency gates delay consumers until their prerequisites satisfy the declared checks.
The loop maintains accepted state; it does not choose a new release or substitute for native data recovery.*

This is **desired-state reconciliation with dependency ordering**. Release orchestration coordinates
the wider release workflow, which may include human decisions, tests and promotion between targets.
Neither function's successful status alone proves end-to-end service availability.

## Failure and recovery

- A rejected or changed proposal must not advance accepted state. An unavailable approval service
  cannot grant access to the publication or target credentials.
- An unavailable source or release portal must not authorize destruction of running workloads.
  Reconciliation reports a blocked condition and retains the last accepted intent.
- Maintenance pauses the actual reconciliation graph, drains in-flight work and controls application
  writers. It preserves unrelated scopes and intentional pauses before controlled resumption.
- Recovery uses independently retained state, artifacts, keys and native data backups. Restore
  prerequisites before consumers, fence stale executions, verify data, then resume accepted state.

Tier 1 delivery holds no Tier 0 runtime credentials or infrastructure state authority.
[Infrastructure execution](../04-hosting/02-provisioning.md) and
[recovery](../11-operations/04-backup-recovery.md) retain their own protected paths.

<a id="choices"></a>

## Selection criteria

Select products against the responsibilities above: scoped identities, authenticated approval,
immutable artifact/configuration identity, exact revision reporting, dependency/health gates,
controlled pause/resume, drift correction and independent recovery. Record administrative bypasses
and edition/version limits. A product name or pipeline diagram proves none of those controls.

For another deployment model, a pipeline can own runtime writes directly. That changes the ownership
contract: another reconciler must not compete for the same objects. A local controller in another
tier is likewise an explicit scope selection, not an inherited permission grant.

## Realization

[D-041](../../07-decisions/README.md#d-041) records the selected product composition.
The [Tier 1 implementation](../../08-reference/tier-1-delivery.md) maps each product to these roles;
its [approval profile](../../08-reference/spinnaker-approval.md) records exact native behavior and enforcement.
Follow [Stage 7](../../03-deployment/stage-07-delivery/README.md) to deploy it and
[delivery operations](../../05-operations/05-delivery.md) to maintain it.
