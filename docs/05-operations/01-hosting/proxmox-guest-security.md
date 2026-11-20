# Inspect boot security and add a VM TPM

Use this controller-owned recipe for **one existing Proxmox VM**. It inspects current/pending
configuration and can add a missing TPM 2.0 through the API, preserving EFI, disks, NIC/MAC and
the original power state. No SSH to the guest or Proxmox host is needed.

The [hardening guide](guest-hardening.md) owns the boot-control choices and guest acceptance.
For new VMs, select the boot profile before deployment; this recipe maintains existing guests.

## Contents

- [1. Initialize the maintenance inputs](#1-initialize-the-maintenance-inputs)
- [2. Inspect the selected VM](#2-inspect-the-selected-vm)
- [3. Prepare the private configuration record](#3-prepare-the-private-configuration-record)
- [4. Check the reviewed one-setting plan](#4-check-the-reviewed-one-setting-plan)
- [5. Apply and verify](#5-apply-and-verify)
- [Prove the controls inside a managed Linux guest](#prove-the-controls-inside-a-managed-linux-guest)
- [Secure Boot on an existing VM](#secure-boot-on-an-existing-vm)
- [Recovery and subsequent maintenance](#recovery-and-subsequent-maintenance)
- [References](#references)

## 1. Initialize the maintenance inputs

**Tier 0**, on the deployment controller:

```bash
bash scripts/init-local-files.sh --setup proxmox-guest-security
```

Edit **`ansible/group_vars/proxmox_guest_security.yml`**:

| Variable | What to enter |
| --- | --- |
| `proxmox_guest_security_vmid` | Integer VMID from the owning Terraform input or Proxmox VM summary. |
| `proxmox_guest_security_node` | Exact current Proxmox node name, for example `pve01`. |
| `proxmox_guest_security_name` | Exact VM name, for example `vm-1`. |
| `proxmox_guest_security_tpm_storage` | VM-image storage available on that node, for example `local-zfs`. |

Use the existing `.env.local` API identity. It needs `VM.Audit`, `VM.PowerMgmt`,
`VM.Config.Disk` on the selected VM, plus `Datastore.Audit` and `Datastore.AllocateSpace` on
the TPM storage. Keep token/user ACL intersection, CA trust and direct internal API routing intact.
Do not grant broad administrator access just for this operation. [1][2]

The play prepares its selected `community.proxmox` collection and Python clients through the
normal controller precheck. Use an [execution environment](../../08-reference/control-node-tooling.md#ansible-environment)
with **Ansible core 2.17 or newer**; the collection's selected version range requires it.
For disconnected use, pre-stage those
dependencies and set `CONTROL_NODE_COLLECTIONS_MODE=check`.

## 2. Inspect the selected VM

**Tier 0**, using the same deployment user and `.env.local`:

```bash
(
  set -a
  source .env.local
  set +a
  ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
    ansible/playbooks/deployment/proxmox-guest-security.yml \
    -e @ansible/group_vars/proxmox_guest_security.yml
)
```

Expected: the exact VM identity, current power state, BIOS, EFI and TPM references. **No VM change.**
The recipe rejects templates, locks, pending changes and identity mismatches. Its output describes
configured hardware; current Secure Boot enforcement still needs guest/firmware verification.

If TPM 2.0 already exists, retain it. TPM 1.2 is reported by inspection but rejected by the addition
path: this recipe does not reset, replace, move or convert existing TPM identity.

## 3. Prepare the private configuration record

**Controller**, create the record directory:

```bash
install -d -m 0700 "$HOME/.local/share/guest-security"
```

In **Tier 0 `ansible/group_vars/proxmox_guest_security.yml`**, set
`proxmox_guest_security_record` to a **new absolute filename** inside that directory, for example
`/home/operator/.local/share/guest-security/vm-1-before-tpm.json`.

**Tier 0**, capture the current hardware and power state:

```bash
(
  set -a
  source .env.local
  set +a
  ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
    ansible/playbooks/deployment/proxmox-guest-security.yml \
    -e @ansible/group_vars/proxmox_guest_security.yml \
    -e proxmox_guest_security_operation=prepare
)
```

Expected: a private JSON record and `proxmox_guest_security_record_sha256` to copy into the input
file after reviewing it. The record contains the **full configuration**, potentially including
cloud-init credentials; retain it privately outside Git. Prepare never overwrites an earlier record.

## 4. Check the reviewed one-setting plan

First retain a [complete independent VM backup](../06-resilience/backups/recovery-set.md), including
EFI, existing TPM state and every required disk. Have independent Proxmox console access. Record its
PBS snapshot or backup archive identifier in `proxmox_guest_security_backup_reference`, then set
`proxmox_guest_security_backup_retained: true`. An unrelated application export is not a VM backup.

When the VM has no TPM, reserve its outage and set `proxmox_guest_security_outage_approved: true`.
For an HA-managed VM, use the [HA workflow](proxmox-ha.md) to put **only that VM's request state in
`ignored`** during maintenance. This recipe never silently changes HA membership or policy.

**Tier 0**, preview against the accepted record:

```bash
(
  set -a
  source .env.local
  set +a
  ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
    ansible/playbooks/deployment/proxmox-guest-security.yml \
    -e @ansible/group_vars/proxmox_guest_security.yml \
    -e proxmox_guest_security_operation=check
)
```

Expected: **add missing TPM 2.0** on the selected storage, or **no change** for an existing TPM 2.0.
No cluster setting changes. A changed configuration/power state requires fresh inspection and a new
record. `check` is the recipe operation; Ansible's generic `--check` is only supported for `inspect`.

## 5. Apply and verify

**Tier 0**, during the approved outage:

```bash
(
  set -a
  source .env.local
  set +a
  ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
    ansible/playbooks/deployment/proxmox-guest-security.yml \
    -e @ansible/group_vars/proxmox_guest_security.yml \
    -e proxmox_guest_security_operation=apply
)
```

The play gracefully stops an originally running VM, rechecks its complete configuration and adds
**only `tpmstate0`** with the current Proxmox digest. It verifies every original setting before
restoring the original running state. A stopped VM remains stopped. It never forces a shutdown.
Repeating apply after a successful addition preserves the new TPM without another outage. [1][2]

Run the Linux proof below or the Talos checks in the [hardening guide](guest-hardening.md), plus
application acceptance. Capture a **new complete backup** with TPM and EFI state;
restore the accepted HA request state if applicable. TPM presence alone does not enable encryption,
remote attestation, HSM key custody or Secure Boot. Do not enable disk-key sealing until recovery
material is independently retained and a restore has been qualified.

## Prove the controls inside a managed Linux guest

Use the owning tier's normal Ansible inventory and config after its baseline and accepted package
supply have been deployed. **The controller manages guest access through Ansible**.
The same recipe is supplied in all three tiers. It rejects Proxmox hosts, Talos,
physical hosts and LXC/containers before package changes.

**Owning tier**, select the deployed Linux VM or inventory group in the existing setup vars file:

```yaml
guest_boot_security_hosts: vm-1
guest_boot_security_operation: apply
guest_boot_security_require_secure_boot: true
guest_boot_security_require_tpm: true
```

`apply` installs only the selected `mokutil`/`tpm2-tools` packages through native DNF or APT from the
guest's configured accepted repositories, then checks. `check` performs read-only probes and requires
the tools already installed. Select either control independently by setting its requirement to false.
No repository is enabled, verification disabled, boot key enrolled or encryption policy changed.

**Owning tier**, rerun the actual setup using its existing inputs and substitute only its playbook:

```bash
read -r -p 'Owning setup from .deployment-setups (example: foundation): ' BOOT_PROOF_SETUP
bash scripts/deploy.sh "$BOOT_PROOF_SETUP" --ansible-only \
  --playbook deployment/guest-boot-security.yml
```

Keep any `--ansible-vars` flag used by that setup's deployment guide; it supplies the existing host
addresses and service settings. For example, Foundation's CA path also loads
`--ansible-vars ansible/group_vars/issuer.yml`.

Expected: actual `mokutil --sb-state` reports **SecureBoot enabled** with no shim-validation bypass,
and `tpm2_getcap properties-fixed` reports TPM **2.0** through the guest's local kernel device. A VM
hardware checkbox alone cannot satisfy these checks. Changing `guest_boot_security_operation` to
`check` makes the same command a repeatable acceptance check, without package changes. [4][5]

## Secure Boot on an existing VM

**The TPM addition deliberately preserves the existing EFI variables disk.** Changing its
`pre_enrolled_keys` metadata does not prove that an existing guest has the needed trust or enforces
signed boot. No BIOS conversion, key deletion, EFI recreation or arbitrary key enrollment is hidden
in this operation. The native VM module's pre-enrollment option applies when creating EFI state. [1]

- For a qualified signed Linux image, use a **new VM with a freshly provisioned secure boot profile**
  through the [template/guest deployment route](../../03-deployment/foundation/proxmox/templates.md),
  restore application data, verify signed boot and then retire the old guest. Preserve its old VM
  until the replacement is accepted. Follow the [Linux qualification checks](guest-hardening.md#linux-secure-boot)
  for Rocky/Alma or Debian rather than flipping SeaBIOS to OVMF on an installed system.
- For a guest that already has the correct UEFI trust but firmware enforcement is disabled, inspect
  its actual OVMF setup and use its qualified OS/firmware procedure with console/recovery access.
  The controller inspection cannot infer that NVRAM state from `efidisk0` metadata.
- `qm enroll-efi-keys` is a Proxmox **certificate-maintenance** operation on supported releases; it
  is not a generic Secure Boot conversion API or automatic trust policy for every OS. Review updated
  trust and TPM-sealed disk recovery before changing certificates. [3]

Use the [Talos boot-security path](guest-hardening.md#talos-boot-security) for signed media and its
own trust chain. Protect the Proxmox host as well: a software vTPM is controlled by that hypervisor,
while the USB HSM has a separate hardware custody role.

## Recovery and subsequent maintenance

If shutdown, allocation or verification fails, the play stops. It does **not** delete a new TPM,
rewrite EFI or force the VM back on. Inspect its console, task log and private record first. A failed
graceful shutdown can leave the VM running; an allocation/verification failure can leave it stopped.

Reinspect before retrying. An interrupted addition that left the accepted TPM 2.0 as the **only**
configuration change is recognized and retained; it does not authorize another stop/start. If power
state differs from the original record, resolve it deliberately through Proxmox and prepare a new
record. Existing prepared TPM identity must always match exactly.

Never delete `tpmstate0` or EFI as a routine rollback. Restore the coherent VM backup if its boot
identity must be recovered. Keep Terraform state and owned VMID/MAC inputs; this maintenance play
does not import or forget resources. The generic VM module preserves adopted TPM/EFI state, while
the [maintenance guide](maintenance.md) covers later CPU/RAM, disk and OS updates.

## References

1. [Native VM module, TPM and EFI options](https://docs.ansible.com/projects/ansible/latest/collections/community/proxmox/proxmox_kvm_module.html).
2. [Proxmox VM configuration API implementation](https://github.com/proxmox/qemu-server/blob/master/src/PVE/API2/Qemu.pm).
3. [Proxmox EFI certificate-maintenance implementation](https://github.com/proxmox/qemu-server/blob/master/src/PVE/CLI/qm.pm).
4. [mokutil's actual Secure Boot and shim validation checks](https://github.com/lcp/mokutil/blob/master/src/mokutil.c).
5. [Native TPM property inspection](https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_getcap.1/).
