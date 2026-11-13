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

Begin with the [Foundation steps](../../03-deployment/foundation/README.md):
first manual Linux template, then the
[bootstrap execution host](../../03-deployment/foundation/bootstrap/README.md), then template adoption/publication.
The bootstrap guide covers local tools, artifacts, Proxmox CA/API access and repository generation;
record [project conventions](../../04-development/project-documentation.md#start-with-project-values) there.
Verify the foundation,
then follow the [numbered capability stages](../../03-deployment/README.md), beginning
with [Software intake](../../03-deployment/stage-1-software-intake/README.md).
Each stage's README explains its numbered steps with diagrams and acceptance checks;
options branch from the relevant decision and return to the main path.

| Stage | Tier 0 responsibility | Walkthrough |
| --- | --- | --- |
| **1: Software intake** | Configure approved consumers; Tier 2 owns the ordinary proxy/cache | [Software intake](../../03-deployment/stage-1-software-intake/README.md) |
| **2: Protected logging** | Independent collector, protected evidence and offline inspection | [Logging, Steps 1–16](../../03-deployment/stage-2-logging/README.md) |
| **3: Cryptographic trust** | Offline root and online issuer; optional hardware protection and approved Tier 0 consumers of verified intake | [Trust](../../03-deployment/stage-3-trust/README.md) |
| **4: Kubernetes** | Control-cluster lifecycle, basic platform, node/API logging and recovery | [Kubernetes, Steps 1–19](../../03-deployment/stage-4-kubernetes/README.md) |
| **5: Identity** | Dedicated FreeIPA pair and Keycloak/OIDC on the accepted cluster | [Identity](../../03-deployment/stage-5-identity/README.md) |
| **6: Secrets** | Vault, audit and recovery; supporting NetBox, Headlamp and independent alerts | [Secrets](../../03-deployment/stage-6-secrets/README.md), [monitoring](../../03-deployment/stage-6-secrets/procedures/independent-monitoring.md) |
| **7: Delivery** | Retain independent Flux/recovery; Tier 1 selects its application controller | [Delivery](../../03-deployment/stage-7-delivery/README.md) |
| **8: Observability** | Own Proxmox/BMC collectors and credentials; export approved metrics/evidence copies to Tier 1 | [Infrastructure monitoring](../../03-deployment/stage-8-observability/step-13-infrastructure-monitoring.md) |
| **9: Development platform** | Install the dedicated runner and Vault CI policy; hand over original state with explicit CI trust | [Development platform](../../03-deployment/stage-9-development/README.md) |
| **10: Lab environments** | Approve bounded infrastructure requests; an automated allocator is not supplied | [Lab environments](../../03-deployment/stage-10-lab-environments/README.md) |

Select optional [HA](../../03-deployment/foundation/proxmox/step-1b-cluster-ha.md) and
[SDN](../../03-deployment/foundation/proxmox/step-1c-sdn.md) before important guests.
Protect access and backups from the first step; the
[support map](../../08-reference/implementation-support.md) identifies automation and remaining integration.

## Getting started

**Templates before managed VMs.** One manual Linux template creates the bootstrap
VM first; the [bootstrap guide](../../03-deployment/foundation/bootstrap/README.md)
prepares the execution host before API publication.

Run from **`<prefix>-tier-0/`**.

```bash
bash scripts/proxmox-templates.sh init
```

Follow [Foundation Steps 4-10](../../03-deployment/foundation/README.md#step-4-configure-the-template-catalog)
to configure, adopt/publish, apply and qualify images and recovery. Tier 0 approves references in the
[shared catalog](../../08-reference/template-catalog.md); other tiers consume them.
Verified existing templates are valid. No hosted CI or cluster is required.
Later changes use [template maintenance](../../05-operations/01-hosting/templates/template-lifecycle.md#local-workflow).

After templates, accept [software intake](../../03-deployment/stage-1-software-intake/README.md),
then establish [foundational syslog](../../03-deployment/stage-2-logging/README.md)
with the Tier 0 `syslog` setup. Prepare storage/TLS before installing its isolated
receiver, then follow its producer, NAS checkpoint and independent-backup recipes.
NAS snapshots/access custody and live acceptance remain commissioning gates; HA is a separate selection.
After the trust stage, initialize the Kubernetes control cluster:

Run from **`<prefix>-tier-0/`**.

```bash
bash scripts/kubernetes-cluster.sh init
```

Follow the numbered [Kubernetes actions](../../03-deployment/stage-4-kubernetes/README.md)
to configure, plan, deploy and accept the cluster. The [common cluster reference](../../03-deployment/stage-4-kubernetes/procedures/kubernetes.md)
and [Talos implementation](../../03-deployment/stage-4-kubernetes/procedures/talos-terraform.md) explain details.
The [Identity actions](../../03-deployment/stage-5-identity/README.md)
deploy the separate FreeIPA pair. Linux setup commands use tier-local inventory
and state; they do not bootstrap Kubernetes or install cluster services.
Replace `homelab` in paths if another prefix was selected.

<a id="find-your-way"></a>

## Navigation

| Need | Guide |
| --- | --- |
| Dependencies, readiness checks, recovery | [Deployment stages](../../03-deployment/README.md) |
| Target placement and certificate trust | [Control platform design](../../01-architecture/03-reference-platform.md) |
| Network/VLAN choices and policy | [Network map](../../01-architecture/05-networking/README.md) |
| File locations and commands | [Code map](../../04-development/code-layout.md), [scripts](../../08-reference/repository-scripts.md) |
| Ownership and future workload requests | [Infrastructure control](../../01-architecture/04-hosting/02-provisioning.md) |

## Repository structure

- `terraform/deployments/`: runnable deployments and local inputs
- `terraform/modules/`: infrastructure building blocks owned by this tier
- `ansible/`: inventory, group vars, playbooks, and service roles
- `templates/`, `packer/`, `ci/`: image recipes, optional builds, publication jobs
- `clusters/tier0/`: optional project GitOps definitions; native installers live in `ansible/roles/`
- `scripts/`: template/cluster commands and entry points to shared Linux helpers
