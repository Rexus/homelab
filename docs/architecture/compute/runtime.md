# Service runtimes and infrastructure

This design expands the [compute domain](README.md). It shows how completed
service runtimes relate to their hosts, persistence and recovery. The
[reference platform](../reference-platform.md) selects the service products and
placements; the hosting relationships below apply across its local variants.

## Table of contents

- [Completed hosting model](#completed-hosting-model)
- [Runtime realizations](#runtime-realizations)
- [Storage interfaces](#storage-interfaces)
- [Persistence and recovery](#persistence-and-recovery)
- [Failure domains](#failure-domains)
- [Related designs and procedures](#related-designs-and-procedures)
- [References](#references)

## Completed hosting model

Proxmox supplies connected VM execution across the tiers. A service can run in a
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

The rows describe placement and ownership, not network connectivity or a shared
control plane. The [Kubernetes topology](kubernetes.md) selects three independent
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

**Object storage** names the capability; **S3-compatible API** names the interface
used by the supplied clients. Neither term requires Amazon-hosted storage.
Block, file and object interfaces can coexist on the same storage system:

| Interface | Typical use | Existing infrastructure |
| --- | --- | --- |
| Block | Live VM disks and application volumes | Proxmox datastores, including Ceph RBD [1] |
| File | Shared files, archive copies and backup repositories | NAS NFS/SMB shares or CephFS [1] |
| Object | Application objects, artifacts and database backup objects | A qualified NAS object endpoint, Ceph Object Gateway (RGW), or another object-storage service [2] |

**Live database data stays on qualified Proxmox/Ceph-backed block storage.**
NAS file exports hold backup copies or explicitly selected shared files, not the
database's live data/WAL directories. Database volume classes and backup mounts
are separate selections; configuring a NAS backup does not move the database.

Ceph is not limited to backups. Proxmox supports RBD for live guest disks and
CephFS for files; an S3-compatible endpoint additionally requires RGW. An existing
Proxmox Ceph installation does not establish that RGW is deployed. The shared
storage-class profile references commissioned datastores; it does not install
Ceph, RGW or a NAS. [1][2]

A NAS can supply file and object interfaces, depending on its product and software.
For UNAS, the reviewed documentation describes NFS/SMB access and **outbound
backups to** object-storage providers, not an application-facing S3 endpoint.
Confirm the selected model/software's serving interface before relying on it. [3][4]

Prefer an existing qualified object endpoint over another service. Qualification
covers the consumer's actual operations, TLS, scoped credentials, versioning and
recovery requirements; API compatibility alone does not prove them. Use direct
NAS file storage where the application supports it. Do not deploy a translation
service merely to make a file share appear to supply another interface. A required
object endpoint remains a commissioned prerequisite, not an implied NAS feature.
Storage capacity, replication and snapshots do not replace independent backup custody.

## Persistence and recovery

Runtime availability, data persistence and recovery are separate responsibilities.
Each service identifies its authoritative data, storage owner and backup path.
No single storage backend is implied for every VM, cluster or service.

Backup jobs read consistent application recovery material and send copies to a
separate file repository or supported object endpoint. Tier 0 owns storage
administration; each consumer receives only its scoped dataset access.
The selected backup method declares its recovery point and restore procedure:
scheduled full copies and continuously archived transactions are not equivalent.
Versioning, replication and a shared NAS do not establish independent backup custody.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  VMData["Service data in VMs"]
  ClusterData["Service data in clusters"]
  VMStorage["Selected VM or external storage"]
  ClusterStorage["Selected volume or external data service"]
  Backups["Service-specific backup copies"]
  Records["State, accepted code and recovery credentials"]
  Recovery["Protected retention outside the recovery target"]
  VMData -->|Persists through| VMStorage
  ClusterData -->|Persists through| ClusterStorage
  VMStorage -->|Defined service backup path| Backups
  ClusterStorage -->|Defined service backup path| Backups
  Backups -->|Independent retention| Recovery
  Records -->|Independent retention| Recovery
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class VMData,ClusterData services
  class VMStorage,ClusterStorage,Backups data
  class Records,Recovery custody
```

These are logical data responsibilities, not a prescribed backup product or a
claim that volume snapshots supply every service's restore requirements.
Application consistency, retention, restore credentials and recovery validation
belong to the service-specific design. Data replication alone does not establish
an independent recovery path.

Keycloak and NetBox consume the reference database service. Vault has its own
storage and recovery design; it does not use that database by implication.
Cluster state, Terraform state and application data are distinct recovery inputs.
The [operations design](../operations/README.md) connects their retention and
recovery responsibilities across the platform.

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

- Parent: [compute and cluster platform](README.md).
- Whole system: [reference platform](../reference-platform.md), [runtime flows](../runtime-flows.md) and [variant model](../variants.md).
- Interfaces: [networking](../networking/README.md), [infrastructure control](provisioning.md) and [tier ownership](../tier-ownership.md).
- Realization: [host/image foundation](../../deployment/foundation/README.md#step-1-prepare-compute-and-templates) and [Kubernetes capability](../../deployment/stage-4-kubernetes/README.md).
- Native storage selection and qualification: [storage prerequisites](../../deployment/foundation/storage/README.md).
- Acceptance and implementation coverage: [deployment readiness](../../deployment/readiness.md).

## References

Storage interfaces checked 2026-10-27; qualify the selected product/software before adoption.

1. [Proxmox Ceph integration: RBD and CephFS](https://github.com/proxmox/pve-docs/blob/master/pveceph.adoc).
2. [Ceph Object Gateway and its S3-compatible interface](https://docs.ceph.com/en/squid/radosgw/).
3. [UNAS file-access interfaces](https://help.ui.com/hc/en-us/articles/39670142044567-Accessing-UniFi-NAS-UNAS-Drives).
4. [UNAS backup destinations](https://help.ui.com/hc/en-us/articles/30961935781655-Troubleshooting-UNAS-Backup-Issues).
