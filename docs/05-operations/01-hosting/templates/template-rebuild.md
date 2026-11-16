# Recreate a template with the same VMID

Remove one old template and its uploaded image, forget the old image's Terraform binding, then
publish its replacement through normal plan/apply. This also resolves `prevent_destroy` or
`The existing image filename differs from the catalog` during an intentional same-key rebuild.

**Work from:** `<prefix>-tier-0/` on bootstrap, using the original initialized publication checkout.
**Keep:** the selected entry in `templates/proxmox.yml`, its key and VMID, and the remaining state.
The Tier 0 entry removed below is **one Terraform state binding**, not the YAML configuration.

These commands use the wrapper's default local backend and working-data directory. For a custom
backend/workspace or `TEMPLATE_STATE_PATH`, use the [original state context](../terraform-state.md#inspect-the-original-state)
instead. Pause other publisher/clone jobs until the replacement is accepted.

> [!CAUTION]
> Removal deletes the selected template's disks. Confirm that no linked clones or snapshots need
> its base disks before proceeding; retain independent artifacts and required backups. Full clones
> have independent disks. Use the [dependency checks](linked-clones.md#verify-zfs-dependencies) if unsure.

## 1. Select the template and back up state

Find the key under **`templates:` in `templates/proxmox.yml`**; for example, `debian-build-1`.
Run from **Tier 0 root** and keep this shell open for Step 3:

```bash
read -r -p 'Template catalog key (example: debian-build-1): ' TEMPLATE_KEY
(
  set -e
  umask 077
  test -s .terraform/state/proxmox-templates/terraform.tfstate
  export TF_DATA_DIR="$PWD/.terraform/data/proxmox-templates"
  mkdir -p .local-archive
  terraform -chdir=terraform/deployments/templates state pull \
    > ".local-archive/templates-before-rebuild-$(date -u +%Y%m%dT%H%M%SZ).tfstate"
  terraform -chdir=terraform/deployments/templates state show \
    "module.templates.proxmox_virtual_environment_file.image[\"${TEMPLATE_KEY:?Select the catalog key first}\"]"
)
```

Require a successful backup and state inspection. The output's `node_name`, `datastore_id` and
`file_name` identify the **old Proxmox upload**. Read the selected template's `vm_id` and `name`
from the matching YAML entry. Stop on missing state, a wrong key or a different backend.

## 2. Remove the old objects from Proxmox

In **Proxmox**, match the recorded identities:

1. Select the old template, then **More > Remove**. Review the dialog and leave
   **Destroy unreferenced disks owned by guest** unchecked. Wait for a successful removal task.
2. Open **the recorded node > recorded image datastore > Import**. Remove only the old
   `file_name` printed in Step 1. Keep the prepared replacement file on bootstrap.
3. Confirm that both the old template and its uploaded image are absent. If already removed,
   verify their absence before continuing.

The imported template boot disk and uploaded Import file are separate objects.
Removing the template alone does not remove that upload. The
[retirement guide](template-lifecycle.md#how-is-a-template-removed) explains the removal options.

## 3. Forget only the old image binding

Run **only after Step 2 confirms host-side removal**, from **the same Tier 0 shell**:

```bash
(
  set -e
  export TF_DATA_DIR="$PWD/.terraform/data/proxmox-templates"
  terraform -chdir=terraform/deployments/templates state rm -lock-timeout=60s \
    "module.templates.proxmox_virtual_environment_file.image[\"${TEMPLATE_KEY:?Repeat Step 1 to select the key}\"]"
)
```

Expect **one resource removed from state**. This command changes state immediately; it does not
delete a Proxmox object. The next normal plan refreshes the deleted template's VM binding.
Other templates keep their bindings. If the image binding is already absent, continue only after
confirming Step 2 and the selected key; no additional state removal is needed.

## 4. Update the retained catalog entry

Edit **Tier 0 `templates/proxmox.yml`**, under the same `templates.<key>`:

| Field | Edit |
| --- | --- |
| `image_path` | Actual absolute path to the prepared replacement `.qcow2` or `.raw` on bootstrap |
| `sha256` | SHA256 of that prepared file |
| `release` | Exact approved source build/version |
| `image_file_name` | Remove the old override so the new upload receives its VMID/hash-based filename |

Keep the key, `vm_id`, name and other intended settings. See the
[image preparation guide](../../../03-deployment/foundation/proxmox/templates.md) for a new source.
Keep the independent artifact and verification record with the state backup.

## 5. Plan the recreation

Run from **Tier 0 root**; the wrapper loads the existing `.env.local`:

```bash
bash scripts/proxmox-templates.sh plan --env-file .env.local
```

Expect **2 to add, 0 to change, 0 to destroy** when only this image/template pair is missing.
Review the selected key, VMID, new image and hardware. Stop on changes to other resources or a
replacement/deletion. Keep the lifecycle guards enabled.

## 6. Apply and qualify a full clone

After accepting that saved plan, run from **the same Tier 0 root**:

```bash
bash scripts/proxmox-templates.sh apply --env-file .env.local
```

Require successful publication and policy verification. Create a disposable full clone and check
[boot, cloud-init, networking and guest control](../../../03-deployment/foundation/proxmox/templates.md#clone-and-guest-control-checks)
before resuming consumers. Existing full-clone VMs retain their current disks.
Return to [template operations](template-lifecycle.md) after acceptance.
