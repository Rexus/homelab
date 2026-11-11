# Network plan and deployment mapping

Reference allocations connect firewall zones, Proxmox SDN VNet IDs and the
supplied deployment inputs. They are editable examples, not detected infrastructure
or an installer. Record selected values in the generated architecture repository's
`platform-standards.md`; individual guest IPs remain in tier-local inventory.

## Contents

- [Read the mapping](#read-the-mapping)
- [Zone overview](#zone-overview)
- [Network allocations](#network-allocations)
- [Deployment mapping](#deployment-mapping)
- [Segmentation](#segmentation)
- [Separate host and VM administration](#separate-host-and-vm-administration)
- [References](#references)

## Read the mapping

- **Layer:** architectural protection position, from Edge through Application / Services to Control.
- **Firewall zone:** networks with compatible traffic policy. A layer can contain several zones.
- **SDN VNet ID:** the Proxmox **Name** field, 2–8 alphanumeric characters starting with a letter;
  hyphens and underscores are not allowed. This project's convention is lowercase.
- **Network label / Alias:** the readable name, separate from the restricted SDN identifier.
- **Logical key:** the Terraform network selection, such as `identity`; it need not match the VNet ID.
- **Tier:** owning repository and impact. It does not name a zone or allocate a VLAN.

Matching UniFi and Proxmox zone labels aid navigation; their configuration and
permissions remain independent. Host-only networks need no guest SDN zone.
UniFi's built-in External and Gateway zones retain their platform meanings. [1][2]

## Zone overview

| Zone — UniFi / Proxmox SDN | Included networks — VNet IDs |
| --- | --- |
| [DMZ](#dmz-zone) / `dmz` | `edge`, `build`; ordinary clients on a separate subnet in the baseline |
| [Services](#services-zone) / `services` | `access`, `app`, `obs`, `lab` |
| [Control](#control-zone) / `control` | `ident`, `control`, `crypto`; optional `admin` split and backup/archive endpoints |
| [Fabric](#fabric-zone) / none required | Host management, BMC/IPMI, Corosync and Ceph networks; host underlay |

DMZ occupies the **Edge layer**, Services the **Application / Services layer**.
Control and Fabric belong to the foundational **Control layer**, with different
memberships and policy. Control groups privileged VM services. Fabric groups
hardware management and host transport; its name does not enable Proxmox **SDN > Fabrics**.

The baseline retains separate client, edge-server and build VLANs. Prefer a
separate **Clients** zone when workstation policy differs from public servers,
and a separate **Lab** zone for untrusted experiments. Move the selected network
to that zone; do not add another tier-derived zone or assign one network twice.
Same-zone rules still require explicit review. [1]

## Network allocations

**SDN VNet ID** below is the attachment ID in the selected SDN variant. `—` means no guest VNet
is required. Existing direct-bridge examples continue using `vmbr0` plus the VLAN
tag until deliberately changed to a prepared VNet. Aliases are suggested labels.

### DMZ zone

| VLAN ID | SDN VNet ID (2–8 chars) | Network label / Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `320` | `edge` | External edge | `10.30.30.0/24` | `10.30.30.1` | `external_edge`: public entry points and ordinary outbound proxy/cache. |
| `321` | `build` | Delivery edge | `10.30.31.0/24` | `10.30.31.1` | `delivery_edge`: external runners; authoritative mirror installation is a separate selection. |
| Site-defined | `—` | Ordinary clients | Site-defined | Site-defined | Separate workstation/WiFi subnet; use Clients zone when policy differs. |

### Services zone

| VLAN ID | SDN VNet ID (2–8 chars) | Network label / Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `11` | `access` | Application access | `10.10.11.0/24` | `10.10.11.1` | Optional front-end network; not the current identity-provider node attachment. |
| `120` | `app` | Application services | `10.20.20.0/24` | `10.20.20.1` | Shared `application` reference; platform cluster and development data services. |
| `130` | `obs` | Observability backends | `10.20.30.0/24` | `10.20.30.1` | Optional VM alternative; normal observability runs in Kubernetes on `app`. |
| `420` | `lab` | Lab environments | `10.42.20.0/24` | `10.42.20.1` | Lab cluster; Linux labs need a tier-local `application` override. Use Lab zone for untrusted experiments. |

### Control zone

| VLAN ID | SDN VNet ID (2–8 chars) | Network label / Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `12` | `ident` | Directory authority | `10.10.12.0/24` | `10.10.12.1` | `identity`: directory primary/replica, DNS and Kerberos. |
| `13` | `control` | Control cluster | `10.10.13.0/24` | `10.10.13.1` | Cluster nodes hosting federation, secrets and control tools. |
| `14` | `admin` | VM administration | `10.10.14.0/24` | `10.10.14.1` | Optional dedicated split for the Linux `management` attachment; not the current starter default. |
| `220` | `crypto` | Cryptographic services | `10.20.21.0/24` | `10.20.21.1` | `cryptography`: issuing CA, optional HSM gateways and standalone secrets variant. |
| `140` | `—` | Backup and archive | `10.20.40.0/24` | `10.20.40.1` | Existing storage endpoints, not the Ceph transport fabric; separate Storage zone if policy differs. |

### Fabric zone

| VLAN ID | SDN VNet ID (2–8 chars) | Network label / Alias | Subnet | Gateway | Comments |
| --- | --- | --- | --- | --- | --- |
| `10` | `—` | Host management | `10.10.10.0/24` | `10.10.10.1` | Existing Proxmox management underlay; starter `management` guests currently share this network. |
| Site-defined | `—` | Out-of-band management | Site-defined | Site-defined or none | IPMI/BMC/controllers; only the approved administrative path. |
| `20` | `—` | Cluster quorum | Site-defined | None | Corosync host interfaces; outside guest SDN. |
| `21` | `—` | Storage clients | Site-defined | None | Ceph client transport; “public” in Ceph does not mean Internet-facing. |
| `22` | `—` | Storage replication | Site-defined | None | Ceph replication transport; outside guest SDN. |

Restrict host/BMC management to approved administrative paths. Keep Corosync/Ceph
transport non-routed where supported by the selected host topology.
Membership is enforced by host interfaces, trunks and switching. A UniFi firewall
zone applies only to traffic traversing its enforcement point; it does not inspect
host-local or non-routed switch traffic. Do not add gateway addresses merely to
populate the zone matrix. See [host networking](../03-deployment/foundation/proxmox/network.md). [3]

Offline custody remains a separate disconnected fabric: reference VLAN `221`,
subnet `10.20.22.0/24`, no connected gateway or guest VNet in this reference.
An optional `telemetry_gateway` network uses VLAN `230` only when its separately
selected intake policy needs it; no default attachment or subnet is supplied.

## Deployment mapping

The following rows describe **current starter inputs**, including direct bridge
attachments and optional variants. Creating a zone or writing a table does not
move a resource. The [network input contract](../08-reference/network-inputs.md) defines overrides
and [SDN lookup](../08-reference/network-inputs.md#sdn-subnet-lookup).

| Deployment / example units | Owning repository and source inputs | Current attachment | Capability guide |
| --- | --- | --- | --- |
| Protected logging: `log-1` | Tier 0 [syslog](../../tier-0/terraform/deployments/syslog/terraform.tfvars.example) | `management` → `vmbr0`, VLAN 10; selected `admin` split requires overrides | [Stage 2](../03-deployment/stage-2-logging/README.md) |
| Infrastructure CI: `iac-1` | Tier 0 [runner](../../tier-0/terraform/deployments/infrastructure-runner/terraform.tfvars.example) | `management` → VLAN 10; same split decision as logging | [Stage 9](../03-deployment/stage-9-development/README.md) |
| Issuer: `ca-1` | Tier 0 [foundation](../../tier-0/terraform/deployments/foundation/terraform.tfvars.example) | `cryptography` → `crypto`, VLAN 220 | [Stage 3](../03-deployment/stage-3-trust/README.md) |
| Directory: `idm-1`, `idm-2` | Tier 0 [foundation](../../tier-0/terraform/deployments/foundation/terraform.tfvars.example) | `identity` → `ident`, VLAN 12 | [Stage 5](../03-deployment/stage-5-identity/README.md) |
| Control cluster; Keycloak, cluster Vault and control tools | Tier 0 [cluster](../../tier-0/terraform/deployments/kubernetes/terraform.tfvars.example) | Nodes → `control`, VLAN 13; no separate `access` node attachment | [Stage 4](../03-deployment/stage-4-kubernetes/README.md), [Stage 6](../03-deployment/stage-6-secrets/README.md) |
| HSM gateways; standalone Vault alternative | Tier 0 [HSM](../../tier-0/terraform/deployments/hsm/terraform.tfvars.example), [Vault](../../tier-0/terraform/deployments/vault/terraform.tfvars.example) | `cryptography` → `crypto`, VLAN 220 | [Trust](../03-deployment/stage-3-trust/README.md), [Secrets](../03-deployment/stage-6-secrets/README.md) |
| Platform cluster; delivery, observability, GitLab and build pods | Tier 1 [cluster](../../tier-1/terraform/deployments/kubernetes/terraform.tfvars.example) | Nodes → `app`, VLAN 120; pods are not automatically DMZ VLAN members | [Stage 7](../03-deployment/stage-7-delivery/README.md), [Stage 8](../03-deployment/stage-8-observability/README.md), [Stage 9](../03-deployment/stage-9-development/README.md) |
| Development data: database, cache and repository storage | Tier 1 [development data](../../tier-1/terraform/deployments/development-data/terraform.tfvars.example) | `application` → `app`, VLAN 120 | [Stage 9](../03-deployment/stage-9-development/README.md) |
| Optional external VM runner: `runner-1` | Tier 1 [Podman runner](../../tier-1/terraform/deployments/podman-runner/terraform.tfvars.example) | `delivery_edge` → `vmbr0`, VLAN 321; `build` is the SDN alternative | [Development platform](../03-deployment/stage-9-development/README.md) |
| Optional VM observability: `otel-*`, `metric-*`, `search-*` | Tier 1 [VM alternative](../../tier-1/terraform/deployments/observability/terraform.tfvars.example) | `observability` → `obs`, VLAN 130; OS baseline, not product installers | [VM option](../03-deployment/stage-8-observability/step-1b-dedicated-vms.md) |
| Ordinary proxy/cache: `cache-1`, `cache-2` | Tier 2 [cache](../../tier-2/terraform/deployments/cache/terraform.tfvars.example) | `external_edge` → `vmbr0`, VLAN 320; `edge` is the SDN alternative | [Stage 1](../03-deployment/stage-1-software-intake/README.md) |
| Edge load balancers: `lb-*` | Tier 2 [edge](../../tier-2/terraform/deployments/edge/terraform.tfvars.example) | `external_edge` → VLAN 320 | [Edge publication](../03-deployment/stage-7-delivery/README.md) |
| Lab cluster | Tier 2 [cluster](../../tier-2/terraform/deployments/kubernetes/terraform.tfvars.example) | Nodes → `vmbr0`, VLAN 420; `lab` is the SDN alternative | [Stage 10](../03-deployment/stage-10-lab-environments/README.md) |
| Linux lab: `lab-1`, `util-1` | Tier 2 [lab](../../tier-2/terraform/deployments/lab/terraform.tfvars.example) | `application` inherits shared VLAN 120 until the lab override is selected | [Lab attachment override](../08-reference/network-inputs.md#guest-attachment) |

## Segmentation

Different ownership does not necessarily require another zone; different access
policy does require an explicit boundary. Keep the following distinctions visible:

- `edge` and `build` remain separate VLANs even in DMZ; public listeners and
  external build jobs receive different endpoint rules.
- `ident`, `control` and `crypto` remain separate VLANs in Control. Consumption
  of OIDC or certificate APIs does not grant directory, cluster or HSM administration.
- The protected log receiver stays under Tier 0 ownership. Observability reads
  approved projections; membership in Services supplies no archive deletion authority.
- Untrusted Linux labs require the `application` override before use; a new VM
  named `lab-1` does not itself create VLAN 420 or isolate it from platform services.
- Same-VLAN peer restrictions need local/VNet or switch enforcement; gateway
  inter-zone rules alone do not cover that traffic. [3]

Use the [firewall contracts](../01-architecture/11-networking/01-firewall-policy.md) for
permitted listeners and denials, the [UniFi guide](../03-deployment/foundation/network/unifi.md)
for gateway policy, and the [SDN guide](../03-deployment/foundation/proxmox/step-1c-sdn.md)
for VNet/subnet preparation. These are manual network prerequisites.

## Separate host and VM administration

The supplied `management` entry currently mixes protected VMs with the host
management subnet. The proposed `admin` / VLAN 14 row is a selectable split,
not an already-deployed network or an automatic migration.

For a new installation, prepare `admin` in Control, then point Tier 0's
`network_zones.management` at it and record matching guest IPs in tier-local group
vars. Keep Proxmox management, BMC interfaces and Corosync/Ceph transport in Fabric,
with separate VLANs and only the required management routes. Update dependent DNS, logging targets and firewall rules with
the selected addresses before running the deployment.

An existing installation needs a planned readdressing cutover, verified recovery
access and rollback. Review every affected deployment plan; changing a zone label
alone does not move guests or separate their interfaces.

## References

1. [UniFi firewall zones, membership and same-zone policies](https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi).
2. [Proxmox SDN zones, VNet IDs and VLAN attachments](https://raw.githubusercontent.com/proxmox/pve-docs/master/pvesdn.adoc).
3. [UniFi gateway, switch and client isolation boundaries](https://help.ui.com/hc/en-us/articles/18965560820247-Implementing-Network-and-Client-Isolation-in-UniFi).
