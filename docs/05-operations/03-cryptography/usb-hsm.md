# USB HSM service operations

<a id="usb-hsm-gateway-maintenance"></a>


Operate an already qualified [USB HSM deployment](../../03-deployment/stage-02-trust/step-1b-usb-hsm.md).
The `hsm` recipe manages native USB attachments, middleware/configuration and provider identity checks.
Device ceremonies, signing-application replication and routing/readiness retain their selected owners.
The [service design](../../01-architecture/08-cryptography/04-usb-hsm.md) owns their relationships.
An issuer-local device remains owned by `foundation`, not the pool's `hsm` state. Use the local-issuer
inspection branch below and [CA operations](certificate-authority.md) for that installation.

**Run from:** generated Tier 0 on the authorized controller; checks use Ansible rather than guest login.
**Before starting:** actual application unit/provider, approved device/key records,
independent wrapping/recovery material and an accepted failure/capacity budget.

| Configuration in **`<prefix>-tier-0/`** | Owning task |
| --- | --- |
| `ansible/group_vars/hsm.yml`, inventory/host vars | Provider, physical serial, native middleware and assigned reader |
| `ansible/group_vars/hsm_remoting.yml` | Optional endpoints, SSH pins, source-restricted clients and original SPKI; [native remoting](../../03-deployment/stage-02-trust/procedures/pkcs11-remoting.md) |
| `ansible/group_vars/openbao_signing.yml`, independent `signing` environment | Optional API keys/clients and recovery; [signing API](../../03-deployment/stage-06-secrets/step-11b-openbao.md) |

<a id="table-of-contents"></a>

## Tasks

