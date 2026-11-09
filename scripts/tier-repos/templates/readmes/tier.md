# ${prefix} ${tier_title}

This repository owns ${purpose}.
Workload definitions, service playbooks and roles, inventory, and separate state roots belong here.
Common building blocks come from `${repo_prefix}-shared`; design and operating documentation
live in `${repo_prefix}-architecture`.

## Getting started

Review the project's [platform standards](../${repo_prefix}-architecture/platform-standards.md)
before creating resources. Keep the sibling shared and architecture repositories
available locally.
Use the [Proxmox VMID quick reference](${docs}/conventions/vmid-convention.md)
when assigning or maintaining guest IDs; existing installations retain their local allocations.

Approved image IDs and titles come from the sibling shared repository's
[template catalog](../${repo_prefix}-shared/templates/proxmox-catalog.tfvars).
The [shared deploy helper](../${repo_prefix}-shared/scripts/deploy.sh) loads it;
the tier-local [inventory resolver](terraform/modules/environment_guests)
and [VM module](terraform/modules/vm) own the resources. Shared supplies
[size profiles](../${repo_prefix}-shared/config/guest-sizes.json), image references,
and a project-owned [platform profile](../${repo_prefix}-shared/config/platform.tfvars).
Set workload tags here, not template recipes. Only Tier 0 publishes templates
and approves catalog changes.

Follow the [deployment checklist](${docs}/paths/${tier}/README.md) for what to
deploy, in what order, and the checks before continuing. It links each step to
its detailed guide.

${prerequisites}

## Linux VM quick start

After the checklist's prerequisites, initialize a Linux VM setup:

Run from **`${repo_prefix}-${tier}/`**.

```bash
bash scripts/init-local-files.sh --setup ${example}
```

Use `--setup` to select an entry in `.deployment-setups`. These commands use the
base production context, matching the main deployment path. For a disposable context,
add the same `--env test` to initialization and deployment, and complete
[environment isolation](${docs}/reference/repository-scripts.md#environment-isolation)
first; the flag does not allocate separate VMIDs or addresses.

Edit in **`${repo_prefix}-${tier}/`**.

- `.env.local`: edit API access and local public-key paths
- `ansible/inventory/hosts.yml`: edit host groups
- `ansible/group_vars/all.yml`: edit domain and common guest settings
- `ansible/group_vars/${example}.yml`: edit the selected service inputs and host IPs
- `terraform/common.tfvars`: edit tier-specific network references
- `terraform/deployments/${example}/terraform.tfvars`: edit guest IDs, sizing and storage selections

Edit in **`${repo_prefix}-shared/`**.

- `config/platform.tfvars`: edit shared placement, storage and network references
- `templates/proxmox-catalog.tfvars`: select approved consumer images

Keep SSH keys outside the
repositories and set only public-key file paths in `.env.local`, as described
in [platform inputs](${docs}/reference/platform-inputs.md). Follow the
[setup guide](${docs}/reference/repository-scripts.md#available-setups), completing its
storage and TLS preparation before host configuration. Then deploy:

Run from **`${repo_prefix}-${tier}/`**.

```bash
bash scripts/deploy.sh ${example}
```

Review the displayed plan and enter `yes` to apply, or `no` to stop.
Add `--plan-only` for a preview, or `--auto-approve` in an approved pipeline.
For staged provisioning, use the setup guide's `--terraform-only` / `--ansible-only` steps.
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
Use [Add a service](${docs}/development/adding-service.md) for an extension, or
[Find and fix a bug](${docs}/development/debugging.md) to trace a failure.

All entry points below belong to `${repo_prefix}-${tier}`. Reusable execution code
in `${repo_prefix}-shared` does not own these deployments or their inventory and state.
Upstream guides name their owners using the [repository map](${docs}/deployment/README.md#repository-locations).

| Deployment | Terraform entry point | Host configuration or images |
| --- | --- | --- |
${deployments}

## Documentation

- [Selected architecture](docs/architecture/README.md)
- [Local deployment, development and administration guides](docs/README.md)
- [Project documentation](../${repo_prefix}-architecture/docs/README.md)
- [Conventions: names, tags, VMIDs and networks](${docs}/conventions/README.md)
- [Deployment order](${docs}/paths/${tier}/README.md)
- [Recovery guides](${docs}/administration/recovery.md)
- [Architecture and tier boundaries](${docs}/architecture/tier-ownership.md)
- [Infrastructure control and delegated requests](${docs}/architecture/hosting/provisioning.md)
- [Deployment commands](${docs}/reference/repository-scripts.md)
- [Tier 0 template lifecycle](${docs}/administration/virtual-machines/template-lifecycle.md)

## Licensing

Project licensing is determined by the repository owners. [Upstream attribution](UPSTREAM-NOTICE)
applies only to material inherited from the deployment kit.
