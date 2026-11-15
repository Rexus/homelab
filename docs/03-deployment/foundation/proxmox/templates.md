# Proxmox VM template guide

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** Proxmox VE 9+, approved image sources, unused template VMIDs,
an image datastore with **Import** content, and live VM storage on the eligible hosts.
For the first manual Linux image, use the independent workstation and Proxmox GUI;
the generated repositories and API publisher are not prerequisites for this guide.

One GUI disk-import workflow covers AlmaLinux, Rocky Linux, Debian and Talos. Choose the
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
- [Debian CA image preparation](#debian-ca-template)
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
| Debian 12 | Official [Bookworm cloud images](https://cloud.debian.org/images/cloud/bookworm/) · [download amd64 GenericCloud QCOW2](https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2) | Required for the supplied Stage 2 OpenXPKI issuer; prepare the guest agent below before import |
| Talos | [Image Factory](https://factory.talos.dev/) disk image, not ISO | Follow the selections below; retain version and schematic ID |

Base and LVM are valid Rocky GenericCloud variants. LVM describes storage inside
the guest; Proxmox clone support is determined by host storage and template disk
conversion. Expanding a virtual disk still requires the guest's partition, volume
and filesystem layers to consume the additional space. Verify the selected image's
first-boot resize behavior on a disposable clone.

> **CA prerequisite:** the current OpenXPKI installer checks for **Debian 12 amd64**. Ubuntu,
> Debian 13 and EL10 are not qualified substitutes for `ca-1`. HSM provider VMs can use EL10.
> Publish this image before reaching Stage 2; it need not replace the normal Linux default.

> **Boot policy:** this baseline uses UEFI with Secure Boot disabled, including Talos and the CA.
> Later stages do not enable it automatically. Signed boot media, guest key enrollment and firmware
> recovery require a separately qualified path; checking **Pre-Enroll keys** alone is not that path.

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

For Alma/Rocky, keep the verified `.qcow2` and calculate its SHA256. For Debian, complete the
agent preparation below and hash that prepared output. For Talos, unpack `.raw.xz`
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

<a id="debian-ca-template"></a>

### Debian CA image preparation

Download **`debian-12-genericcloud-amd64.qcow2`** and its matching
[SHA512SUMS](https://cloud.debian.org/images/cloud/bookworm/latest/SHA512SUMS) from the same accepted
Debian build. The `latest` link is for acquisition; retain the exact build/date and source digest,
then use that build as the catalog's `release`, not `latest`. [9]

On **the acquisition workstation**, verify the downloaded image against the matching manifest:

```bash
sha512sum --check --ignore-missing SHA512SUMS
```

Require `debian-12-genericcloud-amd64.qcow2: OK`. Retain the approved HTTPS source and verification
record; a checksum fetched alongside a file is not an independent publisher signature.

Stock Debian cloud images do not include `qemu-guest-agent`. Prepare a derivative before
enabling Proxmox's agent option. [9][10]

**Execution machine for the commands below:** a Linux preparation host holding the downloaded qcow2
as a file. An existing Rocky/Alma `boot-1`, a Linux workstation or a disposable Linux preparation VM
can fill this role. `virt-customize -a` opens that file and installs the package into its Debian
filesystem through libguestfs. The Debian target image stays powered off throughout preparation.
When using a disposable preparation VM, first copy the verified original qcow2 and its checksum
manifest into a private workspace on that VM. Its own installed OS can be Rocky/Alma or Debian/Ubuntu.

When reusing **`boot-1` already behind the cache**, first reconcile its
[bootstrap package sources](../../stage-01-software-intake/procedures/bootstrap-consumer.md#3-apply-the-local-configuration).
The tool installation below uses that preparation host's OS repositories. Rocky/Alma mirror lists
must select permitted endpoints before installing packages through a restricted proxy.

Install the image tool on **that Linux preparation host**. For Rocky/Alma EL10:

```bash
sudo dnf install -y guestfs-tools qemu-img
```

For Debian/Ubuntu, use this block instead:

```bash
sudo apt-get install -y libguestfs-tools qemu-utils
```

On **the same Linux preparation host**, select the workspace containing the verified original file:

```bash
read -r -e -p 'Absolute image workspace (example /srv/tier0/artifacts/debian-12): ' DEBIAN_IMAGE_WORKSPACE
ls -l "$DEBIAN_IMAGE_WORKSPACE/debian-12-genericcloud-amd64.qcow2"
```

Require the original qcow2 at that path. In **that same preparation-host shell**, create the derivative;
stop if the output already exists:

```bash
(
  set -e
  test ! -e "$DEBIAN_IMAGE_WORKSPACE/debian-12-genericcloud-amd64-agent.qcow2" || {
    printf '%s\n' 'Prepared output already exists; inspect or select a new output path.' >&2
    exit 1
  }
  cp -- "$DEBIAN_IMAGE_WORKSPACE/debian-12-genericcloud-amd64.qcow2" \
    "$DEBIAN_IMAGE_WORKSPACE/debian-12-genericcloud-amd64-agent.qcow2"
  virt-customize -a "$DEBIAN_IMAGE_WORKSPACE/debian-12-genericcloud-amd64-agent.qcow2" \
    --install qemu-guest-agent
  sha256sum "$DEBIAN_IMAGE_WORKSPACE/debian-12-genericcloud-amd64-agent.qcow2"
)
```

The image tool needs accepted Debian package access, or an independently prepared matching package
supply; a partially populated proxy cache is not an offline repository. Keep the original downloaded
file unchanged. Record this recipe plus source/output digests; the derivative is not the original
vendor-signed artifact. Never run `virt-customize` against an image in use by a VM. [10]

**Expected output on the preparation host:**
`$DEBIAN_IMAGE_WORKSPACE/debian-12-genericcloud-amd64-agent.qcow2` and its printed SHA256.
Retain the original image, matching manifest, recipe and both digests in the artifact record.

For GUI import, transfer that prepared output to the machine whose browser uploads it in Step 4.
For Terraform publication, place it in the controller's artifact workspace and set that local absolute
`image_path` plus the prepared output's SHA256 in `templates/proxmox.yml` under `debian-build-1`.

When a disposable VM performed preparation, run this example on **the receiving Linux workstation
or controller**, using its accepted SSH access to that preparation VM:

```bash
read -r -p 'Preparation VM SSH destination (example automation@10.10.10.60): ' DEBIAN_PREP_SSH
read -r -e -p 'Absolute prepared file on that VM (example /srv/tier0/artifacts/debian-12/debian-12-genericcloud-amd64-agent.qcow2): ' DEBIAN_PREPARED_IMAGE
read -r -e -p 'New absolute local output file (example /srv/tier0/artifacts/debian-12-genericcloud-amd64-agent.qcow2): ' DEBIAN_AGENT_LOCAL
scp "$DEBIAN_PREP_SSH:$DEBIAN_PREPARED_IMAGE" "$DEBIAN_AGENT_LOCAL"
sha256sum "$DEBIAN_AGENT_LOCAL"
```

Require a new local output path with an existing parent directory. Compare the received digest with
the preparation host's recorded value before upload/publication. A Windows browser workstation can
use its file-transfer client and `Get-FileHash -Algorithm SHA256` for the same public-image handoff.
Retain the accepted output and verification record before retiring a disposable preparation VM.

| Setting | Debian difference from the other images |
| --- | --- |
| Image | GenericCloud `.qcow2`, not the Talos raw image or an installation ISO |
| SCSI / firmware | Use the common Linux `virtio-scsi-single`, q35 and OVMF settings below; Talos has its own controller selection |
| Initialization | Normal Linux CloudInit user/SSH/IP settings on clones; Talos's drive supplies networking only |
| Agent | Add the Debian package above; Talos needs its Factory extension; verify every clone's agent |
| Guest storage | Do not assume Rocky's selected LVM layout; the CA's separate `scsi1` filesystem is created by Ansible |
| Consumer | `ca-1.template_vm_id` selects this Debian template; retain the EL10 default for other services |

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
| System: controller | **VirtIO SCSI single** for Alma/Rocky/Debian | **VirtIO SCSI** (`virtio-scsi-pci`), not Single, per current Talos guidance [2] |
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

In **Proxmox > VM > Hardware**, remove any unused CD/DVD drive. For **all selected images**,
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

Talos machine configuration/bootstrap belongs to [Stage 4](../../stage-04-kubernetes/procedures/talos-terraform.md)
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
query elsewhere. On the **disposable Debian clone**, use `dpkg-query -W qemu-guest-agent`
and `systemctl status qemu-guest-agent --no-pager`. To include a missing agent in an Enterprise Linux base image, use the existing
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
[cluster guide](../../stage-04-kubernetes/procedures/talos-terraform.md), not in the template.
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
9. [Debian cloud image selection and guest-agent policy](https://wiki.debian.org/Cloud/).
10. [Native offline image customization](https://libguestfs.org/virt-customize.1.html).

Sources 6–8 checked 2026-11-07; other sources reviewed 2026-10-27.
Source 10 rechecked 2026-11-15 for file-based customization and host/guest execution scope.
Match the selected image's release documentation.
