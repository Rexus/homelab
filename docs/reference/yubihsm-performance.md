# YubiHSM 2 Performance

Yubico's published example timings, transcribed as factual measurements from its
technical data sheet. These describe an otherwise unoccupied device; they are
capacity-planning inputs, not an end-to-end application benchmark. [1]

## Contents

- [Published timings](#published-timings)
- [Use the numbers](#use-the-numbers)
- [References](#references)

## Published Timings

| Operation | Approximate time |
| --- | ---: |
| RSA-2048, PKCS#1, SHA-256 | 139 ms |
| RSA-3072, PKCS#1, SHA-384 | 504 ms |
| RSA-4096, PKCS#1, SHA-512 | 852 ms |
| ECDSA P-224, SHA-1 | 64 ms |
| ECDSA P-256, SHA-256 | 73 ms |
| ECDSA P-384, SHA-384 | 120 ms |
| ECDSA P-521, SHA-512 | 210 ms |
| EdDSA-25519, 32 bytes | 105 ms |
| EdDSA-25519, 64 bytes | 121 ms |
| EdDSA-25519, 128 bytes | 137 ms |
| EdDSA-25519, 256 bytes | 168 ms |
| EdDSA-25519, 512 bytes | 229 ms |
| EdDSA-25519, 1024 bytes | 353 ms |
| AES-128/192/256 CCM wrap | 10 ms |
| HMAC-SHA-1/256 | 4 ms |
| HMAC-SHA-384/512 | 243 ms |

The legacy SHA-1/P-224 rows reproduce measurements, not approved new selections.
Do not confuse YubiHSM 2, YubiHSM 2 FIPS and YubiKey capabilities.

## Use The Numbers

P-256 signing is about 11.7 times faster than RSA-4096 in these examples
(`852 / 73`); an offline root's rare signing operations have different needs
from a busy issuer or developer signing key.

Benchmark the actual SDK/provider, message size, concurrency, session setup,
network gateway, firmware and audit settings. Keep headroom for CRLs, renewal
bursts and recovery. Device duplication alone does not provide CA application HA.

Use local hashing for ordinary checksums; a signature remains necessary when
authorship matters. See [algorithm selection](../architecture/cryptography/algorithm-selection.md)
and [post-quantum readiness](../architecture/cryptography/post-quantum.md).

## References

Source checked 2026-10-18.

1. [Yubico YubiHSM 2 technical data sheet, performance section](https://docs.yubico.com/hardware/yubihsm-2/datasheet/_static/YubiHSM_2_Technical_Data_Sheet.pdf)
