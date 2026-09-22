# Kubernetes platform path

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
| GitOps | controller inside the cluster | consumes source control and secret-platform paths |

Use separate clusters for stronger project isolation when shared namespaces,
RBAC, and policy are not enough.

## Read more

- [Application platform path](README.md)
- [Private cloud model](../../architecture/private-cloud.md)
- [Shared services model](../../architecture/shared-services.md)
- [System control path](../system-control/README.md)
