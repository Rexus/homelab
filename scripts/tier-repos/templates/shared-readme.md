# ${prefix} Shared

Reusable scripts, Ansible baseline tasks, stateless size profiles, and deployment
helpers for the ${prefix} repositories. Each tier owns its service playbooks,
roles, inventory, variables, credentials, and state. Tier 0 contains all VM
template implementations, Packer builds, publication scripts, and CD jobs.
This repo exposes their approved IDs and titles in one
[consumer catalog](templates/proxmox-catalog.tfvars), maintained through Tier 0 review.
It never owns inventory, Terraform resources, deployment inputs, or state.

## Getting started

This repository deploys no services by itself. Follow the
[shared automation checklist](${docs}/paths/shared/README.md) to prepare it.

Review the project's [naming conventions](../${prefix}-architecture/docs/naming-conventions.md),
then start from the owning deployment repository:

- [Tier 0: recovery and control](../${prefix}-tier-0/README.md)
- [Tier 1: shared platform](../${prefix}-tier-1/README.md)
- [Tier 2: workloads](../${prefix}-tier-2/README.md)

Run the shared scripts from that tier's root. Keep reviewed copies of this
repository and its dependencies available locally for recovery.

## Repository structure

- `config/guest-sizes.json`: common VM/LXC size profiles, without deployment ownership
- `ansible/playbooks/` and `ansible/roles/`: common precheck, baseline, and task fragments
- `scripts/`: initialization and deployment entry points
- `templates/proxmox-catalog.tfvars`: project-owned template references, read by all tiers

## Documentation

- [Project documentation](../${prefix}-architecture/docs/README.md)
- [Automation layout](${docs}/reference/infrastructure-automation-layout.md)
- [Template references and promotion](${docs}/platforms/proxmox/template-catalog.md)
- [Script reference](${docs}/reference/repository-scripts.md)
- [Upstream refresh contract](${docs}/reference/generated-repository-model.md#refresh-and-local-ownership)
