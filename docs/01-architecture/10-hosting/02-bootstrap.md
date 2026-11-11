# Bootstrap and recovery execution

Bootstrap provides an independently accessible execution context for the first
infrastructure changes and later recovery. It consumes prepared host capacity,
network access and approved software; it does not depend on the platform's hosted
source control, identity or cluster services to restore those same services.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart LR
  Operator["Authorized operator"] -->|Review and execute| Bootstrap["Protected execution host<br/>tools / inputs / state"]
  Bootstrap -->|Provision / configure| Platform["Host and service interfaces"]
  Supply["Accepted software supply"] -->|Approved tools / artifacts| Bootstrap
  Recovery["Independent recovery custody<br/>backups / required inputs"] -.->|Restore| Bootstrap
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class Operator,Supply actor
  class Bootstrap,Platform control
  class Recovery custody
```

*Figure: An operator uses protected execution and accepted software to configure the platform; independent
custody supports recovery.*

The dashed recovery link is a custody and restoration relationship, not an
always-connected network route. A protected existing host can serve this role; the
reference path uses a manually created VM. Later automation can use a separately
protected runner, while original state and independent recovery inputs remain required.

| Need | Guide |
| --- | --- |
| Prepare the initial host | [Bootstrap deployment](../../03-deployment/foundation/bootstrap/README.md) |
| Review privileged execution boundaries | [Infrastructure control](03-provisioning.md#execution-contexts) |
| Restore hosts and infrastructure | [Recovery operations](../../05-operations/README.md) |
