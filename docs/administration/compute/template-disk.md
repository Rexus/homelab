# Replace a template boot disk

Replace `scsi0` from the approved published image while keeping the template's
VMID, name, EFI disk, network and CloudInit settings. The previous boot volume
is retained as an unused disk for rollback. This is explicit maintenance;
normal Terraform adoption/apply does not re-import an existing boot disk. [1][2]

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Code:** [maintenance play](../../../tier-0/ansible/playbooks/maintenance/template-disk.yml),
[native disk recipe](../../../tier-0/ansible/roles/proxmox_template_disk/tasks/replace.yml),
[applied artifact references](../../../tier-0/terraform/modules/proxmox_templates/outputs.tf).
**Prerequisites:** accepted bootstrap tooling and CA trust, Ansible 2.17+ with
Tier 0's `ansible/requirements.yml` and `ansible/requirements.txt`, `qemu-img`
(`qemu-utils` on Debian/Ubuntu), and a stopped, unlocked template.
The API modules use the Linux execution host's CA bundle. For a deliberately
separate approved trust file, set `PROXMOX_CA_FILE` to its absolute path in
`.env.local`; verification remains enabled.

## Contents

- [Step 1: Prepare publication and recovery](#step-1-prepare-publication-and-recovery)
- [Step 2: Preview the disk replacement](#step-2-preview-the-disk-replacement)
- [Step 3: Execute and qualify](#step-3-execute-and-qualify)
- [Recovery and linked clones](#recovery-and-linked-clones)
- [Command reference](#command-reference)
- [References](#references)

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

The scoped API identity needs the existing VM/disk and target-storage permissions.
No Proxmox host shell, root API identity or disabled TLS verification is required.
The [API setup](../../deployment/foundation/proxmox/api-access.md#4-grant-storage-permissions-to-the-group)
distinguishes image staging from live disk storage.

## Step 2: Preview the disk replacement

From the Tier 0 repository root, select the key in `templates/proxmox.yml`:

```bash
read -r -p "Template catalog key: " TEMPLATE_KEY
bash scripts/proxmox-templates.sh replace-disk --template "$TEMPLATE_KEY" --env-file .env.local
```

The preview verifies the local artifact hash/virtual size and reads the current
template. It shows VMID/name, current boot volume, approved source volume/hash
and target capacity. It changes neither Proxmox nor Terraform state.

The implementation uses the native `community.proxmox.proxmox_disk` operation.
Its `create: forced` imports a new volume and retains the old one as unused.
Proxmox converts newly imported disks to base images for template VMs. [2][3]

## Step 3: Execute and qualify

Copy the reviewed **old boot volume** and **approved SHA256** from the preview.
Use the same template key:

```bash
read -r -p "Reviewed old boot volume: " OLD_BOOT_VOLUME
read -r -p "Reviewed approved image SHA256: " IMAGE_SHA256
bash scripts/proxmox-templates.sh replace-disk --template "$TEMPLATE_KEY" --env-file .env.local \
  --execute --expected-disk "$OLD_BOOT_VOLUME" --expected-sha256 "$IMAGE_SHA256"
```

Execution checks the current disk and published image against those exact
values before writing. It records recovery references under
`.terraform/maintenance/template-disk/`, replaces only `scsi0`, and expands the
new disk to the selected capacity. The old volume remains attached as unused;
there is no automatic deletion of old volumes or whole-VM recreation.

After successful verification, the wrapper runs Terraform **refresh-only** to
record the new volume identity. That step updates state, not VM configuration.
Any saved normal publication plan is invalidated before execution. [4]

Run a normal template `plan` again, review it, then clone-test boot, DHCP/static
networking, agent and console behavior before resuming template consumption.
Keep the old volume and independent backup until rollback and linked-clone
requirements have been satisfied. Nothing here upgrades existing cloned VMs.

## Recovery and linked clones

If execution fails or times out, inspect the live template and both receipt
files before doing anything else. An import may have completed despite a
client timeout. Never blindly retry; the old-volume check blocks replay once
the active disk has changed.

For rollback, stop clone creation and keep the template stopped. In Proxmox
Hardware, detach the new `scsi0` **without deleting its volume**, then reattach
the recorded old unused volume as `scsi0`. Restore its recorded disk options
and confirm the existing boot order. Retain both volumes until verified.
Refresh/review Terraform state afterwards; do not run a normal apply merely
to force the disk back. The receipt records volume references, not a disk backup.

Linked clones continue to depend on their original base volume. Keeping VMID
alone is insufficient. Retain that old volume and its storage until every
dependent clone has been retired or independently migrated. [3][5]

## Command reference

| Option | Purpose |
| --- | --- |
| `replace-disk --template KEY` | Read-only preview for one applied catalog entry |
| `--env-file .env.local` | Literal local credentials; existing verified CA trust remains required |
| `--execute` | Perform the explicitly selected boot-disk operation |
| `--expected-disk VOLUME` | Match the live old boot volume; required for execution |
| `--expected-sha256 SHA` | Match the published image approval; required for execution |
| `--platform-file PATH` | Existing shared platform profile override, also used by refresh-only |

## References

1. [Pinned provider skips re-import of existing disks](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/proxmoxtf/resource/vm/disk/disk.go#L642).
2. [Native Ansible disk import, replacement and retention](https://docs.ansible.com/projects/ansible/latest/collections/community/proxmox/proxmox_disk_module.html).
3. [Proxmox disk import and template base-volume conversion](https://github.com/proxmox/qemu-server/blob/master/src/PVE/API2/Qemu.pm).
4. [Terraform refresh-only mode](https://developer.hashicorp.com/terraform/cli/commands/plan#refresh-only-mode).
5. [Proxmox full and linked clones](https://github.com/proxmox/pve-docs/blob/master/qm.adoc).

Sources checked 2026-11-06. Local API fixtures do not establish live storage or recovery acceptance.
