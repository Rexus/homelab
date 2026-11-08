# USB HSM service operations

<a id="usb-hsm-gateway-maintenance"></a>


Operate an already qualified [USB HSM deployment](../../deployment/stage-3-trust/step-1b-usb-hsm.md).
The repository's `hsm` recipe supplies the **OS baseline only**. Device lifecycle,
signing application, routing/readiness and key replication remain selected integrations.
The [service design](../../architecture/cryptography/usb-hsm.md) owns their relationships.

**Run from:** generated Tier 0 for host inputs; the selected gateway for native runtime checks.
**Before starting:** actual application unit/provider, approved device/key records,
independent wrapping/recovery material and an accepted failure/capacity budget.

<a id="table-of-contents"></a>

## Tasks

- [Is a gateway healthy?](#health-checks)
- [How is the attached device verified?](#device-identity)
- [How is one gateway maintained?](#how-is-one-gateway-maintained)
- [How are approved key objects replicated or rotated?](#replica-updates)
- [Which checks are repeated after maintenance?](#routine-checks)
- [References](#references)

<a id="health-checks"></a>

## Is a gateway healthy?

1. On the selected gateway, inspect its **actual commissioned** runtime unit:

   ```bash
   # Run on the selected commissioned HSM gateway.
   read -r -p 'Existing signing runtime systemd unit: ' HSM_UNIT
   systemctl status "$HSM_UNIT" --no-pager
   ```

   The repository creates no generic unit with this name; obtain it from the
   selected application runbook. Review diagnostic logs locally without exporting credentials.
2. Use that application's scoped readiness operation against the expected local
   token/key. Confirm authenticated session setup and a permitted test operation;
   port checks, slot visibility and object listings alone are insufficient.
3. Verify unauthorized operations fail and measured surviving capacity meets the
   accepted latency/error budget. Fail closed on a missing/mismatched key.

For co-hosted proxies (E3), backend readiness and frontend VIP capacity are different
checks. A failed local token need not disable a frontend that can serve another
healthy backend. Use the qualified application/session model, not blind retries.

<a id="device-identity"></a>

## How is the attached device verified?

1. Compare the vendor/provider's reported stable serial/reader/token identity with
   the private project record; never identify a production device only by transient slot number. [1]
2. Compare expected key object IDs/labels, public fingerprints and operation attributes.
   Do not export private keys to perform this check.
3. Require the expected device before application startup. Stop and investigate on
   mismatch; reinitializing an unknown device is not a repair.

<a id="how-is-one-gateway-maintained"></a>

## How is one gateway maintained?

1. Verify another accepted member has capacity, then drain this member through the
   application's native procedure. Preserve pending requests/session state and backups.
2. For **OS-baseline reconciliation only**, from Tier 0 select one inventory host
   and inspect the target list first: [3]

   ```bash
   # Run from <prefix>-tier-0/ on the protected execution host.
   read -r -p 'Gateway inventory host (for example hsm-1): ' HSM_HOST
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/maintenance/hsm.yml -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml --limit "${HSM_HOST:?Select one gateway}" --list-hosts
   ```

   Stop unless exactly the intended connected gateway is selected. Add approved
   named-environment overlays last when used; never target the offline ceremony host.
3. Reconcile only that accepted baseline target:

   Run from `<prefix>-tier-0/` on the protected execution host.

   ```bash
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/maintenance/hsm.yml -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml --limit "${HSM_HOST:?Select one gateway}"
   ```

   This does not upgrade firmware/application/provider, drain traffic or install a VIP.
   Those operations require the selected product's qualified maintenance procedure.
4. Verify device identity, readiness, permitted/denied operations and protected audit
   delivery before admitting traffic. Repeat separately for the next member.

**Rollback:** keep the affected member drained on failure. Use the still-accepted
peer within its capacity budget; restore the member through its tested provider/application
procedure. Never reset a token, discard pending state or revert shared CA history.

<a id="replica-updates"></a>

## How are approved key objects replicated or rotated?

1. Drain the affected member and authorize the key operation separately from CI.
2. Use the device's supported wrapping/backup procedure, with its scoped credentials:
   [Pico HSM](https://docs.picokeys.com/picohsm/backup-restore/) or the selected
   [YubiHSM interface](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-cmd-reference.html). [1][2]
3. Restore only permitted objects to each intended peer; verify the same public
   identity/attributes and reconcile application policy/state. Copied keys do not
   replicate issuance history or application sessions.
4. Refresh the independent offline backup. Prove readiness, authorization and
   recovery before returning that member to traffic.

A new issuer identity requires [CA rollover](hardware-migration.md), not merely copying
an object to more devices. Root signing, sensitive replication and device initialization
remain authorized ceremonies; no batch key-rotation installer is supplied.

<a id="routine-checks"></a>

## Which checks are repeated after maintenance?

| Check | Required evidence |
| --- | --- |
| Each device and consumer | Stable identity, permitted/denied operations and attributable audit events |
| VM/USB/provider failure | Failed backend excluded even while its port remains open; remaining service usable |
| VIP ownership/partition, when selected | Accepted ownership and reconnection behavior; no assumed session sharing |
| Pool capacity | Measured device and frontend headroom under selected failures/maintenance |
| Independence | Tier 0 operates with Tier 1/2 and the consuming secret service unavailable |
| Offline recovery | Original approved objects, attributes, policy and startup credentials restore without online replicas |

Retain results and review whether tier-owned `vm_instances`/placement still matches
real failure domains. Matching replica counts alone do not prove HA.

## References

Native interfaces checked 2026-11-08.

1. [YubiHSM provider and connector configuration](https://developers.yubico.com/yubihsm-shell/yubihsm-pkcs11.html).
2. [Pico HSM wrapped-key backup and restore](https://docs.picokeys.com/picohsm/backup-restore/).
3. [Ansible host listing and target limits](https://docs.ansible.com/projects/ansible/latest/cli/ansible-playbook.html).
