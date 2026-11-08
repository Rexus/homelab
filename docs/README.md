# Documentation

Architecture describes the completed intended platform from overview to detail:
its foundational capabilities, integrated component placement, runtime relationships
and local alternatives. Deployment builds that design in stages;
development and administration maintain it.

| Intent | Start here | Contains |
| --- | --- | --- |
| Understand the design | [Architecture](architecture/README.md) | Foundational capabilities, reference placement, interfaces and design variants |
| Choose names, IDs and network allocations | [Conventions](conventions/README.md) | Names, tags, VMID ranges and zone/VNet examples |
| Build the platform | [Deployment](deployment/README.md) | Foundation prerequisites and numbered capability stages, including software intake and Kubernetes |
| Change the code | [Development](development/README.md) | Visual repository/code maps, extension examples, debugging and focused checks |
| Operate the platform | [Administration](administration/README.md) | Maintenance, backups, recovery and secret handling |
| Work from one repository | [Repository paths](paths/README.md) | Short Tier 0, Tier 1, Tier 2 and shared checklists |
| Look up an input or command | [Reference](reference/README.md) | Naming, catalogs, input contracts and CLI options |
| Understand a decision | [Decision log](decisions/README.md) | Rationale, consequences and review triggers |

## Start here

1. Read the [platform overview](architecture/README.md) and its connected functions.
2. Expand the [integrated reference](architecture/reference-platform.md) and
   [runtime relationships](architecture/runtime-flows.md).
3. Drill into [foundational capabilities](architecture/README.md#foundational-capabilities) and
   [select compatible variants](architecture/variants.md).
4. Record selected paths in the generated architecture repository's `docs/README.md`;
   complete `platform-standards.md` for local standards.
5. Follow the [deployment stages](deployment/README.md), using verified
   existing services wherever they satisfy the prerequisites.

Deployment guides name the working repository; the
[repository map](deployment/README.md#repository-locations) connects Tier 0/1/2
and Shared to generated checkouts and source directories.

The architecture repository's `docs/auto-docs/` is the complete maintained manual.
Its only initial local documents are one platform checklist/navigation record and
naming conventions. Tier/Shared repositories retain their code-specific records;
extra site design/runbooks are added only when needed.

Architecture defines the result and its boundaries. Deployment realizes it;
development changes its implementation; administration maintains its guarantees.
All views follow the [diagram conventions](development/diagrams.md#abstraction-and-implementation):
architecture names capabilities; deployment names the selected instances and links their IaC.

<a id="recommended-path"></a>
<a id="architecture-and-design"></a>
<a id="deployment-guides"></a>
<a id="development-guides"></a>
<a id="administration-guides"></a>
<a id="reference-and-decisions"></a>
<a id="reader-paths"></a>
<a id="path-guides"></a>
<a id="platform-guides"></a>
<a id="security-and-hardening"></a>
