# Identity and access

Identity establishes subjects and exposes authentication interfaces. Authorization
remains local to each service: a successful login is not permission to administer
the platform.

## Table of contents

- [Components and interfaces](#components-and-interfaces)
- [Design choices](#design-choices)
- [Design constraints](#design-constraints)
- [Realization](#realization)

## Components and interfaces

| Component | Function and boundary |
| --- | --- |
| Directory authority | Users, groups, hosts, DNS and Kerberos; independent of the control cluster |
| Identity broker | Federate the authority and provide OIDC to applications |
| Service authorization | Translate identity into scoped application or cluster permissions |
| Operator credentials | Normal strong authentication plus separately protected recovery access |

The reference uses two dedicated FreeIPA VMs and Keycloak inside Tier 0 Kubernetes.
FreeIPA implements the directory function, not the whole identity and access design.
Inventory, source control, dashboards and cluster interfaces consume OIDC only
after their broker integration exists.

## Design choices

| Decision | Variants | Consequence |
| --- | --- | --- |
| Authority | A: new dedicated directory pair; B: existing approved authority | B replaces installation with an interface, ownership and recovery contract |
| Normal operator access | Bootstrap credentials; hardware-backed OTP/PIV or appropriate phishing-resistant mechanisms | Credential capability and application support must be verified separately |
| Windows clients | Selected service interoperability; optional [AD-compatible extension](windows-integration.md) | An extension does not silently replace the primary identity authority |
| Instance boundary | Shared identity; isolated project/domain authority where justified | Isolation adds enrollment, trust and recovery responsibilities |

User authentication devices and server HSMs have different purposes.
A server's key custody does not by itself provide strong user authentication.

<a id="maturity"></a>

## Design constraints

| Concern | Required property |
| --- | --- |
| Authority | Defined namespaces and replication boundaries; one owner for each identity source |
| Authorization | Each consumer maps identity to its own scoped permissions |
| Availability | Directory replication and broker persistence have separate failure and recovery contracts |
| Recovery | The broker cannot be the only means to recover itself or replace lost operator credentials |

## Realization

Implementation procedures: [directory authority](../../deployment/stage-3-identity-runtime/procedures/freeipa.md)
and [broker integration](../../deployment/stage-4-control-services/README.md#step-1-deploy-identity-federation).
Windows integration is an explicit project option, not a supplied domain installer.
