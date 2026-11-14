# Change a VMID with a full clone

Copy an existing VM to a new VMID, retain its original network-interface settings and
cut over with the original stopped. Keep the old VM until validation and ownership updates finish.

<a id="figure-vmid-cutover"></a>

![Full clone with stopped original and retained NIC settings](../../08-reference/diagrams/vmid-cutover.svg)

*Figure: Manual full-clone cutover. Current disks become independent copies; the original NIC settings
are restored before first boot. Only the replacement runs with that network identity.*

**Run on:** the source Proxmox host's root Bash shell, opened from an independent workstation or console.
Do not run the host session through the old VM: stopping it would disconnect that session.
Keep the same host maintenance shell for Steps 1–7 and 10.
**Scope:** an existing QEMU VM, cloned on the same host; not a template or LXC.
For Terraform-managed Linux VMs, Step 8b rebinds the existing resource. Kubernetes and templates
need their own state/adoption procedures; do not apply the Linux resource recipe to those roots.

Proxmox normally assigns a new MAC during cloning. Step 6 restores the complete `netN` values,
including model, MAC, bridge/VNet, VLAN, MTU and firewall options. Firmware UUIDs still change. [1][2]

> [!CAUTION]
> **Account for every data disk before starting or deleting either VM.** A full clone copies attached
> Proxmox-managed VM disks; external mounts, passthrough storage and detached `unusedN` volumes need
> separate handling. Keep filesystem UUID guards for preserved data. Clearing a guard does not restore,
> reattach or erase a disk. Choose the [data-disk path](vmid-data-disks.md) before Step 5.

## Steps

