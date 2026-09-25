# Private Cloud IaC Baseline

A security-first deployment kit for building and operating a private cloud at
homelab or small-datacenter scale. Packer builds images, Terraform provisions
infrastructure, and Ansible configures hosts using the same inventory inputs.
Proxmox is the chosen virtualization platform. Kubernetes is the cluster goal;
Talos is the current node-OS implementation, not an architecture requirement.

The design follows one rule: **it should be easy to do right**. Tiers divide
repository ownership by potential impact: Tier 0 holds the highest-impact
control systems, including hardware, network administration, and VM templates;
Tier 1 holds shared platform services, and Tier 2 workloads.
Network layers separately protect from the outside inward: Edge, Application,
Control. Each tier owns its Terraform resources, service code, inventory, and
state. Shared contains reusable scripts, Ansible roles, and stateless data only.

Use this public upstream for examples and code. Keep operational configuration
in private generated repositories, a private fork, or a local working copy.

## Getting started

From this cloned repository, generate your IaC collection:

```bash
bash scripts/init-tier-repos.sh
```

This creates `../homelab-iac/`, beside this checkout. Requires Python 3 with
PyYAML; see [local tooling](docs/getting-started/local-setup.md).
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
your prefix if customized. Each README is a developer-owned starter template.

Use the [per-repository deployment checklists](docs/paths/README.md#choose-your-repository):
prepare Proxmox (optional HA and SDN), publish templates, then build the control
cluster and dedicated authority VMs. The Tier 0 Day 0-3 checklist links each
phase to its detailed procedure, through identity integration and recovery testing.

## Update Your Collection

After updating this upstream checkout, run this **from the upstream repo**:

```bash
bash scripts/init-tier-repos.sh --refresh
```

Reuse your `--prefix` and `--root` flags if customized. Add `--dry-run` to preview.
Refresh updates unchanged auto-docs, examples, and automation. It preserves
repository READMEs, project documentation, local work, and recorded deletions. See the
[refresh contract](docs/reference/generated-repository-model.md#refresh-and-local-ownership).

## Find Your Way

| Need | Start here |
| --- | --- |
| Documentation map | [Documentation](docs/README.md) |
| System design | [Architecture overview](docs/architecture/overview.md), [tier model](docs/architecture/tier-model.md) |
| Choose a deployment | [Reader paths](docs/paths/README.md) |
| Run, plan, or destroy | [Repository scripts](docs/reference/repository-scripts.md) |
| Find implementation files | [Automation layout](docs/reference/infrastructure-automation-layout.md) |
| Maintain generated project docs | [Project documentation](docs/reference/project-documentation.md) |
| Prepare Proxmox | [Platform guide](docs/platforms/proxmox/README.md) |
| Build a Kubernetes cluster | [Cluster guide](docs/platforms/kubernetes/README.md) |
| Create or update base templates | [Tier 0 template lifecycle](docs/platforms/proxmox/template-lifecycle.md) |
| Handle secrets | [Secret strategy](docs/security/secret-strategy.md) |

## Repository Structure

- `docs/`: architecture, reader paths, platform guides, security, and references
- `tier-0/`: infrastructure and trust services, VM template code, Packer builds, and bootstrap
- `tier-1/`: shared-platform service code, Terraform roots, Ansible inputs, and cluster starters
- `tier-2/`: workload code, Terraform roots, Ansible inputs, and project starters
- `shared/`: baseline roles, generic deployment helpers, sizing data, and approved image references
- `scripts/`: repository-generation tooling and README/project-doc templates
- `tests/`: offline generator and automation checks
- `.ai/`: assistant context

The source split mirrors the generated repositories: `tier-0/` becomes
`<prefix>-tier-0/`, and `shared/` becomes `<prefix>-shared/`. Each tier keeps the
same Terraform/Ansible inventory contract. See the
[source layout](docs/reference/infrastructure-automation-layout.md) before editing automation.

Read Terraform as **inputs -> deployments -> modules -> resources**.
In every tier, start at `terraform/deployments/<name>/main.tf` and follow its
module calls into `terraform/modules/`. The [design map](docs/reference/infrastructure-automation-layout.md#terraform-structure)
explains the files; Ansible inventory remains the common host-data source.

Template recipes and publication stay in Tier 0. Approved IDs, titles, source
nodes, and image tags live once in the [shared consumer catalog](shared/templates/proxmox-catalog.tfvars),
loaded by the shared deploy helper for all tiers. See [catalog ownership](docs/platforms/proxmox/template-catalog.md).

## AI-Assisted Development

AI may help draft documentation and implementation. Human review remains
required for architecture, security controls, secrets, and production behavior.

## License

MIT License
