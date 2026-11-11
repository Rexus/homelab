# Firewall rollout and acceptance

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) for network policy.
Guest-specific inputs remain in the consuming tier; gateway changes are operator procedures.

**Design:** [network map](../../../01-architecture/05-networking/README.md) and
[firewall contracts](../../../01-architecture/05-networking/01-firewall-policy.md).
**Prerequisites:** local console recovery and the approved endpoint/port policy.

## Step 1: Preserve recovery and define rules

1. Export the current configuration and test local recovery access.
2. Inventory routing, NAT/VPN rules, gateway services, and IPv6.
3. Record every required source, destination, protocol and port in the project policy.
   Use the [rule contracts](../../../01-architecture/05-networking/01-firewall-policy.md#rule-contracts).

## Step 2: Apply a pilot policy

1. Create the selected endpoint/port objects in the gateway's policy editor.
2. Add those scoped allows before terminal denies. Keep console access open.
3. Apply to one pilot subnet; test same-zone, gateway-local and IPv6 paths as well
   as routed traffic. Use the [UniFi field guide](unifi.md#apply-the-policy) for that platform.

### Proxmox guest interfaces

The [guest NIC contract](../../../08-reference/network-inputs.md#guest-nic-firewall)
enables each managed interface's **Firewall** checkbox. Before applying this to an
existing guest, inspect **Datacenter > Firewall > Options**, that guest's
**Firewall > Options**, and its accepted rules. The interface flag and general
firewall enablement are separate controls. [1]

Require permitted administration, DNS/time, package access and service traffic
before enabling filtering. Cache guests also need their accepted proxy and VRRP
paths. Keep console access and test one pilot guest first. The NIC change does
not install those rules or enable the cluster firewall.

## Step 3: Verify and continue

Run the relevant checks below from approved and unapproved source networks.
Record actual results rather than treating rule names as proof.

In Foundation, test the existing workstation, host-management and pilot-guest paths.
Use a known listening test service to distinguish a firewall denial from an absent server.
Keep later service rules closed until their owning stage deploys and tests the listener;
identity, ingress and hosted runners are not Foundation acceptance prerequisites.

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

## References

1. [Proxmox Datacenter and VM/container firewall controls](https://github.com/proxmox/pve-docs/blob/master/pve-firewall.adoc#vmcontainer-configuration).
