# UniFi zone firewall

## Table of contents

- [Prerequisites](#prerequisites)
- [Map the architecture](#map-the-architecture)
- [Apply the policy](#apply-the-policy)
- [Verify](#verify)
- [References](#references)

## Prerequisites

Use a gateway and software release supporting UniFi zone-based firewalling;
check current requirements in the official guide. [1] Have a local recovery
path, a configuration backup, and an approved
[network plan](../../architecture/network.md#example-network-plan).

This is a manual translation of the repository model, not gateway automation.

## Map the architecture

Create the needed custom zones from the
[zone assignment](../../architecture/network.md#zone-assignment) and assign
their networks. A UniFi network belongs to one zone. [1]

| Repository placement | UniFi assignment |
| --- | --- |
| Tier 1 / Edge | custom `T1-Edge`; attach `t1-edge` |
| Tier 1 / Application | custom `T1-Application`; attach `t1-access`, `t1-identity`, `t1-apps`, `t1-crypto` as needed |
| Tier 1 / Control | custom `T1-Control`; attach routed `t1-admin`, `t1-archive` |
| Tier 2 cells | matching `T2-Edge`, `T2-Application`, `T2-Control`; attach the corresponding project networks |
| Tier 0 / Control | no network or zone on the connected UniFi gateway |

Keep WAN in External. Gateway represents traffic to/from the gateway itself,
not the architecture's Control layer. VPN describes VPN traffic, not an
administrative privilege level. Review built-in Internal, VPN, and same-zone
allows rather than assuming they implement this repository's policy. [1]

Keep user devices in a separate endpoint group, and add their scoped entry
rules. Do not merge both tiers into a single built-in DMZ or Internal zone.
Non-routed host fabric stays on its own controlled switching path.

## Apply the policy

In the Zone Matrix, rows are sources and columns are destinations. Select the
pair, constrain address/port objects, and add each needed contract from the
[firewall matrix](../../security/firewall-policy.md#connected-zone-matrix).
Place scoped allows before the pair's deny fallback. Check reverse policy;
Auto Allow Return Traffic can provide stateful replies. [1]

For `t2-apps-to-dns`, select source `T2-Application` and destination
`T1-Application`, then constrain the source to the approved project subnet,
destination to DNS server addresses, and ports to TCP/UDP `53`.
The zone pair alone is too broad.

Preserve required gateway DHCP/DNS service access while restricting its admin
interfaces. [1] Apply the same review to IPv6 and existing NAT/VPN policies.

## Verify

Run the [policy validation tests](../../security/firewall-policy.md#rollout-and-validation),
including same-zone pairs. Gateway rules do not replace switch or client
isolation for local paths. [2] Confirm both the configured rule and observed
traffic counters, then export the reviewed configuration to owned documentation.

## References

Sources checked 2026-09-16.

1. [Ubiquiti: Zone-Based Firewalls in UniFi](https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi)
2. [Ubiquiti: Implementing Network and Client Isolation](https://help.ui.com/hc/en-us/articles/18965560820247-Implementing-Network-and-Client-Isolation-in-UniFi)
