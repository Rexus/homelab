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

Start with the [combined architecture view](../architecture/overview.md#tier-and-zone-view)
and [network assignment plan](../architecture/network.md). Know which gateway,
switch, host, or workload firewall actually sees each path. Keep local console
access and a configuration backup before changing policy.

This is the repository's intended policy, not a vendor's factory defaults or
an automatically applied ruleset. Deny new traffic unless a documented rule
permits its source, destination, protocol, and listener. This follows the
default-deny approach in NIST's firewall guidance. [1]

## Connected-zone matrix

Rows are **source zones** and columns are **destination zones**, unlike the
architecture placement view whose axes are tiers and layers. The cells name
candidate rule contracts from the next section, not allow-all permissions.
Only create a rule when a deployed service needs it; deny everything else.

| Source / destination | T2-Edge | T2-Application | T2-Control | T1-Edge | T1-Application | T1-Control |
| --- | --- | --- | --- | --- | --- | --- |
| **T2-Edge** | P | I | Deny | E | S | Deny |
| **T2-Application** | Deny | P | Deny | E | S | W |
| **T2-Control** | A | A | P | E | S | A, W |
| **T1-Edge** | Deny | I | Deny | P | I, S | Deny |
| **T1-Application** | M | M | Deny | E | P | W |
| **T1-Control** | A | A | A | A | A | P |

Tier 0 is absent: there is no routed path or connected firewall zone for
custody. Treat offline artifact approval and transfer as a separate procedure,
never an exception in this matrix.

This table governs **new connections**. Permit stateful replies to authorized
connections without granting the destination permission to initiate arbitrary
reverse sessions. [1] For example, `T1-Edge` may connect to a Tier 2 backend;
its replies need no Tier 2-to-Tier 1 ingress rule. Recovery dependency remains
independent of packet direction.

## Rule contracts

| Code | Purpose | Source and destination constraints |
| --- | --- | --- |
| I | ingress | exact proxy/load-balancer addresses to published backend addresses and listeners; include required health checks |
| S | shared services | named consumers to designated identity, DNS, time, secrets, registry, source-control, or telemetry endpoints only |
| E | controlled egress | approved clients to the outbound proxy/cache listener, not every service in the Edge zone |
| A | administration | named bastions or runners to explicit admin APIs/SSH endpoints, with scoped credentials; never the whole source zone |
| W | backup/archive writes | named producers to a dedicated storage receiver and protocol; no storage administration or cluster fabric access |
| M | monitoring | named collectors to explicit read-only exporters or health endpoints; no arbitrary callbacks or admin ports |
| P | same-zone peers | individually defined service dependencies, replication, or admin paths between member networks; no implicit peer trust |

`A` from `T2-Control` to `T1-Control` is only for an approved delegated API
such as scoped guest provisioning. It does not authorize Tier 2 to administer
the shared hypervisor or network. If no such contract exists, leave it denied.
`W` must distinguish a backup receiver from the storage system's control plane.

Example concrete rules, using addresses from the local plan:

| Rule name | Source selector | Destination selector | Protocol/listener |
| --- | --- | --- | --- |
| `t1-edge-to-project-web` | shared ingress host IPs | project web backend IPs | TCP, configured HTTPS/backend port |
| `t2-apps-to-dns` | approved project subnets | connected DNS server IPs | TCP and UDP `53` |
| `t2-apps-to-identity-web` | approved app hosts | connected identity broker VIP | TCP `443` when using HTTPS there |
| `t2-apps-to-cache` | approved app hosts | cache VIP | TCP `3128` for the reference proxy listener |
| `t2-runner-to-provisioning` | dedicated runner IP | approved platform API endpoint | TCP, deployed API listener; scoped token |

These are examples, not the full requirements of an identity or cluster
deployment. Derive directory, authentication, telemetry, storage, and replication
ports from the deployed service configuration and its guide. A network allow
rule does not replace service authentication or authorization.

Record each actual rule's owner, reason, source/destination zone and address
objects, protocol/ports, IP family, connection state, enforcement point, logging,
and a positive/negative test. Mark temporary exceptions with an expiry.

## Boundary peers

Apply these alongside the six-zone matrix:

| Initiator | Destination | Intended rule |
| --- | --- | --- |
| Internet/WAN | Tier 1 or Tier 2 Edge | only published VIPs/listeners; no direct Application or Control exposure |
| edge egress proxy/cache | Internet/WAN | only required upstream destinations and protocols; do not grant every Edge host unrestricted egress |
| Application or Control hosts | Internet/WAN | denied by default; use approved egress, with explicit bootstrap exceptions when necessary |
| user endpoints | access/app entry points | named service interfaces only, not general server subnet access |
| approved admin devices or remote-access identities | bastion/admin entry | scoped entry rule, then the A contract; separate from ordinary user/VPN access |
| managed networks | gateway-local services | only needed DHCP, DNS, time or other configured gateway services; separate admin UI/SSH permissions |
| designated control administrators | gateway/switch administration | named endpoints and admin protocols only |
| gateway-originated services | managed networks | explicit required infrastructure traffic; not blanket trusted access |

Use destination-specific rules for any direct Internet bootstrap exception
and remove it when the proxy/cache exists. Port forwarding, VPNs, and routing
must be reviewed with the same policy; publishing an endpoint does not justify
access to its entire subnet.

## Enforcement boundaries

- **Between routed subnets:** apply policy where routing actually occurs.
  If an L3 switch routes the path, a gateway-only rule may never see it.
- **Within a zone:** filter member subnets explicitly, including the matrix
  diagonal. Zone membership is not proof of mutual trust.
- **Within one subnet or host:** use switch/port isolation, host firewalls,
  virtual-network controls, or workload policies where required; traffic need
  not cross the gateway. UniFi's isolation guidance distinguishes these paths. [2]
- **Cluster and storage fabric:** restrict participating hosts and interfaces;
  do not expose a host-only fabric merely to bring it under gateway policy.
- **IPv6:** mirror the intended IPv4 policy or explicitly disable IPv6 where
  unsupported. Do not blanket-block the ICMPv6 needed for discovery and path
  operation; choose required types for the interface role. [3]
- **Custody:** enforce physical isolation and offline transfer procedure;
  no dual-homed host, VPN, shared routed gateway, or temporary firewall allow.

## Rollout and validation

1. Export the current configuration and test local recovery access.
2. Inventory routing and existing rules, including automatic NAT/VPN rules and IPv6.
3. Define exact endpoint/port objects and gateway infrastructure requirements.
4. Install scoped allows and required stateful replies before enforcing terminal denies.
5. Test a pilot subnet and then move other networks into their planned zones.
6. Verify rule order and counters, including same-zone pairs and gateway-local traffic.
7. Record results and remove temporary access rules.

| Test | Expected result |
| --- | --- |
| public client to published edge HTTPS listener | succeeds only on the published service |
| edge proxy to its registered app backend | succeeds; another backend port fails |
| Tier 2 app to designated Tier 1 DNS/identity endpoint | succeeds on required listeners |
| same app to Tier 1 admin API or SSH | fails |
| named control runner to its authorized API | succeeds; an ordinary workload source fails |
| unrelated subnets in the same zone | fail unless an explicit peer rule exists |
| reverse new connection after an allowed forward session | fails unless separately authorized; replies still work |
| DHCP/DNS and local recovery access after policy activation | continue to work as planned |
| IPv6 equivalent of a denied IPv4 path | denied, or IPv6 unavailable by design |
| connected system seeking a custody route | no connected path exists |

For UniFi, use the [platform translation](../platforms/unifi/zone-firewall.md).
Keep the approved plan, policy exports, and test evidence in owned architecture
documentation; generated guides are not evidence that a gateway enforces them.

## References

Sources checked 2026-09-16.

1. [NIST SP 800-41 Rev. 1: Guidelines on Firewalls and Firewall Policy](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-41r1.pdf)
2. [Ubiquiti: Implementing Network and Client Isolation](https://help.ui.com/hc/en-us/articles/18965560820247-Implementing-Network-and-Client-Isolation-in-UniFi)
3. [RFC 4890: Recommendations for Filtering ICMPv6 Messages in Firewalls](https://www.rfc-editor.org/info/rfc4890/)
