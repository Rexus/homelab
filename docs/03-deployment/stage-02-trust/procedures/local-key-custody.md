# Local key custody

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) for integration records.
Custody operations run in the authorized environment; key material never belongs in Git.

**Design:** [options A and B](../../../01-architecture/08-cryptography/03-hsm-selection.md).
**Prerequisites:** approved key purpose, host boundary, backup policy and custodian.
These procedures do not require replicated gateways or a published signing endpoint.

## Table of contents

- [Option A: software](#option-a-software)
- [Option B: single USB device](#option-b-single-usb-device)
- [Acceptance](#acceptance)
- [References](#references)

## Option A: software

Use [Step 1a: SoftHSM2](../step-1a-software-hsm.md) for the supplied no-hardware PKCS#11 path.
Ansible prepares its private storage, native middleware and token, then binds the retained identity
to `ca-1`. Initialization is explicit; ordinary runs preserve the token and its key. [1]

Software-token success proves interface behavior, not resistance to host compromise.
The token directory, serial/SPKI pins and separately held PINs belong in issuer recovery. SoftHSM
does not turn a USB pool into shared software state. A move to hardware requires the
[qualified key migration](../../../05-operations/03-cryptography/hardware-migration.md).

Existing encrypted key-file issuers retain their original profile and passphrase. Use
[Stage 2 action 10c](../README.md#10c-encrypted-key-file-profile) for its explicit fresh-key operation;
neither software profile changes an existing issuer identity automatically.

## Option B: single USB device

Follow [Step 1d: single USB device](../step-1d-single-usb.md) for hardware custody.
That branch owns device initialization, acceptance and the return to issuer setup.

## Acceptance

The intended consumer works, unauthorized operations fail, and a recovery custodian
can restore service without undocumented local material. Record the selected threat
model and outage tolerance, then return to
[issuer preparation](../README.md#step-1-prepare-issuer-and-key-custody).
Complete the selected runtime/key/CSR path before the hierarchy-signing step.

## References

1. [SoftHSM](https://www.softhsm.org/) (checked 2026-10-08)
