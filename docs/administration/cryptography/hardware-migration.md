# Move signing custody to hardware

Prefer a new HSM-generated issuing key and controlled CA rollover. Moving an
existing software key into hardware cannot erase earlier software copies or prove
that it was never exported. Keep the offline root and online issuer independent.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** accepted software deployment, tested recovery and selected
[USB/network custody](../../architecture/cryptography/hsm-selection.md). Hardware signing is a separately qualified
integration, not an enabled feature of the software recipe.

## Contents

- [Choose the migration](#choose-the-migration)
- [Qualify and roll over](#qualify-and-roll-over)
- [Retire and recover](#retire-and-recover)
- [References](#references)

## Choose the migration

| Choice | Meaning |
| --- | --- |
| New HSM key and issuer certificate | Preferred: new provenance, explicit trust/issuance rollover |
| Import old key, if supported and approved | Continuity only; preserve history of software exposure |
| Move root custody | Separate offline ceremony and trust-anchor rollover; never a side effect of issuer migration |
| Change DataVault protection | Separate encrypted-data migration; do not replace its secret with an HSM PIN |

Select mechanisms and capacity from the vendor's supported interface and
[measured performance](../../reference/yubihsm-performance.md), not just key-size
labels. Qualify the exact device, firmware, connector, OpenSSL engine/provider and
OpenXPKI backend combination. YubiHSM 2 does not become post-quantum merely because
it offers AES-256 or a validated hardware variant. [1]

## Qualify and roll over

1. Use disposable keys to test CSR creation, certificate/CRL signing, PIN failures,
   restart, connector loss and recovery. Disable unauthorized export/operations;
   use independent operator and backup/wrapping credentials.
2. Generate the new key inside the selected HSM under an approved ceremony.
   Record public-key fingerprint, object ID/label, domains/capabilities and recovery
   attributes. Keep HSM authentication off command lines and out of Git.
3. Obtain a new subordinate certificate from the offline root. Approve overlap,
   leaf lifetime and client chain selection before token activation.
4. Back up the complete current application set. On an isolated restored copy,
   qualify the new native provider configuration and token against existing state.
   The runtime binding intentionally rejects an unapproved configuration change.
5. Roll over with the product's native token lifecycle, confirm the selected issuer
   in newly issued certificates, publish both chains/CRLs and monitor consumers.
   Do not replace the active key file or repoint an alias during routine reconciliation.

The same process applies to algorithms, including future PQC: prove certificate,
protocol, client and backup compatibility first. Hardware adoption is not itself
PQC deployment or regulatory compliance.

## Retire and recover

Keep the previous issuer's history and ability to revoke its outstanding
certificates until its full revocation/publication obligation ends. Retiring it
from new issuance is not permission to discard its key immediately.
Test a second authorized recovery device and replacement host; matching model
names do not prove matching keys, attributes or permissions.

If compromise is suspected, use incident revocation and reissuance rather than
silently importing the suspect key into hardware. Archive custody records and
destroy obsolete material only under the approved retention/ceremony policy.

## References

Sources checked 2026-10-22.

1. [YubiHSM command and algorithm capabilities](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-cmd-reference.html)
2. [OpenXPKI native crypto/token configuration](https://github.com/openxpki/openxpki-config/blob/community/QUICKSTART.md)
