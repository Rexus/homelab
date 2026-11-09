# Step 1c: SDN guest networks

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Execution:** Proxmox GUI and the existing switch/gateway configuration; this is a manual prerequisite.
Consuming tiers own their guest-network inputs.

**Branch from:** [host/network preparation](README.md#before-starting-hosts-and-networks), before attaching guests.
**Change:** use VLAN-backed SDN VNets instead of direct bridge/VLAN guest attachments.
**Return:** [foundation prerequisites](README.md#before-starting-hosts-and-networks)
after activation; finish storage/firewall checks before creating the first template.
API authorization and local inputs follow on the bootstrap host.
**Design:** [network placement](../../architecture/networking/README.md).

## Contents

- [Before starting](#before-starting)
- [Step 1: Create the VLAN zones](#step-1-create-the-vlan-zones)
- [Step 2: Create the VNets](#step-2-create-the-vnets)
- [Step 3: Activate SDN on the nodes](#step-3-activate-sdn-on-the-nodes)
- [Step 4: Authorize and connect IaC](#step-4-authorize-and-connect-iac)
- [DNS with an existing gateway](#dns-with-an-existing-gateway)
- [Return to the main path](#return-to-the-main-path)
- [References](#references)

## Before starting

Create the VLANs, gateway interfaces and firewall policy on the existing network first.
The example uses a UniFi gateway for routing, DHCP and DNS, and a VLAN-aware `vmbr0`
trunk on each eligible Proxmox node. SDN creates guest attachments; it does not
create the gateway's networks or firewall rules. [1]

Keep host-management, Corosync and Ceph transport outside this guest SDN setup.
Test on a non-critical guest VLAN before changing existing attachments. For HA,
the bridge, trunks and VNets must work on
[every eligible destination](step-1b-cluster-ha.md#make-guests-movable).

Record selected IDs and VLAN conventions under **Networks and VLANs** in the
architecture repository's `platform-standards.md`. This worksheet is project-owned;
existing projects update it manually. The values below are reference choices.

## Step 1: Create the VLAN zones

Create three VLAN zones: `dmz`, `services` and `control`, matching the UniFi
**DMZ**, **Services** and **Control** groups. Proxmox zones group VNets for
deployment and permissions; UniFi zones group networks for gateway firewall policy.
The matching names are a convention, with no automatic configuration sync. [1][8]

Open **Datacenter > SDN > Zones > Add > VLAN**. Create `services` first, then
repeat for `dmz` and `control` with the same settings:

| Field | Enter | Meaning |
| --- | --- | --- |
| ID | `services` | SDN group corresponding to the UniFi Services group; use `dmz` and `control` for the other two |
| Bridge | `vmbr0` | Existing trunk bridge on every selected node |
| MTU | Leave blank / `auto` | Use the reference 1500-MTU guest fabric; override only to match an explicit end-to-end MTU plan |
| Nodes | Leave `All (No restrictions)` when all nodes qualify | Otherwise select only prepared nodes, consistent with VM placement and HA rules |
| IPAM | Keep `pve` | Built-in IPAM; this alone does not enable a DHCP server or replace tier-owned inventory |
| DNS Server | Leave blank | Optional DNS record-management integration, not a guest resolver address |
| Reverse DNS Server | Leave blank | Optional reverse-record management integration |
| DNS Zone | Leave blank | Existing authoritative domain for managed records, used only with that integration |

Use 2–8 alphanumeric characters starting with a letter for zone IDs; lowercase
is the project convention. Each zone can contain several VNets. [1][2][3]

All three can use the same VLAN-aware `vmbr0` trunk. Keep each bridge/VLAN
combination in exactly one VNet across these zones: a different zone name does
not isolate a duplicate VLAN on the same trunk. VLAN tags provide the network
separation; UniFi rules control routed access. [1][9]

A single `guests` zone is also valid when separate SDN deployment/permission
groups are unnecessary. It still requires the same VLAN and firewall configuration.
Add a separate `lab` zone only when the selected network policy needs that group;
do not create zones merely because resources belong to different tiers.

## Step 2: Create the VNets

Open **Datacenter > SDN > VNets > Create**. Repeat for each required guest VLAN:

| Field | Application-network example | Meaning |
| --- | --- | --- |
| Name (SDN VNet ID) | `app` | 2–8 letters/digits, starting with a letter; no hyphens/underscores; project IDs use lowercase |
| Alias | `Application services` | Human-readable description; not the Terraform bridge value |
| Zone | `services` | The matching SDN group created above |
| Tag | `120` | Actual VLAN ID configured on the gateway and switch trunk |
| VLAN Aware | Unchecked | The VNet already selects one VLAN; guests attach without another NIC tag |
| Isolate Ports | Unchecked | Blocks direct traffic between isolated guest ports on the same host; required cluster/replica peer traffic must remain possible |

**Isolate Ports is host-local:** it does not isolate guests on different Proxmox
nodes. Use guest/VNet firewall policy for the required peer restrictions across
nodes; gateway rules alone do not filter traffic switched within one VLAN.
Enable port isolation only for a selected guest network whose peer traffic should
be blocked. Restart affected guests for the setting to take effect. [1]

Use the [zone/VNet network plan](../../conventions/network-plan.md#network-allocations)
for the per-zone **VLAN ID, Name, Alias, Subnet and Gateway** values. Its
[deployment mapping](../../conventions/network-plan.md#deployment-mapping) identifies
which current inputs use SDN and which still use direct bridge/VLAN attachments.
Create only the selected networks; optional reference entries are not existing deployments. [4]

Fabric groups hardware/host networks on UniFi. Host management,
Corosync and Ceph interfaces stay on the underlay and need no guest SDN zones.
A UniFi Fabric zone does not enable Proxmox SDN Fabrics.

The SDN zone ID, VNet ID, VLAN number, logical IaC key and firewall zone are
different fields. Keep their mapping in the project network record. Host-management
VLAN 10 stays on its existing underlay attachment.
Gateway rules govern routed traffic between VLANs. Peer traffic within one VNet
needs its own approved guest-firewall or isolation policy.

Choose **2a or 2b**, then continue at **Step 3**:

### 2a: Keep subnet values in IaC

Leave the VNet's subnet list empty when no Proxmox IPAM/subnet lookup is needed.
Record CIDR/gateway in the tier's network inputs instead.

### 2b: Record a subnet for IaC lookup

Open the selected VNet's **Subnets > Create** dialog. For the `ident` example:

| Field | Enter |
| --- | --- |
| Subnet | `10.10.12.0/24`, the existing gateway subnet |
| Gateway | `10.10.12.1`, the existing UniFi interface |
| SNAT | Unchecked |
| DNS Zone Prefix | Blank without an explicit DNS record-management integration |
| DHCP ranges / DHCP configuration | Leave unconfigured; retain the existing gateway DHCP service |

This records metadata; it does not select Proxmox routing/DHCP. [1] Use the actual
values from the [network plan](../../conventions/network-plan.md), not the identity
example for every VNet. Keep static guest addresses outside dynamic pools.
Continue at **Step 3**; [lookup](../../reference/network-inputs.md#sdn-subnet-lookup)
reads only applied subnet configuration.

<a id="step-3-apply-and-connect-iac"></a>

## Step 3: Activate SDN on the nodes

**Creating zones, VNets and subnets only saves pending configuration.** Activate it
in Proxmox before attaching templates or guests. The template publisher's Terraform
`apply` does not apply SDN configuration. [1]

1. Return to **Datacenter > SDN**, the main overview rather than **Zones** or **VNets**.
   Review the pending changes; this action applies the pending SDN configuration cluster-wide.
2. Click **Apply** and wait for the resulting task to finish successfully on all eligible nodes.
   Resolve any failed node before attaching guests or allowing HA placement there.
3. Check that the selected VNet bridges now exist on the eligible nodes and that
   their VLANs match the prepared switch trunks. Listing a VNet in the datacenter
   configuration alone is not evidence that it is active on a host.

**First installation, before the bootstrap host/token exists:** return now to
[foundation prerequisites](README.md#before-starting-hosts-and-networks), then the manual template and bootstrap host.
Complete Step 4 below when configuring API access and local inputs on that host.

## Step 4: Authorize and connect IaC

1. Grant automation [SDN use](proxmox/api-access.md#6-grant-bridge-vlan-or-sdn-use-to-the-group)
   on each selected VNet. A `vmbr0` grant does not carry over to an SDN VNet;
   privilege-separated tokens also need matching token ACLs.
2. Test a disposable guest's address, gateway, DNS and permitted connectivity.
3. Update the owning repository's attachment values before provisioning normal guests.

**Edit existing entries**, not a second map assignment. For explicit settings,
replace the `identity` entry inside **Tier 0's `terraform/common.tfvars` → `network_zones`**:

```hcl
identity = {
  bridge       = "ident"
  vlan_id      = null
  cidr_ipv4    = "10.10.12.0/24"
  gateway_ipv4 = "10.10.12.1"
}
```

For the **2b lookup** path, replace that same entry with:

```hcl
identity = {
  bridge     = "ident"
  sdn_lookup = true
}
```

Preserve the other `network_zones` entries. Require both `SDN.Use` and `SDN.Audit`
for the actual consuming token. The [lookup contract](../../reference/network-inputs.md#sdn-subnet-lookup)
also covers Kubernetes bootstrap. Review the resolved plan before changing existing guests.

The shared `application` attachment lives in **Shared's** `config/platform.tfvars`
under `shared_network_zones`. Tier-only attachments and complete overrides remain
tier-local. Kubernetes roots use their own machine attachment inputs in
`terraform/deployments/kubernetes/`; they do not load Linux `common.tfvars`.
Use the selected VNet as `bridge` and omit/null the guest's `vlan_id` in either path.

For templates, edit the existing `all:` section in **Tier 0's `templates/proxmox.yml`**;
preserve its other fields. For example, a selected `ident` VNet attachment is:

```yaml
bridge: ident
vlan_id: null
```

These two fields belong **under `all:`**, or under one selected build for an override.
Then follow [Foundation Step 3](README.md#step-3-publish-and-test-vm-templates).
The VNet permission applies to the publishing token too. Existing clones keep
their own NIC settings; changing the template does not move them.

See [network input ownership and overrides](../../reference/network-inputs.md).

## DNS with an existing gateway

The zone's DNS fields let Proxmox create/remove hostname and reverse-DNS records
through a supported DNS API integration. They are useful when IPAM and DNS record
lifecycles are deliberately automated together. A gateway listening on port 53 is
a resolver endpoint, not that management integration. Leave these fields blank
when retaining gateway-managed DNS records. [1][3]

For the UniFi reference path:

- **DHCP guests:** UniFi advertises the gateway address as DNS by default, unless
  the network's DHCP DNS setting overrides it. [5]
- **Static CloudInit guests:** configure or qualify their resolver separately.
  Unset CloudInit DNS settings inherit the Proxmox host's DNS, which may be another
  VLAN's gateway. `gateway_ipv4` does not set guest DNS. [6]
- **Kubernetes bootstrap:** use the selected root's optional
  `bootstrap_network.dns_servers` when an explicit gateway resolver is needed;
  see [platform inputs](../../reference/platform-inputs.md).
- **Local names for static guests:** create the required records on the gateway;
  an SDN VNet name alone does not create host or service DNS records. [7]

Keep bootstrap DNS independent of later services. When adding directory DNS, follow
the [identity DNS prerequisites](../stage-5-identity/procedures/freeipa.md)
so the selected resolver can resolve that domain as well.

## Return to the main path

After **Datacenter > SDN > Apply** succeeds and the VNet checks pass, return to
[foundation prerequisites](README.md#before-starting-hosts-and-networks) for storage/firewall acceptance
before creating the first template.
Complete Step 4 above when the bootstrap host/API token exists. If templates are
already managed, return directly to [Foundation Step 3](README.md#step-3-publish-and-test-vm-templates)
to review their attachment change. Changing SDN configuration alone does not update guest NICs.

## References

Sources checked 2026-11-07.

1. [Proxmox SDN concepts, VLAN zones, IPAM and DNS integrations](https://raw.githubusercontent.com/proxmox/pve-docs/master/pvesdn.adoc).
2. [Proxmox SDN zone ID validation](https://raw.githubusercontent.com/proxmox/pve-network/master/src/PVE/Network/SDN/Zones/Plugin.pm).
3. [Proxmox VLAN-zone dialog fields](https://raw.githubusercontent.com/proxmox/pve-manager/master/www/manager6/sdn/zones/Base.js).
4. [Proxmox VNet IDs, tags and options](https://raw.githubusercontent.com/proxmox/pve-network/master/src/PVE/Network/SDN/VnetPlugin.pm).
5. [UniFi DHCP gateway and DNS defaults](https://help.ui.com/hc/en-us/articles/360012097513-UniFi-DHCP-Server).
6. [Proxmox CloudInit DNS inheritance](https://raw.githubusercontent.com/proxmox/qemu-server/master/src/PVE/QemuServer/Cloudinit.pm).
7. [UniFi DNS records and local hostnames](https://help.ui.com/hc/en-us/articles/15179064940439-UniFi-DNS-Records-and-Local-Hostnames).
8. [UniFi firewall zones, network membership and policy](https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi).
9. [Proxmox VLAN-zone bridge and tagged VNet implementation](https://raw.githubusercontent.com/proxmox/pve-network/master/src/PVE/Network/SDN/Zones/VlanPlugin.pm).
