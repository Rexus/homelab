# Documentation

Architecture describes the whole platform and its technical domains. Deployment
builds that design in stages; development and administration maintain it.

| Intent | Start here | Contains |
| --- | --- | --- |
| Understand the design | [Architecture](architecture/README.md) | Platform relationships, technical domains, variants and constraints |
| Build the platform | [Deployment](deployment/README.md) | Six capability stages, numbered steps, adjacent options and detailed procedures |
| Change the code | [Development](development/README.md) | Local tooling, IaC structure, repository generation and review |
| Operate the platform | [Administration](administration/README.md) | Maintenance, backups, recovery and secret handling |
| Work from one repository | [Repository paths](paths/README.md) | Short Tier 0, Tier 1, Tier 2 and shared checklists |
| Look up an input or command | [Reference](reference/README.md) | Naming, catalogs, input contracts and CLI options |
| Understand a decision | [Decision log](decisions/README.md) | Rationale, consequences and review triggers |

## Start here

1. Read the [platform view](architecture/README.md).
2. Select [domain patterns](architecture/README.md#technical-domains).
3. Record project choices in the generated repositories' architecture records.
4. Follow the [deployment stages](deployment/README.md), using verified
   existing services wherever they satisfy the prerequisites.

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
