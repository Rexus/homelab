# Tier 0

Tier 0 owns Proxmox, physical network and storage control, every VM template,
and the trust/control services with authority over the environment. Start here
for a new installation; consume existing infrastructure when it meets the same
readiness checks. Tier 0 must recover without Tier 1 or Tier 2.

## Table of contents

- [Deployment order](#deployment-order)
- [Getting started](#getting-started)
- [Find your way](#find-your-way)
- [Repository structure](#repository-structure)

## Deployment order

Before Day 0, record [project conventions](../../reference/project-documentation.md#start-with-project-values)
and prepare [local tools](../../getting-started/local-setup.md).
Days are readiness phases, not calendar days or repository tiers.

| Phase | Deploy or prepare | Ready to continue when |
| --- | --- | --- |
| **Day 0: foundation** | [Proxmox](../../platforms/proxmox/README.md#first-deployment-order), optional [HA](../../platforms/proxmox/cluster-ha.md) and [SDN](../../platforms/proxmox/network-prerequisites.md#optional-sdn-for-guest-networks), [VM templates](../../platforms/proxmox/template-lifecycle.md#local-workflow); network/storage, source control (Git), OCI registry access, CI/bootstrap runner, Terraform state | Tested templates and [bootstrap dependencies](bootstrap.md#day-0-bootstrap-dependencies) work without the new cluster |
| **Day 1: cluster foundation** | Deploy the [Kubernetes control cluster](../../platforms/kubernetes/README.md); add networking, GitOps, storage, certificates, ingress, databases, and bootstrap secrets using the [shared foundation checklist](../../platforms/kubernetes/README.md#cluster-foundation) | Cluster, reconciliation, storage, TLS, database, and secret-decryption checks pass |
| **Day 2: control services** | FreeIPA on two dedicated VMs; Keycloak in Kubernetes; Vault, NetBox, Headlamp, and monitoring; follow the [service sequence](bootstrap.md#day-2-service-sequence) | Services work, identity integration is tested, backups run, and local recovery remains available |
| **Day 3: operational handover** | Harden RBAC, switch supported normal logins to OIDC, disable or restrict bootstrap credentials, test backup/restore; use the [handover checks](bootstrap.md#day-3-operational-handover) | Scoped access and recovery are proven without relying on the services being restored |

Day 0/1 follows the [platform flow](bootstrap.md#bootstrap-phases); Day 2 follows
**FreeIPA -> Keycloak -> OIDC -> clients**. The FreeIPA pair is deployed through
the Linux `foundation` setup and does not require Kubernetes. Keycloak belongs
in the Tier 0 Kubernetes cluster. Choose one lifecycle owner per service; do not
duplicate FreeIPA in Kubernetes. General platform instances remain in Tier 1.

Restrict access, protect secrets, and retain backups from the start. Day 3 is
the tested handover to normal operation, not the first security work.

## Getting started

After preparing hosts, **Day 0: templates before VMs.** From
`homelab-iac/homelab-tier-0`, initialize
the template catalog:

```bash
bash scripts/proxmox-templates.sh init
```

Follow the
[local template workflow](../../platforms/proxmox/template-lifecycle.md#local-workflow)
to set image paths, checksums, placement, and protected API access; then plan,
publish, and test the required AlmaLinux, Rocky Linux, or Talos templates.
Approve their references in the [shared consumer catalog](../../platforms/proxmox/template-catalog.md)
before any tier selects them. Do not copy the catalog into each tier.
This works before any managed VM, control cluster, or hosted CI exists.
Existing approved templates are valid when their IDs and recovery copies are verified.

Next initialize the Kubernetes control cluster's Tier 0 inputs. The current
implementation uses Talos; [other node OS choices](../../platforms/kubernetes/README.md#implementation-choice)
do not change the goal or ownership.

```bash
bash scripts/kubernetes-cluster.sh init
```

Follow the [current Talos implementation](../../platforms/talos/terraform.md) to configure, plan,
and deploy the cluster, and the [Linux identity VM guide](../shared-services/identity.md) for
the dedicated FreeIPA pair. Run shared commands
from the tier repository root so they use its inventory and state. Replace
`homelab` in paths if you chose another prefix.

## Find your way

| Need | Guide |
| --- | --- |
| Phase dependencies, recovery, and handover | [Tier 0 bootstrap and recovery](bootstrap.md) |
| Approved node and guest images | [Template lifecycle and CD](../../platforms/proxmox/template-lifecycle.md) |
| Kubernetes installation and shared foundation | [Cluster guide](../../platforms/kubernetes/README.md) |
| Tier boundaries | [Tier model](../../architecture/tier-model.md) |
| Hardware ownership and future workload requests | [Infrastructure control](../../architecture/infrastructure-control.md) |
| Network design | [Network architecture](../../architecture/network.md) |
| Inventory and upstream updates | [Generated repository model](../../reference/generated-repository-model.md) |
| Command reference | [Repository scripts](../../reference/repository-scripts.md) |

## Repository structure

- `ansible/`: tier service playbooks and roles, inventory, group vars, and configuration
- `terraform/deployments/`: infrastructure deployments and their inputs
- `terraform/deployments/kubernetes/`: control-cluster VMs and bootstrap; currently Talos
- `templates/`, `terraform/deployments/templates/`, and `ci/`: image catalog, template publication, and CD jobs
- `terraform/modules/` and `packer/`: tier-owned guest/template modules and custom-build scaffolds
- `clusters/tier0/`: cluster-service skeletons
- `scripts/`: template and Kubernetes commands, plus entry points to shared Linux helpers

The Linux setup scripts do not bootstrap Kubernetes or deploy the cluster services.
The [bootstrap and recovery reference](bootstrap.md) distinguishes working
automation from skeletons and records the recovery boundary.
