# Tier 2

Tier 2 owns application, project, and lab workloads. Keep workload definitions,
inventory, service code, and state here. Consume approved infrastructure and
platform services without moving their administrative authority into this repo.
Use the [shared template catalog](../../platforms/proxmox/template-catalog.md) for
approved image IDs and titles; keep only workload selections and service tags here.

## Deployment order

| Step | What to do | Ready to continue when |
| --- | --- | --- |
| 1. Select the target | Record project naming choices and consume an approved VM network/template or an existing platform runtime | Resource allocation and access are approved |
| 2. Define the workload | For the shipped Linux example, initialize `lab`, then edit tier-local inventory, group vars, and Terraform inputs | Plan inputs describe only this tier's resources |
| 3. Provision and configure | An authorized operator reviews the plan and deploys the Linux baseline | Hosts are reachable only through approved paths and baseline checks pass |
| 4. Deliver the application | Add project-specific definitions under `workloads/` or the chosen runtime's delivery path | Service checks, backups, and rollback are tested |

The kit supplies the lab VM baseline, not a complete application deployment.
Future self-service requests are controlled by Tier 0; that controller is
[not implemented yet](../../architecture/infrastructure-control.md#delegated-provisioning).
Do not give workload users infrastructure-wide credentials to fill that gap.

## Getting started

From `homelab-iac/homelab-tier-2`:

```bash
bash ../homelab-shared/scripts/init-local-files.sh --setup lab --env test
```

Replace `homelab` with your prefix; omit `--env test` for production. Edit the
initialized inputs using the [script guide](../../reference/repository-scripts.md),
then have the authorized operator review:

```bash
bash ../homelab-shared/scripts/deploy.sh lab --env test --plan-only
```

Remove `--plan-only` only after review. Terraform and Ansible use this repo's
same inventory; no separate shared inventory is required.

## Find your way

- [Inventory and automation layout](../../reference/infrastructure-automation-layout.md)
- [VM placement and Proxmox HA](../../platforms/proxmox/cluster-ha.md#terraform-against-the-cluster)
- [Application platform capabilities](../application-platform/README.md)
- [Project conventions and recovery records](../../reference/project-documentation.md)
