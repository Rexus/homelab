# Delivery

Delivery applies approved releases to their authorized runtimes. It forms part of the
[software lifecycle](../05-software-lifecycle.md), alongside intake, source and builds.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  Source["Reviewed source / desired state"]
  Registry["Approved artifact registry"]
  Controller["Selected application delivery controller"]
  Runtime["Authorized application runtime"]
  Controller -->|Retrieve approved revisions| Source
  Controller -->|Scoped application changes| Runtime
  Runtime -->|Pull approved artifacts| Registry
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  class Source,Registry data
  class Controller,Runtime services
```

*Figure: The delivery controller retrieves reviewed definitions and changes authorized applications, whose
runtimes pull approved artifacts from the registry.*

**Architecture:** delivery access is scoped to application resources; controller
choices and Tier 0 authority are detailed in [delivery controllers](02-controllers.md).

| View | Guide |
| --- | --- |
| Reconciliation, release orchestration and authority | [Delivery controllers](02-controllers.md) |
| Registries and artifact distribution | [Artifact supply](01-artifact-supply.md) |
| Build the selected path | [Delivery deployment](../../03-deployment/stage-7-delivery/README.md) |
| Maintain deployed services | [Delivery operations](../../05-operations/delivery/README.md) |
