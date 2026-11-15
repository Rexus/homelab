# Restore the original key onto another PicoHSM

Add a recovery or provider replica to the [USB HSM deployment](usb-hsm.md). Preserve the existing
signing identity using the original DKEK and wrapped key. This does not replicate the CA database
or introduce automatic application failover.

**Working repository:** `<prefix>-tier-0` for provider inputs and later IaC deployment.
**Run device commands on:** the protected ceremony host, with **only the new destination board** attached.
Keep the original production device serving its existing owner.

> **One-board learning test:** before this device has been accepted as a live issuer, the original
> board may be the destination of a destructive backup/restore round trip. First retain and independently
> verify the complete recovery set outside that board and controller. Do not use this exception on a
> live signing device. It proves restoration on this board, not recovery after losing it; qualify a
> separate compatible board when one becomes available. PicoHSM supports either destination. [1]

## Contents

- [1. Retrieve the original recovery set](#1-retrieve-the-original-recovery-set)
- [2. Prepare the destination](#2-prepare-the-destination)
- [3. Initialize only the destination](#3-initialize-only-the-destination)
- [4. Import the original DKEK](#4-import-the-original-dkek)
- [5. Restore the wrapped signing key](#5-restore-the-wrapped-signing-key)
- [6. Compare the public identity](#6-compare-the-public-identity)
- [7. Test signing and admit the replica](#7-test-signing-and-admit-the-replica)
- [References](#references)

## 1. Retrieve the original recovery set

Obtain the original encrypted DKEK share, its separately held password, wrapped issuer key,
public SPKI and recorded fingerprint. Use the same share count as the original domain.
The examples below use one share and key ID `01` from
[first-device commissioning](../../03-deployment/stage-02-trust/procedures/picohsm.md).

If the original material is unavailable, stop. A new DKEK or a newly generated signing key does
not restore the existing issuer. PicoHSM and YubiHSM wrapping formats are different.

## 2. Prepare the destination

Follow [commissioning actions 1–5](../../03-deployment/stage-02-trust/procedures/picohsm.md#1-select-the-board-and-firmware)
for the new board's firmware, middleware and explicit reader/slot selection.
**Skip first-device actions 6 and 9:** retain the original share and key instead of creating new ones.

In the temporary root ceremony shell, set the retained-file locations. Example paths below are
private copies restored from independent custody; replace them with their real absolute paths:

```bash
read -r -e -p 'Original encrypted DKEK share file: ' PICO_DKEK_FILE
read -r -e -p 'Original wrapped issuer key file: ' PICO_WRAPPED_FILE
read -r -e -p 'Original public SPKI DER file: ' PICO_ORIGINAL_SPKI
```

Compare the original public file's digest with the independent record:

```bash
openssl dgst -sha256 "$PICO_ORIGINAL_SPKI"
```

## 3. Initialize only the destination

> **Danger:** this destroys the selected board's contents. Verify its physical identity, reader and
> displayed serial. The original production board must not be attached to this ceremony host.
> For the one-board pre-production test, this deliberately erases the only on-device key: proceed
> only with the verified original recovery set and the explicit intent to test restoration.

In the same ceremony shell, choose the destination's own SO-PIN and user PIN:

```bash
(
  read -r -s -p 'Destination SO-PIN (16 hexadecimal characters): ' PICO_SO_PIN; printf '\n'
  read -r -s -p 'Destination user PIN (6-16 characters): ' PICO_USER_PIN; printf '\n'
  export PICO_SO_PIN PICO_USER_PIN
  sc-hsm-tool --reader "$PICO_READER" --initialize --dkek-shares 1 \
    --label issuer --so-pin env:PICO_SO_PIN --pin env:PICO_USER_PIN
)
```

The device serial stays its own identity. Do not copy the original board's serial into this board's inputs.

## 4. Import the original DKEK

Run in the same ceremony shell, providing the **original share password** when asked:

```bash
sc-hsm-tool --reader "$PICO_READER" --import-dkek-share "$PICO_DKEK_FILE"
sc-hsm-tool --reader "$PICO_READER"
```

Require no pending shares and the same recorded DKEK check value as the original device.
For a multiple-share domain, import every required original share under its custodian's control. [1]

## 5. Restore the wrapped signing key

Inspect the destination's current objects:

```bash
pkcs15-tool --reader "$PICO_READER" --dump
```

Select an unused **decimal internal key reference**, for example `1` on a blank destination.
Do not use `--force` to replace an existing object:

```bash
read -r -p 'Unused destination Key ref (decimal; for example 1): ' PICO_RESTORE_REFERENCE
sc-hsm-tool --reader "$PICO_READER" --unwrap-key "$PICO_WRAPPED_FILE" \
  --key-reference "$PICO_RESTORE_REFERENCE"
```

Enter the destination's user PIN. The wrapped record restores the original PKCS#11 ID/metadata;
the internal destination reference is selected separately. [1][2]

## 6. Compare the public identity

Re-list slots after initialization and select the destination's current slot:

```bash
pkcs11-tool --module "$PICO_MODULE" --list-slots
read -r -p 'Destination PKCS#11 slot ID (for example 0x0): ' PICO_SLOT
pkcs11-tool --module "$PICO_MODULE" --slot "$PICO_SLOT" \
  --read-object --type pubkey --id 01 --output-file "$PICO_CUSTODY/replica-spki.der"
openssl dgst -sha256 "$PICO_CUSTODY/replica-spki.der"
cmp -- "$PICO_ORIGINAL_SPKI" "$PICO_CUSTODY/replica-spki.der"
```

`cmp` must exit successfully without output. A mismatch blocks admission; do not generate a replacement key.

## 7. Test signing and admit the replica

For the example P-384 key, sign a disposable SHA-384 digest and verify it with the retained public key:

```bash
printf '%s\n' 'PicoHSM replica acceptance' > "$PICO_CUSTODY/probe.txt"
openssl dgst -sha384 -binary "$PICO_CUSTODY/probe.txt" > "$PICO_CUSTODY/probe.sha384"
pkcs11-tool --module "$PICO_MODULE" --slot "$PICO_SLOT" --login --sign \
  --mechanism ECDSA --id 01 --signature-format openssl \
  --input-file "$PICO_CUSTODY/probe.sha384" --output-file "$PICO_CUSTODY/probe.sig"
openssl pkey -pubin -inform DER -in "$PICO_ORIGINAL_SPKI" -out "$PICO_CUSTODY/issuer-public.pem"
openssl dgst -sha384 -verify "$PICO_CUSTODY/issuer-public.pem" \
  -signature "$PICO_CUSTODY/probe.sig" "$PICO_CUSTODY/probe.txt"
```

Require **Verified OK**. Keep the device out of service on failure. Exit the root ceremony shell:

```bash
exit
```

Record the **new board's** serial/reader and the **original key's** fingerprint in its own provider inputs.
Continue with [single device to provider pool](usb-hsm.md#single-device-to-pool), or retain the board
offline as a tested recovery device. Keep its credentials under its own custody.
For a one-board test, retain its original device serial and record the limited test scope instead.
Finish the [ceremony cleanup](../../03-deployment/stage-02-trust/procedures/picohsm.md#11-retain-custody-and-attach-the-issuer)
before returning the selected host to normal deployment work.

## References

Sources checked 2026-11-15. Cross-board restoration and live admission require physical qualification.

1. [PicoHSM original DKEK and key-reference restore semantics](https://github.com/polhenarejos/pico-hsm/blob/master/doc/backup-and-restore.md).
2. [OpenSC native SmartCard-HSM operations](https://manpages.debian.org/bookworm/opensc/sc-hsm-tool.1.en.html).
3. [OpenSC ECDSA signature formats](https://manpages.debian.org/bookworm/opensc/pkcs11-tool.1.en.html).
