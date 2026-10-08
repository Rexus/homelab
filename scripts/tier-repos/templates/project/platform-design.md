# ${prefix} Platform Architecture

This project-owned record describes the intended platform and how its technical
domains fit together. Replace `TBD` with reviewed decisions. Shared standards
belong in [naming conventions](../naming-conventions.md); stages and acceptance
evidence belong in [deployment](../deployment/README.md).

## Purpose and scope

| Concern | Project decision |
| --- | --- |
| Purpose, users and required outcomes | TBD |
| Sites, platform boundary and external dependencies | TBD |
| Tier ownership and administrative authority | TBD |
| Required availability and recovery independence | TBD |
| Exclusions and assumptions | TBD |

## Platform relationships

Describe the topology and interfaces between domains, using the
[platform reference](../auto-docs/architecture/README.md). Show tier ownership
and network protection separately. Exact hosts and addresses stay in inventory.

| Connection | Purpose / interface | Ownership and trust boundary |
| --- | --- | --- |
| TBD | TBD | TBD |

## Technical domains

| Domain | Project design |
| --- | --- |
| Networking | [Networks, zones and traffic policy](networking/README.md) |
| Compute | [Hypervisors, images and cluster runtime](compute/README.md) |
| Identity | [Authority, authentication and authorization](identity/README.md) |
| Cryptography | [Trust, key custody and secrets](cryptography/README.md) |
| Delivery | [Endpoints, software supply and artifacts](delivery/README.md) |
| Operations | [Visibility, inventory and recovery](operations/README.md) |

## Shared constraints and decisions

| Decision / required property | Rationale and alternatives | Consequences | Review trigger |
| --- | --- | --- | --- |
| TBD: trust, ownership, availability or recovery constraint | TBD | TBD | TBD |

Add focused cross-domain decisions under `decisions/`. Reference patterns:
[principles](../auto-docs/architecture/principles.md),
[tier ownership](../auto-docs/architecture/tier-ownership.md),
[service boundaries](../auto-docs/architecture/service-boundaries.md) and
[reference platform](../auto-docs/architecture/reference-platform.md).
