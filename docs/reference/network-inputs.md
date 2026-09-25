# Network inputs

## Table of contents

- [Prerequisites](#prerequisites)
- [Guest attachment](#guest-attachment)
- [Field reference](#field-reference)
- [Tier-local inputs](#tier-local-inputs)

## Prerequisites

Use the [network plan](../architecture/network.md) to create the required
segments and [firewall policy](../security/firewall-policy.md) first.
Terraform's `network_zones` maps logical guest-network keys to existing
attachments. It does not create firewall zones, gateways, VLAN trunks, or rules.

Host-management IPs, cluster fabric, and storage transport belong in Tier 0
host/network operations. Include a network here only when Terraform should attach a guest
to it, such as a deliberately scoped administration guest.

## Guest attachment

Example Tier 2 values in `terraform/common.tfvars` for the `lab` network
from the [example plan](../architecture/network.md#example-network-plan):

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

Then select the logical network in the owning setup's `terraform.tfvars`:

```hcl
default_platform_node_name = "pve01"

vm_instances = {
  "lab-1" = {
    vm_id            = 500
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

## Field reference

| Field | Meaning |
| --- | --- |
| `default_platform_node_name` | default host for guest placement |
| `vm_instances.<key>` / `lxc_instances.<key>` | stable guest key matching inventory |
| `vm_instances.<key>.tags` | platform tags for filtering and ownership |
| `network_zones.<key>.bridge` | SDN VNet ID or non-SDN Proxmox bridge |
| `network_zones.<key>.vlan_id` | optional VM or LXC NIC VLAN tag for bridge attachment |
| `network_zones.<key>.cidr_ipv4` | network prefix for the guest's static address |
| `network_zones.<key>.gateway_ipv4` | optional in the schema; the static-guest check expects a value; DHCP guests obtain routing from DHCP |
| `vm_instances.*.network_zone_key` | logical network used by a VM |
| `lxc_instances.*.network_zone_key` | logical network used by an LXC guest |

## Tier-local inputs

Keep logical keys such as `application` stable, and select actual subnet and
attachment values from the site plan. An identical key is not automatically
a shared VLAN. Repos may reference the same network when policy permits;
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
In custody, use only an actual custody-local router with no connected-tier
or Internet path. If the design uses static guests without a gateway, resolve
that module check before using the layout; do not invent a gateway or point
custody guests at a connected router to satisfy it. Attachment names and
routing settings alone do not establish physical isolation.

See [Generated repository model](generated-repository-model.md)
for ownership and [Automation layout](infrastructure-automation-layout.md)
for source locations.