- [Is a gateway healthy?](#health-checks)
- [How is the attached device verified?](#device-identity)
- [How is one gateway maintained?](#how-is-one-gateway-maintained)
- [How are approved key objects replicated or rotated?](#replica-updates)
- [How do I expand a single device into a pool?](#single-device-to-pool)
- [Which checks are repeated after maintenance?](#routine-checks)
- [References](#references)

<a id="health-checks"></a>

## Is a gateway healthy?

1. Run [provider inspection](#device-identity). For optional remoting, run its
   [per-endpoint identity/signing check](../../03-deployment/stage-02-trust/procedures/pkcs11-remoting.md#5-check-signing-and-qualify-failure-behavior).
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

For a **provider pool**, from **`<prefix>-tier-0/`**, verify the expected serial without login or key changes:

```bash
bash scripts/deploy.sh hsm --ansible-only --playbook deployment/hsm-inspect.yml
```

For the **device attached directly to `ca-1`**, run from **the same Tier 0 repository**, using its
original foundation address map and issuer service identity:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/hsm.yml \
  -e @ansible/group_vars/foundation.yml -e @ansible/group_vars/issuer.yml \
  -e hsm_inspect_group=issuing_ca ansible/playbooks/deployment/hsm-inspect.yml
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
2. For **baseline and provider reconciliation**, from Tier 0 select one inventory host
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

   The recipe reuses `deployment/hsm-gateways.yml`: it reconciles baseline, declared middleware,
   native configuration and serial inspection. Review those inputs before running it. Firmware,
   key ceremonies, application upgrades, traffic draining and VIP installation retain their own
   qualified procedures. Optional remoting needs its separate server/client reconciliation.
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

<a id="single-device-to-pool"></a>

## How do I expand a single device into a pool?

Keep the original issuer VM, database, certificates and signing key. The expansion adds provider
hosts and device copies; it does not create another CA or automatically make the issuer highly available.

**Starting point:** an accepted single-device issuer with independent recovery custody. This is a
useful review at [Stage 6 seal selection](../../03-deployment/stage-06-secrets/step-1c-seal-integration.md),
before adding consumers. A pool can also host independent keys; the same-key procedure below applies
only to an approved replicated signing domain, never arbitrary keys or a mixed-vendor wrapping domain.

**With two devices in total:** keep the original on `ca-1`. First deploy only `hsm-1` with the newly
restored replica and complete the guarded issuer cutover to it. Then remove the original device's
foundation attachment, add `hsm-2` with that device and qualify the second endpoint. The intermediate
single-remote-provider installation has no provider failover; retain the original local rollback path
until the first cutover passes.

1. **Recover the original material.** Capture the [current issuer recovery set](issuer-recovery.md).
   Retrieve the independently recorded SPKI SHA-256, object ID/label, attributes, original wrapped key
   and wrapping material. PicoHSM needs the original DKEK shares/passwords; YubiHSM needs the original
   wrap material and exportable-under-wrap objects selected at
   [first commissioning](../../03-deployment/stage-02-trust/step-1d-single-usb.md#yubihsm-first-key-recovery-choices).
   Stop if unavailable or if the original key/domain cannot support wrapped recovery; retain local
   custody or perform a separately approved new-key CA rollover. Do not reset the sole production
   device or replace its key to make the upgrade pass. [1][2][4]
2. **Restore and qualify each destination.** For PicoHSM follow [original-key restore](picohsm-replica.md).
   For YubiHSM follow its [native wrapped-object restore](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-backup-restore.html)
   with the retained wrap key, domains and delegated capabilities. Compare the original SPKI and
   required operation attributes, then sign/verify and test denials. Record each destination's own
   serial, reader and least-privilege credential; matching labels alone do not admit a replica. [4]
3. **Deploy independent hosts.** Follow [USB pool action 1](../../03-deployment/stage-02-trust/step-1b-usb-hsm.md#1-prepare-the-service-hosts).
   Initialize `hsm`; edit Terraform VM/node/USB inputs, inventory, IPs and per-device provider inputs.
   Remove single-device serial/reader values from global `hsm.yml` and put each provider's values in
   inventory/host vars; `-e @hsm.yml` overrides host vars if those values remain global.
   Plan before apply and require only the intended provider changes. Keep `ca-1` in foundation state.
   Select separate physical failure domains and enforce USB mobility restrictions. With two boards,
   initially declare only `hsm-1` with the new replica; keep the original on `ca-1` through guarded
   cutover. Move that original to `hsm-2` only afterwards, removing its foundation attachment before
   applying its HSM attachment. One USB device has one VM owner.
4. **Authorize transport.** Complete [native remoting](../../03-deployment/stage-02-trust/procedures/pkcs11-remoting.md)
   when selected: accepted SSH host pins, dedicated application SSH keys, source CIDRs/firewall,
   compatible p11-kit versions and the original SPKI pin on every endpoint. Base `hsm-inspect.yml`
   verifies serial visibility only; remoting adds public-key/signing checks. No listener is admitted
   by merely copying a serial into configuration.
   For the initial one-endpoint phase, explicitly select `hsm_remote_single_backend_transition: true`;
   after admitting `hsm-2`, set it false and reconcile/check the complete two-endpoint domain.
5. **Accept signing policy.** Keep exposed tokens dedicated to the selected signing key. SSH authorizes
   token access, while native HSM permissions and the application's existing issuance/API policy
   authorize operations. Deny administrative/export operations to online signing credentials; test
   unauthorized clients and forbidden requests. Keep the root offline and recovery credentials outside
   this pool. Do not add Vault seal objects to this single-signing-key remoting domain.
6. **Rehearse and cut over the consumer.** Follow the
   [same-key rebind](hardware-migration.md#same-key-provider-rebind) on an isolated restored copy first.
   Record the new module/engine, selected physical serial/object ID, PIN source and transport trust.
   A copied key on a new serial needs an explicit consumer change. During the approved pause, retain
   the current database/history, switch only the qualified binding and verify the original certificate
   and SPKI, issuance/CRL publication, restart and explicit alternate-endpoint selection. Routine
   deployment supplies no automatic live OpenXPKI rebind or replay of failed operations.
7. **Accept recovery or roll back.** Remove one token/host and prove the actual consumer reconnects or
   switches within the accepted outage budget; a transport probe using the survivor proves only that
   endpoint. Restore original keys/state without online replicas. On failure keep new endpoints drained
   and restore the retained original attachment/configuration through its owning state. Resume one
   issuer writer with the **latest** history; never roll back the database over post-cutover writes.
   Retire old access only after acceptance, retaining recovery material and obligations.

Use the same device family for a replicated wrapping domain. A Pico DKEK does not restore a YubiHSM
wrapped key. Cross-vendor transfer, application HA and seal compatibility require separate qualification.

Provider provisioning and selected remoting are automated. An already deployed issuer's immutable
configuration is not automatically upgraded by adding the pool; its consumer cutover still needs
the controlled application migration and live acceptance. Do not replace its bundle/binding in place.
Sessions are reestablished explicitly; more boards do not provide transparent replay or database HA.

## References

Native interfaces checked 2026-11-16. No live device, consumer-switching or recovery claim is made.

1. [YubiHSM provider and connector configuration](https://developers.yubico.com/yubihsm-shell/yubihsm-pkcs11.html).
2. [Pico HSM wrapped-key backup and restore](https://docs.picokeys.com/picohsm/backup-restore/).
3. [Ansible host listing and target limits](https://docs.ansible.com/projects/ansible/latest/cli/ansible-playbook.html).
4. [YubiHSM native wrapped-object backup and restoration](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-backup-restore.html).
