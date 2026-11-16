# Install Talos with Secure Boot and TPM

Use this path for **new nodes** at [Stage 4, action 5](../README.md#step-5-edit-node-hardware-addresses-and-release-pins).
It also serves the independent Tier 1/2 cluster owners. [The cluster figure](../README.md#figure-1-control-cluster-runtime)
shows the resulting deployment; each node additionally owns its EFI variables and TPM 2.0 state.
Terraform uploads the signed ISO, creates blank disks and provisions the nodes. The Talos provider
applies their configuration. No manual guest setup is required.

**Work from:** the owning tier root on bootstrap, with its original cluster inputs/state.
**Requires:** the accepted Talos **1.13.x** release/CLI, approved Image Factory media/installer,
independent API endpoint and node DNS/time/image access. Complete the main guide's preceding actions.

> [!TIP]
> **Recovery and maintenance:**
> [Maintain boot trust and TPM](../../../05-operations/01-hosting/maintenance.md#boot-maintenance),
> [recover the original EFI/TPM identity](../../../05-operations/01-hosting/guest-hardening.md#boot-recovery), or
> [restore a clean Talos control plane](../../../05-operations/06-resilience/recovery/original-state-etcd.md#restore-a-clean-talos-control-plane).

## Contents

- [1. Select a fresh installation](#1-select-a-fresh-installation)
- [2. Obtain the matching signed ISO and installer](#2-obtain-the-matching-signed-iso-and-installer)
- [3. Configure the boot policy](#3-configure-the-boot-policy)
- [4. Provision and verify](#4-provision-and-verify)
- [5. Eject installation media and capture recovery](#5-eject-installation-media-and-capture-recovery)
- [Updates and recovery](#updates-and-recovery)
- [References](#references)

## 1. Select a fresh installation

Select unused VMIDs and empty OS disks. Retain the main guide's inventory, unique MACs, physical
placement, live disk storage, static NoCloud network and endpoint settings.

Existing template-based clusters keep their current policy. The command refuses switching the
boot mode, boot hardware or effective rendered system-disk encryption policy for existing nodes,
including changes hidden in custom patches. An existing GRUB installation needs
a fresh signed installation; an installer-image change alone does not convert it. [1]

This root selects one boot/encryption policy for its entire cluster. It does not mix signed and
template-built nodes as an in-place conversion. For an existing cluster, retain its identity and backups, then use the
[original-state and etcd recovery procedure](../../../05-operations/06-resilience/recovery/original-state-etcd.md#restore-a-clean-talos-control-plane).
Rebuild on separate capacity with the selected signed configuration and recover the original
cluster/application data as that procedure specifies. Keep quorum during a member replacement;
do not run this new-cluster bootstrap against a surviving cluster.

## 2. Obtain the matching signed ISO and installer

In **Image Factory**, select the approved exact **Talos 1.13.x**, **NoCloud / amd64**, **Secure Boot**
and the required extensions, including `siderolabs/qemu-guest-agent` if `qemu_agent = true`.
Retain the schematic definition/ID and the platform-specific installer reference. [1][2]

| Artifact | Required form |
| --- | --- |
| Installation ISO | `nocloud-amd64-secureboot.iso` |
| Installed/upgrade image | `factory.talos.dev/nocloud-installer-secureboot/<schematic-id>:<exact-version>` |
| Schematic/version | The same approved selection for both artifacts |

Use the accepted software-intake copy when available. For a direct approved Factory download,
run on **bootstrap in the artifacts directory**. The existing shell proxy settings apply:

```bash
read -r -p 'Approved exact Talos release, including v (example: v1.13.0): ' TALOS_RELEASE
read -r -p 'Approved Factory schematic ID (64 hex digits, from Factory): ' TALOS_SCHEMATIC
curl --fail --location --output nocloud-amd64-secureboot.iso \
  "https://factory.talos.dev/image/$TALOS_SCHEMATIC/$TALOS_RELEASE/nocloud-amd64-secureboot.iso"
sha256sum nocloud-amd64-secureboot.iso
realpath nocloud-amd64-secureboot.iso
```

Record the source, schematic, release and accepted SHA256 with the artifact. Compare with the
approved publication digest when one exists; calculating a local hash alone proves no provenance.
The hash entered below pins the accepted bytes for the upload. Retain the ISO independently for
recovery; this path does not require a paid Factory digest/publication feature.

## 3. Configure the boot policy

Edit **the owning tier's `terraform/deployments/kubernetes/terraform.tfvars`**.
Replace the existing template selection and firmware profile with this block. Replace the ISO path,
hash and ISO datastore with your accepted values from action 2 and Proxmox **Datacenter > Storage**:

```hcl
template_vm_id = null
vm_firmware = { bios = "ovmf", machine = "q35", scsi_hardware = "virtio-scsi-pci" }
secure_boot = {
  iso_path               = "/home/bootstrap/artifacts/nocloud-amd64-secureboot.iso"
  iso_sha256             = "REPLACE_WITH_ACCEPTED_64_HEX_SHA256"
  iso_datastore_id       = "local"
  encrypt_system_disks   = true
  install_media_attached = true
}
```

In the **existing `cluster` object**, set `installer_image` to the exact signed **NoCloud** installer
from action 2 and `talos_version` to that release. Keep all its other fields and the ordered
`machine_config_patches`. This path requires the NoCloud installer, rather than the generic
metal installer, so the installed system retains the selected NoCloud network behavior. [2]

| Input | Behavior |
| --- | --- |
| `iso_datastore_id` | ISO-capable, active storage on every target host; shared ISO storage is uploaded once, local storage once per host |
| Each `nodes.<name>.datastore_id` | Live VM-image storage for that node's OS, EFI and fresh TPM state |
| `encrypt_system_disks = true` | Default: LUKS2 for STATE and EPHEMERAL with TPM slot 0 and Secure Boot checked at enrollment |
| `encrypt_system_disks = false` | Explicit alternative: signed boot and a unique TPM, without these disk-encryption patches; decide before first deployment |

The provisioning token needs `Datastore.AllocateSpace` and `Datastore.AllocateTemplate` on the ISO
store, plus the existing scoped VM/disk permissions. Use the
[API access guide](../../foundation/proxmox/api-access.md). Terraform does not overwrite an existing
unowned ISO; its cluster/hash filename and retained resource avoid accidental media replacement.

Fresh nodes also have a socket-backed serial console for early boot/recovery inspection.
Fresh EFI variables are `4m`, with vendor pre-enrollment **off** so signed Talos media can enroll
its own trust in setup mode. Terraform creates a separate TPM 2.0 for every node, rather than
cloning an initialized TPM. Routine convergence preserves both state volumes. [1][3]

## 4. Provision and verify

Return to **main-guide action 6**, retaining this policy while preparing image access, CNI/storage
and logging. At actions 8/9, from **the owning tier root**, run:

```bash
bash scripts/kubernetes-cluster.sh plan
```

Require only the intended new VMs and ISO uploads, OVMF/q35, a unique `tpm_state` per VM,
EFI `4m`, ISO `ide0` and network-only NoCloud `ide2`. Review before applying:

```bash
bash scripts/kubernetes-cluster.sh apply
```

**Expected:** each node boots signed media, enrolls EFI trust, installs the matching signed system
and unlocks its selected system volumes through its own TPM. The command queries every node over
its authenticated Talos API and requires `secureBoot` and `bootedWithUKI` to be true. With encryption
selected, it also requires ready LUKS2 STATE/EPHEMERAL volumes using TPM slot 0. A failed check stops
the completion handoff; retain state and diagnose without clearing the TPM or reinitializing nodes.

Export the original credentials at main-guide action 10 and continue the platform deployment.
Boot verification does not replace Cilium, node, storage or application acceptance.

## 5. Eject installation media and capture recovery

After installation, edit **the same `secure_boot` object**: set `install_media_attached = false`.
From **the owning tier root**, prepare the plan:

```bash
bash scripts/kubernetes-cluster.sh plan
```

Review before continuing: require the ISO media to change to `none`, with the existing CD-ROM
device and disk-first boot order retained. Stop on any boot-order/hardware replacement or unrelated
VM change; use [serial maintenance](../../../05-operations/01-hosting/maintenance.md#talos-updates)
for a separate required change. The approved ISO remains retained in storage/state.

After accepting **that saved plan**, run from **the same tier root**:

```bash
bash scripts/kubernetes-cluster.sh apply
```

Schedule a controlled installed-disk cold boot for one node at a time,
preserving quorum; after each boot run from **the same tier root**:

```bash
bash scripts/kubernetes-cluster.sh verify-security
```

Capture a **coherent VM backup including OS, EFI and TPM state**, plus the original machine secrets,
configuration/talosconfig, etcd snapshots and workload/PVC backups. Test isolated recovery before
accepting the encrypted installation. An OS disk alone cannot replace its lost TPM unlock identity.
Use the [boot recovery checklist](../../../05-operations/01-hosting/guest-hardening.md#boot-recovery).

## Updates and recovery

**Adding nodes after ISO eject:** set `secure_boot.install_media_attached = true` in the owning
cluster inputs before planning new nodes. Existing nodes keep the OS disk first in boot order;
new nodes need the approved ISO for their blank disk. The plan guard rejects scale-out with the
media ejected. Review that existing nodes receive only the media change with their boot order
preserved; stop on unrelated existing-node changes. After installation and acceptance, eject again
through action 5.

Keep the signed **NoCloud** installer family and approved signing trust for serial OS updates.
Use [Talos maintenance](../../../05-operations/01-hosting/maintenance.md#talos-updates), then run
`verify-security`. Keep the original enrollment ISO/hash in these inputs; it need not be replaced
for every OS update. Apply changes to machine configuration through the original state/owner.

EFI trust/dbx changes, a TPM reset or loss of backing state can prevent unlock. Restore a coherent
accepted VM set or rebuild a node and recover cluster/workload data through the original recovery
procedure. Do not remove encryption, add an unprotected STATE key, reset EFI or regenerate cluster
secrets as a shortcut. TPM-bound encryption protects stored data within this VM/hypervisor trust
model; a software vTPM does not give a compromised hypervisor the isolation of a physical HSM.

## References

1. Talos 1.13, [Secure Boot, enrollment and TPM encryption](https://docs.siderolabs.com/talos/v1.13/platform-specific-installations/bare-metal-platforms/secureboot).
2. Sidero Labs, [Image Factory artifact API](https://github.com/siderolabs/image-factory/blob/main/docs/api.md)
   and [NoCloud Secure Boot installer resolution](https://github.com/siderolabs/talos/issues/10486).
3. BPG 0.112.0, [VM firmware/TPM and media](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/resources/virtual_environment_vm.md).
