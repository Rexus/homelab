# Network zones and IaC mapping

## Table of contents

- [Purpose](#purpose)
- [Big picture](#big-picture)
- [Zone catalog](#zone-catalog)
- [VLAN ID strategy](#vlan-id-strategy)
- [IaC mapping](#iac-mapping)
- [Stage guidance](#stage-guidance)
- [Proxmox notes](#proxmox-notes)
- [Continue reading](#continue-reading)

## Purpose

Use this document as the shared network reference for the repository.

It gives you one stable set of zone names for:

- architecture and platform planning
- Terraform variable keys
- Proxmox bridge and VLAN mapping
- later service-specific guides such as the USB HSM lab

Not every zone is required on Day 1. The point is to keep one consistent map so
the repository can grow without renaming networks every time a new sub-project
appears.

## Big picture

Use this pattern model:

```mermaid
flowchart TB
  subgraph Edge["Edge-facing layer"]
    Internet[Internet or WAN]
    DMZ[dmz]
    Internet --> DMZ
  end

  subgraph App["Application and shared-service layer"]
    Service[service]
    HSMGateway[hsm_gateway]
  end

  subgraph Infra["Infrastructure and restricted layer"]
    Mgmt[management]
    HSM[hsm]

    subgraph Fabric["Host and storage-close networks"]
      Corosync[corosync]
      CephPublic[ceph_public]
      CephCluster[ceph_cluster]
    end

    Mgmt --> Corosync
    Corosync --> CephPublic
    CephPublic --> CephCluster
  end

  DMZ --> Service
  DMZ --> HSMGateway
  Mgmt --> Service
  Service --> HSMGateway
  Mgmt --> HSM

  style Edge fill:#ecfdf5,stroke:#15803d,stroke-width:2px,color:#1f2937
  style App fill:#eff6ff,stroke:#2563eb,stroke-width:2px,color:#1f2937
  style Infra fill:#fff7ed,stroke:#c2410c,stroke-width:2px,color:#1f2937
  style Fabric fill:#fff1e6,stroke:#9a3412,stroke-width:2px,color:#1f2937

  classDef edgeNode fill:#dcfce7,stroke:#15803d,color:#1f2937
  classDef appNode fill:#dbeafe,stroke:#2563eb,color:#1f2937
  classDef gatewayNode fill:#bfdbfe,stroke:#2563eb,color:#1f2937
  classDef mgmtNode fill:#fed7aa,stroke:#c2410c,color:#1f2937
  classDef proxmoxNode fill:#fdba74,stroke:#9a3412,color:#1f2937
  classDef hsmNode fill:#bbf7d0,stroke:#15803d,color:#1f2937
  classDef cephNode fill:#fee2e2,stroke:#dc2626,color:#1f2937

  class Internet,DMZ edgeNode
  class Service appNode
  class HSMGateway gatewayNode
  class Mgmt mgmtNode
  class Corosync proxmoxNode
  class HSM hsmNode
  class CephPublic,CephCluster cephNode
```

Figure: the zone catalog follows the same top-down trust model as the
architecture overview, from public-facing paths at the top to management,
cluster, storage, and custody networks at the bottom.

The keys above are the same keys you should use in Terraform `network_zones`.

## Zone catalog

Use these zone meanings:

| Zone key | What it is for | Typical users | Guest-facing today |
| --- | --- | --- | --- |
| `management` | host-management access such as Proxmox UI, API, SSH, IaC runners, bastions, and management endpoints | admins, automation, bootstrap helpers | yes |
| `corosync` | cluster membership, quorum, and node coordination | Proxmox cluster nodes | no |
| `ceph_public` | Ceph client-facing storage traffic | hypervisors, storage clients, selected guests | usually no |
| `ceph_cluster` | Ceph replication, recovery, and back-end storage traffic | Ceph nodes only | no |
| `service` | shared services and internal application traffic | Vault, DNS, APIs, apps, internal callers | yes |
| `hsm_gateway` | dedicated service-plane microsegment for live HSM-backed gateways or signers | signer gateways, signing APIs, PKI frontends | yes |
| `hsm` | restricted custody, provisioning, recovery, or helper path | recovery hosts, provisioning hosts, ceremony helpers | sometimes |
| `dmz` | ingress, reverse proxies, externally exposed services | proxies, selected edge services | yes |

Practical notes:

- in the current Proxmox pattern, `management` is the host-management network
  used to reach the hypervisor web UI, API, and SSH
- domain, DNS, and identity services usually live on `service` unless you split
  out a dedicated shared-services segment later
- `hsm_gateway` is the live service microsegment for active HSM-backed
  gateways; keep it separate from custody-only helpers when you have a distinct
  subnet, VLAN, or ACL boundary for that traffic
- `hsm` does not mean the USB device itself is networked; it is the restricted
  path around recovery, provisioning, and custody-adjacent systems
- `corosync`, `ceph_public`, and `ceph_cluster` become active when the platform
  grows into clustering or storage separation

## VLAN ID strategy

Use one VLAN ID plan across the environment and decide it early.

The important part is not the exact numbers. The important part is that related
network types stay grouped so they are easier to sort, review, and extend later.

Use a range model such as this:

| VLAN ID range | Suggested use | Example zones |
| --- | --- | --- |
| `2-99` | critical infrastructure, clustering, and storage | `management`, `corosync`, `ceph_public`, `ceph_cluster` |
| `100-199` | shared internal services | `service`, DNS, PKI, directory services |
| `200-299` | restricted service microsegments | `hsm_gateway`, `hsm`, signing paths |
| `300-399` | edge-facing paths | `dmz`, ingress, reverse proxies |
| `400+` | local extensions and future segments | site-specific app or lab networks |

One example based on that pattern is:

| Zone key | Example VLAN ID |
| --- | --- |
| `management` | `10` |
| `corosync` | `11` |
| `ceph_public` | `20` |
| `ceph_cluster` | `21` |
| `service` | `120` |
| `hsm_gateway` | `220` |
| `hsm` | `221` |
| `dmz` | `320` |

## IaC mapping

Use the same keys in Terraform:

```hcl
network_zones = {
  management = {
    bridge    = "vmbr0"
    vlan_id   = 10
    cidr_ipv4 = "10.10.10.0/24"
  }
  corosync = {
    bridge    = "vmbr0"
    vlan_id   = 11
    cidr_ipv4 = "10.10.11.0/24"
  }
  ceph_public = {
    bridge    = "vmbr1"
    vlan_id   = 20
    cidr_ipv4 = "10.10.20.0/24"
  }
  ceph_cluster = {
    bridge    = "vmbr1"
    vlan_id   = 21
    cidr_ipv4 = "10.10.21.0/24"
  }
  service = {
    bridge    = "vmbr0"
    vlan_id   = 120
    cidr_ipv4 = "10.20.20.0/24"
  }
  hsm_gateway = {
    bridge    = "vmbr0"
    vlan_id   = 220
    cidr_ipv4 = "10.20.21.0/24"
  }
  hsm = {
    bridge    = "vmbr0"
    vlan_id   = 221
    cidr_ipv4 = "10.20.22.0/24"
  }
  dmz = {
    bridge    = "vmbr0"
    vlan_id   = 320
    cidr_ipv4 = "10.30.30.0/24"
  }
}

vm_instances = {
  signer_gw01 = {
    name             = "signer-gw01"
    node_name        = "pve01"
    network_zone_key = "hsm_gateway"
    ipv4_address     = "dhcp"
  }
}
```

Use these field meanings:

| Field | Meaning | Current repository use |
| --- | --- | --- |
| `network_zones.<key>.bridge` | Proxmox bridge name for that zone | consumed by VM and LXC placement |
| `network_zones.<key>.vlan_id` | VLAN tag for that zone when your bridge is VLAN-aware | consumed by VM placement and kept as shared reference |
| `network_zones.<key>.cidr_ipv4` | planning subnet for the zone | documentation and operator reference |
| `network_zones.<key>.gateway_ipv4` | default guest gateway when you assign static addresses | consumed when a guest does not override the gateway |
| `network_zones.<key>.notes` | local planning context or reminders | documentation and operator reference |
| `vm_instances.*.network_zone_key` | which zone a VM belongs to | selects the bridge and optional VLAN |
| `lxc_instances.*.network_zone_key` | which zone an LXC belongs to | selects the bridge |

This is the intended split:

- put durable naming and logical intent in `network_zones`
- put guest placement in `vm_instances` or `lxc_instances`
- keep switch, firewall, and router implementation details outside this repo

## Stage guidance

Use the catalog progressively:

| Stage | Zones you usually need now | Zones you can leave as reference only |
| --- | --- | --- |
| first bootstrap | `management`, `service` | `corosync`, `ceph_public`, `ceph_cluster`, `hsm_gateway`, `hsm`, `dmz` |
| early private cloud | `management`, `service`, `dmz` | `corosync`, `ceph_public`, `ceph_cluster`, `hsm_gateway`, `hsm` |
| clustered platform | `management`, `corosync`, `service`, optional `dmz` | `ceph_public`, `ceph_cluster`, `hsm_gateway`, `hsm` |
| storage-heavy platform | `management`, `corosync`, `ceph_public`, `ceph_cluster`, `service` | `dmz`, `hsm_gateway`, `hsm` |
| HSM or signing lab | `management`, `service`, `hsm_gateway`, optional `hsm`, optional `dmz` | `corosync`, `ceph_public`, `ceph_cluster` unless also clustering storage |

This is why the examples keep extra zones in comments or placeholders. You do
not need to run every network before the repository is useful.

## Proxmox notes

For Proxmox in this repository:

- your switch and firewall design must already make the segmentation real
- Proxmox bridges expose those segments to guests
- a bridge may carry one flat network or multiple VLANs depending on your host
  design
- if you use VLAN-aware bridges, keep the bridge names stable and move the
  segmentation detail into `vlan_id`

Repository boundary:

- this repo maps guests into named zones
- this repo does not configure the physical switch, router, or firewall
- underlay networking still needs its own operational documentation

## Continue reading

- [Architecture overview](overview.md)
- [Proxmox host networking](../platforms/proxmox/network-prerequisites.md)
- [USB HSM active-active blueprint](../security/usb-hsm-active-active-blueprint.md)
