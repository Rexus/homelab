# Firewall rollout and acceptance

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) for network policy.
Guest-specific inputs remain in the consuming tier; gateway changes are operator procedures.

**Design:** [network map](../../../architecture/networking/README.md) and
[firewall contracts](../../../architecture/networking/firewall-policy.md).
**Prerequisites:** local console recovery and the approved endpoint/port policy.

## Step 1: Preserve recovery and define rules

1. Export the current configuration and test local recovery access.
2. Inventory routing, NAT/VPN rules, gateway services, and IPv6.
3. Record every required source, destination, protocol and port in the project policy.
   Use the [rule contracts](../../../architecture/networking/firewall-policy.md#rule-contracts).

## Step 2: Apply a pilot policy

1. Create the selected endpoint/port objects in the gateway's policy editor.
2. Add those scoped allows before terminal denies. Keep console access open.
3. Apply to one pilot subnet; test same-zone, gateway-local and IPv6 paths as well
   as routed traffic. Use the [UniFi field guide](unifi.md#apply-the-policy) for that platform.

## Step 3: Verify and continue

Run the relevant checks below from approved and unapproved source networks.
Record actual results rather than treating rule names as proof.

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

After pilot checks pass, export the reviewed configuration, move the remaining selected
networks and remove temporary access. Keep policy in project architecture and exports/test
evidence in project operating records. Return to
[foundation host/network preparation](../README.md#before-starting-hosts-and-networks).
