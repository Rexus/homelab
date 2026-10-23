# Software root ceremony

Use the [offline custody procedure](offline-root.md) with native clca and the
Tier 0 [configuration examples](../../../../tier-0/templates/offline-root/).
This is an authorized manual ceremony, not a connected Ansible deployment.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) supplies templates;
all authoritative state and ceremony commands stay on the separate offline system.
**Prerequisites:** trusted offline Linux system, approved clca/OpenSSL artifacts,
encrypted working media, independent encrypted backup media and two custodians.
Rehearse with disposable material before creating the real root.
Prepare the tool checkout on Linux and preserve LF line endings in Bash/configuration
files when transferring media from Windows.

## Contents

- [Prepare the instance](#prepare-the-instance)
- [Create the root once](#create-the-root-once)
- [Sign a subordinate](#sign-a-subordinate)
- [Publish and preserve state](#publish-and-preserve-state)
- [References](#references)

## Prepare the instance

Transfer a verified, approved clca revision with its supporting files to offline
media. Record commit and artifact hashes in the ceremony record; a moving branch
is not an artifact pin. These native configuration files define software RSA-4096
root custody, SHA-384, a root path length of one and subordinate path length zero.
They deliberately do not define a leaf-issuance profile.

On the offline system, set these absolute paths to the actual mounted media:

```bash
export CLCA=/media/tools/clca/bin/clca
export INSTANCE=/media/encrypted/root-ca
export TEMPLATES=/media/tools/tier-0/templates/offline-root
umask 077
install -d -m 0700 "$INSTANCE/etc"
install -m 0600 "$TEMPLATES/clca.cfg.example" "$INSTANCE/etc/clca.cfg"
install -m 0600 "$TEMPLATES/openssl.cnf.example" "$INSTANCE/etc/openssl.cnf"
cd "$INSTANCE"
```

Replace organization, root common name and both publication URLs in
`etc/openssl.cnf`. Approve the 10-year root, 5-year subordinate and 90-day root
CRL defaults or change them before creation. Schedule root ceremonies at least
every 60 days, with independent alerts well before the current CRL expires.
Keep subordinate expiry inside root expiry, allowing time for rollover.

Do not rerun preparation over an existing instance. It would replace its policy.
Reject any remaining `REPLACE` or `.invalid` values before continuing.

## Create the root once

Review the mounted volume identity and confirm that no authoritative instance
already exists. clca prompts for the passphrase; keep it out of shell history.

```bash
flock --nonblock "$INSTANCE/ceremony.lock" "$CLCA" genkey
flock --nonblock "$INSTANCE/ceremony.lock" "$CLCA" initialize
openssl x509 -in ca/cacert.pem -noout -subject -issuer -dates -fingerprint -sha256
openssl x509 -in ca/cacert.pem -noout -text
```

Confirm CA:true, pathlen:1, critical keyCertSign/cRLSign and the approved identity.
Record the fingerprint independently. Never delete state in response to an
initialization refusal; investigate or restore the existing instance.

## Sign a subordinate

Receive only the issuer/FreeIPA CSR and an independently approved identity/public
key record. Use controlled media, not a network connection to the root.

```bash
openssl req -in /media/transfer/subordinate.csr -verify -noout -text
openssl req -in /media/transfer/subordinate.csr -pubkey -noout |
  openssl pkey -pubin -outform DER | openssl dgst -sha256
flock --nonblock "$INSTANCE/ceremony.lock" "$CLCA" certify --profile level2 \
  --out /media/transfer/subordinate.pem /media/transfer/subordinate.csr
openssl verify -CAfile ca/cacert.pem /media/transfer/subordinate.pem
openssl x509 -in /media/transfer/subordinate.pem -noout -text -fingerprint -sha256
```

Compare the certificate's public key with the approved CSR, verify CA:true,
pathlen:0, usages, validity and root CDP/AIA URLs. The profile ignores requested
extensions instead of trusting a submitted CA profile. Approve each sibling CA
separately; no root key or CA database enters the return package.

## Publish and preserve state

```bash
flock --nonblock "$INSTANCE/ceremony.lock" "$CLCA" issuecrl
openssl crl -in crl/ca.crl -noout -issuer -lastupdate -nextupdate
openssl crl -in crl/ca.crl -outform DER -out /media/transfer/root.crl
openssl x509 -in ca/cacert.pem -outform DER -out /media/transfer/root.cer
```

Publish only signed public objects at the exact configured URLs. Validate their
signatures and freshness from consumers. HTTP publication is acceptable for signed
CA/CRL objects when signatures are checked; root trust is established independently,
never by trusting the first downloaded certificate.

After every state change, run `clca backup` to encrypted working storage, encrypt
that archive for a separately held recovery recipient and copy it off-device.
The native archive is **not** encrypted by clca. [1] Restore a copy on an isolated
offline system and verify certificate identity, index, serial/CRL counters and
ability to issue a CRL before closing the ceremony. Do not issue competing live
histories from two copies. Record next ceremony, transfer hashes and custodians.

## References

Sources checked 2026-10-18.

1. [clca lifecycle, profiles, serialization and backup](https://github.com/openxpki/clca/blob/master/README.md)
2. [Native clca instance configuration](https://github.com/openxpki/clca/blob/master/etc/clca.cfg)
3. [Native OpenSSL profile shape](https://github.com/openxpki/clca/blob/master/etc/openssl.cnf)
