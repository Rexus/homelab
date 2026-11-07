# ${prefix} Naming Conventions

Project standards for names, domains, tags, VMIDs, and VLANs. Values below are
editable reference placeholders, not approved allocations. Replace each value
in place when the project standard is agreed. Network tables record the selected
subnets; individual guest IPs, hosts and VMIDs remain in inventory and Terraform.

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
| `bootstrap` | Bootstrap execution host | Initial privileged operator tooling; separate from the later CI runner. |
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
| Image tags | `el10`, `alma`, `x86-64-v3`, `cloud-init` | Inherited from the shared template catalog. |

Tags describe the VM; they do not grant access. Product tags allow hostnames to
remain stable. [Tag details](auto-docs/reference/proxmox-conventions.md#vm-tags).

## VMID ranges

| Type | Standard | Comments |
| --- | --- | --- |
| Staged Linux builders and legacy templates | `100-199` | Existing template IDs remain valid; new templates use the range below. |
| Infrastructure | `200-299` | Infrastructure guests. |
| Shared services | `300-399` | Shared service guests. |
| Databases | `400-499` | Database guests. |
| Application and lab VMs | `500-999` | Workload guests. |
| Versioned VM templates | `9000-9999` | Examples use `9100-9103`; retain IDs after testing and selection. |

Ranges describe **resource purpose**, not tier, zone, or VLAN. Reservations are
cluster-wide across all repositories; exact assignments remain in Terraform.
[ID guidance](auto-docs/reference/proxmox-conventions.md#vm-and-template-id-ranges).

## Networks and VLANs

| Type | Standard | Comments |
| --- | --- | --- |
| VLAN ranges | `2-99` platform; `100-199` services; `200-299` specialist; `300-399` edge; `400+` projects | Allocation convention, not a security policy. |
| Zone grouping | Protection layer and matching access policy | Tier ownership does not name or select a zone. Split zones when policy differs. |
| VNet Name / ID | 2–8 lowercase alphanumeric characters, starting with a letter | Stable Proxmox attachment ID; the IaC `bridge` value. |
| Alias | Purpose in readable words | Proxmox description; use the same wording for the UniFi network name where practical. |
| Direct bridge alternative | `vmbr0` with the network's VLAN tag | Use either VNet tagging or a NIC tag, never both. |
| SDN DNS integration | Unconfigured | Guest resolvers remain a separate DHCP/CloudInit/OS setting unless record-management integration is selected. |

### Zone mapping

| Zone — UniFi / Proxmox SDN | Included networks — VNet IDs |
| --- | --- |
| [DMZ](#dmz-zone) / `dmz` | `edge`, `build`; ordinary clients on a separate subnet |
| [Services](#services-zone) / `services` | `access`, `app`, `obs`, `lab` |
| [Control](#control-zone) / `control` | `ident`, `control`, `crypto`; optional `admin` split and backup/archive endpoints |
| [Fabric](#fabric-zone) / none required | Host management, BMC/IPMI, Corosync and Ceph networks; host underlay |

Layers map broadly as **Edge → DMZ**, **Application / Services → Services**,
**Control → Control and Fabric**. A layer can contain several zones. A separate `Clients`
zone is preferable when endpoint policy differs from public servers; untrusted
experiments should use a separate `Lab` zone. If selected, move that network to
the new zone in both records; a network belongs to one firewall zone.

The tables below are editable reference allocations. **Name** is the short VNet
ID; `—` means no Proxmox VNet is required in this reference. Matching zone names
do not synchronize firewall rules or grant member networks access to each other.
Control groups privileged VM services. Fabric groups hardware and host networks
and needs no guest SDN zone; its name does not select the Proxmox SDN Fabrics feature.

### DMZ zone

| VLAN ID | Name | Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `320` | `edge` | External edge | `10.30.30.0/24` | `10.30.30.1` | `external_edge`: edge load balancers and ordinary proxy/cache. |
| `321` | `build` | Delivery edge | `10.30.31.0/24` | `10.30.31.1` | `delivery_edge`: external build runners; authoritative mirrors require their selected service. |
| Set locally | `—` | Ordinary clients | Set locally | Set locally | Separate wired/WiFi subnet; no public-server subnet sharing. |

### Services zone

| VLAN ID | Name | Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `11` | `access` | Application access | `10.10.11.0/24` | `10.10.11.1` | Optional front-end network; not the current identity-provider node attachment. |
| `120` | `app` | Application services | `10.20.20.0/24` | `10.20.20.1` | Shared `application`: platform cluster and development data services. |
| `130` | `obs` | Observability backends | `10.20.30.0/24` | `10.20.30.1` | Optional VM path; normal observability runs in the platform cluster on `app`. |
| `420` | `lab` | Lab environments | `10.42.20.0/24` | `10.42.20.1` | Lab cluster; Linux labs need an `application` override. Use Lab zone for untrusted experiments. |

### Control zone

| VLAN ID | Name | Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `12` | `ident` | Directory authority | `10.10.12.0/24` | `10.10.12.1` | `identity`: dedicated directory primary/replica. |
| `13` | `control` | Control cluster | `10.10.13.0/24` | `10.10.13.1` | Kubernetes nodes hosting identity federation, cluster secrets and control tools. |
| `14` | `admin` | VM administration | `10.10.14.0/24` | `10.10.14.1` | Optional split for `management` VMs; current starters use VLAN 10. Select inputs before deployment. |
| `220` | `crypto` | Cryptographic services | `10.20.21.0/24` | `10.20.21.1` | `cryptography`: issuing CA, optional HSM gateways and standalone secrets variant. |
| `140` | `—` | Backup and archive | `10.20.40.0/24` | `10.20.40.1` | Existing storage endpoints; select a separate Storage zone if policy differs. |

### Fabric zone

| VLAN ID | Name | Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `10` | `—` | Host management | `10.10.10.0/24` | `10.10.10.1` | Host underlay; current starter log/runner VMs also use it until the `admin` split is selected. |
| Set locally | `—` | Out-of-band management | Set locally | Set locally or none | IPMI/BMC/controllers; approved administrative access only. |
| `20` | `—` | Cluster quorum | Set locally | None | Host-only Corosync fabric; outside guest SDN. |
| `21` | `—` | Storage clients | Set locally | None | Host-only Ceph client fabric; outside guest SDN. |
| `22` | `—` | Storage replication | Set locally | None | Host-only Ceph replication fabric; outside guest SDN. |

Host management has only the approved administrative path. Keep Corosync/Ceph
transport non-routed where the topology permits it; Fabric membership does not
replace switch/host isolation or require a gateway on each network.

### Offline custody

| VLAN ID | Name | Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `221` | `—` | Offline custody | `10.20.22.0/24` | None | Separate disconnected fabric; no connected gateway zone. |

The [reference network plan](auto-docs/reference/network-plan.md#deployment-mapping)
maps these networks to owning repositories, actual deployment inputs and capability guides.
Its [host/VM split](auto-docs/reference/network-plan.md#separate-host-and-vm-administration)
identifies the current mixed management default and the changes needed for separate VM administration.
These tables record approved project choices, not a second guest inventory or an installer.
With [SDN lookup](auto-docs/reference/network-inputs.md#sdn-subnet-lookup), applied
Proxmox metadata supplies prefix/gateway; explicit networks retain their IaC values.
Keep this record aligned after an approved change. Existing project worksheets are not refreshed.
Use the [SDN field guide](auto-docs/deployment/foundation/step-1c-sdn.md) for GUI fields
and the [VLAN conventions](auto-docs/architecture/networking/README.md#vlan-id-strategy) for allocation ranges.
