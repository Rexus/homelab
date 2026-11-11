# USB HSM service operations

<a id="usb-hsm-gateway-maintenance"></a>


Operate an already qualified [USB HSM deployment](../../03-deployment/stage-3-trust/step-1b-usb-hsm.md).
The `hsm` recipe manages native USB attachments, middleware/configuration and provider identity checks.
Device ceremonies, signing-application replication and routing/readiness retain their selected owners.
The [service design](../../01-architecture/08-cryptography/04-usb-hsm.md) owns their relationships.

**Run from:** generated Tier 0 on the authorized controller; checks use Ansible rather than guest login.
**Before starting:** actual application unit/provider, approved device/key records,
independent wrapping/recovery material and an accepted failure/capacity budget.

| Configuration in **`<prefix>-tier-0/`** | Owning task |
| --- | --- |
| `ansible/group_vars/hsm.yml`, inventory/host vars | Provider, physical serial, native middleware and assigned reader |
| `ansible/group_vars/hsm_remoting.yml` | Optional endpoints, SSH pins, source-restricted clients and original SPKI; [native remoting](../../03-deployment/stage-3-trust/procedures/pkcs11-remoting.md) |
| `ansible/group_vars/openbao_signing.yml`, independent `signing` environment | Optional API keys/clients and recovery; [signing API](../../03-deployment/stage-6-secrets/step-1d-openbao.md) |

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

1. Run [provider inspection](#device-identity). For optional remoting, run its
   [per-endpoint identity/signing check](../../03-deployment/stage-3-trust/procedures/pkcs11-remoting.md#5-check-signing-and-qualify-failure-behavior).
   The native listener is `hsm-remote-<pool-id>.service`; inspect it through Ansible if a transport
   probe fails. An accepted external application follows its own runtime runbook.
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

From **`<prefix>-tier-0/`**, verify the expected provider serial without login or key changes:

```bash
bash scripts/deploy.sh hsm --ansible-only --playbook deployment/hsm-inspect.yml
```

1. Compare the vendor/provider's reported stable serial/reader/token identity with
   the private project record; never identify a production device only by transient slot number. [1]
2. Compare expected key object IDs/labels, public fingerprints and operation attributes.
   Do not export private keys to perform this check.
3. Require the expected device before application startup. Stop and investigate on
   mismatch; reinitializing an unknown device is not a repair.

<a id="how-is-one-gateway-maintained"></a>

## How is one gateway maintained?

1. Select the maintenance condition: with a pool, verify another accepted member has capacity and
   drain this member through the application's native procedure. With a single gateway, approve
   the signing outage and preserve queued requests before stopping service. Do not claim continued
   signing availability in that branch. Preserve session state and independent backups in either case.
2. For **OS-baseline reconciliation only**, from Tier 0 select one inventory host
   and inspect the target list first: [3]

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   read -r -p 'Gateway inventory host (for example hsm-1): ' HSM_HOST
   ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/maintenance/hsm.yml -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml --limit "${HSM_HOST:?Select one gateway}" --list-hosts
   ```

   Stop unless exactly the intended connected gateway is selected. Add approved
   named-environment overlays last when used; never target the offline ceremony host.
3. Reconcile only that accepted baseline target:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

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
