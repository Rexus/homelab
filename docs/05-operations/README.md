# Operations

Open the deployed capability, find its inputs, then select a maintenance or recovery task.
The names match [architecture](../01-architecture/README.md); the numbers order this
operating manual, independently of the [installation stages](../03-deployment/README.md).

## Recover a failed system

Start with [recovery order](06-resilience/README.md#recovery-order). Restore the
[bootstrap](06-resilience/recovery/bootstrap.md), [one VM](06-resilience/recovery/virtual-machines.md),
[a failed host](06-resilience/recovery/host.md) or the
[whole platform](06-resilience/recovery/platform.md) using the original inputs and recovery copies.

<a id="capability-guides"></a>
<a id="hosts"></a>
<a id="virtual-machines-and-kubernetes"></a>
<a id="trust-access-and-evidence"></a>

## Choose a capability

| Chapter | Start here | Tasks and related design |
| --- | --- | --- |
| 1 | [Hosting](01-hosting/README.md) | Register hosts; manage templates, VMs, Kubernetes and Lab environments. [Design](../01-architecture/04-hosting/README.md) |
| 2 | [Software intake](02-software-intake/README.md) | Update cache policy, check consumers and operate verified publication. [Design](../01-architecture/07-software-intake/README.md) |
| 3 | [Cryptography](03-cryptography/README.md) | Maintain Cryptographic trust, issuers, key custody and Secrets. [Design](../01-architecture/08-cryptography/README.md) |
| 4 | [Identity](04-identity.md) | Grant, revoke and verify access for people, devices and services. [Design](../01-architecture/09-identity/README.md) |
| 5 | [Delivery](05-delivery.md) | Maintain artifact supply, controllers and the Development platform. [Design](../01-architecture/10-delivery/README.md) |
| 6 | [Operations and resilience](06-resilience/README.md) | Check Protected logging and Observability; verify backups and restore services. [Design](../01-architecture/11-operations/README.md) |

<a id="recovery-and-resource-retirement"></a>
<a id="backups-and-recovery"></a>

## Protect or retire resources

| Task | Guide |
| --- | --- |
| Capture the independent recovery set | [Recovery-set checklist](06-resilience/backups/recovery-set.md) |
| Schedule and verify backup copies | [Backup tasks](06-resilience/README.md#backups) |
| Destroy a selected deployment deliberately | [Resource retirement](01-hosting/provisioning.md) |
| Reconcile state after an external removal or restore | [Terraform state](01-hosting/terraform-state.md) |

Use the [capability index](../06-paths/capabilities.md) to move between design, deployment
and operating tasks. Record successful checks and recovery results in project records.
Product-specific upgrade limits remain in each task and the
[implementation support map](../08-reference/implementation-support.md#stage-coverage).
