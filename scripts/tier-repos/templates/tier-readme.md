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
and [VM module](terraform/modules/vm/) own the resources. Shared supplies only
[size profiles](../${prefix}-shared/config/guest-sizes.json) and image references.
Set workload tags here, not template recipes. Only Tier 0 publishes templates
and approves catalog changes.

Follow the [deployment checklist](${docs}/paths/${tier}/README.md) for what to
deploy, in what order, and the checks before continuing. It links each step to
its detailed guide.

${prerequisites}

## Linux VM quick start

After the checklist's prerequisites, initialize a Linux VM setup from this root:

```bash
bash ../${prefix}-shared/scripts/init-local-files.sh --setup ${example} --env test
```

Use `--setup` to select an entry in `.deployment-setups` and `--env` to select
an environment. Omit `--env` for production.

Edit `.env.local`, inventory and group vars under `ansible/`, and local
Terraform inputs under `terraform/`. Follow the
[setup guide](${docs}/reference/repository-scripts.md#available-setups), then plan:

```bash
bash ../${prefix}-shared/scripts/deploy.sh ${example} --env test --plan-only
```

Review the plan before removing `--plan-only`. Shared scripts use this
repository's inputs and state; run these commands from this root.

## Repository structure

- `ansible/`: tier playbooks, service roles, inventory, group vars, and configuration
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
See the [Terraform design map](${docs}/reference/infrastructure-automation-layout.md#terraform-structure)
for file responsibilities and the inventory-to-resource flow.

| Deployment | Terraform entry point | Host configuration or images |
| --- | --- | --- |
${deployments}

## Documentation

- [Project documentation](../${prefix}-architecture/docs/README.md)
- [Deployment order](${docs}/paths/${tier}/README.md)
- [Recovery runbook](../${prefix}-architecture/docs/owned/runbooks/recovery.md)
- [Architecture and tier boundaries](${docs}/architecture/tier-model.md)
- [Infrastructure control and delegated requests](${docs}/architecture/infrastructure-control.md)
- [Deployment commands](${docs}/reference/repository-scripts.md)
- [Tier 0 template lifecycle](${docs}/platforms/proxmox/template-lifecycle.md)
