# Project documentation

## Table of contents

- [Purpose](#purpose)
- [Start with project values](#start-with-project-values)
- [Architecture repository layout](#architecture-repository-layout)
- [Ownership and refresh](#ownership-and-refresh)
- [Existing collections](#existing-collections)
- [Maintaining the starter templates](#maintaining-the-starter-templates)

## Purpose

Each generated repository starts with an ordinary README explaining its
purpose, entry points, and documentation. Developers maintain that README
as the repository evolves; upstream refresh never replaces it, even before
its first local edit.

The architecture repository separates project records from upstream reference
material. Use the references to make decisions, then record the chosen values
in the project documents. Do not populate local values into auto-docs.

## Start with project values

Every root README links to the architecture repository's
`docs/naming-conventions.md`. Fill in its tables before provisioning:

| Record | Detailed upstream guidance |
| --- | --- |
| VM, template, and DNS naming; environment prefixes/suffixes | [Platform conventions](../platforms/proxmox/conventions.md) and [inventory inputs](infrastructure-automation-layout.md#ownership-rule) |
| VM/LXC and template ID reservations | [ID planning](../platforms/proxmox/conventions.md#vm-and-template-id-ranges) |
| Tier/layer zones, VLANs, subnets, gateways, and attachments | [Network plan](../architecture/network.md) and [network fields](network-inputs.md) |
| Firewall object names and local policy records | [Firewall policy](../security/firewall-policy.md) |
| Platform hosts, storage mappings, and shared-code revision | [Automation layout](infrastructure-automation-layout.md) and [recovery inputs](generated-repository-model.md#shared-code-and-recovery) |

This is a compact conventions and allocation record, not a duplicate of the
live inventory. Individual host IPs and resource assignments remain in the
owning tier's Ansible and Terraform inputs.

Next, fill in the project overview and recovery runbook. They link back to
auto-docs for design and operational detail, so local records can stay concise.

## Architecture repository layout

```text
<prefix>-architecture/
  README.md                         # developer-owned repository front door
  docs/
    README.md                       # project documentation index
    naming-conventions.md           # names, IDs, network and platform choices
    owned/
      design/overview.md            # actual environment, owners, and decisions
      runbooks/recovery.md          # recovery inputs, procedures, test records
      decisions/                    # detailed local decisions as needed
      services/                     # detailed local service records as needed
      tiers/                        # tier-specific records as needed
      network/                      # actual policies and verification evidence
    auto-docs/                      # upstream-managed reference tree
      README.md
      architecture/
      paths/
      platforms/
      reference/
      security/
  site/                             # optional site integration
```

The folders are documentation organization, not separate network or ownership
models. Keep secrets out of both project records and auto-docs.

## Ownership and refresh

The generator seeds root READMEs and project documents once and records them
as owned in `.generated-files.json`. Template changes affect new files only.
An edited file stays edited; a recorded deletion stays deleted. Refresh may
add a newly introduced template at a path that has never existed, but does
not overwrite an existing project file.

Every copied guide under `docs/auto-docs/` displays **AUTO-DOCS - DO NOT EDIT**
and identifies the upstream refresh command. Unchanged managed docs can be
updated by refresh; accidental local edits are still preserved by the normal
hash checks. Move useful local decisions into project records and compare
upstream changes manually before adopting them.

The same preservation contract continues to apply to shared automation and
examples. This change does not make all scripts seed-only. See
[Refresh and local ownership](generated-repository-model.md#refresh-and-local-ownership).

## Existing collections

From the updated upstream checkout, refresh the existing collection:

```bash
bash scripts/init-tier-repos.sh --refresh
```

Reuse the original `--prefix` and `--root` flags when customized; add `--dry-run`
to preview. No repositories are moved, committed, or deployed.

Existing root READMEs are promoted to owned without rewriting their content.
Refresh adds the new project templates and `docs/auto-docs/`. Earlier
`docs/generated/upstream/` copies remain in place but are no longer refreshed.
The generator reports that legacy path when present.

Update the owned READMEs deliberately:

| README location | Link target for naming and allocations |
| --- | --- |
| tier or shared root | `../<prefix>-architecture/docs/naming-conventions.md` |
| architecture root | `docs/naming-conventions.md` |

Change upstream guide links from `docs/generated/upstream/` to `docs/auto-docs/`
while retaining their remaining path. Review any local edits in the old tree,
move project-specific content into owned records, and retire the legacy copies
only after their links and contents have been checked. Existing `docs/owned/`
content is preserved.

## Maintaining the starter templates

The upstream templates live in `scripts/tier-repos/templates/` as Markdown,
with collection names and repository-relative links filled in during generation.
They are starting points, not a second maintained copy of a project's README.
Downstream developers edit the resulting files in their own repositories.
