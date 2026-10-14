# Private Cloud IaC Baseline

A security-first deployment kit for building and operating a private cloud at
homelab or small-datacenter scale. Packer builds images, Terraform provisions
infrastructure, and Ansible configures hosts using the same inventory inputs.
Proxmox is the chosen virtualization platform. Kubernetes is the cluster goal;
Talos is the current node-OS implementation, not an architecture requirement.

The design follows one rule: **it should be easy to do right**. Networks are
named by purpose; tiers divide ownership into infrastructure and trust (Tier 0),
shared services (Tier 1), and public edge, clients and workloads (Tier 2).

Use this public upstream for examples and code. Keep operational configuration
in private generated repositories, a private fork, or a local working copy.

## Getting started

From this cloned repository, generate the IaC collection:

```bash
bash scripts/init-tier-repos.sh
```

This creates `../homelab-iac/`, beside this checkout. Requires Python 3 with
PyYAML; see [local tooling](docs/development/local-setup.md).
Use `--prefix mylab` to rename the collection and repos, `--root /path/to/parent`
to choose their parent directory, or `--dry-run` to preview without writing.

```text
homelab-iac/                 # collection directory, not a Git repository
  homelab-tier-0/
  homelab-tier-1/
  homelab-tier-2/
  homelab-shared/
  homelab-architecture/
```

First, fill in `homelab-architecture/docs/naming-conventions.md` inside the
collection. Then follow `homelab-tier-0/README.md` from that tier's root; its
commands use tier-local code and shared helpers with local inputs. Substitute
the prefix if customized. Each README is a developer-owned starter template.

The [deployment checklist](docs/paths/tier-0/README.md#deployment-order) leads
from Proxmox and templates through trust, identity, Kubernetes, shared services,
and controlled automation. Each stage links to its detailed procedure.
Select [domain patterns](docs/architecture/README.md#technical-domains) in each generated
repo's `docs/architecture/README.md`; keep procedures under `docs/deployment/`,
`docs/development/`, and `docs/administration/`.

<a id="update-your-collection"></a>

## Update the Collection

After updating this upstream checkout, run this **from the upstream repo**:

```bash
bash scripts/init-tier-repos.sh --refresh
```

Reuse the `--prefix` and `--root` flags if customized. Add `--dry-run` to preview.
Refresh updates unchanged auto-docs, examples, and automation. It preserves
repository READMEs, project documentation, local work, and recorded deletions. See the
[refresh contract](docs/development/generated-repositories.md#refresh-and-local-ownership).

<a id="find-your-way"></a>

## Navigation

| Need | Start here |
| --- | --- |
| Documentation map | [Documentation](docs/README.md) |
| Platform design | [Architecture overview](docs/architecture/README.md) |
| Networks and VLANs | [Network map](docs/architecture/networking/README.md) |
| Choose a deployment | [Reader paths](docs/paths/README.md) |
| Run, plan, or destroy | [Repository scripts](docs/reference/repository-scripts.md) |
| Find implementation files | [Automation layout](docs/development/code-layout.md) |
| Handle secrets | [Secret strategy](docs/administration/secret-handling/strategy.md) |

## Repository Structure

- `docs/architecture/`: platform relationships and technical-domain designs
- `docs/deployment/`, `docs/development/`, `docs/administration/`: installation, code and operations
- `docs/paths/` and `docs/reference/`: repository checklists and exact contracts
- `tier-0/`: infrastructure and trust services, VM template code, Packer builds, and bootstrap
- `tier-1/`: shared-platform service code, Terraform roots, Ansible inputs, and cluster starters
- `tier-2/`: public edge, ordinary outbound caches, workload code and project starters
- `shared/`: baseline roles, generic helpers, sizing data, and image/platform references
- `scripts/`: repository-generation tooling and README/project-doc templates
- `tests/`: offline generator and automation checks
- `.ai/`: assistant context

The source split mirrors the generated repositories. Each tier owns its
Terraform resources, inventory, and state; Terraform and Ansible share that
tier's host inputs. Shared never owns inventory or state. Read Terraform as
**inputs -> deployments -> modules -> resources**; the
[code map](docs/development/code-layout.md) explains the files.

## AI-Assisted Development

AI may help draft documentation and implementation. Human review remains
required for architecture, security controls, secrets, and production behavior.

## License

This upstream kit uses the MIT License. Generated projects select their own
licensing terms; copied material retains its upstream notices. See
[licensing and attribution](docs/development/generated-repositories.md#licensing-and-attribution).
