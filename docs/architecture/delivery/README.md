# Traffic and delivery

Delivery supplies approved service endpoints, software sources, code and
artifacts. General delivery services normally belong to Tier 1. Privileged
infrastructure execution and image publication remain Tier 0 responsibilities.

## Table of contents

- [Components and interfaces](#components-and-interfaces)
- [Design choices](#design-choices)
- [Design constraints](#design-constraints)
- [Realization](#realization)

## Components and interfaces

| Component | Function and boundary |
| --- | --- |
| Edge proxy | Publish named application listeners, not administrative subnet access |
| Outbound supply | Deliver approved packages/images through egress, cache, mirrors or offline transfer |
| Source control | Retain reviewed definitions and coordinate changes; not a source of Tier 0 authority |
| Registry | Own approved artifact versions and consumer access |
| Distribution layer | Accelerate artifact delivery without becoming the artifact authority |
| Build runners | Produce candidate artifacts; privileged execution has a separate approval and credential boundary |

## Design choices

| Decision | Alternatives | Consequence |
| --- | --- | --- |
| Software supply | A: existing approved egress; B: caching proxy; C: mirrors/offline content | A cache is not an offline mirror and cannot fetch unreachable content |
| Endpoint resilience | Existing ingress; proxy pair/set with owned VIPs | Failover and backend health require separate evidence; VIP count does not imply load balancing |
| Source-control runtime | Dedicated VM; cluster service; existing platform | Lifecycle and data recovery differ, while source/approval interfaces remain |
| Artifact service | A: integrated registry; B: independent registry; C: registry plus distribution acceleration | [Artifact supply design](artifact-supply.md) separates authority from delivery |
| Build environment | General container runner; image-based OS builder | Builds cannot publish trusted Tier 0 templates without Tier 0 approval |
| Trust boundary | Shared services; isolated project service | Separate policy, credentials, storage and recovery when isolation requires it |

The cache reference is a pair with one active VIP, not active-active balancing.
Bootstrap software supply is independent of hosted delivery services.
Recovery retains approved artifacts outside the platform that consumes them.

<a id="maturity"></a>

## Design constraints

| Concern | Required property |
| --- | --- |
| Publication | Named listeners and scoped artifact publishers; no blanket administrative access |
| Artifact authority | Approved versions and promotion policy remain independent of distribution caches |
| Isolation | Build credentials cannot authorize privileged infrastructure changes |
| Recovery | Required code and images survive loss of the hosted delivery platform |

An integrated registry can remain the final choice. Distribution acceleration
is justified by capacity requirements, not by an assumed product progression.

## Realization

Implementation procedures: [independent software supply](../../deployment/stage-1-foundation/README.md#step-2-protect-provisioning-access-and-state)
and [hosted delivery](../../deployment/stage-5-delivery/README.md#step-1-deploy-shared-delivery-services).
Procedure reuse does not transfer service ownership between tiers.
