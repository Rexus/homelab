# Shared template references

**Tier 0 creates and maintains Proxmox templates. Shared stores their approved consumer
references; every tier reads the same catalog.** A tag on a workload VM describes
its source image or service, not ownership of the template lifecycle.

## Table of contents

- [Where to edit](#where-to-edit)
- [Approve a reference](#approve-a-reference)
- [How consumers use it](#how-consumers-use-it)
- [Existing collections](#existing-collections)
- [References](#references)

## Where to edit

| Location | Responsibility |
| --- | --- |
| Tier 0 `templates/proxmox.yml` | Build/publication details: source images, checksums, releases, schematic, node, storage, network, VMID |
| Tier 0 template module, Packer, scripts, CI, and state | Create, test, update, and recover template artifacts |
| Shared `templates/proxmox-catalog.tfvars` | Approved VMIDs and titles, source nodes, OS family, and reusable image tags |
| Each tier's Terraform inputs | Select an approved template ID; define guest hardware and workload tags |
| Shared `terraform/modules/environment_guests/` | Resolve the selected template, inventory, placement, and combined guest tags once |
| Shared `terraform/modules/vm/` | Create Linux clones; tolerate subsequent Proxmox-managed node moves |

The [shared catalog starter](../../../shared/templates/proxmox-catalog.tfvars)
contains no approved images initially. It is project-owned from generation,
versionable, and never overwritten by upstream refresh. Tier 0 reviews promotions
to this shared contract; it contains no credentials, hashes, image paths, build
settings, host inventory, or Terraform state.

## Approve a reference

1. Use the Tier 0 [publication workflow](template-lifecycle.md#local-workflow).
   It works independently of shared and does not modify the consumer catalog.
2. Test disposable clones on the destination cluster and network. Publication
   outputs show candidate VMIDs, titles, and source nodes; they are not approval.
3. In shared `templates/proxmox-catalog.tfvars`, add the approved ID with its
   exact Proxmox name as `title`, source `node_name`, `family`, and image tags.
   Keep lifecycle tags such as `tier-0` and `template` out of consumer image tags.
4. Set `default_linux_vm_template_id` to the approved Linux ID when ready for
   consumers to adopt it. Talos references are listed too, but cannot be used by
   the Linux VM module; use the [Talos procedure](../talos/bootstrap.md).
5. Review and version the shared change, then review plans in consuming tiers.
   Changing the selected source template may replace VMs; pin existing guests
   with `template_vm_id` when they must stay on their current revision.

Retain old entries while guests or recovery procedures use them. Prefer a new
VMID for each approved revision. The optional Tier 0 same-ID refresh workflow
has its own explicit replacement gate and does not change this ownership model.

VMIDs belong to a Proxmox cluster. If an image is transferred from custody or
another cluster, record the **destination** ID and source node accessible to the
consumer. A reference is neither permission to administer Proxmox nor a network
route to custody. Keep independent catalogs/collections for different clusters.

## How consumers use it

Run the shared deployment helper from the owning tier root as usual. No catalog
copy into the tier is needed. The helper prints the shared path and loads:

1. Shared `templates/proxmox-catalog.tfvars`.
2. Tier `terraform/common.tfvars`, then its optional environment overlay.
3. Setup `terraform.tfvars`, then its optional environment overlay.
4. Explicit inventory and ordered group-var paths.

Terraform's later `-var-file` arguments take precedence. Maps are replaced, not
deep-merged; select an ID locally instead of maintaining another full catalog. [1]
For manual Terraform commands, include the shared file first; see the
[manual equivalent](../../reference/repository-scripts.md#manual-equivalent).

The thin tier roots pass catalog data to the typed shared resolver. The resolver
uses the actual clone ID for title and source-node selection, and adds image
tags to that guest's workload tags. Tier 0 builders may use `template_catalog_id`
for output-image tags; that never changes the clone's source node.

No consumer reads Tier 0 state or its private publication configuration.
The publisher remains independently recoverable, while consumers need only
their own checkout/inputs and a reviewed shared revision. Protect shared code
and catalog changes at the privilege level of their consumers.

## Existing collections

Refresh shared and all affected tiers together. New collections use only the
shared catalog; refresh preserves existing shared catalogs, root READMEs, and
local tier inputs, including recorded deletions.

Move common entries from tier-local `linux_vm_template_catalog` maps into shared
`proxmox_template_catalog`, changing `description` to `title` and recording
`family`. Keep existing IDs and image tags during migration. Then remove the
duplicated maps deliberately, leaving only intentional per-tier ID selections.

The legacy variable still works and overrides shared metadata for matching IDs.
An old entry can therefore hide a shared source-node setting until migrated.
If no shared catalog exists, the helper warns and uses the legacy inputs.
An empty starter does not select an image automatically. Review a no-change
plan before deployment; adding clone-source metadata can affect existing
resources, so do not apply unexpected replacements. State paths do not move.

## References

1. [Terraform variable precedence](https://developer.hashicorp.com/terraform/language/values/variables),
   checked 2026-09-22.
