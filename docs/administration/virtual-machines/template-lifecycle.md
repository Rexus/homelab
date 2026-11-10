# Proxmox template operations

Publish approved image revisions, adopt manual templates and select tested images for
new guests. Tier 0 owns publication; Shared holds consumer references.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`). Commands below run from its root.
**Before starting:** retained original state, verified API trust/token, approved local images,
unused [template VMIDs](../../conventions/vmid-convention.md), independent backups
and no concurrent publisher or clone-maintenance operation.
**Why:** [artifact approval and promotion](../../architecture/software/artifact-supply.md).

<a id="table-of-contents"></a>

## Find the task

| Question | Task |
| --- | --- |
| Find settings and prerequisites? | [Inputs and execution host](#where-are-settings-and-prerequisites-recorded) |
| Publish a new image revision? | [Publish](#how-is-a-new-template-published) |
| Bring manually created templates under IaC? | [Adopt](#how-are-existing-templates-adopted) |
| Check fixed RAM and empty CloudInit accounts? | [Verify policy](#how-is-template-policy-verified) |
| Recover a failed upload/apply? | [Recover publication](#what-if-publication-fails) |
| Select or roll back the default image? | [Promote](#how-is-a-tested-image-promoted-or-rolled-back) |
| Replace a disk, refresh packages or remove old images? | [Image maintenance](#how-are-template-disks-and-packages-maintained) |
| Delete a retired template before a fresh installation? | [Remove a template](#how-is-a-template-removed) |
| Run the same publication in CI? | [Protected CI](#how-is-publication-run-in-ci) |
| Move old ownership or run code checks? | [Migration and maintenance references](#where-are-migration-and-maintainer-checks-documented) |

<a id="prerequisites"></a>
<a id="ownership"></a>

## Where are settings and prerequisites recorded?

| Item | Location / action |
| --- | --- |
| Execution host and dependencies | [Bootstrap host](../../deployment/foundation/bootstrap/README.md); `apply`, `verify` and `replace-disk` prepare their ignored Python runtime automatically |
| Provider access | Tier 0 `.env.local`; pass `--env-file .env.local`. No `source`, `set -a` or token concatenation |
| Public image authenticity | Verify the vendor release outside restricted custody, retain approval and hash the unpacked artifact; a supplied hash alone is not vendor authentication |
| Site/common settings and selected builds | `templates/proxmox.yml`; shared values under `all:`, per-image overrides under `templates:` |
| Field meanings and provider compatibility | [Publication inputs](../../reference/template-publication.md) |
| Exact code/state ownership | [Template catalog contract](../../reference/template-catalog.md#where-to-edit) |

For the manual GUI path and Talos image preparation, use the
[common template guide](../../deployment/foundation/proxmox/templates.md).
Talos uses fresh approved raw images; Linux package-refresh recipes do not apply to it. [9]

<a id="local-workflow"></a>
<a id="catalog-fields-and-defaults"></a>

## How is a new template published?

1. Create missing local inputs. Existing catalogs are preserved:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/proxmox-templates.sh init
   ```

