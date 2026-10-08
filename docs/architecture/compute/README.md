# Compute and cluster platform

Compute supplies execution, storage attachment and recovery beneath every service.
Proxmox is the chosen hypervisor. Tier 0 owns hardware control and image publication;
resource definitions, inventory and state remain in the consuming tier.

## Table of contents

- [Components and interfaces](#components-and-interfaces)
- [Design choices](#design-choices)
- [Design constraints](#design-constraints)
- [Realization](#realization)

## Components and interfaces

| Component | Function and boundary |
| --- | --- |
| Hypervisor and host fabrics | Run guests; separate management, quorum and storage transport from guest traffic |
| Image publication | Supply approved, recoverable templates; consumer references do not own the build lifecycle |
| Cluster runtime | Supply a Kubernetes API, scheduling, networking and storage for platform services |
| Infrastructure execution | Accept authorized changes without granting workload users hardware administration |
| State and recovery | Retain resource ownership and bootstrap independently of hosted tooling |

The [provisioning design](provisioning.md) defines the privileged execution boundary.
A VM template is an input to provisioning, not a configured cluster or application.

## Design choices

Choices are independent; they do not form a mandatory upgrade ladder.

| Decision | Option A | Option B | Consequence |
| --- | --- | --- | --- |
| Host availability | Single Proxmox host | Cluster with selected HA/storage design | B adds failure-domain, quorum and storage obligations; cluster membership alone is not HA |
| Guest network attachment | VLAN-aware bridge | SDN VNet over the host underlay | Both implement the same purpose-based network and firewall design |
| Linux lifecycle | Configured mutable guest | Image-based Linux/bootc | Image promotion replaces some in-place configuration; builds need an approved artifact source |
| Cluster OS | Talos reference | Another suitable OS or existing cluster | Kubernetes interfaces remain stable; the alternative needs validated bootstrap and lifecycle code |
| Service runtime | Dedicated VMs | Kubernetes workloads | Availability, persistence and recovery must be defined for either placement |

Single-switch/dual-uplink and separate storage-fabric arrangements are physical
variants beneath the same logical model. Exact cabling and host configuration
belong in deployment procedures. Image-based Linux is an independent lifecycle
choice, not a requirement to replace the current cluster OS.

<a id="maturity"></a>

## Design constraints

| Concern | Required property |
| --- | --- |
| Availability | Explicit host, storage and cluster failure domains; node count alone is not HA |
| Placement | Guest mobility must preserve storage, network and resource ownership contracts |
| Images | Approved templates and bootstrap artifacts remain recoverable independently of hosted delivery |
| Recovery | Higher-tier source control must not be required to recover Tier 0 |

## Realization

Implementation procedures: [host/image foundation](../../deployment/stage-1-foundation/README.md#step-1-prepare-compute-and-templates)
and [cluster foundation](../../deployment/stage-3-identity-runtime/README.md#step-2-create-the-kubernetes-cluster).
The current cluster installer uses Talos; each cluster has its own owner and state.
