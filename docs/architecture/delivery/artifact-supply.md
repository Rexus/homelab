# Artifact supply design

Source control owns definitions and proposed changes. The registry owns promoted
artifacts. A distribution layer accelerates pulls but is not the authority for
which artifact is approved.

## Components and variants

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart LR
  Source["Source control / build runners"] --> Registry["Approved registry authority"]
  Registry --> Direct["Direct consumers"]
  Registry --> Distribution["Optional distribution acceleration"]
  Distribution --> Fleet["Cluster / host fleet"]
  Registry --> Images["OS images and template inputs"]
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  class Registry,Distribution services
  class Images data
  class Source,Direct,Fleet actor
```

| Option | Design | Reference example | Trade-off |
| --- | --- | --- | --- |
| A | Registry integrated with source control | GitLab registry [1] | Simple project-local ownership; coupled service lifecycle |
| B | Independent platform registry | Harbor [2] | Separate artifact policy and recovery; another stateful service |
| C | B plus distribution acceleration | Harbor plus Dragonfly [3] | Additional capacity/distribution function and operating responsibility |

An existing registry is valid for any compatible consumer. The reference products
are examples, not required stages. C does not replace B's artifact authority.
Kubernetes and image-based Linux can consume all suitable variants.

<a id="maturity-and-dependencies"></a>

## Availability and dependencies

Every variant needs scoped push/pull, approved promotion, retention and recovery.
Independent bootstrap needs approved artifact availability, not a specific hosted
registry. Distribution acceleration is justified by measured pull demand.

Harbor's cluster HA pattern depends on external ingress, database/cache and artifact
storage readiness; increasing application replicas alone is insufficient. [2]
Recovery copies for Tier 0 remain independent of the delivery platform.

[Registry integration](../../deployment/stage-5-delivery/procedures/registry.md)
owns implementation and acceptance.

## References

Sources checked 2026-10-08.

1. [GitLab container registry](https://docs.gitlab.com/user/packages/container_registry/)
2. [Harbor HA deployment](https://goharbor.io/docs/main/install-config/harbor-ha-helm/)
3. [Dragonfly project documentation](https://d7y.io/docs/)
