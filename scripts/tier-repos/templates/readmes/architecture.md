# ${prefix} Architecture

Design, naming conventions, resource allocations, and recovery documentation
for ${prefix}. Project decisions live here alongside a refreshable copy of
the upstream reference guides.

## Getting started

1. Complete [naming conventions](docs/naming-conventions.md).
2. Record the [platform architecture](docs/architecture/README.md) and its [technical domains](docs/architecture/README.md#technical-domains).
3. Follow the [owning repo's deployment checklist](docs/auto-docs/paths/README.md#choose-a-repository).
4. Record the results and test the [recovery runbook](docs/administration/recovery.md).

Use the [project documentation index](docs/README.md) to find local records
and the [upstream guides](docs/auto-docs/README.md) for detailed reference.
This repository deploys no infrastructure; see the
[documentation operating order](docs/auto-docs/development/project-documentation.md#operating-order).

## Repository structure

- `docs/naming-conventions.md`: VM names, Proxmox tags, VMID ranges, and VLAN conventions
- `docs/architecture/README.md`: platform relationships, ownership and shared constraints
- `docs/architecture/<domain>/`: networking, compute, identity, cryptography, delivery and operations designs
- `docs/deployment/`: selected stages, prerequisites and acceptance records
- `docs/development/`: review, validation and upstream adoption procedures
- `docs/administration/`: maintenance, recovery and verification records
- `docs/auto-docs/`: upstream-maintained reference docs; do not edit
- `site/`: optional documentation-site integration

This README and the project documents are maintained by the repository's
developers. Keep credentials and recovery secrets out of documentation.

## Licensing

Project licensing is determined by the repository owners. Copied reference guides
retain their [upstream license](docs/auto-docs/LICENSE); [upstream attribution](UPSTREAM-NOTICE)
also covers inherited document templates, not independently authored project content.
