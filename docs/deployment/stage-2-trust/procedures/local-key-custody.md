# Local key custody

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) for integration records.
Custody operations run in the authorized environment; key material never belongs in Git.

**Design:** [options A and B](../../../architecture/cryptography/hsm-selection.md).
**Prerequisites:** approved key purpose, host boundary, backup policy and custodian.
These procedures do not require replicated gateways or a published signing endpoint.

## Table of contents

- [Option A: software](#option-a-software)
- [Option B: single USB device](#option-b-single-usb-device)
- [Acceptance](#acceptance)
- [References](#references)

## Option A: software

1. Select the issuer application's native keystore or a compatible software provider.
   SoftHSM exposes PKCS#11 for environments without a hardware device. [1]
2. Isolate the service account and protect provider storage and backups. Use disposable
   keys for rehearsal; do not copy production root keys into a test token.
3. Follow the selected provider's installation and initialization procedure, then
   configure the issuer's supported provider interface.
4. Test the required signing mechanisms, authorization and independent restore.

Software-token success proves interface behavior, not resistance to host compromise.
The existing hsm setup can supply test hosts; token installation remains operator work.

## Option B: single USB device

Follow [Step 1d: single USB device](../step-1d-single-usb.md) for hardware custody.
That branch owns device initialization, acceptance and the return to issuer setup.

## Acceptance

The intended consumer works, unauthorized operations fail, and a recovery custodian
can restore service without undocumented local material. Record the selected threat
model and outage tolerance, then return to the [hierarchy step](../README.md#step-2-establish-the-certificate-hierarchy).

## References

1. [SoftHSM](https://www.softhsm.org/) (checked 2026-10-08)
