# Kubernetes platform path

## Table of contents

- [Purpose](#purpose)
- [Dependency direction](#dependency-direction)
- [Starting shape](#starting-shape)
- [Cluster foundation](#cluster-foundation)
- [Read more](#read-more)
- [References](#references)

## Purpose

Use this path when the private cloud needs an application runtime layer above
the Proxmox VM foundation.

For installation, follow the shared [Talos bootstrap procedure](../../platforms/talos/bootstrap.md).
Use the [Tier 1 checklist](../tier-1/README.md) for platform services or the
[Tier 0 checklist](../tier-0/README.md) for the independent control cluster.
This page explains application-platform choices; the supplied cluster code is
still a skeleton rather than a complete installer.

## Dependency direction

Kubernetes should consume the shared services when they exist:

These integrations are not prerequisites for creating the first control cluster.
Keep Tier 0 bootstrap and recovery independent of higher-tier services.

| Shared service | How Kubernetes uses it |
| --- | --- |
| identity | operator access, groups, SSO, and workload administration |
| PKI | internal TLS, ingress certificates, and service identity |
| secret platform | secrets, workload credentials, and dynamic secret patterns |
| edge | north-south entry into selected cluster services |
| cache | controlled outbound repository/update access for restricted clusters |
| system control | metrics, logs, traces, audit events, and alert routing |

Keep Proxmox as the infrastructure and VM boundary. Use Kubernetes as the
application runtime on top when GitOps, namespaces, policies, and horizontal
application scaling become the main need.

## Starting shape

Start with a small worker cluster when the goal is application deployment, not
full private-cloud multi-tenancy:

| Role | Example name | Notes |
| --- | --- | --- |
| control plane | `k8ctl-1` | control-plane node or small HA control-plane set |
| worker | `k8node-1` | application worker node |
| ingress | cluster-native ingress | consumes the shared edge path instead of replacing it |
| GitOps | controller inside the cluster | consumes independent source access and bootstrap secrets; later secret-platform integration is optional |

Use separate clusters for stronger project isolation when shared namespaces,
RBAC, and policy are not enough.

## Cluster foundation

Use this same checklist after [Talos bootstrap](../../platforms/talos/bootstrap.md)
for Tier 0 or Tier 1. Select the owning repo's `clusters/tier0/` or `clusters/tier1/`
path. **The directories are empty starters, not installed components.** Choose
and pin implementations before enabling reconciliation.

The following are dependency gates, not merely YAML list order:

| Gate | Deploy/configure | Verify before consumers |
| --- | --- | --- |
| 1. Networking | CNI, cluster DNS, approved image access | Nodes Ready, cross-node pod traffic, DNS, and image pulls work |
| 2. Reconciliation | Flux with independent source credentials and the owning repo/path [1] | A reviewed change reconciles; source access does not require Day 2 identity |
| 3. Bootstrap secrets | SOPS decryption and protected external recovery keys; follow the [secret strategy](../../security/secret-strategy.md#gitops-bootstrap-secrets) | An encrypted test Secret reconciles before workloads use it |
| 4. Persistence | Storage driver/classes and backup destination | A disposable claim binds, survives pod recreation, and has a tested recovery path |
| 5. TLS and entry points | cert-manager, an available issuer, and the selected ingress implementation | Controller/webhook readiness, certificate issuance, and intended network access pass [2] |
| 6. Database | CloudNativePG operator, then PostgreSQL instances and backups | Required CRDs/operator, claims, database connections, and backup access work before applications [3] |

CNI is part of initial cluster bring-up, even though the overall flow shows
Flux before basic services. The Talos fast path uses its default CNI. If choosing
a different CNI, install it through the release's bootstrap procedure before
expecting Flux and ordinary pods to be healthy; do not install two competing CNIs. [5]

Provide cert-manager's issuer credentials before requesting certificates; it
must not depend on a Vault or identity service that has not been deployed yet.
An HTTP-based certificate challenge may also need ingress first. Treat these as
explicit dependencies, not a universal cert-manager-before-ingress ordering. [6]
CNPG supplies PostgreSQL, not every application's data dependency; deploy any
required cache, object store, or additional database separately.

When implementing Flux resources, use `dependsOn` with readiness/health checks
for controllers, custom resources, and consumers. A Kustomize `resources` list
does not enforce readiness or deployment phases. [4]

Continue with [Tier 0 Day 2](../tier-0/bootstrap.md#day-2-service-sequence) or the
[Tier 1 checklist](../tier-1/README.md). Do not copy Tier 0 credentials or grant
Tier 0 privileges to a Tier 1 cluster merely because the procedure is shared.

## Read more

- [Application platform path](README.md)
- [Private cloud model](../../architecture/private-cloud.md)
- [Shared services model](../../architecture/shared-services.md)
- [System control path](../system-control/README.md)

## References

Official guidance checked 2026-09-23. Use documentation matching pinned releases.

1. [Flux generic Git bootstrap](https://fluxcd.io/flux/installation/bootstrap/generic-git-server/).
2. [cert-manager installation](https://cert-manager.io/docs/installation/).
3. [CloudNativePG quickstart source](https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/docs/src/quickstart.md) (learning example, not production settings).
4. [Flux Kustomization dependencies and health checks](https://fluxcd.io/flux/components/kustomize/kustomizations/#dependencies).
5. [Talos Cilium bootstrap](https://docs.siderolabs.com/kubernetes-guides/cni/deploying-cilium).
6. [cert-manager HTTP-01 solver dependencies](https://cert-manager.io/docs/configuration/acme/http01/).
