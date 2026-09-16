"""Repository front doors and optional cluster bootstrap skeletons."""

import yaml

from generated_files import MARKER


def kustomization(writer, path, resources):
    content = {"apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
               "resources": resources}
    writer.write(f"{path}/kustomization.yaml", f"# {MARKER}\n" + yaml.safe_dump(content, sort_keys=False),
                 owned=True)


def cluster_scaffold(writer, tier):
    if tier == "tier-2":
        for directory in ("environments/dev", "environments/prod", "workloads"):
            writer.write(f"{directory}/.gitkeep", "", owned=True)
        return
    root = f"clusters/{tier.replace('-', '')}"
    sections = {
        "infrastructure": ["cni", "ingress", "cert-manager", "external-secrets", "storage"],
        "databases": ["cloudnative-pg"],
        "applications": ["freeipa", "keycloak", "vault", "headlamp", "netbox"],
    } if tier == "tier-0" else {
        "infrastructure": ["ingress", "external-secrets", "policy", "storage"],
        "platform": ["source-control", "artifact-registry", "ci-runners", "observability", "cluster-management"],
    }
    kustomization(writer, root, list(sections))
    for section, components in sections.items():
        kustomization(writer, f"{root}/{section}", components)
        for component in components:
            kustomization(writer, f"{root}/{section}/{component}", [])
    if tier != "tier-0":
        return
    writer.write(f"{root}/flux-system/.gitkeep", "", owned=True)
    writer.write("bootstrap/talos/patches/.gitkeep", "", owned=True)
    placeholders = {
        "proxmox/main.tf": 'terraform {\n  required_version = ">= 1.6.0"\n}\n',
        "proxmox/backend.tf": 'terraform {\n  backend "local" {}\n}\n',
        "proxmox/network.tf": "# Define isolated custody networks here; no routed DMZ connection.\n",
        "proxmox/tier0-vms.tf": "# Define Talos VMs here. Linux setup roots live under terraform/environments/.\n",
        "talos/cluster.tf": "# Define Talos cluster bootstrap resources here.\n",
        "talos/machines.tf": "# Define Talos machines using tier-owned inventory and recovery inputs.\n",
    }
    for path, content in placeholders.items():
        writer.write(f"bootstrap/{path}", f"# {MARKER}\n\n{content}", owned=True)


def tier_readme(writer, tier, prefix, setups):
    example = setups[0]
    descriptions = {
        "tier-0": "the recoverable control foundation and custody-local infrastructure",
        "tier-1": "shared platform services and connected infrastructure",
        "tier-2": "application, project, and lab workloads",
    }
    extra_paths = {
        "tier-0": "- `bootstrap/` and `clusters/tier0/`: cluster bootstrap and service skeletons\n",
        "tier-1": "- `clusters/tier1/`: platform cluster skeletons\n",
        "tier-2": "- `environments/` and `workloads/`: project and workload definitions\n",
    }
    docs = f"../{prefix}-architecture/docs/generated/upstream"
    writer.write("README.md", f"""<!-- {MARKER} -->

# {prefix} {tier.replace('-', ' ').title()}

This repository owns {descriptions[tier]}.
Inventory, configuration, and state live here. Reusable automation comes from
`{prefix}-shared`; detailed design and diagrams live in `{prefix}-architecture`.

## Getting started

From this repository's root, initialize the {example} example:

```bash
bash ../{prefix}-shared/scripts/init-local-files.sh --setup {example} --env test
```

Use `--setup` to choose a deployment and `--env` for a separate environment.
Omit `--env` for production. Setups: {', '.join(f'`{setup}`' for setup in setups)}.

Edit `.env.local`, the inventory and group vars under `ansible/`, and local
Terraform inputs under `terraform/`. Follow the
[setup guide]({docs}/reference/repository-scripts.md#available-setups), then plan:

```bash
bash ../{prefix}-shared/scripts/deploy.sh {example} --env test --plan-only
```

Remove `--plan-only` to deploy after reviewing the plan. Keep running commands
from this repository; the shared scripts use its inputs and state.

## Find your way

- [Architecture and diagrams]({docs}/architecture/overview.md)
- [Tier boundaries and recovery]({docs}/architecture/tier-model.md)
- [Inventory and refresh contract]({docs}/reference/generated-repository-model.md)
- [Deployment commands]({docs}/reference/repository-scripts.md)

## Repository structure

- `ansible/`: this tier's inventory, group vars, and configuration
- `terraform/`: infrastructure setups and environment inputs
{extra_paths[tier]}- `scripts/`: local entry points to the shared scripts
- `.deployment-setups`: setups owned by this tier

Keep local values in the initialized files. Upstream refresh preserves local
edits and development; it does not initialize or deploy an environment.
""")


def architecture_scaffold(writer, prefix):
    for area in ("design", "decisions", "runbooks", "services", "tiers", "network"):
        writer.write(f"docs/owned/{area}/.gitkeep", "", owned=True)
    writer.write("site/.gitkeep", "", owned=True)
    writer.write("README.md", f"""<!-- {MARKER} -->

# {prefix} Architecture

This repository holds environment design, diagrams, decisions, service records,
and runbooks.

- [Upstream documentation](docs/generated/upstream/README.md)
- [System design and diagrams](docs/generated/upstream/architecture/overview.md)
- [Network design](docs/generated/upstream/architecture/network.md)
- [Repository and inventory ownership](docs/generated/upstream/reference/generated-repository-model.md)
- `docs/owned/`: local design, decisions, runbooks, services, tiers, and networks
- `site/`: optional documentation-site integration; no site is generated

Use capability names in architecture: identity authority, identity broker,
source control, inventory, observability, and cluster management. Product
choices belong in implementation guides and service records.
""")
