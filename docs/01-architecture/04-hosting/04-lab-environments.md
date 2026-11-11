# Workload lab isolation

**Deploy:** [Lab environments](../../03-deployment/stage-10-lab-environments/README.md).
**Operate:** [Lab environments operations](../../05-operations/01-hosting/kubernetes-and-labs.md).

Provide a project-owned Kubernetes API and disposable capacity without exposing
hypervisors, host OS, control-cluster credentials or other tenants.
This differs from ephemeral CI build pods and ordinary application delivery.

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

The dedicated VM-backed option gives a tenant access to its allocated API while
the platform retains lifecycle authority. The diagram shows authority boundaries,
not network rules or physical isolation.

```mermaid
%%{init: {"theme":"base","themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart LR
  Tenant["Tenant"]
  Operator["Platform operator"]
  subgraph T2["Tier 2 / allocated cluster"]
    direction TB
    API["Project Kubernetes API"]
    Workloads["Project workloads"]
    API -->|Manages| Workloads
  end
  Execution["Tier 0<br/>Protected lifecycle execution"]
  Tenant -->|Owner-scoped access| API
  Operator -->|Authorized operations| Execution
  Execution -->|Provisions and maintains| T2
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  class Tenant,Operator actor
  class T2 boundary
  class API,Workloads services
  class Execution control
```

*Figure: A tenant manages workloads through its allocated API while Tier 0 execution controls the cluster
lifecycle.*

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

## References

1. [Kubernetes multi-tenancy and isolation](https://kubernetes.io/docs/concepts/security/multi-tenancy/).
