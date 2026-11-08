# Kubernetes platform path

**Working repository:** `<prefix>-tier-1` (source: `tier-1/`) for the delivery platform.
Use [Tier 1 cluster IaC](../../../../tier-1/terraform/deployments/kubernetes) and
[clusters/tier1/](../../../../tier-1/clusters/tier1); other clusters use their own tier repositories.

**Design:** [delivery runtimes](../../../architecture/software/README.md).

## Table of contents

- [Purpose](#purpose)
- [Step 1: Initialize and edit Tier 1 inputs](#initialize-tier-1)
- [Step 2: Deploy and qualify the cluster](#deploy-tier-1)
- [Step 3: Cluster foundation](#cluster-foundation)
- [Capacity and delivery choices](#capacity-and-delivery-choices)
- [Read more](#read-more)

## Purpose

Create the Tier 1 application cluster, then install its basic platform. The same
[cluster implementation](../../stage-4-kubernetes/procedures/talos-terraform.md)
is reused with tier-owned inventory, state and credentials. Tier 0 remains independent.

<a id="initialize-tier-1"></a>

## Step 1: Initialize and edit Tier 1 inputs

From the **Tier 1 root**:

Run from `<prefix>-tier-1/`.

```bash
bash scripts/kubernetes-cluster.sh init
```

Retain the existing cluster's original identities and state.

Edit these files:

```text
# Edit in <prefix>-tier-1/
ansible/inventory/hosts.yml
# Edit: Tier 1 talos_control_plane / talos_workers hosts
ansible/group_vars/talos.yml
# Edit: Their actual reserved platform_host_ips
terraform/deployments/kubernetes/terraform.tfvars
# Edit: Cluster name/private API endpoint, unique VMIDs, approved template/source node, releases/installer,
#       Tier 1 attachment and native patches
```

Complete the [common cluster configuration](../../stage-4-kubernetes/procedures/talos-terraform.md#configure),
including image access, firmware, CNI patches and an independent API endpoint.
Use Tier 1's source inputs throughout. This command does **not** load `.env.local`:
supply `PROXMOX_VE_ENDPOINT` and `PROXMOX_VE_API_TOKEN` through the accepted protected environment.

<a id="deploy-tier-1"></a>

## Step 2: Deploy and qualify the cluster

Run from `<prefix>-tier-1/`.

```bash
bash scripts/kubernetes-cluster.sh plan
```

Review the saved plan's addresses, disks, templates and failure-domain placement, then apply:

```bash
# Run from <prefix>-tier-1/
bash scripts/kubernetes-cluster.sh apply
bash scripts/kubernetes-cluster.sh credentials
```

Apply uses the saved plan without an extra Terraform `yes` prompt. It creates/bootstrap-configures
the selected cluster; it is not an adoption/recovery command. Keep the exported
`secrets/talos/` client files and original state under independent recovery custody.
Continue to **Step 3: Cluster foundation** below before any application installation.

<a id="cluster-foundation"></a>

## Step 3: Cluster foundation

Follow the common [cluster foundation checklist](../../stage-4-kubernetes/procedures/kubernetes.md#cluster-foundation)
for networking, reconciliation, secrets, persistence, TLS, and databases.
Use the same [native basic-platform procedure](../../stage-4-kubernetes/procedures/basic-platform.md)
from the **Tier 1 repository**, with its own
[playbook](../../../../tier-1/ansible/playbooks/deployment/cluster-platform.yml) and
[inputs](../../../../tier-1/ansible/group_vars/cluster_platform.yml.example).
Shared's `cluster_platform` role executes the add-ons; Tier 1 owns their selection,
values, cluster credentials and resources. No add-on code is copied between tiers.

Create the local inputs:

Run from `<prefix>-tier-1/`.

```bash
cp -n ansible/group_vars/cluster_platform.yml.example ansible/group_vars/cluster_platform.yml
```

Edit these files using the fields below:

```text
# Edit in <prefix>-tier-1/
ansible/group_vars/cluster_platform.yml
# Edit: Cluster context, selected components, chart/image pins, storage, network and DNS inputs.
```

Edit `ansible/group_vars/cluster_platform.yml`: Tier 1's kubeconfig/context, exact chart pins, image access,
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
# Run from <prefix>-tier-1/
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/cluster-platform.yml \
  -e @ansible/group_vars/cluster_platform.yml
```

With accepted inputs and the explicit Tier 1 context, apply the same selection:

```bash
# Run from <prefix>-tier-1/
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/cluster-platform.yml \
  -e @ansible/group_vars/cluster_platform.yml -e cluster_platform_action=apply
```

The common procedure owns add-on prerequisites and readiness gates, including the
distinction between installing CloudNativePG and creating an application database.
After accepting CNI, logging, storage, ingress, TLS and database-controller gates,
return to [Stage 7 Step 2](../README.md#step-2-select-and-qualify-delivery).

<a id="dependency-direction"></a>
<a id="starting-shape"></a>
<a id="delivery-selection"></a>

## Capacity and delivery choices

The starter has three schedulable control-plane VMs, `pctl-1` through
`pctl-3`. Add workers in the tier-local inputs before reserving control
planes for Kubernetes components. Review rendered Harbor, Spinnaker, Observability
and GitLab requests; starter sizing is not capacity for every later service.
Retain headroom for a physical-host failure, upgrades and recovery.

Select one [Argo CD or Spinnaker path](../README.md#step-2-select-and-qualify-delivery).
Keep bootstrap Git/OCI and Tier 0 recovery independent of the Tier 1 cluster.
Separate clusters remain an option where namespace/RBAC isolation is insufficient.

## Read more

- [Cluster topology and capacity](../../../architecture/hosting/kubernetes.md)
- [Delivery choices and authority](../../../architecture/software/controllers.md)
- [Shared service dependencies](../../../architecture/service-boundaries.md)
- [Tier 1 deployment checklist](../../../paths/tier-1/README.md)
