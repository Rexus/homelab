# Development

Start with the repository that owns the change. Follow its inputs, execution code
and checks; use the [architecture](../architecture/README.md) when changing a design boundary.

## Contents

- [Which repository?](#which-repository)
- [Where to edit](#where-to-edit)
- [Fast change loop](#fast-change-loop)
- [Exact references](#exact-references)

## Which repository?

The upstream kit supplies reusable code and examples. A generated collection holds
the private implementation and project decisions. Paths inside each tier remain
the same: upstream `tier-2/ansible/` becomes `<prefix>-tier-2/ansible/`.

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":16,"rankSpacing":20,"padding":10,"subGraphTitleMargin":{"top":4,"bottom":10}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart TB
  Kit["Upstream kit<br/>Tier / Shared payloads, docs and templates"]
  Generator["Repository generator<br/>scripts/init-tier-repos.sh"]
  subgraph Collection["&lt;prefix&gt;-iac / collection directory"]
    direction LR
    subgraph Tiers["Resource-owning repositories"]
      direction TB
      T2["&lt;prefix&gt;-tier-2<br/>Edge and lab resources"]
      T1["&lt;prefix&gt;-tier-1<br/>Shared platform services"]
      T0["&lt;prefix&gt;-tier-0<br/>Hosting and trust control"]
      T2 ~~~ T1 ~~~ T0
    end
    subgraph Support["Reusable code and documentation"]
      direction TB
      Shared["&lt;prefix&gt;-shared<br/>Scripts, roles and stateless references"]
      Architecture["&lt;prefix&gt;-architecture<br/>Project record and standards<br/>docs/auto-docs/ manual"]
      Shared ~~~ Architecture
    end
    Tiers -->|Uses code / references docs| Support
  end
  Kit --> Generator
  Generator -->|Generate / refresh| Collection
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef services fill:#e7f0fc,stroke:#4d719b,color:#203a5b
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  class Kit,Collection,Support boundary
  class T2,T1 services
  class T0,Shared control
  class Generator,Architecture data
```

**Code:** the upstream kit's `scripts/tier-repos/generate.py` and `payload.py`
implement the [generation contract](generated-repositories.md).
[Tier-local entry points](../../tier-2/scripts/deploy.sh) call Shared helpers.
This is a repository map,
not a network or deployment diagram. Inventory, resources and state stay tier-owned.
The collection directory is not itself a Git repository.

| Change | Edit in |
| --- | --- |
| Reusable fix or example for future projects | This upstream kit; verify generated output before publishing |
| Site names, IPs, guest sizes or application settings | The owning private tier repository |
| Common platform references or reusable role behavior | Shared; references may be project-owned, while managed code follows the refresh contract |
| Selected designs, standards and operating records | The architecture repository's project documents |
| Maintained manual | Upstream `docs/`; refresh copies it to `docs/auto-docs/` |

## Where to edit

| Immediate goal | Open next |
| --- | --- |
| Find the file behind a command or setting | [Code map](code-layout.md) |
| Add a guest, service configuration or separate setup | [Add a service](adding-service.md) |
| Trace a failure from its first error | [Find and fix a bug](debugging.md) |
| Prepare a checkout for development | [Local setup](local-setup.md) |
| Work before hosted source control exists | [Private repository workflow](repository-workflow.md) |
| Change a diagram alongside its code | [Diagram conventions](diagrams.md) |

## Fast change loop

1. Locate the owner and implementing files in the [code map](code-layout.md).
2. Edit the smallest responsible unit. Reuse an existing module, role or recipe;
   keep the deployment figure and inputs aligned when the topology changes.
3. Run the relevant [focused checks](testing.md), then review the diff.

Run from **the edited repository root**.

```bash
git diff --check
git diff --stat
```

For upstream generation changes, preview from **the upstream kit checkout**.

```bash
bash scripts/init-tier-repos.sh --dry-run
```

## Exact references

| Need | Authoritative reference |
| --- | --- |
| Input ownership, defaults and overrides | [Platform inputs](../reference/platform-inputs.md) |
| Proxmox guest and template IDs | [VMID convention](../conventions/vmid-convention.md) |
| Generator flags and refresh preservation | [Generated repositories](generated-repositories.md) |
| Command options and effects | [Repository scripts](../reference/repository-scripts.md) |
| Test dependencies, native tools and evidence | [Testing](testing.md) |
| Publishing and secret checks | [Secret scanning](secret-scanning.md) |
| Project-owned records and upstream references | [Project documentation](project-documentation.md) |
| Preserved architecture alternatives | [Design coverage](design-coverage.md) |
