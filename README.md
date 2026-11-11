# Private Cloud IaC Baseline

A security-first deployment kit for building and operating a private cloud at
homelab or small-datacenter scale. Packer builds images, Terraform provisions
infrastructure, and Ansible configures hosts using the same inventory inputs.
Proxmox is the chosen virtualization platform. Kubernetes is the cluster goal;
Talos is the current node-OS implementation, not an architecture requirement.
Runnable workflows and project integration starters are distinguished in the
[implementation support map](docs/08-reference/implementation-support.md).

The design follows one rule: **it should be easy to do right**. Networks are
named by purpose; tiers divide ownership into infrastructure and trust (Tier 0),
shared services (Tier 1), and public edge, clients and workloads (Tier 2).

Use this public upstream for examples and code. Keep operational configuration
in private generated repositories, a private fork, or a local working copy.

## Getting started

For a first installation without a prepared execution host, follow the
[manual template and bootstrap-host steps](docs/03-deployment/foundation/README.md) first.

From the upstream kit checkout, generate the IaC collection:

```bash
bash scripts/init-tier-repos.sh
```

By default, this creates `../homelab-iac/`, beside this checkout. Requires Python 3 with
PyYAML; see [local tooling](docs/04-development/local-setup.md).
Use `--prefix <prefix>` to rename the collection and repos (default: `homelab`), `--root /path/to/parent`
to choose their parent directory, or `--dry-run` to preview without writing.
Prefix casing is preserved in document headings; generated folder names are lowercase.

Default collection:

```text
homelab-iac/                 # collection directory, not a Git repository
  homelab-tier-0/
  homelab-tier-1/
  homelab-tier-2/
  homelab-shared/
  homelab-architecture/
```

First, fill in `<prefix>-architecture/platform-standards.md` inside the
collection. Use the [VMID quick reference](docs/02-conventions/vmid-convention.md)
before assigning Proxmox guest or template IDs. Then follow `<prefix>-tier-0/README.md`
from that tier's root; its
commands use tier-local code and shared helpers with local inputs. Substitute
the prefix if customized. Each README is a developer-owned starter template.
Track completed deployment paths and options in `<prefix>-architecture/deployments.md`.

The [deployment checklist](docs/06-paths/tier-0/README.md#deployment-order) leads
from foundation prerequisites through software intake, protected logging, trust, Kubernetes, identity,
shared services and controlled automation. Each capability has a numbered deployment path.
Use `<prefix>-architecture/docs/README.md` for selected design and evidence links,
and `deployments.md` beside its root README for completed paths and options. These lead to the `docs/auto-docs/` manual;
add project documentation only for local differences or operating records.

<a id="update-your-collection"></a>

## Update the Collection

After updating this upstream checkout, run this **from the upstream repo**:

```bash
bash scripts/init-tier-repos.sh --refresh
```

Reuse the `--prefix` and `--root` flags if customized. Add `--dry-run` to preview.
Refresh updates kit automation and replaces example files with their current versions,
saving backups before replacing local code edits.
It preserves local configuration and project records, restores missing generated files,
and removes obsolete auto-docs. Use `--code-conflicts ask` to choose per edited automation file,
or `--code-conflicts preserve` to keep local development changes. See the
[refresh contract](docs/04-development/generated-repositories.md#refresh-and-local-ownership).
A final review summary links preserved automation/configuration differences to current templates and lists
retired generated code. Changed examples point to matching local configuration for comparison.
README/prose differences are omitted; project documents stay protected.

<a id="find-your-way"></a>

## Navigation

| Need | Start here |
| --- | --- |
| Documentation map | [Documentation](docs/README.md) |
| Names, tags, VMIDs and network allocations | [Conventions](docs/02-conventions/README.md) |
| Platform design | [Architecture overview](docs/01-architecture/README.md) |
| Networks and VLANs | [Network map](docs/01-architecture/05-networking/README.md) |
| Choose a deployment | [Reader paths](docs/06-paths/README.md) |
| Run, plan, or destroy | [Repository scripts](docs/08-reference/repository-scripts.md) |
| Back up or recover a VM, host or platform | [Operations and recovery](docs/05-operations/README.md) |
| Find implementation files | [Automation layout](docs/04-development/code-layout.md) |
| Handle secrets | [Secret strategy](docs/05-operations/03-cryptography/secret-handling.md) |
| Deploy private PKI and public HTTPS | [Software-backed PKI](docs/03-deployment/stage-3-trust/procedures/software-pki.md) |

## Repository Structure

- `docs/01-architecture/`: foundational capabilities, platform relationships and implementation variants
- `docs/02-conventions/`: naming and allocation conventions
- `docs/03-deployment/`, `docs/04-development/`, `docs/05-operations/`: installation, code and operations
- `docs/06-paths/`, `docs/07-decisions/`, `docs/08-reference/`: checklists, decisions and exact contracts
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
[code map](docs/04-development/code-layout.md) explains the files.

## AI-Assisted Development

AI may help draft documentation and implementation. Human review remains
required for architecture, security controls, secrets, and production behavior.

## License

This upstream kit uses the MIT License. Generated projects select their own
licensing terms; copied material retains its upstream notices. See
[licensing and attribution](docs/04-development/generated-repositories.md#licensing-and-attribution).
