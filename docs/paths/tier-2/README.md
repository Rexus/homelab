# Tier 2

Tier 2 owns public edge ingress, ordinary outbound caches, clients and application,
project and lab workloads. Keep workload definitions,
inventory, service code, and state here. Consume approved infrastructure and
platform services without moving their administrative authority into this repo.
Use the [shared template catalog](../../reference/template-catalog.md) for
approved image IDs and titles; keep only workload selections and service tags here.

## Deployment order

For public application access, deploy the [edge load-balancer set](../../deployment/stage-7-delivery/procedures/edge-proxy.md)
with the `edge` setup. Early [software intake](../../deployment/stage-1-software-intake/README.md)
uses `cache`. Both run from this repository with its own inventory and state.
Client VLANs are network-policy references, not provisioned server guests.
Keep clients, public edge and Tier 1 build/supply hosts in separate subnets.

For an independent Kubernetes workload runtime, use this tier's
`terraform/deployments/kubernetes/` and `bash scripts/kubernetes-cluster.sh init`.
Follow the [common cluster procedure](../../deployment/stage-4-kubernetes/procedures/kubernetes.md),
then record [scoped application delivery](../../architecture/delivery/controllers.md).
The Linux `lab` workflow below is a separate VM option, not the cluster installer.

| Step | What to do | Ready to continue when |
| --- | --- | --- |
| 1. Select the target | Record project naming choices and consume an approved VM network/template or an existing platform runtime | Resource allocation and access are approved |
| 2. Define the workload | For the shipped Linux example, initialize `lab`, then edit tier-local inventory, group vars, and Terraform inputs | Plan inputs describe only this tier's resources |
| 3. Provision and configure | An authorized operator reviews the plan and deploys the Linux baseline | Hosts are reachable only through approved paths and baseline checks pass |
| 4. Deliver the application | Add project-specific definitions under `workloads/` or the chosen runtime's delivery path | Service checks, backups, and rollback are tested |

The kit supplies the lab VM baseline, not a complete application deployment.
Future self-service requests are controlled by Tier 0; that controller is
[not implemented yet](../../architecture/compute/provisioning.md#delegated-provisioning).
Do not give workload users infrastructure-wide credentials to fill that gap.

## Getting started

From `homelab-iac/homelab-tier-2`:

```bash
bash ../homelab-shared/scripts/init-local-files.sh --setup lab --env test
```

Replace `homelab` with the prefix; omit `--env test` for production. Edit the
initialized inputs using the [script guide](../../reference/repository-scripts.md),
then have the authorized operator review:

```bash
bash ../homelab-shared/scripts/deploy.sh lab --env test --plan-only
```

Remove `--plan-only` only after review. Terraform and Ansible use this repo's
same inventory; no separate shared inventory is required.

<a id="find-your-way"></a>

## Navigation

- [Inventory and automation layout](../../development/code-layout.md)
- [Lab environments stage](../../deployment/stage-10-lab-environments/README.md)
- [VM placement and Proxmox HA](../../deployment/foundation/step-1b-cluster-ha.md#terraform-against-the-cluster)
- [Development-platform handover](../../deployment/stage-9-development/procedures/handover.md)
- [Project conventions and recovery records](../../development/project-documentation.md)
