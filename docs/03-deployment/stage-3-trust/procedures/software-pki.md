# Software-backed PKI: policy and custody

<a id="deploy-a-fresh-software-backed-pki"></a>
<a id="contents"></a>

The continuous first-install workflow is now [Stage 3, actions 1-15](../README.md).
Select software custody there and follow it top to bottom; this page is the policy/custody reference,
not another runtime installation. Hardware custody uses its own original-key provider contract.

**Working repository:** `<prefix>-tier-0` for issuer inputs and policy artifacts; root signing uses offline custody.

<a id="decisions-and-recovery-kit"></a>
<a id="build-the-private-policy-bundle"></a>
<a id="install-and-prepare-the-issuing-key"></a>
<a id="sign-and-activate"></a>
<a id="complete-identity-and-acceptance"></a>
<a id="accept-the-issuer-and-continue"></a>
<a id="step-1-approve-policy-and-custody"></a>
<a id="step-2-build-the-private-policy-bundle"></a>
<a id="step-3-install-and-prepare-the-issuing-key"></a>
<a id="step-4-sign-and-activate"></a>
<a id="step-5-accept-the-issuer-and-continue"></a>

## Policy and recovery kit


Approve names, trust scope and [algorithms](../../../01-architecture/08-cryptography/02-algorithm-selection.md)
before generating keys. The supplied policy has one TLS-server leaf profile,
client-held keys, explicit DNS suffixes, a 30-day default lifetime and a separate
requester/approver. It has no internal ACME, OCSP, client-auth or code-signing endpoint.
Manual renewal uses a new CSR through the same approval workflow.

| Material | Custody |
| --- | --- |
| Root instance, encrypted root key and unlock secret | Offline, separately authorized copies |
| Signer passphrase and DataVault master secret | Independently backed-up recovery kit |
| Database/session credentials and session secret | Stable protected controller inputs |
| Configuration archive and local CLI key | Secret-bearing artifacts; encrypt backups, never commit |
| CA certificates and fingerprints | Public records, independently verified |
| Recovery recipient private key | Offline, separate from the issuer and backup destination |

Software encryption does not prevent a compromised running CA host from signing.
Restrict host administration and qualify the
[hardware migration path](../../../05-operations/03-cryptography/hardware-migration.md).

## First-install locations

| Work | Continue in the Stage 3 guide |
| --- | --- |
| Private policy, account hashes and immutable archive | [Actions 4-6](../README.md#step-4-prepare-the-private-policy) |
| Host, disk and inactive runtime | [Actions 7-9](../README.md#step-7-provision-the-issuer-and-attached-storage) |
| Software key and public CSR | [Action 10a](../README.md#step-10-prepare-the-issuing-request) |
| Authorized offline signing | [Action 11](../README.md#step-11-sign-the-approved-request-offline) |
| Public certificates and native token activation | [Actions 12-13](../README.md#step-12-install-public-certificates-and-start-the-prepared-backend) |
| Issuance and independent restore | [Action 14](../README.md#step-14-accept-issuance-and-recovery) |

## References

Sources checked 2026-10-18.

1. [OpenXPKI native CLI, token setup and DataVault custody](https://github.com/openxpki/openxpki-config/blob/community/QUICKSTART.md)
2. [Argon2 reference CLI and encoded password hashes](https://github.com/P-H-C/phc-winner-argon2#command-line-utility)
