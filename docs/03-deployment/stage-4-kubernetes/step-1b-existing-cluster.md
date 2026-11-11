# Step 1b: Use an existing Talos cluster

**Branch from:** [Step 1](README.md#step-1-create-the-kubernetes-cluster), instead of creating a new cluster.
**Change:** Consume an accepted cluster whose existing owner manages its nodes through IaC.
**Return:** [Step 2](README.md#step-2-establish-the-basic-platform) after the checks below.
**Working repository:** the consuming tier's `<prefix>-tier-0`, `<prefix>-tier-1` or `<prefix>-tier-2`.

New clusters use the [Terraform/Talos path](procedures/talos-terraform.md).
This option creates no VMs and does not generate replacement cluster secrets or Terraform state.
The current platform installers target Talos; another node OS requires a qualified integration.

## Contents

1. [Accept the existing ownership](#1-accept-the-existing-ownership)
2. [Provide the existing clients and inputs](#2-provide-the-existing-clients-and-inputs)
3. [Verify and hand over](#verify-and-hand-over)

<a id="bootstrap-kubernetes-with-talos"></a>

<a id="prepare"></a>

## 1. Accept the existing ownership

Record the cluster's owner, management endpoint, retained node definitions/state,
machine-secret recovery, backups and failure domains in the project architecture record.
The owner supplies DNS/time, restricted image supply and an independent API endpoint.
Keep one writer per node/state root; a new empty Terraform state cannot adopt existing nodes.

Require the same [node networking and basic-platform settings](procedures/basic-platform.md#prepare-talos)
as the new-cluster path. The existing owner's IaC applies any accepted node changes before this handover.
Do not create manual clones or modify the reusable template to follow this option.

<a id="generate-configuration"></a>
<a id="configure-and-bootstrap"></a>

## 2. Provide the existing clients and inputs

Obtain the existing protected kubeconfig and Talos client configuration from the owner.
Retain their original cluster/CA identities and independent recovery copies.
Set the consuming tier's `ansible/group_vars/cluster_platform.yml` and the selected platform
procedure's context, node addresses and Talos client paths to those existing values.

On the **deployment controller**, select the supplied kubeconfig:

```bash
read -r -p 'Existing protected kubeconfig path: ' KUBECONFIG
export KUBECONFIG
kubectl config current-context
kubectl get nodes -o wide
```

Stop on an unexpected context, node or identity. Use the matching accepted `talosctl`
and Kubernetes client versions from the [cluster prerequisites](procedures/talos-terraform.md).

<a id="verify-and-hand-over"></a>

## 3. Verify and hand over

1. Have the existing owner verify control-plane health, etcd recovery and physical failure placement.
2. Confirm the supplied API and Talos configuration work from the deployment controller.
3. Preserve the original inputs/state and use [Stage 4, Step 2](README.md#step-2-establish-the-basic-platform)
   for the platform's native installers. Do not rerun new-cluster bootstrap on this cluster.

For later API-server identity configuration, use the existing owner's qualified
[SSO integration](../stage-5-identity/procedures/kubernetes-sso.md); retain the original
node lifecycle and state ownership. This option does not claim live acceptance for an arbitrary cluster.

## Recovery

The existing owner retains the original node definitions, Talos machine secrets and etcd recovery set.
Use the [original-state and etcd procedure](../../05-operations/06-resilience/recovery/original-state-etcd.md)
with that owner; do not regenerate cluster identities or apply a new empty state to recover this installation.
