# ${prefix} Architecture

Project standards, selected deployment paths and verification records for ${prefix}.
The complete design and operating guides are maintained under `docs/auto-docs/`;
local records contain only project choices and exceptions.

## Getting started

1. Complete [platform standards](platform-standards.md).
2. Select the paths and follow the [deployment checklist](deployments.md).
3. Run each step from its owning tier repository; check its entry after completing that deployment path.

## Navigation

- [Deployment checklist](deployments.md)
- [Project choices and operating records](docs/README.md)
- [Conventions: names, tags, VMIDs and networks](docs/auto-docs/conventions/README.md)
- [Reference design](docs/auto-docs/architecture/README.md)
- [Installation guides](docs/auto-docs/deployment/README.md)
- [Administration and recovery](docs/auto-docs/administration/README.md)
- [Development and updates](docs/auto-docs/development/README.md)

This repository deploys nothing. `README.md`, `deployments.md`, `docs/README.md` and platform standards
are project-owned; refresh updates auto-docs without rewriting these records.
Add local detail only when the project differs from the reference. Keep secrets out of documentation.

## Licensing

Project licensing is determined by the repository owners. Copied material retains its
[upstream license](docs/auto-docs/LICENSE) and [attribution](UPSTREAM-NOTICE).
