# Firewall rollout and acceptance

**Design:** [network map](../../../architecture/networking/README.md) and
[firewall contracts](../../../architecture/networking/firewall-policy.md).
**Prerequisites:** local console recovery and the approved endpoint/port policy.

## Procedure

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

For UniFi, use the [platform translation](unifi-zones.md).
Keep intended policy in project architecture; exports and test evidence belong in
project deployment and administration records.
A naming convention is not evidence that the firewall enforces it.
