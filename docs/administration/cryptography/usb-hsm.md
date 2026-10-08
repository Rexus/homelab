# USB HSM gateway maintenance

Operate the selected [USB HSM gateway pattern](../../architecture/cryptography/usb-hsm.md)
after completing [deployment and acceptance](../../deployment/stage-2-trust/step-1b-usb-hsm.md).
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
- a harmless crypto operation succeeds with the expected key label or ID

Do not rely on slot visibility or object listing alone.

## Device identity

Keep one gateway bound to one expected local token:

- do not rely on transient slot numbering alone
- pin by stable reader, token label, serial, or similar identity when possible
- start gateway services only after the expected local token is present
- fail closed when the expected token is missing or mismatched

## Replica updates

When changing key material:

1. change it on the source-of-truth device
2. export under the approved wrap or backup process
3. restore to the other active device
4. refresh the offline backup device
5. verify labels, IDs, and expected objects before returning traffic

Use the selected device's supported process from the
[implementation references](../../deployment/stage-2-trust/step-1b-usb-hsm.md#references).
Do not treat the offline backup device as a routine active peer.

## Routine checks

Keep at least these checks in the normal maintenance cycle:

- verify gateway health from the edge load-balancer path
- verify local PKCS#11 access on each gateway host
- compare expected object inventory across active devices
- test restore from the offline backup on a controlled schedule
- review whether the current `vm_instances` layout still matches the load
