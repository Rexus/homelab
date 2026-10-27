# Step 1c: SDN guest networks

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
Consuming tiers keep their own guest-network inputs.

**Branch from:** [Step 1](README.md#step-1-prepare-compute-and-templates), before attaching guests.
**Change:** use SDN VNets instead of direct bridge/VLAN guest attachments.
**Design:** [network placement](../../architecture/networking/README.md).

## Deployment

Use SDN as a foundation option for VM-facing networks. This repository
only needs the final VM attachment name.

Choose this during [early host preparation](proxmox/README.md#first-deployment-order),
before publishing templates and attaching guests. For a cluster, validate the
underlay and resulting VNets on **every eligible migration/HA destination**;
see [cluster readiness](step-1b-cluster-ha.md#make-guests-movable).

Short guardrails:

- use SDN for guest/workload networks such as `identity`, `application`,
  `external_edge`, `cryptography`, labs, and tenant networks
- do not move host-management, Corosync, `ceph_public`, `ceph_cluster`, or
  other Proxmox/Ceph transport networks into SDN
- keep `bond0`/`vmbr0` and optional `bond1`/`vmbr1` as the stable underlay
- test SDN on a non-critical guest network before using it broadly
- stage bridge, LACP, VLAN, and SDN changes instead of changing everything at
  once

Use the current
[Proxmox SDN documentation](https://pve.proxmox.com/pve-docs/chapter-pvesdn.html)
for exact UI fields. For this repo, a VLAN-backed SDN setup usually looks like:

1. Confirm the underlay bridge, usually `vmbr0`, is VLAN-aware and trunked on
   the switch.
2. In Proxmox, open `Datacenter` -> `SDN` -> `Zones` and create a VLAN zone.
   Use a short zone ID and point it at the underlay bridge, such as `vmbr0`.
3. Open `Datacenter` -> `SDN` -> `VNets` and create one VNet per guest
   network. Keep VNet IDs short, ideally eight characters or fewer, such as
   `app`, `ident`, `crypto`, `edge`, or `tenant1`.
4. Set the VNet VLAN tag to the real VLAN carried by the underlay trunk. Use
   the Proxmox Alias or description fields for longer human-readable names.
5. Apply the SDN configuration from the main SDN panel and verify that the VNet
   exists on every intended creation and failover node before attaching guests.
6. Skip Proxmox SDN subnets unless using Proxmox IPAM, DHCP, or
   routed SDN features. This repo still provides static guest IPs through
   Terraform cloud-init values in `network_zones`.

Map the result into `terraform/common.tfvars`:

```hcl
network_zones = {
  application = {
    bridge       = "app" # SDN VNet ID
    cidr_ipv4    = "10.20.20.0/24"
    gateway_ipv4 = "10.20.20.1"
  }

  external_edge = {
    bridge       = "vmbr0" # non-SDN bridge
    vlan_id      = 320     # VM NIC is tagged
    cidr_ipv4    = "10.30.30.0/24"
    gateway_ipv4 = "10.30.30.1"
  }
}
```

## Return to the main path

Verify the VNet on every eligible node, then return to
[Step 1](README.md#step-1-prepare-compute-and-templates) for API access and templates.
This branch does not move host-management, Corosync or Ceph transport into SDN.
