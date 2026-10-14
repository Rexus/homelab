# Documentation

Architecture describes the completed intended platform from overview to detail:
its functions, integrated component placement, runtime relationships, domain
designs and local alternatives. Deployment builds that design in stages;
development and administration maintain it.

| Intent | Start here | Contains |
| --- | --- | --- |
| Understand the design | [Architecture](architecture/README.md) | Whole platform, integrated reference, domain diagrams and detailed variants |
| Build the platform | [Deployment](deployment/README.md) | Six capability stages, numbered steps, adjacent options and detailed procedures |
| Change the code | [Development](development/README.md) | Local tooling, IaC structure, repository generation and review |
| Operate the platform | [Administration](administration/README.md) | Maintenance, backups, recovery and secret handling |
| Work from one repository | [Repository paths](paths/README.md) | Short Tier 0, Tier 1, Tier 2 and shared checklists |
| Look up an input or command | [Reference](reference/README.md) | Naming, catalogs, input contracts and CLI options |
| Understand a decision | [Decision log](decisions/README.md) | Rationale, consequences and review triggers |

## Start here

1. Read the [platform overview](architecture/README.md) and its connected functions.
2. Expand the [integrated reference](architecture/reference-platform.md) and
   [runtime relationships](architecture/runtime-flows.md).
3. Drill into [domain designs](architecture/README.md#technical-domains) and
   [select compatible variants](architecture/variants.md).
4. Record the selected composition in the generated repositories' project-owned
   architecture records.
5. Follow the [deployment stages](deployment/README.md), using verified
   existing services wherever they satisfy the prerequisites.

Deployment guides name the working repository; the
[repository map](deployment/README.md#repository-locations) connects Tier 0/1/2
and Shared to generated checkouts and source directories.

Generated repositories use the same architecture, deployment, development and
administration folders for project-owned records. The architecture repository's
`docs/auto-docs/` mirrors this upstream tree as reference material.

Architecture defines the result and its boundaries. Deployment realizes it;
development changes its implementation; administration maintains its guarantees.

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
