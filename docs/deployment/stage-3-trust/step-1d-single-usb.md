# Step 1d: Single USB key device

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) for issuer/device integration.
Device initialization and custody are operator procedures, not a supplied installer.

**Branch from:** [Step 1](README.md#step-1-prepare-issuer-and-key-custody), before creating keys.
**Change:** use one host-local hardware device instead of a software key store.
**Return:** [Step 2](README.md#step-2-establish-the-certificate-hierarchy) for intermediate signing and issuer verification.
**Design:** [single-device custody](../../architecture/cryptography/hsm-selection.md#options-a-d).

This option protects a selected root or issuer key without deploying gateway replicas.
It does not provide host/device failover. For an offline root, the entire ceremony
remains offline; online issuer use does not create a route to root custody.

## Deployment

1. Select the device, supported middleware and consumer integration. Confirm the
   required mechanisms and backup policy before creating non-recoverable keys.
2. Prepare a dedicated authorized host, attach the device locally and follow its
   manufacturer's initialization and custodian procedure. [1][2]
3. Configure the application for that device identity and permitted operations.
   Keep custody credentials outside inventory and Git.
4. Establish the authorized recovery arrangement and rehearse a restore with test
   keys. Measure the interruption while the sole active device is unavailable.

## Return to the main path

After signing, denied-operation and restore tests pass, return to
[Step 2](README.md#step-2-establish-the-certificate-hierarchy) for the intermediate
certificate ceremony and issuer acceptance. Replicated
[USB gateways](step-1b-usb-hsm.md) are a separate service pattern, not a required next step.

When Vault, signing workflows or other selected consumers require higher throughput
or continued online operations during failures, use that replicated branch before accepting their new
availability contract. Extend only the selected online key/provider arrangement;
do not bring offline root custody online or assume a backup is an automatic failover device.

## References

1. [Pico HSM capability map and device procedures](https://docs.picokeys.com/picohsm/features/)
2. [YubiHSM PKCS#11 integration](https://developers.yubico.com/yubihsm-shell/yubihsm-pkcs11.html)
