# Proxmox planning guidelines

## Table of contents

- [Purpose](#purpose)
- [Why decide this early](#why-decide-this-early)
- [What this covers](#what-this-covers)
- [VM and template ID ranges](#vm-and-template-id-ranges)
- [Templates](#templates)
- [Template names](#template-names)
- [Template tags](#template-tags)
- [Virtual machines](#virtual-machines)
- [VM names](#vm-names)
- [VM tags](#vm-tags)
- [Naming boundaries](#naming-boundaries)
- [Related references](#related-references)

## Purpose

Use this as the current source of truth for the Proxmox planning guidelines
used across this repository.

These are recommended patterns, not hard requirements. Record your selections
in the generated architecture repo's short `docs/naming-conventions.md`
worksheet. Keep the complete host list in inventory, not in that document.

Names describe roles, tags add detail, and VMID ranges group resource types.
None of them encode a tier or grant network access.

## Why decide this early

Set these guidelines early when you first shape the environment.

Later changes can affect:

- how easy it is to scale VM creation and template reuse
- how clearly Terraform and Ansible definitions map to the platform
- how easy it is to reserve space for infrastructure, services, and workloads
- how much cleanup is needed when the environment grows

## What this covers

This document currently owns the shared guidance for:

- reusable VM and template ID ranges
- template naming patterns used by shared images
- VM naming patterns used by deployed guests
- VM tag patterns used for more specific service identity
- common template tags used in the manual Proxmox flow
- naming boundaries that point to the network and hardening references

## VM and template ID ranges

Use these ranges when you want a stable split between template, infrastructure,
and application workloads. If you prefer a different range plan, decide it
before broad provisioning starts and keep it consistent.

| Range | Purpose |
| --- | --- |
| `100-199` | Base templates and staged Linux template builders |
| `200-299` | Infrastructure |
| `300-399` | Shared services |
| `400-499` | Databases |
| `500-999` | Application and lab VMs |
| `9000-9999` | Versioned template candidates in the publication catalog |

VMID `200` means an infrastructure allocation, not Tier 2, VLAN 200, or an
address. Reserve non-overlapping IDs across all repos and environments using
the same Proxmox cluster. The publication catalog uses example candidates
`9100-9102`; legacy base templates and staged refresh builders use `100-199`.
These are conventions, not a request to renumber deployed resources.

Terraform examples should set `vm_id` explicitly for repo-managed guests so
deployments are predictable and do not depend on Proxmox auto-allocation.
Change the example IDs before deployment when the range is already used in your
cluster.

## Templates

### Template names

Keep shared template names short and descriptive. The current pattern is:

```text
<os>-<major>-tmpl
```

Current examples:

- `alma-10-tmpl`
- `rocky-10-tmpl`

When the same OS release has different image lifecycle tracks, add a short
generic variant before `tmpl`. Keep implementation names such as `bootc` out of
the VM name unless you intentionally want the template tied to that
implementation:

```text
<os>-<major>-<variant>-tmpl
```

Examples:

- `rhel-10-immu-tmpl`
- `alma-10-immu-tmpl`
- `fedora-42-immu-tmpl`

For versioned publication candidates, add a build suffix, such as
`<os>-<release>-tmpl-<build>`, and record the exact release in the catalog.
Existing catalog names are placeholders to replace with your chosen pattern.

Keep environment-specific names, hostnames, and workload labels out of reusable
templates.

### Template tags

Add tags one by one in the Proxmox GUI.

Use template tags for image identity, not future workload identity.

Recommended practice:

- use tags in clear categories so they stay filterable in the Proxmox GUI
- keep template tags focused on architecture, distro, release, and image
  capabilities
- avoid service or workload tags on templates because those belong on deployed
  VMs
- register template tags in `linux_vm_template_catalog` so Terraform-created
  guests can carry source-image tags based on the selected template VM ID

Suggested tag categories:

| Category | Purpose | Current examples |
| --- | --- | --- |
| `arch` | target architecture | `x86_64`, `aarch64` |
| `family_release` | OS family or release track | `el10`, `debian12`, `windows_nt` |
| `capability` | image capability or build style | `cloud-init`, `uefi`, `immutable`, `bootc` |
| `image_source` | exact distro or OS image source | `alma10`, `rocky10`, `ubuntu2404`, `debian12`, `windows11` |

## Virtual machines

### VM names

Use short, predictable VM names for deployed guests. The stable inventory key is:

```text
<role>-<n>
```

Choose one order. The simplest default is `<env>-<role>-<n>`, with the
environment omitted for production. The automation also supports a suffix
before the number when that is your established convention:

```text
<env>-<role>-<n>
<role>-<env>-<n>
<role>-<n>
```

Do not add tier, zone, VLAN, IP, or VMID to the hostname. Those belong in
ownership, inventory, or network records and can change independently.

Name parts:

| Part | Purpose | Current examples |
| --- | --- | --- |
| `env` | optional short, stable environment marker | `test`, `prod`, `dev` |
| `role` | generic, stable workload role | `idm`, `idp`, `ca`, `ca-root`, `edge-lb`, `hsm`, `k8node`, `db`, `pbs` |
| `n` | always-present numeric suffix | `1`, `2`, `3` |

Current examples:

- `test-idm-1`
- `idm-test-1`
- `ca-root-test-1`
- `dev-k8node-1`
- `prod-db-1`

Recommended practice:

- keep `env` short and stable so names stay easy to read and sort
- use `role` for the generic workload function, such as `db` instead of a
  product name like PostgreSQL, so the VM name and DNS can stay stable if the
  implementation changes later
- use product tags when the exact implementation matters, such as `freeipa` on
  `idm-1` or `keycloak` on `idp-1`
- always keep the numeric suffix, even for the first VM, because you may later
  need more than one instance of the same role

### VM tags

Use tags for the exact service or implementation when that detail may change
over time while the VM name and DNS stay stable.

Terraform-created guests receive source-image tags from
`linux_vm_template_catalog` in `terraform/common.tfvars` before their workload
tags are added. Terraform looks up the tags by the selected template VM ID,
including per-VM `template_vm_id` overrides. Treat `vm_instances.<key>.tags` as
workload-specific tags and use `vm_instances.<key>.template_tags` only as an
escape hatch for a source image that is not in the catalog. Template-producing
setups may use `vm_instances.<key>.template_catalog_id` when the builder should
receive tags for the target template ID instead of the source clone template
ID.

Recommended practice:

- use tags in clear categories so they stay filterable in the Proxmox GUI
- keep category values short and stable
- use tags for the exact service, such as `postgres`, `mariadb`, `vault`,
  `openbao`, `haproxy`, or `traefik`
- change tags when the service implementation changes

These category names organize the convention; the actual tags are the short
values shown below, not a required `category:value` syntax. Tag order has no
security meaning.

| Category | Purpose | Current examples |
| --- | --- | --- |
| `sla` | operational priority and recovery expectation | `critical`, `high`, `standard`, `low` |
| `exposure` | trust boundary or security posture | `public`, `internal`, `restricted`, `isolated` |
| `lifecycle` | expected runtime behavior | `always-on`, `scheduled`, `ephemeral`, `legacy`, `maintenance` |
| `ownership` | team or operator responsibility | `platform`, `security`, `data`, `apps`, `team-foo` |
| `service` | exact implementation or product | `postgres`, `mariadb`, `vault`, `openbao`, `haproxy`, `traefik`, `nginx`, `redis` |

When you use tags this way, you can keep the hostname stable while still
filtering by urgency, security posture, runtime pattern, owner, and actual
service.

## Naming boundaries

Use these related documents as the source of truth for adjacent platform
guidelines:

- use [Host networking](network-prerequisites.md) and
  [Network architecture](../../architecture/network.md)
  for bridge, VLAN, and subnet naming
- use [Hardening baseline](hardening.md) for the checkpoint that node, bridge,
  and storage names are finalized before broad automation
- keep environment-specific VM names, IP settings, and workload labels in local
  Terraform variables and Ansible inventory rather than in shared templates

## Related references

- [Proxmox reference platform](README.md)
- [Enterprise Linux template](enterprise-linux-template.md)
- [Proxmox maturity path](maturity-path.md)
