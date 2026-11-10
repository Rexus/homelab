# Replace a template boot disk

Replace `scsi0` from an approved published image while keeping the template's VMID,
name, EFI, network and CloudInit settings. The old disk stays available for rollback.
The same workflow applies to every image in `templates/proxmox.yml`, including Linux
and Talos templates; no guest login is required.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Code:** [maintenance play](../../../tier-0/ansible/playbooks/maintenance/template-disk.yml)
and [disk replacement role](../../../tier-0/ansible/roles/proxmox_template_disk/tasks/replace.yml).

<a id="contents"></a>

## Find the task

| Question | Task |
| --- | --- |
| Replace only the boot disk? | [Prerequisites](#prerequisites), then [Steps 1-6](#step-1-select-the-template) |
| Replacement failed or the clone does not boot? | [Rollback](#rollback-if-the-clone-does-not-work) |
| Remove an old unused disk after acceptance? | [Dependency checks and permanent deletion](#retire-the-old-disk) |
| Run unattended or finish an older base conversion? | [Explicit options](#other-options) |

**Why:** [image approval and promotion](../../architecture/software/artifact-supply.md);
changing a template does not update existing guests.

## Prerequisites

- Complete [template publication/adoption](template-lifecycle.md#local-workflow),
  including its normal apply. Keep the approved local image at its recorded path.
- Use the prepared bootstrap host, `.env.local` and
  [trusted API access](../../deployment/foundation/proxmox/api-access.md).
  The publishing token also needs `VM.Allocate` on the template for base conversion. [1]
- Keep the template stopped and unlocked. Back up its disks and original Terraform
  state, and pause clone creation and other template/state writers during maintenance.

The command automatically prepares an isolated Python/Ansible environment and
installs missing module requirements, the Proxmox collection and `qemu-img` on the
**deployment host**. No manual environment activation is needed. Missing OS packages
require root or sudo; CI must provide noninteractive privileges or preinstalled packages.
See [runtime and offline options](../../development/local-setup.md#automatic-template-runtime). [2]

## Step 1: Select the template

In `templates/proxmox.yml`, select the **key under `templates:`**, not its VMID.
Examples include `debian-build-1`, `rocky-build-1` and `talos-build-1`.
Confirm the published image is the intended replacement and its configured capacity
fits the image. The replacement uses those applied catalog values; it does not shrink
or overwrite the old volume.

<a id="step-2-preview-and-confirm"></a>

<a id="step-2-preview-the-disk-replacement"></a>
<a id="step-3-execute-and-qualify"></a>

## Step 2: Start the interactive replacement

Run from **`<prefix>-tier-0/`** on the protected execution host.

```bash
read -r -p "Template catalog key (example: debian-build-1): " TEMPLATE_KEY
bash scripts/proxmox-templates.sh replace-disk --template "$TEMPLATE_KEY" --env-file .env.local
```

Ansible checks the image/template and pauses with the old disk, approved source and target capacity.

## Step 3: Review and confirm the disk swap

At **the Ansible prompt**, check the template identity, old volume, source image and capacity.
Type **yes** only for the intended replacement; **no** or Enter stops without importing a disk.
The play imports the new disk, retains the old disk as unused and converts the new
`scsi0` to a template base volume. Other VM settings remain unchanged. [1][3]

<a id="step-3-verify-and-clone-test"></a>

<a id="step-4-verify-the-replacement"></a>

## Step 4: Check the result and retained disk

Require **`verification: passed`**, `retained_old_disk: true` and
`base_conversion: completed`. The output identifies the new boot volume and recovery
receipts under `.terraform/maintenance/template-disk/`.
The wrapper then refreshes Terraform state; an **Objects have changed outside of
Terraform** notice during that refresh is expected. [4]

In **Proxmox > template > Hardware**, check that `scsi0` matches the printed new volume
and the recorded old volume is an unused disk. Stop on a failed check; keep both disks.

## Step 5: Test a disposable full clone

In **Proxmox**, create a disposable **full clone** from the updated template.
Test boot, networking, console and the guest agent where the selected image supports it.
A successful disk check does not prove the guest boots. Existing cloned VMs are unchanged.

## Step 6: Review the template plan

Run from **`<prefix>-tier-0/`** on the protected execution host.

```bash
bash scripts/proxmox-templates.sh plan --env-file .env.local
```

Check for unintended disk or VM changes before resuming template consumption.
This plan checks the maintained template after the swap; it does not repeat the replacement.
For read-only inspection, rerun the replacement command with `--preview`; it does not import a disk.

## Rollback if the clone does not work

<a id="recovery-and-linked-clones"></a>

> [!IMPORTANT]
> Keep both disks and the template stopped. If the run failed or timed out, inspect
> its available receipts and live Hardware view before retrying; the import may have completed.

1. Read the `.before.json` receipt for the original `old_scsi0` volume and options.
2. In Proxmox **Hardware**, detach the new `scsi0` **without deleting its volume**.
3. Reattach the recorded old unused disk as **SCSI / scsi0**, restoring its recorded
   options. Keep the boot order on `scsi0`; leave EFI and CloudInit unchanged.
4. Test a disposable full clone of the restored template, then review a fresh Tier 0
   template plan before applying further changes.

Receipts record configuration; they do not replace independent disk backups.

## Retire the old disk

An **Unused Disk N** row keeps the old volume registered with the template for
rollback; it is already detached from its disk controller. Removing that row through
Proxmox **also permanently deletes the stored disk**. The play never does this automatically. [1][6]

Existing linked clones may still read that old base disk. While such dependents
exist, it is required storage, not just history. Use
[linked-clone migration](linked-clones.md) to preserve their contents in independent
copies, or deploy replacement VMs from the new template. With no dependents, the
old disk is optional rollback storage.

For a ZFS template whose replacement still has a `vm-*` name,
[complete base conversion](#complete-base-conversion) before cleanup.

1. Test a full clone of the new image and keep an independent backup of the old
   boot disk. Confirm no linked clones depend on its old base; if uncertain, retain it. [5]
2. Keep the template stopped and pause clone creation. Open the template's
   **Hardware** tab in Proxmox.
3. Match the old volume in the `.before.json` receipt's `old_scsi0` to an
   **Unused Disk N** row. Match the full storage/volume ID, not just the row number.
   Confirm the current **Hard Disk (scsi0)** uses the replacement volume.
4. Select that **Unused Disk N** row and click **Remove**. No additional detach
   step is needed. Remove only that unused entry; keep `scsi0`, EFI and CloudInit.
5. Read the deletion confirmation, recheck the selected entry and confirm only
   when the checks above are satisfied. If Proxmox reports a dependency or storage
   error, stop and investigate; do not force deletion through the storage backend.
6. Wait for successful completion and refresh **Hardware**. The old unused row
   should be gone; the current `scsi0`, EFI and CloudInit entries must remain.
   Check the storage's **VM Disks** view for the old volume's removal, then
   [review a fresh template plan](#step-6-review-the-template-plan).

After deletion, rollback to that disk requires its independent backup; the receipt
alone cannot restore it.

Proxmox owns disk names: a new `base-…-disk-2` and retained `base-…-disk-1` are normal;
CloudInit media may remain `vm-*`. Do not rename backing files or reuse old volume IDs.

## Other options

<details>
<summary>Automation without an interactive prompt</summary>

Run `--preview` first. Supply its exact old volume and approved SHA256 as protected
job inputs, then use `--execute --expected-disk VOLUME --expected-sha256 SHA` on the
same replacement command. Both values are required and checked before execution.
For all flags, run `bash scripts/proxmox-templates.sh --help`.

</details>

<a id="complete-base-conversion"></a>

<details>
<summary>Complete base conversion after an older replacement recipe</summary>

If an older recipe replaced the disk but left `scsi0` as `vm-*`, complete conversion
on the Proxmox host holding the stopped template, without importing another disk: [1]

Run on **the selected Proxmox host as an authorized root operator**.

```bash
read -r -p "Stopped template VMID (example: 9101): " TEMPLATE_VMID
qm template "$TEMPLATE_VMID" --disk scsi0
```

Check Hardware and review a fresh Tier 0 template plan afterwards. Do not rename
storage files manually.

</details>

## References

Sources checked 2026-11-07.

1. [Proxmox disk import and template base-volume conversion](https://raw.githubusercontent.com/proxmox/qemu-server/master/src/PVE/API2/Qemu.pm).
2. [Proxmox collection's Ansible runtime requirement](https://raw.githubusercontent.com/ansible-collections/community.proxmox/2.1.0/meta/runtime.yml).
3. [Native Ansible disk import, replacement and retention](https://docs.ansible.com/projects/ansible/latest/collections/community/proxmox/proxmox_disk_module.html).
4. [Terraform refresh-only mode](https://developer.hashicorp.com/terraform/cli/commands/plan#refresh-only-mode).
5. [Proxmox full and linked clones](https://raw.githubusercontent.com/proxmox/pve-docs/master/qm.adoc).
6. [Proxmox Hardware view: unused disks and removal](https://raw.githubusercontent.com/proxmox/pve-manager/master/www/manager6/qemu/HardwareView.js).
