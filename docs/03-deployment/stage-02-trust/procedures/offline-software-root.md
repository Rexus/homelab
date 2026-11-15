# Software root ceremony

Use the [offline custody procedure](offline-root.md) with native clca and the
Tier 0 [configuration examples](../../../../tier-0/templates/offline-root).
This is an authorized manual ceremony, not a connected Ansible deployment.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) supplies templates;
all authoritative state and ceremony commands stay on the separate offline system.
**Prerequisites:** trusted offline Linux system, approved clca/OpenSSL artifacts,
encrypted working media, independent encrypted backup media and two custodians.
Rehearse with disposable material before creating the real root.
Prepare the tool checkout on Linux and preserve LF line endings in Bash/configuration
files when transferring media from Windows.

**Two visits:** Stage 2 Step 1 prepares/creates this root and closes custody with a verified backup.
Step 11 restores that **same** instance to sign `ca-1`'s CSR. A PicoHSM selected for `ca-1` changes
the issuer's key storage, not this root's software custody.

## Contents

- [1. Prepare the instance](#prepare-the-instance)
- [2. Create the root once](#create-the-root-once)
- [3. Sign a subordinate](#sign-a-subordinate)
- [4. Publish and preserve state](#publish-and-preserve-state)
- [References](#references)

<a id="prepare-the-instance"></a>

## 1. Prepare the instance

**Existing root, including the Stage 5 FreeIPA ceremony:** restore the approved instance from custody.
On **the offline ceremony host**, set its existing tool/instance paths and enter that instance:

```bash
export CLCA=/media/tools/clca/bin/clca
export INSTANCE=/media/encrypted/root-ca
umask 077
cd "$INSTANCE"
```

Verify the recorded root fingerprint and recovered state. Skip template copying and root creation;
continue at [Sign a subordinate](#sign-a-subordinate). Never initialize a second root for the identity CA.

Display the recovered identity on **the offline ceremony host** and compare it with the independent record:

```bash
openssl x509 -in "$INSTANCE/ca/cacert.pem" -noout -subject -dates -fingerprint -sha256
```

**New root only:** continue below with the approved initial-creation ceremony.

Transfer a verified, approved clca revision with its supporting files to offline
media. Include its `bin/` and `lib/` directories, the Tier 0 `templates/offline-root/` directory,
and Bash, GNU core utilities, OpenSSL, Perl, `flock` and tar on the approved offline Linux image.
The native script calls Perl even when secret sharing/provisioning are unused. [1]
Record commit and artifact hashes in the ceremony record; a moving branch
is not an artifact pin. These native configuration files define software RSA-4096
root custody, SHA-384, a root path length of one and subordinate path length zero.
They deliberately do not define a leaf-issuance profile.

On the offline system, set these absolute paths to the actual mounted media:

Run on **the authorized offline ceremony host**.

```bash
export CLCA=/media/tools/clca/bin/clca
export INSTANCE=/media/encrypted/root-ca
export TEMPLATES=/media/tools/tier-0/templates/offline-root
umask 077
(
  set -e
  test -x "$CLCA"
  test ! -e "$INSTANCE/etc/clca.cfg"
  test ! -e "$INSTANCE/etc/openssl.cnf"
  install -d -m 0700 "$INSTANCE/etc"
  install -m 0600 "$TEMPLATES/clca.cfg.example" "$INSTANCE/etc/clca.cfg"
  install -m 0600 "$TEMPLATES/openssl.cnf.example" "$INSTANCE/etc/openssl.cnf"
)
cd "$INSTANCE"
```

Use the actual mounted paths, without spaces for the native clca script. Require every preparation
command to succeed before continuing. In **`$INSTANCE/etc/openssl.cnf`**, edit these fields:

| Section / field | Example value | Source of the real value |
| --- | --- | --- |
| `[root_dn] organizationName` | `Example Private Cloud` | Approved organization identity |
| `[root_dn] commonName` | `Example Offline Root CA` | Approved root name, retained across later ceremonies |
| `[level2_ext] crlDistributionPoints` | `URI:http://ca.internal.example.com/download/root.crl` | Chosen root-CRL publication endpoint |
| `[level2_ext] authorityInfoAccess` | `caIssuers;URI:http://ca.internal.example.com/download/root.cer` | Chosen root-certificate publication endpoint |

The examples can use the future issuer's publication directory. At the first root-only checkpoint,
retain its public objects on transfer media. Publish them when Stage 2 Step 12 installs that endpoint,
then verify retrieval before accepting issuance. An existing independent publication service can
serve them immediately. The endpoint must remain usable for later FreeIPA consumers too.

Approve the 10-year root, 5-year subordinate and 90-day root
CRL defaults or change them before creation. Schedule root ceremonies at least
every 60 days, with independent alerts well before the current CRL expires.
Keep subordinate expiry inside root expiry, allowing time for rollover.

Do not rerun preparation over an existing instance. It would replace its policy.
Reject any remaining `REPLACE` or `.invalid` values before continuing.

<a id="create-the-root-once"></a>

## 2. Create the root once

Review the mounted volume identity and confirm that no authoritative instance
already exists. clca prompts for the passphrase; keep it out of shell history.

Run on **the authorized offline ceremony host**.

```bash
flock --nonblock "$INSTANCE/ceremony.lock" "$CLCA" genkey
flock --nonblock "$INSTANCE/ceremony.lock" "$CLCA" initialize
openssl x509 -in ca/cacert.pem -noout -subject -issuer -dates -fingerprint -sha256
openssl x509 -in ca/cacert.pem -noout -text
```

Confirm CA:true, pathlen:1, critical keyCertSign/cRLSign and the approved identity.
Record the fingerprint independently. Never delete state in response to an
initialization refusal; investigate or restore the existing instance.

**First visit, no CSR yet:** continue at [Publish and preserve state](#publish-and-preserve-state),
retain a verified independent recovery copy, then return to
[Stage 2 Step 2](../README.md#step-2-initialize-the-issuer-inputs).
Leave the root offline while the online issuer and its CSR are prepared. At Step 11,
restore this same instance and continue below without key generation or initialization.

<a id="sign-a-subordinate"></a>

## 3. Sign a subordinate

Receive only the issuer/FreeIPA CSR and an independently approved identity/public
key record. Use controlled media, not a network connection to the root.

Run on **the authorized offline ceremony host**.

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

<a id="publish-and-preserve-state"></a>

## 4. Publish and preserve state

Run on **the authorized offline ceremony host**.

```bash
flock --nonblock "$INSTANCE/ceremony.lock" "$CLCA" issuecrl
openssl crl -in crl/ca.crl -noout -issuer -lastupdate -nextupdate
openssl crl -in crl/ca.crl -outform DER -out /media/transfer/root.crl
openssl x509 -in ca/cacert.pem -outform DER -out /media/transfer/root.cer
install -m 0644 ca/cacert.pem /media/transfer/root.pem
```

The transfer volume must already be mounted at the selected path. `root.pem` is the public PEM
input used by Stage 2's certificate installer; `root.cer` and `root.crl` are the DER publication objects.
After signing, include `subordinate.pem` from action 3 in that public return package.

Publish signed public objects at the exact configured URLs once their endpoint exists. Validate their
signatures and freshness from consumers. HTTP publication is acceptable for signed
CA/CRL objects when signatures are checked; root trust is established independently,
never by trusting the first downloaded certificate.

After every state change, create the native archive on **the offline host's encrypted working storage**:

```bash
ROOT_BACKUP="${INSTANCE}-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
flock --nonblock "$INSTANCE/ceremony.lock" "$CLCA" backup "$ROOT_BACKUP"
tar -tzf "$ROOT_BACKUP"
```

Require the archive listing to contain configuration, `private/cakey.pem`, CA database and CRL state.
Encrypt that archive for a separately held recovery recipient and copy it off-device.
The native archive is **not** encrypted by clca. [1] Restore a copy on an isolated
offline system and verify certificate identity, index, serial/CRL counters and
ability to issue a CRL before closing the ceremony. Do not issue competing live
histories from two copies. Record next ceremony, transfer hashes and custodians.

Return with public signed objects to [software PKI activation](software-pki.md#sign-and-activate)
or [FreeIPA completion](../../stage-05-identity/procedures/freeipa.md#step-3-complete-the-primary-and-replica),
whichever requested this ceremony. Keep the authoritative root instance offline.
If this was the first root-only visit, return to [Stage 2 Step 2](../README.md#step-2-initialize-the-issuer-inputs)
instead; there is no signed subordinate certificate to install yet.

## References

Sources checked 2026-10-18.

1. [clca lifecycle, profiles, serialization and backup](https://github.com/openxpki/clca/blob/master/README.md)
2. [Native clca instance configuration](https://github.com/openxpki/clca/blob/master/etc/clca.cfg)
3. [Native OpenSSL profile shape](https://github.com/openxpki/clca/blob/master/etc/openssl.cnf)
