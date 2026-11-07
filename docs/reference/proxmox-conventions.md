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
- [Service DNS names](#service-dns-names)
- [VM tags](#vm-tags)
- [Naming boundaries](#naming-boundaries)
- [Related references](#related-references)
- [References](#references)

## Purpose

Use this as the current source of truth for the Proxmox planning guidelines
used across this repository.

These are recommended patterns, not hard requirements. Record the selections
in the generated architecture repo's short `docs/naming-conventions.md`
worksheet. Keep the complete host list in inventory, not in that document.

Names describe roles, tags add detail, and VMID ranges group resource types.
None of them encode a tier or grant network access.

## Why decide this early

Set these guidelines early when first designing the environment.

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

Use these ranges for a stable split between template, infrastructure,
and application workloads. Select any alternative range plan
before broad provisioning starts and keep it consistent.

| Range | Purpose |
| --- | --- |
| `100-199` | Staged Linux template builders and legacy base templates |
| `200-299` | Infrastructure |
| `300-399` | Shared services |
| `400-499` | Databases |
| `500-999` | Application and lab VMs |
| `9000-9999` | Versioned VM templates, including candidates and selected releases |

VMID `200` means an infrastructure allocation, not Tier 2, VLAN 200, or an
address. Reserve non-overlapping IDs across all repos and environments using
the same Proxmox cluster. The publication catalog uses example candidates
`9100-9103`; templates retain their VMIDs after clone testing and selection.
Legacy base templates and staged refresh builders can retain `100-199`.
These are conventions, not a request to renumber deployed resources.

Terraform examples should set `vm_id` explicitly for repo-managed guests so
deployments are predictable and do not depend on Proxmox auto-allocation.
Change the example IDs before deployment when the range is already used in the
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
the VM name unless the template is intentionally tied to that
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
Existing catalog names are placeholders to replace with the selected pattern.

Keep environment-specific names, hostnames, and workload labels out of reusable
templates.

### Template tags

For manual templates, add tags in the Proxmox GUI. Tier 0's publisher derives the
standard image tags from its catalog; `tags: []` on each build accepts extra variant tags.

Use template tags for image identity, not future workload identity.

Recommended practice:

- use tags in clear categories so they stay filterable in the Proxmox GUI
- keep template tags focused on CPU model, distro, release, and image
  capabilities
- avoid service or workload tags on templates because those belong on deployed
  VMs
- register reusable image tags once in the [shared template catalog](template-catalog.md) so Terraform-created
  guests can carry source-image tags based on the selected template VM ID

Suggested tag categories:

| Category | Purpose | Current examples |
| --- | --- | --- |
| `cpu` | Configured Proxmox CPU model | `x86-64-v3`, `host` |
| `release_track` | Shared family/major where applicable; otherwise distribution/major | `el10`, `debian12`, `talos1`, `fedora42` |
| `distribution` | Selected OS distribution | `alma`, `rocky`, `rhel`, `debian`, `talos` |
| `capability` | Configured image capability | `cloud-init` when NoCloud media is enabled |
| `variant` | Optional additional image property | `test`, `hardened`, `immutable`, `bootc` |

For example, a Rocky 10 template with the default CPU and CloudInit drive receives:

```text
el10, rocky, x86-64-v3, cloud-init
```

`el10` identifies the Enterprise Linux release track shared by AlmaLinux, Rocky Linux
and RHEL; the distribution tag distinguishes them. There is no redundant `el` or
`rocky10` tag. `rhel` denotes the Red Hat Enterprise Linux distribution. The catalog's
broader `family: redhat` matches Ansible's family terminology and also covers Fedora;
Fedora's release number is not an Enterprise Linux version. [1][2]

The publisher extracts the leading major number from the pinned `release`, including
an optional `v` prefix. Debian 12 produces `debian12` and `debian`; Talos v1.14 produces
`talos1` and `talos`. Derivatives with independent version numbers use their own track,
such as `ubuntu24`; a known parent version can be added explicitly in `tags`.

Use the configured CPU model as the hardware tag; do not also add a generic `x86_64`
architecture tag. CPU tags describe the guest model, not detected physical host
features or an inspected image's minimum requirement. Selecting `host` does not infer
a `v3` tag. The default `x86-64-v3` profile must work on every eligible host. [3]
The `cloud-init` tag records enabled CloudInit/NoCloud media; for Talos that media
supplies networking, while the Talos API still owns machine configuration.

Do not add `template` status or tier ownership to reusable image tags. Proxmox already
records template status; future clones can belong to any tier. Extra tags such as
`test` are deliberate and may be inherited by clones. Publication outputs expose the
resolved `tags` for review and promotion into the shared consumer catalog.

## Virtual machines

### VM names

Use short, predictable VM names for deployed guests. The stable inventory key is:

```text
<role>-<n>
```

Choose one order. The simplest default is `<env>-<role>-<n>`, with the
environment omitted for production. The automation also supports a suffix
before the number when that is the established convention:

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
- always keep the numeric suffix, even for the first VM, because the deployment may later
  need more than one instance of the same role

### Service DNS names

VM names identify individual guests. Service FQDNs identify stable endpoints
and omit the VM instance number. Record the internal and external domains,
service patterns, and role abbreviation definitions in the project's
`docs/naming-conventions.md`.

The reference internal pattern is `<role>.<env>.<internal-domain>`, such as
`idp.prod.corp.example.com`. The external pattern can use the external domain,
such as `idp.prod.example.com`. Production remains explicit in these service
examples even when the VM naming convention omits its environment marker.

Current guest automation still forms host FQDNs from the VM name and
`platform_domain`. It does not create service DNS records, ingress routes, or
certificates from the naming document. Configure these separately, pointing
each service name at its approved endpoint; an external domain does not by
itself authorize public exposure.

### VM tags

Use tags for the exact service or implementation when that detail may change
over time while the VM name and DNS stay stable.

Terraform-created guests receive source-image tags from
`proxmox_template_catalog` in shared `templates/proxmox-catalog.tfvars` before their workload
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

These tags allow hostnames to remain stable while supporting
filtering by urgency, security posture, runtime pattern, owner, and actual
service.

## Naming boundaries

Use these related documents as the source of truth for adjacent platform
guidelines:

- use [Host networking](../deployment/foundation/proxmox/network.md) and
  [Network architecture](../architecture/networking/README.md)
  for bridge, VLAN, and subnet naming
- use [Hardening baseline](../administration/compute/hardening.md) for the checkpoint that node, bridge,
  and storage names are finalized before broad automation
- keep environment-specific VM names, IP settings, and workload labels in local
  Terraform variables and Ansible inventory rather than in shared templates

## Related references

- [Proxmox reference platform](../deployment/foundation/proxmox/README.md)
- [Proxmox VM templates](../deployment/foundation/proxmox/templates.md)
- [Deployment readiness](../deployment/readiness.md)

## References

1. [Ansible OS-family mapping](https://github.com/ansible/ansible/blob/devel/lib/ansible/module_utils/facts/system/distribution.py),
   checked 2026-11-07.
2. [AlmaLinux Enterprise Linux comparison](https://wiki.almalinux.org/Comparison.html), checked 2026-11-07.
3. [Proxmox CPU models](https://github.com/proxmox/pve-docs/blob/master/qm.adoc#_cpu_type), checked 2026-11-07.
