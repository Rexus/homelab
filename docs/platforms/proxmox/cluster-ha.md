# Proxmox cluster and HA

Optional early Tier 0 setup, **before templates and important guests**. A single
host is valid for a pilot. A cluster adds shared administration; HA must be
configured separately for selected guests. Neither replaces backups.

## Table of contents

- [Prepare and join hosts](#prepare-and-join-hosts)
- [Make guests movable](#make-guests-movable)
- [Enable HA](#enable-ha)
- [Terraform against the cluster](#terraform-against-the-cluster)
- [Prove failover](#prove-failover)
- [References](#references)

## Prepare and join hosts

Start with [host installation and preparation](README.md#first-deployment-order).

| Step | Action | Ready when |
| --- | --- | --- |
| 1. Plan | Choose final node names/IPs, Corosync links, and host capacity | Choices recorded in project docs |
| 2. Install | Use compatible Proxmox releases; configure DNS/time and protected access | Every node works independently |
| 3. Network | Follow [host networking](network-prerequisites.md); separate latency-sensitive Corosync from busy storage/migration traffic | Links tested before joining |
| 4. Create | On the first node, use **Datacenter > Cluster > Create Cluster** and select the intended Corosync links | First node reports quorum |
| 5. Join | Copy **Join Information**; use **Join Cluster** on each empty additional node | All intended nodes are members |

Joining replaces the node's cluster configuration. Do not join a host containing
guests without a reviewed backup/migration plan. Prefer three hosts for reliable
quorum; a two-host design needs a separately reviewed external QDevice and
failure model. Never lower expected votes to disguise a production partition. [1]

On a Proxmox host, verify membership:

```bash
pvecm status
pvecm nodes
```

## Make guests movable

| Requirement | Check before enabling HA |
| --- | --- |
| Storage | All eligible hosts can access every guest disk, including cloud-init, EFI, TPM, and attached media |
| Network | Identical bridge/VNet names and effective VLAN/MTU policy on eligible nodes |
| CPU | Guest CPU model supported across the destination hosts; this kit's Linux VM module uses `x86-64-v3` |
| Devices | No unreviewed local passthrough, local ISO, or host-specific device dependency |
| Capacity | Surviving hosts can carry the required guests after a host failure |

Use resilient shared storage for the straightforward HA path. The name `shared`
in this repo is only a storage mapping: it does not build shared storage.
Local replicated storage needs its own replication, recovery-point, and failure
testing plan; copying a datastore name across nodes does not copy its data. [2][3]

For SDN, complete [optional guest SDN](network-prerequisites.md#optional-sdn-for-guest-networks)
on **every eligible node** now. An SDN zone is a network implementation group,
not the architecture's DMZ/Services/Control firewall zone.

## Enable HA

After creating a disposable guest, add it under **Datacenter > HA**, with the
desired state started. Configure eligible nodes and affinity using the controls
for your installed release. Proxmox VE 9 replaces legacy HA groups with node
affinity rules. Keep Kubernetes control-plane VMs on separate physical hosts;
review whether strict anti-affinity would prevent recovery when capacity drops. [2]

Verify watchdog/fencing and redundant network/storage paths before a failure
test. HA can restart a guest after a host failure; it does not preserve that
guest's running memory. Migration, HA restart, and application-level availability
are different outcomes. Review cluster scheduling separately: do not assume
that merely joining hosts enables continuous workload balancing. [2]

This kit does not create the host cluster, storage, fencing, HA membership, or
affinity rules. Those are Tier 0 operator steps, not implied by Terraform VM creation.

## Terraform against the cluster

Use one reachable Proxmox API endpoint for the cluster and permissions covering
the intended nodes, storage, and guests; see [API setup](setup-api.md).
The endpoint is not a placement selector. Keep a working alternate endpoint or
independent API frontend for recovery; never host the only access path on the
cluster you are rebuilding. The provider does not select healthy target nodes. [4]

| Tier-local input | Meaning |
| --- | --- |
| `default_platform_node_name` | Initial VM creation node (or LXC target node), not a cluster name |
| `vm_instances.<key>.proxmox_node_name` | Per-VM initial placement override |
| Shared `proxmox_template_catalog["<vmid>"].node_name` | Node holding the source template for cross-node cloning |
| `proxmox_storage_classes` | Real datastore IDs available to the selected nodes |
| `network_zones.<key>.bridge` | Consistent Linux bridge or SDN VNet attachment |

The shared **VM** module ignores later `node_name` drift. Proxmox owns relocation,
HA, and maintenance moves; changing the configured initial node no longer moves
an existing VM. Other hardware changes remain managed. Resource addresses and
tier-local state paths are unchanged. Templates retain their own fixed publication
placement; update consumer source-node metadata if a template is deliberately moved. [4]

Set the source node using the **selected clone template's VMID**, not a future
builder output ID. If omitted, the provider assumes the initial destination
node also holds the template. Check cross-node clone storage prerequisites. [5]
Maintain that metadata once in the [shared consumer catalog](template-catalog.md).

**Scope:** this placement contract covers QEMU VMs, not the LXC module. The
reviewed container provider reads a node-specific path; do not assume the same
external-migration behavior for LXC. [6] Talos clones need their own resources,
not the Linux cloud-init module; see [Talos bootstrap](../talos/bootstrap.md).

The Linux guest roots currently set provider `insecure = true`. Before production,
establish trusted API certificates and review that setting in the owning roots.
The separate template publisher already verifies TLS.

## Prove failover

Use a disposable guest and a maintenance window; retain working out-of-band access.

1. Create on a different node from its source template; confirm all disks and networks.
2. Migrate with Proxmox, then run the owning tier's normal `--plan-only` workflow.
   It must not propose recreation or moving the VM back solely because of placement.
3. Exercise the reviewed host-failure/fencing procedure. Confirm restart on an
   eligible host, storage integrity, network reachability, and sufficient capacity.
4. Repeat the Terraform plan after recovery. Stop on unexpected drift; do not apply it.
5. For Kubernetes, also test API and workload availability, then record recovery times.

Offline mock tests cover the Terraform contract, not real failover. Recheck with
the provider version locked by each consuming root. Keep the
[backup and restore procedure](backup-foundation.md) independent of HA.

## References

Official documentation, checked 2026-09-21. Use the matching installed-release documentation.

1. [Proxmox cluster manager](https://github.com/proxmox/pve-docs/blob/master/pvecm.adoc).
2. [Proxmox HA manager](https://github.com/proxmox/pve-docs/blob/master/ha-manager.adoc).
3. [Proxmox storage replication](https://github.com/proxmox/pve-docs/blob/master/pvesr.adoc).
4. [Provider multi-node guide](https://registry.terraform.io/providers/bpg/proxmox/latest/docs/guides/multi-node).
5. [Provider VM clone arguments](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/resources/virtual_environment_vm.md).
6. [Provider container read implementation](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/proxmoxtf/resource/container/container.go).