1. [Select the VM and free destination](#1-select-the-vm-and-free-destination).
2. [Pause writers and take backups](#2-pause-writers-and-take-backups).
3. [Record the configuration](#3-record-the-configuration).
4. [Stop the original](#4-stop-the-original).
5. [Create the full clone](#5-create-the-full-clone).
6. [Restore the original NIC settings](#6-restore-the-original-nic-settings).
7. [Start and verify the replacement](#7-start-and-verify-the-replacement).
8. [Update manual or Terraform ownership](#8-update-ownership).
9. [Update jobs and records](#9-update-jobs-and-records).
10. [Retain or retire the original](#10-retain-or-retire-the-original).

## 1. Select the VM and free destination

On **the source Proxmox host**, run this command alone and wait for `vmid-maintenance>`:

```bash
PS1='vmid-maintenance> ' bash --noprofile --norc -euo pipefail
```

`PS1` only labels the command prompt; it does not configure the host or VM.
Errors stop this child shell and return to the normal host prompt without closing SSH.
Restart here after a failure; do not continue later blocks from the parent prompt.

At **the `vmid-maintenance>` prompt**, enter the actual values:

```bash
read -r -p 'Old VMID: ' OLD_VMID
read -r -p 'New VMID: ' NEW_VMID
read -r -p 'Target VM-disk datastore ID: ' VM_STORAGE
test "$OLD_VMID" != "$NEW_VMID"
pvesh get /cluster/resources --type vm
pvesm status --content images
qm config "$OLD_VMID" --current 1
```

Confirm the original VM, a cluster-wide unused destination ID and enough VM-image storage for
every attached VM disk. Use the [VMID convention](../../02-conventions/vmid-convention.md).
Resolve pending configuration changes first. Review external mounts and passthrough devices separately.

If another VM occupies the destination ID, complete its move and retire its original first.
A stopped rollback VM still occupies its ID. Select the actual owning repository for each VM.

## 2. Pause writers and take backups

Pause the VM's Terraform/Ansible/CI writers and scheduled application jobs. Take a verified
[independent VM and application backup](../06-resilience/backups/virtual-machines.md), including
every workspace/data disk. Preserve the owning deployment's original state and inputs.

For an **HA-managed VM**, first record its resource/rules and set its requested state to **stopped**
through [HA operations](proxmox-ha.md). Keep the old resource stopped until it is retired;
disabling guest autostart alone does not stop HA from starting it.

## 3. Record the configuration

On **the same Proxmox host**, save a private recovery record:

```bash
umask 077
VM_RECORD="/root/vmid-${OLD_VMID}-to-${NEW_VMID}-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$VM_RECORD"
qm config "$OLD_VMID" --current 1 > "$VM_RECORD/original.conf"
sed -n '/^net[0-9][0-9]*: /p' "$VM_RECORD/original.conf" > "$VM_RECORD/network.conf"
VM_NAME=$(sed -n 's/^name: //p' "$VM_RECORD/original.conf")
cat "$VM_RECORD/network.conf"
```

Record the current IP/DHCP reservation and SSH host-key fingerprint too. The configuration records
original startup settings and NICs; it is not a disk backup.

## 4. Stop the original

On **the same Proxmox host**:

```bash
qm set "$OLD_VMID" --onboot 0
qm shutdown "$OLD_VMID" --timeout 180
qm status "$OLD_VMID"
```

**Expected:** `status: stopped`. If shutdown times out, diagnose it through the console;
do not continue with a running source. The original remains stopped throughout cutover.

## 5. Create the full clone

Choose how to handle data before continuing:

| Choice | Action |
| --- | --- |
| 5a. Preserve the copied disks | Run the full clone below; [verify each copied volume](vmid-data-disks.md#1-preserve-the-copied-disks) |
| 5b. Keep an original volume | Clone below, then [reassign that data disk](vmid-data-disks.md#2-reassign-an-original-data-disk) before Step 6 |
| 5c. Discard data and rebuild | Follow [deliberate IaC recreation](vmid-data-disks.md#3-recreate-disposable-data-through-iac) instead of cloning; this is a fresh deployment |

On **the same Proxmox host**:

```bash
test "$(qm status "$OLD_VMID")" = 'status: stopped'
qm clone "$OLD_VMID" "$NEW_VMID" --full 1 --name "$VM_NAME" --storage "$VM_STORAGE"
qm set "$NEW_VMID" --onboot 0
qm status "$NEW_VMID"
qm config "$NEW_VMID" --current 1
```

Wait for a successful clone task and require the replacement to remain stopped. Check every expected
disk, including EFI/Cloud-Init and extra workspace/data disks. A full clone copies current attached VM
disk contents, not snapshot history or detached `unusedN` volumes. [1][2]

## 6. Restore the original NIC settings

On **the same Proxmox host**, restore every recorded interface before first boot:

```bash
test "$(qm status "$OLD_VMID")" = 'status: stopped'
test "$(qm status "$NEW_VMID")" = 'status: stopped'
while IFS= read -r NIC_LINE; do
  NIC_NAME="${NIC_LINE%%:*}"
  NIC_CONFIG="${NIC_LINE#*: }"
  qm set "$NEW_VMID" "--$NIC_NAME" "$NIC_CONFIG"
done < "$VM_RECORD/network.conf"
qm config "$NEW_VMID" --current 1 | sed -n '/^net[0-9][0-9]*: /p' > "$VM_RECORD/replacement-network.conf"
diff -u "$VM_RECORD/network.conf" "$VM_RECORD/replacement-network.conf"
```

**Expected:** no diff. This keeps complete interface settings rather than rebuilding `net0` from
only a MAC. In **replacement VM > Firewall**, also compare VM-level rules, aliases and IP sets.

## 7. Start and verify the replacement

On **the same Proxmox host**:

```bash
test "$(qm status "$OLD_VMID")" = 'status: stopped'
qm start "$NEW_VMID"
qm status "$NEW_VMID"
```

In **the replacement's console**, verify the expected hostname, IP, NICs, disks/mounts and service.
From **an approved workstation**, verify SSH against the recorded host key and test the service endpoint.
If first-boot initialization regenerated a key, verify it through the independent console before accepting it.
DHCP clients using other identifiers can need a reservation adjustment despite an unchanged MAC.
Check any first-boot Cloud-Init behavior or hardware-bound settings before accepting the copy.

Verify the guest's persistent mounts, volume UUIDs and application data. Run its owning operations
guide's service checks; a booted guest or a successful SSH login alone does not validate the workload.
Keep the original filesystem UUID pin and the matching stable device path for preserved volumes;
the [disk identity guide](vmid-data-disks.md#1-preserve-the-copied-disks) distinguishes them from Proxmox volume IDs.

## 8. Update ownership

### 8a. Manually managed VM

Update the local platform/recovery records with the new VMID. A VM outside Terraform has no VM
resource to import. If it holds Terraform states for other infrastructure, retain those files
unchanged; moving the execution host does not rebind the resources it manages. Continue to Step 9.

### 8b. Terraform-managed Linux VM

> [!IMPORTANT]
> Editing `vm_id` alone does not adopt the clone. If state still shows the old VMID, Terraform can
> propose destroying the old VM and creating another one. Decline that apply and complete adoption first.

On **the owning tier's original checkout**, follow the numbered
[VM state rebinding instructions](../06-resilience/recovery/terraform-import.md) from Step 1 through Step 13.
They include a copyable command and expected result for each action:

| Action | Exact step |
| --- | --- |
| Prepare the original state, inputs and credentials | [Steps 1–7](../06-resilience/recovery/terraform-import.md#1-open-the-maintenance-shell) |
| Preview the selected old binding | [Step 8](../06-resilience/recovery/terraform-import.md#8-enter-the-new-identity-and-preview-removal) |
| Remove only that Terraform binding | [Step 9](../06-resilience/recovery/terraform-import.md#9-remove-the-old-state-binding) |
| Import the already created new VM at the same address | [Step 10](../06-resilience/recovery/terraform-import.md#10-import-the-existing-replacement) |
| Verify the new VMID and return here | [Steps 11–13](../06-resilience/recovery/terraform-import.md#11-review-a-fresh-plan) |

The removal command changes Terraform's binding only. It does not delete either VM or its disks. [3]

Select the VM's actual setup, group-vars file and resource address from the original state.
Set the new VMID and retain its original template selection; the current module preserves imported boot hardware.
Retain its logical resource key, IP and disk declarations.
Keep preserved volumes' existing UUID pins; use the actual service input names from the
[storage-input convention](../../02-conventions/iac-inputs.md#storage-identity-inputs).
Return here at Step 9 after a plan confirms the new binding without unexpected creation,
destruction or disk replacement.
Ensure the deployment's API identity can inspect the new VMID before import; extend any old-ID-only
permission scope deliberately while leaving scheduled writers paused.

## 9. Update jobs and records

In **Proxmox and the owning configuration**, update VMID-specific selections:

- Backup jobs, monitoring targets, VM-scoped API permissions and resource-pool membership.
- Selected HA resources and affinity rules; keep the original stopped and retire its old membership.
- Recovery records and the new VM's **Start at boot** setting, using `original.conf` as the reference.

Take a new accepted independent backup and preserve the reconciled Terraform state. Resume only the
authorized writer. The MAC/IP can stay unchanged; these VMID-specific selections still need review.

## 10. Retain or retire the original

### 10a. Keep a rollback VM

Leave the original stopped, with **Start at boot** off and no HA rule able to start it.
Its VMID remains occupied. Never run both copies with the same MAC/IP.

### 10b. Release the old VMID

After validation, state rebinding and a verified independent backup, remove the original through
**Proxmox > original VM > More > Remove**. Confirm its old VMID and disks before removal.
For a reassigned disk, verify that its current owner is the replacement before removing the original.
Keep the backup; deleting the original disks ends the instant rollback path.
Only then may another VM use the released ID.

After the selected host task finishes, run **at the `vmid-maintenance>` prompt**:

```bash
exit
```

This returns to the parent host shell; it does not end the SSH connection.

## Roll back before retiring the original

If an original data disk was reassigned, [move it back while both VMs are stopped](vmid-data-disks.md#roll-back-a-reassigned-disk)
before starting the original. It no longer has that disk after reassignment.

1. Pause writers again. Shut down the replacement and keep its autostart/HA membership disabled.
2. Require it to be stopped before starting the original. Restore the original's recorded startup/HA
   settings only when it is again the accepted VM.
3. For a Terraform-managed VM already rebound, restore the old configured VMID and repeat the
   [single-resource rebinding procedure](../06-resilience/recovery/terraform-import.md) with the original node/ID.
   Keep the rest of the current state; do not overwrite it with a whole-state backup.
4. Recheck service access, mounts and data; account for writes made to the replacement since cutover.
   Returning to the original does not copy those writes back. Resume one writer after its plan is accepted.

## References

Sources checked 2026-11-14.

1. [Proxmox copies and clones: independent disks, snapshots and regenerated MAC/BIOS UUID](https://github.com/proxmox/pve-docs/blob/master/qm.adoc#copies-and-clones).
2. [Proxmox clone/configuration API: full copy, NIC values, unused volumes and firewall configuration](https://github.com/proxmox/qemu-server/blob/master/src/PVE/API2/Qemu.pm).
3. [Terraform state removal changes the binding without deleting the remote object](https://developer.hashicorp.com/terraform/cli/commands/state/rm).
