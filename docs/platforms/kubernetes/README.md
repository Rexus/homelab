# Kubernetes clusters

The goal is an independently recoverable Kubernetes cluster on Proxmox.
Tier 0 uses it for control services; Tier 1 can use a separate cluster for
shared platform services. The node operating system is an implementation
choice, not the name or purpose of the platform.

## Table of contents

- [Prerequisites](#prerequisites)
- [Implementation choice](#implementation-choice)
- [Deploy the cluster](#deploy-the-cluster)
- [Cluster foundation](#cluster-foundation)
- [Continue reading](#continue-reading)
- [References](#references)

## Prerequisites

Prepare [Proxmox](../proxmox/README.md#first-deployment-order), approved node
images, networks, storage, API access, and an execution host outside the cluster.
Record the owning tier, node allocations, cluster API endpoint, and recovery
inputs. Tier 0 must bootstrap and recover without Tier 1 or Tier 2 services.

An existing cluster is a valid prerequisite when it meets the same ownership,
network, access, and recovery requirements. Do not run a new-cluster bootstrap
against existing resources as an adoption procedure.

## Implementation choice

| Choice | Role in this repository | Detailed procedure |
| --- | --- | --- |
| Talos | Current working node-OS example; the starting path for Kubernetes bootstrap | [Tier 0 Terraform](../talos/terraform.md) or [manual Tier 0/Tier 1 bootstrap](../talos/bootstrap.md) |
| Immutable AlmaLinux or another node OS | Possible later implementation; cluster installation, upgrades, and recovery are not supplied for it | Record the choice in project documentation and implement its lifecycle in the owning tier |

Talos is the starting implementation because it provides a focused Kubernetes
node and bootstrap workflow. It is not an architectural requirement. Proxmox,
by contrast, is the chosen virtualization platform for this kit.

The public Tier 0 entry points are `terraform/deployments/kubernetes/` and
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

For the supplied Tier 0 implementation, run from its repository root:

```bash
bash scripts/kubernetes-cluster.sh init
```

Then use the [Talos implementation guide](../talos/terraform.md#configure) to
edit inputs, review a plan, and deploy. Initialization alone creates no cluster.
Tier 1 currently uses the manual procedure or project-owned automation.

## Cluster foundation

Use this checklist after Kubernetes bootstrap, regardless of node OS. Select
the owning repo's `clusters/tier0/` or `clusters/tier1/` path. **The directories
are empty starters, not installed components.** Choose and pin implementations
before enabling reconciliation; the products below are concrete examples.

These are dependency gates, not merely YAML list order:

| Gate | Capability and example | Verify before consumers |
| --- | --- | --- |
| 1. Networking | CNI, cluster DNS, approved image access | Nodes Ready, cross-node pod traffic, DNS, and image pulls work |
| 2. Reconciliation | GitOps controller; Flux with independent source credentials and the owning repo/path [1] | A reviewed change reconciles; source access does not require Day 2 identity |
| 3. Bootstrap secrets | Manifest decryption; SOPS with protected external recovery keys, following the [secret strategy](../../security/secret-strategy.md#gitops-bootstrap-secrets) | An encrypted test Secret reconciles before workloads use it |
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

With Flux, use `dependsOn` with readiness/health checks for controllers, custom
resources, and consumers. A Kustomize `resources` list does not enforce readiness
or deployment phases. [4]

Continue with [Tier 0 Day 2](../../paths/tier-0/bootstrap.md#day-2-service-sequence)
or the [Tier 1 checklist](../../paths/tier-1/README.md). Shared procedures do not
justify copying Tier 0 credentials or privileges into a Tier 1 cluster.

## Continue reading

- [Application-platform choices](../../paths/application-platform/kubernetes.md)
- [Tier ownership and recovery](../../architecture/tier-model.md)
- [Cluster implementation and state](../talos/terraform.md#state-and-lifecycle)

## References

Official guidance checked 2026-09-25. Use documentation matching pinned releases.

1. [Flux generic Git bootstrap](https://fluxcd.io/flux/installation/bootstrap/generic-git-server/).
2. [cert-manager installation](https://cert-manager.io/docs/installation/).
3. [CloudNativePG quickstart source](https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/quickstart.md) (learning example, not production settings).
4. [Flux Kustomization dependencies and health checks](https://fluxcd.io/flux/components/kustomize/kustomizations/#dependencies).
5. [cert-manager HTTP-01 solver dependencies](https://cert-manager.io/docs/configuration/acme/http01/).
