# Shared template references

**Tier 0 creates and maintains Proxmox templates. Shared stores their published consumer
references; every tier reads the same catalog.** A tag on a workload VM describes
its source image or service, not ownership of the template lifecycle.

## Table of contents

- [Where to edit](#where-to-edit)
- [Publish references and select a default](#publish-references-and-select-a-default)
- [How consumers use it](#how-consumers-use-it)
- [Existing collections](#existing-collections)
- [References](#references)

## Where to edit

| Location | Responsibility |
| --- | --- |
| Tier 0 `templates/proxmox.yml` | Build/publication details: source images, checksums, releases, schematic, node, storage, network, VMID |
| Tier 0 template module, Packer, scripts, CI, and state | Create, test, update, and recover template artifacts |
| Shared `templates/proxmox-catalog.tfvars` | Published IDs, source nodes, family, tags, boot hardware and TPM-free source evidence; project-selected default |
| Each tier's Terraform inputs | Select a template ID; define capacity, network, disks and workload tags; optional boot-hardware override |
| Each tier's `terraform/modules/environment_guests/` | Resolve that tier's template selections, inventory, placement, and combined guest tags |
| Each tier's `terraform/modules/vm/` | Create Linux clones; tolerate subsequent Proxmox-managed node moves |
| Each tier's `terraform/deployments/kubernetes/` | Create Talos nodes through the retained clone or fresh signed-ISO route; configure its independent cluster through the API |

The [shared catalog starter](../../shared/templates/proxmox-catalog.tfvars)
contains no images initially. It is project-owned from generation,
versionable, and never overwritten by upstream refresh. Successful Tier 0 template
apply updates its references; it contains no credentials, hashes, image paths, build
settings, host inventory, or Terraform state.

<a id="approve-a-reference"></a>

## Publish references and select a default

1. Use the Tier 0 [publication workflow](../05-operations/01-hosting/templates/template-lifecycle.md#local-workflow).
   After Terraform apply, template-policy checks and state refresh succeed, the script
   updates the sibling Shared catalog from the applied `template_candidates` output.
   VMID becomes the map key; name becomes `title`; node, family, image tags and
   BIOS/machine/SCSI/EFI settings and the boolean `tpm_state_present` follow the applied template.
2. Test disposable clones on the destination cluster and network. Publication
   and catalog synchronization do not prove guest acceptance.
3. Review the updated Shared file. Existing VMIDs are refreshed, older entries and
   extra entry fields are retained, and `default_linux_vm_template_id` is preserved.
   No-change synchronization leaves the file untouched. The reference map's formatting
   is regenerated; settings and comments outside it remain. The
   [tag convention](../02-conventions/proxmox-conventions.md#template-tags) applies to the synchronized image tags.
4. Set `default_linux_vm_template_id` in Shared to the tested Linux ID when ready for
   consumers to adopt it. Talos references are listed too, but cannot be used by
   the Linux VM module; use the [Talos Kubernetes implementation](../03-deployment/stage-04-kubernetes/procedures/talos-terraform.md) or the
   [manual procedure](../03-deployment/stage-04-kubernetes/step-1b-existing-cluster.md).
5. Review and version the shared change, then review plans in consuming tiers.
   The clone source applies when creating a VM; changing it does not upgrade an existing guest.
   Its boot-hardware profile initializes new VMs; existing/imported guests retain their boot settings.
   Pin existing guests with `template_vm_id` to retain the correct source record for future recreation.

The script edits the local Shared checkout; it never commits or pushes it. When Shared
is absent, standalone Tier 0 publication still works and reports skipped synchronization.
Restore the Shared checkout and rerun plan/apply to populate it; no template changes are
required. A failed catalog update retains applied state and the existing Shared file.
Correct the file/tooling and rerun plan/apply. Catalog updates do not run on `plan`,
`import`, `verify`, disk replacement, or failed publication.

CI can select another existing catalog with the exported absolute path
`TEMPLATE_SHARED_CATALOG_FILE`. An explicitly selected missing file blocks apply.
No Shared repository or catalog is created implicitly. For independently built or transferred
images, add the same reference fields manually after testing; consumer selection is unchanged.

Use the [publisher's OS-family choices](template-publication.md#os-families-and-windows)
consistently. Tier 0's publication catalog separately records `distribution`;
consumer titles/tags retain that specificity.
Existing consumer entries using `family: alma` or `rocky` remain accepted; changing
metadata does not approve a different image or change its VMID.

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

1. Shared `config/platform.tfvars` for common platform references.
2. Shared `templates/proxmox-catalog.tfvars`.
3. Tier `terraform/common.tfvars`, then its optional environment overlay.
4. Setup `terraform.tfvars`, then its optional environment overlay.
5. Explicit inventory and ordered group-var paths.

Terraform's later `-var-file` arguments take precedence. Maps are replaced, not
deep-merged; select an ID locally instead of maintaining another full catalog. [1]
For manual Terraform commands, include both shared files before tier overrides; see the
[manual equivalent](repository-scripts.md#manual-equivalent).

Keep `default_linux_vm_template_id` on a clone-tested Linux cloud-init image.

The Linux tier roots pass catalog data to their tier-local typed resolver. The resolver
uses the actual clone ID for title, source node and boot hardware, and adds image
tags to that guest's workload tags. Tier 0 builders may use `template_catalog_id`
for output-image tags; that never changes the clone's source node or hardware profile.

BIOS, machine, SCSI controller and EFI enrollment belong to the template reference.
Do not repeat them in every service deployment. The selected entry's `bios`, `machine`,
`scsi_hardware` and `efi_pre_enrolled_keys` supply the VM's creation `firmware` profile.
An explicit per-VM `firmware` block replaces that complete creation profile for an intentional exception;
its omitted members use the VM schema's defaults, rather than merging individual template fields.
Existing and imported Linux VMs preserve BIOS, machine, SCSI controller, EFI disk and boot order.
Changing a catalog entry or a `firmware` override does not retrofit those settings. Plan a separate
boot-hardware migration or replacement when required. CPU, RAM, disk configuration and networking
remain deployment-managed; this preservation does not ignore the VM or its disk blocks as a whole. [2]
Disk I/O-thread defaults still follow the configured controller profile and remain managed disk
options; review those separately from the preserved boot fields.

Keep reusable clone sources **TPM-free**. Each new service VM selects its own `.tpm` object;
`tpm = {}` creates TPM 2.0 on its VM-image datastore. The source catalog must explicitly report
`tpm_state_present = false`. The module rejects a known populated source TPM even when no fresh TPM
is requested, because the provider can otherwise copy its identity. Absence of that field is not
proof of an empty TPM. The publisher records applied state, not a live inspection on every clone;
do not change or repoint an approved source after publication. Existing guest TPM state remains
preserved during routine reconciliation. Use [TPM maintenance](../05-operations/01-hosting/proxmox-guest-security.md)
for an existing VM's additive change.

Tier 0's separate Talos command reads the same catalog but uses its own root
and inputs, without Linux common variables or Ansible configuration.

No consumer reads Tier 0 state or its private publication configuration.
The publisher remains independently recoverable, while consumers need only
their own checkout/inputs and a reviewed shared revision. Protect shared code
and catalog changes at the privilege level of their consumers.

## Existing collections

Refresh shared and all affected tiers together. New collections use only the
shared catalog; refresh preserves existing shared catalogs, root READMEs and local tier inputs.
Deleting a generated catalog or README resets it to its current starter on refresh;
private tier inputs and state are not generated or recovered by that command.

Move common entries from tier-local `linux_vm_template_catalog` maps into shared
`proxmox_template_catalog`, changing `description` to `title` and recording
`family`. Keep existing IDs and image tags during migration. Then remove the
duplicated maps deliberately, leaving only intentional per-tier ID selections.

The legacy variable still overrides tags/source-node metadata for matching IDs;
boot hardware comes from the Shared catalog. An old entry can therefore hide a shared
source-node setting until migrated.
If no shared catalog exists, the helper warns and uses the legacy inputs.
An empty starter does not select an image automatically. Review a no-change
plan before deployment; adding clone-source metadata can affect existing
resources, so do not apply unexpected replacements. State paths do not move.

After updating older automation, rerun the template publication `apply` with the original
catalog/state to synchronize its boot-hardware output into Shared. Review the plan first;
a metadata-only update does not require recreating templates. For independently maintained
templates, record the observed settings once in their Shared entry instead. Entries without
any boot-hardware fields retain the legacy provider-default behavior for creation; partial profiles
fail with an actionable error. Updated VM modules preserve imported boot settings even when the
selected profile differs or is absent. Record the actual source for future recreation; backfilling
Shared metadata is not a prerequisite for adopting an existing guest with a wholly absent profile.

New starter VM inputs select `tpm = {}`. Before provisioning them from older catalog entries,
republish the original TPM-free template to populate `tpm_state_present = false`. For a separately
maintained template, inspect its actual Proxmox hardware and record the boolean only after confirming
no TPM is attached. Do not delete a populated TPM to satisfy the check: publish a qualified TPM-free
source instead. Synchronizing legacy publisher outputs without this evidence removes a stale TPM
claim; it cannot silently authorize a fresh TPM selection.

## References

1. [Terraform variable precedence](https://developer.hashicorp.com/terraform/language/values/variables),
   checked 2026-09-22.
2. [Terraform creation/update semantics of ignored attributes](https://developer.hashicorp.com/terraform/language/meta-arguments/lifecycle#ignore_changes),
   checked 2026-11-14.
