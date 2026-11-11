# Service runtimes and infrastructure

This view expands the selected realization of [Hosting and orchestration](README.md).
It shows service placement and runtime control boundaries, while [Data and storage](../06-data/README.md)
owns persistence interfaces and [Operations](../11-operations/04-backup-recovery.md) owns recovery policy.
The [reference platform](../03-reference-platform.md) selects the service products and placements.

## Table of contents

- [Completed hosting model](#completed-hosting-model)
- [Runtime realizations](#runtime-realizations)
- [Storage interfaces](#storage-interfaces)
- [Persistence and recovery](#persistence-and-recovery)
- [Failure domains](#failure-domains)
- [Related designs and procedures](#related-designs-and-procedures)
- [References](#references)

## Completed hosting model

**Reference realization:** Proxmox supplies connected VM execution across the tiers. A service can run in a
dedicated VM or in a Kubernetes cluster whose nodes are VMs. The hosting layer
does not change the service's authority classification or transfer its resource
definitions and state to another tier.

```mermaid
block-beta
  columns 3
  Owner["Owning tier"] Runtime["Hosted service runtimes"]:2
  T2["Tier 2<br/>Workloads"] Workloads["Workload VMs and cluster-node VMs"]:2
  T1["Tier 1<br/>Shared platform"] Shared["Shared-service VMs and cluster-node VMs"]:2
  T0["Tier 0<br/>Trust / infrastructure"]
  Cluster["Control-cluster<br/>node VMs"] Dedicated["Dedicated service<br/>and execution VMs"]
  Hosts["Hosting foundation for every row: Proxmox hosts and approved resources"]:3
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  class Owner,Runtime,T2,T1,T0 boundary
  class Workloads,Shared services
  class Dedicated,Cluster,Hosts control
```

*Figure: Proxmox hosts provide VM execution across tiers; each tier retains ownership of its service and
cluster-node VMs.*

The rows describe placement and ownership, not network connectivity or a shared
control plane. The [Kubernetes topology](03-kubernetes.md) selects three independent
tier clusters, each with its own API, inventory, state and credentials. Dedicated
VMs remain available alongside them. Host placement and failure-domain separation
remain explicit project decisions.

In the reference allocation, the directory pair and protected execution VM are
dedicated Tier 0 guests, while selected control services use the Tier 0 cluster.
Tier 1 cluster management is scoped to Tier 2 workload clusters and has no
authority over Tier 0. Offline root keys and their ceremony environment remain
outside this connected hosting model.

## Runtime realizations

Both realizations expose the service's agreed client interface. Their deployment,
storage and recovery mechanisms differ and require a recorded service design.

| Concern | Dedicated VM realization | Kubernetes realization |
| --- | --- | --- |
| Execution | Service processes in an owned guest OS | Workloads on the selected cluster's node VMs |
| Client interface | Published service endpoint with service authentication and authorization | Published service endpoint with service authentication and authorization |
| Administration | Guest and service access, separate from hypervisor authority | Cluster and workload access, separate from hypervisor authority |
| Persistent data | Explicit guest disks, external services or storage attachments | Explicit persistent volumes or external data services; node replacement must preserve required data |
| Lifecycle | Approved images plus the selected configuration/update model | Cluster lifecycle plus service reconciliation and data lifecycle |
| Recovery inputs | Guest definitions, configuration, service data and scoped credentials | Cluster definitions and state, service manifests, service data and scoped credentials |

The directory pair's dedicated-VM placement is part of the reference design.
A runtime alternative for another service does not imply migration of that pair
or of any existing service. Moving a service requires an explicit data and
lifecycle design, even when its client interface remains unchanged.

## Storage interfaces

[Data and storage](../06-data/README.md#storage-interfaces) defines block, file and object
contracts. Its [reference realization](../06-data/README.md#reference-realization) distinguishes
live block volumes, NAS backup files and native object endpoints.

## Persistence and recovery

The [persistence contract](../06-data/README.md#persistence-and-recovery) owns dataset
responsibilities and the transferred data view. [Operations](../11-operations/04-backup-recovery.md)
owns independent copies, retention and recovery objectives; hosting consumes those contracts.

## Failure domains

An availability claim includes the resources and dependencies that can fail
together. Tier separation, multiple VM names and a cluster label do not establish
independent failure domains by themselves.

| Domain | Required design property |
| --- | --- |
| Physical hosts | Placement identifies which guests fail together and which surviving capacity can run the required services |
| Cluster control | The selected node and quorum design identifies the failures it can tolerate and its independent recovery inputs |
| Service replicas | Replicas have a deliberate placement and data design rather than an assumed benefit from their count |
| Storage | Data placement, access paths and restore material support the declared host and service failure scenarios |
| Networking | Uplinks, switches, routing and host fabrics have recorded shared dependencies and reachable recovery paths |
| Hosted management | Loss of source control, registry, identity or inventory tooling leaves the required lower-tier recovery inputs available |

Tier 0 recovery does not require Tier 1 or Tier 2 services; Tier 1 recovery does
not require Tier 2 workloads. Normal consumption of higher-tier source or
artifact services is compatible with this rule only when protected recovery
copies and local administrative execution remain available.

## Related designs and procedures

- Parent: [Hosting and orchestration](README.md).
- Whole system: [reference platform](../03-reference-platform.md), [interaction index](../README.md#how-the-platform-works-together) and [selection guidance](../02-organization/README.md#selected-design).
- Interfaces: [networking](../05-networking/README.md), [infrastructure control](02-provisioning.md) and [tier ownership](../02-organization/01-tier-ownership.md).
- Realization: [host/image foundation](../../03-deployment/foundation/README.md#step-1-prepare-compute-and-templates) and [Kubernetes capability](../../03-deployment/stage-4-kubernetes/README.md).
- Persistence: [Data and storage](../06-data/README.md), including its selected storage qualification links.
- Acceptance and implementation coverage: [deployment readiness](../../03-deployment/readiness.md).

## References

Storage-interface sources are maintained in [Data and storage](../06-data/README.md#references).
The hosting figure is the repository's selected reference, not a cloud-provider deployment claim.
