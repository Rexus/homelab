# Kubernetes platform path

**Branch from:** [Stage 7, Step 1a](../README.md#step-1-create-the-platform-runtime) for a new cluster.
**Return:** to Step 1 readiness, then Step 2 controller selection. An accepted existing cluster uses
Step 1b and does not repeat this creation procedure.

**Working repository:** `<prefix>-tier-1` (source: `tier-1/`) for the delivery platform.
Use [Tier 1 cluster IaC](../../../../tier-1/terraform/deployments/kubernetes) and
[clusters/tier1/](../../../../tier-1/clusters/tier1); other clusters use their own tier repositories.

**Design:** [delivery runtimes](../../../01-architecture/10-delivery/README.md).

## Table of contents

- [Purpose](#purpose)
- [1. Initialize Tier 1 inputs](#initialize-tier-1)
- [2. Edit the cluster definition](#2-edit-the-cluster-definition)
- [3. Load the provider environment](#3-load-the-provider-environment)
- [4. Create the saved plan](#deploy-tier-1)
- [5. Review and apply that plan](#5-review-and-apply-that-plan)
- [6. Export the client credentials](#6-export-the-client-credentials)
- [7. Select the basic platform](#cluster-foundation)
- [8. Render the add-ons](#8-render-the-add-ons)
- [9. Apply and qualify the platform](#9-apply-and-qualify-the-platform)
- [Capacity and delivery choices](#capacity-and-delivery-choices)
- [Read more](#read-more)

## Purpose

Create the Tier 1 application cluster, then install its basic platform. The same
[cluster implementation](../../stage-4-kubernetes/procedures/talos-terraform.md)
is reused with tier-owned inventory, state and credentials. Tier 0 remains independent.

<a id="initialize-tier-1"></a>
<a id="step-1-initialize-and-edit-tier-1-inputs"></a>

## 1. Initialize Tier 1 inputs

Run from **`<prefix>-tier-1/`**.

```bash
bash scripts/kubernetes-cluster.sh init
```

Retain the existing cluster's original identities and state.

## 2. Edit the cluster definition

Edit in **`<prefix>-tier-1/`**.

- `ansible/inventory/hosts.yml`: Tier 1 `talos_control_plane` / `talos_workers` hosts
- `ansible/group_vars/talos.yml`: Their actual reserved `platform_host_ips`
- `terraform/deployments/kubernetes/terraform.tfvars`: Cluster name/private API endpoint, unique VMIDs,
  approved template/source node, releases/installer, Tier 1 attachment and native patches

Complete the [common cluster configuration](../../stage-4-kubernetes/procedures/talos-terraform.md#configure)
and its node-configuration steps before planning: image access, firmware, ordered CNI/logging
patches and an independent API endpoint. Use Tier 1's inputs throughout, then return here.

**Size before provisioning:** edit `nodes[*].size` or add workers in those same three files.
The `medium` starter is for cluster bootstrap; it is insufficient for the complete Delivery,
Observability and GitLab stack. Budget the selected releases' rendered CPU/memory requests,
storage and surviving-host capacity using the [cluster capacity design](../../../01-architecture/04-hosting/03-kubernetes.md).

## 3. Load the provider environment

On **the authorized execution host**, from **`<prefix>-tier-1/`**, load the already configured
`.env.local`. This script does not load it automatically. Keep shell tracing disabled.

```bash
set -a
source .env.local
set +a
export PROXMOX_VE_ENDPOINT="${PROXMOX_API_URL:?Set the real Proxmox API URL}"
export PROXMOX_VE_API_TOKEN="${PROXMOX_API_TOKEN_ID:?Set the token ID}=${PROXMOX_API_TOKEN_SECRET:?Set the token secret}"
```

An approved runner may inject those two native provider variables instead.
Retain verified Proxmox CA trust; no credentials are printed or committed.

<a id="deploy-tier-1"></a>
<a id="step-2-deploy-and-qualify-the-cluster"></a>

## 4. Create the saved plan

Run from **`<prefix>-tier-1/`**.

```bash
bash scripts/kubernetes-cluster.sh plan
```

Expect a saved plan. Unlike Linux `deploy.sh`, this cluster script requires separate `plan`
and `apply` commands; it has no `--plan-only` or `--auto-approve` flag.

## 5. Review and apply that plan

Review the plan's addresses, disks, templates and failure-domain placement.
Stop on unexpected replacements or removals. Apply only the reviewed plan:

Run from **`<prefix>-tier-1/`**.

```bash
bash scripts/kubernetes-cluster.sh apply
```

Apply uses the saved plan without an extra Terraform `yes` prompt. It creates/bootstrap-configures
the selected cluster; it is not an adoption/recovery command.

## 6. Export the client credentials

Run from **`<prefix>-tier-1/`** after a successful apply:

```bash
bash scripts/kubernetes-cluster.sh credentials
```

Expect protected client files in `secrets/talos/`. Back them up with the original state
under independent recovery custody. Continue below before installing applications.

<a id="cluster-foundation"></a>
<a id="step-3-cluster-foundation"></a>

## 7. Select the basic platform

Follow the common [cluster foundation checklist](../../stage-4-kubernetes/procedures/kubernetes.md#cluster-foundation)
for networking, reconciliation, secrets, persistence, TLS, and databases.
Use the same [native basic-platform procedure](../../stage-4-kubernetes/procedures/basic-platform.md)
from the **Tier 1 repository**, with its own
[playbook](../../../../tier-1/ansible/playbooks/deployment/cluster-platform.yml) and
[inputs](../../../../tier-1/ansible/group_vars/cluster_platform.yml.example).
Shared's `cluster_platform` role executes the add-ons; Tier 1 owns their selection,
values, cluster credentials and resources. No add-on code is copied between tiers.

Run from **`<prefix>-tier-1/`**.

```bash
cp -n ansible/group_vars/cluster_platform.yml.example ansible/group_vars/cluster_platform.yml
```

In **`<prefix>-tier-1/`**, edit `ansible/group_vars/cluster_platform.yml`: Tier 1's kubeconfig/context,
exact chart pins, image access, storage, network/DNS and issuer prerequisites.
Retain Tier 1's explicit component selection:

```yaml
cluster_platform_components: [cilium, storage, cert_manager, ingress, cloudnative_pg]
```

**Omit Flux in Tier 1.** Tier 0 retains its independent Flux installation; choose
Argo CD or Spinnaker for Tier 1 application delivery after basic-platform acceptance.
Add `barman_cloud` only for the object/WAL database backup option. Live database
volumes remain on qualified Proxmox/Ceph-backed block CSI; NAS backup claims are separate.

## 8. Render the add-ons

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/cluster-platform.yml \
  -e @ansible/group_vars/cluster_platform.yml -e cluster_platform_action=render
```

Review the private rendered resources using the
[basic-platform review](../../stage-4-kubernetes/procedures/basic-platform.md).
Confirm that all resources target Tier 1 and that Flux is absent.

## 9. Apply and qualify the platform

Apply the same selection with the accepted Tier 1 kubeconfig/context.
This Ansible action changes the cluster without another confirmation prompt.

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/cluster-platform.yml \
  -e @ansible/group_vars/cluster_platform.yml -e cluster_platform_action=apply
```

The common procedure owns add-on prerequisites and readiness gates, including the
distinction between installing CloudNativePG and creating an application database.
After accepting CNI, logging, storage, ingress, TLS and database-controller gates,
complete [cluster verification](../../stage-4-kubernetes/procedures/talos-terraform.md#verify-and-hand-over),
then return to [Stage 7 Step 2](../README.md#step-2-select-and-qualify-delivery).

<a id="dependency-direction"></a>
<a id="starting-shape"></a>
<a id="delivery-selection"></a>

## Capacity and delivery choices

The starter has three schedulable control-plane VMs, `pctl-1` through
`pctl-3`. Reserve control planes for Kubernetes components only after the selected
worker capacity exists; see the sizing decision in Step 2.

Select one [Argo CD or Spinnaker path](../README.md#step-2-select-and-qualify-delivery).
Keep bootstrap Git/OCI and Tier 0 recovery independent of the Tier 1 cluster.
Separate clusters remain an option where namespace/RBAC isolation is insufficient.

## Read more

- [Cluster topology and capacity](../../../01-architecture/04-hosting/03-kubernetes.md)
- [Delivery choices and authority](../../../01-architecture/10-delivery/02-controllers.md)
- [Shared service dependencies](../../../01-architecture/02-organization/README.md)
- [Tier 1 deployment checklist](../../../06-paths/tier-1/README.md)
