# Architecture overview

## Table of contents

- [Purpose](#purpose)
- [Goals](#goals)
- [Layered model](#layered-model)
- [Tiered model](#tiered-model)
- [Tier and zone view](#tier-and-zone-view)
- [Automation flow](#automation-flow)
- [Network references](#network-references)
- [Boundaries](#boundaries)

## Purpose

This repository is a private-cloud baseline built around enterprise-style trust
boundaries, layered networking, and a strict split between image creation,
resource provisioning, and configuration management.

The design is meant to stay stable as the environment grows. The number of
segments, hosts, and services can change without changing the core model, even
when the platform starts at homelab or small-datacenter scale.

The architecture uses Tier 0, Tier 1, and Tier 2 ownership. Tiers describe
dependency direction and recovery ownership: Tier 0 bootstraps and recovers the
platform, Tier 1 provides shared platform services, and Tier 2 hosts
application or project workloads. Read [Tier model](tier-model.md) before
splitting automation across generated downstream repositories.

For the repository definition of private cloud and the boundary between
Proxmox, Kubernetes, and OpenStack, read
[Private cloud model](private-cloud.md).
For the shared identity, PKI, secrets, and telemetry backbone, read
[Shared services model](shared-services.md).

## Goals

- clear separation of edge, application, and control concerns
- no implicit trust between zones
- controlled remote user and administrator access
- reusable structure for IaC and multi-cloud thinking
- clear placement of identity, secrets, and hardware-backed systems
- lower tiers can recover without higher-tier services

## Layered model

Security layers describe a capability's responsibility and the boundaries
around it. Draw them left to right: **Edge**, **Application**, then
**Control**.

```mermaid
flowchart LR
  Edge["Edge layer<br/>Ingress and controlled egress<br/>external_edge networks"]
  App["Application layer<br/>Services and workloads<br/>access, identity, application"]
  Control["Control layer<br/>Administration and recovery<br/>management, storage, custody"]

  Edge --- App --- Control

  style Edge fill:#dcfce7,stroke:#15803d,color:#1f2937
  style App fill:#dbeafe,stroke:#2563eb,color:#1f2937
  style Control fill:#fed7aa,stroke:#c2410c,color:#1f2937
```

Figure: security layers run from edge-facing functions on the left to
control on the right. Lines show conceptual order, not allowed
traffic or a required request path. Moving right never grants implicit trust.

The **Control layer** includes connected administration and separately isolated
recovery/custody functions. It is a functional boundary, not the `management`
network or a single tier. Compute, storage, and networking support every layer.

This is a pattern model, not a public-cloud feature match. Proxmox is the
current reference platform, but the architecture is broader than a single
platform.

Proxy placement in this architecture:

- an edge load balancer in `external_edge` handles early ingress and
  controlled egress for infrastructure and host-based services
- a separate internal cluster proxy can be added later when Kubernetes becomes
  part of the platform

## Tiered model

Tiers describe ownership, dependency direction, and recovery independence.
Draw **Tier 2 at the top**, **Tier 1 in the middle**, and **Tier 0 at the bottom**.

```mermaid
flowchart TB
  T2["Tier 2: workloads<br/>Applications, projects, labs"]
  T1["Tier 1: shared platform<br/>Connected services and platform operations"]
  T0["Tier 0: recovery and control<br/>Bootstrap, root trust, recovery<br/>Air-gapped custody only"]

  T2 -->|may depend on| T1
  T1 -. uses approved outputs from .-> T0

  classDef tier fill:#f8fafc,stroke:#64748b,color:#1f2937
  class T2,T1,T0 tier
```

Figure: dependency arrows point down toward the provider; capabilities are
provided upward. The dashed link means an offline artifact handoff, not a live
connection into Tier 0. Tier 2 can also consume approved Tier 0 outputs.
Lower tiers must recover without higher-tier services.

Tier numbers do not identify network exposure or replace security layers.
Tier 1 and Tier 2 can each have edge, application, and control functions;
a control endpoint is not automatically Tier 0. Read the
[tier model](tier-model.md#dependency-rule) for the dependency and recovery rules.

## Tier and zone view

Place networks directly in the architecture: tiers are rows and security
layers are columns. A connected firewall zone groups subnets in one tier/layer
cell. Create only the cells your deployment needs; multiple subnets can share
a zone without gaining unrestricted access to each other.

```mermaid
flowchart TB
  subgraph Tier2["Tier 2: workloads"]
    direction LR
    T2E["T2-Edge<br/>Workload ingress<br/>external_edge subnets"]
    T2A["T2-Application<br/>Apps and labs<br/>application subnets"]
    T2C["T2-Control<br/>Workload administration<br/>management subnets"]
    T2E ~~~ T2A ~~~ T2C
  end

  subgraph Tier1["Tier 1: shared platform"]
    direction LR
    T1E["T1-Edge<br/>Shared ingress and egress<br/>external_edge subnets"]
    T1A["T1-Application<br/>Shared services<br/>identity, application subnets"]
    T1C["T1-Control<br/>Platform administration<br/>management, storage subnets"]
    T1E ~~~ T1A ~~~ T1C
  end

  subgraph Tier0["Tier 0: air-gapped custody"]
    direction LR
    T0E["Edge<br/>Not present"]
    T0A["Application<br/>No connected services"]
    T0C["T0-Control: offline only<br/>Custody-local subnets<br/>No connected firewall zone"]
    T0E ~~~ T0A ~~~ T0C
  end

  Tier2 ~~~ Tier1 ~~~ Tier0

  classDef edge fill:#dcfce7,stroke:#15803d,color:#1f2937
  classDef app fill:#dbeafe,stroke:#2563eb,color:#1f2937
  classDef control fill:#fed7aa,stroke:#c2410c,color:#1f2937
  classDef absent fill:#f8fafc,stroke:#94a3b8,stroke-dasharray:4 4,color:#475569
  class T2E,T1E edge
  class T2A,T1A app
  class T2C,T1C,T0C control
  class T0E,T0A absent
  style Tier2 fill:#f8fafc,stroke:#64748b,color:#1f2937
  style Tier1 fill:#f8fafc,stroke:#64748b,color:#1f2937
  style Tier0 fill:#f8fafc,stroke:#64748b,color:#1f2937
```

Figure: one placement view for layers, tiers, firewall zones, and their subnets.
No traffic is implied. Tier 0's local services support custody and recovery;
they are not connected Application-zone services. Its air gap is an isolation
boundary, not a firewall deny rule.

| Term | What it decides |
| --- | --- |
| Layer | Edge, Application, or Control responsibility |
| Tier | ownership and recovery dependencies |
| Firewall zone | policy group such as `T1-Application` |
| Network | a specific VLAN/subnet assigned to that zone |
| Firewall rule | which source may initiate traffic to which destination and listener |

For example, an identity subnet belongs to `T1-Application`; Tier 2 clients
reach named identity endpoints through rules, not by joining its subnet.
Shared ingress in `T1-Edge` can publish a Tier 2 application without requiring
a separate `T2-Edge` network. These are service interfaces, not merged tiers.

Use [Network placement](network.md) to choose networks and zones, then the
[firewall policy matrix](../security/firewall-policy.md) to define traffic.

## Automation flow

Each tool has one primary job:

- Tier 0 owns image creation, update jobs, verification, and release approval;
  shared code implements the repeatable steps
- Packer is optional for custom image builds; approved vendor images can be
  imported directly as unconfigured templates
- Terraform provisions identity foundation hosts first and later shared-service
  hosts
- Ansible applies baseline configuration first and then service-specific
  playbooks, such as a secret platform, on dedicated hosts

```mermaid
flowchart LR
  A["Approved local images<br/>Optional custom image build"] --> B["Tier 0 template publication"]
  B --> C["Terraform"]
  C --> D["Ansible baseline"]
  D --> E["Identity and PKI ready"]
  E --> F["Terraform and Ansible service deployment"]
  F --> G["Secret platform handoff"]

  classDef mgmtNode fill:#fed7aa,stroke:#c2410c,color:#1f2937
  classDef buildNode fill:#dbeafe,stroke:#2563eb,color:#1f2937
  classDef secretNode fill:#bbf7d0,stroke:#15803d,color:#1f2937

  class A,E mgmtNode
  class B,C,D,F buildNode
  class G secretNode
```

Figure: image build, identity foundation bring-up, and later shared-service
deployment stay separate until the first secret-platform handoff.

The diagram shows the Linux service path. The dedicated Tier 0 cluster uses
an immutable OS template and its own machine bootstrap path instead of Ansible
guest configuration. Publication and recovery must work before that cluster
or its automation service exists; see the [Tier 0 shape](tier-model.md#tier-0-shape).

The secret platform is treated as an early shared service that follows the
identity foundation layer, so the platform can reduce first-run secret handling
before broader service deployment.

## Network references

The [network catalog](network.md#network-catalog) maps logical network names
such as `management`, `identity`, and `external_edge` into the same tier/layer
view. [Network inputs](../reference/network-inputs.md) maps that design to
Terraform and host attachments; [UniFi zone setup](../platforms/unifi/zone-firewall.md)
is a concrete firewall example. The repository does not apply gateway policy.

## Boundaries

Current repository scope:

- platform-facing automation
- reusable templates and images
- VM and container provisioning
- baseline guest and host configuration

Outside current scope:

- router, firewall, and switch underlay configuration
- end-to-end network fabric automation

Operating assumptions:

- host-management paths stay separate from workloads
- edge services do not get implicit access to host-management or restricted
  systems
- workload access to secrets and other high-trust services is explicit
- network segmentation must already exist before full platform automation
- the `external_edge` edge load balancer stays separate from any later
  Kubernetes-specific cluster proxy
