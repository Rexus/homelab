# Choose Cryptographic Algorithms

Use ECDSA P-256 for ordinary TLS leaf keys, P-384 for the reference software issuer,
and RSA-3072 when a consumer requires RSA. Choose by purpose, lifetime and compatibility;
the largest available key is rarely the best default.

This is the project's engineering baseline, not a certification of a deployment.
See [post-quantum readiness](post-quantum.md) and [HSM timings](../../reference/yubihsm-performance.md).

## Contents

- [Choose the operation](#choose-the-operation)
- [Choose the key size](#choose-the-key-size)
- [Apply the baseline](#apply-the-baseline)
- [Review and rotation](#review-and-rotation)
- [References](#references)

## Choose the operation

| Need | Primitive | What it provides |
| --- | --- | --- |
| Encrypt application traffic | TLS 1.3; authenticated symmetric encryption | Confidentiality and integrity with authenticated peers |
| Identify a TLS server/client | Certificate and digital signature | Binds an approved identity to a public key |
| Identify a commit/release author | SSH, OpenPGP or X.509 signature | Verifiable authorship when the signing key is trusted |
| Compare an artifact with a trusted manifest | SHA-256 or SHA-384 | Detects changes; authenticate the manifest separately |
| Authenticate a message with a shared secret | HMAC-SHA-256 | Integrity and shared-secret authentication |
| Protect password verifiers | Application-supported salted, costed password KDF | Slows offline guessing; plain SHA-256 is unsuitable |

RSA is a family used for signatures and, in some protocols, encryption. ECC means
elliptic-curve cryptography: ECDSA/EdDSA sign, while ECDH establishes keys. They are
different operations. Modern TLS uses symmetric encryption for bulk traffic. [1][2]

A Git object hash is not an author's signature. Use SHA-256 for new independent
checksums and a trusted signature for release/commit provenance where required.
An Ed25519 or P-256 signing key avoids making a routine signing operation depend on
RSA-4096 latency. This does not require changing an existing repository's object format. [3][4]

## Choose the key size

RSA sizes normally mean **2048, 3072 and 4096**, rather than 2000 or 4000.
ECC key sizes are not numerically comparable with RSA sizes. NIST's classical
security-strength relationships include the following: [1]

| Classical security strength | RSA modulus | ECC key range | Typical example |
| --- | --- | --- | --- |
| 112 bits | 2048 | 224-255 | RSA-2048 compatibility baseline |
| 128 bits | 3072 | 256-383 | ECDSA P-256 |
| 192 bits | 7680 | 384-511 | ECDSA P-384 |
| 256 bits | 15360 | 512+ | ECDSA P-521 |

RSA-4096 sits between the listed 128- and 192-bit RSA levels; it is not equivalent
to P-384 or to 4096 bits of symmetric security. These are classical comparisons,
not estimates of resistance to a cryptographically relevant quantum computer. [1][5]

Use at least a 128-bit classical design target for new private infrastructure.
RSA-2048 can remain a documented compatibility exception, including certificates
issued under an external public CA's policy; prefer ECC or RSA-3072 for new keys
under project control. Avoid new DSA, MD5 and SHA-1 signatures. [1][4][6]

## Apply the baseline

| Purpose | Project default | Reason and boundary |
| --- | --- | --- |
| Offline root | RSA-4096 with SHA-384 | Infrequent signing; broad chain compatibility; offline custody |
| OpenXPKI software issuer | ECDSA P-384 with SHA-384 | Efficient CA signing; protected online key; separate root |
| Private TLS server | ECDSA P-256; RSA-3072 exception | Short-lived client-held keys; DNS/SAN policy and independent approval |
| Public reverse proxy | Let's Encrypt, ECDSA P-256 leaf | Browser trust; automated HTTP-01 renewal; separate ACME account key |
| Proxy-to-origin connection | Verified TLS with the origin's exact DNS name | Encryption alone cannot establish which server answered |
| Git commit/release signing | Ed25519 or supported P-256 signature | Independent developer key; verify against approved signers |
| New artifact checksums | SHA-256; SHA-384 for a larger margin | Usually hash locally; authenticate the publisher separately |
| Long-lived confidential storage | Product-supported AES-256 encryption with integrity | Recovery and key wrapping need the same confidentiality lifetime |

These selections are project policy based on the cited standards and supported
interfaces. Root and leaf algorithms can differ; qualify the whole chain against
actual consumers. Private leaf validity defaults to 30 days; renewal must start
well before expiry. A stronger issuer cannot compensate for a weak or stolen leaf key.

Prefer TLS 1.3. Permit TLS 1.2 only for documented interoperability with ECDHE and
AEAD ciphers; disable older TLS, static RSA key exchange, RC4 and CBC suites.
The public certificate's RSA/ECDSA signature is separate from the negotiated
key-establishment group and traffic cipher. [2][7][8]

## Review and rotation

Record key purpose, algorithm, size, provider, owner, creation/expiry, consumer
compatibility, recovery location and replacement procedure in the private project.
Rotate leaf keys through their certificate workflow. Change a CA identity only
through the documented rollover or
[hardware migration procedure](../../administration/cryptography/hardware-migration.md).

Review this baseline when standards or vendor support change, a weakness is published,
or the protected data lifetime changes. A short certificate lifetime does not erase
previously captured encrypted traffic. Use the [post-quantum guide](post-quantum.md)
for long-lived confidentiality.

## References

Sources checked 2026-10-18. Final standards underpin the baseline; drafts inform
planning and are explicitly identified.

1. [NIST SP 800-57 Part 1 Rev. 5, final; strength comparisons and key management](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final)
2. [IETF RFC 9325, secure TLS deployment](https://www.rfc-editor.org/info/rfc9325/)
3. [Git signature formats and verification](https://git-scm.com/docs/gitformat-signature)
4. [NIST hash-function policy](https://csrc.nist.gov/projects/hash-functions/nist-policy-on-hash-functions)
5. [NIST IR 8547, initial public draft; quantum migration planning](https://csrc.nist.gov/pubs/ir/8547/ipd)
6. [NIST SP 800-131A Rev. 3, initial public draft; algorithm transitions](https://csrc.nist.gov/pubs/sp/800/131/a/r3/ipd)
7. [IETF RFC 9852, TLS 1.3 requirements for new protocols](https://www.rfc-editor.org/info/rfc9852/)
8. [IETF RFC 10015, obsolete TLS 1.2 key exchanges](https://www.rfc-editor.org/info/rfc10015/)
