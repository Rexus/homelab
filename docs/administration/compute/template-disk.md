# Replace a template boot disk

Replace `scsi0` from the approved published image while keeping the template's
VMID, name, EFI disk, network and CloudInit settings. The previous boot volume
is retained as an unused disk for rollback. This is explicit maintenance;
normal Terraform adoption/apply does not re-import an existing boot disk. [1][2]

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Code:** [maintenance play](../../../tier-0/ansible/playbooks/maintenance/template-disk.yml),
[native disk recipe](../../../tier-0/ansible/roles/proxmox_template_disk/tasks/replace.yml),
[applied artifact references](../../../tier-0/terraform/modules/proxmox_templates/outputs.tf).
**Prerequisites:** [bootstrap tooling](../../development/local-setup.md), accepted CA trust,
the [maintenance dependencies](#prerequisites), and a stopped, unlocked template.
The API modules use the Linux execution host's CA bundle. For a deliberately
separate approved trust file, set `PROXMOX_CA_FILE` to its absolute path in
`.env.local`; verification remains enabled.

## Contents

- [Prerequisites](#prerequisites)
- [Step 1: Prepare publication and recovery](#step-1-prepare-publication-and-recovery)
- [Step 2: Preview and confirm](#step-2-preview-and-confirm)
- [Step 3: Verify and clone-test](#step-3-verify-and-clone-test)
- [Disk names and an already-imported disk](#disk-names-and-an-already-imported-disk)
- [Rollback if the clone does not work](#rollback-if-the-clone-does-not-work)
- [Retire the old disk](#retire-the-old-disk)
- [Unattended execution](#unattended-execution)
- [Command reference](#command-reference)
- [References](#references)

## Prerequisites

Run this complete block from **Tier 0** on the AlmaLinux/Rocky Linux bootstrap
host, as the deployment user. It installs the OS image utility, prepares an isolated
Ansible runtime and installs maintenance dependencies. An existing accepted virtual
environment is also valid; see [runtime setup](../../development/local-setup.md#ansible-environment).
`community.proxmox` requires `ansible-core >=2.17`; OS-provided 2.16 is insufficient. [7]

```bash
sudo dnf install -y /usr/bin/qemu-img
python3 -m venv "$HOME/.local/share/homelab/venv"
source "$HOME/.local/share/homelab/venv/bin/activate"
python3 -m pip install --upgrade 'ansible-core>=2.17' -r ansible/requirements.txt
ansible-galaxy collection install 'community.proxmox:>=2.1.0,<3.0.0' --force
ansible-playbook --version
qemu-img --version
```

DNF selects the package providing `/usr/bin/qemu-img`, avoiding assumptions about
its package name in the approved repository. [8] On Debian/Ubuntu, replace the
first line with `sudo apt-get install -y qemu-utils python3-venv`.
Activate the same environment in each new deployment shell. `qemu-img` is an OS
utility; pip and Galaxy do not install it.

The collection supplies both `proxmox_vm_info` and `proxmox_disk`. [2][6] Installing it
as another user or into another Ansible search path does not make it available
to the current wrapper. If resolution still fails, inspect
`ansible-galaxy collection list community.proxmox` and `ansible-doc --version`.
The wrapper verifies tools and both modules before initializing Terraform. It uses
the tier's Ansible configuration and treats collection/runtime incompatibility as
an error; `ansible-doc`'s exit status alone is insufficient. A prerequisite failure
does not change any template disk.
Offline hosts must use approved pre-staged collection archives and Python wheels.

## Step 1: Prepare publication and recovery

Complete [template publication/adoption](template-lifecycle.md#local-workflow)
with the current code first. Apply the reviewed normal plan so the selected
template and approved uploaded image exist in the original Terraform state.
The maintenance recipe reads these references from Terraform outputs; it does
not maintain another inventory or infer ownership from VMID alone.

Set `all.disk_size_gb` to the base capacity, normally 10 GiB when the source
image fits. Explicit older values such as 32 still override that default.
This operation imports new bytes into a new volume; it does not shrink the old
disk. Verify vendor provenance and the uploaded image's SHA256 independently.
Retain the exact approved local artifact at its published `image_path`.

Back up the template and original state independently. Stop clone creation,
template updates and other state writers during maintenance. Identify linked
clones before proceeding; their old base volume must remain available.
The existing [mutable refresh](template-lifecycle.md#mutable-linux-refresh)
same-ID path replaces the whole template and is a different operation.

The scoped API identity needs the existing VM/disk and target-storage permissions,
including `VM.Allocate` on the selected VM for single-disk base conversion. [3]
No Proxmox host shell, root API identity or disabled TLS verification is required.
The [API setup](../../deployment/foundation/proxmox/api-access.md#4-grant-storage-permissions-to-the-group)
distinguishes image staging from live disk storage.

<a id="step-2-preview-the-disk-replacement"></a>
<a id="step-3-execute-and-qualify"></a>

## Step 2: Preview and confirm

From the Tier 0 repository root, select the **map key under `templates:`** in
`templates/proxmox.yml`. For the starter's Rocky image, the key is `rocky-build-1`;
its VMID is a separate value. The prompt includes an example of the expected input:

```bash
read -r -p "Template catalog key (example: rocky-build-1): " TEMPLATE_KEY
bash scripts/proxmox-templates.sh replace-disk --template "$TEMPLATE_KEY" --env-file .env.local
```

The preview verifies the local artifact hash/virtual size and reads the current
template. It shows VMID/name, current boot volume, approved source volume/hash
and target capacity. Ansible then asks **Type yes to execute; no or Enter ends without changes**.
Only an explicit `yes` continues; every other response leaves the disks unchanged.
There is no need to copy the volume and hash into a second execution command. [9]

The implementation uses the native `community.proxmox.proxmox_disk` operation.
Its `create: forced` imports a new volume and retains the old one as unused. After
approval, the recipe rechecks the live template against the preview and stops if
it changed. It then records recovery references under `.terraform/maintenance/template-disk/`,
replaces `scsi0`, resizes it, and requests Proxmox's **single-disk base conversion**.
The conversion targets only `scsi0`; EFI, NICs and CloudInit are preserved. [2][3]

After successful verification, the wrapper runs Terraform **refresh-only** to
record the new volume identity. That step updates state, not VM configuration.
Any saved normal publication plan is invalidated before execution. [4]

<a id="step-4-verify-the-replacement"></a>

## Step 3: Verify and clone-test

Successful execution prints **verification: passed**, the old/new boot volumes,
the new disk's live options/capacity and the recovery receipt paths. The checks
require a different `scsi0` volume, the old volume retained as unused, and all
other VM settings unchanged. A declined operation or explicit `--preview` run
has not performed a replacement. The wrapper refreshes Terraform state only after
successful execution, including an interactive `yes`.

From Tier 0, read back the live template and review the normal Terraform plan:

```bash
read -r -p "Template catalog key (example: rocky-build-1): " TEMPLATE_KEY
bash scripts/proxmox-templates.sh replace-disk --template "$TEMPLATE_KEY" --env-file .env.local --preview
bash scripts/proxmox-templates.sh plan --env-file .env.local
```

The first command is read-only. Its `old_boot_volume` now means the **current**
boot volume: it should match the new volume printed after execution. The original
volume remains in the receipts/Proxmox unused disks. Neither command repeats the import.
Terraform's **Objects have changed outside of Terraform** notice is expected during
the refresh-only phase: Ansible changed the volume, and Terraform records its new
identity. It is not another disk import or a request to delete the rollback volume.
Disk maintenance preserves memory settings; its preview reports whether live
ballooning is disabled. For adopted templates, follow the
[fixed-RAM check](template-lifecycle.md#verify-fixed-ram-after-adoption), even if Terraform reports no changes.

Create a disposable full clone and test boot, DHCP/static networking, agent and
console behavior before resuming template consumption. Configuration/volume checks
do not prove the guest boots or compare the converted disk byte-for-byte with its source.
Keep the old volume and independent backup until rollback and linked-clone
requirements have been satisfied. Nothing here upgrades existing cloned VMs.

## Disk names and an already-imported disk

Proxmox owns backing-volume names. On the reference ZFS storage, a replacement
can pass through these states; storage plugins may use different native names:

| Role | Example | Treatment |
| --- | --- | --- |
| Old boot disk | `base-110-disk-1` | Retained under its original ID as the rollback volume |
| Imported replacement | `vm-110-disk-2` | Converted by Proxmox after import/resize |
| Final template boot disk | `base-110-disk-2` | Attached as `scsi0` |
| CloudInit drive | `vm-*` | Per-clone configuration media; not a shared boot base |

The disk number is an allocation identifier, not the `scsi0` slot number. Retaining
the old volume means the new one receives a different allocation. Do not rename
the old base or reuse its name: linked clones may reference that exact backing volume. [3][5]

For a disk already replaced by an older recipe and still named `vm-*`, complete
the native conversion **without importing another disk**. On the Proxmox host
holding that stopped template:

```bash
read -r -p "Stopped template VMID (example: 110): " TEMPLATE_VMID
qm template "$TEMPLATE_VMID" --disk scsi0
qm config "$TEMPLATE_VMID" --current 1 | grep -E '^(scsi0|ide2|unused[0-9]+):'
```

Proxmox performs the conversion and updates the volume reference; do not rename
ZFS datasets or disk files manually. Review a normal Tier 0 template plan afterwards.

<a id="recovery-and-linked-clones"></a>

## Rollback if the clone does not work

> [!IMPORTANT]
> **How to roll back if the clone does not work:** retain both disks and use the
> recorded old `scsi0` from the `.before.json` receipt. Stop clone creation and keep
> the template stopped. A failed clone test is not a reason to repeat the import.

If execution fails or times out, inspect the live template and both receipt
files before doing anything else. An import may have completed despite a
client timeout. Never blindly retry; the old-volume check blocks replay once
the active disk has changed.

1. Read the `.before.json` and `.after.json` receipts printed by the run. Match
   their old/new volume IDs to the template's **Hardware** view.
2. Detach the new `scsi0` **without deleting its volume**. It must remain available
   as an unused disk while the original is restored.
3. Reattach the recorded old unused volume as **SCSI / scsi0**, restoring the
   recorded disk options. Confirm the existing boot order still selects `scsi0`;
   leave EFI and CloudInit unchanged.
4. Boot a disposable full clone to qualify the restored image. Review a normal
   Tier 0 template plan afterwards; do not force replacement or disk deletion to
   reconcile state. Retain both volumes until recovery has been accepted.

The receipts identify volumes and options; they are not independent disk backups.

## Retire the old disk

Linked clones continue to depend on their original base volume. Keeping VMID
alone is insufficient. Retain that old volume and its storage until every
dependent clone has been retired or independently migrated. [3][5]
After the replacement's clone tests and recovery copies are accepted, remove only
the **unused disk matching the recorded old volume** through Proxmox Hardware.
Confirm that no linked clone still depends on it. Cleanup is a separate acceptance
decision; successful import alone does not authorize deleting the rollback disk.

## Unattended execution

For CI or another noninteractive run, obtain a `--preview` first and pass its exact
old volume and approved hash with `--execute`. The pinned values remain supported:

```bash
read -r -p "Template catalog key (example: rocky-build-1): " TEMPLATE_KEY
read -r -p "Reviewed old boot volume (example: local-zfs:base-110-disk-1): " OLD_BOOT_VOLUME
read -r -p "Reviewed approved image SHA256 (64 hex characters from preview): " IMAGE_SHA256
bash scripts/proxmox-templates.sh replace-disk --template "$TEMPLATE_KEY" --env-file .env.local \
  --execute --expected-disk "$OLD_BOOT_VOLUME" --expected-sha256 "$IMAGE_SHA256"
```

In a pipeline, supply those same values through protected job inputs instead of
interactive `read`. Blank input, EOF or `no` never authorizes an interactive write.

## Command reference

| Option | Purpose |
| --- | --- |
| `replace-disk --template KEY` | Preview and request one interactive execution decision |
| `--preview` | Read-only inspection, with no execution prompt |
| `--env-file .env.local` | Literal local credentials; existing verified CA trust remains required |
| `--execute` | Noninteractive execution; both reviewed disk/hash values are required |
| `--expected-disk VOLUME` | Match the live old boot volume; required for execution |
| `--expected-sha256 SHA` | Match the published image approval; required for execution |
| `--platform-file PATH` | Existing shared platform profile override, also used by refresh-only |

## References

1. [Pinned provider skips re-import of existing disks](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/proxmoxtf/resource/vm/disk/disk.go#L642).
2. [Native Ansible disk import, replacement and retention](https://docs.ansible.com/projects/ansible/latest/collections/community/proxmox/proxmox_disk_module.html).
3. [Proxmox disk import and template base-volume conversion](https://github.com/proxmox/qemu-server/blob/master/src/PVE/API2/Qemu.pm).
4. [Terraform refresh-only mode](https://developer.hashicorp.com/terraform/cli/commands/plan#refresh-only-mode).
5. [Proxmox full and linked clones](https://github.com/proxmox/pve-docs/blob/master/qm.adoc).
6. [Native VM information module and Python requirements](https://docs.ansible.com/projects/ansible/latest/collections/community/proxmox/proxmox_vm_info_module.html).
7. [Proxmox collection's Ansible runtime requirement](https://github.com/ansible-collections/community.proxmox/blob/2.1.0/meta/runtime.yml).
8. [DNF installation by provided file](https://dnf.readthedocs.io/en/latest/command_ref.html).
9. [Ansible pause and returned user input](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/pause_module.html).

Sources checked 2026-11-07. Local API fixtures do not establish live storage or recovery acceptance.
