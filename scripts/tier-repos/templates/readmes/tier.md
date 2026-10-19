# ${prefix} ${tier_title}

This repository owns ${purpose}.
Workload definitions, service playbooks and roles, inventory, and separate state roots belong here.
Common building blocks come from `${prefix}-shared`; design and operating documentation
live in `${prefix}-architecture`.

## Getting started

Review the project's [naming conventions](../${prefix}-architecture/docs/naming-conventions.md)
before creating resources. Keep the sibling shared and architecture repositories
available locally.

Approved image IDs and titles come from the sibling shared repository's
[template catalog](../${prefix}-shared/templates/proxmox-catalog.tfvars).
The [shared deploy helper](../${prefix}-shared/scripts/deploy.sh) loads it;
the tier-local [inventory resolver](terraform/modules/environment_guests/)
and [VM module](terraform/modules/vm/) own the resources. Shared supplies
[size profiles](../${prefix}-shared/config/guest-sizes.json), image references,
and a project-owned [platform profile](../${prefix}-shared/config/platform.tfvars).
Set workload tags here, not template recipes. Only Tier 0 publishes templates
and approves catalog changes.

Follow the [deployment checklist](${docs}/paths/${tier}/README.md) for what to
deploy, in what order, and the checks before continuing. It links each step to
its detailed guide.

${prerequisites}

## Linux VM quick start

After the checklist's prerequisites, initialize a Linux VM setup from this root:

```bash
bash ../${prefix}-shared/scripts/init-local-files.sh --setup ${example}
```

Use `--setup` to select an entry in `.deployment-setups`. These commands use the
base production context, matching the main deployment path. For a disposable context,
add the same `--env test` to initialization and deployment, and complete
[environment isolation](${docs}/reference/repository-scripts.md#environment-isolation)
first; the flag does not allocate separate VMIDs or addresses.

Edit `.env.local`, inventory and group vars under `ansible/`, and local
Terraform inputs under `terraform/`. Set common storage, initial placement and
network references once in the shared profile; keep tier-specific networks and overrides here.
Keep SSH keys outside the
repositories and set only public-key file paths in `.env.local`, as described
in [platform inputs](${docs}/reference/platform-inputs.md). Follow the
[setup guide](${docs}/reference/repository-scripts.md#available-setups), then plan:

```bash
bash ../${prefix}-shared/scripts/deploy.sh ${example} --plan-only
```

Review the plan, then follow the setup guide's provisioning and configuration steps.
Some setups require storage or TLS preparation before host configuration.
Shared scripts use this repository's inputs and state; run these commands from this root.

## Repository structure

- `ansible/`: tier playbooks, service roles, inventory, group vars, and configuration
- `ansible/playbooks/deployment/` and `maintenance/`: recipes reusing the same roles
- `terraform/deployments/`: runnable root modules, one per independently managed deployment
- `terraform/modules/`: tier-owned infrastructure building blocks used by deployments
- `terraform/common.tfvars.example`: tier-wide Linux deployment defaults
${extra_paths}
- `scripts/`: tier commands and entry points to shared deployment helpers
- `.deployment-setups`: Linux deployments supported by the shared helper

## Read the code

Start with a deployment's `main.tf`, then follow its module calls into
`terraform/modules/`. For guest deployments, edit local values beside
`terraform.tfvars.example`; host names, groups, and IPs come from this tier's
`ansible/` inputs.
See the [Terraform design map](${docs}/development/code-layout.md#terraform-structure)
for file responsibilities and the inventory-to-resource flow.

All entry points below belong to `${prefix}-${tier}`. Reusable execution code
in `${prefix}-shared` does not own these deployments or their inventory and state.
Upstream guides name their owners using the [repository map](${docs}/deployment/README.md#repository-locations).

| Deployment | Terraform entry point | Host configuration or images |
| --- | --- | --- |
${deployments}

## Documentation

- [Selected architecture](docs/architecture/README.md)
- [Local deployment, development and administration guides](docs/README.md)
- [Project documentation](../${prefix}-architecture/docs/README.md)
- [Deployment order](${docs}/paths/${tier}/README.md)
- [Recovery runbook](../${prefix}-architecture/docs/administration/recovery.md)
- [Architecture and tier boundaries](${docs}/architecture/tier-ownership.md)
- [Infrastructure control and delegated requests](${docs}/architecture/compute/provisioning.md)
- [Deployment commands](${docs}/reference/repository-scripts.md)
- [Tier 0 template lifecycle](${docs}/administration/compute/template-lifecycle.md)

## Licensing

Project licensing is determined by the repository owners. [Upstream attribution](UPSTREAM-NOTICE)
applies only to material inherited from the deployment kit.
