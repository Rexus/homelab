# Kubernetes topology

Each tier has an independent Kubernetes API, etcd quorum, administrative
credentials and lifecycle state. Tiers separate authority; worker pools organize
capacity within that authority. Talos is the supplied node OS, not the design goal.

Prefer Kubernetes for services with a documented native deployment path when
storage, resource isolation, upgrades and recovery can meet their requirements.
A container image alone is not a supported deployment model. Keep bootstrap,
offline custody and outage visibility independent of the clusters they recover.

## Cluster boundaries

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":16,"rankSpacing":16,"padding":10,"wrappingWidth":350,"subGraphTitleMargin":{"top":2,"bottom":10}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  subgraph T2["Tier 2 / workload authority"]
    C2["Workload cluster<br/>Independent API / etcd / credentials<br/>Development, testing and labs"]
  end
  subgraph T1["Tier 1 / shared-platform authority"]
    C1["Platform cluster<br/>Independent API / etcd / credentials<br/>Source, registry and delivery services"]
  end
  subgraph T0["Tier 0 / infrastructure and trust authority"]
    direction TB
    subgraph Connected["Connected runtimes"]
      direction LR
      C0["Control cluster<br/>Independent API / etcd / credentials<br/>IdP, secrets and control services"]
      Directory["Outside Kubernetes<br/>Dedicated directory VM pair<br/>Protected execution host"]
      C0 ~~~ Directory
    end
    Custody["Offline root and recovery custody<br/>Outside connected hosts and clusters"]
    Connected ~~~ Custody
  end
  T2 ~~~ T1 ~~~ T0
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class Directory control
  class Connected boundary
  classDef kubernetes fill:#e8eef6,stroke:#6b83a3,color:#263d59
  class C0,C1,C2 kubernetes
  class Custody custody
  classDef tier0 fill:#d8cbb9,stroke:#83715a,color:#352a1e
  class T0 tier0
  classDef tier1 fill:#e9e2d8,stroke:#968976,color:#44382a
  class T1 tier1
  classDef tier2 fill:#f6f3ef,stroke:#aca59b,color:#4b443c
  class T2 tier2
```

*Figure: Each tier retains its own cluster authority. Tier 0 also owns dedicated directory and execution
hosts; its offline custody sits outside every connected runtime.*

Read each cluster as a complete administrative boundary, not a worker pool in one
larger cluster. The node VMs sit inside Proxmox as shown in the
[hosting view](01-runtime.md#completed-hosting-model); this figure expands cluster
authority rather than physical host allocation.

Network attachments follow purpose and exposure, not tier numbers. The examples
use Control for Tier 0, application/Services for Tier 1, and lab for Tier 2;
the [network map](../05-networking/README.md) owns VLAN and firewall design.
Sharing Proxmox hosts does not create physical isolation between tiers.

FreeIPA remains on two dedicated Tier 0 VMs and supplies directory federation
to the IdP, as shown in the [identity view](../09-identity/README.md). Offline root keys remain outside
the clusters. The protected infrastructure runner is a Tier 0 execution host,
not a general build pod or a Tier 1 delivery controller.

## Table of contents

- [Cluster boundaries](#cluster-boundaries)
- [Scheduling and capacity](#scheduling-and-capacity)
- [Availability and recovery](#availability-and-recovery)
- [Implementation](#implementation)
- [References](#references)

## Scheduling and capacity

The [scaling view](01-runtime.md#scaling-and-host-capacity) separates larger node VMs, additional workers,
application replicas and physical-host headroom. Choose the layer before changing its inputs.

| Cluster | Compact reference | Optional worker pools |
| --- | --- | --- |
| Tier 0 | Three schedulable control planes; no initial workers | Additional trusted control-service capacity |
| Tier 1 | Three control planes; scheduling enabled for the compact start | Separately budgeted infrastructure, metrics, search and compute capacity |
| Tier 2 | Three control planes; scheduling enabled for the compact start | Development, testing and lab |

Tier 1/2 can instead use dedicated workers with control-plane scheduling disabled.
This is an explicit capacity choice, not an automatic transition. Tier 0 remains
compact unless its trusted services justify additional workers.

[Observability](../11-operations/03-observability.md) uses native Kubernetes workloads with
independent gateway, metrics, search and UI scaling. Qualify backend capacity before
deployment; three small schedulable control planes are not a search-storage budget.
Use dedicated worker pools when storage or resource contention requires separation.

Pools use labels and workload selectors/affinity. Taints with matching tolerations
reserve nodes; a toleration alone does not force a workload onto that pool. [1]
Pools share the API, cluster-wide resources and administrative boundary. Namespaces,
RBAC, quotas and network policy add workload controls, not independent clusters. [2]

General CI must not run untrusted code alongside sensitive infrastructure on the
same hosts. Use isolated execution capacity and ephemeral environments; Tier 2
is a suitable scope for untrusted project builds. Disruptive CNI, CRD, privileged
or cluster-upgrade experiments require a separately owned disposable cluster,
not merely another namespace in the long-lived workload cluster.

## Availability and recovery

Three control planes are an initial quorum topology, not an application HA guarantee.
Separate physical placement, resilient API access, adequate capacity after failure,
storage availability, application replicas and restore tests remain obligations.
Proxmox HA membership must preserve the selected physical failure domains after moves.

Tier 0 bootstrap and recovery cannot depend on Tier 1 delivery or normal identity
login. Every cluster retains its own state, node secrets, administrator credentials,
etcd recovery material and workload backups outside that cluster.

## Implementation

Each tier owns `terraform/deployments/kubernetes/`, its Ansible inventory host keys
and IP reservations, and `clusters/tierN/` manifests. Shared owns the stateless
command and approved image/sizing references, never cluster resources or inventory.

The supplied roots support explicit node definitions and a `node-pool` label.
They do not install an autoscaler, self-service controller, add-ons or applications.
Delivery selection is independent: [controller patterns](../10-delivery/02-controllers.md).
Installation: [common Kubernetes procedure](../../03-deployment/stage-4-kubernetes/procedures/kubernetes.md).
The [Kubernetes deployment path](../../03-deployment/stage-4-kubernetes/README.md) joins node creation,
platform services and acceptance; [operations](../../05-operations/01-hosting/kubernetes-and-labs.md)
covers ongoing cluster and lab work.

## References

1. [Kubernetes taints and tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/).
2. [Kubernetes multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/).
