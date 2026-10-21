# Design variants and selected instances

The [platform overview](README.md) describes stable functions. The
[integrated reference](reference-platform.md) connects them in a reference
placement. Detailed designs can realize a function in different ways while
keeping its role visible in the same overall system.

A variant is a design alternative, not a deployment stage, maturity ranking,
generator flag or claim that an installer exists. The
[support map](../reference/implementation-support.md) records implementation scope.

## Table of contents

- [The parent and child contract](#the-parent-and-child-contract)
- [Where choices belong](#where-choices-belong)
- [A concrete custody example](#a-concrete-custody-example)
- [Compose the selected environment](#compose-the-selected-environment)
- [When the overview changes](#when-the-overview-changes)
- [Connect design and deployment](#connect-design-and-deployment)

## The parent and child contract

Every detailed variant expands a named component or function from its parent.
Consumers remain visible at the edge of the diagram. A finished topology shows
the components, interfaces, persistent state and relevant custody/recovery
boundaries that exist together after its deployment procedure is complete.

| Design concern | Recorded for every alternative |
| --- | --- |
| Parent role | Function supplied to the platform and the parent design link |
| Consumer contract | Protocol/API, identity, endpoint purpose and authorization boundary |
| Internal composition | Resulting components and relationships; labels consistent with the parent |
| Placement and ownership | Owning tier, VM/cluster/external placement, state and data owner |
| Different properties | Availability, capacity, isolation, custody and recovery implications |
| Preconditions | Supported integration, required independent services and lifecycle responsibilities |
| Realization | Relevant deployment branch/procedure and required acceptance outcomes |

Stable function does not mean identical guarantees. For example, a single-device
issuer and a replicated signing service both provide issuance but tolerate
different failures. An alternative is valid for an instance only when it meets
that instance's recorded requirements. A change to those requirements or outward
boundaries must be reflected in the parent view and decision record.

Small differences can remain in a comparison table. Alternatives with different
runtime, trust or recovery topology receive separate completed diagrams. The
overview does not accumulate every possible optional box.

## Where choices belong

| Stable platform function | Local choices already represented by the design | Design owner |
| --- | --- | --- |
| VM and cluster execution | Single Proxmox host or selected HA arrangement; VM or Kubernetes service placement; validated node OS/lifecycle | [Compute](compute/README.md), [runtime](compute/runtime.md) |
| Purpose-based connectivity | VLAN-aware bridge or SDN VNet; selected host/storage fabrics | [Networking](networking/README.md) |
| Directory and federation | New dedicated directory pair or existing approved authority; explicit client integrations | [Identity](identity/README.md) |
| Certificate key protection | Software, single USB, replicated USB gateways or network HSM | [Custody designs](cryptography/hsm-selection.md) |
| Secret delivery | VM, cluster or existing secret service; separately selected Shamir, Transit or supported native PKCS#11 seal | [Cryptography](cryptography/README.md), [seals](cryptography/vault-seal.md) |
| Approved software supply | Approved egress, cache, mirror or offline content; shared or dedicated supply | [Delivery](delivery/README.md) |
| Artifact authority | Integrated registry, independent registry, or independent registry with distribution acceleration | [Artifacts](delivery/artifact-supply.md) |
| Application delivery | Tier 0 Flux; unselected Tier 1 Argo CD or Spinnaker; scoped Tier 2 delivery | [Controller patterns](delivery/controllers.md) |
| Operational visibility | Independent Tier 0 security logging/critical monitoring; Tier 1 Kubernetes Observability with separate workloads; dedicated VMs or existing service as alternatives | [Telemetry](operations/telemetry.md), [protected evidence](operations/security-logging.md) |
| Evidence retention | NAS snapshots and independent backups with trusted administrators; storage-enforced retention locks; combined local/locked copies | [Archive and custody choices](operations/log-retention.md) |
| Resource changes | Reviewed protected operator execution or a separately implemented bounded request service | [Infrastructure control](compute/provisioning.md) |

Selection is per component and decision, not one global option letter. Root-key
custody, online signing-key custody and Vault seal protection are independent.
Existing external services replace an implementation only through an explicit
consumer, ownership and recovery contract.

## A concrete custody example

At platform scale, the relationship stays **offline trust authority, online
issuing service, certificate consumers**. The issuer's selected provider is
expanded only inside the cryptography design.

| Completed issuer detail | Same outward role | Material difference |
| --- | --- | --- |
| Software provider on the authorized service host | Routine issuance through the approved issuer interface | Key protection shares the selected software/host boundary |
| One USB device on an authorized host | Routine issuance through the approved issuer interface | Local device custody; host/device loss needs the selected recovery path |
| Replicated USB signing gateways | Routine issuance through the approved issuer interface | Explicit routing, authorized key replication and separate host/device failure domains |
| Network HSM service | Routine issuance through the approved issuer interface | Vendor client/partition, management and recovery dependencies |

The [four completed custody designs](cryptography/hsm-selection.md) show those
arrangements. A switch of provider need not redraw workload or source-control
functions. It does require review of signing integration, consumer compatibility,
availability and recovery. A changed trust root or new external dependency can
also require updates to the integrated platform view.

The same method applies to a secret service on VMs or Kubernetes: secret
consumers retain a named service and authorization contract, while hosting,
persistence, seal availability and recovery dependencies are recorded differently.
It does not imply that every component is freely movable; the reference directory
pair remains outside the control cluster.

## Compose the selected environment

Upstream architecture describes reusable designs. Project-owned architecture
records one coherent composition for a site or environment. Its overview shows
selected services; its domain records identify selected alternatives and link
to component details. Reference alternatives remain available for comparison.

| Instance record | Content |
| --- | --- |
| Platform overview | Intended outcomes, consumers, complete functions and consequential external dependencies |
| Integrated placement and interactions | Selected runtime boundaries and the access/change/trust/data relationships between them |
| Domain selection | Variant name scoped to that decision, rationale, fulfilled requirements and changed guarantees |
| Component design | Completed topology, owning implementation, data, custody and failure/recovery boundaries |
| Deployment record | Procedure/branch used, actual inputs, acceptance and current readiness |
| Operating record | Owners, restore procedures, retained recovery inputs and maintenance evidence |

Exact hosts, addresses, VMIDs and state assignments remain in tier-owned
inventory and implementation inputs. Architecture links to those sources rather
than creating another inventory. A lab, test or production instance can reuse
the same logical pattern with explicit differences in sharing, scale and isolation.
An environment label alone creates no boundary.

Cross-domain consistency matters: a clustered identity provider needs its selected
database and certificate dependencies; a secret service needs independent recovery
and a viable seal dependency; a protected executor needs independent state and
approved code; an external provider needs an accepted outage and recovery contract.

## When the overview changes

| Change | Design updates required |
| --- | --- |
| Capacity or host count within agreed failure/authority boundaries | Component placement and inventory; parent capacity assumptions where relevant |
| Different internal key provider satisfying existing requirements | Custody design, signing integration and recovery; parent only for changed external dependencies |
| VM-to-cluster placement | Integrated placement, affected domain/data/recovery views and explicit migration design |
| New identity authority, CA trust boundary or service owner | Platform relationships, domain contracts and decision rationale |
| Cross-tier privileges or shared failure/recovery dependency | Whole-platform authority and failure views, plus affected detailed designs |
| New external dependency | Platform context, consumer contract and outage/recovery implications |

The logical role may remain stable while the placement view changes. Keeping the
overview understandable does not justify hiding a material change of authority,
trust, data ownership or recovery dependence.

## Connect design and deployment

Each domain's **Realization** section links to the deployment stages that build
its result. Detailed options link to the applicable adjacent procedure. The
[reference mapping](reference-platform.md#design-to-deployment) covers all six
capabilities without turning the architecture into a chronological walkthrough.

For example, identity spans the directory work in the identity/runtime stage
and federation work in the control-services stage. Its architecture shows the
directory, IdP and authorization boundaries together. Cryptography shows the
complete root/issuer/provider arrangement even when a hardware deployment branch
is selected partway through a trust walkthrough.

Project starters follow this contract in
[project documentation](../development/project-documentation.md). New upstream
references can refresh automatically; existing project-owned decisions and
diagrams require deliberate adoption. A documentation refresh does not migrate
services or demonstrate deployment readiness.
