# Proxmox foundation

Install the virtualization hosts and prepare the network/storage that guest IaC consumes.
Proxmox host administration and every template lifecycle belong to Tier 0.

**Working repository:** `<prefix>-tier-0` after generation (source: `tier-0/`).
**Run on:** an independent workstation and each host's console/GUI.
**Target:** Proxmox VE 9+; the native dynamic-rebalancing branch requires 9.2+.
**Design:** [compute foundation](../../../01-architecture/04-hosting/README.md).

## Contents

- [First deployment order](#first-deployment-order)
- [Platform guides](#platform-guides)
- [References](#references)

<a id="purpose"></a>
<a id="what-this-covers"></a>

## First deployment order

### Step 1: Record host values

Record these in the project platform standards, or a temporary protected record before
the [bootstrap host](../bootstrap/README.md) generates that worksheet.

| Item | Record before installation |
| --- | --- |
| Host | Final short name/FQDN, management IP/CIDR, gateway, DNS and time sources |
| Disks | Boot targets, live guest storage and independent backup destination |
| Network | Physical NICs, switch ports, management VLAN and permitted guest VLANs |
| Recovery | Console/BMC path and verified installation sources |

Use the [Proxmox conventions](../../../02-conventions/proxmox-conventions.md) and
[network plan](../../../02-conventions/network-plan.md); replace example allocations with actual choices.

<a id="step-2-install-and-verify-each-host"></a>

### Step 2: Install each host

1. Boot the approved Proxmox installer and select only the intended boot disks.
   **Installation removes existing contents on those disks.** Preserve required data first. [1]
2. Enter the final hostname, management address, gateway and independent DNS.
3. Complete installation. From the workstation, open `https://<host-name>:8006/`;
   verify the host/certificate through the console before accepting initial browser trust.
**Expected:** each installed host is reachable independently. An accepted existing host needs
the checks below, not another installation.

### Step 3: Verify management, DNS and time

Check console/UI access, DNS and time on every host. Stop on failed access or incorrect host identity
before configuring a cluster or changing uplinks.

### Step 4: Prepare host networking

Follow [host networking: initial trunk](network.md#step-1-prepare-the-guest-trunk) for the
`vmbr0`/VLAN path and any selected bond/storage-fabric alternatives. Keep console access during
activation. Return here at Step 5; the network guide does not require a guest before the first template.

<a id="step-3-select-optional-branches-before-adding-guests"></a>

### Step 5: Select optional branches before adding guests

| Branch | Complete now | Return |
| --- | --- | --- |
| Single-host pilot | No cluster required; retain the selected host/storage inputs | Step 6 below |
| 1b: Cluster and HA | [Join empty hosts](step-1b-cluster-ha.md#prepare-and-join-hosts), check mobility prerequisites; enroll/test disposable HA guests later | Step 6 below |
| 1c: Guest SDN | [Create and activate VNets, Steps 1–3](step-1c-sdn.md); this can accompany either host option | Step 6 below |

Joining a cluster replaces the joining node's configuration; decide before populating
it with templates/VMs. HA needs usable shared/replicated storage, fencing, capacity and
explicit resource enrollment; membership alone is insufficient.

<a id="step-4-return-to-the-foundation-path"></a>

### Step 6: Return to the foundation path

The selected cluster/SDN guide returns here to finish any other selected host option once.
Then return to [Foundation Step 1](../README.md#step-1-prepare-hosts-and-networks), actions **3–4**,
for storage and firewall checks. Continue through that README's manual-template, bootstrap and
managed-publication steps in order; do not skip directly to Stage 1 from host preparation.
API tokens and Terraform follow creation of the first manual template and bootstrap host.

## Platform guides

| Task | Guide |
| --- | --- |
| Host attachments, bonds and storage fabric | [Host networking](network.md) |
| Scoped credentials and trust | [API setup](api-access.md) |
| Initialize local files and manage installed hosts over SSH | [Bootstrap host-management setup](../../../05-operations/01-hosting/README.md) |
| Import a verified image in the GUI | [VM templates](templates.md) |
| Publish/adopt and maintain templates | [Template lifecycle](../../../05-operations/01-hosting/templates/template-lifecycle.md) |
| HA controls and fault behavior | [Menu reference](../../../08-reference/proxmox-ha.md), [worked failover](failover.md) |
| ProxLB instead of native rebalancing | [Alternative balancer](step-10b-proxlb.md) |
| Restore a disposable guest | [Backup/restore](../../../05-operations/06-resilience/backups/virtual-machines.md) |
| Apply the Linux service-VM profile after guest deployment | [Stage 1, option 8b](../../stage-1-software-intake/README.md#8b-apply-the-linux-security-profile--optional) |

<a id="related-references"></a>

For broader context, see the [private-cloud model](../../../01-architecture/01-background/README.md)
and [Tier 0 checklist](../../../06-paths/tier-0/README.md).

## References

1. [Proxmox installation guide](https://raw.githubusercontent.com/proxmox/pve-docs/master/pve-installation.adoc).
   Use documentation matching the installed release.
