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
Verify the unnumbered [foundation prerequisites](../../deployment/foundation/README.md),
then follow the [numbered capability stages](../../deployment/README.md), beginning
with [Software intake](../../deployment/stage-1-software-intake/README.md).
Each stage's README explains its numbered steps with diagrams and acceptance checks;
options branch from the relevant decision and return to the main path.

| Stage | Tier 0 responsibility | Walkthrough |
| --- | --- | --- |
| **1: Software intake** | Configure approved consumers; Tier 2 owns the ordinary proxy/cache | [Software intake](../../deployment/stage-1-software-intake/README.md) |
| **2: Protected logging** | Independent collector, protected evidence and offline inspection | [Logging, Steps 1-3](../../deployment/stage-2-logging/README.md) |
| **3: Cryptographic trust** | Offline root and online issuer; optional hardware protection | [Trust](../../deployment/stage-3-trust/README.md) |
| **4: Kubernetes** | Control-cluster lifecycle, basic platform, node/API logging and recovery | [Kubernetes, Steps 1-3](../../deployment/stage-4-kubernetes/README.md) |
| **5: Identity** | Dedicated FreeIPA pair and Keycloak/OIDC on the accepted cluster | [Identity](../../deployment/stage-5-identity/README.md) |
| **6: Secrets** | Vault, audit and recovery; supporting NetBox, Headlamp and independent alerts | [Secrets](../../deployment/stage-6-secrets/README.md), [monitoring](../../deployment/stage-6-secrets/monitoring.md) |
| **7: Delivery** | Retain independent Flux/recovery; Tier 1 selects its application controller | [Delivery](../../deployment/stage-7-delivery/README.md) |
| **8: Observability** | Own Proxmox/BMC collectors and credentials; export approved metrics/evidence copies to Tier 1 | [Infrastructure monitoring](../../deployment/stage-8-observability/infrastructure-monitoring.md) |
| **9: Development platform** | Install the dedicated runner and Vault CI policy; hand over original state with explicit CI trust | [Development platform](../../deployment/stage-9-development/README.md) |
| **10: Lab environments** | Approve bounded infrastructure requests; an automated allocator is not supplied | [Lab environments](../../deployment/stage-10-lab-environments/README.md) |

Select optional [HA](../../deployment/foundation/step-1b-cluster-ha.md) and
[SDN](../../deployment/foundation/step-1c-sdn.md) before important guests.
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

After templates, accept [software intake](../../deployment/stage-1-software-intake/README.md),
then establish [foundational syslog](../../deployment/stage-2-logging/README.md)
with the Tier 0 `syslog` setup. Prepare storage/TLS before installing its isolated
receiver, then follow its producer, NAS checkpoint and independent-backup recipes.
NAS snapshots/access custody and live acceptance remain commissioning gates; HA is a separate selection.
After the trust stage, initialize the Kubernetes control cluster:

```bash
bash scripts/kubernetes-cluster.sh init
```

Follow the [common Kubernetes procedure](../../deployment/stage-4-kubernetes/procedures/kubernetes.md)
and [current Talos implementation](../../deployment/stage-4-kubernetes/procedures/talos-terraform.md)
to configure, plan, and deploy. The [identity VM guide](../../deployment/stage-5-identity/procedures/freeipa.md)
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
