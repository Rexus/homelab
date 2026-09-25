# Kubernetes platform path

## Table of contents

- [Purpose](#purpose)
- [Dependency direction](#dependency-direction)
- [Starting shape](#starting-shape)
- [Cluster foundation](#cluster-foundation)
- [Read more](#read-more)

## Purpose

Use this path when the private cloud needs an application runtime layer above
the Proxmox VM foundation.

For installation and node-OS choices, follow the shared
[Kubernetes cluster guide](../../platforms/kubernetes/README.md).
Use the [Tier 1 checklist](../tier-1/README.md) for platform services or the
[Tier 0 checklist](../tier-0/README.md) for the independent control cluster.
This page explains application-platform choices. Tier 0 has a
[Kubernetes Terraform root](../../platforms/talos/terraform.md), currently implemented
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

Follow the common [cluster foundation checklist](../../platforms/kubernetes/README.md#cluster-foundation)
for networking, reconciliation, secrets, persistence, TLS, and databases.
It applies to both tiers independently of node OS and owns the readiness gates.
Then continue with the [Tier 1 service checklist](../tier-1/README.md).

## Read more

- [Application platform path](README.md)
- [Private cloud model](../../architecture/private-cloud.md)
- [Shared services model](../../architecture/shared-services.md)
- [System control path](../system-control/README.md)
