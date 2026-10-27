# Proxmox foundation

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).

**Design:** [compute foundation](../../../architecture/compute/README.md).

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

Target **Proxmox VE 9+**, with **9.2+** for the selected native dynamic-rebalancing
path. Use current supported 9.x packages and matching installed-release help;
older HA-group or pre-import workflows are not the new-deployment baseline.

Its hardware-facing administration belongs to Tier 0: hosts, storage, network
control, and every VM template lifecycle. Tier 1/2 workload definitions remain
in their own repos; they do not grant their users Proxmox administration.
See [Infrastructure control](../../../architecture/compute/provisioning.md).

Use [Private cloud model](../../../architecture/private-cloud.md) to understand
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

- [Planning guidelines](../../../reference/proxmox-conventions.md)
- [Tier 0 template lifecycle and CD](../../../administration/compute/template-lifecycle.md)
- [Shared template references](../../../reference/template-catalog.md)
- [VM template import: AlmaLinux, Rocky Linux and Talos](templates.md)
- [Using the cache from Proxmox](../../../administration/compute/update-access.md)
- [Backup foundation](../../../administration/compute/backup-restore.md)
- [API setup](api-access.md)
- [Host networking](network.md)
- [Cluster, HA, and Terraform placement](../step-1b-cluster-ha.md)
- [HA menu and recommended starting values](../../../reference/proxmox-ha.md)
- [Worked host failure and recovery](failover.md)
- [Kubernetes clusters](../../stage-4-kubernetes/procedures/kubernetes.md)
- [Hardening baseline](../../../administration/compute/hardening.md)

## First deployment order

Run these Tier 0 preparation steps before the first managed guest. A single
host is a valid pilot; cluster membership, HA, and SDN are explicit choices.

| Step | Action and detailed guide | Completion check |
| --- | --- | --- |
| 1. Plan | Record [names, IDs, and tags](../../../reference/proxmox-conventions.md) in the project worksheet | No conflicting allocations |
| 2. Install hosts | Use the official [Proxmox installer procedure][1] with final node names, addresses, DNS, and time | Protected UI/console access works on every host |
| 3. Prepare networking | Follow [host networking](network.md) and approved gateway/firewall policy | Management, cluster/storage links, and intended guest paths are tested |
| 4. Optional cluster/HA | Follow [cluster and HA](../step-1b-cluster-ha.md), including shared storage and failure-domain planning | Quorum is healthy; guest mobility prerequisites are met |
| 5. Optional SDN | Configure [guest VNets](network.md#optional-sdn-for-guest-networks) on eligible nodes | VNet/bridge IDs and VLAN policy match the tier inputs |
| 6. Protect access and data | Configure [API access](api-access.md), [backups](../../../administration/compute/backup-restore.md), and the [hardening baseline](../../../administration/compute/hardening.md) | Scoped credentials, recovery access, and restore checks work |
| 7. Publish templates | Run the [local template workflow](../../../administration/compute/template-lifecycle.md#local-workflow) | Disposable clones boot with the correct disks and networks |
| 8. Start capabilities | Accept [Stage 1: Software intake](../../stage-1-software-intake/README.md), then begin [Stage 2: Protected logging](../../stage-2-logging/README.md) | Approved supply and protected collection work before trust, clusters and identity |

The installer writes the selected disks; back up existing contents before
installation. [1] [Cluster joining](../step-1b-cluster-ha.md#prepare-and-join-hosts) also needs
empty/prepared nodes, so decide on the cluster before populating hosts with
templates and important VMs.

Return to the [Tier 0 checklist](../../../paths/tier-0/README.md) after preparation.

## Related references

- [Deployment readiness](../../readiness.md)
- [Safe repository usage](../../../development/repository-workflow.md)
- [Secret strategy](../../../administration/secret-handling/strategy.md)
- [Security principles](../../../architecture/principles.md)

## References

1. [Proxmox installation guide](https://github.com/proxmox/pve-docs/blob/master/pve-installation.adoc),
   checked 2026-09-21. Use documentation matching the installed release.

[1]: https://github.com/proxmox/pve-docs/blob/master/pve-installation.adoc
