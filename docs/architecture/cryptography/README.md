# Cryptography and secrets

Cryptography establishes trust, protects key custody and delivers credentials.
Root custody, online issuance, signing and secret storage are separate functions;
one product need not implement all of them.

## Table of contents

- [Components and interfaces](#components-and-interfaces)
- [Independent choices](#independent-choices)
- [Design constraints](#design-constraints)
- [Realization](#realization)

## Components and interfaces

| Component | Function and boundary |
| --- | --- |
| Offline root | Signs intermediate CA certificates during authorized ceremonies; no normal network service |
| Online issuer | Issues and renews certificates under approved policy without access to the root key |
| Key provider | Performs permitted cryptographic operations using software or hardware custody |
| Secret service | Stores/delivers credentials with scoped authorization, audit and independent recovery |
| Seal/unseal mechanism | Protects secret-service startup material; distinct from the certificate-signing backend |

The [certificate design](../reference-platform.md#certificate-trust) shows
consumer-to-issuer relationships. A gateway cannot become a signing backend merely
by being reachable; the application needs supported provider integration.

## Independent choices

| Decision | Alternatives | Design |
| --- | --- | --- |
| Key custody | A: software; B: single USB; C: replicated USB gateways; D: network HSM | [Key-protection options](hsm-selection.md) |
| Issuer location | Existing authority; dedicated VM; cluster service | Same offline-root/online-issuer boundary; no self-bootstrap dependency |
| Secret-service placement | Dedicated VM; Kubernetes service; existing approved service | Same access and recovery contract; migration needs explicit data/state ownership |
| Secret-service seal | Shamir; independent Transit service; supported native PKCS#11 | [Seal patterns](vault-seal.md), independent of A-D |

Root and online keys may select different providers. None of the options requires
passing through every other option first. Hardware can be selected initially or
introduced later without changing its purpose.

<a id="maturity"></a>

## Design constraints

| Concern | Required property |
| --- | --- |
| Custody | Key purpose, authorized operations and custodians are explicit for each provider |
| Isolation | Offline root material is not available to online issuers or ordinary consumers |
| Lifecycle | Rotation and revocation preserve the intended trust and consumer compatibility |
| Recovery | Device/provider loss cannot require the unavailable secret service to restore its own keys |

Software custody can satisfy an accepted threat model. Hardware presence alone
does not establish the required isolation, recovery or compliance properties.

## Realization

Implementation procedures: [trust and custody](../../deployment/stage-2-trust/README.md#step-1-prepare-issuer-and-key-custody)
and [secret-service integration](../../deployment/stage-4-control-services/README.md#step-2-deploy-operational-services).
Device operations remain authorized procedures; the existing hsm automation supplies
hosts and baseline only.
