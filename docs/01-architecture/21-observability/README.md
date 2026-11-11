# Observability

Observability supports operational diagnosis through logs, metrics, traces and scoped
queries. It can consume approved evidence copies; [Protected logging](../14-protected-logging/README.md)
retains authority over Tier 0 originals. Independent control monitoring is established
with [Secrets](../19-secrets/README.md).

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  Sources["Platform / application sources"]
  Collection["Telemetry collection"]
  Query["Metrics / log / trace queries"]
  Evidence[("Tier 0 protected evidence<br/>Originals")]
  Monitoring["Tier 0 independent<br/>health / alerts"]
  Sources -->|Operational signals| Collection
  Collection -->|Logs / metrics / traces| Query
  Sources -->|Security / audit submissions| Evidence
  Evidence -->|Optional approved copies| Query
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  class Collection,Query services
  class Monitoring control
  class Evidence data
```

*Figure: Operational signals feed shared queries, while Tier 0 retains original security evidence and
independent health monitoring; only approved copies may reach shared queries.*

See [telemetry design](../24-operations/03-telemetry.md) for signal paths and boundaries.

| View | Guide |
| --- | --- |
| Signals, collection, queries and infrastructure coverage | [Telemetry design](../24-operations/03-telemetry.md) |
| Independent visibility and recovery | [Operations and resilience](../24-operations/README.md) |
| Protected evidence boundaries | [Security logging design](../24-operations/01-security-logging.md) |
| Deploy the selected visibility path | [Observability deployment](../../03-deployment/stage-8-observability/README.md) |
| Maintain deployed services | [Observability operations](../../05-operations/observability/README.md) |
