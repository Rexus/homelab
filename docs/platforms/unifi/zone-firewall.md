# UniFi zone firewall

## Table of contents

- [Prerequisites](#prerequisites)
- [Map the architecture](#map-the-architecture)
- [Apply the policy](#apply-the-policy)
- [Verify](#verify)
- [References](#references)

## Prerequisites

Use a gateway/release supporting zone-based firewalling; check the current
official requirements. [1] Keep a local recovery path, configuration backup,
and approved [network plan](../../architecture/network.md#example-network-plan).

This is a manual translation, not gateway automation. No zone is created just
because a tier repository exists.

## Map the architecture

Use the existing DMZ zone and add Services and Control zones as needed.
Assign each network to one zone. [1]

| Layer / purpose | Zone | Example member networks |
| --- | --- | --- |
| Edge | built-in `DMZ` | `edge` |
| Application | custom `Services` | `apps`, application-only `access`, telemetry |
| Control | custom `Control` | `management`, `identity`, `crypto` |
| Offline custody | none on the connected gateway | isolated ceremony/recovery fabric |

Use a separate `Lab` or other purpose-named zone when its policy differs.
Do not put untrusted labs into a service subnet merely to keep the zone count low.
Host-only cluster/storage fabrics can remain on controlled, non-routed switching.

WAN stays External. Gateway covers the gateway's own traffic, not the Control
layer. VPN membership is not administrative privilege. Review default Internal,
VPN, and same-zone policies; they are not this repository's intended rules. [1]

## Apply the policy

In the Zone Matrix, select the source row and destination column. Narrow each
allow by endpoint and listener, then keep a deny fallback. Review reverse
traffic; Auto Allow Return Traffic can provide replies. [1]

Example: `apps-to-dns` selects `Services` to `Control`, the approved app
subnet, the DNS server addresses, and TCP/UDP `53`. It does not allow the
whole Services zone to every Control endpoint.

Use the [firewall contracts](../../security/firewall-policy.md#rule-contracts)
for other flows. Preserve necessary gateway DHCP/DNS while restricting its
admin interfaces. [1] Apply equivalent intent to IPv6 and review NAT/VPN paths.

## Verify

Run the [policy tests](../../security/firewall-policy.md#rollout-and-validation),
including same-zone pairs and admin-denial checks. Gateway rules do not replace
local switch/client isolation. [2] Confirm rules and counters, then export the
reviewed configuration into project-owned documentation.

Renaming old tier-prefixed zones does not itself preserve policy. Review their
member networks and scoped rules before combining anything; retain separate
zones whenever access requirements differ.

## References

Sources checked 2026-09-19.

1. [Ubiquiti: Zone-Based Firewalls in UniFi](https://help.ui.com/hc/en-us/articles/115003173168-Zone-Based-Firewalls-in-UniFi)
2. [Ubiquiti: Implementing Network and Client Isolation](https://help.ui.com/hc/en-us/articles/18965560820247-Implementing-Network-and-Client-Isolation-in-UniFi)
