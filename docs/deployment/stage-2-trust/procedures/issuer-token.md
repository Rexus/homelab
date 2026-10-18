# Activate the software issuer token

Bind the separately signed public certificate to the already prepared private key.
This is a custodian operation after [software PKI installation](software-pki.md);
routine reconciliation never creates or imports a CA token.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) supplies the
approved configuration; commands here run on its independently managed issuer.
**Prerequisites:** prepared active backend, approved issuer/root certificates,
independently recorded fingerprints and the same recoverable signer/DataVault secrets.
Commands below run on the issuer with authorized local privilege.

## Contents

- [Verify identity](#verify-identity)
- [Import and check the token](#import-and-check-the-token)
- [Publish and test](#publish-and-test)
- [References](#references)

## Verify identity

```bash
openssl verify -CAfile /srv/openxpki/identity/root.pem /srv/openxpki/identity/issuer.pem
openssl x509 -in /srv/openxpki/identity/issuer.pem -noout -text -fingerprint -sha256
openssl x509 -in /srv/openxpki/identity/issuer.pem -pubkey -noout |
  openssl pkey -pubin -outform DER | openssl dgst -sha256
openssl pkey -in /srv/openxpki/keys/issuer.pem -pubout -outform DER |
  openssl dgst -sha256
```

The two public-key hashes must match. Enter the key passphrase interactively;
do not export or print the private key. Check approved subject, validity,
CA:true/pathlen:0, signing usages and publication URLs. Any mismatch stops activation.

## Import and check the token

The supplied bundle registers a native CLI public key and installs its protected
private counterpart at `/srv/openxpki/keys/cli.pem`. It is a privileged
administrative credential, not a requester login. Limit it to the CA service/root,
include it in encrypted recovery and audit its use. Current OpenXPKI uses this
authentication for protected and out-of-realm commands. [1]

Inspect `oxi --help` and `oxi token add --help` for the approved package
revision. With the default realm and paths:

```bash
sudo -u openxpki oxi --auth-key /srv/openxpki/keys/cli.pem certificate add \
  --cert /srv/openxpki/identity/root.pem
sudo -u openxpki oxi --auth-key /srv/openxpki/keys/cli.pem token add \
  --realm infrastructure --type certsign --cert /srv/openxpki/identity/issuer.pem
sudo -u openxpki oxi --auth-key /srv/openxpki/keys/cli.pem token list --realm infrastructure
```

The crypto configuration references the existing filesystem key. Do not add
`--key` to import another copy into the database, or create a second root realm
with online root-key access. If an alias already exists, inspect it; this is not
a repeatable import script. Preserve the token alias/identifier in recovery records.

Use the returned alias with the product's `get_token_info` API to verify signer
readiness. The symmetric DataVault comes from the separately protected 32-byte
master secret; it needs no fabricated self-signed DataVault certificate. [1]

## Publish and test

```bash
sudo -u openxpki oxi --auth-key /srv/openxpki/keys/cli.pem workflow create \
  --realm infrastructure --type crl_issuance
sudo -u openxpki oxi --auth-key /srv/openxpki/keys/cli.pem workflow create \
  --realm infrastructure --type ca_publish
systemctl status openxpki-crl.timer
```

Inspect both workflows through completion; enqueueing is not successful publication.
The native CA publisher writes PEM/DER `issuer.crt`/`issuer.cer`.
Copy only the signed offline root objects as `root.cer`/`root.crl` beneath
`/srv/openxpki/public/`. The native CRL publisher writes DER `issuer.crl`.
Confirm HTTP downloads, signatures, freshness and independent stale-CRL alerts.

Log in as the requester, upload an allowed host CSR and obtain a second person's
approval. Reject self-approval, out-of-scope SANs, wildcard names, CA profiles and
unapproved keys. Inspect the issued certificate, then revoke it, publish a new CRL
and prove rejection at an enforcing client. Renew with another approved CSR.
Replace bootstrap portal TLS and complete
[recovery acceptance](../../../administration/cryptography/issuer-recovery.md)
before production. A ready token alone is not acceptance.

## References

Source checked 2026-10-18.

1. [OpenXPKI CLI authentication, token import, DataVault and CRL workflow](https://github.com/openxpki/openxpki-config/blob/community/QUICKSTART.md)
