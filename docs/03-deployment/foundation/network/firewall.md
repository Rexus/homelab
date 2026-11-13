# Firewall rollout and acceptance

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) for network policy.
Guest-specific inputs remain in the consuming tier; gateway changes are operator procedures.

**Design:** [network map](../../../01-architecture/05-networking/README.md) and
[firewall contracts](../../../01-architecture/05-networking/01-firewall-policy.md).
**Prerequisites:** local console recovery and the approved endpoint/port policy.

**Already applied the gateway policy in the UniFi workflow?** Retain that configuration and
continue at [Step 5: acceptance checks](#step-5-verify-accepted-paths). Steps 1–4 are for an
unconfigured or changed policy, not another mandatory application of the same rules.

<a id="step-1-preserve-recovery-and-define-rules"></a>

## Step 1: Preserve recovery access

Export the current gateway configuration and test local console/recovery access before changes.

## Step 2: Record the required flows

Inventory routing, NAT/VPN rules, gateway services and IPv6. Record every required source,
destination, protocol and port in the project policy, using the
[rule contracts](../../../01-architecture/05-networking/01-firewall-policy.md#rule-contracts).

<a id="step-2-apply-a-pilot-policy"></a>

## Step 3: Configure scoped rules

In the **gateway policy editor**, create the selected endpoint/port objects and scoped allows
before terminal denies. Keep console access open. The [UniFi field reference](unifi.md#apply-the-policy)
explains that platform's fields; it is not another commissioning workflow to repeat.

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

## Step 4: Apply to a pilot subnet

Apply the selected gateway policy to one pilot subnet. Preserve management access and test
same-zone, gateway-local and IPv6 paths as well as routed traffic before expanding the rollout.

<a id="step-3-verify-and-continue"></a>

## Step 5: Verify accepted paths

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

## Step 6: Record and continue

After pilot checks pass, export the reviewed configuration, move the remaining selected
networks and remove temporary access. Keep policy in project architecture and exports/test
evidence in project operating records. Return to
[Foundation Step 2: manual Linux template](../README.md#step-2-create-the-first-linux-template-manually).
Do not repeat gateway commissioning or host installation. Later guest-dependent rules/tests stay
with the owning deployment; their services do not need to exist for Foundation acceptance.

## References

1. [Proxmox Datacenter and VM/container firewall controls](https://github.com/proxmox/pve-docs/blob/master/pve-firewall.adoc#vmcontainer-configuration).
