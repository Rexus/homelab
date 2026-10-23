# USB HSM gateway maintenance

Operate the selected [USB HSM gateway pattern](../../architecture/cryptography/usb-hsm.md)
after completing [deployment and acceptance](../../deployment/stage-3-trust/step-1b-usb-hsm.md).
These are operator checks, not automated device-lifecycle recipes.

The protected Tier 0 runner may maintain gateway VMs and software. Key
initialization, sensitive key replication, and root-CA signing require
separate authorized ceremonies; they are not routine CI jobs.

## Table of contents

- [Health checks](#health-checks)
- [Device identity](#device-identity)
- [Replica updates](#replica-updates)
- [Routine checks](#routine-checks)

## Health checks

Treat a gateway as healthy only when:

- the service is reachable
- login and session setup work against the expected local token
- a policy-safe readiness operation succeeds with the expected key label or ID

Do not rely on slot visibility or object listing alone.
Keep probe privileges scoped; a proxy or health identity is not an unrestricted
signing caller. Basic TCP checks only establish listener reachability.

For E3, device/key readiness removes an unusable replica from backend selection.
VIP ownership tracks usable frontend/backend capacity separately: loss of a
local token need not discard a frontend that can still reach the other healthy
replica. Follow the application's supported HA and session model, not generic retries.

## Device identity

Keep one gateway bound to one expected local token:

- do not rely on transient slot numbering alone
- pin by stable reader, token label, serial, or similar identity when possible
- start gateway services only after the expected local token is present
- fail closed when the expected token is missing or mismatched

## Replica updates

When changing key material:

1. Drain the affected replica according to the selected application/session model.
2. Change the approved material on the source-of-truth device and export through
   the supported wrapping or backup process.
3. Restore permitted objects to the other device and reconcile application policy/state.
4. Refresh the independent offline backup.
5. Verify key identity, authorization, application state and readiness before returning traffic.

Use the selected device's supported process from the
[implementation references](../../deployment/stage-3-trust/step-1b-usb-hsm.md#references).
Do not treat the offline backup device as a routine active peer.

## Routine checks

Keep at least these checks in the normal maintenance cycle:

- verify gateway health through the selected private Tier 0 signing path
- verify local PKCS#11 access on each gateway host
- compare expected object inventory across active devices
- repeat host-loss, USB-loss and VIP-owner/partition tests after relevant changes
- verify Tier 0 operation while Tier 1/2 services are unavailable
- test restore from the offline backup on a controlled schedule
- review whether the current `vm_instances` layout still matches the load
- measure pool capacity and VIP/proxy capacity separately, including peak traffic
  with the accepted device/host losses or maintenance drain
