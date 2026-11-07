# Replace a template boot disk

Replace `scsi0` from an approved published image while keeping the template's VMID,
name, EFI, network and CloudInit settings. The old disk stays available for rollback.
The same workflow applies to every image in `templates/proxmox.yml`, including Linux
and Talos templates; no guest login is required.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Code:** [maintenance play](../../../tier-0/ansible/playbooks/maintenance/template-disk.yml)
and [disk replacement role](../../../tier-0/ansible/roles/proxmox_template_disk/tasks/replace.yml).

## Contents

- [Prerequisites](#prerequisites)
- [Step 1: Select the template](#step-1-select-the-template)
- [Step 2: Preview and confirm](#step-2-preview-and-confirm)
- [Step 3: Verify and clone-test](#step-3-verify-and-clone-test)
- [Rollback if the clone does not work](#rollback-if-the-clone-does-not-work)
- [Retire the old disk](#retire-the-old-disk)
- [Other options](#other-options)
- [References](#references)

## Prerequisites

- Complete [template publication/adoption](template-lifecycle.md#local-workflow),
  including its normal apply. Keep the approved local image at its recorded path.
- Use the prepared bootstrap host, `.env.local` and
  [trusted API access](../../deployment/foundation/proxmox/api-access.md).
  The publishing token also needs `VM.Allocate` on the template for base conversion. [1]
- Keep the template stopped and unlocked. Back up its disks and original Terraform
  state, and pause clone creation and other template/state writers during maintenance.

Install the image utility on the **deployment host**, using the block matching its
package manager. This choice is independent of the template's operating system.

**DNF-based host:**

```bash
sudo dnf install -y python3 python3-pip /usr/bin/qemu-img
```

**APT-based host:**

```bash
sudo apt-get install -y python3-venv python3-pip qemu-utils
```

Prepare or reuse the deployment user's **Python environment**, from the Tier 0 root:

```bash
python3 -m venv "$HOME/.local/share/homelab/venv"
source "$HOME/.local/share/homelab/venv/bin/activate"
python3 -m pip install --upgrade 'ansible-core>=2.17' -r ansible/requirements.txt
ansible-galaxy collection install 'community.proxmox:>=2.1.0,<3.0.0' --force
```

Activate that environment in each new shell. For other hosts or offline installation,
see [local tooling](../../development/local-setup.md#ansible-environment).
The wrapper checks tools and modules before starting maintenance. [2]

## Step 1: Select the template

In `templates/proxmox.yml`, select the **key under `templates:`**, not its VMID.
Examples include `debian-build-1`, `rocky-build-1` and `talos-build-1`.
Confirm the published image is the intended replacement and its configured capacity
fits the image. The replacement uses those applied catalog values; it does not shrink
or overwrite the old volume.

## Step 2: Preview and confirm

<a id="step-2-preview-the-disk-replacement"></a>
<a id="step-3-execute-and-qualify"></a>

Run from the **Tier 0 root**:

```bash
read -r -p "Template catalog key (example: debian-build-1): " TEMPLATE_KEY
bash scripts/proxmox-templates.sh replace-disk --template "$TEMPLATE_KEY" --env-file .env.local
```

Ansible checks the image and template, then displays the old disk, approved source
and target capacity. Review them and type **yes** to replace; **no** or Enter stops.
The play imports the new disk, retains the old disk as unused and converts the new
`scsi0` to a template base volume. Other VM settings remain unchanged. [1][3]

## Step 3: Verify and clone-test

<a id="step-4-verify-the-replacement"></a>

Require **`verification: passed`**, `retained_old_disk: true` and
`base_conversion: completed`. The output identifies the new boot volume and recovery
receipts under `.terraform/maintenance/template-disk/`.
The wrapper then refreshes Terraform state; an **Objects have changed outside of
Terraform** notice during that refresh is expected. [4]

1. Check the template's **Hardware** view: `scsi0` matches the printed new volume,
   and the recorded old volume is an unused disk.
2. Create a disposable full clone. Test boot, networking, console and the guest agent
   where the selected image supports it.
3. Review a fresh plan before resuming template consumption:

```bash
bash scripts/proxmox-templates.sh plan --env-file .env.local
```

A successful disk check does not prove the guest boots. Existing cloned VMs are unchanged.
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

Keep the old volume until clone tests and recovery copies are accepted. **Linked
clones may still depend on that exact base volume**, even after the template uses
a new boot disk. Retain it until those dependencies are removed. [5]

Cleanup is manual: remove only the unused disk matching the recorded old volume,
after confirming it has no dependent clones. The play never deletes it automatically.
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

<details>
<summary>Complete base conversion after an older replacement recipe</summary>

If an older recipe replaced the disk but left `scsi0` as `vm-*`, complete conversion
on the Proxmox host holding the stopped template, without importing another disk: [1]

```bash
read -r -p "Stopped template VMID (example: 110): " TEMPLATE_VMID
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
