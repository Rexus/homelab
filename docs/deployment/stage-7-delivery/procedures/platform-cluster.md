# Kubernetes platform path

**Working repository:** `<prefix>-tier-1` (source: `tier-1/`) for the delivery platform.
Use [Tier 1 cluster IaC](../../../../tier-1/terraform/deployments/kubernetes) and
[clusters/tier1/](../../../../tier-1/clusters/tier1); other clusters use their own tier repositories.

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
[Kubernetes cluster guide](../../stage-4-kubernetes/procedures/kubernetes.md).
Use the [Tier 1 checklist](../../../paths/tier-1/README.md) for platform services or the
[Tier 0 checklist](../../../paths/tier-0/README.md) for the independent control cluster.
This page explains application-platform choices. Every tier has its own
[Kubernetes Terraform root](../../stage-4-kubernetes/procedures/talos-terraform.md), currently implemented
with Talos. The native basic-platform installer supplies selected add-ons; application
directories remain tier-owned delivery targets rather than automatically installed services.

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

The starter node sizes establish the cluster, not capacity for every later service.
Before installing Harbor, Spinnaker, Observability or GitLab, review their rendered
resource requests and add appropriately sized workers. Retain headroom for the
selected failures, upgrades, database recovery and JVM startup; VM count alone is not a budget.

Use separate clusters for stronger project isolation when shared namespaces,
RBAC, and policy are not enough.

## Delivery selection

Record [A: Argo CD or B: Spinnaker](../../../architecture/delivery/controllers.md) in the
project architecture before installation. Use the [native delivery installer](delivery-installer.md)
with explicit controller selection, pinned charts/images, scoped destinations/accounts,
RBAC/OIDC and secret handling. The
[Spinnaker native reference](../step-2b-spinnaker.md#installation-decision) supplies its
service base and SQL/cache dependencies; custom overlays remain optional.
Tier 0's Flux remains independently owned.

Test approved delivery, rejected targets, health gates, rollback and recovery
without the normal delivery service. Never register Tier 0 as a Tier 1 delivery target.

## Cluster foundation

Follow the common [cluster foundation checklist](../../stage-4-kubernetes/procedures/kubernetes.md#cluster-foundation)
for networking, reconciliation, secrets, persistence, TLS, and databases.
Use the same [native basic-platform procedure](../../stage-4-kubernetes/procedures/basic-platform.md)
from the **Tier 1 repository**, with its own
[playbook](../../../../tier-1/ansible/playbooks/deployment/cluster-platform.yml) and
[inputs](../../../../tier-1/ansible/group_vars/cluster_platform.yml.example).
Shared's `cluster_platform` role executes the add-ons; Tier 1 owns their selection,
values, cluster credentials and resources. No add-on code is copied between tiers.

Copy `ansible/group_vars/cluster_platform.yml.example` to its ignored `.yml`
counterpart and configure Tier 1's kubeconfig/context, exact chart pins, image access,
storage and issuer prerequisites. Retain Tier 1's explicit component selection:

```yaml
cluster_platform_components: [cilium, storage, cert_manager, ingress, cloudnative_pg]
```

**Omit Flux in Tier 1.** Tier 0 retains its independent Flux installation; choose
Argo CD or Spinnaker for Tier 1 application delivery after basic-platform acceptance.
Add `barman_cloud` only for the object/WAL database backup option. Live database
volumes remain on qualified Proxmox/Ceph-backed block CSI; NAS backup claims are separate.
From Tier 1, render and review:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/cluster-platform.yml \
  -e @ansible/group_vars/cluster_platform.yml
```

With accepted inputs and the explicit Tier 1 context, apply the same selection:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/cluster-platform.yml \
  -e @ansible/group_vars/cluster_platform.yml -e cluster_platform_action=apply
```

The common procedure owns add-on prerequisites and readiness gates, including the
distinction between installing CloudNativePG and creating an application database.
Then continue with the [Tier 1 service checklist](../../../paths/tier-1/README.md).

## Read more

- [Delivery stage](../README.md#step-2-select-and-qualify-delivery)
- [Private cloud model](../../../architecture/private-cloud.md)
- [Shared services model](../../../architecture/service-boundaries.md)
- [Telemetry procedure](../../stage-8-observability/step-1b-dedicated-vms.md)
