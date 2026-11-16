# Step 11: Secure the Proxmox hosts

**Continue from:** [Foundation Step 11](../README.md#step-11-secure-the-foundation).
**Return:** [Foundation Step 11](../README.md#step-11-secure-the-foundation) to finish the
bootstrap/template checkpoint, then continue to Stage 1.
**Expected result:** the hosts in [Foundation Figure 1](../README.md#figure-foundation-ready)
have protected administration, verified signed boot and an enabled TPM 2.0 where supported.
Record an explicit hardware exception when a host cannot meet that baseline.

**Work from:** `<prefix>-tier-0/` on bootstrap, plus each server's independent firmware console.
The [host-management setup](../../../05-operations/01-hosting/README.md) must already provide
the real `hypervisors` inventory, approved SSH identity and independent recovery access.
Use the currently accepted initial package sources; the future cache/PKI/IdP are not prerequisites.

> [!TIP]
> **Recovery and maintenance:**
> [Maintain physical host firmware/TPM](../../../05-operations/01-hosting/proxmox-host-boot-security.md#maintenance-and-recovery)
> or [recover a guest's separate EFI/TPM state](../../../05-operations/01-hosting/guest-hardening.md#boot-recovery).

## 1. Finish management protection

Complete [Proxmox access hardening](../../../05-operations/01-hosting/proxmox-hardening.md):
administrative source restrictions, fresh allowed/denied access tests and human-account MFA.
Verify [API TLS trust](../../../05-operations/01-hosting/proxmox-tls.md) and retain the
[scoped automation roles](api-access.md). Keep BMC/firmware credentials and emergency access
independent of the hosted services.

## 2. Prepare and enable physical host boot security

Follow [physical host Secure Boot and TPM](../../../05-operations/01-hosting/proxmox-host-boot-security.md),
actions **1–4**, for each server:

1. Run its Ansible `prepare` operation from bootstrap to install native inspection tools.
2. Identify the current bootloader and finish any required signed-boot preparation.
3. In the server firmware, enable its existing TPM 2.0 and the qualified Secure Boot chain.
4. Run the read-only Ansible `check` operation after the server boots.

For fresh hosts, choose UEFI, signed boot and TPM before installation when possible. Existing
hosts need their inspected boot layout and a maintenance window; BIOS mode is not changed by
the playbook. Keep clustered hosts on the [one-node maintenance path](../../../05-operations/01-hosting/proxmox-ha.md#node-maintenance).

The **physical server TPM**, each **guest vTPM** and **USB HSM signing devices** have separate
identities and consumers. Host TPM activation creates no guest TPM, disk-encryption enrollment
or application signing key.

## 3. Retain recovery and close Foundation

Record host boot mode, signed bootloader, observed Secure Boot/TPM checks, firmware version,
hardware exceptions and recovery owner in the private platform record. Preserve host configuration,
boot/storage layout, independent credentials and any enrolled consumer's recovery keys through
the [recovery-set routine](../../../05-operations/06-resilience/backups/recovery-set.md).

Return to [Foundation Step 11](../README.md#step-11-secure-the-foundation) for bootstrap/template
acceptance. Firmware, bootloader and TPM changes later follow the same
[host boot-security maintenance](../../../05-operations/01-hosting/proxmox-host-boot-security.md#maintenance-and-recovery)
and [common maintenance guide](../../../05-operations/01-hosting/maintenance.md#boot-maintenance).
