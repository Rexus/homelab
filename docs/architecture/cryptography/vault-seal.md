# Secret-service seal patterns

A seal protects the secret service's startup key material. It is separate from
offline root custody, the PKI signing provider, and application-secret authorization.
The reference product is Vault; alternative implementations need their own compatibility review.

Vault consumes the selected provider; the reference HSM service starts independently
of Vault. [HSM-backed key generation and private-key operations](usb-hsm.md#authority-and-transport)
are a separate consumer integration, not a consequence of choosing a seal pattern.

## Table of contents

- [Pattern choices](#pattern-choices)
- [Seal placement](#seal-placement)
- [Recovery contract](#recovery-contract)
- [Realization](#realization)
- [References](#references)

<a id="purpose"></a>
<a id="initial-deployment"></a>
<a id="day-1-position"></a>
<a id="community-edition-paths"></a>
<a id="candidate-devices"></a>
<a id="decision-rule"></a>

## Pattern choices

| Pattern | Function | Consequence |
| --- | --- | --- |
| S1: Shamir | Authorized custodians supply unseal shares | Simple independent bootstrap; restart/recovery needs an operator process |
| S2: Transit | A separately recoverable service performs unseal cryptography for the main service | Adds a live dependency and a scoped credential; not native HSM seal [1] |
| S3: Native PKCS#11 | A supported implementation delegates seal operations to a compatible provider | Vault requires Enterprise for this feature; OpenBao documents a separate PKCS#11 path [2][3] |

S1 is the shipped VM reference. S2/S3 are design alternatives, not automatic
upgrades applied by the existing role. Device choice is independent:
[key-protection options A-D](hsm-selection.md).

<a id="recommended-oss-architecture"></a>

<a id="transit-dependency"></a>

## Seal placement

The selected runtime can be the Tier 0 cluster or a dedicated secret-service host.
The provider group shows alternatives, not two simultaneously required services:
S1 has no online seal provider; S2 uses A; S3 uses its qualified native provider.
Solid arrows are dependencies; the dashed link is authorized offline recovery.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
block-beta
  columns 1
  block:T0
    columns 2
    T0Title["Tier 0 / secret-service startup and recovery"]:2
    block:Runtime
      columns 1
      B["Main secret service B<br/>Selected control runtime"]
      Data["Persistent service state"]
    end
    block:Provider
      columns 1
      A["S2: Transit service A<br/>Independent unseal provider"]
      Hardware["S3: Qualified native provider"]
    end
    Custody["Offline recovery custody<br/>S1: Shamir shares; S2/S3: independent recovery material"]:2
  end
  B --> Data
  B --> A
  B --> Hardware
  Custody -.-> B
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef controlHeading fill:#e2f3ed,stroke:#e2f3ed,color:#173f36
  classDef runtime fill:#d9eeec,stroke:#4d7b77,color:#173f3e
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class T0,Provider control
  class T0Title controlHeading
  class Runtime runtime
  class Data data
  class Custody,Hardware custody
```

A has a narrowly scoped purpose, audit and independent recovery. B's restart
depends on A under S2, so A cannot depend on B's secrets or unavailable hosted platform.
Hardware protecting A's recovery material is a proposed custody integration;
the repository does not implement it.

<a id="benefits"></a>
<a id="what-this-gives-you"></a>
<a id="limitations"></a>
<a id="what-this-does-not-give-you"></a>

S2 can remove routine manual unseal of B, but does not make B's barrier key
HSM-wrapped or give Vault Community Edition Enterprise seal wrapping.
The actual seal and recovery guarantees depend on the selected implementation. [1][2]

<a id="maturity-and-recovery"></a>

## Recovery contract

Seal dependencies and custodians are explicit. The design defines startup behavior
when the provider is unavailable, independent recovery material, credential ownership
and supported data restoration. A seal change requires a separate migration and
rollback plan in deployment; it is not an automatic consequence of service maturity.

Root CA custody is not the secret-service seal. An offline backup of an online
key does not become a root CA, and HSM presence alone proves neither recovery nor compliance.

<a id="read-more"></a>

## Realization

[The Secrets stage](../../deployment/stage-4-secrets/README.md#step-1-deploy-the-secret-service) integrates the
secret service using [the selected seal procedure](../../deployment/stage-4-secrets/step-1c-seal-integration.md).
Administration owns subsequent recovery and rotation; architecture records the
dependency and custody contract.

## References

Sources checked 2026-10-08.

1. [HashiCorp Transit seal](https://developer.hashicorp.com/vault/docs/configuration/seal/transit)
2. [HashiCorp PKCS#11 seal](https://developer.hashicorp.com/vault/docs/configuration/seal/pkcs11)
3. [OpenBao PKCS#11 seal](https://openbao.org/docs/configuration/seal/pkcs11/)