2. Edit `templates/proxmox.yml` and `.env.local`. On first use, keep only the selected builds.
   For an existing publisher, retain every still-managed catalog entry until its reviewed retirement;
   deleting an entry is not promotion and its lifecycle guard can block the plan. For a
   new revision, use a new catalog key/VMID, exact release, absolute local `image_path`
   and approved unpacked `sha256`. Review storage, bridge/VLAN, firmware and capacity
   against the [field reference](../../reference/template-publication.md#inputs-and-defaults).
3. Prepare the publication plan:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/proxmox-templates.sh plan --env-file .env.local
   ```

4. Stop on an unexpected replacement, deletion or hardware change. Apply the accepted
   **saved plan**, then verify policy:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/proxmox-templates.sh apply --env-file .env.local
   bash scripts/proxmox-templates.sh verify --env-file .env.local
   ```

5. Boot disposable clones on the approved test network. Check OS boot, networking,
   guest control, provisioning and rollback. Do not boot the template itself.

**Expected:** stopped template candidates exist, policy verification passes and Shared
references are synchronized. This does not upgrade existing guests or select a new default.
Select the accepted image in [promotion](#how-is-a-tested-image-promoted-or-rolled-back).
For an SDN change, [activate the VNet and grant its scoped permissions](../../deployment/foundation/proxmox/step-1c-sdn.md)
before applying; policy verification alone does not check NICs.

<a id="adopt-existing-templates"></a>

## How are existing templates adopted?

1. Pause other writers and back up the original publication state. Confirm no other
   Terraform root owns these VMIDs/files.
2. Fill `templates/proxmox.yml` with each existing template's actual VMID, name, node,
   storage, firmware, memory and original approved artifact/hash. Preserve map keys.
3. Find the exact uploaded basename in **Node > storage > Import**. Set `image_file_name`
   to it, even when it differs from the normal hash-based name. Independently verify
   the remote file's SHA256: discovery checks identity, not remote bytes.
4. Prepare and inspect adoption:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/proxmox-templates.sh import --env-file .env.local
   ```

5. Require the intended imports and only accepted setting changes. The matching VM
   must be a stopped template. Resolve conflicts before proceeding, then run:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/proxmox-templates.sh apply --env-file .env.local
   ```

   Optional: check for drift after the accepted apply; expect no changes:

   Run from **`<prefix>-tier-0/`** on the protected execution host. Optional drift check; this creates a new saved
   plan, not another required apply.

   ```bash
   bash scripts/proxmox-templates.sh plan --env-file .env.local
   ```

**Expected:** adopted templates and passed [live policy verification](#how-is-template-policy-verified).
Import writes are part of `apply`; `import` alone does not adopt anything. Existing
uploaded bytes and boot disks are not reimaged by adoption. [6]

<a id="verify-fixed-ram-after-adoption"></a>

## How is template policy verified?

From Tier 0, check every applied template, or select one catalog key:

Run from **`<prefix>-tier-0/`** on the protected execution host.

```bash
read -r -p "Catalog key (example: rocky-build-1): " TEMPLATE_KEY
bash scripts/proxmox-templates.sh verify --template "$TEMPLATE_KEY" --env-file .env.local
```

Require `ballooning_disabled: true`, `cloud_init_accounts_cleared: true` and
`other_settings_preserved: true`. `verify` is read-only. If policy fails, review a new
`plan`, run the normal `apply`, then verify again. The native policy phase handles the
[pinned provider's memory/account behavior](../../reference/template-publication.md#state-and-execution). [17]

This checks fixed RAM and cleared CloudInit accounts only. Clone boot, disks and
networking have their own acceptance checks. An **Apply complete** line is insufficient.

<a id="interrupted-publication"></a>

## What if publication fails?

Keep the same state, catalog keys, VMIDs and artifact files. Back up state before recovery;
a failed apply can still have completed imports/resources. Never start with empty state.

Follow [publication troubleshooting](template-troubleshooting.md) to diagnose the first error,
then its [partial-publication recovery steps](template-troubleshooting.md#how-is-partial-publication-recovered)
to prepare a new adoption plan and return to publication. Review successful prior work and all
remaining changes. The wrapper discards plans after apply attempts; do not retry an older saved plan.

**Stop:** incomplete remote image bytes, uncertain resource ownership or unexplained
replacement. Do not remove lifecycle guards or delete backing disks to force progress.

<a id="updates-and-promotion"></a>

## How is a tested image promoted or rolled back?

1. Complete publication and disposable-clone acceptance. Successful apply refreshes
   Shared references while preserving its default and older entries.
2. In Shared's `templates/proxmox-catalog.tfvars`, set `default_linux_vm_template_id`
   to the tested Linux image. Keep the previous approved entry for rollback. A tier/setup
   can select another approved ID explicitly; see [consumer selection](../../reference/template-catalog.md#how-consumers-use-it).
3. Review and commit that reference change separately. Only new/reconciled consuming
   deployments select it; no running VM or Talos node is upgraded by promotion.
4. To roll back the **selection**, restore the previous approved default/override and
   review the affected tier's plan. Already-created guests need their own product recovery
   or replacement path; changing the catalog does not rewrite them.

For another Proxmox cluster, record its destination IDs under one owner. Transfer
and offline custody remain explicit operations, not routes created by this workflow.

<a id="replace-a-boot-disk"></a>
<a id="mutable-linux-refresh"></a>

## How are template disks and packages maintained?

| Task | Runbook / acceptance |
| --- | --- |
| Replace only `scsi0`, retaining the VMID and rollback disk | [Boot-disk replacement](template-disk.md) |
| Refresh a staged AlmaLinux/Rocky package image | [Linux template refresh](template-refresh.md) |
| Remove dependent linked clones before cleanup | [Linked-clone migration](linked-clones.md) |
| Retire an old disk | [Reviewed disk cleanup](template-disk.md#retire-the-old-disk); check snapshots and linked-clone origins first |
| Retire an entire published revision | [Template removal](#how-is-a-template-removed); retain backups and check consumer dependencies first |

New versioned VMIDs are the main path. Same-ID replacement is explicitly destructive
and separate; never give two Terraform roots ownership of the same template.
Retain approved artifacts independently of a live Tier 1 registry or Git service.

## How is a template removed?

**Run in:** Proxmox GUI. The template wrapper has **no `destroy` action**; both template
VMs and uploaded images have Terraform `prevent_destroy` guards. Keep those guards enabled.
This is explicit manual retirement, followed by state/reference reconciliation.

1. Stop publisher/clone jobs. Retain independent approved images/checksums and any
   required guest backups. Verify the exact template name and VMID against Tier 0's catalog.
2. Prove no linked clones or retained snapshots require its base disks. Check the
   surviving bootstrap too: a **full clone** is independent; a linked clone still needs
   its base. Use the [dependency checks](linked-clones.md#verify-zfs-dependencies).
   Keep the template until the replacement bootstrap is full-cloned if it is still needed.
3. Select that **template** in the Proxmox tree, then **More > Remove** to open the dialog.
   Check the displayed identity; do not confirm removal until Step 4 is complete. [18]
4. Leave **Destroy unreferenced disks owned by guest** unchecked unless every additional
   volume has been reviewed. It scans beyond the template's current disk references.
   **Purge from job configurations** also removes its HA/replication/backup-job entries;
   select it only for the retired identity. Recheck the identity, enter its VMID and confirm removal
   only after reviewing those options. This deletes the template and its referenced disks.
   Wait for a successful removal task. [18]
5. For a full reset, separately open **Node > image datastore > Import**, select only
   the retired catalog's uploaded image and remove it when no other operation needs it.
   This is the Proxmox upload, not the retained `.raw`/`.qcow2` source on the bootstrap disk.
6. Repeat only for reviewed retired templates. For a complete rebuild, now follow
   [deployment retirement](../provisioning.md) and [state archiving](../terraform-state.md#archive-a-retired-deployment).
   For partial retirement, remove only the deleted revision's exact VM/image
   [state bindings](../terraform-state.md#forget-a-deleted-resource), then update its catalog and
   Shared consumer references. Retain state for all surviving resources before the next publisher run.

**Expected:** retired templates are absent, retained clones still work, and approved local
artifacts remain available. If Proxmox reports a base-disk dependency, stop and resolve it;
do not force storage deletion. Until state/catalog reconciliation, publication can recreate
the removed revision.

<a id="gitlab-ci-example"></a>

## How is publication run in CI?

1. Qualify a protected Tier 0 shell runner tagged `tier0-templates`, durable state/artifact
   storage, verified API trust, scoped credentials and the same reviewed commit in both jobs.
2. Review `ci/gitlab-templates.yml.example`. Merge it into an existing `.gitlab-ci.yml`,
   or copy the starter only when no pipeline exists:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   cp -n ci/gitlab-templates.yml.example .gitlab-ci.yml
   ```

3. Set protected absolute `TEMPLATE_STATE_PATH` and `TEMPLATE_CATALOG_FILE` paths,
   local image/provider access and masked/protected credentials. Keep a writable sibling
   Shared checkout, or set an existing `TEMPLATE_SHARED_CATALOG_FILE`.
4. Validate in GitLab CI Lint. Restrict logs/artifacts to the intended project/maintainers,
   protect the publish environment and serialize the jobs. The `maintainer` artifact
   access mode requires GitLab 18.4+. [4][5]
5. Review the plan job, then approve its blocking publish job. Keep state outside
   disposable workspaces; saved plans are sensitive. Review/commit Shared changes separately.

Only the reviewed plan and provider locks belong in this example's restricted artifacts;
never upload state, private inputs or keys. Code/approval/control-plane authority follows
the [protected provisioning design](../../architecture/hosting/provisioning.md); a runner
tag or branch name alone does not establish that boundary.

**Expected:** CI runs the same saved-plan workflow. A stale plan needs replanning.
This example does not perform unattended same-ID replacement or live Talos upgrades.
Local Tier 0 execution remains the recovery path when hosted CI is unavailable.

<a id="existing-collections"></a>
<a id="offline-validation"></a>

## Where are migration and maintainer checks documented?

Refresh does not move live inputs or state. Before moving old Tier 1 template ownership
into Tier 0, stop old jobs, retain state/inputs, review privileges/network placement,
transfer the authoritative state deliberately and update both inventories, job paths
and owned setup files. Require a no-change plan before enabling the new owner.
Use the [ownership upgrade guide](../../development/generated-repositories.md#automation-ownership-upgrade).
An empty Tier 0 state is not a migration.

Maintainers run [repository tests](../../development/testing.md). Mock tests do not boot images;
operator acceptance still needs disposable-clone evidence.

## References

4. [GitLab CI YAML reference](https://docs.gitlab.com/ci/yaml/), accessed 2026-09-17.
5. [GitLab resource groups](https://docs.gitlab.com/ci/resource_groups/), accessed 2026-09-17.
6. [Terraform configuration-driven imports](https://developer.hashicorp.com/terraform/language/import), checked 2026-11-06.
9. [Talos Proxmox controller and guest-agent requirements](https://docs.siderolabs.com/talos/v1.14/platform-specific-installations/virtualized-platforms/proxmox), checked 2026-11-06.
17. [Native Proxmox VM updates and selective setting deletion](https://docs.ansible.com/projects/ansible/latest/collections/community/proxmox/proxmox_kvm_module.html), checked 2026-11-07.
18. Proxmox's [guest removal action](https://github.com/proxmox/pve-manager/blob/master/www/manager6/qemu/Config.js)
    and [disk/job removal options](https://github.com/proxmox/pve-manager/blob/master/www/manager6/window/SafeDestroyGuest.js),
    checked 2026-11-08.
