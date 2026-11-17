# Existing native clca software root

Use this compatibility path only for an **existing pre-kit clca root instance**. Keep its accepted
tool revision, key, database and policy. For a fresh root use the [ORCA kit](offline-root.md#first-visit).
Do not rerun key generation/initialization or copy fresh policy over an existing CA.

**Work on:** the separate offline ceremony computer, with retained encrypted working storage and
independent recovery. Never execute these commands on bootstrap or `ca-1`.
**Working repository:** `<prefix>-tier-0` supplies references; authoritative state stays offline.

## Contents

- [Open the retained instance](#prepare-the-instance)
- [Sign a subordinate](#sign-a-subordinate)
- [Publish and preserve state](#publish-and-preserve-state)
- [References](#references)

<a id="prepare-the-instance"></a>
<a id="create-the-root-once"></a>

## Open the retained instance

On **the offline computer**, set the real retained tool/instance paths and enter that instance:

```bash
export CLCA=/media/tools/clca/bin/clca
export INSTANCE=/media/encrypted/root-ca
umask 077
cd "$INSTANCE"
openssl x509 -in ca/cacert.pem -noout -subject -dates -fingerprint -sha256
```

Compare the original fingerprint with the independent record; verify the complete recovered database,
serial/CRL state and original policy. Use the original native tool revision. The new kit does not
silently adopt an instance without its binding/ceremony records.

## Sign a subordinate

Receive only the approved issuer/FreeIPA CSR and an independently recorded subject/key fingerprint.
On **the offline computer**, with the transfer media mounted at the actual selected path:

```bash
openssl req -in /media/transfer/subordinate.csr -verify -noout -text
openssl req -in /media/transfer/subordinate.csr -pubkey -noout |
  openssl pkey -pubin -outform DER | openssl dgst -sha256
```

Compare that identity and key with the independent approval. Require the original `level2` profile,
CA:true/pathlen:0, keyCertSign/cRLSign, approved publication URLs and validity within the root's
remaining life. From **that same retained instance**, only after approval:

```bash
flock --nonblock "$INSTANCE/ceremony.lock" "$CLCA" certify --profile level2 \
  --out /media/transfer/subordinate.pem /media/transfer/subordinate.csr
openssl verify -CAfile ca/cacert.pem /media/transfer/subordinate.pem
openssl x509 -in /media/transfer/subordinate.pem -noout -text -fingerprint -sha256
```

Verify the certificate's public key matches the approved CSR. Reject an existing output instead of
replacing it. Later FreeIPA signing uses this same root; it does not initialize another root.

<a id="publish-and-preserve-state"></a>

## Publish and preserve state

On **the offline computer**, from **the retained root instance**:

```bash
flock --nonblock "$INSTANCE/ceremony.lock" "$CLCA" issuecrl
openssl crl -in crl/ca.crl -noout -issuer -lastupdate -nextupdate
openssl crl -in crl/ca.crl -outform DER -out /media/transfer/root.crl
openssl x509 -in ca/cacert.pem -outform DER -out /media/transfer/root.cer
install -m 0644 ca/cacert.pem /media/transfer/root.pem
```

Return only signed public objects. Publish them at the URLs in the retained CA policy and verify
signatures/freshness from consumers. Root trust is established independently of that download.

After every change, on **encrypted working storage**, create the complete native archive:

```bash
ROOT_BACKUP="${INSTANCE}-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
flock --nonblock "$INSTANCE/ceremony.lock" "$CLCA" backup "$ROOT_BACKUP"
tar -tzf "$ROOT_BACKUP"
```

Require configuration, `private/cakey.pem`, CA database and CRL state. Native clca archives are not
encrypted. Encrypt to the independent recovery recipient before copying off working storage; verify
a separate offline restore without publishing its divergent history. Retain the current instance and
backups together under controlled custody. Never put the plaintext archive on public transfer media.

Return to [Stage 2 certificate installation](../README.md#step-12-install-public-certificates-and-start-the-prepared-backend)
or [FreeIPA completion](../../stage-05-identity/procedures/freeipa.md#step-3-complete-the-primary-and-replica).
For a newly created kit-managed root, [ORCA operations](../../../05-operations/03-cryptography/offline-root.md)
own the on-demand commands and encrypted backup path.

## References

1. [Native clca lifecycle and backup](https://github.com/openxpki/clca/blob/d560135cf4bbdc1916fa4c5545012085b96d4a21/README.md).
