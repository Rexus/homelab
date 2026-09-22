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

| Step | What to do | Ready to continue when |
| --- | --- | --- |
| 1. Record choices | Generate the collection; fill in [project conventions](../../reference/project-documentation.md#start-with-project-values) and prepare [local tools](../../getting-started/local-setup.md) | Names, IDs, networks, operator access, and recovery locations are recorded |
| 2. Prepare hosts | Follow [Proxmox preparation](../../platforms/proxmox/README.md#first-deployment-order), including optional [cluster/HA](../../platforms/proxmox/cluster-ha.md) and [SDN](../../platforms/proxmox/network-prerequisites.md#optional-sdn-for-guest-networks) now | Hosts, storage, networks, backups, and API access are tested |
| 3. Publish templates | Run the [local template workflow](../../platforms/proxmox/template-lifecycle.md#local-workflow); use the [Talos image guide](../../platforms/proxmox/talos-template.md) for cluster nodes | Approved Linux/Talos clones boot on their intended hosts |
| 4. Build the control cluster | Follow the shared [Talos bootstrap procedure](../../platforms/talos/bootstrap.md), then install GitOps | Nodes and API are healthy; recovery inputs exist outside the cluster |
| 5. Add authority services | Use the [identity foundation](../shared-services/identity.md), then [Vault](../shared-services/vault.md) and optional [HSM](../../security/usb-hsm-active-active-blueprint.md) guides | Each selected service passes its checks and has an independent recovery path |
| 6. Add Day 2 clients | Follow the [service sequence](bootstrap.md#day-2-service-sequence), including early inventory documentation | SSO and local break-glass access both work |

Step 4 is the Talos control-cluster route. Linux authority VMs are a separate
route and can be deployed after step 3; they do not require Kubernetes. Do not
deploy a second identity or secret service simply because a cluster placeholder
exists. Choose one lifecycle owner per service.

## Getting started

After preparing hosts, **Day 0-1: templates before VMs.** From
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

Next choose [Talos bootstrap](../../platforms/talos/bootstrap.md) or the
[Linux identity VM guide](../shared-services/identity.md). Run shared commands
from the tier repository root so they use its inventory and state. Replace
`homelab` in paths if you chose another prefix.

## Find your way

| Need | Guide |
| --- | --- |
| Bootstrap, recovery, and Day 2 services | [Tier 0 bootstrap and recovery](bootstrap.md) |
| AlmaLinux, Rocky Linux, and Talos templates | [Template lifecycle and CD](../../platforms/proxmox/template-lifecycle.md) |
| Tier boundaries | [Tier model](../../architecture/tier-model.md) |
| Hardware ownership and future workload requests | [Infrastructure control](../../architecture/infrastructure-control.md) |
| Network design | [Network architecture](../../architecture/network.md) |
| Inventory and upstream updates | [Generated repository model](../../reference/generated-repository-model.md) |
| Command reference | [Repository scripts](../../reference/repository-scripts.md) |

## Repository structure

- `ansible/`: tier service playbooks and roles, inventory, group vars, and configuration
- `terraform/`: Linux infrastructure setups and environment inputs
- `templates/`, `terraform/templates/`, and `ci/`: image catalog, template publication, and CD jobs
- `terraform/modules/` and `packer/`: template implementations and custom-build scaffolds
- `bootstrap/`: Talos and infrastructure bootstrap skeletons
- `clusters/tier0/`: cluster-service skeletons
- `scripts/`: local template publisher and entry points to shared deployment helpers

The Linux setup scripts do not bootstrap Talos or deploy the cluster services.
The [bootstrap and recovery reference](bootstrap.md) distinguishes working
automation from skeletons and records the recovery boundary.
