# Delivery and software lifecycle

Software passes through controlled intake, reviewed source, builds, approved artifacts
and scoped release delivery. These functions have different owners and can use different
tools; a downloaded package or successful build alone is not release approval.

## Contents

- [Completed design](#completed-design)
- [Application delivery](#application-delivery)
- [Components and interfaces](#components-and-interfaces)
- [Design choices](#design-choices)
- [Design constraints](#design-constraints)
- [Realization](#realization)

## Completed design

The view places lifecycle functions by ownership. Source authority and approved
artifact supply sit to the right of their build/deployment consumers. These are
stable capabilities, not a pipeline execution order or an installed-service inventory.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":16,"rankSpacing":20,"padding":10,"subGraphTitleMargin":{"top":4,"bottom":10}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T2["Tier 2 / software consumers"]
    direction LR
    Cache["Outbound proxy/cache<br/>DMZ intake support"]
    Workloads["Application runtimes<br/>Release consumers"]
    Cache ~~~ Workloads
  end
  subgraph T1["Tier 1 / shared software lifecycle"]
    direction LR
    Build["General builds / tests<br/>Scoped job runtime"]
    Deploy["Application delivery<br/>Scoped releases"]
    subgraph Supply["Software authority"]
      direction TB
      Source["Source control<br/>Reviewed inputs"]
      Artifacts["Approved artifacts<br/>Mirrors and registry"]
      Source ~~~ Artifacts
    end
    Build ~~~ Deploy ~~~ Supply
  end
  subgraph T0["Tier 0 / protected control"]
    direction LR
    ControlDelivery["Control-service delivery<br/>Tier 0 accepted sources"]
    Hosting["Infrastructure control<br/>Resource lifecycle"]
    ControlDelivery ~~~ Hosting
  end
  T2 ~~~ T1 ~~~ T0
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef edge fill:#fce8ec,stroke:#9b4d67,color:#502638
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef replicas fill:#f8fafc,stroke:#64748b,color:#1f2937,stroke-dasharray:5 4
  class T2,T1,Workloads,Deploy services
  class Cache edge
  class Build services
  class Source,Artifacts data
  class Supply replicas
  class T0,ControlDelivery,Hosting control
```

*Figure: Builds and release delivery consume source and artifact authorities in Tier 1.
Tier 0 retains separate control-service delivery and infrastructure authority; this is a placement map.*

Read the Tier 1 row as cooperating services. Source control retains reviewed definitions;
build jobs read those definitions and publish versioned candidates. A delivery controller
reads approved release intent and changes only its authorized application targets.
The sequence below follows those handoffs rather than the map's placement order.

Tier 0 separately accepts sources; source access does not transfer control authority.
Retained code, artifacts, keys and recovery remain usable without hosted Tier 1 services.

The cache is an intake support function. Its actual request/response paths are in
[software intake](../07-software-intake/README.md); public edge load balancing is not a software
lifecycle component. Infrastructure control marks the separate protected authority for
infrastructure changes, not an installed self-service request API.

## Application delivery

This sequence shows the handoffs between reviewed definitions, build outputs and an
existing runtime. The selected release policy decides what is approved; exact triggers
depend on GitOps reconciliation or pipeline orchestration.

```mermaid
sequenceDiagram
  participant Source as Reviewed source
  participant Build as Build job
  participant Registry as Artifact registry
  participant Delivery as Scoped delivery controller
  participant Runtime as Application runtime
  Build->>Source: Read selected revision
  Build->>Build: Build and test
  Build->>Registry: Publish candidate with version identity
  Build-->>Source: Report build and test result
  Delivery->>Source: Read approved release intent
  Delivery->>Delivery: Apply target release policy
  Delivery->>Runtime: Apply scoped application change
  Runtime->>Registry: Retrieve the approved image
  Registry-->>Runtime: Identified image content
  Runtime-->>Delivery: Rollout status
```

*Figure: Builds publish candidates; approved release intent drives scoped deployment,
and the runtime retrieves the selected artifact independently of the controller.*

<a id="domain-boundaries"></a>

## Components and interfaces

The handoffs carry different kinds of authority. Intake admits external packages and artifacts;
source review accepts definitions; a build produces a candidate; release policy authorizes a
particular version for a particular target. Registry storage and a successful build do not
collapse those decisions into one approval.

The runtime retrieves the identified artifact from its approved supply path. The controller
uses target credentials to apply the release and observe rollout status. Operators use that
status, service telemetry and recovery evidence to decide whether the release is acceptable.
Application rollback still needs the application's own data compatibility contract.

Application traffic follows [Networking](../05-networking/README.md#service-reachability-and-publication),
not the release pipeline. A new base template does not update existing VMs; workload
maintenance and hardware-facing provisioning remain separate operations.
Infrastructure changes belong to [Hosting](../04-hosting/02-provisioning.md).

## Design choices

First decide how approved releases reach their targets: continuous reconciliation or
pipeline orchestration. [Controller patterns](02-controllers.md) explains the consequence
of that choice; Tier 0 uses Flux and Tier 1 selects Argo CD or Spinnaker.

Then select [artifact supply](01-artifact-supply.md): an existing compatible registry or
an independently operated registry, with distribution acceleration only where justified.
The [software-intake design](../07-software-intake/README.md) owns external acceptance and
retained upstream content; this chapter adds builds and release delivery to that supply path.

Kubernetes build pods and external VM runners are placements of build execution,
not interchangeable network grants. [Development platform](03-development-platform.md)
explains their isolation and the privileged infrastructure-project trust exception.

## Design constraints

Each target retains one authorized release writer, scoped credentials and its own
data/rollback contract. General CI cannot administer Tier 0. Tier 0 retains accepted
code, artifacts, credentials and state independently of hosted source control.
An unavailable portal or repository must not authorize workload destruction.

## Realization

Stage 7 establishes delivery using an existing bootstrap source and approved artifacts.
Stage 9 adds hosted source control and general CI; delivery must therefore work before the
new GitLab service exists. Observability is established between those deployment stages.

**Deploy:** [Stage 7: Delivery](../../03-deployment/stage-7-delivery/README.md), then follow
its onward path through Observability to [Stage 9: Development](../../03-deployment/stage-9-development/README.md).
**Operate:** [Delivery and development](../../05-operations/05-delivery.md).
The [support map](../../08-reference/implementation-support.md) distinguishes supplied installers
from required existing interfaces and project integrations.
