# Key-protection options

The choice is the key-custody boundary, not a compulsory sequence of products.
Software providers, USB devices and network HSMs can expose cryptographic functions
to an issuer or signing service, but provide different isolation and recovery properties.

## Table of contents

- [Options A-D](#options-a-d)
- [Selection criteria](#selection-criteria)
- [Assurance requirements](#assurance-requirements)
- [Interfaces and limits](#interfaces-and-limits)
- [References](#references)

<a id="purpose"></a>
<a id="use-and-scale-matrix"></a>
<a id="how-to-read-the-matrix"></a>

## Options A-D

| Option | Design shape | Suitable purpose | Limit and operating responsibility |
| --- | --- | --- | --- |
| A: Software | Application keystore or software PKCS#11 provider; SoftHSM is an example [1] | Accepted software-custody deployment or interface rehearsal | Host access can expose key material; not hardware isolation |
| B: Single USB | One authorized host and one local device, with a separate recovery arrangement | Offline custody, low-concurrency issuer or signing service | Host/device loss interrupts service; availability depends on restore |
| C: Replicated USB gateways | Two service hosts with independent local tokens and separately governed backups | Service-level failover and horizontal signing capacity | Application routing and approved key replication are operator responsibilities, not a native HSM cluster |
| D: Network HSM | Authorized clients use appliance partitions through the vendor client/HA model | Shared hardware service with product-supported partitions and resilience | Separate management, client trust, backup and vendor compatibility obligations |

B and C are both hardware-backed options. Pico HSM and YubiHSM 2 are device
examples, not interchangeable security or certification claims. Their documented
PKCS#11 and backup capabilities require validation against the selected firmware,
mechanisms and consumer. [2][3]

[USB gateway design](usb-hsm.md) details C. [Network HSM design](network-hsm.md)
details D. An existing approved provider can satisfy any applicable option.

<a id="start-with-the-right-problem"></a>
<a id="certification-and-reality"></a>

## Selection criteria

| Requirement | Architectural implication |
| --- | --- |
| Which key is protected? | Root, issuing, code-signing and seal keys have different consumers and custody requirements |
| Host compromise | A hardware boundary may reduce extraction risk; an authorized compromised client can still misuse allowed operations |
| Availability | Define the tolerated outage and failure domains; two devices alone do not establish HA |
| Scale | Measure the actual algorithms, request concurrency and client path; developer count is not a throughput guarantee |
| Recovery | Supported export/backup policy, wrapping material, custodians and independent restore must match the selected product |
| Compliance | Verify the exact model, firmware, operating mode and required certification; price or product family is not evidence |

Historical price and team-size estimates are not design guarantees.
The simplest variant meeting the selected risk and availability requirements is valid.

<a id="repository-path"></a>

<a id="maturity-and-stages"></a>

## Assurance requirements

The selected design defines permitted operations, key-extraction boundaries,
failure tolerance and independent recovery. A change of provider requires review
of those properties and consumer compatibility; A-D are not an upgrade ladder.
Software rehearsal can validate protocols but cannot demonstrate hardware isolation.

<a id="what-usb-hsm-active-active-solves"></a>
<a id="read-more"></a>

## Interfaces and limits

PKCS#11 compatibility does not establish support for every algorithm, key attribute,
backup mechanism or application integration. C uses application-level failover;
D follows the selected vendor's client/partition model. For example, Luna's HA
model groups compatible partitions; this is not equivalent to a generic HTTP proxy. [4]

Certificate signing and secret-service unseal are separate integrations:
[seal design](vault-seal.md). Procedure selection belongs in
[the trust-stage decision](../../deployment/stage-2-trust/README.md#step-1-prepare-issuer-and-key-custody).

## References

Sources checked 2026-10-08.

1. [SoftHSM project](https://www.softhsm.org/)
2. [Pico HSM capability map](https://docs.picokeys.com/picohsm/features/)
3. [YubiHSM PKCS#11 module](https://developers.yubico.com/yubihsm-shell/yubihsm-pkcs11.html)
4. [Thales Luna redundancy and reliability](https://thalesdocs.com/gphsm/luna/7/docs/network/Content/Product_Overview/redundancy_and_reliability.htm)
