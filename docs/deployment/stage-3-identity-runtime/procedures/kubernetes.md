# Kubernetes clusters

**Working repository:** the cluster owner's `<prefix>-tier-0`, `<prefix>-tier-1`
or `<prefix>-tier-2` (source: matching `tier-N/`). Stage 3 uses Tier 0.

**Design:** [cluster runtime variants](../../../architecture/compute/README.md).

The goal is an independently recoverable Kubernetes cluster on Proxmox.
Tier 0 uses it for control services; Tier 1 can use a separate cluster for
shared platform services; Tier 2 has its own workload cluster. The node operating
system is an implementation choice, not the name or purpose of the platform.

## Table of contents

- [Prerequisites](#prerequisites)
- [Repository locations](#repository-locations)
- [Implementation choice](#implementation-choice)
- [Deploy the cluster](#deploy-the-cluster)
- [Cluster foundation](#cluster-foundation)
- [Continue reading](#continue-reading)
- [References](#references)

## Prerequisites

Prepare [Proxmox](../../stage-1-foundation/procedures/proxmox.md#first-deployment-order), approved node
images, networks, storage, API access, and an execution host outside the cluster.
Record the owning tier, node allocations, cluster API endpoint, and recovery
inputs. Tier 0 must bootstrap and recover without Tier 1 or Tier 2 services.

An existing cluster is a valid prerequisite when it meets the same ownership,
network, access, and recovery requirements. Do not run a new-cluster bootstrap
against existing resources as an adoption procedure.

## Repository locations

Choose one row and work from that repository's root. The same relative paths
exist in all tiers, but each cluster has its own resources, inputs, credentials and state.

| Cluster | Working repository | Terraform root | Host/IP inputs | Service manifests |
| --- | --- | --- | --- | --- |
| Control | `<prefix>-tier-0` | [terraform/deployments/kubernetes/](../../../../tier-0/terraform/deployments/kubernetes/) | [ansible/inventory/](../../../../tier-0/ansible/inventory/) and [ansible/group_vars/talos.yml.example](../../../../tier-0/ansible/group_vars/talos.yml.example) | [clusters/tier0/](../../../../tier-0/clusters/tier0/) |
| Platform | `<prefix>-tier-1` | [terraform/deployments/kubernetes/](../../../../tier-1/terraform/deployments/kubernetes/) | [ansible/inventory/](../../../../tier-1/ansible/inventory/) and [ansible/group_vars/talos.yml.example](../../../../tier-1/ansible/group_vars/talos.yml.example) | [clusters/tier1/](../../../../tier-1/clusters/tier1/) |
| Workload | `<prefix>-tier-2` | [terraform/deployments/kubernetes/](../../../../tier-2/terraform/deployments/kubernetes/) | [ansible/inventory/](../../../../tier-2/ansible/inventory/) and [ansible/group_vars/talos.yml.example](../../../../tier-2/ansible/group_vars/talos.yml.example) | [clusters/tier2/](../../../../tier-2/clusters/tier2/) |

Each tier's `scripts/kubernetes-cluster.sh` delegates to Shared's
[scripts/kubernetes-cluster.sh](../../../../shared/scripts/kubernetes-cluster.sh).
Shared owns that reusable command, not the Terraform root or cluster inventory.
See the [collection repository map](../../README.md#repository-locations) for source/generated paths.

## Implementation choice

| Choice | Role in this repository | Detailed procedure |
| --- | --- | --- |
| Talos | Current working node-OS example; the starting path for Kubernetes bootstrap | [Tier-local Terraform](talos-terraform.md) or [manual bootstrap](../step-2b-manual-cluster.md) |
| Immutable AlmaLinux or another node OS | Possible later implementation; cluster installation, upgrades, and recovery are not supplied for it | Record the choice in project documentation and implement its lifecycle in the owning tier |

Talos is the starting implementation because it provides a focused Kubernetes
node and bootstrap workflow. It is not an architectural requirement. Proxmox,
by contrast, is the chosen virtualization platform for this kit.

Each tier's public entry points are `terraform/deployments/kubernetes/` and
`scripts/kubernetes-cluster.sh`. They currently use the Talos provider and
Talos inventory groups. This is **not a multi-OS installer**: changing a template
ID or OS label does not switch the implementation. A different node OS needs
reviewed provisioning, configuration, upgrade, and recovery code, not another
state owner for the same cluster.

## Deploy the cluster

1. Select the owning tier and an implementation from the table above.
2. Publish or select the matching approved node image through Tier 0.
3. Configure that tier's inventory, node hardware, endpoint, and protected state.
4. Follow the implementation's installation procedure and readiness checks.
5. Continue with the common foundation below; retain OS-specific recovery inputs.

For the supplied implementation in any tier, run from that tier's repository root:

```bash
bash scripts/kubernetes-cluster.sh init
```

Then use the [Talos implementation guide](talos-terraform.md#configure) to
edit inputs, review a plan, and deploy. Initialization alone creates no cluster.
The same command operates on only the current tier's root, inventory and state.

## Cluster foundation

Use this checklist after Kubernetes bootstrap, regardless of node OS. Select
the owning repo's `clusters/tier0/`, `clusters/tier1/` or `clusters/tier2/` path.
**The directories are empty starters, not installed components.** Choose and pin implementations
before enabling reconciliation; the products below are concrete examples.

These are dependency gates, not merely YAML list order:

| Gate | Capability and example | Verify before consumers |
| --- | --- | --- |
| 1. Networking | CNI, cluster DNS, approved image access | Nodes Ready, cross-node pod traffic, DNS, and image pulls work |
| 2. Delivery | Tier 0 Flux [1]; Tier 1 Argo CD or Spinnaker, selected separately | Approved revisions reach only authorized targets; recovery does not require normal identity login |
| 3. Bootstrap secrets | Tier 0 Flux/SOPS; selected Tier 1/2 delivery needs its own secret/decryption integration and external recovery keys | A protected test Secret is available before workloads use it; controller installation alone does not provide secret handling |
| 4. Persistence | Storage driver/classes and backup destination | A disposable claim binds, survives pod recreation, and has a tested recovery path |
| 5. TLS and entry points | Certificate automation and ingress; cert-manager with an available issuer | Controller/webhook readiness, certificate issuance, and intended network access pass [2] |
| 6. Database | PostgreSQL operator; CloudNativePG, database instances, and backups | Required CRDs/operator, claims, database connections, and backup access work before applications [3] |

CNI must work before expecting GitOps controllers and ordinary pods to be
healthy. Follow the chosen implementation's networking bootstrap procedure;
do not install two competing CNIs.

Provide issuer credentials before requesting certificates; they must not
depend on a secret or identity service that has not been deployed yet. An
HTTP-based certificate challenge may need ingress first. Treat these as
explicit dependencies, not a universal certificate-controller-before-ingress
ordering. [5] The PostgreSQL operator does not supply every application's data
dependency; deploy required caches, object stores, or other databases separately.

Tier 0 uses Flux `dependsOn` with readiness/health checks for controllers, custom
resources, and consumers. Tier 1 uses the selected tool's dependency and health gates.
A Kustomize `resources` list does not enforce readiness or deployment phases. [4]

Continue with [Tier 0 control services](../../stage-4-control-services/README.md)
or the [Tier 1](../../../paths/tier-1/README.md) / [Tier 2 checklist](../../../paths/tier-2/README.md).
Shared procedures do not justify copying Tier 0 credentials or privileges into another tier.

## Continue reading

- [Cluster topology](../../../architecture/compute/kubernetes.md)
- [Delivery controller choices](../../../architecture/delivery/controllers.md)
- [Application-platform choices](../../stage-5-delivery/procedures/platform-cluster.md)
- [Tier ownership and recovery](../../../architecture/tier-ownership.md)
- [Cluster implementation and state](talos-terraform.md#state-and-lifecycle)

## References

Official guidance checked 2026-09-25. Use documentation matching pinned releases.

1. [Flux generic Git bootstrap](https://fluxcd.io/flux/installation/bootstrap/generic-git-server/).
2. [cert-manager installation](https://cert-manager.io/docs/installation/).
3. [CloudNativePG quickstart source](https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/quickstart.md) (learning example, not production settings).
4. [Flux Kustomization dependencies and health checks](https://fluxcd.io/flux/components/kustomize/kustomizations/#dependencies).
5. [cert-manager HTTP-01 solver dependencies](https://cert-manager.io/docs/configuration/acme/http01/).
