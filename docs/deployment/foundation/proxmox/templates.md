# Proxmox VM template guide

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Prerequisites:** Proxmox VE 9+, approved image sources, unused template VMIDs,
an image datastore with **Import** content, and live VM storage on the eligible hosts.

One GUI disk-import workflow covers AlmaLinux, Rocky Linux and Talos. Choose the
image below, then follow Steps 1-3. Talos-specific differences are explicit;
there is no separate ISO installation. For repeatable API publication instead,
use the [template lifecycle](../../../administration/compute/template-lifecycle.md).
Do not adopt the same template under both manual and Terraform ownership.

## Contents

- [Select the image](#select-the-image)
- [Step 1: Verify, unpack and upload](#step-1-verify-unpack-and-upload)
- [Step 2: Create the VM shell and import the disk](#step-2-create-the-vm-shell-and-import-the-disk)
- [Step 3: Convert, clone-test and approve](#step-3-convert-clone-test-and-approve)
- [Cluster handoff](#cluster-handoff)
- [References](#references)

## Select the image

| Image | Download | Important selection |
| --- | --- | --- |
| AlmaLinux | Official [Generic Cloud](https://wiki.almalinux.org/cloud/Generic-cloud.html), x86_64 `.qcow2` | Review EL10's CPU baseline; use the explicitly selected x86_64_v2 variant only for older compatible hosts |
| Rocky Linux | Official [GenericCloud Base](https://download.rockylinux.org/pub/rocky/10/images/x86_64/), x86_64 `.qcow2` | EL10 needs x86-64-v3-capable hosts |
| Talos | [Image Factory](https://factory.talos.dev/) disk image, not ISO | Follow the selections below; retain version and schematic ID |

For Talos, make these Image Factory selections in order: [1][2]

1. **Cloud server**, then the selected pinned Talos version.
2. **NoCloud**, architecture **amd64**.
3. System extension **`siderolabs/qemu-guest-agent`**.
4. Bootloader **UEFI only**, not Secure Boot.
5. Save the schematic definition/ID and matching installer-image reference;
   download the **disk image** `nocloud-amd64.raw.xz` and its verification material.

The extension must also be present in the matching installer/upgrade schematic;
adding it to a boot artifact alone is not the lifecycle contract.
Keep artifacts independently of the factory/registry for Tier 0 recovery.

## Step 1: Verify, unpack and upload

1. Verify the vendor checksum/signature for the **downloaded** artifact using the
   vendor's procedure. A locally calculated hash is not proof of vendor origin.
2. For Alma/Rocky, keep the verified `.qcow2`. For Talos, unpack `.raw.xz` with
   7-Zip or `unxz`; upload the resulting **`.raw` only**, not the compressed archive.
3. Calculate SHA256 for the exact file to upload. The `.raw.xz` digest cannot
   verify the unpacked `.raw` bytes. In **Node > image storage > Import**, upload
   the file or use the GUI URL transfer with its matching digest where offered.
   Check the task result before continuing. [3]

For a Bash workstation, from the directory containing the verified Talos download:

```bash
unxz --keep nocloud-amd64.raw.xz
sha256sum nocloud-amd64.raw
```

`--keep` retains the approved compressed artifact. If the raw output already exists,
inspect it rather than overwriting it blindly. The optional
[approved cache](../../../administration/compute/update-access.md) is not required for initial import.

## Step 2: Create the VM shell and import the disk

Select **Create VM**, enable **Advanced**, and leave **Start after created** off.
Reserve an unused VMID using [project conventions](../../../reference/proxmox-conventions.md#vm-and-template-id-ranges).
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
| Memory | 4096 MiB initially; reserve the real capacity in the host plan | **Ballooning unchecked**; Talos does not support memory hotplug [2] |
| Network | VirtIO NIC, selected bridge/VNet and VLAN where needed | Same; each clone receives its own static NoCloud IP |
| Confirm | Review imported disk/EFI storage; **do not start** | Same |

Use a CPU model supported by **every eligible destination**, not `host` by default.
Use the 9.2 CPU-model UI and actual CPU flags/requirements to select it;
qualify live migration on mixed hardware.

## Step 3: Convert, clone-test and approve

1. In **Hardware**, remove any unused CD/DVD drive. For **all three images**,
   retain/add a **CloudInit Drive**: **Hardware > Add >
   CloudInit Drive**, bus **IDE**, slot **2**, on the selected live VM storage.
   Leave template values at defaults. In **Options > Boot Order**, enable `scsi0`
   first; add a serial console if needed. Do not put site IPs, accounts or secrets in the template.
2. With the image **unbooted**, select **Convert to template**, then create a
   disposable full clone with its own VMID. Do not boot/configure the reusable template.
3. On the **clone**, open **Cloud-Init > IP Config (net0)** and set its static IPv4/CIDR and gateway. For Talos,
   leave **User, Password, SSH public keys, DNS and other fields at defaults**,
   then regenerate the image if edited. The drive supplies **networking only**;
   Talos machine configuration is applied separately over its API. [4] Boot and test
   the clone's disk, agent and network; continue with the
   [cluster procedure](../../stage-4-kubernetes/procedures/talos-terraform.md) for Talos configuration/bootstrap.

For EL packages or cleanup that require booting a builder, follow the
[mutable Linux refresh](../../../administration/compute/template-lifecycle.md#mutable-linux-refresh); never capture a configured
Talos node back into a base template. Disposable clone tests must not modify the template.

DNS defaults must resolve required bootstrap services without this cluster or
later FreeIPA/Keycloak. If the host defaults cannot do that, commission independent
DNS first; an explicit DNS-only override is supported in the cluster inputs.
The common import flow is the same for Linux and Talos. The Talos-specific changes
are the raw image/Factory selections and fixed-memory/agent requirements, not another wizard.

After testing, Tier 0 promotes the VMID, title and source node in Shared's
[consumer catalog](../../../reference/template-catalog.md). The consuming tier selects
that VMID and matching firmware; the template ID is not allocated in every tier.
Publication state belongs to Tier 0. A manually created template is not automatically
managed/imported by the publication root.

Fresh Talos publication and cluster examples explicitly select `ovmf`, `q35`,
`virtio-scsi-pci`, an EFI disk without pre-enrolled keys, fixed RAM and the guest
agent. Existing input files without firmware settings retain their legacy BIOS
configuration. **Do not copy new firmware settings onto running VMs as an update**;
publish/test a new template and use a reviewed replacement/migration plan.

## Cluster handoff

Tier 0 alone owns the reusable image and `terraform/deployments/templates/` state.
Shared holds its approved VMID/title/source node. Each consuming tier owns its
`terraform/deployments/kubernetes/`, inventory, clone disks and cluster secrets.

For the [API publisher](../../../administration/compute/template-lifecycle.md#local-workflow),
record the unpacked image/hash, version/schematic and explicit firmware in Tier 0's
`templates/proxmox.yml`. It keeps base templates without initialization media;
the consuming root creates the same network-only CloudInit drive per clone.
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

Sources reviewed 2026-10-27. Match the selected image's release documentation.
