# Tier 2

Tier 2 owns public edge ingress, ordinary outbound caches, clients and application,
project and lab workloads. Keep workload definitions,
inventory, service code, and state here. Consume approved infrastructure and
platform services without moving their administrative authority into this repo.
Use the [shared template catalog](../../reference/template-catalog.md) for
approved image IDs and titles; keep only workload selections and service tags here.

## Deployment order

For a new installation, early [software intake](../../deployment/stage-1-software-intake/README.md)
uses the `cache` setup from this repository, after Tier 0's foundation/template gates.
Later, public application access uses the [edge load-balancer set](../../deployment/stage-7-delivery/procedures/edge-proxy.md)
and its publication checks. Edge publication is not a prerequisite to software intake or private labs.
These setups retain independent inventory selections and state.
Client VLANs are network-policy references, not provisioned server guests.
Keep clients, public edge and Tier 1 build/supply hosts in separate subnets.

For an independent Kubernetes workload runtime, enter through
[Stage 10's runtime choice](../../deployment/stage-10-lab-environments/README.md).
Its Kubernetes path selects this tier's `terraform/deployments/kubernetes/`, cluster credentials,
platform installation and acceptance before scoped application delivery.
The Linux `lab` workflow below is a separate VM option, not the cluster installer.

| Step | What to do | Ready to continue when |
| --- | --- | --- |
| 1. Select the target | Record project naming choices and consume an approved VM network/template or an existing platform runtime | Resource allocation and access are approved |
| 2. Define the workload | For the shipped Linux example, initialize `lab`, then edit tier-local inventory, group vars, and Terraform inputs | Plan inputs describe only this tier's resources |
| 3. Provision and configure | An authorized operator reviews the plan and deploys the Linux baseline | Hosts are reachable only through approved paths and baseline checks pass |
| 4. Deliver the application | Add project-specific definitions under `workloads/` or the chosen runtime's delivery path | Service checks, backups, and rollback are tested |

The Linux `lab` setup supplies an OS baseline; its application installer is project-owned.
The [Stage 10 application recipe](../../deployment/stage-10-lab-environments/step-3a-application.md)
supplies a bounded Kubernetes HTTP example after an accepted cluster, not a Linux application installer.
Future self-service requests are controlled by Tier 0; that controller is
[not implemented yet](../../architecture/hosting/provisioning.md#delegated-provisioning).
Do not give workload users infrastructure-wide credentials to fill that gap.

## Getting started

Initialize the selected isolated context:

Run from **`<prefix>-tier-2/`**.

```bash
bash scripts/init-local-files.sh --setup lab --env test
```

Keep `--env test` on both commands for this example. Before deployment, complete the
[environment-isolation contract](../../reference/repository-scripts.md#environment-isolation)
in **`<prefix>-tier-2/`**:

- Create `terraform/deployments/lab/terraform.test.tfvars` with the complete intended test
  `vm_instances`/`lxc_instances` maps and unused VMIDs. The initializer does not create this overlay.
- Edit `ansible/group_vars/lab.test.yml` for distinct test addresses and the matching inventory keys.
- Select the isolated lab attachment in `terraform/common.tfvars`, or use
  `terraform/common.test.tfvars` for the test-specific override. A `network_zones` override replaces
  that complete map; preserve other tier-local entries needed by the selected setup.
  The inherited shared `application` subnet is not isolation merely because a guest is named `lab-1`.
- Configure this tier's `.env.local` and its local SSH public-key paths.

The environment flag separates state and selects inputs; it does not allocate safe VMIDs,
addresses or networks. Do not point a new test state at guests already owned by another state.
For production, omit `--env test` consistently and configure the base inputs instead.
Then have the authorized operator deploy:

Run from **`<prefix>-tier-2/`**.

```bash
bash scripts/deploy.sh lab --env test
```

Review the displayed plan and enter `yes` to apply, or `no` to stop. Add `--plan-only`
for an optional preview; approved pipelines can use `--auto-approve`.
Terraform and Ansible use this repo's
same inventory; no separate shared inventory is required.

<a id="find-your-way"></a>

## Navigation

- [Inventory and automation layout](../../development/code-layout.md)
- [Lab environments stage](../../deployment/stage-10-lab-environments/README.md)
- [VM placement and Proxmox HA](../../deployment/foundation/proxmox/step-1b-cluster-ha.md#terraform-against-the-cluster)
- [Development-platform handover](../../deployment/stage-9-development/procedures/handover.md)
- [Project conventions and recovery records](../../development/project-documentation.md)
