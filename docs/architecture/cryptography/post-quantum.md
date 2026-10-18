# Post-Quantum Readiness

Post-quantum cryptography (PQC) uses algorithms designed to resist attacks by
classical computers and sufficiently capable quantum computers. It runs on ordinary
computers. Increasing RSA from 2048 to 4096 bits, or choosing a larger elliptic
curve, does not make either family post-quantum secure. [1]

The reference CA deployment currently uses classical certificate signatures.
Treat it as a migration-capable baseline; make a quantum-resistance claim only for
the exact protocols, libraries, providers and consumers that have been qualified.

## Contents

- [Choose by purpose](#choose-by-purpose)
- [Protect long-lived secrets](#protect-long-lived-secrets)
- [Qualify a migration](#qualify-a-migration)
- [References](#references)

## Choose by purpose

| Purpose | Standardized family | Deployment decision |
| --- | --- | --- |
| Establish a shared secret | ML-KEM, FIPS 203 | Test a supported hybrid TLS group; ML-KEM-768 is a useful compatibility target |
| Sign certificates or artifacts | ML-DSA, FIPS 204 | Evaluate ML-DSA-65 where the entire signature ecosystem supports it |
| Alternative signature design | SLH-DSA, FIPS 205 | Evaluate hash-based signatures when their larger signatures and performance fit |
| Symmetric encryption | AES-256 in a product-supported construction | Verify integrity, nonce discipline and the wrapping layer too |
| Hashing | SHA-384 or SHA-512 for a larger margin | Hashes do not replace signatures or authenticated key establishment |

The first three families are final NIST standards; their parameter sets have
different security categories and performance. They are not interchangeable:
a KEM does not sign a certificate. Check each publication's errata. [2][3][4]

OpenSSL 3.5 supports PQ algorithms and hybrid TLS groups including
`X25519MLKEM768`. A service must actually link a suitable library and negotiate the
group with its peer. Installing another `openssl` executable alongside a service
does not change that service's TLS behavior. [5]

Hybrid key establishment combines classical and PQ components according to the
supported protocol. It can improve confidentiality while the certificate chain
still uses a classical signature. That is a scoped transport property, rather
than a fully PQ certificate hierarchy.

## Protect long-lived secrets

An attacker can retain encrypted traffic now and try to decrypt it later.
Prioritize data whose confidentiality must survive a long migration period:
backups, personal/customer data, long-lived credentials and sensitive archives.
Forward secrecy based only on classical ECDH does not remove the quantum risk. [1]

For each path, record the client and server, negotiated TLS version/group,
certificate algorithms, data retention requirement and fallback behavior.
The browser-to-edge connection, edge-to-origin connection and backup key wrapping
are separate paths. A hybrid public connection does not upgrade a classical origin hop.

The YubiHSM 2's documented algorithm list is classical. Do not infer ML-KEM,
ML-DSA or SLH-DSA support from its secure key storage, AES-256 support or FIPS label. [6]
Choose future hardware by explicit algorithm/firmware/provider support and measured
latency, capacity, audit and same-identity recovery.

## Qualify a migration

1. Inventory certificate signatures, TLS groups, SSH/commit signatures, backup
   encryption and wrapping keys. Identify all consumers of each trust anchor.
2. Prefer maintained protocol/library implementations. Keep experimental providers
   and test roots away from production trust stores.
3. Test a supported hybrid TLS deployment with representative clients. Record the
   negotiated group, handshake sizes, latency, proxies, inspection tools and failures.
4. Test PQ certificate/signature support separately, including CRLs, validation,
   HSM interfaces, recovery, revocation and rollback to the approved trust set.
5. Define whether classical fallback is acceptable for each data class. Alert on
   unexpected fallback when PQ confidentiality is a requirement.
6. Replace long-lived credentials and wrapping keys through a controlled migration.
   Re-encryption cannot undo exposure of earlier ciphertext already copied by an attacker.

There is no single universal "post-quantum compliant" checkbox. A named regulatory
or contractual regime may impose its own algorithms, dates and validated-module
requirements. NIST IR 8547 and SP 800-57 Rev. 6 were still public drafts at this
review date; distinguish their proposals from final standards and local obligations. [1][7]

## References

Sources checked 2026-10-18.

1. [NIST IR 8547, initial public draft: migration risks and planning](https://csrc.nist.gov/pubs/ir/8547/ipd)
2. [NIST FIPS 203: ML-KEM, final and errata](https://csrc.nist.gov/pubs/fips/203/final)
3. [NIST FIPS 204: ML-DSA, final and errata](https://csrc.nist.gov/pubs/fips/204/final)
4. [NIST FIPS 205: SLH-DSA, final](https://csrc.nist.gov/pubs/fips/205/final)
5. [OpenSSL 3.5 supported groups and hybrid keyshares](https://docs.openssl.org/3.5/man3/SSL_CTX_set1_curves/)
6. [YubiHSM 2 supported algorithms](https://docs.yubico.com/hardware/yubihsm-2/hsm-2-user-guide/hsm2-cmd-reference.html)
7. [NIST SP 800-57 Part 1 Rev. 6, initial public draft](https://csrc.nist.gov/pubs/sp/800/57/pt1/r6/ipd)
