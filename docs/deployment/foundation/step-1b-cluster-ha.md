# Step 1b: Proxmox cluster HA

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).

<a id="proxmox-cluster-and-ha"></a>

**Branch from:** [Step 1](README.md#step-1-prepare-compute-and-templates), before important guests exist.
**Change:** Add clustered placement and tested failover.
**Return:** [Step 1](README.md#step-1-prepare-compute-and-templates) to continue with access, templates and a test guest.

**Design:** [compute availability](../../architecture/compute/README.md).

Optional foundation setup in Tier 0, **before templates and important guests**. A single
host is valid for a pilot. A cluster adds shared administration; HA must be
configured separately for selected guests. Neither replaces backups.

**Target: Proxmox VE 9+.** The selected path uses **9.2+ native HA and dynamic
rebalancing**, not a second scheduler. ProxLB remains an [alternative](proxmox/proxlb.md).
On 9.0/9.1, HA and affinity are available, but the native automatic load balancer is not. [7]

**Yes: an HA-enrolled VM can restart on a surviving host after its original host dies.**
The original host must be fenced, a quorate survivor must have its disks/networks,
and placement/capacity must permit recovery. This is a cold restart with downtime,
not migration of a dead host's memory. An application hang inside a running VM is
not automatically detected by guest-level HA. [2]

## Table of contents

- [Prepare and join hosts](#prepare-and-join-hosts)
- [Make guests movable](#make-guests-movable)
- [Enable HA](#enable-ha)
- [Select rebalancing](#select-rebalancing)
- [Terraform against the cluster](#terraform-against-the-cluster)
- [Prove failover](#prove-failover)
- [References](#references)

## Prepare and join hosts

Start with [host installation and preparation](proxmox/README.md#first-deployment-order).

| Step | Action | Ready when |
| --- | --- | --- |
| 1. Plan | Choose final node names/IPs, Corosync links, and host capacity | Choices recorded in project docs |
| 2. Install | Use compatible Proxmox releases; configure DNS/time and protected access | Every node works independently |
| 3. Network | Follow [host networking](proxmox/network.md); separate latency-sensitive Corosync from busy storage/migration traffic | Links tested before joining |
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

For SDN, complete [optional guest SDN](proxmox/network.md#optional-sdn-for-guest-networks)
on **every eligible node** now. An SDN zone is a network implementation group,
not the architecture's DMZ/Services/Control firewall zone.

## Enable HA

1. Qualify shared live storage, remaining-host capacity and watchdog/fencing on all nodes.
   Prefer the server's supported hardware watchdog; do not change watchdog settings without console access.
2. After creating a disposable VM, add it in **Datacenter > HA > Resources**.
   Use `started`, `Max. Restart = 1`, `Max. Relocate = 1`; these are a conservative starting policy,
   not an outage-duration guarantee. Enroll each important guest explicitly after its tests pass.
3. Configure **HA > Rules**, then the shutdown/scheduling options below. Use the
   [menu reference](../../reference/proxmox-ha.md) for every field, state and recommended starting value.

Use node affinity for required hardware/storage eligibility and resource anti-affinity
for replica separation. Proxmox VE 9 uses rules rather than legacy HA groups.
Resource anti-affinity is a **hard constraint**: three control-plane VMs constrained
to three separate hosts cannot all restart on two hosts. The surviving two may preserve
etcd quorum, while the third waits. Do not describe this as three recovered replicas. [2]

This kit does not create the host cluster, storage, fencing, HA membership, or
affinity rules. Those are Tier 0 operator steps, not implied by Terraform VM creation.

## Select rebalancing

In **Datacenter > Options > HA Settings**, select `migrate` for planned single-node
maintenance after migration has been qualified. For **Cluster Resource Scheduling**,
use `Dynamic Load`, enable `Automatic Rebalance`, and retain the initial threshold
`30%`, hold duration `3` rounds, minimum improvement `10%` and `Bruteforce` method.
These are starting values to measure, not universal sizing advice. Leave `Rebalance
on Start` off initially: it is a separate placement option, not required for failure recovery.
Details and cautions are in the [scheduler reference](../../reference/proxmox-ha.md#scheduling-and-maintenance). [7][8]

Native rebalancing applies to **HA-managed resources only** and respects HA rules.
For this path, do not run ProxLB against the same guests. If ProxLB is selected
for another scope, follow its [separate rollout and compatibility checks](proxmox/proxlb.md).
The [worked failover example](proxmox/failover.md) shows the directory pair
before and after a node failure, including where recovery must wait.

## Terraform against the cluster

Use one reachable Proxmox API endpoint for the cluster and permissions covering
the intended nodes, storage, and guests; see [API setup](proxmox/api-access.md).
The endpoint is not a placement selector. Keep a working alternate endpoint or
independent API frontend for recovery; never host the only access path on the
cluster being rebuilt. The provider does not select healthy target nodes. [4]

| Tier-local input | Meaning |
| --- | --- |
| `default_platform_node_name` | Initial VM creation node (or LXC target node), not a cluster name |
| `vm_instances.<key>.proxmox_node_name` | Per-VM initial placement override |
| Shared `proxmox_template_catalog["<vmid>"].node_name` | Node holding the source template for cross-node cloning |
| `proxmox_storage_classes` | Real datastore IDs available to the selected nodes |
| `network_zones.<key>.bridge` | Consistent Linux bridge or SDN VNet attachment |

Each tier's **VM** module ignores later `node_name` drift. Proxmox owns relocation,
HA, and maintenance moves; changing the configured initial node no longer moves
an existing VM. Other hardware changes remain managed. Resource addresses and
tier-local state paths are unchanged. Templates retain their own fixed publication
placement; update consumer source-node metadata if a template is deliberately moved. [4]

Set the source node using the **selected clone template's VMID**, not a future
builder output ID. If omitted, the provider assumes the initial destination
node also holds the template. Check cross-node clone storage prerequisites. [5]
Maintain that metadata once in the [shared consumer catalog](../../reference/template-catalog.md).

**Scope:** this placement contract covers QEMU VMs, not the LXC module. The
reviewed container provider reads a node-specific path; do not assume the same
external-migration behavior for LXC. [6] Talos clones need their own resources,
not the Linux cloud-init module; see [Talos bootstrap](../stage-4-kubernetes/step-1b-manual-cluster.md).

Complete the [API TLS gate](proxmox/api-access.md#tls-gate) before live deployment;
cluster membership does not establish trusted API certificates.

## Prove failover

Use a disposable guest and a maintenance window; retain working out-of-band access.

1. Create on a different node from its source template; confirm all disks and networks.
2. Migrate with Proxmox, then run the owning tier's normal `--plan-only` workflow.
   It must not propose recreation or moving the VM back solely because of placement.
3. Exercise the reviewed host-failure/fencing procedure. Confirm restart on an
   eligible host, storage integrity, network reachability, and sufficient capacity.
4. Repeat the Terraform plan after recovery. Stop on unexpected drift; do not apply it.
5. For Kubernetes, also test API and workload availability, then record recovery times.

Follow the [fault and recovery checks](proxmox/failover.md#verify-the-result)
for quorum loss, placement constraints and the returned host. A clean migration
test alone is not proof of recovery after host death.

Offline mock tests cover the Terraform contract, not real failover. Recheck with
the provider version locked by each consuming root. Keep the
[backup and restore procedure](../../administration/compute/backup-restore.md) independent of HA.

## References

Official documentation, checked 2026-10-27. Use the matching installed 9.x documentation.

1. [Proxmox cluster manager](https://github.com/proxmox/pve-docs/blob/master/pvecm.adoc).
2. [Proxmox HA manager](https://github.com/proxmox/pve-docs/blob/master/ha-manager.adoc).
3. [Proxmox storage replication](https://github.com/proxmox/pve-docs/blob/master/pvesr.adoc).
4. [Provider multi-node guide](https://registry.terraform.io/providers/bpg/proxmox/latest/docs/guides/multi-node).
5. [Provider VM clone arguments](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/resources/virtual_environment_vm.md).
6. [Provider container read implementation](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/proxmoxtf/resource/container/container.go).
7. [Proxmox VE 9.2: native dynamic load balancer](https://www.proxmox.com/en/about/company-details/press-releases/proxmox-virtual-environment-9-2).
8. [Proxmox scheduling controls](https://github.com/proxmox/pve-manager/blob/master/www/manager6/form/CRSOptions.js).
