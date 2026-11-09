# Destroy or retire infrastructure

Remove a selected deployment deliberately, then reconcile its configuration and state.
For an outage with recoverable data, use [recovery](recovery.md) before choosing destruction.

**Work from:** the resource owner's tier root on the bootstrap or protected infrastructure runner.
**Before starting:** stop other writers, retain an accepted [recovery set](backups/recovery-set.md),
and identify the exact setup, environment and original state. Shared owns no inventory or state.

## Choose the task

| Situation | Procedure |
| --- | --- |
| Remove a Linux setup and its managed VMs/containers | [Destroy a setup](#destroy-a-setup) |
| Retire a published VM template | [Template removal](virtual-machines/template-lifecycle.md#how-is-a-template-removed) |
| Remove a Kubernetes cluster | [Cluster retirement boundary](#retire-a-kubernetes-cluster) |
| A resource was already deleted on the host | [Remove only its state binding](terraform-state.md#forget-a-deleted-resource) |
| Everything owned by one state is already gone | [Archive a retired deployment](terraform-state.md#archive-a-retired-deployment) |
| Recover a VM, failed host or complete platform | [Recovery scenarios](recovery.md#find-a-task) |

<a id="destroy-a-setup"></a>

## How is a setup destroyed?

1. Open the owning tier. Confirm the setup is listed in `.deployment-setups` and its original
   inventory, variables, API endpoint and state are available. Use the same environment/overrides
   used to create it; initialization from examples is not recovery of its inputs.
2. Check consumers and the recovery set. A Terraform destroy deletes all managed resources in
   that selected setup's state, not just the VM currently being investigated. [1]
3. Run the native wrapper. This example removes the Tier 2 cache setup:

   Run from **`<prefix>-tier-2/`** on the protected execution host.

   ```bash
   test -s .terraform/state/cache/prod/terraform.tfstate || exit 1
   bash scripts/deploy.sh cache --destroy --terraform-only --env-file .env.local
   ```

   Inspect the destruction plan and type `yes` only when every listed removal is intended.

   | Option | Use |
   | --- | --- |
   | `--env <environment>` | Required if the original setup used a non-default environment; default is `prod` |
   | `--plan-only` | Preview the destroy plan without execution |
   | `--auto-approve` | Non-interactive pipeline destruction after an independent approval gate |
   | Original inventory/variable overrides | Preserve the selected deployment context; see [script flags](../reference/repository-scripts.md) |

   The file check above selects the default local state. Adjust it to the recorded environment/backend;
   do not initialize a new empty state because the original file is missing. Kit `--env` and Terraform
   workspaces are separate selections; verify the original workspace through [state inspection](terraform-state.md).

4. Confirm the expected resources are absent in Proxmox. Retain the resulting state and recovery
   records; an empty successful state is not a reason to erase other setups in the same tier.
5. Remove retired entries from the owning tier's resource definitions/inventory and affected
   consumer references when they will no longer be deployed. Otherwise the next normal apply
   can recreate the declared resources. Keep backups under their independent retention policy.

**Expected:** only the selected setup is destroyed. The command does not uninstall Shared,
remove the manual bootstrap, erase backups or tear down the physical Proxmox/network foundation.
If destruction fails partly, preserve the updated state and investigate; do not clear state to hide survivors.

<a id="retire-a-kubernetes-cluster"></a>

## How is a Kubernetes cluster retired?

The supplied `kubernetes-cluster.sh` entry point has **no destroy action**. Do not substitute
the Linux setup wrapper: it selects a different state layout. Template publication also has
explicit destruction guards and its [separate removal path](virtual-machines/template-lifecycle.md#how-is-a-template-removed).

1. Retain accepted application/PVC copies, original cluster secrets and the required etcd history.
   Confirm that dependants have migrated or their loss is approved.
2. Stop delivery and provisioning writers. Identify the owning cluster's original state and exact
   resources using [state inspection](terraform-state.md#inspect-the-original-state).
3. Plan cluster decommissioning with the selected CSI, external volumes, DNS/API endpoints and
   service identities. Deleting a Kubernetes node VM does not establish that external data or
   consumer access has been retired. No generic automated cluster teardown is supplied.
4. After the reviewed manual/native retirement is complete, reconcile only that cluster's state
   and inputs. Keep the other tier deployments and independent backups intact.

## How is a new installation started after retirement?

1. Confirm old resources and competing automation cannot return under reused identities.
2. Retain old inputs/state privately. Generate a new collection in an empty directory through
   [foundation](../deployment/foundation/README.md), using accepted existing networks/storage where selected.
3. Follow the numbered installation path. Adopt any retained manual templates or other existing
   resources deliberately; do not copy retired state or saved plans into the new installation.

Recovering the original services instead uses the original state and backups through
[bootstrap-led recovery](recovery/bootstrap.md). The [offline bundle](../deployment/foundation/proxmox/bootstrap-offline.md)
prepares tooling, not a replacement for either service backups or guest package repositories.

## References

1. [Terraform destroy](https://developer.hashicorp.com/terraform/cli/commands/destroy).
