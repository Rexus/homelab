# Tier 0

Tier 0 owns Proxmox, network and storage control, all VM templates, and the
trust services beneath the platform. It must remain recoverable without
Tier 1 or Tier 2. Start here for a new installation.

## Table of contents

- [Deployment order](#deployment-order)
- [Getting started](#getting-started)
- [Navigation](#navigation)
- [Repository structure](#repository-structure)

## Deployment order

Record [project conventions](../../development/project-documentation.md#start-with-project-values)
and prepare [local tools](../../development/local-setup.md) first.
Follow the [six capability stages](../../deployment/README.md).
Each stage's README explains its numbered steps with diagrams and acceptance checks;
options branch from the relevant decision and return to the main path.

| Stage | Tier 0 responsibility | Walkthrough |
| --- | --- | --- |
| **1: Compute foundation** | Proxmox, networks, templates, independent tools/state and protected logging | [Foundation](../../deployment/stage-1-foundation/README.md) |
| **2: Cryptographic trust** | Offline root and online issuer; optional hardware protection | [Trust](../../deployment/stage-2-trust/README.md) |
| **3: Identity and Kubernetes** | Dedicated FreeIPA pair and control cluster | [Identity and Kubernetes](../../deployment/stage-3-identity-runtime/README.md) |
| **4: Control services** | Keycloak, Vault, NetBox, Headlamp and monitoring | [Control services](../../deployment/stage-4-control-services/README.md) |
| **5: Delivery and handover** | Protected Tier 0 runner; Tier 1 owns delivery services | [Delivery and handover](../../deployment/stage-5-delivery/README.md) |
| **6: Workload provisioning** | Approve and execute infrastructure requests | [Workload provisioning](../../deployment/stage-6-workloads/README.md) |

Select optional [HA](../../deployment/stage-1-foundation/step-1b-cluster-ha.md) and
[SDN](../../deployment/stage-1-foundation/step-1c-sdn.md) before important guests.
Protect access and backups from the first step; the
[support map](../../reference/implementation-support.md) identifies automation and remaining integration.

## Getting started

**Templates before VMs.** From `homelab-iac/homelab-tier-0`:

```bash
bash scripts/proxmox-templates.sh init
```

Follow the [local template workflow](../../administration/compute/template-lifecycle.md#local-workflow)
to configure, plan, publish, and test images. Tier 0 approves references in the
[shared catalog](../../reference/template-catalog.md); other tiers consume them.
Verified existing templates are valid. No hosted CI or cluster is required.

After templates, establish [foundational syslog](../../deployment/stage-1-foundation/procedures/syslog.md)
with the Tier 0 `syslog` setup. Receiver/HA/retention installation remains project integration.
After the trust stage, initialize the Kubernetes control cluster:

```bash
bash scripts/kubernetes-cluster.sh init
```

Follow the [common Kubernetes procedure](../../deployment/stage-3-identity-runtime/procedures/kubernetes.md)
and [current Talos implementation](../../deployment/stage-3-identity-runtime/procedures/talos-terraform.md)
to configure, plan, and deploy. The [identity VM guide](../../deployment/stage-3-identity-runtime/procedures/freeipa.md)
covers the separate FreeIPA pair. Linux setup commands use tier-local inventory
and state; they do not bootstrap Kubernetes or install cluster services.
Replace `homelab` in paths if another prefix was selected.

<a id="find-your-way"></a>

## Navigation

| Need | Guide |
| --- | --- |
| Dependencies, readiness checks, recovery | [Deployment stages](../../deployment/README.md) |
| Target placement and certificate trust | [Control platform design](../../architecture/reference-platform.md) |
| Network/VLAN choices and policy | [Network map](../../architecture/networking/README.md) |
| File locations and commands | [Code map](../../development/code-layout.md), [scripts](../../reference/repository-scripts.md) |
| Ownership and future workload requests | [Infrastructure control](../../architecture/compute/provisioning.md) |

## Repository structure

- `terraform/deployments/`: runnable deployments and local inputs
- `terraform/modules/`: infrastructure building blocks owned by this tier
- `ansible/`: inventory, group vars, playbooks, and service roles
- `templates/`, `packer/`, `ci/`: image recipes, optional builds, publication jobs
- `clusters/tier0/`: cluster-service skeletons
- `scripts/`: template/cluster commands and entry points to shared Linux helpers
