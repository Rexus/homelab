# Network zones and IaC mapping

Use one stable network map for architecture, Proxmox, Terraform, and firewall
policy. Names describe purpose: `management`, `identity`, `application`,
`cryptography`, and so on. Not every network is needed at the first deployment.

## Table of contents

- [Zone assignment](#zone-assignment)
- [Network catalog](#network-catalog)
- [VLAN ID strategy](#vlan-id-strategy)
- [Automation mapping](#automation-mapping)
- [Attachment constraints](#attachment-constraints)
- [Continue reading](#continue-reading)

<a id="purpose"></a>

## Zone assignment

The [layered view](../README.md#layered-model) reads left to right:

| Layer | Firewall zone | Network purposes |
| --- | --- | --- |
| Edge | `DMZ` | ingress and controlled egress |
| Application | `Services` | shared services, access front ends, workloads |
| Control | `Control` | administration, directory authority, control cluster, cryptography |
| Offline custody | none | root keys and authorized recovery ceremonies |

A tier selects the owning repo, not a VLAN or zone. One subnet belongs to one
firewall zone; group subnets only when their baseline policy matches. Add
`Lab`, `Storage`, or another zone when the required policy differs, not
because another repository exists.

Zone membership does not allow traffic. Use [named service rules](firewall-policy.md)
between subnets, including subnets in the same zone. Same-subnet traffic needs
host, switch, or workload enforcement. WAN, client devices, and VPN entry are
boundary peers; VPN membership alone grants no control authority.

<a id="example-network-plan"></a>

## Network catalog

Reference allocations below are examples, not an automatically allocated plan.
The logical keys are the Terraform `network_zones` names, **not firewall zones**.
Short VNet names such as `edge`, `apps`, `control`, and `crypto` map to these
purposes in the Proxmox examples.

| Network key | Purpose | VLAN / subnet example | Firewall zone |
| --- | --- | --- | --- |
| `external_edge` | shared ingress and outbound proxies | 320 / `10.30.30.0/24` | DMZ |
| `application` | internal shared services and workloads | 120 / `10.20.20.0/24` | Services |
| `application` in the lab repo | isolated lab workloads | 420 / `10.42.20.0/24` | Services or separate Lab policy |
| `access` | application-only access and SSO front ends | 11 / `10.10.11.0/24` | Services; privileged interfaces need Control protection |
| `management` | Proxmox API/UI, bastions, protected runners | 10 / `10.10.10.0/24` | Control |
| `identity` | directory authority, DNS, Kerberos | 12 / `10.10.12.0/24` | Control |
| `control_cluster` | control-cluster nodes and private API | 13 / `10.10.13.0/24` | Control |
| `cryptography` | online issuer, privileged secrets, HSM gateways | 220 / `10.20.21.0/24` | Control |
| `storage` | archive/backup receivers; separate administration | 140 / `10.20.40.0/24` | Control or separate Storage policy |

Additional networks are introduced only when needed:

| Network key | Reference VLAN | Use |
| --- | --- | --- |
| `observability` | 130 | telemetry backends and dashboards in Services |
| `telemetry_gateway` | 230 | scoped telemetry intake in Services |
| `security_telemetry` | 231 | restricted audit/log intake |
| `corosync` | 20 | non-routed Proxmox quorum fabric |
| `ceph_public` | 21 | non-routed storage client fabric; not public Internet |
| `ceph_cluster` | 22 | non-routed storage replication fabric |
| `ceremony` | 221 on a separate fabric | offline custody; example subnet `10.20.22.0/24`, no connected gateway |
| `client` | site-defined | workstation/endpoint reference, not a server deployment |

A service may have separate client, backend, and administrative interfaces.
Permit the required listeners without exposing authority or administration.
Multi-interface hosts must not bridge zones. Offline custody needs physical
separation: a VLAN, missing route, or deny rule on a connected fabric is not an air gap.

## VLAN ID strategy

| Range | Reference use |
| --- | --- |
| `2-99` | management, access, identity, clustering, storage transport |
| `100-199` | internal services, applications, observability, archive |
| `200-299` | cryptography, ceremony, specialist telemetry |
| `300-399` | edge-facing networks |
| `400+` | projects, labs, local extensions |

These are allocations, not security labels or tier numbers. Keep one site plan
and avoid duplicate IDs on shared trunks. Record chosen ranges and names in
`docs/naming-conventions.md` in the generated architecture repo; keep complete
subnets, gateways, and addresses in network inventory.

## Automation mapping

Tier 0 operates the physical network across all tiers. Each tier selects
approved guest attachments; the generator neither creates networks nor installs
firewall rules.

| Location or field | Responsibility |
| --- | --- |
| Shared `config/platform.tfvars` / `shared_network_zones` | Existing network references used across tiers, such as `application` |
| Tier-local `terraform/common.tfvars` / `network_zones` | Tier-specific networks and overrides of shared bridge/VNet, VLAN, subnet, gateway references |
| `vm_instances.<key>.network_zone_key` | Select that guest's network; the key joins Terraform with Ansible inventory |
| Tier-local Ansible inventory and group vars | Host identity and IP inputs used by both tools |
| Kubernetes `nodes[*].bridge` and `vlan_id` | Direct node attachment; this deployment does not use the Linux `network_zones` map |
| Proxmox host and network configuration | Host management, quorum/storage fabrics, bridges, routing and segmentation |

For example, Linux `network_zone_key = "cryptography"` selects that tier's
`network_zones.cryptography` attachment. Cluster nodes instead use a `control`
VNet or `vmbr0` with VLAN 13. Let either the VNet or the guest NIC own tagging;
do not tag twice. Exact fields and runnable examples belong in
[network inputs](../../reference/network-inputs.md).

Identical logical keys across repos do not allocate or guarantee the same
subnet when overridden. Sharing a reference does not attach guests or grant
access; guest selections and host IPs remain tier-owned. Review bridge, VLAN,
address, and VMID values before use. Host-only
fabrics stay outside guest inputs unless a guest attachment is deliberate.

<a id="deployment-order"></a>

<a id="growth-and-assurance"></a>

## Attachment constraints

Management and host fabrics support infrastructure control; guest attachments follow
the selected service purpose and policy. Tier numbers are not VLANs. Offline custody
remains separate from the routed platform.

Existing networks can satisfy the same policy; a project does not need another DMZ
when a shared proxy can publish its endpoint. Isolation and recovery requirements
apply regardless of subnet count.

The [Step 1 procedure](../../deployment/stage-1-foundation/README.md#step-1-prepare-compute-and-templates) owns setup
order; [firewall rollout](../../deployment/stage-1-foundation/procedures/firewall-rollout.md)
owns implementation and acceptance tests.

## Continue reading

- [Deployment stages](../../deployment/README.md)
- [Proxmox host networking](../../deployment/stage-1-foundation/procedures/host-network.md)
- [Firewall policy](firewall-policy.md) and [UniFi zone setup](../../deployment/stage-1-foundation/procedures/unifi-zones.md)
- [Project conventions](../../development/project-documentation.md#start-with-project-values)
