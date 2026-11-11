# Recover the bootstrap execution host

Restore the machine that holds provisioning tools and the original tier-owned inputs/state.
Use its VM backup before recovering dependent services; GitLab, SSO and Vault are not prerequisites.

**Run on:** an independent privileged workstation, the replacement Proxmox host, then the restored bootstrap.
**Required backup set:** [bootstrap and provisioning records](../backups/recovery-set.md).
**Design:** [independent execution](../../../01-architecture/04-hosting/02-provisioning.md#execution-contexts).

## Steps

1. [Fence the old bootstrap](#1-fence-the-old-bootstrap).
2. [Obtain the backup and independent credentials](#2-obtain-the-backup-and-independent-credentials).
3. [Select the replacement Proxmox host](#3-select-the-replacement-proxmox-host).
4. [Reconnect the backup target](#4-reconnect-the-backup-target).
5. [Restore the stopped VM](#5-restore-the-stopped-vm).
6. [Check the workspace disks](#6-check-the-workspace-disks).
7. [Select the authoritative workspace copy](#7-select-the-authoritative-workspace-copy).
8. [Restore the original inputs and state](#8-restore-the-original-inputs-and-state).
9. [Quarantine old plans and caches](#9-quarantine-old-plans-and-caches).
10. [Verify the tools](#10-verify-the-tools).
11. [Verify access and state](#11-verify-access-and-state).
12. [Return to service recovery](#12-return-to-service-recovery).

<a id="1-prepare-an-independent-restore-path"></a>

## 1. Fence the old bootstrap

Stop its runner/jobs and prevent the old VM from returning while its replacement is active.
Only one execution host may write each state.

## 2. Obtain the backup and independent credentials

On **the independent privileged workstation**, obtain the selected backup, its integrity record,
separate NAS/PBS credentials and decryption keys. Do not obtain the only key from the Vault being restored.

## 3. Select the replacement Proxmox host

| Available capacity | Next action |
| --- | --- |
| An accepted Proxmox host survives | Continue to Step 4 |
| No hypervisor survives | Prepare **one** host with [foundation host/network setup](../../../03-deployment/foundation/proxmox/README.md#first-deployment-order), then return to Step 4 |

## 4. Reconnect the backup target

On **the replacement Proxmox host**, reconnect the existing
[backup target](../backups/virtual-machines.md#quick-steps) using its recorded interface and independently
verified trust. Do not initialize or format surviving backup storage.

<a id="2-restore-the-bootstrap-vm"></a>

## 5. Restore the stopped VM

In **Proxmox > backup storage > Backups**, select the recorded bootstrap backup and **Restore**.

| Restore setting | Enter/check |
| --- | --- |
| Node and live storage | Accepted replacement host and actual VM-disk datastore; backup storage remains the source |
| VMID | Original ID only if free and the old VM is fenced; otherwise use an unused recovery ID |
| Disks | Every disk required by the selected layout: OS, any separate workspace and additional root-LVM PVs |
| Start after restore / Live restore | Off; inspect the recovered configuration before boot |
| Network | Disconnected or isolated recovery network until duplicate-address and job checks pass |

Use the [native VM restore procedure](../backups/virtual-machines.md#restore-a-test-vm) for the GUI/CLI
mechanics. A full VM backup restores disks without the original cloud-image template. [1]
The restored hostname is the one recorded in the backup; `boot-1` is the starter example,
not a recovery-time rename. The manually created bootstrap is outside the supplied Terraform roots.

## 6. Check the workspace disks

Boot through **the restored bootstrap's console**. Keep jobs paused and confirm its selected workspace
filesystem before opening repositories. Substitute the recorded workspace path if different:

```bash
findmnt -T /srv/tier0
df -h / /srv/tier0
```

**Separate workspace disk:** require the recorded data filesystem rather than an OS-disk fallback.

**Root-LVM layout:** `/srv/tier0` is deliberately on root. On **the restored bootstrap**, check every
recorded PV and the root LV:

```bash
sudo pvs
sudo lvs -o lv_path,devices
```

If `/home` uses the optional bind mount, verify the [home layout checks](../../../03-deployment/foundation/bootstrap/step-3c-bootstrap-home.md).
All selected layout checks must pass before Step 7. See the
[LVM layout](../../../03-deployment/foundation/bootstrap/step-3b-bootstrap-lvm.md) if needed.

<a id="3-recover-the-authoritative-workspace"></a>

## 7. Select the authoritative workspace copy

Compare the bootstrap backup's date with the separately protected provisioning-input backup.
A recent VM copy does not automatically contain the latest state from a later runner.
Preserve extracted and VM-backup copies separately while resolving which set is authoritative.

## 8. Restore the original inputs and state

On **the restored bootstrap**, recover the recorded code revision and sibling Tier 0/1/2/Shared layout.
Follow [input custody](input-custody.md) and
[original-state recovery](original-state-etcd.md#recover-original-state) to restore the latest coherent
original state, ignored inventory/group vars/tfvars, credentials and cluster secrets.

## 9. Quarantine old plans and caches

Retain `.terraform/state/` and dependency lockfiles. Quarantine old saved plans and initialization caches
before reinitializing against the replacement platform. Do not move the whole `.terraform/` out of active
use on this recovery path; [state handling](../../01-hosting/terraform-state.md) distinguishes those files.

## 10. Verify the tools

On **the restored bootstrap**, compare installed tools with the recorded versions. Rebuild
unavailable/non-portable Python environments from the
[retained offline bundle](../../../03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md).
Do not generate a replacement collection or new service identities.

<a id="4-verify-access-before-enabling-writers"></a>

## 11. Verify access and state

| Check | Required result |
| --- | --- |
| Proxmox endpoint and CA | Actual replacement endpoint verifies against independently accepted trust; install a new cluster CA if the cluster was rebuilt |
| API/SSH credentials | Scoped local recovery access works without SSO; recreated Proxmox installations may need newly issued API tokens |
| Network/storage references | Actual bridges/VNets, node and datastore IDs match the recovery mapping |
| Original state | Correct owning tier, setup, environment, lineage and accepted backup age |
| Offline tools/artifacts | Required providers, packages, collections and images are available through the approved path |

Use [Proxmox trust](../../01-hosting/proxmox-tls.md) and
[API access](../../../03-deployment/foundation/proxmox/api-access.md) for changed endpoint credentials.
Do not apply against VMs still awaiting restoration: a missing VM can be proposed as a new empty guest.

## 12. Return to service recovery

Continue with the originating [one-VM](virtual-machines.md), [host](host.md) or
[whole-platform](platform.md) recovery task. Re-enable writers only after its state and service checks pass.
Back up the recovered bootstrap/workspace again and qualify its independent restore path.

## References

1. [Proxmox VM backup and restore](https://github.com/proxmox/pve-docs/blob/master/vzdump.adoc).
