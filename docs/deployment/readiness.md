# Deployment readiness

Deployment adds and verifies capabilities in stages against a selected
[platform architecture](../architecture/README.md) and its
[domain designs](../architecture/README.md#technical-domains).
Readiness describes what has been implemented and demonstrated, not a new architecture.

## Table of contents

- [Stages and readiness](#stages-and-readiness)
- [Readiness levels](#readiness-levels)
- [Capability evidence](#capability-evidence)
- [Project records](#project-records)

<a id="purpose"></a>
<a id="how-to-read-this-path"></a>
<a id="three-dimensions"></a>
<a id="system-states"></a>
<a id="dependency-order"></a>

## Stages and readiness

The [stage index](README.md#deployment-stages) owns the rollout sequence and links
each procedure to its design. A stage identifies work and dependencies; readiness
records the evidence for an individual capability. A later stage does not make
all preceding services highly available or ready for production.

A design variant changes the arrangement of components. Software custody, USB
devices and network HSMs are alternatives, not readiness levels. Existing services
can satisfy prerequisites after their interfaces and recovery have been verified.

<a id="maturity-levels"></a>

## Readiness levels

Apply these levels independently to each deployed capability. The selected design
defines its required guarantees; deployment records whether they have been met.

| Level | Deployment status | Required evidence |
| --- | --- | --- |
| 0: Defined | Design, owner, dependencies and variant are selected | Reviewed design and acceptance criteria |
| 1: Usable | The interface serves approved consumers | Functional, access-boundary and basic recovery checks |
| 2: Assured | Selected availability, isolation and recovery requirements are demonstrated | Failure tests, restore evidence and maintained operating procedures |

Hardware expense, node count and successful VM creation do not establish a level.

<a id="capability-groups"></a>
<a id="platform-preparation"></a>
<a id="shared-services"></a>
<a id="system-control"></a>
<a id="recovery"></a>
<a id="application-platform"></a>
<a id="security-and-cryptography"></a>
<a id="subsystem-evolution"></a>

<a id="subsystem-evidence"></a>

## Capability evidence

| Capability | First integration | Evidence for acceptance |
| --- | --- | --- |
| Compute | Compute foundation; identity/runtime | Approved guests and APIs work; selected node/storage failures and independent restore are tested |
| Cryptography | Cryptographic trust; control services | Authorized signing, denied operations, rotation, revocation, device/provider loss and independent restore |
| Identity | Identity/runtime; control services | Replication, scoped federation, denied access, replica/broker loss and lost-credential recovery |
| Traffic and delivery | Compute foundation; delivery and handover | Scoped publication/pulls, promotion, rollback, endpoint failover and recovery artifacts |
| Operations | Backups from compute foundation; visibility in control services | Ingestion, retention, scoped queries, external failure detection and restore exercises |

The directory and broker, or issuer and seal provider, may have different readiness.
Each stage records acceptance and operational handover; later stages do not postpone basic protection and
backups until the end of deployment.

<a id="variants-and-existing-services"></a>

## Project records

Project architecture records the chosen design and required properties.
Project deployment records current readiness, outstanding work, selected procedures
and acceptance evidence. Administration keeps recurring verification and recovery
records. A failed requirement can block acceptance without changing the architecture.

For an existing service, record its owner and verified interface instead of
creating duplicate resources or state. A separate isolated instance requires an
explicit design decision. An alternative without supplied automation remains
project integration work; see the [support map](../reference/implementation-support.md).
