# Firewall policy

## Table of contents

- [Prerequisites](#prerequisites)
- [Connected-zone matrix](#connected-zone-matrix)
- [Rule contracts](#rule-contracts)
- [Boundary peers](#boundary-peers)
- [Enforcement boundaries](#enforcement-boundaries)
- [Rollout and validation](#rollout-and-validation)
- [References](#references)

## Prerequisites

Use the [network plan](../architecture/network.md). Zone names describe network
protection; tier numbers identify repository ownership and potential impact.
Know which gateway, switch, host, or workload firewall sees each path.
Keep local console access and a configuration backup before changing policy.

This is the intended policy, not vendor defaults or an applied ruleset.
Deny new traffic unless an explicit rule permits its source, destination,
protocol, and listener, following default-deny guidance. [1]

## Connected-zone matrix

Rows initiate traffic; columns receive it. Start with three server zones,
not separate zones for every repo. The codes are possible rule types below,
**not permissions for the whole zone**. Add only the rules a service needs.

| Source / destination | DMZ | Services | Control |
| --- | --- | --- | --- |
| **DMZ** | P | I, S | S |
| **Services** | E | P, S, M | S, W |
| **Control** | A, M, E | A, M, S | P, A, S, W |

For example, a proxy may reach its backend and designated DNS servers.
It cannot administer the hypervisor. A workload may authenticate against an
identity endpoint without gaining access to its management interface.

Tier 0 connected control systems appear in the appropriate network policy.
**Offline custody does not:** there is no connected zone or route into it.
Approved offline transfers are a separate procedure, never a matrix exception.

Permit stateful replies to allowed connections without authorizing arbitrary
new sessions in the reverse direction. [1] A backend's reply to its proxy
does not require permission to initiate connections to every DMZ host.

## Rule contracts

| Code | Purpose | Required scope |
| --- | --- | --- |
| I | ingress | exact proxy IPs to published backend listeners and health checks |
| S | service access | named consumers to designated DNS, time, identity, secrets, registry, or other service endpoints |
| E | controlled egress | approved clients to a proxy/cache listener, not every DMZ service |
| A | administration | approved bastions or runners to specific admin endpoints with target-tier credentials |
| W | backup/archive writes | named producers to a dedicated receiver; no storage administration or cluster fabric |
| M | monitoring | named collectors to read-only exporters or health endpoints |
| P | same-zone peers | explicit dependencies or replication between selected hosts/subnets; no implicit peer trust |

Control-zone membership is not an administrative credential. An ordinary
workload or Tier 1 runner must not gain Tier 0 authority through an `A` rule.
Privileged execution and its approval path must be protected at the target tier.

Example rules, using addresses from the local plan:

| Rule name | Source selector | Destination selector | Protocol/listener |
| --- | --- | --- | --- |
| `edge-to-web` | ingress proxy IPs | published backend IPs | configured HTTPS/backend port |
| `apps-to-dns` | approved app subnets | DNS server IPs | TCP and UDP `53` |
| `apps-to-login` | approved app hosts | identity broker VIP | TCP `443` when deployed with HTTPS |
| `apps-to-cache` | approved app hosts | cache VIP | TCP `3128` for the reference proxy |
| `admin-to-platform` | Tier 0 bastion/runner IPs | platform admin API | configured listener; scoped admin identity |

These are not the complete requirements of an identity or cluster deployment.
Derive other ports from the actual service configuration. A network allow
does not replace authentication or authorization.

Record each rule's reason, source/destination objects, protocol/ports, IP family,
enforcement point, owner, and positive/negative tests. Give temporary rules an expiry.

## Boundary peers

Apply these alongside the server-zone matrix:

| Initiator | Destination | Intended rule |
| --- | --- | --- |
| Internet/WAN | DMZ | only published VIPs/listeners; no direct Services or Control exposure |
| egress proxy/cache | Internet/WAN | required upstream destinations/protocols only |
| Services or Control hosts | Internet/WAN | deny by default; approved egress or explicit bootstrap exception |
| user endpoints | application/access entry points | named service interfaces, not general subnet access |
| approved admin devices | bastion/admin entry | scoped entry then target-specific administration |
| managed networks | gateway services | required DHCP/DNS/time only; separate gateway admin permissions |
| control administrators | gateway/switch administration | named endpoints and admin protocols |
| gateway-originated services | managed networks | required infrastructure traffic, not blanket trust |

A VPN is an entry path, not a privilege tier. Review VPN, NAT, and port-forward
policy alongside the zone rules. Remove direct Internet bootstrap exceptions
when the approved update path is ready.

## Enforcement boundaries

- **Routed subnets:** filter at the device that routes the traffic.
- **Same zone:** filter member subnets explicitly, including the matrix diagonal.
- **Same subnet or host:** use switch isolation, host firewalls, or workload
  policy; that traffic need not cross the gateway. [2]
- **Cluster/storage fabric:** restrict host/interface membership without exposing it through a gateway.
- **IPv6:** apply the same policy intent or disable it where unsupported; retain
  required ICMPv6 functions rather than blocking them indiscriminately. [3]
- **Offline custody:** no routed gateway, dual-homed host, VPN, or temporary allow
  may bridge physical isolation.

## Rollout and validation

1. Export the current configuration and test local recovery access.
2. Inventory routing, NAT/VPN rules, gateway services, and IPv6.
3. Define endpoint/port objects and add scoped allows before terminal denies.
4. Test a pilot subnet, including same-zone and gateway-local traffic.
5. Record results, then move other networks and remove temporary access.

| Test | Expected result |
| --- | --- |
| public client to published edge listener | only the published service succeeds |
| edge proxy to backend | configured listener succeeds; unrelated ports fail |
| application to identity/DNS endpoint | required service listeners succeed |
| same application to identity admin or hypervisor API | fails |
| approved control runner to its authorized API | succeeds; an ordinary workload source fails |
| unrelated same-zone subnets | denied unless explicitly allowed |
| reverse new session after an allowed session | denied unless separately allowed; replies still work |
| required DHCP/DNS and local recovery access | continue to work |
| denied IPv4 path tested with IPv6 | also denied, or IPv6 unavailable by design |
| connected system seeking an offline-custody route | no path exists |

For UniFi, use the [platform translation](../platforms/unifi/zone-firewall.md).
Keep actual policies, exports, and evidence in owned architecture documentation.
A naming convention is not evidence that the firewall enforces it.

## References

Sources checked 2026-09-19.

1. [NIST SP 800-41 Rev. 1: Guidelines on Firewalls and Firewall Policy](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-41r1.pdf)
2. [Ubiquiti: Implementing Network and Client Isolation](https://help.ui.com/hc/en-us/articles/18965560820247-Implementing-Network-and-Client-Isolation-in-UniFi)
3. [RFC 4890: Recommendations for Filtering ICMPv6 Messages in Firewalls](https://www.rfc-editor.org/info/rfc4890/)
