# ProxLB balancing alternative

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** accepted [native HA foundation](../step-1b-cluster-ha.md), movable guests,
trusted Proxmox API TLS, a protected execution host and a reviewed pinned ProxLB release.

The main path uses Proxmox VE 9.2+ native balancing. Select ProxLB only for a
specific additional scheduling requirement. It is a third-party API client,
not fencing, storage replication or automatic recovery of a dead host's VMs. [1]

## Contents

- [Choose the ownership boundary](#choose-the-ownership-boundary)
- [Qualify and enable](#qualify-and-enable)
- [References](#references)

## Choose the ownership boundary

ProxLB's current HA integration guidance warns against competing HA-group placement
and ProxLB decisions. Do not infer compatibility with every newer native rule. [1]

| Scope | Placement authority | Policy |
| --- | --- | --- |
| Critical HA guests, including directory and control planes | Native HA/CRS | Exclude from ProxLB using `plb_ignore_<purpose>` tags or `balancing.ignore_guests` |
| Selected non-HA movable guests | ProxLB | Native automatic balancing does not select these; ProxLB tags/pools express their grouping |
| Same HA guest managed by both | Unqualified alternative | Not the selected path; needs pinned-version rule/failover evidence before acceptance |

ProxLB tags are not native HA rules. Its `service.enable_ha` coordinates ProxLB
instances using cluster state; it does **not** enroll guests in Proxmox HA or
guarantee service availability. Keep the first deployment to one active scheduler. [1][2]

## Qualify and enable

1. Install the selected signed release using the maintained
   [upstream installation instructions](https://github.com/credativ/ProxLB#installation).
   Run on an existing protected Tier 0 execution host; this kit installs no extra VM or ProxLB service.
   Keep the API token/config local and private, use certificate verification and scope permissions
   to inspected nodes/guests. The balancer's credentials are Tier 0 authority.
2. Start from that release's [example configuration](https://github.com/credativ/ProxLB/blob/main/config/proxlb_example.yaml).
   Select VM-only balancing, live migrations, sequential work, no local-disk moves,
   explicit ignored HA guests and host reservations. A reasonable trial is memory-based
   balancing, 75% trigger, 10-point imbalance and a 60-minute interval; tune after measurements.
3. With the service stopped, review a one-shot dry run:

   ```bash
   proxlb --config /etc/proxlb/proxlb.yaml --dry-run
   ```

   Set daemon mode off for a one-shot review. Ensure no ignored/HA/passthrough guest
   appears in the move set. Test one approved migration, repeat Terraform plans and
   verify native HA rules remain effective. Enable periodic operation only afterward.

Keep N+1 capacity outside the balancer's optimization target. Stop it for conflicting
maintenance, fault investigation or unexpected migration churn. Native HA must still
recover its enrolled guests with ProxLB stopped. Record the selected version, exclusion
set, dry-run output and migration tests in the project platform record.

## References

1. [Maintained ProxLB project: configuration, HA warning and tags](https://github.com/credativ/ProxLB), reviewed 2026-10-27.
2. [ProxLB example: service coordination and selected controls](https://github.com/credativ/ProxLB/blob/main/config/proxlb_example.yaml), reviewed 2026-10-27.
