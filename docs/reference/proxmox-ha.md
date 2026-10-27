# Proxmox VE HA controls

Field reference for the [cluster/HA setup](../deployment/foundation/step-1b-cluster-ha.md).
Target Proxmox VE 9+; native dynamic balancing and HA arm/disarm require 9.2+.
Values below are a conservative homelab starting policy, not settings applied by this kit.
Use the installed UI's help if its patch-level labels differ.

## Contents

- [HA menu](#ha-menu)
- [Resources](#resources)
- [Affinity rules](#affinity-rules)
- [Scheduling and maintenance](#scheduling-and-maintenance)
- [References](#references)

## HA menu

| Area / action | Meaning | Expected use |
| --- | --- | --- |
| Status | Quorum, active cluster resource manager (CRM), each node's local manager (LRM), guest state | Healthy quorum, active CRM, current LRM updates; investigate stale timestamps/errors |
| Resources: Add/Edit | Enroll a VM/CT and set its requested behavior | Add only after storage, mobility and fencing tests |
| Resources: Remove | Remove HA supervision; does not itself stop/delete the guest | Planned ownership change; no automatic recovery afterward |
| Rules: Node Affinity | Allowed/preferred host placement | Hardware/storage restrictions or preferences |
| Rules: Resource Affinity | Keep selected guests together or apart | Separate replicas; avoid unnecessary together-rules |
| Rule errors / disabled rule | A rule is ineffective or conflicts with another rule | Resolve the reported conflict; do not assume the intended separation exists |
| Groups, if retained during upgrade | Deprecated predecessor to node-affinity rules | Review migrated rules; no new group-based setup |
| Arm / Disarm (9.2+) | Enable or suspend cluster-wide fencing/recovery | Keep **armed** normally; disarm only under an approved whole-cluster maintenance plan |

CRM coordinates the cluster; LRM performs actions on its node. Neither is an application
health probe. Do not kill these daemons or `watchdog-mux` to simulate failure. [1]

## Resources

Resource ID is `vm:<VMID>` or `ct:<VMID>`, not its display name. The requested state
is a policy; the status column is the asynchronous outcome. Current controls: [2][3]

| Field | Meaning | Starting choice |
| --- | --- | --- |
| VM / CT | Guest enrolled in HA | The exact tier-owned VMID; never a template |
| Request State | Desired service state, below | `started` for accepted always-on services |
| Max. Restart | Extra start attempts on the current host before relocation is considered | `1`; raising it can prolong a failed-start outage |
| Max. Relocate | Attempts at another eligible host after local retries fail | `1`; investigate persistent failures rather than retry indefinitely |
| Failback | Return toward higher-priority node-affinity placement when it becomes available | Off initially to avoid an immediate return to a repaired host; review with rule priorities |
| Auto-Rebalance (9.2+) | Permit this resource to participate in automatic load-balancing migrations | On for proven movable guests; off for a measured exception |
| Comment | Operational context | Owner, service, dependencies and recovery-runbook link; no secrets |

| Requested state | Effect |
| --- | --- |
| `started` | Attempt to run and recover the guest; `enabled` is an API alias |
| `stopped` | Keep stopped, but still relocate its ownership after node failure |
| `disabled` | Stop, do not relocate; also clears the HA error state for deliberate repair |
| `ignored` | Bypass HA supervision without requesting a stop; ordinary management resumes |

`starting`, `migrate`, `relocate`, `fence`, `recovery`, `freeze` and `error` can appear
as observed states. `fence`/`recovery` may mean waiting safely, not successful recovery.
An `error` requires fixing the cause before disabling/re-enabling the resource. [1][2]

## Affinity rules

| Field / type | Meaning | Starting choice |
| --- | --- | --- |
| ID, Comment, Enabled/Disable | Rule identity, rationale and whether enforced | Stable purpose name; enabled only after reviewing eligibility |
| Resources | Enrolled resource IDs affected by the rule | Explicit VMIDs; keep unrelated services out |
| Node Affinity: Nodes / Priority | Preferred host list; a higher priority is preferred | Equal priorities for general movable guests; omit unnecessary preferences |
| Node Affinity: Strict | Restrict to listed hosts instead of permitting fallback | Off for preference; on only for a real dependency/security restriction |
| Node Affinity: Positive/Negative, where exposed | Prefer/require listed hosts, or avoid/exclude them | Positive allowlist for hardware constraints; qualify negative rules on installed release |
| Resource Affinity: Positive | All selected resources must share a host | Avoid for redundant service members |
| Resource Affinity: Negative | Selected resources must use distinct hosts | Use for the directory pair; capacity and host count must permit it |

Node preference is not resource anti-affinity. Resource affinity has no soft/strict
toggle in the reviewed implementation: unsatisfied separation can block recovery. [4][5]
For example, three separated control planes on three hosts leave one unrecovered
after a host dies, even when the other two have spare RAM. Document that degraded
state or design an explicit reviewed alternative; never promise automatic relaxation.

## Scheduling and maintenance

These controls are in **Datacenter > Options**, not all under the HA submenu. [6][7]

| Control | Meaning | Starting choice |
| --- | --- | --- |
| HA Settings: Shutdown Policy | Behavior during an orderly node shutdown/reboot; not unexpected power loss | `migrate` after qualification; can wait indefinitely if rules/devices prevent migration |
| CRS: Scheduling Mode | `basic`: guest count; `static`: configured CPU/RAM; `dynamic`: observed and configured load | `dynamic` on 9.2+; `static` for 9.0/9.1 placement, not periodic balancing |
| CRS: Rebalance on Start | Choose placement again when an HA resource starts | Off initially; separate from node-failure recovery and periodic balancing |
| CRS: Automatic Rebalance | Periodic HA-guest migrations for lower imbalance; static/dynamic modes only | On after migration/affinity tests; 9.2+ |
| CRS: Imbalance Threshold | Trigger based on normalized cluster imbalance, not one host's CPU percentage | `30%` initially; do not set to zero to chase every difference |
| CRS: Hold Duration | Consecutive HA rounds above threshold before considering a move | `3` rounds initially; roughly 30 seconds, not a failover timer |
| CRS: Minimum Imbalance Improvement | Minimum predicted relative improvement to justify migration | `10%` initially to reduce churn |
| CRS: Rebalancing Method | Candidate-selection algorithm: `bruteforce` or `topsis` | `bruteforce` default for a small cluster; change only after measurement |
| HA worker limit (`max_worker`, HA-manager option) | Concurrent HA work per node; distinct from the generic bulk-action worker setting | Keep HA default `4`, reduce on constrained migration networks after testing |
| Node maintenance | Evacuate HA guests and prevent new HA placement there | One node at a time; confirm no guest/work remains before poweroff; non-HA guests need separate handling |

`migrate` evacuates on orderly shutdown; `failover` stops then permits recovery;
`freeze` waits for that same node; `conditional` uses failover for poweroff and
freeze for reboot. Returning from maintenance can move guests back, so review
the outcome before allowing routine rebalancing. [1]

Disabling Failback prevents priority-driven return, not all load-balancing moves.
Keep a repaired host in maintenance, or pause automatic rebalancing, until its
hardware/storage checks pass. For three equal hosts, the protected workload must
fit within **two hosts' usable capacity**, after OS/Ceph reservations, and each
recoverable VM must fit on an eligible individual survivor.

Keep headroom for a failed node, host/OS/Ceph needs and migration overhead; low average
CPU is not N+1 capacity. A node returning online is not proof its storage or hardware
is healthy. Do not lower Ceph safety thresholds or quorum votes to force a guest start.
During HA disarm there is **no automatic fencing or recovery**. It is not ordinary
single-node maintenance. The [worked test](../deployment/foundation/proxmox/failover.md)
records both service downtime and rule-constrained degraded states.

## References

Official sources reviewed 2026-10-27; installed-release help is authoritative.

1. [HA manager: fencing, states, shutdown and maintenance](https://github.com/proxmox/pve-docs/blob/master/ha-manager.adoc).
2. [HA resource state and retry schema](https://github.com/proxmox/pve-ha-manager/blob/master/src/PVE/HA/Resources.pm).
3. [Resource dialog](https://github.com/proxmox/pve-manager/blob/master/www/manager6/ha/ResourceEdit.js).
4. [Node-affinity schema](https://github.com/proxmox/pve-ha-manager/blob/master/src/PVE/HA/Rules/NodeAffinity.pm).
5. [Resource-affinity constraints](https://github.com/proxmox/pve-ha-manager/blob/master/src/PVE/HA/Rules/ResourceAffinity.pm).
6. [Datacenter HA options](https://github.com/proxmox/pve-manager/blob/master/www/manager6/dc/OptionView.js).
7. [CRS dialog and defaults](https://github.com/proxmox/pve-manager/blob/master/www/manager6/form/CRSOptions.js).
