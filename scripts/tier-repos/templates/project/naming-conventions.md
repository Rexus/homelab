# ${prefix} Naming Conventions

Project standards for names, domains, tags, VMIDs, and VLANs. Values below are
editable reference placeholders, not approved allocations. Replace each value
in place when the project standard is agreed. Individual hosts, IPs, and VMIDs
remain in inventory and Terraform.

**Tier = owning repo and potential impact. Zone = network protection.**
Neither defines a naming or numbering scheme. Service ownership is recorded in the
[platform record](README.md#selected-design).

## Contents

- [VM and DNS names](#vm-and-dns-names)
- [Role abbreviations](#role-abbreviations)
- [Proxmox tags](#proxmox-tags)
- [VMID ranges](#vmid-ranges)
- [Networks and VLANs](#networks-and-vlans)

## VM and DNS names

| Type | Standard | Comments |
| --- | --- | --- |
| Internal domain | `corp.example.com` | Private host and service DNS namespace. |
| External domain | `example.com` | Public service DNS namespace; does not imply public access. |
| VM name-part order | `<env>-<role>-<n>` | Omit env for production; role comes from [role abbreviations](#role-abbreviations). |
| Number format | `1`, `2`, `3` | Always present in VM names, including the first instance. |
| Internal service FQDN | `<role>.<env>.<internal-domain>` | For example, `idp.prod.corp.example.com`; no VM instance number. |
| External service FQDN | `<role>.<env>.<external-domain>` | For example, `idp.prod.example.com`; publish only approved endpoints. |
| Template name | `<os>-<release>-tmpl` | Add a build suffix for versioned candidates. |

Inventory keys remain stable, such as `idm-1`. VM environment decoration comes
from `platform_hostname_prefix` or `platform_hostname_suffix`; select one style.
Tier, VLAN, IP, and product names are excluded from hostnames.
Service FQDNs identify stable endpoints rather than individual VMs. Host FQDNs
remain `<vm-name>.<platform_domain>` in the current automation; service DNS,
ingress, and certificate records require separate configuration.
[Name patterns and alternatives](auto-docs/reference/proxmox-conventions.md#vm-names).

## Role abbreviations

The `role` field in VM names and service FQDNs refers to this table. Abbreviations
describe capabilities, independently of the deployed product.

| Abbreviation | Full name | Comments |
| --- | --- | --- |
| `idm` | Identity management | Directory authority. |
| `idp` | Identity provider | Application authentication and federation. |
| `ca` | Certificate authority | Certificate issuance. |
| `edge-lb` | Edge load balancer | Service entry point. |
| `db` | Database | Data service. |
| `k8node` | Kubernetes node | Cluster node role; not normally a service alias. |

## Proxmox tags

| Type | Standard | Comments |
| --- | --- | --- |
| Service / product | `freeipa`, `keycloak`, `vault`, `haproxy` | Implementation identity; VM names remain role-based. |
| Priority | `critical`, `high`, `standard`, `low` | Operational priority. |
| Exposure | `public`, `internal`, `restricted`, `isolated` | Intended reachability, not an access grant. |
| Lifecycle | `always-on`, `scheduled`, `ephemeral`, `maintenance` | Operating pattern. |
| Owner | `platform`, `security`, `apps` | Responsible team. |
| Image tags | `x86_64`, `el10`, `alma10`, `cloud-init` | Inherited from the shared template catalog. |

Tags describe the VM; they do not grant access. Product tags allow hostnames to
remain stable. [Tag details](auto-docs/reference/proxmox-conventions.md#vm-tags).

## VMID ranges

| Type | Standard | Comments |
| --- | --- | --- |
| Base templates and staged Linux builders | `100-199` | Publication and build resources. |
| Infrastructure | `200-299` | Infrastructure guests. |
| Shared services | `300-399` | Shared service guests. |
| Databases | `400-499` | Database guests. |
| Application and lab VMs | `500-999` | Workload guests. |
| Versioned template candidates | `9000-9999` | Candidate images before promotion. |

Ranges describe **resource purpose**, not tier, zone, or VLAN. Reservations are
cluster-wide across all repositories; exact assignments remain in Terraform.
[ID guidance](auto-docs/reference/proxmox-conventions.md#vm-and-template-id-ranges).

## Networks and VLANs

| Type | Standard | Comments |
| --- | --- | --- |
| Network name | `management`, `identity`, `apps`, `edge`, `lab` | Purpose first. |
| VLAN ranges | `2-99` platform; `100-199` services; `200-299` specialist; `300-399` edge; `400+` projects | Allocation convention, not a security policy. |
| Firewall zones | `DMZ`, `Services`, `Control` | Split further only for different policy. |
| Bridge / VNet naming | `vmbr0` with VLAN tags | SDN alternative: short, purpose-based VNet IDs. |

| Network purpose | Standard | Comments |
| --- | --- | --- |
| Administration | `10 / Control` | VLAN / zone. |
| Identity authority | `12 / Control` | VLAN / zone. |
| Internal applications | `120 / Services` | VLAN / zone. |
| Public-facing edge | `320 / DMZ` | VLAN / zone. |
| Build runners / authoritative mirrors | `321 / DMZ` | Separate Tier 1 subnet; not the public Tier 2 edge. |
| Ordinary clients | `Site-defined / DMZ` | Separate Tier 2 subnet; no implicit peer access. |
| Lab / project | `420 / Services` | Separate `Lab` zone when policy requires it. |

VLAN IDs are allocations, not tier numbers or firewall rules. Offline custody
uses a separate isolated fabric, not a connected zone. Complete subnet,
gateway, and address assignments remain in the network inventory.
[Network and VLAN guide](auto-docs/architecture/networking/README.md#vlan-id-strategy).
