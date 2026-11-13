# ${prefix} Platform Standards

Local deployment standards. Values below are editable reference placeholders;
replace them with the selected project values.
[Platform record](docs/README.md) · [Conventions](docs/auto-docs/02-conventions/README.md)

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
| VM name-part order | `<role>-<n>` | Optional `<env>-<role>-<n>`; use [role abbreviations](#role-abbreviations). |
| VM hostname length | Prefer 3–8 characters | Include hyphens and sequence; `boot-1`, `idm-1`, `api-gw-1`. |
| Number format | `1`, `2`, `3` | First and subsequent instances. |
| Service DNS label | Prefer familiar 2–8 character labels | `ldap`, `idp`, `auth`, `git`, `proxy`, `db`, `nfs`; see [service DNS names](docs/auto-docs/02-conventions/service-dns.md). |
| Internal service FQDN | `<service>.<internal-domain>` | Stable endpoint, such as `ldap.corp.example.com`. |
| External service FQDN | `<service>.<external-domain>` | Selected published endpoint, such as `git.example.com`. |
| Service scope | Optional `<service>.<env>.<domain>` or `<service>.<project>.<domain>` | Add only when needed to distinguish services. |
| Template name | `<os>-<release>-tmpl` | Candidate suffix where selected. |

The hostname length is a preference; DNS labels allow 63 octets. SDN IDs below have
a separate hard restriction. Template titles and Kubernetes object/release names
keep their own conventions. Existing host keys require a deliberate
[state and identity migration](docs/auto-docs/02-conventions/proxmox-conventions.md#existing-installations),
not an automatic rename during refresh.
Service labels identify interfaces; numbered VM names identify individual machines.

## Role abbreviations

| Abbreviation | Full name | Comments |
| --- | --- | --- |
| `idm` | Identity management | Directory authority. |
| `idp` | Identity provider | Authentication and federation. |
| `ca` | Certificate authority | Certificate issuance. |
| `boot` | Bootstrap execution host | `boot-1`; manual initial operator tooling. |
| `lb` | Edge load balancer | `lb-1`; service entry point. |
| `db` | Database | Data service. |
| `repo` | Repository data | `repo-1`; Git repository storage. |
| `kv` | Key-value service | `kv-1`; queue/cache backend. |
| `k8ctl` | Control-cluster control-plane node | Tier 0 cluster. |
| `pctl` | Platform-cluster control-plane node | Tier 1 cluster. |
| `wctl` | Lab-cluster control-plane node | Tier 2 cluster. |
| `otel` / `metric` | Telemetry gateway / metrics backend | Dedicated-VM alternative. |
| `util` | Lab utility guest | `util-1`. |
| `cadm` | Cryptography administration helper | Optional `cadm-1`. |

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

- [VMID convention](docs/auto-docs/02-conventions/vmid-convention.md)
- [VM/DNS patterns](docs/auto-docs/02-conventions/proxmox-conventions.md#vm-names)
- [Tag conventions](docs/auto-docs/02-conventions/proxmox-conventions.md#vm-tags)
- [Network allocations and deployment mapping](docs/auto-docs/02-conventions/network-plan.md)
- [SDN fields and setup](docs/auto-docs/03-deployment/foundation/proxmox/step-1c-sdn.md)
