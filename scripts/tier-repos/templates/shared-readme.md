# ${prefix} Shared

Reusable Terraform modules, Ansible playbooks and roles, Packer templates,
and deployment scripts for the ${prefix} repositories. Each tier supplies
its own inventory, variables, credentials, and state.

## Getting started

Review the project's [naming and allocations](../${prefix}-architecture/docs/naming-conventions.md),
then start from the owning deployment repository:

- [Tier 0: recovery and control](../${prefix}-tier-0/README.md)
- [Tier 1: shared platform](../${prefix}-tier-1/README.md)
- [Tier 2: workloads](../${prefix}-tier-2/README.md)

Run the shared scripts from that tier's root. Keep reviewed copies of this
repository and its dependencies available locally for recovery.

## Repository structure

- `terraform/modules/`: reusable guest and platform modules
- `ansible/playbooks/` and `ansible/roles/`: shared host configuration
- `packer/`: reusable image builds
- `scripts/`: initialization and deployment entry points
- `templates/`: project-specific reusable templates

## Documentation

- [Project documentation](../${prefix}-architecture/docs/README.md)
- [Automation layout](${docs}/reference/infrastructure-automation-layout.md)
- [Script reference](${docs}/reference/repository-scripts.md)
- [Upstream refresh contract](${docs}/reference/generated-repository-model.md#refresh-and-local-ownership)
