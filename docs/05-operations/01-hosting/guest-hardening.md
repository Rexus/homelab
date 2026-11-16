# Guest hardening and commissioning

Apply the selected baseline while deploying each component. Use the final checkpoint in Foundation
and each stage to verify it, close temporary access and record the accepted operating state.
Secure Boot, a virtual TPM (vTPM) and disk encryption are separate choices made before changing
firmware, media or key dependencies. There is no universal end-of-stage switch for them.

**Work from:** the owning tier's original inputs/state and the selected host or guest console.
**Before a change:** independent console access, approved artifacts, a maintenance window and a
[complete recovery set](../06-resilience/backups/recovery-set.md).
Offline custody and root ceremonies retain their own procedures and authority boundaries.

## Contents

- [Close a stage or commission a permanent guest](#stage-checkpoint)
- [Choose independent controls](#control-decisions)
- [What the current IaC actually controls](#iac-contract)
- [Qualify Linux Secure Boot](#linux-secure-boot)
- [Qualify Talos boot security](#talos-boot-security)
- [Preserve boot identity and recover](#boot-recovery)
- [References](#references)

<a id="stage-checkpoint"></a>

## Close a stage or commission a permanent guest

Run this checkpoint for the **selected components only**, after that stage's functional checks.
An earlier stage needs no later PKI, directory, central logging or Vault deployment to finish.
Use its accepted local credentials, local logs, independent time/DNS and recovery custody until
those later capabilities are deliberately integrated. Do not postpone access restrictions or
backup capture until the checkpoint.

1. Identify each retained VM, container, Kubernetes node and physical host. Record its owner,
   purpose, tier/setup, VMID, OS/image release, network paths and temporary/permanent status in
   `<prefix>-architecture/deployments.md` or its linked private operating record. Containers share
   their host kernel and have no independent EFI/vTPM choice. Keep original state and identities.
2. Verify the baseline appropriate to that component. Ordinary EL/Debian leaf VMs can use the
   opt-in [Linux security profile](linux-security.md); it owns key-only SSH, chrony, its selected
   firewalld zone and local audit. Proxmox uses [host hardening](proxmox-hardening.md), its own
   firewall and [TLS trust](proxmox-tls.md). Talos uses its API/machine configuration and network
   policy; never apply the leaf-host role to Proxmox or Kubernetes nodes. Confirm a fresh allowed
   administration connection, denied access from an unrelated source, working time/DNS and the
   actual service listeners. Keep the independent console usable.
3. Close deployment-only paths: retire temporary accounts/tokens/keys after testing their permanent
   replacements, remove temporary firewall allows, eject installation ISOs and review **VM > Options
   > Boot Order**. Retain a required NoCloud/cloud-init network drive. A permanent VM stays a VM;
   converting it to a template or rebuilding it is not a hardening action. Review **Start at boot**
   and startup/shutdown dependencies, or the selected HA resource policy, before claiming unattended
   recovery. An `always-on` tag alone configures neither behavior.
4. Inspect the actual boot hardware before selecting any change. On the **owning Proxmox host**,
   choose the VMID from the owning tier input, for example `701` for a disposable pilot:

   ```bash
   read -r -p 'Selected VMID from owned inputs (example: 701): ' GUEST_VMID
   qm config "$GUEST_VMID" --current 1
   qm pending "$GUEST_VMID"
   ```

   Record `bios`, `machine`, `scsihw`, `boot`, `efidisk0`, `tpmstate0`, disk/backup settings and
   pending changes. Absence of `bios` normally means SeaBIOS on this x86 deployment. EFI keys in
   configuration do not prove that verification is active inside the guest. Use the OS checks below.
5. Record the [control decisions](#control-decisions). If selected, qualify boot verification before
   creating a new permanent guest, or schedule the explicit migration/replacement below. Keep an
   existing accepted boot profile until that workflow passes. An unmet required control blocks
   production acceptance; record an exception with owner/review date rather than marking it enabled.
6. Capture the original ignored inputs/state, service data and recovery credentials through the
   [backup procedure](../06-resilience/backups/virtual-machines.md). Include firmware and TPM state
   where present. Verify backup completion and recoverability using this stage's available backup
   target; do not require a future in-cluster backup controller. Run an isolated restore before
   accepting a recovery or production claim that depends on it.
7. Record results, exceptions, recovery location and the next maintenance owner. Use
   [maintenance](maintenance.md) for patch/capacity policy. Confirm currently available local audit
   records; verify central receipt only when that service is already commissioned. Return to the
   calling stage's completion gate.

| Acceptance | Required evidence |
| --- | --- |
| Stage complete | Selected functions work; applicable baseline checks pass; original inputs and recovery material are captured; deferred optional integrations are named |
| Production accepted | Required security controls are observed, supported patch/reboot policy is owned, and service capacity/access/monitoring meet the selected contract |
| Recovery accepted | An isolated restore uses independently recoverable state, artifacts, keys and service data; record measured data age and restore time |
| HA accepted, if selected | Independent placement, quorum, fencing, surviving capacity/storage and a measured failure test through [Proxmox HA](proxmox-ha.md) and the application runbook |

Boot verification does not establish any of the other acceptance results.

<a id="control-decisions"></a>

## Choose independent controls

| Control | Protects / decision to record | Does not establish |
| --- | --- | --- |
| UEFI Secure Boot | Verification of the selected signed boot chain against enrolled firmware trust; record media, signer, trust database and observed guest state | Disk confidentiality, safe applications, protection from a privileged hypervisor operator |
| vTPM | A software TPM interface and persistent per-VM state; select only for an identified consumer | Boot verification, encryption or physical TPM isolation; Proxmox administrators can access its backing volume [1] |
| Disk encryption | Confidentiality of the selected disks/volumes; record unlock method and independent recovery key custody | A backup, service failover or protection from a running compromised guest/hypervisor |
| Unattended updates | A separately qualified package/image selection, scheduling and reboot policy | Approval merely because an intake proxy permits a download |
| HA | Recovery of availability under the tested failure model | Backup history or clean recovery from corruption/compromise |

Adding a TPM never enrolls application secrets or disk-unlock keys in this kit. Encryption and TPM
binding need their own recovery-tested design. Changing EFI keys, dbx revocations, firmware, machine
type or TPM identity can change measurements and prevent an existing TPM-bound volume unlocking.
Keep recovery credentials outside that VM and outside its dependent identity/secret services. [2][3]

<a id="iac-contract"></a>

## What the current IaC actually controls

The source contract is the same across the three tier-local generic VM modules. Template publication
and the separate Kubernetes root have different lifecycles; do not infer one from another.

| Owner and exact input | Implemented behavior / limit |
| --- | --- |
| Tier 0 `templates/proxmox.yml`, `all` / `templates.<key>`: `bios`, `machine`, `scsi_hardware`, `efi_pre_enrolled_keys`, `tpm_version` | Maps to `images` in [`proxmox_templates`](../../../tier-0/terraform/modules/proxmox_templates/variables.tf). OVMF creates a `4m` EFI disk. Optional `tpm_version: v2.0` creates TPM state on `datastore_id`; `v1.2` is also accepted. Omitted enrollment is `false`; omitted TPM is absent. These are hardware capabilities, not signed-image preparation |
| Shared `templates/proxmox-catalog.tfvars`, `proxmox_template_catalog["<VMID>"]`: `bios`, `machine`, `scsi_hardware`, `efi_pre_enrolled_keys` | Published creation profile for generic Linux clones. Defaults/older revisions are preserved by synchronization; TPM metadata is not exported. See [catalog ownership](../../08-reference/template-catalog.md) |
| Owning tier `terraform/deployments/<setup>/terraform.tfvars`, `vm_instances["<host>"].template_vm_id` and optional `.firmware` | Generic Linux guests use the actual clone source's catalog profile. A `.firmware = { bios = "ovmf", machine = "q35", scsi_hardware = "virtio-scsi-single", efi_pre_enrolled_keys = true }` override replaces the whole creation profile; it does not merge missing fields |
| Generic [`vm` lifecycle](../../../tier-0/terraform/modules/vm/main.tf) | Preserves existing/imported BIOS, machine, SCSI controller, EFI disk, boot order and TPM state. Changing catalog/firmware inputs does not retrofit them. CPU, RAM, regular disks and networking remain managed. Per-guest TPM creation/rotation is not exposed; do not infer safe unique TPM identities from template cloning |
| Template adoption, `scripts/proxmox-templates.sh import` | Import plans against the supplied publication catalog; its template resource does **not** use the generic VM boot-preservation rules. Enter the observed firmware/enrollment/TPM settings and review all differences before apply |
| Owning tier `terraform/deployments/kubernetes/terraform.tfvars`: `template_vm_id`, `vm_firmware.{bios,machine,scsi_hardware}`, `qemu_agent` | Talos root creates full clones, OVMF `4m` EFI disks with `pre_enrolled_keys = false`, and no explicit TPM block. Defaults retain legacy BIOS/Single-controller behavior; new examples explicitly select OVMF/q35/`virtio-scsi-pci`. Only `node_name` is ignored; firmware edits can affect existing nodes |
| Same Talos file: `cluster.talos_version`, `cluster.installer_image`, `machine_config_patches` | Supplies initial Talos machine configuration. No signed-media enrollment/upgrade controller, generic guest adoption or TPM-encryption recovery workflow is implemented. Changing the installer string is not an OS upgrade |

The native provider offers `efi_disk` and `tpm_state`, but a complete guest TPM path also needs typed
inputs/resolution, unique clone identity, import preservation, placement/backup checks and recovery
tests. The Talos Packer file is an incomplete scaffold. Neither path supplies missing lifecycle
automation. Use the existing supported controls above; qualify extensions explicitly. [4]

<a id="linux-secure-boot"></a>

## Qualify Linux Secure Boot

Use a disposable pilot on an isolated network. The ordinary vendor boot chains for Debian and
EL10 use signed shim/bootloader/kernel components. Custom kernels and out-of-tree drivers need
trusted signatures/enrollment too; an OS family label alone does not qualify the artifact. [3][5]

1. Select the service-supported distribution/release and verify its image provenance. Keep service
   constraints: a bootable EL10 image is not a substitute for a service that requires Debian 12.
   Prepare UEFI boot files and an EFI System Partition (ESP) **inside the guest disk**; this ESP is
   distinct from Proxmox's EFI variable disk. Use current signed recovery media for that image.
2. For a **new template revision**, edit Tier 0 `templates/proxmox.yml` under the selected
   `templates.<new-key>`: set `bios: ovmf`, the tested `machine`/`scsi_hardware`, and explicitly
   `efi_pre_enrolled_keys: true`. Retain all required artifact/hash/VMID/storage fields and all
   existing managed entries. Leave `tpm_version` absent unless separately selected. Do not apply
   these choices to Talos. Proxmox pre-enrollment initializes trust and enables verification on a
   new EFI disk; the firmware menu can subsequently change the effective state. [1]
3. Publish through the [template procedure](templates/template-lifecycle.md#how-is-a-new-template-published),
   then boot an isolated disposable clone. On the **Linux pilot**, install inspection tools from
   its approved sources if absent. Choose only the matching distribution block:

   Debian pilot:

   ```bash
   sudo apt-get install mokutil efibootmgr
   ```

   Rocky/Alma pilot:

   ```bash
   sudo dnf install mokutil efibootmgr
   ```

   On **that pilot**, inspect after a cold start from its installed disk:

   ```bash
   mokutil --sb-state
   sudo efibootmgr -v
   sudo journalctl -k -b --no-pager
   ```

   Require `SecureBoot enabled`, the intended signed loader and functioning storage/network
   drivers. A tool reporting unavailable EFI variables is not successful verification. Test a kernel
   update, another cold start, backup restore and recovery-media boot before promotion.
4. Retain the tested firmware profile in Shared and select the new `template_vm_id` for **new**
   guests, following [promotion](templates/template-lifecycle.md#how-is-a-tested-image-promoted-or-rolled-back).
   The publisher synchronizes references; it does not change the default selection automatically.
   Existing guests retain their installed OS/boot hardware. Plan and review their own lifecycle.
5. For an **existing guest**, capture its recovery set and reproduce it on isolated capacity first.
   Already-UEFI guests with a compatible signed chain can be qualified using the OVMF console.
   SeaBIOS installations need an explicit boot-layout migration or replacement; changing `bios`
   alone does not create an ESP/loader. A `2m` EFI disk needs replacement to support Secure Boot;
   that resets firmware variables/boot entries/custom keys. Do not delete/recreate the production
   EFI disk as a generic recipe. Schedule only the tested change, verify through the console, then
   inspect a no-surprise IaC plan before resuming writers. [1]

Current trust also matters: 2011/2023 Microsoft CA transitions, shim/SBAT and dbx revocations can
invalidate older boot/recovery media. Updating host firmware packages does not necessarily update
an existing VM's enrolled databases. Inspect actual guest trust and the installed Proxmox version's
**EFI Disk > Disk Action > Enroll Updated Certificates** support before planning an enrollment;
retain recovery keys and test the transition first. Do not weaken revocations to make stale media
boot. Alma's current certificate guidance is specific to its supplied shim/architecture. [1][2]

<a id="talos-boot-security"></a>

## Qualify Talos boot security

**Current kit path:** approved NoCloud raw image/template plus its matching installer/schematic.
The reference platform selects Talos 1.13.x; changing to 1.14 also needs the existing full-platform
qualification. Use the [Talos deployment contract](../../03-deployment/stage-04-kubernetes/procedures/talos-terraform.md).

**Not implemented:** a complete signed Talos media/publication/enrollment lifecycle. Upstream Talos
uses signed systemd-boot and a Unified Kernel Image (UKI), an enrolled Sidero/custom signing key and
the matching Secure Boot installer. Its 1.13 guide requires a fresh installation for a non-UKI
GRUB-based node. Pre-enrolling Microsoft keys is not the Sidero enrollment procedure. [6]

1. Keep current nodes on their accepted firmware/media. In a separate isolated qualification
   project/state, select an exact release, schematic/extensions and signed ISO/UKI installer from
   the version-matched upstream guide. Retain hashes and the signer/trust policy.
2. Design UEFI setup-mode/key enrollment, repeatable publication and upgrade/recovery handling
   before creating a candidate. The existing NoCloud clone workflow does not implement those steps.
   Do not pass a signed installer name to ordinary nodes and claim conversion support.
3. Verify a candidate's installed-disk boot through its authenticated Talos API. On the **approved
   execution host**, using that candidate cluster's own credentials:

   ```bash
   read -r -p 'Candidate Talos node IP (example: 192.0.2.41): ' TALOS_NODE
   read -r -p 'Candidate talosconfig path (example: secrets/talos/talosconfig): ' TALOS_CONFIG
   talosctl --talosconfig "$TALOS_CONFIG" --nodes "$TALOS_NODE" get securitystate
   ```

   Require the intended `SECUREBOOT` result, working API/network/storage and cold-start recovery.
   Ordinary current nodes can use the same read-only command to record their actual state.
4. Test signed upgrades, backup/restore and trust-key continuity. If separately selecting TPM-based
   encryption, first supply a unique per-node TPM and an independent, tested unlock/rebuild recovery
   method. Preserve signing/PCR keys when using custom keys. Do not copy the upstream TPM-encryption
   example into all-node `machine_config_patches` as an automatic hardening step. [6]
5. Only after qualification, implement/review the missing media/input/lifecycle path and its native
   provider tests. Migrate nodes using the product's supported replacement process, preserving
   cluster identity/quorum and application data. No supplied command completes this transition today.

<a id="boot-recovery"></a>

## Preserve boot identity and recover

1. Before firmware, key, TPM, storage, host or VMID changes, capture the **coherent guest backup**,
   configuration and [original tier state](terraform-state.md). Include OS/data disks, Proxmox EFI
   variables (`efidisk0`), TPM state (`tpmstate0`), actual boot order/controller/machine version,
   guest ESP, enrolled custom keys and independently usable encryption recovery material.
   Proxmox includes its EFI disk in backups/snapshots; inspect the actual backup task and isolated
   restore for all required volumes. A bare OS-disk export is not this recovery set. [1]
2. Keep original approved boot/installer artifacts, working recovery media, API/client credentials
   and external data backups available without the guest. For Talos retain original machine secrets,
   per-node configuration, talosconfig, etcd snapshots and workload/PVC backups. A VM snapshot does
   not establish a coherent database or multi-member cluster recovery point.
3. Before migration/HA, verify every target can access or receive **all** required disks including
   EFI/TPM state, the same bridges/VLANs, compatible CPU/firmware and required passthrough devices.
   A host's physical TPM does not automatically become a guest's vTPM. Test a cold boot/failover;
   inspect the guest boot/encryption state after the move. Use [HA operations](proxmox-ha.md).
4. On failed verification or unlock, stop the rollout and retain console/error evidence. Use the
   last accepted complete recovery set on isolated capacity and the product's recovery procedure.
   Do not clear a TPM, reset firmware keys, reformat a volume or regenerate cluster/application
   identities to make it boot. Use the independently retained recovery method when measurements
   change. Suspected compromise follows [clean-target recovery](../06-resilience/recovery/README.md).
5. Return production ownership only after service, access, boot and backup checks pass. Import or
   reconcile recovered resources through the [state guide](terraform-state.md); never apply a
   creation plan against an unadopted recovered VM.

## References

Official constraints reviewed 2026-11-16; use documentation matching the installed release.

1. Proxmox, [VM firmware, EFI trust and TPM](https://github.com/proxmox/pve-docs/blob/master/qm.adoc#bios-and-uefi).
2. AlmaLinux, [UEFI Secure Boot certificate transition](https://wiki.almalinux.org/documentation/secure-boot-2023-certificates).
3. Red Hat, [EL10 Secure Boot and module signing](https://docs.redhat.com/pt-br/documentation/red_hat_enterprise_linux/10/html/managing_monitoring_and_updating_the_kernel/signing-a-kernel-and-modules-for-secure-boot).
4. BPG Proxmox provider 0.112.0, [VM resource and cloning notes](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/resources/virtual_environment_vm.md).
5. Debian 13, [UEFI and Secure Boot installation constraints](https://www.debian.org/releases/trixie/amd64/ch03s06.en.html).
6. Talos 1.13, [Secure Boot, UKI installation and TPM dependencies](https://docs.siderolabs.com/talos/v1.13/platform-specific-installations/bare-metal-platforms/secureboot).
