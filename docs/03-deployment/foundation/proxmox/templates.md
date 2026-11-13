# Proxmox VM template guide

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** Proxmox VE 9+, approved image sources, unused template VMIDs,
an image datastore with **Import** content, and live VM storage on the eligible hosts.
For the first manual Linux image, use the independent workstation and Proxmox GUI;
the generated repositories and API publisher are not prerequisites for this guide.

One GUI disk-import workflow covers AlmaLinux, Rocky Linux and Talos. Choose the
image below, then follow the numbered actions. Talos-specific differences are explicit;
there is no separate ISO installation. For repeatable API publication instead,
use the [template lifecycle](../../../05-operations/01-hosting/templates/template-lifecycle.md).
On the Foundation path, create the first Linux template here and adopt it after bootstrap preparation.
Standalone manual ownership is also valid; use the
[lifecycle reference](../../../05-operations/01-hosting/templates/template-lifecycle.md#adopt-existing-templates)
for later adoption or maintenance.
Never let two Terraform states manage the same VMID or image file.

## Contents

- [Step 1: Select the image](#step-1-select-the-image)
- [Step 2: Verify the download](#step-2-verify-the-download)
- [Step 3: Unpack and hash the image](#step-3-unpack-and-hash-the-image)
- [Step 4: Upload the prepared file](#step-4-upload-the-prepared-file)
- [Step 5: Create the VM and import its disk](#step-5-create-the-vm-and-import-its-disk)
- [Step 6: Add initialization media and boot order](#step-6-add-initialization-media-and-boot-order)
- [Step 7: Convert and create a disposable clone](#step-7-convert-and-create-a-disposable-clone)
- [Step 8: Configure and qualify the clone](#step-8-configure-and-qualify-the-clone)
- [Clone and guest-control checks](#clone-and-guest-control-checks)
- [Cluster handoff](#cluster-handoff)
- [References](#references)

<a id="select-the-image"></a>

## Step 1: Select the image

| Image | Download | Important selection |
| --- | --- | --- |
| AlmaLinux | Official [Generic Cloud](https://wiki.almalinux.org/cloud/Generic-cloud.html), x86_64 `.qcow2` | Review EL10's CPU baseline; use the explicitly selected x86_64_v2 variant only for older compatible hosts |
| Rocky Linux | Official [GenericCloud Base or LVM](https://download.rockylinux.org/pub/rocky/10/images/x86_64/), x86_64 `.qcow2` | Select the guest disk layout; EL10 needs x86-64-v3-capable hosts [6] |
| Talos | [Image Factory](https://factory.talos.dev/) disk image, not ISO | Follow the selections below; retain version and schematic ID |

Base and LVM are valid Rocky GenericCloud variants. LVM describes storage inside
the guest; Proxmox clone support is determined by host storage and template disk
conversion. Expanding a virtual disk still requires the guest's partition, volume
and filesystem layers to consume the additional space. Verify the selected image's
first-boot resize behavior on a disposable clone.

<a id="talos-version-contract"></a>

### Select the Talos version before downloading

The complete Tier 0 reference path through **Stage 5 Kubernetes SSO** uses an approved exact
**Talos 1.13.x** release and matching `talosctl`. Record that patch release and Factory schematic
before downloading. Keep these selections together:

| Input | Reference selection |
| --- | --- |
| Image Factory and Tier 0 `templates/proxmox.yml` build `release` / `schematic_id` | Same approved exact 1.13.x release and schematic |
| Cluster `cluster.talos_version` / `cluster.installer_image` | Same release (`v1.13.x`) and matching NoCloud installer schematic; select a compatible Kubernetes pin separately |
| `cluster_security_logging_talos_schema` | `v1.13`; this is a schema selection, not the exact OS patch release |
| Operator `talosctl` and Stage 5 serial SSO | Matching 1.13 client; the rollout checks the plan and running nodes too |

Talos **1.14 is not qualified for the complete path**: its logging renderer is available, but that
does not qualify the Cilium configuration or the Stage 5 serial SSO workflow. Select another minor
only as a separately qualified variant. Image Factory and linked hardware documentation may show
a newer release; they do not select an upgrade for this deployment. Do not downgrade an existing cluster.

For Talos, make these Image Factory selections in order: [1][2]

1. **Cloud server**, then the approved exact **1.13.x** version for the reference path.
2. **NoCloud**, architecture **amd64**.
3. System extension **`siderolabs/qemu-guest-agent`**.
4. Bootloader **UEFI only**, not Secure Boot.
5. Save the schematic definition/ID and matching installer-image reference;
   download the **disk image** `nocloud-amd64.raw.xz` and its verification material.

The extension must also be present in the matching installer/upgrade schematic;
adding it to a boot artifact alone is not the lifecycle contract.
Keep artifacts independently of the factory/registry for Tier 0 recovery.

<a id="step-1-verify-unpack-and-upload"></a>

## Step 2: Verify the download

On the **acquisition workstation**, verify the vendor checksum/signature for the **downloaded**
artifact using the vendor's procedure. A locally calculated hash is not proof of vendor origin.
Retain the artifact, verification material and source/release record for the later IaC catalog.

## Step 3: Unpack and hash the image

For Alma/Rocky, keep the verified `.qcow2` and calculate its SHA256. For Talos, unpack `.raw.xz`
with 7-Zip or the block below. The `.raw.xz` digest cannot verify the unpacked `.raw` bytes.

For a Bash workstation, from the directory containing the verified Talos download:

Run on **the acquisition workstation in the verified download directory**.
Unpack before uploading to Proxmox Import; retain the verified `.xz` archive.

```bash
unxz --keep nocloud-amd64.raw.xz
sha256sum nocloud-amd64.raw
```

`--keep` retains the approved compressed artifact. If the raw output already exists,
inspect it rather than overwriting it blindly. The optional
[approved cache](../../../05-operations/02-software-intake/host-updates.md) is not required for initial import.

## Step 4: Upload the prepared file

**When reusing only the artifact preparation for IaC:** return after Steps 2–3 and stage its local
file/checksum in the catalog. Do not perform the GUI upload/VM creation for an additional managed build.

In **Proxmox > Node > image storage > Import**, upload the verified `.qcow2`; for Talos, use the
resulting **`.raw` only**, not the compressed archive. Alternatively use the GUI URL transfer
with its matching digest where offered. Do not upload the compressed `.raw.xz`.
Check the upload task result before continuing. [3]
An existing first manual upload is adopted later, not reuploaded.

<a id="step-2-create-the-vm-shell-and-import-the-disk"></a>

## Step 5: Create the VM and import its disk

Select **Create VM**, enable **Advanced**, and leave **Start after created** off.
Reserve an unused `9xxx` template ID using the [VMID quick reference](../../../02-conventions/vmid-convention.md).
The following values are a starting profile; clones receive their actual sizing/network inputs.

| Wizard page | Common setting | Talos difference |
| --- | --- | --- |
| General | An unused template VMID and descriptive image name; e.g. `alma-10-tmpl`, `rocky-10-tmpl`, `talos-tmpl` | Record the exact Talos version/schematic in its publication record |
| OS | **Do not use any media**, guest OS Linux | Same; the raw image is the installed disk, not an installer ISO |
| System | Machine **q35**, BIOS **OVMF (UEFI)**, EFI disk **4m** on approved live storage | Same |
| System: EFI | **Pre-Enroll keys unchecked** for this non-Secure-Boot path; no TPM | Do not select a Secure Boot image accidentally |
| System: controller | **VirtIO SCSI single** for Alma/Rocky | **VirtIO SCSI** (`virtio-scsi-pci`), not Single, per current Talos guidance [2] |
| System: QEMU Agent | Enable only if the image contains the agent | Enable: the selected schematic includes `siderolabs/qemu-guest-agent` |
| Disks | Remove the default disk; click **Import**, choose the uploaded image, attach as **SCSI / scsi0** | Select the unpacked `.raw`; do not add another empty boot disk |
| Disks: target | Approved Proxmox live storage; discard when supported; cache **None** for the clustered path | Same; leave IO thread off with the non-Single controller |
| CPU | 2 cores initially; a common cluster CPU baseline, normally **x86-64-v3** on compatible hosts | Do not use `kvm64`; validate against the selected Talos release |
| Memory | 2048 MiB template default; **Ballooning unchecked** for all server templates; size each clone for its actual role | Same; Talos does not support memory hotplug [2] |
| Network | VirtIO NIC, `vmbr0` by default, NIC firewall enabled, MTU 1500; select the actual VLAN | Same; each clone receives its own static NoCloud IP |
| Confirm | Review imported disk/EFI storage; **do not start** | Same |

Use a CPU model supported by **every eligible destination**, not `host` by default.
Use the 9.2 CPU-model UI and actual CPU flags/requirements to select it;
qualify live migration on mixed hardware.

For IaC publication, set the shared template bridge/VLAN under `all:`; the publisher
selects NIC and OS-specific controller defaults without per-image tuning. Optional
overrides are listed in the [catalog reference](../../../05-operations/01-hosting/templates/template-lifecycle.md#catalog-fields-and-defaults).
For an existing [SDN VNet](step-1c-sdn.md), set `bridge` to its ID and
`vlan_id: null`. Activate the VNet with **Datacenter > SDN > Apply** before this GUI import;
the authorized GUI operator uses existing administrative access. Grant the publisher's VNet
permissions later during bootstrap API setup. The publisher attaches the template; it does not create zones,
VNets, port-isolation settings or firewall rules. Managed Linux and Kubernetes
clones select their own attachments from tier-owned inputs.
The base template starts at 10 GiB when the verified image fits; use a larger value
for a larger source image. Service clones receive their own disk sizing.
Templates and server VMs in every tier use fixed RAM with ballooning disabled.
The Terraform VM modules set `memory.floating = 0` explicitly; size hosts for the
configured guest RAM and HA failover capacity. [3][5]

<a id="step-3-convert-clone-test-and-approve"></a>

## Step 6: Add initialization media and boot order

In **Proxmox > VM > Hardware**, remove any unused CD/DVD drive. For **all three images**,
retain/add a **CloudInit Drive**: **Hardware > Add > CloudInit Drive**, bus **IDE**, slot **2**,
on the selected live VM storage. Retain IPv4 DHCP as the template network default;
leave accounts/passwords unset. In **Options > Boot Order**, enable `scsi0` first;
add a serial console if needed. Do not put site IPs, accounts or secrets in the template.

## Step 7: Convert and create a disposable clone

With the image **unbooted**, select **Convert to template**, then create a disposable **full clone**
with its own unused VMID. Do not boot/configure the reusable template.

## Step 8: Configure and qualify the clone

On the **clone**, open **Cloud-Init > IP Config (net0)** and set its static IPv4/CIDR and gateway.
For a Linux access test, add the approved test user's public key on this clone only.
For Talos, leave **User, Password, SSH public keys, DNS and other fields at defaults**;
regenerate the initialization image if edited. Its NoCloud drive supplies **networking only**. [4]
Boot and perform the [clone checks below](#clone-and-guest-control-checks).

Talos machine configuration/bootstrap belongs to [Stage 4](../../stage-4-kubernetes/procedures/talos-terraform.md)
when that cluster is deployed. Do not jump to that installation to finish the initial Linux-template path.

For EL packages or cleanup that require booting a builder, follow the
[mutable Linux refresh](../../../05-operations/01-hosting/templates/template-lifecycle.md#mutable-linux-refresh); never capture a configured
Talos node back into a base template. Disposable clone tests must not modify the template.

After the first manual Linux template passes, continue with the [bootstrap execution host](../bootstrap/README.md):
clone the tested Linux template to prepare the machine that will run the remaining IaC.
Do not capture that machine's credentials or state back into the reusable template.

DNS defaults must resolve required bootstrap services without this cluster or
later FreeIPA/Keycloak. If the host defaults cannot do that, commission independent
DNS first; an explicit DNS-only override is supported in the cluster inputs.
The common import flow is the same for Linux and Talos. The Talos-specific changes
are the raw image/Factory selections and OS-specific firmware/controller/agent requirements,
not another wizard. Disabling ballooning is common to all server templates.

After managed publication and clone acceptance, Tier 0 promotes the VMID, title and source node in Shared's
[consumer catalog](../../../08-reference/template-catalog.md). The consuming tier selects
that VMID and matching firmware; the template ID is not allocated in every tier.
Publication state belongs to Tier 0. A manually created template is not automatically
managed/imported by the publication root.
After preparing the bootstrap host, complete
[Foundation Step 4: import or publish with IaC](../README.md#step-4-publish-and-test-vm-templates)
before Stage 1. That step selects the plan for existing templates or new candidates.

Fresh Talos publication and cluster examples explicitly select `ovmf`, `q35`,
`virtio-scsi-pci`, an EFI disk without pre-enrolled keys, fixed RAM and the guest
agent. Existing input files without firmware settings retain their legacy BIOS
configuration. **Do not copy new firmware settings onto running VMs as an update**;
publish/test a new template and use a reviewed replacement/migration plan.

## Clone and guest-control checks

Qualify these independently before promoting a template:

| Check | Expected result |
| --- | --- |
| Full clone | Independent copy boots with its own network settings |
| Linked clone, when selected | Host storage supports it and all attached disks have the required base/snapshot state |
| Guest control | Proxmox's agent option is enabled, and the guest agent is installed and running inside the clone |

For a ZFS template, an imported boot disk still named `vm-*` may need
[single-disk base conversion](../../../05-operations/01-hosting/templates/template-disk.md#complete-base-conversion).
An unused rollback disk is skipped during cloning; deleting it is not a clone repair. [7]
Keep it until the new template has passed qualification. The current Linux VM
Terraform modules request full clones explicitly.

On the **Proxmox host**, test the running disposable clone's agent:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
read -r -p "Disposable clone VMID: " CLONE_VMID
qm agent "$CLONE_VMID" ping
```

If the agent does not respond, inspect it through the **disposable clone's console**,
not the reusable template or the deployment host:

Run inside the **disposable cloned Linux VM**.

```bash
rpm -q qemu-guest-agent
systemctl status qemu-guest-agent --no-pager
```

These package checks apply to RPM-based guests; use the guest distribution's package
query elsewhere. To include a missing agent in an Enterprise Linux base image, use the existing
[template-refresh builder](../../../05-operations/01-hosting/templates/template-lifecycle.md#mutable-linux-refresh),
which installs and starts the agent before publication. Do not boot or modify the
published template directly. Do not repair a manually configured clone and assume the base image is fixed.
For Talos, use its Factory extension instead.

When the Proxmox agent option is enabled but the guest agent is unavailable,
shutdown requests can time out. A fresh VM start is required after enabling the
Proxmox agent channel; a guest-only reboot does not recreate its virtual hardware. [8]

## Cluster handoff

Tier 0 alone owns the reusable image and `terraform/deployments/templates/` state.
Shared holds its approved VMID/title/source node. Each consuming tier owns its
`terraform/deployments/kubernetes/`, inventory, clone disks and cluster secrets.

For the [API publisher](../../../05-operations/01-hosting/templates/template-lifecycle.md#local-workflow),
record the unpacked image/hash, version/schematic and explicit firmware in Tier 0's
`templates/proxmox.yml`. Fresh examples include a DHCP CloudInit drive at `ide2`;
the consuming root supplies network-only settings per clone. Legacy catalogs that
omit `cloud_init_drive` retain their previous no-media behavior. For adoption, set
this field to match the manually created template rather than removing its drive.
This reaches the same clone configuration as the GUI path above without putting
site-specific network settings into a reusable image.

Use a matching **NoCloud installer** from the same Factory schematic/version so
the platform networking survives Talos installation and upgrades. A generic metal
installer is not an equivalent replacement for this boot contract.
Cluster configuration and bootstrap remain in the
[cluster guide](../../stage-4-kubernetes/procedures/talos-terraform.md), not in the template.
Never add Talos to mutable Linux template builders or capture an initialized node.
Publishing a new image does not update existing nodes; retain original state,
installer artifacts and recovery secrets independently of the cluster and hosted CI.

## References

1. [Talos Image Factory](https://docs.siderolabs.com/talos/v1.14/learn-more/image-factory).
2. [Talos on Proxmox: firmware, controller, memory and agent](https://docs.siderolabs.com/talos/v1.14/platform-specific-installations/virtualized-platforms/proxmox).
3. [Proxmox VM and disk configuration](https://pve.proxmox.com/pve-docs/qm.1.html).
4. [Talos NoCloud configuration](https://docs.siderolabs.com/talos/v1.14/platform-specific-installations/cloud-platforms/nocloud).
5. [Terraform Proxmox VM memory settings](https://registry.terraform.io/providers/bpg/proxmox/latest/docs/resources/virtual_environment_vm).
6. [Rocky Linux cloud image variants](https://docs.rockylinux.org/latest/teams/rel_eng/image/).
7. [Proxmox clone validation and unused-disk handling](https://raw.githubusercontent.com/proxmox/qemu-server/master/src/PVE/API2/Qemu.pm).
8. [Proxmox guest-agent setup and shutdown troubleshooting](https://raw.githubusercontent.com/proxmox/pve-docs/master/qm.adoc).

Sources 6–8 checked 2026-11-07; other sources reviewed 2026-10-27.
Match the selected image's release documentation.
