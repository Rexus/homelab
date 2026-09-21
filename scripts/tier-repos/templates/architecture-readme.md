# ${prefix} Architecture

Design, naming conventions, resource allocations, and recovery documentation
for ${prefix}. Project decisions live here alongside a refreshable copy of
the upstream reference guides.

## Getting started

1. Complete [naming conventions](docs/naming-conventions.md).
2. Describe the deployed environment in the [project overview](docs/owned/design/overview.md).
3. Complete and test the [recovery runbook](docs/owned/runbooks/recovery.md).

Use the [project documentation index](docs/README.md) to find local records
and the [upstream guides](docs/auto-docs/README.md) for detailed reference.

## Repository structure

- `docs/naming-conventions.md`: VM names, Proxmox tags, VMID ranges, and VLAN conventions
- `docs/owned/`: environment design, decisions, service records, and runbooks
- `docs/auto-docs/`: upstream-maintained reference docs; do not edit
- `site/`: optional documentation-site integration

This README and the project documents are maintained by the repository's
developers. Keep credentials and recovery secrets out of documentation.
