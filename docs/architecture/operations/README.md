# Operations and workloads

Operations supplies independent visibility, inventory documentation, recovery and
workload governance. Every stateful resource has a recovery owner, regardless
of whether its monitoring is local or supplied by shared operational services.

## Table of contents

- [Components and interfaces](#components-and-interfaces)
- [Design choices](#design-choices)
- [Design constraints](#design-constraints)
- [Realization](#realization)

## Components and interfaces

| Component | Function and boundary |
| --- | --- |
| Inventory documentation | Describe deployed infrastructure; never replace tier-local bootstrap inputs |
| Cluster interface | Expose scoped cluster operations; not blanket infrastructure administration |
| Telemetry collectors | Receive, normalize and route signals under approved access policy |
| Signal backends | Store metrics, traces, logs and audit records according to purpose and retention |
| Recovery storage | Retain backups and restore evidence outside the service being recovered |
| Workload governance | Isolate consumers and authorize changes without transferring Tier 0 control |

## Design choices

| Decision | Alternatives | Consequence |
| --- | --- | --- |
| Telemetry placement | A: dedicated VM services; B: cluster services; C: existing service | [Telemetry design](telemetry.md) keeps signal roles independent of placement |
| Sharing | Central platform service; isolated project collectors/backends | Isolation follows access, retention and trust requirements |
| Recovery target | Dedicated backup service; approved external target; protected offsite copy | Storage availability alone is not tested restore |
| Workload runtime | Linux VMs, image-based Linux, Kubernetes applications | Definitions and inventory stay tier-local; runtime changes need explicit lifecycle ownership |
| Workload execution | Reviewed operator action; bounded self-service | The latter needs the [request contract](../compute/provisioning.md), not unrestricted CI credentials |

NetBox, Headlamp and monitoring are reference implementations, not prerequisites
for creating the infrastructure on which they run.

<a id="maturity"></a>

## Design constraints

| Concern | Required property |
| --- | --- |
| Visibility | Failure detection remains available outside the observed cluster |
| Access and retention | Signal stores enforce the sensitivity and retention requirements of their sources |
| Recovery | Backups, custodians and recovery targets remain independent of the protected service |
| Governance | Workload requests cannot bypass tier ownership or infrastructure authorization |

Hardware custody and application-state recovery remain separate responsibilities.
A central dashboard alone is insufficient for independent failure detection.

## Realization

Implementation procedures: [operational services](../../deployment/stage-4-control-services/README.md#step-2-deploy-operational-services)
and [operational acceptance](../../deployment/stage-4-control-services/README.md#step-3-integrate-access-and-recovery).
Recurring work belongs in [administration](../../administration/README.md).
