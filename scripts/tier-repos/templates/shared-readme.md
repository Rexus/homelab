# ${prefix} Shared

Cross-tier Terraform guest modules, Ansible baseline tasks, and deployment
helpers for the ${prefix} repositories. Each tier owns its service playbooks,
roles, inventory, variables, credentials, and state. Tier 0 contains all VM
template implementations, Packer builds, publication scripts, and CD jobs.

## Getting started

Review the project's [naming conventions](../${prefix}-architecture/docs/naming-conventions.md),
then start from the owning deployment repository:

- [Tier 0: recovery and control](../${prefix}-tier-0/README.md)
- [Tier 1: shared platform](../${prefix}-tier-1/README.md)
- [Tier 2: workloads](../${prefix}-tier-2/README.md)

Run the shared scripts from that tier's root. Keep reviewed copies of this
repository and its dependencies available locally for recovery.

## Repository structure

- `terraform/modules/`: guest inventory resolution and VM/LXC resources used across tiers
- `ansible/playbooks/` and `ansible/roles/`: common precheck, baseline, and task fragments
- `scripts/`: initialization and deployment entry points
- `templates/`: project-specific reusable templates

## Documentation

- [Project documentation](../${prefix}-architecture/docs/README.md)
- [Automation layout](${docs}/reference/infrastructure-automation-layout.md)
- [Script reference](${docs}/reference/repository-scripts.md)
- [Upstream refresh contract](${docs}/reference/generated-repository-model.md#refresh-and-local-ownership)
