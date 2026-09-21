# ${prefix} Naming Conventions

Our quick reference for names, tags, VMIDs, and VLANs. Replace `TBD` with the
chosen convention; the examples are suggestions, not assigned resources.
Keep individual hosts, IPs, and VMIDs in inventory and Terraform.

**Tier = owning repo and potential impact. Zone = network protection.**
Do not encode both into names or numbers. Record service ownership in the
[project overview](owned/design/overview.md).

## Contents

- [VM and DNS names](#vm-and-dns-names)
- [Proxmox tags](#proxmox-tags)
- [VMID ranges](#vmid-ranges)
- [Networks and VLANs](#networks-and-vlans)

## VM and DNS names

| Choice | Example | Your choice |
| --- | --- | --- |
| Internal domain | `corp.example.com` | TBD |
| Name-part order | `<env>-<role>-<n>`; omit env for production | TBD |
| Production / test name | `idm-1` / `test-idm-1` | TBD |
| Role abbreviations | `idm`, `idp`, `ca`, `edge-lb`, `db`, `k8node` | TBD |
| Number format | `1`, `2`, `3`; always present | TBD |
| FQDN | `idm-1.corp.example.com` | TBD |
| Template name | `<os>-<release>-tmpl`; add a build suffix for versioned candidates | TBD |

Keep the inventory key stable, such as `idm-1`. Environment decoration comes
from `platform_hostname_prefix` or `platform_hostname_suffix`; use one style.
Keep tier, VLAN, IP, and product names out of the hostname.
[Name patterns and alternatives](auto-docs/platforms/proxmox/conventions.md#vm-names).

## Proxmox tags

| Tag category | Example values | Your choice |
| --- | --- | --- |
| Service / product | `freeipa`, `keycloak`, `vault`, `haproxy` | TBD |
| Priority | `critical`, `high`, `standard`, `low` | TBD |
| Exposure | `public`, `internal`, `restricted`, `isolated` | TBD |
| Lifecycle | `always-on`, `scheduled`, `ephemeral`, `maintenance` | TBD |
| Owner | `platform`, `security`, `apps` | TBD |
| Image tags, inherited from the template catalog | `x86_64`, `el10`, `alma10`, `cloud-init` | TBD |

Example VM tags: `freeipa, critical, restricted, always-on, platform`.
Tags describe the VM; they do not grant access. Use product tags so names can
stay stable. [Tag details](auto-docs/platforms/proxmox/conventions.md#vm-tags).

## VMID ranges

| Purpose | Reference range | Our range / cluster |
| --- | --- | --- |
| Base templates and staged Linux builders | `100-199` | TBD |
| Infrastructure | `200-299` | TBD |
| Shared services | `300-399` | TBD |
| Databases | `400-499` | TBD |
| Application and lab VMs | `500-999` | TBD |
| Versioned template candidates | `9000-9999` | TBD |

The range says **what the resource is**, not its tier, zone, or VLAN.
For example, `200` is an infrastructure allocation, not "Tier 2".
Reserve IDs across all repos using the same cluster; keep exact assignments in
Terraform. [ID guidance](auto-docs/platforms/proxmox/conventions.md#vm-and-template-id-ranges).

## Networks and VLANs

| Convention | Example | Your choice |
| --- | --- | --- |
| Network name | purpose first: `management`, `identity`, `apps`, `edge`, `lab` | TBD |
| VLAN ranges | `2-99` platform; `100-199` services; `200-299` specialist; `300-399` edge; `400+` projects | TBD |
| Firewall zones | `DMZ`, `Services`, `Control`; split further only for different policy | TBD |
| Bridge / VNet naming | `vmbr0` with VLAN tags, or short purpose-based VNet IDs | TBD |

| Network purpose | Example VLAN / zone | Our VLAN / zone |
| --- | --- | --- |
| Administration | `10 / Control` | TBD |
| Identity authority | `12 / Control` | TBD |
| Internal applications | `120 / Services` | TBD |
| Public-facing edge | `320 / DMZ` | TBD |
| Lab / project | `420 / Services`, or a separate `Lab` zone | TBD |

VLAN IDs are allocations, not tier numbers or firewall rules. Offline custody
uses a separate isolated fabric, not a connected zone. Keep complete subnet,
gateway, and address assignments in the network inventory; record conventions here.
[Network and VLAN guide](auto-docs/architecture/network.md#vlan-id-strategy).
