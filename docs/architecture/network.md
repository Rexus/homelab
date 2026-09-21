# Network placement

## Table of contents

- [Purpose](#purpose)
- [Zone assignment](#zone-assignment)
- [Network catalog](#network-catalog)
- [VLAN ID strategy](#vlan-id-strategy)
- [Example network plan](#example-network-plan)
- [Deployment order](#deployment-order)
- [Automation mapping](#automation-mapping)
- [Continue reading](#continue-reading)

## Purpose

Protect services from outside inward: **Edge -> Application -> Control**.
The [architecture view](overview.md#layered-model) shows these layers with
their network zones. Tiers separately decide repository ownership and impact.

Start with a network's purpose and required traffic, then choose its subnet,
VLAN, zone, and enforcement point. Do not create a network for every tier/layer
combination. Routing, switching, and firewall policy are operator-managed
prerequisites, not resources created by this kit.

Tier 0 owns that network control plane across all zones. Other tiers select
approved guest attachments; they do not own the switches, gateways, or policy
because their VMs use a network. See [Infrastructure control](infrastructure-control.md).

## Zone assignment

Use three plain zone names as the starting example. Add a zone only when it
needs a different policy.

| Layer | Example zone | What belongs here |
| --- | --- | --- |
| Edge | `DMZ` | public entry points, reverse proxies, controlled outbound proxies |
| Application | `Services` | shared services, internal applications, workload backends |
| Control | `Control` | administration, identity authority, privileged secrets and signing endpoints |
| Separate offline custody | no connected zone | offline root keys, recovery material, ceremonies |

Tier numbers do not appear in zone names. For example, a Tier 1 platform
service and a Tier 2 application can both use `Services`, while a Tier 0
identity authority uses `Control`.

One subnet belongs to one firewall zone. Group subnets only when their baseline
policy is alike; use names such as `Lab` or `Storage` when a separate policy
is useful. Separate hostile labs, tenants, or administrative scopes rather
than putting them into a shared broadcast domain.

A common zone is not an allow-all group. Filter between its routed subnets and
use host, switch, or workload controls for same-subnet isolation. See
[firewall policy](../security/firewall-policy.md).

WAN, user devices, VPN clients, and the gateway itself are boundary peers, not
additional server layers. VPN membership alone does not grant Control access.

## Network catalog

Terraform's `network_zones` keys are **logical guest-network names**, not
firewall-zone names. `management` is one network purpose inside Control,
not another name for the whole layer.

| Network key | Usual zone / placement | Purpose |
| --- | --- | --- |
| `external_edge` | DMZ | ingress and controlled egress |
| `application` | Services | internal services and project workloads |
| `access` | Services, or Control for privileged access | identity-broker and access-service interfaces |
| `identity` | Control | identity authority, directory, authoritative DNS |
| `cryptography` | Control | issuing CA, signing services, HSM gateways |
| `management` | Control | bastions, privileged runners, hypervisor/admin interfaces |
| `observability`, `telemetry_gateway` | Services | telemetry intake, backends, dashboards |
| `security_telemetry` | restricted service subnet | hardened audit/log intake; scope its receiver permissions |
| `storage` | Control, or separate Storage policy | backup/archive receivers; separate administration |
| `corosync`, `ceph_public`, `ceph_cluster` | non-routed host fabric | quorum and storage transport; not Internet-facing |
| `ceremony` | separate offline custody | root trust and recovery operations |
| `client` | endpoint boundary | user/operator devices, not a server layer |

Choose placement per interface. An identity service's public front end belongs
at the edge; its authority and administration stay protected. Do not expose
admin listeners just because clients need DNS or authentication.

Hosts with multiple interfaces must not bridge zones or make the management
NIC a transit path. Host-only fabrics need local enforcement; routing them
through a gateway is not required merely to assign a policy name.

## VLAN ID strategy

Use numbers as allocations, not as security labels. Keep one site plan, avoid
duplicate IDs on shared trunks, and leave room for growth. The existing examples
use these ranges; choose different ranges when they better fit your site.

| VLAN range | Reference use |
| --- | --- |
| `2-99` | platform, administration, identity, clustering, and storage transport |
| `100-199` | internal services, applications, observability, and archive |
| `200-299` | specialist cryptographic and telemetry networks |
| `300-399` | edge-facing networks |
| `400+` | projects, labs, and local extensions |

A VLAN in the `200` range does not mean Tier 2. A number also does not select
a firewall zone; the configured network-to-zone mapping does.

Record your chosen ranges and a few purpose-to-zone examples in the generated
architecture repo's `docs/naming-conventions.md`. Keep the complete subnet,
gateway, DHCP, and address assignments in network inventory.

## Example network plan

These are examples, not an automatically allocated plan. Existing addresses
are retained so adopting the simpler naming model does not imply renumbering.

| Network name | Logical key | VLAN | IPv4 subnet | Zone |
| --- | --- | --- | --- | --- |
| `edge` | `external_edge` | `320` | `10.30.30.0/24` | DMZ |
| `apps` | `application` | `120` | `10.20.20.0/24` | Services |
| `lab` | `application` in the lab repo | `420` | `10.42.20.0/24` | Services, or separate Lab policy |
| `access` | `access` | `11` | `10.10.11.0/24` | Services for application-only access |
| `identity` | `identity` | `12` | `10.10.12.0/24` | Control |
| `management` | `management` | `10` | `10.10.10.0/24` | Control |
| `crypto` | `cryptography` | `220` | `10.20.21.0/24` | Control |
| `archive` | `storage` | `140` | `10.20.40.0/24` | Control, with dedicated receiver rules |

Additional examples are observability `130`, telemetry intake `230`,
security telemetry `231`, and host-only fabrics `20`, `21`, `22`.
They are not mandatory networks.

Offline `ceremony` may use VLAN `221` and `10.20.22.0/24` on its own
isolated fabric. It has no zone or route on the connected gateway. A VLAN,
missing route, or deny rule on a connected fabric is not an air gap. No
dual-homed host or operator connection may bridge the custody boundary.

## Deployment order

1. Record naming and VLAN choices in the short conventions worksheet.
2. Create the required networks by purpose; reuse suitable existing services.
3. Preserve a tested local recovery and administrative access path.
4. Map connected networks to zones and apply [scoped rules](../security/firewall-policy.md).
5. Test allowed and denied traffic before adding workloads.
6. Establish offline custody separately where required.

An application does not need its own DMZ when a shared proxy can publish it.
Add networks as actual trust or traffic requirements appear, not once per repo.

## Automation mapping

Each tier owns its guest attachment inputs. Identical logical keys do not
automatically mean the same VLAN; choose actual attachments from the site plan.
A network may serve interfaces owned by several repos if policy permits.
Its definition still needs one recorded operational owner.

The generator copies examples; it does not allocate unique IDs/subnets, create
zones, or install firewall rules. Review values before applying them.
Use [Network inputs](../reference/network-inputs.md) for exact fields and
[Proxmox networking](../platforms/proxmox/network-prerequisites.md) for the fabric.

## Continue reading

- [Ownership and network placement](overview.md#tier-and-zone-view)
- [Firewall policy and validation](../security/firewall-policy.md)
- [UniFi zone setup](../platforms/unifi/zone-firewall.md)
- [Project conventions worksheet](../reference/project-documentation.md#start-with-project-values)
