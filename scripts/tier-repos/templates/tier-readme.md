# ${prefix} ${tier_title}

This repository owns ${purpose}.
Workload definitions, service playbooks and roles, inventory, and separate state roots belong here.
Common building blocks come from `${prefix}-shared`; design and operating documentation
live in `${prefix}-architecture`.

## Getting started

Review the project's [naming conventions](../${prefix}-architecture/docs/naming-conventions.md)
before creating resources. Keep the sibling shared and architecture repositories
available locally.

${prerequisites}

From this repository's root, initialize a Linux VM setup:

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
- `terraform/`: infrastructure setups and environment inputs
${extra_paths}
- `scripts/`: tier commands and entry points to shared deployment helpers
- `.deployment-setups`: deployments maintained by this tier

## Documentation

- [Project documentation](../${prefix}-architecture/docs/README.md)
- [Recovery runbook](../${prefix}-architecture/docs/owned/runbooks/recovery.md)
- [Architecture and tier boundaries](${docs}/architecture/tier-model.md)
- [Infrastructure control and delegated requests](${docs}/architecture/infrastructure-control.md)
- [Deployment commands](${docs}/reference/repository-scripts.md)
- [Tier 0 template lifecycle](${docs}/platforms/proxmox/template-lifecycle.md)
