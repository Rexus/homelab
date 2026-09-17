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

Networks implement the [tier-and-layer architecture](overview.md#tier-and-zone-view).
This document maps subnets into that view; it does not introduce another
network hierarchy. Use the [firewall policy](../security/firewall-policy.md)
for traffic between those networks.

Before deploying, choose the owning tier, security layer, subnet, VLAN or
equivalent segment, gateway, and enforcement point for every interface.
Switching, routing, and gateway policy are operator-managed prerequisites,
not resources created by this repository.

## Zone assignment

Use `T<tier>-<layer>` for connected firewall zones. Create only zones with
actual networks, and group networks only when their baseline policy is alike.

| Architecture cell | Firewall zone | Networks it groups |
| --- | --- | --- |
| Tier 2 / Edge | `T2-Edge` | dedicated workload ingress or egress, when shared edge is insufficient |
| Tier 2 / Application | `T2-Application` | project, application, tenant, and lab subnets |
| Tier 2 / Control | `T2-Control` | workload administration and tier-scoped automation |
| Tier 1 / Edge | `T1-Edge` | shared ingress, outbound proxies, and caches |
| Tier 1 / Application | `T1-Application` | connected identity, access services, apps, telemetry, and cryptography |
| Tier 1 / Control | `T1-Control` | platform administration, recovery storage, and control endpoints |
| Tier 0 / Control | none on the connected gateway | physically isolated custody-local networks |

Internet/WAN, user endpoints, remote-access clients, and the gateway itself
are boundary peers, not extra architecture layers. Keep their policy groups
separate from the server zones. A client VPN is not automatically a trusted
Control-zone source.

Each routed subnet has one owning tier and one firewall zone. Cross-tier
consumers use rules to reach endpoints; they do not make a subnet a member of
two zones. Separate projects into different subnets and, where policy differs,
more specific zones such as `T2-Application-Lab`. Keep that zone in the same
architecture cell and adapt the matrix to it.

Do not treat a shared zone as an allow-all group. Filter routed traffic between
its member subnets; enforce same-subnet isolation at hosts, switches, or the
workload platform. See [enforcement boundaries](../security/firewall-policy.md#enforcement-boundaries).

## Network catalog

The existing `network_zones` keys are **logical guest-network names**, not
firewall-zone identifiers. `management` names a network purpose; **Control**
names the architectural layer. Defaults below describe connected instances.

| Network key | Layer / usual tier | Purpose | Guest attachment |
| --- | --- | --- | --- |
| `external_edge` | Edge / Tier 1 or 2 | public entry points, ingress, controlled egress | yes |
| `access` | Application / Tier 1 | identity brokers, SSO and access-service interfaces | yes |
| `identity` | Application / Tier 1 | connected identity authorities, directory, DNS | yes |
| `application` | Application / Tier 1 or 2 | internal APIs, shared apps, project and lab services | yes |
| `observability` | Application / Tier 1 | telemetry backends, dashboards, queries | yes |
| `telemetry_gateway` | Application / Tier 1 | dedicated telemetry intake and routing | yes |
| `security_telemetry` | Application / Tier 1 | separate hardened audit/log intake; no general peer access | yes |
| `cryptography` | Application / Tier 1 | online issuing CA, signing APIs, HSM gateways | yes |
| `management` | Control / owning connected tier | bastions, IaC runners, hypervisor and system admin interfaces | selected admin guests only |
| `storage` | Control / owning connected tier | archive, backup, and recovery storage interfaces | selected storage guests |
| `corosync` | Control / platform owner | host cluster membership and quorum | host-only |
| `ceph_public` | Control / platform owner | storage client transport, despite the name not Internet-facing | usually host-only |
| `ceph_cluster` | Control / platform owner | storage replication and recovery transport | host-only |
| `ceremony` | Control / Tier 0 | offline root trust, provisioning, recovery and custody | custody-local only |
| `client` | boundary peer | operator/user endpoints, not a server layer | reference only |

Tier 0 may reuse keys such as `identity` or `application` for services inside
custody. Their instances remain Tier 0 Control functions: map them to separate
custody-local attachments, not connected Tier 1 networks. An online replica is
a distinct Tier 1 instance. An access service's public listener belongs at the
Edge boundary; its protected backend can remain in `access`.

For hosts with several interfaces, document and filter each one. Do not bridge
zones through a guest or turn a management NIC into a transit path. Host-only
storage/cluster networks need local enforcement; their Control placement does
not require exposing them through the gateway.

## VLAN ID strategy

Keep one site allocation plan and avoid reusing VLAN IDs on a shared trunk.
Numbers are identifiers, not security controls and not tier numbers. Keep the
existing reference ranges when useful; allocate distinct networks when the
same logical key is used in multiple connected tiers.

| VLAN ID range | Reference use |
| --- | --- |
| `2-99` | control, access, identity, host clustering and storage transport |
| `100-199` | internal application, observability and archive networks |
| `200-299` | cryptography, telemetry and separately isolated custody examples |
| `300-399` | shared edge-facing networks |
| `400+` | local extensions, including distinct Tier 2 networks |

Tier 0 needs physically isolated custody infrastructure. A dedicated VLAN on
the connected fabric, a missing route, or a deny-all rule does not satisfy
the air-gap requirement. Its switches, hosts, and operator access must not
provide a concurrent path into connected tiers.

## Example network plan

These values illustrate the mapping; they are not an automatically allocated
plan. Replace them before deployment. The `.1` address can be the gateway on
each connected example subnet if that matches the local routing design.

| Network name | Key / purpose | VLAN | IPv4 subnet | Firewall zone |
| --- | --- | --- | --- | --- |
| `t2-edge` | `external_edge` | `432` | `10.42.32.0/24` | `T2-Edge` |
| `t2-apps` | `application` | `420` | `10.42.20.0/24` | `T2-Application` |
| `t2-admin` | `management` | `410` | `10.42.10.0/24` | `T2-Control` |
| `t1-edge` | `external_edge` | `320` | `10.30.30.0/24` | `T1-Edge` |
| `t1-access` | `access` | `11` | `10.10.11.0/24` | `T1-Application` |
| `t1-identity` | `identity` | `12` | `10.10.12.0/24` | `T1-Application` |
| `t1-apps` | `application` | `120` | `10.20.20.0/24` | `T1-Application` |
| `t1-crypto` | `cryptography` | `220` | `10.20.21.0/24` | `T1-Application` |
| `t1-admin` | `management` | `10` | `10.10.10.0/24` | `T1-Control` |
| `t1-archive` | `storage` | `140` | `10.20.40.0/24` | `T1-Control` |
| `t0-ceremony` | `ceremony` | `221`, isolated fabric only | `10.20.22.0/24` | none on connected gateway |

Optional reference allocations remain `observability` = VLAN `130`,
`telemetry_gateway` = `230`, `security_telemetry` = `231`, and host-only
`corosync` / `ceph_public` / `ceph_cluster` = `20` / `21` / `22`.
Keep host-only fabric un-routed unless a documented requirement demands
otherwise. Local custody routing, if needed, stays entirely within custody.

For each actual network, also record IPv6 policy, DHCP or static reservations,
DNS/time endpoints, zone membership, owner, and rule IDs in the architecture
repository's owned documentation. The inventory app can mirror that plan
after Day 2; it must not be required to rebuild it.

## Deployment order

1. Map existing or planned networks into the combined architecture view.
2. Establish the custody boundary separately; do not add it to the connected gateway.
3. Prepare connected control access with a tested local recovery path.
4. Create only the needed service and edge subnets, VLANs, trunks, and gateways.
5. Apply and test the [firewall matrix](../security/firewall-policy.md) before adding workloads.
6. Add Tier 2 subnets as projects appear; use Tier 1 services through scoped rules.

No dedicated Tier 2 edge is needed when shared Tier 1 ingress can publish
the workload. Existing identity, DNS, storage, and gateway services are valid
prerequisites; document their placement and policies instead of redeploying them.

## Automation mapping

The generator copies reference network values into each tier's examples. It
does **not** allocate unique subnets, create firewall zones, or enforce isolation.
Replace each tier's values using this plan. Terraform maps guests into those
networks; Ansible configures hosts using that tier's matching inventory IPs.

Use [Network inputs](../reference/network-inputs.md) for exact fields and
attachment examples, and [Proxmox networking](../platforms/proxmox/network-prerequisites.md)
for host bridges and fabric. Keep real addresses, rules, and credentials in
the environment-owned repositories.

## Continue reading

- [Architecture view](overview.md#tier-and-zone-view)
- [Firewall policy and validation](../security/firewall-policy.md)
- [UniFi zone setup](../platforms/unifi/zone-firewall.md)
- [USB HSM deployment](../security/usb-hsm-active-active-blueprint.md)
