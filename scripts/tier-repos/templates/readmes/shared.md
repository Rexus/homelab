# ${prefix} Shared

Reusable scripts, Ansible baseline tasks, stateless size profiles, and deployment
helpers for the ${prefix} repositories. Each tier owns its service playbooks,
roles, inventory, variables, credentials, and state. Tier 0 contains all VM
template implementations, Packer builds, publication scripts, and CD jobs.
This repo exposes their approved IDs and titles in one
[consumer catalog](templates/proxmox-catalog.tfvars), maintained through Tier 0 review.
The [platform profile](config/platform.tfvars) holds common storage, placement and
network references with tier-local overrides. Shared never owns inventory, Terraform
resources, guest assignments, credentials, or state.

## Getting started

This repository deploys no services by itself. Follow the
[shared automation checklist](${docs}/paths/shared/README.md) to prepare it.

Review the project's [naming conventions](../${prefix}-architecture/docs/naming-conventions.md),
then start from the owning deployment repository:

- [Tier 0: recovery and control](../${prefix}-tier-0/README.md)
- [Tier 1: shared platform](../${prefix}-tier-1/README.md)
- [Tier 2: public edge and workloads](../${prefix}-tier-2/README.md)

Run the shared scripts from that tier's root. Keep reviewed copies of this
repository and its dependencies available locally for recovery.

## Repository structure

- `config/guest-sizes.json`: common VM/LXC size profiles, without deployment ownership
- `config/platform.tfvars`: project-owned platform references; loaded before tier overrides
- `ansible/playbooks/` and `ansible/roles/`: common precheck, baseline, and task fragments
- `scripts/`: initialization and deployment entry points
- `templates/proxmox-catalog.tfvars`: project-owned template references, read by all tiers

## Documentation

- [Selected architecture](docs/architecture/README.md)
- [Local development and administration guides](docs/README.md)
- [Project documentation](../${prefix}-architecture/docs/README.md)
- [Automation layout](${docs}/development/code-layout.md)
- [Template references and promotion](${docs}/reference/template-catalog.md)
- [Script reference](${docs}/reference/repository-scripts.md)
- [Upstream refresh contract](${docs}/development/generated-repositories.md#refresh-and-local-ownership)

## Licensing

Project licensing is determined by the repository owners. [Upstream attribution](UPSTREAM-NOTICE)
applies only to material inherited from the deployment kit.
