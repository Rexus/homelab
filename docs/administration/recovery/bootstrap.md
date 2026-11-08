# Recover the bootstrap execution host

Restore the machine that holds provisioning tools and the original tier-owned inputs/state.
Use its VM backup before recovering dependent services; GitLab, SSO and Vault are not prerequisites.

**Run on:** an independent privileged workstation, the replacement Proxmox host, then the restored bootstrap.
**Required backup set:** [bootstrap and provisioning records](../backups/recovery-set.md).
**Design:** [independent execution](../../architecture/hosting/provisioning.md#execution-contexts).

## Steps

1. [Prepare an independent restore path](#1-prepare-an-independent-restore-path).
2. [Restore the bootstrap VM](#2-restore-the-bootstrap-vm).
3. [Recover the authoritative workspace](#3-recover-the-authoritative-workspace).
4. [Verify access before enabling writers](#4-verify-access-before-enabling-writers).

## 1. Prepare an independent restore path

1. Fence the old bootstrap and pause its runner/jobs. Only one execution host may write each state.
2. From the independent workstation, obtain the selected backup, its integrity record and separate
   NAS/PBS credentials and decryption keys. Do not obtain the only key from the Vault being restored.
3. If no hypervisor survives, first prepare **one** replacement host using
   [foundation host/network setup](../../deployment/foundation/proxmox/README.md#first-deployment-order).
   This manual work precedes recovery of the bootstrap VM.
4. Reconnect the existing [backup target](../backups/virtual-machines.md#quick-steps) using its recorded
   interface and independently verified trust. Do not initialize or format surviving backup storage.

## 2. Restore the bootstrap VM

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

Boot through the console. Confirm the selected workspace filesystem before opening its repositories:

```bash
# Run on the restored bootstrap. Substitute its recorded workspace mount if different.
findmnt -T /srv/tier0
df -h / /srv/tier0
```

For a separate workspace disk, require the recorded data filesystem rather than an OS-disk fallback.
For the [root-LVM layout](../../deployment/foundation/proxmox/bootstrap-lvm.md), `/srv/tier0` is deliberately
on root: verify the recorded root LV and all of its PV disks with `sudo pvs` and `sudo lvs -o lv_path,devices`.
If `/home` uses the optional bind mount, verify the [home layout checks](../../deployment/foundation/proxmox/bootstrap-home.md).
Keep jobs paused even when the restored login works.

## 3. Recover the authoritative workspace

1. Compare the bootstrap backup's date with the separately protected provisioning-input backup.
   A recent VM copy does not automatically contain the latest state from a later runner.
2. Recover the recorded code revision and sibling Tier 0/1/2/Shared layout. Restore the latest coherent
   original state, ignored inventory/group vars/tfvars, credentials and cluster secrets through
   [input custody](input-custody.md) and [original-state recovery](original-state-etcd.md#recover-original-state).
   Preserve extracted and VM-backup copies separately when resolving which set is authoritative.
3. Retain `.terraform/state/` and dependency lockfiles. Quarantine old saved plans and initialization
   caches before reinitializing against the replacement platform; do not move the whole `.terraform/`
   out of active use on this recovery path. [State handling](../terraform-state.md) explains the distinction.
4. Verify the installed tools match the recorded versions. Rebuild unavailable/non-portable Python
   environments from the [retained offline bundle](../../deployment/foundation/proxmox/bootstrap-offline.md),
   without generating a replacement collection or new service identities.

## 4. Verify access before enabling writers

| Check | Required result |
| --- | --- |
| Proxmox endpoint and CA | Actual replacement endpoint verifies against independently accepted trust; install a new cluster CA if the cluster was rebuilt |
| API/SSH credentials | Scoped local recovery access works without SSO; recreated Proxmox installations may need newly issued API tokens |
| Network/storage references | Actual bridges/VNets, node and datastore IDs match the recovery mapping |
| Original state | Correct owning tier, setup, environment, lineage and accepted backup age |
| Offline tools/artifacts | Required providers, packages, collections and images are available through the approved path |

Use [Proxmox trust](../hosts/proxmox-tls.md) and
[API access](../../deployment/foundation/proxmox/api-access.md) for changed endpoint credentials.
Do not apply against VMs still awaiting restoration: a missing VM can be proposed as a new empty guest.

**Continue:** return to [one-VM recovery](virtual-machines.md), [host recovery](host.md) or
[whole-platform recovery](platform.md). Re-enable writers only after their state and service checks pass.
Back up the recovered bootstrap/workspace again and qualify its independent restore path.

## References

1. [Proxmox VM backup and restore](https://github.com/proxmox/pve-docs/blob/master/vzdump.adoc).
