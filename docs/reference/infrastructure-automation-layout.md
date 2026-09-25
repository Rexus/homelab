# Infrastructure automation layout

## Table of contents

- [Purpose](#purpose)
- [Source ownership](#source-ownership)
- [Terraform structure](#terraform-structure)
- [Ownership rule](#ownership-rule)
- [Environment data split](#environment-data-split)
- [Terraform setups](#terraform-setups)
- [Shared automation](#shared-automation)
- [Tier-owned automation](#tier-owned-automation)
- [Maintaining the split](#maintaining-the-split)
- [References](#references)

## Purpose

Use this reference only when you need to find the automation code behind the
guides.

Guides and walkthroughs live under `docs/`. The automation directories stay
focused on source, examples, modules, roles, and playbooks.

The source tree mirrors the generated ownership boundaries. Generation copies
the tier and shared payloads, renames sibling references for the chosen prefix,
and adds repository front doors. Read [Generated repository model](generated-repository-model.md)
for downstream ownership and refresh behavior.

For run order, prerequisites, and setup-specific choices, follow the guide
linked for that deployment instead of this reference.

## Source ownership

| Source directory | Generated destination | Contains |
| --- | --- | --- |
| `tier-0/` | `<prefix>-tier-0/` | control services, host administration, complete template workflows, bootstrap |
| `tier-1/` | `<prefix>-tier-1/` | platform service code, inputs, and cluster starters |
| `tier-2/` | `<prefix>-tier-2/` | workload code, inputs, and project starters |
| `shared/` | `<prefix>-shared/` | baseline roles, generic runtime helpers, stateless sizes and image references |
| `docs/` | `<prefix>-architecture/docs/auto-docs/` | authoritative upstream guidance |
| `scripts/tier-repos/` | not copied | generation, refresh policy, README/project-doc templates |
| `tests/` | not copied | offline source and generated-repository checks |

Inside **each tier**, the paths are the same before and after generation:

| Tier-relative path | Responsibility |
| --- | --- |
| `.deployment-setups` | Linux setup names supported by the shared helper |
| `terraform/deployments/<setup>/` | provisioning roots and hardware examples |
| `terraform/modules/` | tier-owned inventory resolution and VM/LXC resources |
| `terraform/common.tfvars.example` | defaults for that tier's setups |
| `ansible/inventory/hosts.yml.example` | logical hosts and service groups |
| `ansible/group_vars/` | tier identity, IP maps, and service examples |
| `ansible/playbooks/` | tier service entry points and control-node requirements |
| `ansible/roles/` | service-specific roles, where needed |
| `ansible/ansible.cfg` | tier inventory; local roles first, then shared roles |
| `scripts/` | tier commands and entry points to shared runtime helpers |

Operational paths below are relative to the owning tier. Start there, not at
the kit root. Direct shared calls use `../shared/` in source and
`../<prefix>-shared/` after generation. No aggregate inventory or deployment
context exists at the kit root.

## Terraform structure

Read the design as **inputs -> deployments -> modules -> resources**.
Every tier uses `terraform/deployments/<name>/` for runnable **root modules**
and `terraform/modules/<building-block>/` for **child modules**. `foundation`,
`kubernetes`, and `templates` are deployment names, not different layout patterns.

A root module describes a deployment and connects its building blocks, roughly
like an Ansible playbook connects roles. A child module implements a focused
piece of infrastructure. This is module composition, not a new wrapper language. [1]
The directory name `deployments/` is this repository's convention, not a Terraform keyword.

| Read or edit | Location | Responsibility |
| --- | --- | --- |
| Host identity | `ansible/inventory/`, `ansible/group_vars/` | names, groups, and IPs consumed by both tools |
| Guest deployment values | `deployments/<name>/terraform.tfvars.example` | hardware and deployment choices; initialize a local `.tfvars` file |
| Deployment design | `deployments/<name>/main.tf` | connect inputs and modules; follow sibling resource files where needed |
| Building blocks | `modules/<name>/main.tf` | resource implementation and internal relationships |
| Input contract | `variables.tf` in a root or child module | accepted values, types, defaults, and validation |
| External connections | root `providers.tf` | provider configuration and authentication inputs |
| Tooling and state backend | root `versions.tf` | Terraform/provider requirements and backend declaration |
| Exported results | `outputs.tf`, where needed | values exposed to callers or operators |

Paths in this table after the first row are relative to the tier's `terraform/`
directory. Terraform evaluates the `.tf` files in a directory together; file
names aid navigation, not execution order. `main.tf`, `variables.tf`, and
`outputs.tf` follow the standard module convention. [2][3]
Template publication takes image recipes from `templates/proxmox.yml` at the
tier root instead of guest `.tfvars`; it does not consume guest inventory.

Start with [foundation's composition](../../tier-0/terraform/deployments/foundation/main.tf):
`module.environment` resolves inventory plus hardware inputs, then feeds
`module.vms` and `module.lxcs`. Shared contributes stateless sizes and approved
image references, not Terraform modules or inventory. Talos keeps its cluster-specific
resources in its root's `machines.tf`; a one-off resource does not need a child
module just to fit the layout.

Each deployment has an independent lifecycle and state. An **environment** such
as `test` or `prod` is a choice of values and state within a Linux deployment,
not another source-code hierarchy. Keep the existing commands and separate
template, cluster, and service states; do not apply the entire tier as one root.

## Ownership rule

Keep shared host identity in Ansible and hardware placement in Terraform.

This contract applies independently inside each tier. Here, "shared" inputs
mean shared by Terraform and Ansible within that tier, not a live inventory in
the shared-code repository.

| Owner | Defines |
| --- | --- |
| Ansible inventory | stable logical host keys and service groups |
| Ansible `all` group vars | hostname prefix or suffix, domain, and baseline inputs |
| Ansible setup group vars | guest IP map, service settings, and host configuration inputs |
| Terraform deployment tfvars | Proxmox VMID, tags, size, storage class, disk size, network zone, and optional Proxmox node override |
| Shared template catalog | approved image IDs, titles, source nodes, family, image tags, and the default Linux selection |
| Tier Terraform common tfvars | default platform node, storage mappings, guest network attachments, optional template selection, and cloud-init SSH keys |

Terraform guest maps are keyed by the matching Ansible inventory host key, for
example `idm-1`. Keep that key stable across environments.
Set `vm_instances.<key>.vm_id` and `lxc_instances.<key>.vm_id` explicitly in
examples so repo-managed guests follow the Proxmox VMID ranges from the platform
conventions. Change the IDs when those ranges are already used in your cluster.

Use `platform_hostname_prefix`, `platform_hostname_suffix`, and
`platform_domain` in `all.yml` or `all.<env>.yml` to shape each environment.
The same logical key can become `test-idm-1.corp.example.com`,
`idm-test-1.corp.example.com`, or `idm-1.corp.example.com`.
Use a private internal subdomain such as `corp.example.com` or
`internal.example.com` instead of the public website apex.
Use DNS-safe environment names with letters, numbers, and dashes.
Do not include separators in the prefix or suffix value; the automation adds
the dash only when the value is not empty. Suffixes are inserted before the
numeric suffix, so `ca-root-1` becomes `ca-root-test-1`.

Setup group vars own `platform_host_ips`, so `foundation.yml`,
`edge.yml`, and the other setup files stay small and focused.
Terraform reads the same setup group vars for the guest IP map and generated
Proxmox name, so IPs and names are not maintained in both tools.
Every Terraform guest key should have a matching `platform_host_ips` entry, or
the value `dhcp` when that guest is intentionally dynamic.
For DHCP guests, Ansible connects to `platform_fqdn`; provide a working DNS
record from the deployment host before configuration. The kit does not discover
leases or create DNS records. Static entries continue to use their mapped IP.
Existing collections keep their live inventory on refresh; compare its
`ansible_host` expression with the updated example to adopt this DHCP behavior.
Static guest addressing uses the CIDR prefix and gateway in Terraform
`network_zones`. Keep each zone focused on deployable guest networks:
`bridge`, optional `vlan_id`, `cidr_ipv4`, and optional `gateway_ipv4`.
When you use `<setup>.<env>.yml`, keep the full IP map for that setup in the
environment file. The wrapper layers YAML files predictably, but it does not
try to merge partial maps.

When `--env` is used, the wrapper loads both the environment-wide vars file and
the matching setup vars file when that setup has one. For example,
`--env test` with `foundation` loads `all.test.yml` and
`foundation.test.yml`.

Use `default_platform_node_name` for initial VM placement or the LXC target node.
Only set `proxmox_node_name` on an individual guest when you intentionally
override that default for a clustered Proxmox placement.
After VM creation, Proxmox owns node moves; changing this input does not migrate
an existing VM. This does not cover external LXC migration. See the
[cluster placement contract](../platforms/proxmox/cluster-ha.md#terraform-against-the-cluster).
The older `default_proxmox_node_name` key is still accepted as a compatibility
fallback, but new local files should use the platform-generic name.

The shared `templates/proxmox-catalog.tfvars` supplies the approved
`default_linux_vm_template_id`. Override it in tier common inputs, `terraform.tfvars`, or
`terraform.<env>.tfvars` when one deployment tests another supported distro or
template. Use `vm_instances.<key>.template_vm_id` only when one guest should
differ from the deployment default.

Maintain image metadata once in shared `proxmox_template_catalog`; keep only
guest-specific tags and selections in the tiers. The shared helper loads that
file first and Linux roots pass it to their tier-local inventory resolver. See
[template references](../platforms/proxmox/template-catalog.md) for the contract,
source-node selection, builder output tags, and migration of legacy
`linux_vm_template_catalog` overrides. Template recipes and publication remain
entirely Tier 0-owned.

## Environment data split

Within each tier, use the same source code and main inventory for every
environment. Split only the data that changes:

| Layer | Test example | Production default |
| --- | --- | --- |
| Terraform setup vars | `terraform/deployments/foundation/terraform.tfvars` | `terraform/deployments/foundation/terraform.tfvars` |
| Optional Terraform setup overlay | `terraform/deployments/foundation/terraform.test.tfvars` | not used by default |
| Shared Terraform vars | `terraform/common.tfvars` or `--common-var-file` override | `terraform/common.tfvars` or `--common-var-file` override |
| Shared consumer catalog | sibling shared `templates/proxmox-catalog.tfvars` | same reviewed catalog; tier selection overrides are optional |
| Optional tier-wide Terraform overlay | `terraform/common.test.tfvars` | not used by default |
| Ansible inventory | `ansible/inventory/hosts.yml` | `ansible/inventory/hosts.yml` |
| Ansible environment vars | `ansible/group_vars/all.test.yml` from `all.env.yml.example` | `ansible/group_vars/all.yml` |
| Ansible setup vars | `ansible/group_vars/foundation.yml` plus `foundation.test.yml` | `ansible/group_vars/foundation.yml` |
| Terraform state | `.terraform/state/foundation/test/terraform.tfstate` | `.terraform/state/foundation/prod/terraform.tfstate` |

The repository wrapper keeps Terraform state separate per setup and
environment. Terraform vars are shared by default and only layered per
environment when the optional override files exist. Do not share a Terraform
state file between environments. Omit `--env` for production.

## Terraform setups

Every Linux setup lives in `<owner>/terraform/deployments/<setup>/` with its IP and
service example at `<owner>/ansible/group_vars/<stem>.yml.example`. The stem
replaces setup-name dashes with underscores.

| Owner | Setup | Guide |
| --- | --- | --- |
| `tier-0` | `foundation` | [Identity](../paths/shared-services/identity.md) |
| `tier-0` | `vault` | [Vault](../paths/shared-services/vault.md) |
| `tier-0` | `hsm` | [HSM scope and connected adaptation](../security/usb-hsm-active-active-blueprint.md) |
| `tier-0` | `immutable-template` | [Image-based Linux](../paths/application-platform/image-based-linux.md) |
| `tier-0` | `template-refresh` | [Enterprise Linux templates](../platforms/proxmox/enterprise-linux-template.md) |
| `tier-1` | `edge` | [Edge](../paths/shared-services/edge.md) |
| `tier-1` | `cache` | [Cache](../paths/shared-services/cache.md) |
| `tier-1` | `development` | [Development platform](../paths/application-platform/development.md) |
| `tier-1` | `observability` | [Observability](../paths/system-control/observability.md) |
| `tier-1` | `podman-runner` | [Podman runner](../paths/application-platform/podman-runner.md) |
| `tier-2` | `lab` | [Local setup](../getting-started/local-setup.md) |

Base-image publication is a Day 0-1 Tier 0 root at `tier-0/terraform/deployments/templates/`.
Its catalog, approved offline artifacts, and optional CI starter live under
`tier-0/templates/` and `tier-0/ci/`. See [Template lifecycle](../platforms/proxmox/template-lifecycle.md).

The Kubernetes control cluster has its own Tier 0 root at `terraform/deployments/kubernetes/`
and `scripts/kubernetes-cluster.sh`. It currently uses Talos inventory groups/IPs
and native configuration rather than the Linux setup helper. Start with the
[cluster guide](../platforms/kubernetes/README.md); use the
[Talos implementation](../platforms/talos/terraform.md) for exact inputs and state.

Tier-local VM roots remain workload definitions with separate state. Tier 0 owns
hardware-facing control and the future delegated execution service; no state
is moved by generation. Current wrappers are operator tools, not a workload-user
API. See [Infrastructure control](../architecture/infrastructure-control.md).

## Shared automation

| Source path | Contains |
| --- | --- |
| `shared/templates/proxmox-catalog.tfvars` | one project-owned consumer catalog; approved through Tier 0 review |
| `shared/config/guest-sizes.json` | stateless VM/LXC size profiles read by tier-local Terraform |
| `shared/ansible/playbooks/` | control-node checks, baseline site play, and local SSH-key cleanup |
| `shared/ansible/roles/` | baseline and shared task fragments |
| `shared/ansible/requirements.yml` | common Ansible collections |
| `shared/scripts/` | deployment, local-input initialization, tier-context checks |

Shared never owns inventory, Terraform resources, credentials, state, or deployment
inputs. It provides reusable execution code, roles, and stateless data only.

## Tier-owned automation

| Owner | Implementation |
| --- | --- |
| Each tier | `terraform/modules/environment_guests/`, `vm/`, and `lxc/`; inventory resolution and resource lifecycle |
| Tier 0 | `terraform/deployments/kubernetes/`, `scripts/kubernetes-cluster.sh`, Talos inventory groups and IPs |
| Tier 0 | `terraform/modules/proxmox_templates/`, `scripts/proxmox-templates.sh`, `packer/`, template catalog and CI starter |
| Tier 0 | identity, secrets, HSM, Proxmox host, and Linux template-builder playbooks and roles |
| Tier 1 | edge, cache, development, observability, runner, and ingress playbooks and service roles |
| Tier 2 | lab playbook and workload definitions |

Each tier's `ansible/playbooks/control-node.yml` declares its setup-to-collection
mapping and imports the common precheck. Tier-specific collections also have a
local requirements file: Tier 0 adds the identity collection. Shared does not
register tier services. See [local tooling](../getting-started/local-setup.md).

Guest module copies intentionally give each tier control of its resource lifecycle.
They start from the same contract but are not routed through shared Terraform.
Common sizes and image references remain single-source shared data; reviewed
upstream fixes can be adopted per tier without transferring resource or state ownership.

Template image publication is entirely local to Tier 0 and needs no shared
checkout. Linux builder configuration still consumes the common baseline roles.
Packer definitions are optional custom-build scaffolds, not the automated
base-image publication path.

## Maintaining the split

- Change a setup's Terraform root, playbook, roles, and examples in its owning tier.
- Register added setups in that tier's `.deployment-setups`; the generator checks
  for missing inputs, unregistered roots, and overlapping tier ownership. Terraform-only
  roots have dedicated commands; Tier 0's `kubernetes` and `templates` are explicitly validated separately.
- Keep single-tier behavior with its owner. Extract to `shared/` only when
  multiple tiers consume the same stateless behavior; keep Terraform and all inventory tier-local.
- Keep tier-wide default examples separate: each tier owns its network and
  identity choices even when starter values match.
- Edit cluster/bootstrap starter files directly under their owning tier; they
  are seeded once downstream, not constructed in Python.
- Update README/project-doc templates under `scripts/tier-repos/templates/`
  and upstream guidance under `docs/`.

From the kit root, run the [offline checks](generated-repository-model.md#implementation-scope).
Use [repository scripts](repository-scripts.md) for operational command options.

## References

1. [Terraform module composition](https://developer.hashicorp.com/terraform/language/modules/develop/composition).
2. [Terraform files and configuration structure](https://developer.hashicorp.com/terraform/language/files).
3. [Terraform standard module structure](https://developer.hashicorp.com/terraform/language/modules/develop/structure).
