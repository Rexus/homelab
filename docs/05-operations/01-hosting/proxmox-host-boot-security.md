# Proxmox host Secure Boot and TPM

Enable and verify boot security on the **physical Proxmox server** represented in the
[host-management figure](README.md#figure-host-management). Foundation calls this procedure at
[Step 11](../../03-deployment/foundation/proxmox/step-11-host-security.md).

| Layer | Selected control | What owns its state |
| --- | --- | --- |
| Physical server | UEFI Secure Boot and TPM 2.0 | Server firmware and its hardware/firmware TPM |
| Virtual machine | Guest UEFI and a unique vTPM | Guest EFI/TPM volumes on Proxmox storage; [guest procedure](proxmox-guest-security.md) |
| Application signing | Selected USB HSM and PKI policy | Separately commissioned devices/keys; [key custody](../03-cryptography/usb-hsm.md) |

An enabled host TPM supports machine-bound key operations and measured-boot consumers. It does
not automatically encrypt Proxmox disks, attest the host, create guest TPMs or protect CA keys.
This baseline verifies availability; key sealing requires a separately selected consumer and recovery plan.

## Contents

- [1. Prepare one host from bootstrap](#1-prepare-one-host-from-bootstrap)
- [2. Check the signed boot path](#2-check-the-signed-boot-path)
- [3. Enable TPM and Secure Boot in firmware](#3-enable-tpm-and-secure-boot-in-firmware)
- [4. Verify after boot](#4-verify-after-boot)
- [Maintenance and recovery](#maintenance-and-recovery)
- [References](#references)

## 1. Prepare one host from bootstrap

Retain host/guest backups and independent console access. Move or stop affected workloads through
[node maintenance](proxmox-ha.md#node-maintenance) before rebooting a host; preserve quorum and capacity.
Firmware activation uses the server console/vendor interface. The supplied Ansible operation
installs inspection tools and checks the OS; it changes no firmware, trust keys or TPM identity.

Before the first package operation, use **Proxmox > Node > Updates > Repositories** to confirm
the accepted Debian, PVE and selected Ceph sources. Enterprise sources need a valid subscription;
an unsubscribed lab can explicitly select the corresponding no-subscription sources and disable
unusable enterprise entries. Keep the installed release/track and signature verification. [4]
Foundation uses its accepted initial access path; the later cache is configured in Stage 1.

From **Tier 0 root on bootstrap**, select a registered host and its approved SSH account:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-inventory -i ansible/inventory/hosts.yml --graph hypervisors
read -r -p 'One inventory host from that list (example: pve01): ' PVE_HOST
read -r -p 'Its approved SSH account (example: root): ' PVE_SSH_USER
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  ansible/playbooks/maintenance/proxmox-boot-security.yml --limit "$PVE_HOST" \
  -e @ansible/group_vars/all.yml -e "ansible_user=$PVE_SSH_USER" \
  -e proxmox_host_boot_security_operation=prepare
```

**Expected:** exactly that physical Proxmox host, native `mokutil`, `efibootmgr` and `tpm2-tools`
installed through its accepted APT configuration, and current boot information. Disabled controls
can be prepared; acceptance happens in action 4. Missing sudo credentials use the same approved
become method as host management. No Proxmox API token or `.env.local` is needed.

## 2. Check the signed boot path

On **the selected Proxmox host's console as root**, inspect:

```bash
findmnt /
lsblk -o NAME,PATH,SIZE,FSTYPE,PARTTYPENAME,MOUNTPOINTS
proxmox-boot-tool status
efibootmgr -v
mokutil --sb-state
```

Choose **2a, 2b or 2c**, then continue at action 3. Use current approved updates before converting
an existing installation. Proxmox's supported signed path uses shim, signed GRUB and its signed
kernel; a systemd-boot or legacy-BIOS installation needs different preparation. [1]

### 2a. Fresh or already accepted signed UEFI installation

Current Proxmox installers include the signed packages. Retain the known-working signed `proxmox`
boot entry; verify actual enforcement in action 4. Continue at action 3. [1]

### 2b. Existing UEFI GRUB installation

After [approved host updates](../02-software-intake/host-updates.md#how-are-proxmox-updates-installed),
run on **that host's console as root**:

```bash
apt-get install proxmox-secure-boot-support
efibootmgr -v
```

Review the transaction first. Require the intended `proxmox` shim entry, normally
`\EFI\proxmox\shimx64.efi` on x86_64, and a signed Proxmox kernel. Review custom/DKMS driver
signatures too. Continue at action 3 only after this boot chain is ready. [1]

### 2c. Existing ZFS root with systemd-boot

First complete action 2b's package preparation. Identify **each existing EFI System Partition**
from `proxmox-boot-tool status` and the disk layout. On **the host console**, initialize GRUB on
one inspected, unmounted ESP at a time; repeat for its boot-mirror partner when present: [1]

```bash
read -r -p 'Verified existing ESP, not a whole disk (example: /dev/sda2): ' PVE_ESP
proxmox-boot-tool init "$PVE_ESP" grub
efibootmgr -v
proxmox-boot-tool status
```

Require the shim entry and every intended boot disk covered. This uses the existing ESP; do not
format it. A legacy-BIOS installation follows a separately planned UEFI host rebuild/migration,
with [host recovery](../06-resilience/recovery/host.md); do not simply disable CSM on that installation.

## 3. Enable TPM and Secure Boot in firmware

For a **fresh host**, select these before the Proxmox installation when supported. For an
**existing host**, use its prepared boot chain and scheduled shutdown/reboot. Open the server's
UEFI setup through its physical console or protected BMC console. Use its model-specific manual. [2][3]

| Firmware item | Select / retain |
| --- | --- |
| Boot mode | UEFI for the qualified installation; retain its prepared `proxmox` boot entry |
| TPM / Trusted Computing / Security Device Support | Enabled or On, with TPM 2.0 available to the OS |
| Discrete TPM, Intel PTT or AMD fTPM | Retain the commissioned implementation; on new hardware choose its supported TPM 2.0 option |
| TPM Clear / Reset / factory reset | Leave unchanged; activation requires no clearing of existing keys |
| Secure Boot | Enabled with the accepted vendor/third-party trust for the signed Linux chain; retain existing custom trust where selected |
| Firmware/BMC administration | Protected credentials and independent recovery access; restrict BMC to management paths |

For example, Dell PowerEdge commonly uses **System BIOS > System Security**; HPE ProLiant uses
**BIOS/Platform Configuration > Server Security > Trusted Platform Module options**. Labels vary.
On new stock firmware without enrolled trust, follow the vendor's standard-key provisioning path;
resetting an existing custom key database is a separate recovery-sensitive change.

Save and boot the prepared Proxmox entry. A TPM 1.2 device/mode is not proof of TPM 2.0. If absent,
check the server's supported module/firmware configuration; do not select an arbitrary TPM header module.
On an existing host, changing TPM mode or switching discrete/firmware TPMs is an identity migration:
retain and test enrolled consumers' recovery methods before following the vendor's transition procedure.

## 4. Verify after boot

From **the same Tier 0 root on bootstrap**, with the selected host/account above:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  ansible/playbooks/maintenance/proxmox-boot-security.yml --limit "$PVE_HOST" \
  -e @ansible/group_vars/all.yml -e "ansible_user=$PVE_SSH_USER" \
  -e proxmox_host_boot_security_operation=check
```

**Require:** enforced Secure Boot without shim bypass, and local TPM **2.0** fixed properties.
The recipe rejects guest/container targets; a nested Proxmox VM's vTPM is not the server chip.
It queries the local kernel TPM device, never a simulator/network TPM. `check` installs nothing.

Defaults require both controls. A reviewed hardware exception can set
`proxmox_host_require_secure_boot: false` or `proxmox_host_require_tpm: false` in that host's
inventory entry. Keep at least one required and record the exception; disabling a check does not
configure the missing control. Verify management, cluster/storage health and guest startup too.
Record firmware/bootloader versions, TPM manufacturer, observed checks and recovery owner privately.

## Maintenance and recovery

1. Before BIOS/BMC/TPM firmware, shim/GRUB/kernel, db/dbx or motherboard changes, retain host
   configuration, boot layout, tested recovery media and every enrolled consumer's independent
   recovery credentials. Physical TPM keys are not a guest `tpmstate0` volume in a Proxmox backup.
2. Change one host at a time through [node maintenance](proxmox-ha.md#node-maintenance). Retain the
   selected TPM implementation, hierarchy and approved trust. A firmware update or battery/default
   reset can change settings or measured-boot policy; follow the consumer/vendor recovery procedure.
3. Boot the accepted signed chain, rerun action 4, and verify storage, networking, quorum and
   workloads before resuming the next host. Test retained recovery media after trust/revocation changes.
4. On failure, use the independent console and last accepted boot/recovery procedure. TPM clearing
   is not a boot repair. Use a consumer's recovery key when required; suspected compromise follows
   [clean-target recovery](../06-resilience/recovery/host.md), rather than accepting an untrusted chain.

Continue with [common maintenance](maintenance.md#boot-maintenance). Guest EFI/vTPM recovery remains
under the [guest procedure](guest-hardening.md#boot-recovery); USB HSM key recovery keeps its own custody.

## References

1. Proxmox, [host bootloader, signed-boot preparation and existing-installation conversion](https://github.com/proxmox/pve-docs/blob/master/system-booting.adoc#secure-boot), checked 2026-11-16.
2. Dell, [PowerEdge System Security and TPM settings](https://www.dell.com/support/manuals/en-uk/poweredge-r6415/per6415_ism/system-security-settings-details?guid=guid-e217811b-ed01-40b2-ae8d-d2b0d9b3bcac&lang=en-us), checked 2026-11-16.
3. HPE, [enabling TPM 2.0 in server firmware](https://support.hpe.com/hpesc/public/docDisplay?docId=a00019109en_us&docLocale=en_US&page=GUID-A9FD5F2B-327F-40CF-AC65-BF1B0A30F315.html), checked 2026-11-16.
4. Proxmox, [repository selection and subscription requirements](https://github.com/proxmox/pve-docs/blob/master/pve-package-repos.adoc#repository-management), checked 2026-11-16.
