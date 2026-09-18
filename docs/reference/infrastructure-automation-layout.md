# Infrastructure automation layout

## Table of contents

- [Purpose](#purpose)
- [Source ownership](#source-ownership)
- [Ownership rule](#ownership-rule)
- [Environment data split](#environment-data-split)
- [Terraform setups](#terraform-setups)
- [Shared automation](#shared-automation)
- [Maintaining the split](#maintaining-the-split)

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
| `tier-0/` | `<prefix>-tier-0/` | custody/control inputs, templates, CI starter, bootstrap, cluster starters |
| `tier-1/` | `<prefix>-tier-1/` | connected platform inputs and cluster starters |
| `tier-2/` | `<prefix>-tier-2/` | workload inputs and project starters |
| `shared/` | `<prefix>-shared/` | reusable modules, playbooks, roles, Packer definitions, runtime scripts |
| `docs/` | `<prefix>-architecture/docs/auto-docs/` | authoritative upstream guidance |
| `scripts/tier-repos/` | not copied | generation, refresh policy, README/project-doc templates |
| `tests/` | not copied | offline source and generated-repository checks |

Inside **each tier**, the paths are the same before and after generation:

| Tier-relative path | Responsibility |
| --- | --- |
| `.deployment-setups` | registered setup names |
| `terraform/environments/<setup>/` | provisioning roots and hardware examples |
| `terraform/common.tfvars.example` | defaults for that tier's setups |
| `ansible/inventory/hosts.yml.example` | logical hosts and service groups |
| `ansible/group_vars/` | tier identity, IP maps, and service examples |
| `ansible/ansible.cfg` | tier inventory plus sibling shared role path |
| `scripts/` | local entry points delegating to shared runtime code |

Operational paths below are relative to the owning tier. Start there, not at
the kit root. Direct shared calls use `../shared/` in source and
`../<prefix>-shared/` after generation. No aggregate inventory or deployment
context exists at the kit root.

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
| Terraform environment tfvars | Proxmox VMID, tags, size, storage class, disk size, network zone, and optional Proxmox node override |
| Terraform common tfvars | default platform node, shared storage mappings, guest network attachments, template IDs, and cloud-init SSH keys |

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

Use `default_platform_node_name` for the normal platform placement target.
Only set `proxmox_node_name` on an individual guest when you intentionally
override that default for a clustered Proxmox placement.
The older `default_proxmox_node_name` key is still accepted as a compatibility
fallback, but new local files should use the platform-generic name.

Use `default_linux_vm_template_id` in `terraform/common.tfvars` for the shared
Linux cloud-init template. Override it in `terraform.tfvars` or
`terraform.<env>.tfvars` when one deployment tests another supported distro or
template. Use `vm_instances.<key>.template_vm_id` only when one guest should
differ from the deployment default.

Use `linux_vm_template_catalog` in `terraform/common.tfvars` for the OS,
distro, architecture, and image-capability tags that should carry from source
templates onto cloned VMs. Terraform looks up catalog tags by the selected
template VM ID, so a per-VM `template_vm_id` override also changes the image
tags when that ID exists in the catalog. Terraform combines catalog tags with
`vm_instances.<key>.tags`, where the latter should stay focused on workload
identity. Template-producing setups can set
`vm_instances.<key>.template_catalog_id` when a builder VM should receive tags
for the target template ID instead of the source clone template ID. Set
`vm_instances.<key>.template_tags` only as an escape hatch for a source image
that is not in the catalog, or set it to `[]` when you intentionally do not
want source-image tags on that deployed VM.

## Environment data split

Within each tier, use the same source code and main inventory for every
environment. Split only the data that changes:

| Layer | Test example | Production default |
| --- | --- | --- |
| Terraform setup vars | `terraform/environments/foundation/terraform.tfvars` | `terraform/environments/foundation/terraform.tfvars` |
| Optional Terraform setup overlay | `terraform/environments/foundation/terraform.test.tfvars` | not used by default |
| Shared Terraform vars | `terraform/common.tfvars` or `--common-var-file` override | `terraform/common.tfvars` or `--common-var-file` override |
| Optional shared Terraform overlay | `terraform/common.test.tfvars` | not used by default |
| Ansible inventory | `ansible/inventory/hosts.yml` | `ansible/inventory/hosts.yml` |
| Ansible environment vars | `ansible/group_vars/all.test.yml` from `all.env.yml.example` | `ansible/group_vars/all.yml` |
| Ansible setup vars | `ansible/group_vars/foundation.yml` plus `foundation.test.yml` | `ansible/group_vars/foundation.yml` |
| Terraform state | `.terraform/state/foundation/test/terraform.tfstate` | `.terraform/state/foundation/prod/terraform.tfstate` |

The repository wrapper keeps Terraform state separate per setup and
environment. Terraform vars are shared by default and only layered per
environment when the optional override files exist. Do not share a Terraform
state file between environments. Omit `--env` for production.

## Terraform setups

Every setup lives in `<owner>/terraform/environments/<setup>/` with its IP and
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

Base-image publication is a separate Tier 0 root at `tier-0/terraform/templates/`.
Its catalog, approved offline artifacts, and optional CI starter live under
`tier-0/templates/` and `tier-0/ci/`. See [Template lifecycle](../platforms/proxmox/template-lifecycle.md).

## Shared automation

| Source path | Contains |
| --- | --- |
| `shared/terraform/modules/environment_guests/` | resolves tier inventory, names, and IP maps |
| `shared/terraform/modules/vm/`, `lxc/` | reusable Proxmox guest resources |
| `shared/terraform/modules/proxmox_templates/` | offline image import and unbooted template resources |
| `shared/ansible/playbooks/` | control-node precheck and setup/service entry points |
| `shared/ansible/roles/` | baseline, shared task fragments, and service configuration |
| `shared/ansible/requirements.yml` | required Ansible collections |
| `shared/packer/templates/proxmox/` | optional Enterprise Linux, Debian, and Talos build scaffolds |
| `shared/scripts/` | deployment, local-input initialization, template publication, tier-context checks |

The shared tree contains no live inventory, credentials, state, or per-tier
defaults. Packer inputs belong to `tier-0/packer/`; automated base-image
publication uses Terraform, not the optional Packer scaffolds.

## Maintaining the split

- Change a setup's Terraform root and Ansible examples together in its owning tier.
- Register added setups in that tier's `.deployment-setups`; the generator checks
  for missing inputs, unregistered roots, and overlapping tier ownership.
- Change reusable behavior once under `shared/`; do not copy roles into tiers.
- Keep tier-wide default examples separate: each tier owns its network and
  identity choices even when starter values match.
- Edit cluster/bootstrap starter files directly under their owning tier; they
  are seeded once downstream, not constructed in Python.
- Update README/project-doc templates under `scripts/tier-repos/templates/`
  and upstream guidance under `docs/`.

From the kit root, run the [offline checks](generated-repository-model.md#implementation-scope).
Use [repository scripts](repository-scripts.md) for operational command options.
