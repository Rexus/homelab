# Workload lab isolation

Provide a project-owned Kubernetes API and disposable capacity without exposing
hypervisors, host OS, control-cluster credentials or other tenants.
This differs from ephemeral CI build pods and ordinary application delivery.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":12,"rankSpacing":12,"padding":8,"wrappingWidth":300,"subGraphTitleMargin":{"top":2,"bottom":8}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart BT
  subgraph T2["Tier 2 / allocated cluster"]
    direction LR
    Tenant["Tenant"]
    subgraph PVE["Proxmox hosting capacity"]
      subgraph Nodes["Dedicated node VMs"]
        subgraph Cluster["Project Kubernetes"]
          direction TB
          API{{"Project<br/>Kubernetes API"}}
          Workloads["Project<br/>workloads"]
          API -- "Manages" --> Workloads
        end
      end
    end
    Tenant -- "Project API<br/>access" --> PVE
  end
  subgraph T0["Tier 0 / lifecycle authority"]
    direction LR
    Operator["Platform<br/>operator"]
    Execution["Protected lifecycle<br/>execution"]
    Operator -- "Authorized<br/>operations" --> Execution
  end
  T0 -- "Execution: node-VM lifecycle" --> T2
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  class Tenant,Operator actor
  class PVE boundary
  class Workloads services
  classDef traffic fill:#e1f3f5,stroke:#4c7f88,color:#214a52
  class API traffic
  classDef kubernetes fill:#e8eef6,stroke:#6b83a3,color:#263d59
  class Cluster kubernetes
  class Execution control
  class Nodes runtime
  classDef tier0 fill:#d8cbb9,stroke:#83715a,color:#352a1e
  class T0 tier0
  classDef tier2 fill:#f6f3ef,stroke:#aca59b,color:#4b443c
  class T2 tier2
```

*Figure: Tenant access ends at the allocated Kubernetes API. Tier 0 execution provisions and maintains
the node VMs while the tenant manages workloads inside them. Boundary arrows identify these scoped
API and lifecycle interfaces; they grant no tenant access to Proxmox.*

The figure separates using a cluster from creating or replacing it. The lifecycle
arrow names privileged operations; it does not grant tenants a return administrative path.
VM hosting does not establish a dedicated physical failure domain.

## Contents

- [Choices](#choices)
- [Authority](#authority)
- [Lifecycle and scale](#lifecycle-and-scale)
- [Realization](#realization)
- [References](#references)

## Choices

| Pattern | Appropriate scope | Constraint |
| --- | --- | --- |
| Dedicated VM-backed cluster | Reference for unsafe workloads and OS/add-on experiments | Separate control/data planes; more capacity and slower creation |
| Virtual control plane | Optional faster Kubernetes-API experiments | Shared data-plane/kernel isolation still needs qualification |
| Shared namespace | Trusted application teams | Not a separate cluster; namespace policy does not isolate cluster-scoped administration |
| Dedicated physical pool | Workloads beyond the accepted VM boundary | Separate hardware/fabric and stronger operating controls |

Kubernetes distinguishes control-plane and data-plane isolation. Virtual control
planes alone do not isolate worker kernels; namespace policy does not cover every
cluster-scoped resource. [1] The reference favors dedicated VM-backed clusters for
unsafe experiments, without claiming they are sufficient for every hostile workload.

## Authority

The platform operates lifecycle; tenants receive only their allocated Kubernetes
API and owner-scoped authorization. Hidden control-plane hosting means withholding
Talos/SSH/hypervisor credentials, not removing the tenant API.
Tenant cluster-admin is an explicit experiment option inside that cluster, never
access to the infrastructure executor or other clusters.

Tier 2 owns per-cluster definitions, inventory, allocation records and state.
Tier 0 holds provisioning authority. A dispatcher verifies identity/ownership,
accepts bounded profiles/operations and returns sanitized status/access.
A request is data, not permission to execute user CI definitions or arbitrary IaC.

## Lifecycle and scale

Profiles separate control-plane count, worker count and worker resources.
Multiple clusters need distinct VMIDs/MACs, addresses/endpoints, enforced networks,
state and credentials; an environment suffix is not an allocator.
Latency includes cloning, bootstrap, networking, identity and health. No seconds-level
target is assumed. Warm capacity or virtual clusters are separately qualified options.
Expiry is an explicit authorized event with data-retention checks. Missing requests
or an unavailable portal never authorize destruction.

## Realization

[Stage 10](../../03-deployment/stage-10-lab-environments/README.md) owns the operator path and
future request contract. The current Tier 2 root creates one configured cluster,
not a multi-tenant allocator, automatic DNS service or portal backend.
[Cluster and lab operations](../../05-operations/01-hosting/kubernetes-and-labs.md)
covers the corresponding maintenance tasks.

## References

1. [Kubernetes multi-tenancy and isolation](https://kubernetes.io/docs/concepts/security/multi-tenancy/).
