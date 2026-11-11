# Protected logging

Protected logging preserves security and audit evidence under independent Tier 0
custody. Operational diagnosis and scoped queries belong to [Observability](../21-observability/README.md);
that capability does not control the original evidence.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart LR
  Producers["Approved producers<br/>All tiers"] -->|"Submit records"| Intake["Tier 0 protected intake"]
  Intake -->|"Retain"| Evidence[("Original evidence")]
  Evidence -->|"Approved projections"| Search["Scoped observability copies"]
  Reader["Authorized security reader"] -->|"Investigate"| Evidence
  Evidence -->|"Independent recovery copy"| Copy[("Separate custody")]
  AppReader["Application reader"] -->|"Approved scope"| Search
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  class Producers,Reader,AppReader actor
  class Intake control
  class Evidence,Copy data
  class Search services
```
*Figure: Approved producers send records to Tier 0 custody; security readers access originals, while
application readers use scoped copies and a separate recovery copy is retained.*

| View | Guide |
| --- | --- |
| Evidence custody, intake and read boundaries | [Security logging design](../24-operations/01-security-logging.md) |
| Retention and deletion authority | [Log archive choices](../24-operations/02-log-retention.md) |
| Recovery and independent copies | [Backup and recovery](../24-operations/04-backup-recovery.md) |
| Deploy the selected path | [Protected logging deployment](../../03-deployment/stage-2-logging/README.md) |
| Operate and investigate | [Protected logging operations](../../05-operations/protected-logging/README.md) |
