# Tier 0

Tier 0 owns the hardware-facing control plane, all VM templates, trust systems,
and their recovery. Proxmox hosts, storage and network administration belong
here, including infrastructure serving other tiers. Its
repository holds service code, inventory, infrastructure definitions, and recovery inputs.
Common baseline helpers live in the sibling shared repo; the architecture repo
holds the detailed design, diagrams, and guides. Connected control systems are
valid Tier 0 systems; offline custody is protected separately.

## Getting started

First [generate the collection](../../reference/generated-repository-model.md).
**Day 0-1: templates before VMs.** From `homelab-iac/homelab-tier-0`, initialize
the template catalog:

```bash
bash scripts/proxmox-templates.sh init
```

Follow the
[local template workflow](../../platforms/proxmox/template-lifecycle.md#local-workflow)
to set image paths, checksums, placement, and protected API access; then plan,
publish, and test the required AlmaLinux, Rocky Linux, or Talos templates.
This works before any managed VM, control cluster, or hosted CI exists.
Existing approved templates are valid when their IDs and recovery copies are verified.

Once a Linux template is ready, initialize the identity example from the same directory:

```bash
bash ../homelab-shared/scripts/init-local-files.sh --setup foundation --env test
```

Replace `homelab` if you chose another prefix. Use `--setup vault` or `--setup hsm`
for those capabilities; omit `--env test` for production.

Edit the initialized local files using the
[identity guide](../shared-services/identity.md), including protected network placement
and administrative access, then review a plan:

```bash
bash ../homelab-shared/scripts/deploy.sh foundation --env test --plan-only
```

Remove `--plan-only` to deploy after reviewing the plan. Run all shared commands
from the tier repository root so they use its inventory and state.

## Find your way

| Need | Guide |
| --- | --- |
| Bootstrap, recovery, and Day 2 services | [Tier 0 bootstrap and recovery](bootstrap.md) |
| AlmaLinux, Rocky Linux, and Talos templates | [Template lifecycle and CD](../../platforms/proxmox/template-lifecycle.md) |
| Tier boundaries | [Tier model](../../architecture/tier-model.md) |
| Hardware ownership and future workload requests | [Infrastructure control](../../architecture/infrastructure-control.md) |
| Network design | [Network architecture](../../architecture/network.md) |
| Inventory and upstream updates | [Generated repository model](../../reference/generated-repository-model.md) |
| Command reference | [Repository scripts](../../reference/repository-scripts.md) |

## Repository structure

- `ansible/`: tier service playbooks and roles, inventory, group vars, and configuration
- `terraform/`: Linux infrastructure setups and environment inputs
- `templates/`, `terraform/templates/`, and `ci/`: image catalog, template publication, and CD jobs
- `terraform/modules/` and `packer/`: template implementations and custom-build scaffolds
- `bootstrap/`: Talos and infrastructure bootstrap skeletons
- `clusters/tier0/`: cluster-service skeletons
- `scripts/`: local template publisher and entry points to shared deployment helpers

The Linux setup command above does not bootstrap Talos or deploy the cluster
services. Follow the [bootstrap guide](bootstrap.md) for that separate path.
