# ${prefix} Naming and Allocations

Fill in `TBD` with this project's approved values. This is the quick reference
for conventions and reservations, not a second live inventory. Keep host IPs
and deployment values in the owning tier's inputs and record changes here.

## Contents

- [Project](#project)
- [VM and DNS names](#vm-and-dns-names)
- [Resource IDs](#resource-ids)
- [Networks](#networks)
- [Platform resources](#platform-resources)

## Project

| Setting | Project value |
| --- | --- |
| Collection prefix | `${prefix}` |
| Owner / change approver | TBD |
| Sites and platform clusters | TBD |
| Internal DNS domain | TBD |
| Environment names | TBD |
| Tier 0 / Tier 1 / Tier 2 owners | TBD |

Reference: [tier ownership](auto-docs/architecture/tier-model.md).

## VM and DNS names

| Convention | Approved pattern / example |
| --- | --- |
| Stable inventory key, such as `<role>-<n>` | TBD |
| Role abbreviations | TBD |
| Production hostname pattern | TBD |
| Non-production hostname pattern | TBD |
| `platform_hostname_prefix` / `platform_hostname_suffix` by environment | TBD |
| `platform_domain` and FQDN pattern | TBD |
| Template name pattern and variants | TBD |
| Workload tags: owner, service, lifecycle, priority | TBD |

Reference: [VM and template naming](auto-docs/platforms/proxmox/conventions.md)
and [inventory inputs](auto-docs/reference/infrastructure-automation-layout.md#ownership-rule).
Keep inventory keys stable; environment prefixes/suffixes shape deployed names.

## Resource IDs

| Platform / cluster | Owner and purpose | Reserved VM/LXC ID range | Template IDs |
| --- | --- | --- | --- |
| TBD | Tier 0 custody | TBD | TBD |
| TBD | Tier 1 platform | TBD | TBD |
| TBD | Tier 2 workloads | TBD | TBD |

Reserve non-overlapping IDs wherever tiers or environments share a platform's
ID namespace. Record individual assignments in Terraform, not in a second
host list here. Reference: [ID planning](auto-docs/platforms/proxmox/conventions.md#vm-and-template-id-ranges).

## Networks

Fill in only the cells you use; add rows for additional subnets or projects.
`network_zones` keys identify guest attachments, not gateway firewall zones.

| Tier / layer | Firewall zone | Network name / key | VLAN | IPv4 / IPv6 CIDR |
| --- | --- | --- | --- | --- |
| Tier 2 / Edge | `T2-Edge` | TBD | TBD | TBD |
| Tier 2 / Application | `T2-Application` | TBD | TBD | TBD |
| Tier 2 / Control | `T2-Control` | TBD | TBD | TBD |
| Tier 1 / Edge | `T1-Edge` | TBD | TBD | TBD |
| Tier 1 / Application | `T1-Application` | TBD | TBD | TBD |
| Tier 1 / Control | `T1-Control` | TBD | TBD | TBD |
| Tier 0 / Control | no connected zone | custody-local: TBD | isolated fabric: TBD | TBD |

| Network name / key | Gateway or no gateway | Bridge / VNet | DHCP / static ranges | DNS / time services |
| --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD |

| Policy convention | Project choice |
| --- | --- |
| Firewall rule IDs and address/port object names | TBD |
| IPv6 policy | TBD |
| User and administrator entry networks | TBD |
| Custody isolation and offline transfer procedure | TBD |
| Detailed policy record and validation evidence | TBD |

References: [network plan](auto-docs/architecture/network.md),
[attachment fields](auto-docs/reference/network-inputs.md), and
[firewall rules](auto-docs/security/firewall-policy.md). Allocate distinct
connected-tier subnets. Tier 0 must not share the connected fabric.

## Platform resources

| Resource | Naming convention / local mapping |
| --- | --- |
| Platform nodes and clusters | TBD |
| Bridges, VNets and uplinks | TBD |
| Storage classes and datastore names | TBD |
| Image/template catalog and VMIDs | TBD |
| Source repositories, branches and deployment environments | TBD |
| Shared automation revision used by deployments | TBD |

References: [platform conventions](auto-docs/platforms/proxmox/conventions.md)
and [shared-code recovery](auto-docs/reference/generated-repository-model.md#shared-code-and-recovery).
