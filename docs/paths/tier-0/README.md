# Tier 0

Tier 0 owns the recoverable control foundation in air-gapped custody. Its
repository holds inventory, infrastructure definitions, and recovery inputs.
Shared automation lives in the sibling shared repo; the architecture repo
holds the detailed design, diagrams, and guides.

## Getting started

First [generate the collection](../../reference/generated-repository-model.md).
From `homelab-iac/homelab-tier-0`, initialize the Linux identity example:

```bash
bash ../homelab-shared/scripts/init-local-files.sh --setup foundation --env test
```

Replace `homelab` if you chose another prefix. Use `--setup vault` or `--setup hsm`
for those capabilities; omit `--env test` for production.

Edit the initialized local files using the
[identity guide](../shared-services/identity.md), including custody-local network
placement, then review a plan:

```bash
bash ../homelab-shared/scripts/deploy.sh foundation --env test --plan-only
```

Remove `--plan-only` to deploy after reviewing the plan. Run all shared commands
from the tier repository root so they use its inventory and state.

## Find your way

| Need | Guide |
| --- | --- |
| Bootstrap, recovery, and Day 2 services | [Tier 0 bootstrap and recovery](bootstrap.md) |
| Tier boundaries | [Tier model](../../architecture/tier-model.md) |
| Network design | [Network architecture](../../architecture/network.md) |
| Inventory and upstream updates | [Generated repository model](../../reference/generated-repository-model.md) |
| Command reference | [Repository scripts](../../reference/repository-scripts.md) |

## Repository structure

- `ansible/`: tier-owned inventory, group vars, and configuration
- `terraform/`: Linux infrastructure setups and environment inputs
- `bootstrap/`: Talos and infrastructure bootstrap skeletons
- `clusters/tier0/`: cluster-service skeletons
- `scripts/`: local entry points to shared automation

The Linux setup command above does not bootstrap Talos or deploy the cluster
services. Follow the [bootstrap guide](bootstrap.md) for that separate path.
