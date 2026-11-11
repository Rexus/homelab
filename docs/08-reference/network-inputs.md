# Network inputs

## Table of contents

- [Prerequisites](#prerequisites)
- [Guest attachment](#guest-attachment)
- [Guest NIC firewall](#guest-nic-firewall)
- [SDN subnet lookup](#sdn-subnet-lookup)
- [Field reference](#field-reference)
- [Shared references and tier overrides](#shared-references-and-tier-overrides)
- [References](#references)

## Prerequisites

Use the [network plan](../01-architecture/11-networking/README.md) to create the required
segments and [firewall policy](../01-architecture/11-networking/01-firewall-policy.md) first.
The [allocation and deployment map](../02-conventions/network-plan.md) connects each zone/VNet to
the current source inputs and identifies optional network splits.
Terraform combines `shared_network_zones` and tier-local `network_zones` to map logical guest-network keys to existing
attachments. It does not create firewall zones, gateways, VLAN trunks, or rules.

Host-management IPs, cluster fabric, and storage transport belong in Tier 0
host/network operations. Include a network here only when Terraform should attach a guest
to it, such as a deliberately scoped administration guest.

## Guest attachment

The common `application` attachment is defined once in shared `config/platform.tfvars`.
Example Tier 2 override in `terraform/common.tfvars` for the `lab` network
from the [example plan](../01-architecture/11-networking/README.md#example-network-plan):

```hcl
network_zones = {
  application = {
    bridge       = "vmbr0"
    vlan_id      = 420
    cidr_ipv4    = "10.42.20.0/24"
    gateway_ipv4 = "10.42.20.1"
  }
}
```

On the gateway, assign the subnet to `Services` or a separate `Lab` zone when
its policy differs. The firewall-zone
name is not a Terraform field. With Proxmox SDN, use the short VNet ID as
`bridge` and omit `vlan_id` when tagging is handled by the VNet.
The [SDN field guide](../03-deployment/foundation/proxmox/step-1c-sdn.md) maps these keys to
zone IDs, VNet IDs, VLAN tags and gateway firewall zones. An SDN zone's DNS fields
manage DNS records through an API integration; guest resolver settings are separate.

Then select the logical network in the owning setup's `terraform.tfvars`:

```hcl
default_platform_node_name = "pve01"

vm_instances = {
  "lab-1" = {
    vm_id            = 3201
    size             = "small"
    storage_class    = "local"
    disk_size_gb     = 30
    network_zone_key = "application"
    tags             = ["lab"]
  }
}
```

Set the matching guest IP in that tier's Ansible group vars. The shared
inventory mechanism supplies it to both Terraform and Ansible; do not
maintain a second address list in VM placement variables.

## Guest NIC firewall

Tier-owned Linux VM, Kubernetes node and LXC resources explicitly set the Proxmox
interface's `firewall = true`. A clone's declared NIC must set this itself; an
omitted field uses the provider's `false` default rather than preserving template
policy. [3][4] Template publication separately defaults `nic_firewall` to `true`;
an explicit `false` in `templates/proxmox.yml` overrides that default.

This flag participates in Proxmox guest filtering; it does not enable the
Datacenter/guest firewall, install rules, configure the guest OS firewall or replace
gateway policy. Review those separate controls with the
[firewall rollout checks](../03-deployment/foundation/network/firewall.md#proxmox-guest-interfaces).
When upgrading existing guests, review the NIC change and accepted allow rules
before applying it. SDN attachment does not remove this requirement.

## SDN subnet lookup

Use an existing Proxmox SDN subnet as the prefix/gateway source instead of
repeating those values in IaC. This is optional; explicit network entries remain valid.

1. Under the selected **VNet > Subnets**, record its IPv4 CIDR and existing
   gateway, then **Apply** SDN. Keep UniFi as router/DHCP/DNS provider on the VLAN
   path; do not enable Proxmox DHCP or SNAT just to use this lookup.
2. Grant the execution token `SDN.Audit` on that VNet, in addition to its existing
   attachment permissions; see [API access](../03-deployment/foundation/proxmox/api-access.md#6-grant-bridge-vlan-or-sdn-use-to-the-group).
3. Replace the selected Linux network entry with the following form. Use Shared's
   `config/platform.tfvars` / `shared_network_zones` for a shared network, or the
   owning tier's `terraform/common.tfvars` / `network_zones` for a private one:

```hcl
network_zones = {
  identity = {
    bridge     = "ident"
    sdn_lookup = true
  }
}
```

Preserve other entries in the map. Omit `vlan_id`, `cidr_ipv4` and `gateway_ipv4`
from a lookup entry. Guest IPs remain in tier-local inventory inputs; each guest
still selects its logical network. Plan with the normal deployment command.

Kubernetes uses its separate input contract in the **selected tier's**
`terraform/deployments/kubernetes/terraform.tfvars`:

```hcl
bootstrap_network = {
  sdn_vnet = "control"
}
```

All nodes must attach to that VNet with no NIC VLAN tag. Omit explicit
`prefix_length` and `gateway`; optional `dns_servers` remains independently configured.
`bootstrap_network = null` retains the existing DHCP path.

The tier-owned [Linux resolver](../../tier-0/terraform/modules/environment_guests/networks.tf)
and [Kubernetes root](../../tier-0/terraform/deployments/kubernetes/networks.tf) use
Shared's stateless [lookup helper](../../shared/scripts/proxmox-sdn.py) through
Terraform's external data source. Python 3 needs no additional packages. Authentication
uses the normal environment-only `TF_VAR_proxmox_api_*`, `PROXMOX_VE_*` or
`PROXMOX_API_*` token/endpoint settings. Conflicting settings are rejected;
TLS uses the execution host's trusted CA store or `SSL_CERT_FILE`/`SSL_CERT_DIR`.
For Linux deployments, `deploy.sh` loads the consuming tier's `.env.local`; it does
not inherit Tier 0's file. Check that file's endpoint and trust overrides when a
manual connection to another endpoint succeeds.
The helper reads applied subnet metadata with GET only; it does not reserve addresses,
change networks, create DNS records or configure a DHCP server. [1][2]

Exactly one applied IPv4 subnet with a usable gateway is required per selected
VNet. Missing, ambiguous or unreadable metadata fails the plan; explicit values
are not a silent fallback. Inventory IPs outside that subnet, its network/broadcast
addresses and the gateway itself are rejected. Linux deployments query only their
selected networks. A plan stores the resolved values, not API credentials from the lookup.

| Lookup error | Check |
| --- | --- |
| Certificate verification failed | Approved execution-host CA, certificate dates and endpoint hostname/SAN |
| Cannot resolve API hostname | Effective tier-local API URL and execution-host DNS |
| Connection timed out / refused | Effective endpoint port, routing/firewall policy and Proxmox API service |
| HTTP 403 | Token's effective `SDN.Audit` grant on the selected VNet |

An HTTPS connection test must use the same URL and trust environment as the deployment.
Keep TLS verification enabled while correcting endpoint, trust or connectivity settings.

Keep the SDN/network backup with recovery records. Changing the subnet can change
guest network configuration: review the plan. If SDN cannot be recovered yet,
deliberately restore an explicit network entry from the approved record.

## Field reference

Entries in both network maps use the same fields below. The tier-local entry
replaces the complete shared entry with the same key; other shared entries remain available.

| Field | Meaning |
| --- | --- |
| `default_platform_node_name` | default host for guest placement |
| `vm_instances.<key>` / `lxc_instances.<key>` | stable guest key matching inventory |
| `vm_instances.<key>.tags` | platform tags for filtering and ownership |
| `network_zones.<key>.bridge` | SDN VNet ID or non-SDN Proxmox bridge |
| `network_zones.<key>.vlan_id` | optional VM or LXC NIC VLAN tag for bridge attachment |
| `network_zones.<key>.cidr_ipv4` | IPv4 prefix for explicit networks; omitted with SDN lookup |
| `network_zones.<key>.gateway_ipv4` | gateway for explicit static networks; omitted with SDN lookup; DHCP guests obtain routing from DHCP |
| `network_zones.<key>.sdn_lookup` | default `false`; read the selected VNet's applied IPv4 subnet and gateway |
| `vm_instances.*.network_zone_key` | logical network used by a VM |
| `lxc_instances.*.network_zone_key` | logical network used by an LXC guest |

<a id="tier-local-inputs"></a>

## Shared references and tier overrides

Keep logical keys such as `application` stable, and select actual subnet and
attachment values from the site plan. Put an attachment used across tiers in
shared `shared_network_zones`; keep networks used by only one tier in that tier's
`network_zones`. Guest selections and individual IP addresses always remain tier-local.
An identical key is not automatically a shared VLAN when a tier overrides it.
Repos may reference the same network when policy permits;
separate subnets wherever trust or access requirements differ.
Document each network's operational owner and zone in the network inventory.

Generated examples retain upstream reference addresses. Review all bridge,
VLAN, CIDR, gateway, and inventory IP values before applying them. Tier 0
control systems may use connected protected networks. Only assets designated
for offline custody use the separately isolated fabric.

VMs and LXC guests consume the same bridge and VLAN selection. When upgrading
an existing LXC deployment, review its plan: earlier modules ignored `vlan_id`.
Applying a newly honored tag can change connectivity; verify trunk and firewall
configuration before applying it. Omit the tag when the SDN VNet owns tagging.

The current `environment_guests` static-guest check expects `gateway_ipv4`.
An enabled SDN lookup supplies that value from the applied subnet.
In custody, use only an actual custody-local router with no connected-tier
or Internet path. If the design uses static guests without a gateway, resolve
that module check before using the layout; do not invent a gateway or point
custody guests at a connected router to satisfy it. Attachment names and
routing settings alone do not establish physical isolation.

See [Generated repository model](../04-development/generated-repositories.md)
for ownership and [Automation layout](../04-development/code-layout.md)
for source locations.

## References

1. [Terraform external data source and execution environment](https://registry.terraform.io/providers/hashicorp/external/latest/docs/data-sources/external).
2. [Proxmox subnet reads, running configuration and scoped permissions](https://raw.githubusercontent.com/proxmox/pve-network/master/src/PVE/API2/Network/SDN/Subnets.pm).
3. [Pinned VM provider NIC settings](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/resources/virtual_environment_vm.md#argument-reference).
4. [Pinned container provider NIC settings](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/resources/virtual_environment_container.md#argument-reference).
