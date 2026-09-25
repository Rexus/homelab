# Proxmox platform

## Table of contents

- [Purpose](#purpose)
- [What this covers](#what-this-covers)
- [Platform guides](#platform-guides)
- [First deployment order](#first-deployment-order)
- [Related references](#related-references)
- [References](#references)

## Purpose

Proxmox is the chosen virtualization platform in this repository.
It provides the cluster, storage, networking, and API surface used by the first
image build, provisioning, and configuration workflows.

Its hardware-facing administration belongs to Tier 0: hosts, storage, network
control, and every VM template lifecycle. Tier 1/2 workload definitions remain
in their own repos; they do not grant their users Proxmox administration.
See [Infrastructure control](../../architecture/infrastructure-control.md).

Use [Private cloud model](../../architecture/private-cloud.md) to understand
where Proxmox fits compared with a later Kubernetes layer or an OpenStack-style
private cloud.

## What this covers

Use the Proxmox platform layer for:

- shared Proxmox planning guidelines such as VM ID ranges and template naming
- API token setup and least-privilege access
- node, bridge, and storage naming conventions
- template creation and refresh
- VM provisioning from Terraform
- host and guest configuration touchpoints from Ansible

## Platform guides

- [Planning guidelines](conventions.md)
- [Tier 0 template lifecycle and CD](template-lifecycle.md)
- [Shared template references](template-catalog.md)
- [Enterprise Linux template](enterprise-linux-template.md)
- [Talos template](talos-template.md)
- [Using the cache from Proxmox](cache-usage.md)
- [Backup foundation](backup-foundation.md)
- [API setup](setup-api.md)
- [Host networking](network-prerequisites.md)
- [Cluster, HA, and Terraform placement](cluster-ha.md)
- [Kubernetes clusters](../kubernetes/README.md)
- [Hardening baseline](hardening.md)

## First deployment order

Run these Tier 0 preparation steps before the first managed guest. A single
host is a valid pilot; cluster membership, HA, and SDN are explicit choices.

| Step | Action and detailed guide | Completion check |
| --- | --- | --- |
| 1. Plan | Record [names, IDs, and tags](conventions.md) in the project worksheet | No conflicting allocations |
| 2. Install hosts | Use the official [Proxmox installer procedure][1] with final node names, addresses, DNS, and time | Protected UI/console access works on every host |
| 3. Prepare networking | Follow [host networking](network-prerequisites.md) and approved gateway/firewall policy | Management, cluster/storage links, and intended guest paths are tested |
| 4. Optional cluster/HA | Follow [cluster and HA](cluster-ha.md), including shared storage and failure-domain planning | Quorum is healthy; guest mobility prerequisites are met |
| 5. Optional SDN | Configure [guest VNets](network-prerequisites.md#optional-sdn-for-guest-networks) on eligible nodes | VNet/bridge IDs and VLAN policy match the tier inputs |
| 6. Protect access and data | Configure [API access](setup-api.md), [backups](backup-foundation.md), and the [hardening baseline](hardening.md) | Scoped credentials, recovery access, and restore checks work |
| 7. Publish templates | Run the [Day 0-1 local workflow](template-lifecycle.md#local-workflow) | Disposable clones boot with the correct disks and networks |
| 8. Deploy guests | Continue with [Kubernetes](../kubernetes/README.md) or [Linux identity VMs](../../paths/shared-services/identity.md) | Chosen service/cluster checks pass; selected HA guests pass failover tests |

The installer writes the selected disks; back up existing contents before
installation. [1] [Cluster joining](cluster-ha.md#prepare-and-join-hosts) also needs
empty/prepared nodes, so decide on the cluster before populating hosts with
templates and important VMs.

Return to the [Tier 0 checklist](../../paths/tier-0/README.md) after preparation.

## Related references

- [Private cloud maturity path](../../paths/private-cloud-maturity.md)
- [Proxmox maturity path](maturity-path.md)
- [Safe repository usage](../../usage-model.md)
- [Secret strategy](../../security/secret-strategy.md)
- [Security principles](../../security/security-principles.md)

## References

1. [Proxmox installation guide](https://github.com/proxmox/pve-docs/blob/master/pve-installation.adoc),
   checked 2026-09-21. Use documentation matching the installed release.

[1]: https://github.com/proxmox/pve-docs/blob/master/pve-installation.adoc
