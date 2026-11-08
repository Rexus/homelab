# ${prefix} Platform Standards

Local deployment standards. Values below are editable reference placeholders;
replace them with the selected project values.
[Platform record](docs/README.md) · [Conventions](docs/auto-docs/conventions/README.md)

## Contents

- [VM and DNS names](#vm-and-dns-names)
- [Role abbreviations](#role-abbreviations)
- [Proxmox tags](#proxmox-tags)
- [Networks and VLANs](#networks-and-vlans)
- [References](#references)

## VM and DNS names

| Type | Standard | Comments |
| --- | --- | --- |
| Internal domain | `corp.example.com` | Private DNS namespace. |
| External domain | `example.com` | Public DNS namespace. |
| VM name-part order | `<env>-<role>-<n>` | Omit env for production; use [role abbreviations](#role-abbreviations). |
| Number format | `1`, `2`, `3` | First and subsequent instances. |
| Internal service FQDN | `<role>.<env>.<internal-domain>` | Stable service endpoint. |
| External service FQDN | `<role>.<env>.<external-domain>` | Selected published endpoint. |
| Template name | `<os>-<release>-tmpl` | Candidate suffix where selected. |

## Role abbreviations

| Abbreviation | Full name | Comments |
| --- | --- | --- |
| `idm` | Identity management | Directory authority. |
| `idp` | Identity provider | Authentication and federation. |
| `ca` | Certificate authority | Certificate issuance. |
| `bootstrap` | Bootstrap execution host | Initial operator tooling. |
| `edge-lb` | Edge load balancer | Service entry point. |
| `db` | Database | Data service. |
| `k8node` | Kubernetes node | Cluster node. |

## Proxmox tags

| Type | Standard | Comments |
| --- | --- | --- |
| Service / product | `freeipa`, `keycloak`, `vault`, `haproxy` | Selected implementation. |
| Priority | `critical`, `high`, `standard`, `low` | Operational priority. |
| Exposure | `public`, `internal`, `restricted`, `isolated` | Intended reachability. |
| Lifecycle | `always-on`, `scheduled`, `ephemeral`, `maintenance` | Operating pattern. |
| Owner | `platform`, `security`, `apps` | Responsible team. |

## Networks and VLANs

**SDN VNet ID:** 2–8 lowercase letters/digits, starting with a letter; no hyphens or underscores.
**Network label / Alias:** readable text; separate from the SDN ID and VM/DNS naming.

### Zone mapping

| Firewall zone / SDN zone ID | Included SDN VNet IDs |
| --- | --- |
| [DMZ](#dmz-zone) / `dmz` | `edge`, `build`; separate client subnet |
| [Services](#services-zone) / `services` | `access`, `app`, `obs`, `lab` |
| [Control](#control-zone) / `control` | `ident`, `control`, `crypto`; optional `admin` |
| [Fabric](#fabric-zone) / — | Host management, BMC, Corosync and Ceph |
| Offline custody / — | Disconnected ceremony network |

### DMZ zone

| VLAN ID | SDN VNet ID (2–8 chars) | Network label / Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `320` | `edge` | External edge | `10.30.30.0/24` | `10.30.30.1` | Edge load balancers and ordinary proxy/cache. |
| `321` | `build` | Delivery edge | `10.30.31.0/24` | `10.30.31.1` | Build runners and selected mirrors. |
| Set locally | — | Ordinary clients | Set locally | Set locally | Separate wired/WiFi subnet. |

### Services zone

| VLAN ID | SDN VNet ID (2–8 chars) | Network label / Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `11` | `access` | Application access | `10.10.11.0/24` | `10.10.11.1` | Optional front-end network. |
| `120` | `app` | Application services | `10.20.20.0/24` | `10.20.20.1` | Platform cluster and data services. |
| `130` | `obs` | Observability backends | `10.20.30.0/24` | `10.20.30.1` | Optional VM path. |
| `420` | `lab` | Lab environments | `10.42.20.0/24` | `10.42.20.1` | Select a separate Lab zone for untrusted experiments. |

### Control zone

| VLAN ID | SDN VNet ID (2–8 chars) | Network label / Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `12` | `ident` | Directory authority | `10.10.12.0/24` | `10.10.12.1` | Directory primary/replica. |
| `13` | `control` | Control cluster | `10.10.13.0/24` | `10.10.13.1` | Control Kubernetes services. |
| `14` | `admin` | VM administration | `10.10.14.0/24` | `10.10.14.1` | Optional split; current starters use VLAN 10. |
| `220` | `crypto` | Cryptographic services | `10.20.21.0/24` | `10.20.21.1` | Issuer, signing and standalone secrets. |
| `140` | — | Backup and archive | `10.20.40.0/24` | `10.20.40.1` | Selected storage endpoints. |

### Fabric zone

| VLAN ID | SDN VNet ID (2–8 chars) | Network label / Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `10` | — | Host management | `10.10.10.0/24` | `10.10.10.1` | Current starter management attachment. |
| Set locally | — | Out-of-band management | Set locally | Set locally or none | BMC/IPMI. |
| `20` | — | Cluster quorum | Set locally | None | Corosync. |
| `21` | — | Storage clients | Set locally | None | Ceph client transport. |
| `22` | — | Storage replication | Set locally | None | Ceph replication. |

### Offline custody

| VLAN ID | SDN VNet ID (2–8 chars) | Network label / Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `221` | — | Offline custody | `10.20.22.0/24` | None | Disconnected ceremony network. |

## References

- [VMID convention](docs/auto-docs/conventions/vmid-convention.md)
- [VM/DNS patterns](docs/auto-docs/conventions/proxmox-conventions.md#vm-names)
- [Tag conventions](docs/auto-docs/conventions/proxmox-conventions.md#vm-tags)
- [Network allocations and deployment mapping](docs/auto-docs/conventions/network-plan.md)
- [SDN fields and setup](docs/auto-docs/deployment/foundation/step-1c-sdn.md)
