# Lab environments

Lab environments provide scoped Tier 2 runtimes and applications for experiments,
without transferring infrastructure authority to workload users. Operator deployment
and a future bounded request interface are separate choices.

This view shows the operator-controlled paths to selected lab runtimes. The
Kubernetes and VM/LXC paths can be selected independently or together.

```mermaid
%%{init: {"theme":"base","themeVariables":{"lineColor":"#627581"}}}%%
block-beta
  columns 1
  block:T2
    columns 2
    Inputs["Tier 2 / labs<br/>Definitions, inventory and state"]
    block:Labs
      columns 1
      VM["VM / LXC runtime"]
      Cluster["Kubernetes runtime"]
    end
  end
  block:T0
    columns 1
    Execution["Tier 0<br/>Protected infrastructure execution"]
  end
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  class T2,T0 boundary
  class Execution control
  class VM,Cluster services
  class Inputs data
```

*Figure: Tier 2 owns lab definitions and selected VM/LXC or Kubernetes runtimes; Tier 0 provides protected
execution.*

An operator approves and runs the selected path.

| View | Guide |
| --- | --- |
| Runtime and tenant boundaries | [Workload lab isolation](../10-hosting/05-workload-isolation.md) |
| Authorized infrastructure requests | [Infrastructure control](../10-hosting/03-provisioning.md) |
| Shared and isolated services | [Service boundaries](../04-service-boundaries.md) |
| Deploy selected lab runtimes and applications | [Lab environments deployment](../../03-deployment/stage-10-lab-environments/README.md) |
| Operate and recover lab environments | [Lab operations](../../05-operations/lab-environments/README.md) |
