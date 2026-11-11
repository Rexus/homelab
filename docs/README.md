# Documentation

Architecture describes the completed intended platform from overview to detail:
its foundational capabilities, integrated component placement, runtime relationships
and local alternatives. Deployment builds that design in stages;
development changes the implementation and operations maintains the system.
The same capability names connect these views: for example, Software Intake is
designed in architecture, built in Stage 1 and maintained in operations.
The Delivery chapter connects intake, source, builds and release delivery without duplicating their designs.

| Intent | Start here | Contains |
| --- | --- | --- |
| Understand the design | [Architecture](01-architecture/README.md) | Foundational capabilities, reference placement, interfaces and design variants |
| Choose names, IDs and network allocations | [Conventions](02-conventions/README.md) | Names, tags, VMID ranges and zone/VNet examples |
| Build the platform | [Deployment](03-deployment/README.md) | Foundation prerequisites and numbered capability stages, including software intake and Kubernetes |
| Change the code | [Development](04-development/README.md) | Visual repository/code maps, extension examples, debugging and focused checks |
| Operate the platform | [Operations](05-operations/README.md) | Maintenance, backups, recovery and secret handling |
| Work from one repository | [Repository paths](06-paths/README.md) | Short Tier 0, Tier 1, Tier 2 and shared checklists |
| Understand a decision | [Decision log](07-decisions/README.md) | Rationale, consequences and review triggers |
| Look up an input or command | [Reference](08-reference/README.md) | Naming, catalogs, input contracts and CLI options |

## Read command examples

`<prefix>` means the generated repository folder prefix selected with `--prefix`;
the default is `homelab`, giving the default Tier 0 folder `homelab-tier-0/`.
It is separate from host/DNS naming choices. Other `<...>` values mark deployment-specific inputs.
Generated auto-docs resolve repository markers to the selected collection prefix;
replace remaining `<...>` inputs before executing an example.

The text above a command or configuration block names its working repository or machine in **bold**.
File paths and variables use inline code, such as `config/platform.tfvars` and
`default_platform_node_name`. Edit instructions stay above the block or in a short file list;
command blocks contain the commands to copy. Fences name the actual language: `bash`, `yaml`,
`hcl` or `dotenv`; `text` is for plain output and file trees.
Keep comments only when they explain the code itself. Separate logical comment/command groups
with blank lines, and indent wrapped comment text consistently.
See the [repository map](03-deployment/README.md#repository-locations) for ownership.

## Start here

Find the same capability across design, installation and operations in the
[capability index](06-paths/capabilities.md).

For installation, start with [foundation prerequisites](03-deployment/foundation/README.md), then follow
the [numbered capability stages](03-deployment/README.md#deployment-stages). Each guide links its design
and reference details at the point they are needed.

For a design review, follow this reading order:

1. Read the [platform overview](01-architecture/README.md) to see the complete system.
2. Read [responsibilities and service boundaries](01-architecture/02-organization/README.md)
   before assigning administrative authority or choosing shared/isolated services.
3. Open the [capability](01-architecture/README.md#capabilities) needed for the next design choice.
   Its design explains communication, alternatives and failure/recovery consequences;
   the [integrated reference](01-architecture/03-reference-platform.md) places the selected components.
   Use [background and principles](01-architecture/01-background/README.md) when comparing platform models.
4. Record selected design in the generated architecture repository's `docs/README.md`;
   complete `platform-standards.md` for local standards and use `deployments.md` for completion checks.
5. Follow the [deployment stages](03-deployment/README.md), using verified
   existing services wherever they satisfy the prerequisites.

Deployment guides name the working repository; the
[repository map](03-deployment/README.md#repository-locations) connects Tier 0/1/2
and Shared to generated checkouts and source directories.

The architecture repository's `docs/auto-docs/` is the complete maintained manual.
Its initial local documents are the platform design/navigation record, `deployments.md`
completion checklist and platform standards worksheet. After a successful installation,
check the matching deployment and options in `<prefix>-architecture/deployments.md`;
keep acceptance evidence separate. Tier/Shared repositories retain their code-specific records;
extra site design/runbooks are added only when needed.

Architecture defines the result and its boundaries. Deployment realizes it;
development changes its implementation; operations maintains its guarantees.
All views follow the [diagram conventions](04-development/diagrams.md#abstraction-and-implementation):
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
