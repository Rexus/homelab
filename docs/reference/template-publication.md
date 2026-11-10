# Template publication inputs and compatibility

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
This reference owns catalog fields and pinned-provider behavior. For operator tasks,
use [template lifecycle](../administration/virtual-machines/template-lifecycle.md).
Image approval and promotion follow the [software-supply design](../architecture/software/artifact-supply.md).

## Contents

- [Inputs and defaults](#inputs-and-defaults)
- [State and execution](#state-and-execution)
- [References](#references)

## Inputs and defaults

Edit in **`<prefix>-tier-0/`**.

- `templates/proxmox.yml`: common all: values and each approved templates: build

The full build schema is [`images` in the template module's variables.tf](../../tier-0/terraform/modules/proxmox_templates/variables.tf).
[`templates/main.tf`](../../tier-0/terraform/deployments/templates/main.tf) resolves catalog fields
such as `storage_class` before passing each build to that schema.

The YAML catalog is an input file, not another IaC implementation. The resources live in
Tier 0's `terraform/modules/proxmox_templates/`; `terraform/deployments/templates/main.tf`
merges `all:` into each entry under `templates:`. A build overrides individual fields;
lists such as `tags` replace the common list rather than deep-merging it.
Set common site choices such as bridge, VLAN and storage in `all:` once. Each image
inherits them. Technical defaults stay in the implementation; add optional fields
only when the selected image or site needs a different value.

| Input | Meaning |
| --- | --- |
| `all:` | Common placement, hardware, firmware, agent and additional tags |
| `bridge` | Template NIC bridge; defaults to `vmbr0`, with a per-build override where needed |
| `vlan_id` | Common template VLAN in `all:`; starter uses example VLAN 10; set the site's value or `null` for untagged |
| `nic_firewall` / `nic_mtu` | Optional overrides; omitted values enable the NIC firewall and select MTU 1500 |
| `scsi_hardware` | Optional override; normally omitted so OS family selects Single for Alma/Rocky/Debian or non-Single for Talos |
| `qemu_agent` / `cpu_type` | Optional overrides; defaults are `true` / `x86-64-v3` |
| `memory_mb` | Fixed template RAM; defaults to 2048 MiB with ballooning disabled for every OS; actual service sizing is applied to clones |
| `disk_size_gb` | Template capacity; defaults to 10 GiB, never below the source image's virtual size; cloned service disks are sized separately |
| `storage_class` | Class in Shared `config/platform.tfvars`, selecting its `vm_disk` datastore |
| `datastore_id` | Explicit live disk/EFI storage override; wins over `storage_class` |
| `image_datastore_id` | Tier 0 staging datastore with Import content; independent of live storage |
| `cloud_init_drive` / `cloud_init_datastore_id` | NoCloud media at `ide2` with IPv4 DHCP / override of class `cloud_init_drive` or live disk storage |
| `family` / `distribution` | OS family (`redhat`, `debian`, `talos`) / selected distribution (`alma`, `rocky`, etc.); Fedora uses the `redhat` family |
| `tags` | Extra image/variant tags, such as `[test]`; standard [image tags](../conventions/proxmox-conventions.md#template-tags) are generated automatically |
| `image_path` / `sha256` | Absolute local unpacked artifact path / approved hash of those bytes |
| `image_file_name` | Optional existing Import basename; defaults to `<vm_id>-<sha256>.raw` or `.qcow2` |
| `release` / `schematic_id` | Exact build version, optional `v` prefix / mandatory Talos Factory schematic |

Each build includes `tags: []` for optional extras such as `[test]`. Standard tags
describe the image and CPU profile, not template status or tier ownership. The
`template_candidates` output includes the resolved tags for consumer-catalog review.
Existing local `tags` remain explicit extras: remove old `template`, `tier-0`, `x86_64` or
redundant distribution-version entries there to adopt the current convention.
Successful apply refreshes image tags in Shared's catalog. Existing clones change only
through their consuming tier's reviewed deployment; synchronization does not apply those plans.

`release` records the approved version/build, not the template name or image filename.
For example, `10.0-20250601` and `v1.14.0` illustrate the accepted format; use the
actual artifact's version. Replace all `REPLACE_WITH_*` values; `latest`/`stable` aliases
are rejected. `vm_id` must be an integer of at least 100 and match the existing VMID
when adopting. Validation errors identify the catalog key, field and rejected value.

The script loads the sibling Shared platform profile if present. Use `--platform-file PATH`
or `TEMPLATE_PLATFORM_FILE` for another profile; catalog `datastore_id` and `node_name`
override shared references. A missing storage class fails validation rather than falling
back silently. Shared owns no template resources, image staging inventory or state.

Existing flat catalogs remain valid; `all:` is optional. Legacy `family: alma`/`rocky`
is accepted. Preserve existing hardware/firmware and explicit `qemu_agent: false` where
required; the new default is true. Changing a revision's inputs can cause drift even
when its VMID is unchanged. Review before applying, never force replacement to fix adoption.
For existing templates, set `bridge` and `memory_mb` to their actual values before
adoption or refresh; omitted memory now defaults to 2048 MiB rather than 4096 MiB.
Omitted NIC settings now use firewall enabled and MTU 1500. Explicit settings still
win. An existing `all.scsi_hardware` overrides automatic selection for every image;
remove it after review to use the OS profiles, or retain an explicit exception.
Fresh examples include DHCP CloudInit media, matching the GUI guide; existing catalogs
without `cloud_init_drive` keep the no-media behavior. All addresses/accounts stay clone-local.
The publisher leaves the optional CloudInit format to Proxmox/provider state:
Linux defaults to NoCloud, and an existing explicit format is retained. Forcing
`nocloud` onto an imported template whose format was implicit can make the pinned
provider propose replacement, despite equivalent Linux behavior. [7][8]

The x86 publication path also leaves CPU architecture implicit. `cpu_type` still
selects the configured CPU model and its tag; an explicit architecture assignment
would request a root-restricted Proxmox operation that API tokens cannot perform. [3]

Ten GiB is a base-image starting capacity, not the recommended disk size for every
service. Check the verified image's virtual size before importing; increase the
template setting when the image requires it. Existing larger disks are not shrunk
by changing this default. Production clones receive their own role-specific disk sizing.
DHCP remains enabled on reusable templates; a clone's explicit network configuration
replaces it. No site-specific account/password is stored in the template. [11]

Discard remains enabled so supported guest filesystems can return unused blocks to
thin-provisioned storage. On adoption, `discard = "ignore" -> "on"` is intentional:
it enables guest TRIM passthrough, not boot-disk replacement or capacity reduction.
Guest-side TRIM still needs to run. The socket-backed serial
port remains available for console diagnostics; visible output depends on the image's
serial-console configuration. The graphical display is retained. [10][11]

## State and execution

| Contract | Value / behavior |
| --- | --- |
| Publication state | `.terraform/state/proxmox-templates/terraform.tfstate`; retain it independently |
| Alternate state | Absolute `TEMPLATE_STATE_PATH`, unchanged between planning, apply and recovery |
| Alternate catalog | Absolute `TEMPLATE_CATALOG_FILE` |
| Platform profile | Sibling Shared `config/platform.tfvars`; override with `--platform-file PATH` or `TEMPLATE_PLATFORM_FILE` |
| Runtime | `apply`, `verify`, `replace-disk` prepare ignored `.venv/`; [setup contract](../development/local-setup.md#automatic-template-runtime) |
| Local credentials | `--env-file .env.local` parses literal assignments; no shell sourcing |
| CI credentials | Export native provider names or supported aliases; conflicting values fail closed |
| Apply | Saved Terraform plan, native fixed-RAM/account policy, live verification, original-state refresh, then Shared reference synchronization |
| Verify | Read-only fixed RAM and empty CloudInit accounts; not disk/NIC/guest acceptance |

The native policy phase writes explicit `balloon: 0` and clears `ciuser`, `cipassword`
and `sshkeys`, preserving CloudInit media and networking. The pinned provider can report
an absent balloon field as floating memory zero while Proxmox still enables the device;
Terraform plan alone does not establish the live policy. [8][16][17]
Template accounts inside a previously booted image are a separate cleanup obligation.
Direct `terraform apply` omits the compatibility phase; the operator workflow uses the wrapper.

## References

3. [Proxmox provider authentication](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/index.md), accessed 2026-09-17.
7. [Proxmox CloudInit format selection](https://raw.githubusercontent.com/proxmox/qemu-server/master/src/PVE/QemuServer/Cloudinit.pm), checked 2026-11-06.
8. [Pinned provider CloudInit and memory import refresh](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/proxmoxtf/resource/vm/vm.go), checked 2026-11-07.
10. [Proxmox disk discard support](https://github.com/proxmox/pve-docs/blob/master/qm.adoc#qm_hard_disk_discard), checked 2026-11-06.
11. [Proxmox CloudInit networking and serial consoles](https://github.com/proxmox/pve-docs/blob/master/qm-cloud-init.adoc), checked 2026-11-06.
16. [Proxmox enables ballooning unless explicitly disabled](https://github.com/proxmox/qemu-server/blob/master/src/PVE/QemuServer.pm#L3325), checked 2026-11-07.
17. [Native Proxmox VM updates and selective setting deletion](https://docs.ansible.com/projects/ansible/latest/collections/community/proxmox/proxmox_kvm_module.html), checked 2026-11-07.
