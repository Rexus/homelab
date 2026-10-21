# Kubernetes platform path

**Working repository:** `<prefix>-tier-1` (source: `tier-1/`) for the delivery platform.
Use [Tier 1 cluster IaC](../../../../tier-1/terraform/deployments/kubernetes/) and
[clusters/tier1/](../../../../tier-1/clusters/tier1/); other clusters use their own tier repositories.

**Design:** [delivery runtimes](../../../architecture/delivery/README.md).

## Table of contents

- [Purpose](#purpose)
- [Dependency direction](#dependency-direction)
- [Starting shape](#starting-shape)
- [Delivery selection](#delivery-selection)
- [Cluster foundation](#cluster-foundation)
- [Read more](#read-more)

## Purpose

Use this path when the private cloud needs an application runtime layer above
the Proxmox VM foundation.

For installation and node-OS choices, follow the common
[Kubernetes cluster guide](../../stage-3-identity/procedures/kubernetes.md).
Use the [Tier 1 checklist](../../../paths/tier-1/README.md) for platform services or the
[Tier 0 checklist](../../../paths/tier-0/README.md) for the independent control cluster.
This page explains application-platform choices. Every tier has its own
[Kubernetes Terraform root](../../stage-3-identity/procedures/talos-terraform.md), currently implemented
with Talos; GitOps and cluster-service
directories remain starters rather than a complete platform installer.

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

Use the independent [Tier 1 cluster topology](../../../architecture/compute/kubernetes.md).
The compact start runs trusted workloads on three control planes; add workers
before reserving control planes for Kubernetes components:

| Role | Example name | Notes |
| --- | --- | --- |
| control plane | `platform-k8ctl-1` to `platform-k8ctl-3` | Three nodes, scheduling configurable |
| worker | Project-defined nodes | Optional infrastructure/stateful/compute pools |
| ingress | cluster-native ingress | consumes the shared edge path instead of replacing it |
| Delivery | Argo CD or Spinnaker; unselected | Application GitOps or release orchestration; scoped credentials and independent recovery |

Use separate clusters for stronger project isolation when shared namespaces,
RBAC, and policy are not enough.

## Delivery selection

Record [A: Argo CD or B: Spinnaker](../../../architecture/delivery/controllers.md) in the
project architecture before installation. Follow the selected product's official
installation procedure with pinned manifests/images, then configure sources,
scoped destinations/accounts, RBAC/OIDC and secret handling. No controller installer
is supplied. Do not bootstrap Tier 1 Flux simply because Tier 0 uses it.

Test approved delivery, rejected targets, health gates, rollback and recovery
without the normal delivery service. Never register Tier 0 as a Tier 1 delivery target.

## Cluster foundation

Follow the common [cluster foundation checklist](../../stage-3-identity/procedures/kubernetes.md#cluster-foundation)
for networking, reconciliation, secrets, persistence, TLS, and databases.
It applies to all tiers independently of node OS and owns the readiness gates.
Then continue with the [Tier 1 service checklist](../../../paths/tier-1/README.md).

## Read more

- [Delivery stage](../README.md#step-2-enable-protected-execution)
- [Private cloud model](../../../architecture/private-cloud.md)
- [Shared services model](../../../architecture/service-boundaries.md)
- [Telemetry procedure](../../stage-6-observability/step-1b-dedicated-vms.md)
