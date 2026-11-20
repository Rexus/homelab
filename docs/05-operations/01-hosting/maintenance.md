# Maintenance and hardware replacement

Maintain one bounded component at a time using its native lifecycle procedure and the original
tier-owned configuration/state. Successful convergence is not proof that an upgrade is compatible.
This is the common operating guide for permanent Linux VMs, Talos nodes and Proxmox hosts.
Apply [guest hardening and commissioning](guest-hardening.md) during deployment and verify it
again after changes; a new template selection does not update an existing installed guest.
Use [template lifecycle](templates/template-lifecycle.md),
[Ansible recipes](ansible-recipes.md) and the selected product's release documentation for exact commands.
For ownership and storage boundaries, see [runtime design](../../01-architecture/04-hosting/01-runtime.md).

<a id="contents"></a>

## Find a task

- [What needs routine attention?](#routine-schedule)
- [How is a configuration reconciled?](#reconcile-a-component)
- [How is an upgrade approved?](#upgrade-gate)
- [Which OS lifecycle applies?](#os-lifecycles)
- [How are Debian or Rocky/Alma packages updated?](#linux-updates)
- [How are Talos and Kubernetes updated?](#talos-updates)
- [How are boot trust and TPM maintained?](#boot-maintenance)
- [How are CPU, RAM and guest disks resized?](#resize-guests)
- [How is the changed component accepted?](#post-change)
- [How is failed or aging hardware replaced?](#replace-hardware)
- [References](#references)

<a id="routine-schedule"></a>

## What needs routine attention?

Record actual intervals, owners and evidence in project administration:

| Activity | Review / action |
| --- | --- |
| Backup and intake health | Alert on missing successful jobs, source silence, queue/WAL growth and storage pressure; do not wait for a dashboard review |
| Certificates and credentials | Review expiry/renewal, CA/CRL distribution, service identities, backup access and independent break-glass custody |
| Security updates | Review product advisories, approve artifacts through software intake and schedule a canary/maintenance window |
| Restore drill | Restore one selected recovery set to isolated clean targets and record observed RPO/RTO |
| Capacity/failure domains | Review node/storage growth, real physical placement and single shared NAS/power/network dependencies |
| Access | Review privileged roles, abandoned devices/tokens, source-project protections and logging read scopes |
| Boot/recovery compatibility | Review firmware/EFI trust, shim/UKI, revocations, TPM/encryption dependencies and whether retained recovery media still boots |
| Physical Proxmox TPM and signed boot | Before/after firmware, motherboard or bootloader changes, retain consumer recovery material and rerun the [host acceptance procedure](proxmox-host-boot-security.md#maintenance-and-recovery) |
| Signing hardware | Inspect commissioned USB devices, approved key fingerprints, connector/client credentials and independently retained wrapped-key recovery material |

The proxy/cache controls software access; it is not a patch-selection or automatic reboot controller.
The kit's maintenance recipes cover their documented supported operations, not a universal
distribution/product upgrader. OS/vendor update approval and rolling-upgrade execution remain
explicit operator tasks unless a project supplies a qualified controller.

<a id="reconcile-a-component"></a>

## How is a configuration reconciled?

**Work from:** the owning tier's repository root on the approved execution host.
**Prerequisites:** existing inventory/state, accepted service inputs, independent recovery and a maintenance window.

1. Select the supported operation in the [recipe map](ansible-recipes.md#recipe-map).
2. Review that tier's `ansible/group_vars/<setup>.yml` and any selected environment overlay.
   Keep original inventory and service identities; do not copy starter examples over live inputs.
3. Run the selected maintenance recipe. For Tier 0 directory health checks:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/deploy.sh foundation --recipe maintenance
   ```

4. Verify the recipe's service checks and protected audit delivery before closing the window.

**Expected:** only the documented maintenance operation runs; Terraform is skipped.
**Stop:** on failed checks or unexpected changes. Earlier tasks may already be active;
there is no automatic rollback. Restore the last approved configuration through the product runbook.

<a id="upgrade-gate"></a>

## How is an upgrade approved?

**Work from:** the product owner's tier and native administration interface.
**Prerequisites:** a supported upgrade path, approved artifacts, tested backups and an isolated canary.

1. Select the component and target release; read its supported upgrade path, intermediate stops,
   dependencies and rollback restrictions. Record the resolved provider/chart/image/tool versions
   in owned machine-readable inputs and retain their approved artifacts independently.
2. Take a coherent recovery point and verify access to the original state, keys and
   [product restore procedure](../06-resilience/recovery/README.md). Pause competing Terraform, Ansible and delivery
   writers. Inspect the plan/rendered manifests; stop on unexpected deletion or replacement.
3. Exercise a canary with separate inputs/state. Upgrade one approved failure domain at a time;
   verify quorum, readiness, application access, audit delivery, queues and storage after each unit.
   A pod count alone is not a service health gate.
4. Continue only after the recorded gate passes. On failure, stop and use the product's supported
   rollback or restore path. Database/schema migrations can make a simple Helm or image rollback
   invalid. Never reinitialize keys, state or cluster identity merely to make convergence pass.

For Kubernetes, retain original machine configuration/secrets and etcd snapshots; use release-matched
Talos lifecycle commands, not fresh Terraform bootstrap, to upgrade nodes. For GitLab, follow its
required upgrade stops and dependency ordering in the
[data-service guide](../../03-deployment/stage-09-development/procedures/data-services.md).
For CA/directory services, preserve the original signing/domain identity and audit continuity.
For Proxmox packages, follow [host updates through the approved proxy](../02-software-intake/host-updates.md#how-are-proxmox-updates-installed).

**Expected:** each upgraded unit passes its health, access, audit and recovery gates before the next unit.
The kit supplies no universal upgrade command. A maintenance reconciliation is not an upgrade controller.

<a id="os-lifecycles"></a>

## Which OS lifecycle applies?

Select the actual installation type before running commands. The repo's baseline supports more
distributions than every application does; retain each service's exact supported OS/release.

| Installed component | Owner / supported operating path | Boundary |
| --- | --- | --- |
| Proxmox VE host | Tier 0 inventory; host APT sources/proxy; [one-host maintenance](proxmox-ha.md#node-maintenance) and [package updates](../02-software-intake/host-updates.md#how-are-proxmox-updates-installed) | Debian-derived appliance: use Proxmox release/bootloader/Ceph instructions; never the Linux leaf-host firewall role or a generic Debian release upgrade |
| Debian 12/13 VM | Owning tier `vm_instances`, inventory, service configuration and APT sources; [package workflow](#linux-updates) | Match signed loader/kernel and any custom module trust to the actual image; service support may require Debian 12 even when 13 boots |
| Rocky/Alma 9/10 VM | Same tier ownership; DNF repositories, SELinux labels/policy and the service's supported release | Rocky 10 x86 uses a v3 CPU baseline; do not infer another EL image's CPU support. Generic VM modules use `x86-64-v3`; validate all migration targets. Major upgrades require vendor-supported migration/rebuild paths [1] |
| Talos node | Owning tier `terraform/deployments/kubernetes/terraform.tfvars`, original `.terraform/state/talos/terraform.tfstate`, `secrets/talos/` and Talos API | No SSH/APT/DNF or leaf-host Ansible. Separate OS, Kubernetes and workload upgrades. Current whole-platform reference is Talos 1.13.x; see [release constraints](../../03-deployment/stage-04-kubernetes/procedures/talos-terraform.md) |
| bootc/other immutable image | Its selected image-build/update contract | Do not apply mutable-VM package commands to an image-managed installation |

**IaC now:** generic VM CPU/RAM/disk sizes, existing service-volume filesystem growth through
`data_volume`, template publication, Linux baseline/security reconciliation and selected Proxmox
HA policy. New generic VMs can select fresh TPM 2.0 state. The existing-VM controller recipe adds a
missing TPM during a controlled outage. Talos inputs declare node capacity, initial machine
configuration and release pins.
Native tools perform the OS/cluster upgrade, host migration, root/LVM growth and any separately
qualified firmware/encryption changes. These are not hidden operations of `deploy.sh --recipe maintenance`.

<a id="linux-updates"></a>

## How are Debian or Rocky/Alma packages updated?

**Run on:** one selected mutable Linux guest, with sudo and its independent console.
**Before starting:** pass the [upgrade gate](#upgrade-gate); retain package-source configuration,
application backups and the last accepted boot/recovery artifacts. Use currently commissioned
software intake or the stage's accepted independent sources; a future cache is not a prerequisite.

1. Inspect the installed OS, disk reserve and services. On the **selected guest**:

   ```bash
   cat /etc/os-release
   uname -r
   df -hT / /boot
   systemctl --failed
   systemctl list-timers --all
   ```

   Resolve full disks, unfinished package transactions and failed services first. Record existing
   automatic-update/reboot policy and coordinate it so it cannot compete with this window.
2. Preview the transaction using **only the matching distribution block**. On a **Debian guest**:

   ```bash
   sudo apt-get -o APT::Update::Error-Mode=any update
   ```

   Stop on repository refresh failure. Then, on **the same Debian guest**:

   ```bash
   apt-mark showhold
   sudo apt-get --simulate full-upgrade
   ```

   On a **Rocky/Alma guest** instead:

   ```bash
   sudo dnf repolist
   sudo dnf upgrade --refresh --assumeno
   ```

   DNF's declined transaction may exit nonzero; inspect its proposal and any actual error.
   Review removals, kernel/module changes, service restarts and configuration conflicts. Package
   holds/exclusions need an owner and review date; do not clear them indiscriminately. [2][3]
3. After accepting that proposal, install in the same window. On **the Debian guest**:

   ```bash
   sudo apt-get full-upgrade
   ```

   Or on **the Rocky/Alma guest**:

   ```bash
   sudo dnf upgrade --refresh
   ```

   These commands use native prompts. Resolve package configuration choices against owned inputs;
   preserve local changes that need reconciliation. A later repository change can alter a newly
   resolved transaction. These commands do not change the configured distribution major version.
4. Verify kernel/bootloader/module compatibility before a reboot. If Secure Boot is selected,
   preserve the signed boot chain and check [guest boot security](guest-hardening.md#linux-secure-boot).
   Do not disable SELinux or signature enforcement to make an updated driver/service work.
   Drain/fail over the selected service, or announce its outage. When ready, on **that guest**:

   ```bash
   sudo systemctl reboot
   ```

   Reconnect through the accepted access path and complete [post-change acceptance](#post-change)
   before changing its peer. Do not wait only for ping or SSH.
5. Keep a separately selected unattended policy. Debian uses APT periodic configuration and
   `unattended-upgrades`; EL uses DNF Automatic's `/etc/dnf/automatic.conf` and the selected timer.
   Inspect actual timers/configuration rather than assuming image defaults. Allowed origins,
   exclusions, notification/failure alerting, service restarts and reboot windows need qualification.
   The kit does not install a universal unattended patch/reboot policy. Proxmox hosts and Talos
   nodes keep their native lifecycle, even when a package download is allowed. [2][3]

**Failure:** stop the rollout. An old kernel may be selectable from the console, but package/database
changes may require application restore or clean-target VM recovery. A package downgrade or
`dnf history undo` is not a general rollback contract.

<a id="talos-updates"></a>

## How are Talos and Kubernetes updated?

**Run from:** the original owning tier root on the approved execution host, with its release-matched
`talosctl`, existing talosconfig/kubeconfig and retained node configuration. No fresh cluster init.
**Before starting:** supported adjacent release steps, approved installer image/schematic/extensions,
working API/time/DNS/registry access, healthy quorum, disruption budgets and independent backups.
Talos OS upgrades and Kubernetes upgrades are separate operations. [4]

1. Select a healthy control-plane address and credentials from this tier's original recovery set.
   The examples describe input format, not actual site values. On the **execution host**:

   ```bash
   read -r -p 'Healthy control-plane IP (example: 192.0.2.41): ' TALOS_CONTROL_PLANE
   export TALOSCONFIG="$PWD/secrets/talos/talosconfig"
   export KUBECONFIG="$PWD/secrets/talos/kubeconfig"
   talosctl --nodes "$TALOS_CONTROL_PLANE" health
   talosctl --nodes "$TALOS_CONTROL_PLANE" etcd members
   kubectl get nodes -o wide
   kubectl get pdb -A
   ```

   Resolve unhealthy members, storage/replication faults and blocked workloads first. Verify
   application backups/PVC recovery separately; an etcd snapshot does not contain their data.
2. Capture etcd off-node in a protected directory. On **that execution host**:

   ```bash
   umask 077
   install -d -m 0700 secrets/talos/maintenance
   TALOS_SNAPSHOT="secrets/talos/maintenance/etcd-$(date -u +%Y%m%dT%H%M%SZ).snapshot"
   talosctl --nodes "$TALOS_CONTROL_PLANE" etcd snapshot "$TALOS_SNAPSHOT"
   ```

   Copy it with the original machine secrets/configuration and tier state into the independently
   recoverable backup set. Verify access and the [cluster restore procedure](../06-resilience/recovery/original-state-etcd.md).
3. Select **one canary node** and its exact approved installer image, matching its current boot mode
   and required extensions. On **the execution host**, only after the canary is ready for disruption:

   ```bash
   read -r -p 'One canary Talos node IP (example: 192.0.2.44): ' TALOS_NODE
   read -r -p 'Exact approved installer reference from the release/schematic record: ' TALOS_INSTALLER
   talosctl --nodes "$TALOS_NODE" upgrade --image "$TALOS_INSTALLER"
   ```

   Stop on a health/eviction error; do not force past it. Follow release-specific ordering and
   verify the canary's OS version, readiness, storage, network, audit and application health before
   selecting another node. Upgrade control-plane members serially with quorum retained. For Talos
   1.13, review its documented upgrade API limitations when relying on `machine.install.extraKernelArgs`;
   choose the version-supported mitigation before the upgrade. This remains an operator decision. [4]
4. For a **separately approved Kubernetes upgrade**, inspect the target matrix and version-skew rules.
   This command upgrades the **whole cluster**; `--nodes` selects the control-plane API contact.
   From **the execution host**, choose the target version and preview its changes:

   ```bash
   read -r -p 'Exact approved Kubernetes version (example format: 1.35.0): ' KUBERNETES_VERSION
   talosctl --nodes "$TALOS_CONTROL_PLANE" upgrade-k8s --to "$KUBERNETES_VERSION" --dry-run
   ```

   Review component changes and bootstrap-manifest ownership/pruning before proceeding. After
   accepting the preview, on **the same execution host**:

   ```bash
   talosctl --nodes "$TALOS_CONTROL_PLANE" upgrade-k8s --to "$KUBERNETES_VERSION"
   ```

   Follow the command's health gates and the target release notes; verify CNI, CSI, admission,
   controllers and actual application transactions afterward. Do not combine this with an
   unqualified CNI/CSI or application schema upgrade. [5]
5. Reconcile owned release records and inputs: `cluster.talos_version`, `cluster.installer_image`,
   `cluster.kubernetes_version`, and retained `machine_config_patches` in
   `terraform/deployments/kubernetes/terraform.tfvars`. Keep one state owner. On **the owning tier root**:

   ```bash
   bash scripts/kubernetes-cluster.sh plan
   ```

   Review any proposed machine-configuration changes before applying. The root uses Talos `auto`
   apply mode and can reboot multiple nodes; a broad Terraform apply is not this serial rollout.
   Version-input changes alone do not upgrade installed nodes. Retain the original secrets and state.

**Failure:** stop before another node. Use the release-supported Talos rollback if still valid;
otherwise use original-identity recovery and application backups. Firmware/TPM/encryption failures
use the [boot recovery dependencies](guest-hardening.md#boot-recovery), not regenerated secrets.

<a id="boot-maintenance"></a>

## How are boot trust and TPM maintained?

For **physical Proxmox servers**, follow [host boot-security maintenance](proxmox-host-boot-security.md#maintenance-and-recovery)
before firmware, motherboard, trust-database or bootloader changes. Preserve every enrolled
consumer's independent recovery method; physical TPM keys are not a guest state-volume backup.
Rerun its read-only Ansible acceptance after the reboot before returning that host to service.

For **guests**, work from the owning tier using the original state and inputs. Retain console access and a
coherent backup of OS/data disks, EFI variables and TPM state before a boot-security change.

1. Inspect the installed boot profile and TPM through the controller's existing-VM recipe. Use its
   read-only `inspect` operation first. If the VM needs a TPM 2.0, follow the same recipe's private
   record, check and controlled-outage sequence. Record the observed TPM and reconcile the owning
   generic VM inputs through the common hardening procedure. [Existing-VM inspection and TPM addition](proxmox-guest-security.md)
2. For **Rocky/Alma or Debian**, patch the signed shim, bootloader and kernel through the normal
   package workflow. Include custom module signatures in the same review. After the canary's cold
   start, verify Secure Boot and TPM visibility using the common checks. Promote the accepted
   template revision for future guests. [Linux boot checks](guest-hardening.md#linux-secure-boot)
3. For **Talos**, retain the Secure Boot installer family, approved schematic/extensions and signing
   trust across OS upgrades. Use the serial upgrade procedure above, then verify `securitystate`
   and, when selected, the encrypted system volumes after the canary's installed-disk boot. Changes
   to its trust or TPM policy require the corresponding recovery test before the next node.
   [Talos boot checks](guest-hardening.md#talos-boot-security)
4. For **Proxmox-managed guest EFI**, review OVMF certificate updates and each affected VM's
   enrolled trust. For vendor-signed Linux guests on releases supporting it, use **VM > Hardware >
   EFI Disk > Disk Action > Enroll Updated Certificates** after testing the candidate guest's boot
   and recovery media. Confirm the action's activation/power-state requirements in that release.
   Enrollment can change TPM measurements, so use the encryption owner's recovery procedure when
   sealing is configured. Talos follows its own signed-media and trust procedure. [10][12]
5. For **USB HSM consumers**, retain the commissioned signing identity and wrapping material
   through device, connector and middleware changes. Use the same-key migration or replica
   procedure when expanding hardware. Verify signing through the consumer after the change.
   [HSM operations and expansion](../03-cryptography/usb-hsm.md)
6. Capture a new backup containing the accepted boot identity. Restore it on isolated capacity and
   verify boot, storage unlock where selected, API/service identity and the actual application
   transaction. Complete the common post-change checks before returning it to service.

For a guest with TPM-bound data, retain that VM's original TPM state during recovery. A replacement
TPM has a different identity. If the original state is lost, use the independently retained unlock
method or rebuild the node and recover its application data through the selected recovery path.
Keep those credentials and backups available while PKI, identity and Vault are unavailable.

<a id="resize-guests"></a>

## How are CPU, RAM and guest disks resized?

**Work from:** the guest owner's original tier/root/state, then its own OS or Talos API.
**Before starting:** capacity on every eligible target, a recoverable backup, preserved disk UUIDs,
and a window for stop/start where required. Grow only; disk shrinking needs a separate data migration.

1. Record current hardware and guest layout. On **a Linux guest**:

   ```bash
   lscpu
   free -m
   lsblk -o NAME,PATH,SIZE,TYPE,FSTYPE,UUID,MOUNTPOINTS
   findmnt
   df -hT
   ```

   Where LVM exists, also inspect `sudo pvs`, `sudo vgs` and `sudo lvs`. Record any partition,
   LUKS mapping and thin pool between the VM disk and filesystem; never assume `/dev/sda1` is root.
   On **the Talos execution host**, with the credentials and selected `TALOS_NODE` above, use:

   ```bash
   talosctl --nodes "$TALOS_NODE" get disks
   talosctl --nodes "$TALOS_NODE" get volumestatus
   ```

2. Edit only the existing host's capacity fields. Keep VMID, source, network/MAC and storage identity.

   | Guest owner | Exact mutable input |
   | --- | --- |
   | Generic Linux setup `terraform/deployments/<setup>/terraform.tfvars` | `vm_instances["<host>"].size`, `.cores`, `.memory` (MiB), `.disk_size_gb`; data disk `extra_disks` entry's `.size_gb`, retaining its `.interface` and datastore selection |
   | Talos root `terraform/deployments/kubernetes/terraform.tfvars` | `nodes["<host>"].size`, `.cores`, `.memory` (MiB), `.disk_size_gb`; no generic `extra_disks` input |

   Explicit CPU/RAM values override the size profile. Changing a profile does not size a disk.
   Avoid simultaneously changing firmware/controller or a datastore; those are different procedures.
3. For a **generic Linux setup**, select the original setup/environment from its recorded deployment.
   On **the owning tier root**, for example `<prefix>-tier-1/`:

   ```bash
   cat .deployment-setups
   read -r -p 'Original setup (example: intake): ' MAINT_SETUP
   read -r -p 'Original environment (blank for production): ' MAINT_ENV
   MAINT_ENV_ARGS=()
   if [ -n "$MAINT_ENV" ]; then MAINT_ENV_ARGS=(--env "$MAINT_ENV"); fi
   bash scripts/deploy.sh "$MAINT_SETUP" "${MAINT_ENV_ARGS[@]}" --terraform-only \
     --plan-only --plan-file .terraform/plans/maintenance.tfplan
   ```

   Require only the intended capacity changes, with no deletion/replacement, disk detach or boot
   policy drift. The setup plan covers every resource in that state. Drain/fail over affected
   services or accept their outage **before apply**: the provider's default `reboot_after_update`
   permits automatic reboot/power-off for hardware changes, and these roots do not override it. [11]
   On **the same tier root**, apply only the reviewed saved plan:

   ```bash
   bash scripts/deploy.sh "$MAINT_SETUP" "${MAINT_ENV_ARGS[@]}" --terraform-only \
     --plan-file .terraform/plans/maintenance.tfplan
   ```

   For **Talos**, use `bash scripts/kubernetes-cluster.sh plan` and, only for an accepted hardware-only
   plan, `bash scripts/kubernetes-cluster.sh apply`. Keep machine configuration unchanged. Schedule
   one node at a time; a source-wide apply has no rolling availability controller.
4. Check pending hardware in **Proxmox > VM > Hardware/Options** and activate changes with the
   required guest shutdown/start. Do not assume RAM/CPU hotplug. Talos uses fixed dedicated RAM
   and does not support memory hotplug/ballooning in this path. Drain a node before disruptive work;
   keep control-plane quorum. Verify the OS reports the new CPU/RAM/disk capacity. [6]
5. Grow the guest filesystem through its **actual owner**:

   - A service using Shared's [`data_volume`](../../../shared/ansible/roles/data_volume/tasks/prepare.yml)
     already uses native `community.general.filesystem` with `resizefs: true` and UUID guards for
     its supported dedicated whole-device ext4/XFS filesystem. Retain the existing device/path/UUID
     inputs; run that service's mapped [deployment recipe](ansible-recipes.md#recipe-map) with
     `--ansible-only`. Inspect its whole setup scope first. This grows the filesystem after Terraform
     grows the attached disk; it does not grow arbitrary guest partitions, LVM or LUKS mappings.
   - For an **unmanaged direct ext4 filesystem**, after its underlying device/partition is already
     larger, use the exact observed filesystem device. On **that Linux guest**:

     ```bash
     read -r -p 'Verified ext4 filesystem device from lsblk/findmnt (example: /dev/sda3): ' GROW_DEVICE
     sudo resize2fs "$GROW_DEVICE"
     ```

     For **XFS**, use the actual mounted filesystem path after its backing device is larger:

     ```bash
     read -r -p 'Verified XFS mount point from findmnt (example: /srv/data): ' GROW_MOUNT
     sudo xfs_growfs "$GROW_MOUNT"
     ```

     ext4/XFS are different tools. Partition/LUKS/PV/LV expansion must happen in the inspected
     layer order first, using that layout's reviewed native storage procedure. Those operations
     are not implemented by the generic VM resize. Do not reformat or blindly allocate all VG
     space. This procedure supports growth only. [7][8]
   - For **Talos**, VM disk capacity is IaC-managed; `VolumeConfig`/volume provisioning is a separate
     API contract. Provisioning edits do not resize an already-provisioned volume. Inspect its
     status and release-specific support; the kit provides no existing-volume resize controller.
     Qualify a native growth path or replace a node with a correctly sized one, preserving
     quorum/cluster identity and recovering its workloads. Increasing a VM disk does not itself
     prove more usable `EPHEMERAL` space, PVC capacity or CSI storage. [9]

6. Verify usable filesystem space, preserved UUID/mount options, service writes and backup coverage;
   complete [acceptance](#post-change). If growth fails, retain the larger virtual disk and diagnose
   the remaining layer. Do not reduce it to its old size or restore only a partition table.

<a id="post-change"></a>

## How is the changed component accepted?

1. Check actual installed versions and capacity, failed services and current-boot errors. Linux uses
   `uname -r`, `systemctl --failed`, `journalctl -p err -b --no-pager` and `df -hT`; Talos uses
   `talosctl version`, `talosctl health` and `kubectl get nodes`. Compare before/after observations.
2. Test the real service transaction and access denial, time/DNS, queues/replication, storage and
   local audit. Verify central telemetry only when already commissioned. Repeat selected
   [boot-security checks](guest-hardening.md#stage-checkpoint); do not infer Secure Boot from OVMF.
3. Run/verify the next backup and retain tested recovery artifacts/keys. A changed signed boot chain,
   trust database, encryption policy or backup format requires a fresh isolated restore qualification.
4. Record versions, changed inputs, exceptions and results in the private deployment/operating record.
   Re-enable the deliberately paused writers after an accepted no-surprise plan. Continue to another
   component only when service health and the selected production/recovery/HA gates pass.

<a id="replace-hardware"></a>

## How is failed or aging hardware replaced?

**Work from:** the Proxmox administration interface and the owning tier's original repository/state.
**Prerequisites:** independent console access, surviving capacity and verified recoverable backups.

1. Inventory the affected host, guests, disks, bridges/VLANs, storage paths and physical failure
   labels. Verify that surviving capacity can meet the selected quorum/availability contract.
   Preserve incident evidence before reusing disks if compromise is suspected.
2. Prepare the replacement through the [foundation](../../03-deployment/foundation/README.md) and
   [cluster HA procedure](../../03-deployment/foundation/proxmox/step-1b-cluster-ha.md). Verify API trust, storage,
   networking and recovery access before moving or restoring a guest.
3. Use Proxmox's native migration/backup restore with original guest identities and tier state.
   VM placement inputs are creation-time choices; changing `proxmox_node_name` is not an IaC
   migration command. Do not apply examples over original production resource maps.
   Preserve [EFI/TPM/encryption recovery dependencies](guest-hardening.md#boot-recovery), not only
   the OS disk. For host boot-disk replacement, inspect `proxmox-boot-tool status` and the actual
   GRUB/systemd-boot layout through the console; use Proxmox's matching ESP synchronization
   procedure. Host Secure Boot and guest Secure Boot have separate firmware/trust stores. [10]
4. Reconcile actual node topology/failure labels and storage attachment after moves. Test one
   affected service, SSO/access denial, intake and backups before retiring the old host or media.
   Update project records and preserve a replacement-host restore result.

For a failed host without automatic recovery, follow [host recovery](../06-resilience/recovery/host.md).
If the entire environment is lost, follow [platform recovery](../06-resilience/recovery/platform.md).
This section covers planned hardware replacement; failure recovery retains the original backup/state contract.

**Stop:** if quorum/capacity, storage attachment or migration acceptance fails. Keep the original
host/media intact until the replacement passes; suspected compromise uses clean-target recovery.

## References

Official constraints reviewed 2026-11-16; follow the installed release's documentation.

1. Rocky Linux, [Rocky 10 CPU and upgrade constraints](https://docs.rockylinux.org/latest/releases/release_notes/10_0/).
2. Debian, [package updates and unattended policy](https://www.debian.org/doc/manuals/debian-handbook/sect.regular-upgrades.en.html).
3. DNF upstream, [package commands](https://dnf.readthedocs.io/en/latest/command_ref.html) and
   [automatic updates](https://dnf.readthedocs.io/en/latest/automatic.html); inspect the actual EL release's shipped timers.
4. Talos 1.13, [OS upgrades and API limitations](https://docs.siderolabs.com/talos/v1.13/configure-your-talos-cluster/lifecycle-management/upgrading-talos).
5. Talos, [Kubernetes upgrades](https://docs.siderolabs.com/kubernetes-guides/advanced-guides/upgrading-kubernetes).
6. Talos 1.13, [Proxmox guest hardware constraints](https://docs.siderolabs.com/talos/v1.13/platform-specific-installations/virtualized-platforms/proxmox).
7. Debian/e2fsprogs, [resize2fs](https://manpages.debian.org/trixie/e2fsprogs/resize2fs.8.en.html).
8. Debian/xfsprogs, [xfs_growfs](https://manpages.debian.org/trixie/xfsprogs/xfs_growfs.8.en.html).
9. Talos 1.13, [system-volume provisioning](https://docs.siderolabs.com/talos/v1.13/configure-your-talos-cluster/storage-and-disk-management/disk-management/system).
10. Proxmox, [host bootloader and ESP management](https://github.com/proxmox/pve-docs/blob/master/system-booting.adoc).
11. BPG Proxmox provider 0.112.0, [VM update/reboot behavior](https://github.com/bpg/terraform-provider-proxmox/blob/v0.112.0/docs/resources/virtual_environment_vm.md).
12. Proxmox, [guest firmware trust, certificate enrollment and TPM state](https://github.com/proxmox/pve-docs/blob/master/qm.adoc#bios-and-uefi).
