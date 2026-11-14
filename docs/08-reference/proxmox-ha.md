# Proxmox VE HA controls

Exact field lookup for the HA dialogs, CLI and API. Follow the operations guide for
configuration, illustrations and recovery tasks. Proxmox VE 9 uses affinity rules.
Dynamic scheduling, automatic balancing and cluster-wide arm/disarm require 9.2+.
[Operations guide](../05-operations/01-hosting/proxmox-ha.md)

## Contents

- [HA menu and status](#ha-menu)
- [Resource fields and states](#resources)
- [Affinity rules](#affinity-rules)
- [Scheduling and maintenance](#scheduling-and-maintenance)
- [References](#references)

<a id="ha-menu"></a>

## HA menu and status

CRM means cluster resource manager. Each host's local resource manager, LRM, performs
its assigned actions. The GUI's requested configuration and observed status can differ
while an operation runs. [1][2]

| Area / field | Meaning |
| --- | --- |
| Status / Quorum | Whether this partition has the votes needed for cluster decisions |
| Status / Fencing | Watchdog/arming state, detailed below |
| Status / Master and LRM | Coordinating CRM and each node's LRM, with current timestamps |
| Resources / Add or Edit | Enroll an existing VM/CT or change its HA policy |
| Resources / Remove | Remove HA supervision while retaining the guest |
| Affinity Rules | Placement constraints on enrolled resources |
| Rule State | Reported feasibility or conflict, inspect after changing a rule |
| Arm HA / Disarm HA | Resume HA protection or release cluster-wide watchdogs |
| CRS Settings | Open the cluster resource scheduling options |

| Fencing state | Interpretation |
| --- | --- |
| `standby` | CRM watchdog on standby, for example before active HA work exists |
| `armed` | HA watchdog protection is armed, inspect node/resource status as well |
| `disarming` | Watchdogs are being released, wait for completion |
| `disarmed` | Watchdogs released, automatic fencing and recovery suspended |

`quorum OK` with an empty resource list and standby fencing is a cluster awaiting
HA enrollment. Check the effective state after enrollment and after every maintenance
window. Preserve the installed release's displayed detail when investigating a fault. [2]

<a id="resources"></a>

## Resource fields and states

Resource IDs use `vm:<VMID>` or `ct:<VMID>`. Defaults describe Proxmox's schema.
The local `proxmox_ha.yml` supplies the policy selected for this cluster. [3][4]

In the native recipe, `state` selects membership (`present` / `absent`), while `hastate`
selects the GUI's Request State. The recipe exposes retries and comments. The current collection
leaves Failback, Auto-Rebalance, negative node affinity and CRS settings to the GUI.
[Maintained input schema](../../tier-0/ansible/group_vars/proxmox_ha.yml.example)

| GUI field | API / CLI key | Meaning | Proxmox default |
| --- | --- | --- | --- |
| VM / CT, ID | `sid` | Existing guest selected for supervision | Required |
| Max. Restart | `max_restart` | Local restart attempts when starting the resource fails | `1` |
| Max. Relocate | `max_relocate` | Relocation attempts after local restart attempts are exhausted | `1` |
| Failback | `failback` | Move toward higher-priority node placement when available again | On |
| Auto-Rebalance | `auto-rebalance` | Permit periodic load-balancing migration of this resource | On |
| Request State | `state` | Desired state, table below | `started` |
| Comment | `comment` | Owner, purpose and runbook context | Empty |

Retry counts govern failed starts. They neither set a host-failure detection timeout
nor guarantee an outage duration. The relocation counter resets after a successful start. [3]

| Requested state | Controller behavior |
| --- | --- |
| `started` | Start and recover the resource, API alias `enabled` |
| `stopped` | Keep stopped, retain relocation of resource ownership on node failure |
| `disabled` | Stop and retain its node assignment, clear an existing HA error state |
| `ignored` | Stop HA supervision and allow ordinary guest management, retain configuration |

Observed `starting`, `migrate`, `relocate`, `fence`, `recovery`, `freeze`, `queued` and
`error` describe work or outcomes. Inspect the task log before changing requested state.
`recovery` can persist while no eligible destination exists. [1][3]

## Affinity rules

| GUI field | API / CLI key | Meaning |
| --- | --- | --- |
| ID | Rule identifier | Stable, unique rule name |
| Enable | Inverse of `disable` | Apply the rule when enabled |
| State | Observed result | Inspect conflicts or disabled rules |
| HA Resources | `resources` | Explicit enrolled resource IDs |
| Comment | `comment` | Reason for the constraint |
| Node Affinity / Prefer Nodes | `affinity=positive` | Prefer the selected host set |
| Node Affinity / Avoid Nodes | `affinity=negative` | Avoid the selected host set |
| Node Affinity / Strict | `strict` | Make preference/exclusion mandatory |
| Node Affinity / Priority | `nodes` entries | Higher positive-rule priority is preferred, equal values form a peer set |
| Resource Affinity / Keep Together | `affinity=positive` | Selected resources must share a host |
| Resource Affinity / Keep Separate | `affinity=negative` | Selected resources must occupy different hosts |

Node rules select eligible/preferred hosts. Resource rules relate guests to each other
and enforce hard placement constraints. Three separated VMs on three hosts leave one
waiting when only two hosts remain. Resource affinity exposes no soft/strict switch. [5][6]

Negative node rules accept no priorities. A resource belongs to at most one node rule.
When combining node and resource affinity, use a single node-priority class. Inspect
rule state after applying, because conflicting rules can be disabled. [5][6]

## Scheduling and maintenance

| Control | Meaning | Initial choice to qualify |
| --- | --- | --- |
| HA Settings / Shutdown Policy | Response to orderly host shutdown/reboot | `migrate` for movable resources |
| CRS / Scheduling Mode | `basic` counts guests, `static` considers configured CPU/RAM, `dynamic` also considers measured use | `static` on 9.0/9.1, assess `dynamic` on 9.2+ |
| Rebalance on Start | Select placement when an HA resource starts | Off during initial qualification |
| Automatic Rebalance | Periodically migrate HA resources to reduce cluster imbalance | Enable after mobility and affinity checks |
| Imbalance Threshold | Normalized cluster imbalance that triggers evaluation | Default `30%` |
| Hold Duration | Consecutive HA rounds above threshold | Default `3` rounds, approximately 30 seconds |
| Minimum Imbalance Improvement | Required predicted improvement before moving | Default `10%` |
| Rebalancing Method | Candidate-selection algorithm | Default `bruteforce`, alternative `topsis` |
| HA `max_worker` | Concurrent HA workers per node | Default `4`, qualify against migration bandwidth |
| Node Maintenance | Evacuate HA resources, exclude this host from new HA placement | One host at a time |

The UI reaches HA/CRS settings through **Datacenter > Options** or **HA > CRS Settings**.
Automatic balancing uses static/dynamic mode and each resource's Auto-Rebalance flag.
Positive-affinity peers of a resource excluded from balancing are excluded with it. [7][8]

| Shutdown policy | Orderly host action |
| --- | --- |
| `migrate` | Evacuate running HA resources, can wait when mobility/rules block evacuation |
| `failover` | Stop resources, permit recovery on another host |
| `freeze` | Stop and retain resources for return on the same host |
| `conditional` | Use failover for poweroff and freeze for reboot |

| Disarm mode | During the disarmed interval |
| --- | --- |
| `freeze` | Preserve current resource state and suspend HA requests |
| `ignore` | Suspend HA tracking and permit manual guest management |

Node-maintenance state survives disarm/re-arm. Watch the observed arming state until
its requested transition completes. Consult the operations guide for the complete
maintenance and re-arm sequence. [1][2]

## References

Official sources checked 2026-11-14. Use the installed Proxmox release's help for its supported controls.

1. [HA manager, service states and maintenance](https://github.com/proxmox/pve-docs/blob/master/ha-manager.adoc).
2. [HA status API and fencing state](https://github.com/proxmox/pve-ha-manager/blob/master/src/PVE/API2/HA/Status.pm).
3. [Resource state, retry and failback schema](https://github.com/proxmox/pve-ha-manager/blob/master/src/PVE/HA/Resources.pm).
4. [Resource dialog and defaults](https://github.com/proxmox/pve-manager/blob/master/www/manager6/ha/ResourceEdit.js).
5. [Node-affinity schema](https://github.com/proxmox/pve-ha-manager/blob/master/src/PVE/HA/Rules/NodeAffinity.pm).
6. [Resource-affinity schema](https://github.com/proxmox/pve-ha-manager/blob/master/src/PVE/HA/Rules/ResourceAffinity.pm).
7. [CRS dialog and defaults](https://github.com/proxmox/pve-manager/blob/master/www/manager6/form/CRSOptions.js).
8. [HA options and worker limit](https://github.com/proxmox/pve-cluster/blob/master/src/PVE/DataCenterConfig.pm).
