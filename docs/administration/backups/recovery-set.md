# Prepare and verify the recovery set

Keep the data, identities, tools and records needed to recover without the source platform.
An accepted VM backup is one part of this set, not proof that the whole environment can be restored.

**Custody:** encrypted independent copies, separately recoverable keys, and a readable index of locations,
owners, versions, backup IDs/times and integrity records. Record unused capabilities as not applicable.
**Policy:** [backup objectives and retention](virtual-machines.md#backup-policy).
**Design:** [recovery boundaries](../../architecture/operations/backup-recovery.md#recovery-boundaries).

## Contents

- [What must be retained?](#required-material)
- [When is the set updated?](#capture-and-update)
- [How is independence proved?](#verify-independence)

<a id="required-material"></a>

## What must be retained?

- [ ] **Bootstrap VM:** accepted full-VM backup of the execution host, including the OS and any
  workspace/additional PV disks, relocated `/home`, mount/SELinux configuration and local tools. Record its actual name;
  `boot-1` is the starter example. A full clone on the same storage is not an independent backup.
  For an LVM root spanning disks, include and restore every required PV disk together; `/srv/tier0`
  can be a root-filesystem directory rather than a separate mount.
- [ ] **Original IaC identity:** every tier's original state/backend recovery point, workspace/
  environment selection, ignored tfvars, inventories, group vars and local environment inputs.
  Preserve partial-apply state too; Git alone does not contain these files.
- [ ] **Matching code and references:** recorded tier/Shared revisions, provider lockfiles,
  Shared platform profile/template catalog and project standards, in the sibling repository layout.
- [ ] **Approved software:** guest/template images and checksums, matching OS packages, wheels,
  transitive collections, provider mirror and required product/chart/OCI artifacts. The
  [offline bundle](../../deployment/foundation/bootstrap/step-3e-bootstrap-offline.md) covers controller
  dependencies, not every guest or application download.
- [ ] **Independent access:** accepted CA/API trust and SSH host fingerprints; separately protected
  console/API, SSH, backend and NAS/PBS recovery credentials, plus backup encryption keys.
  Retain root/HSM custody, Vault unseal material and SOPS/Ansible Vault keys through their separate
  custody paths. Do not collect all authority into the bootstrap VM backup.
- [ ] **Cluster and application identity/data:** original machine secrets/configuration/access files,
  verified etcd snapshot and native database, Vault, issuer/directory and media recovery sets.
  Record compatible recovery points; etcd is not a persistent-volume backup.
- [ ] **Protected evidence:** log archives, integrity/source catalogues and the independent offline
  reader/key kit. A disposable search index is not the retained security record.
- [ ] **Platform configuration:** gateway/switch configuration exports and Proxmox host/cluster,
  SDN, storage and backup configuration records. Record bridge/VNet/VLAN mappings, independent
  DNS/time, guest IDs, disk interfaces, destination datastores and mount UUIDs/paths. Recovering a
  new cluster is not a blanket copy of old `/etc/pve` over its new configuration.

The index must be readable without NetBox, GitLab, SSO or Vault. Use
[input custody](../recovery/input-custody.md), [original state/etcd](../recovery/original-state-etcd.md)
and the [product procedures](../recovery/README.md) for exact capture contracts.

<a id="capture-and-update"></a>

## When is the set updated?

| Trigger | Capture/check |
| --- | --- |
| Bootstrap tooling, trust and keys are ready | Back up every required bootstrap disk and qualify restore before depending on that VM |
| A state-changing operation completes or partly fails | Protect the resulting original state and matching ignored inputs; a newer state copy can supersede the bootstrap VM's older copy |
| Application data changes | Capture product-native points on the schedule required by its RPO; pair database/media/key versions |
| Host/network/storage or approved software changes | Update configuration exports, recovery mapping and matching artifacts |
| Before destructive work or upgrades | Capture a coherent accepted set and verify independent access before proceeding |

1. Pause competing configuration writers for the selected capture. Record the actual provisioning
   host/backend, code revision, state identity and time; do not create empty state as a substitute.
2. Capture selected product-native data using their procedures, then
   [back up the guests](virtual-machines.md#schedule-and-run), including every required bootstrap disk.
   Use an accepted stopped/quiescent execution-host point when needed; separate jobs are not an atomic snapshot.
3. Establish the early bootstrap/state backup path **before Vault exists**. The later
   [control-copy job](control-applications.md) also captures Vault snapshots and needs Vault available;
   it does not replace the independent bootstrap backup or schedule etcd capture.
4. Record guest, state/input and application recovery-point IDs together. Check that they meet the
   selected consistency and data-age contract; retain the previous accepted set until the new one passes.

<a id="verify-independence"></a>

## How is independence proved?

1. From the independent recovery workstation, access the selected NAS/PBS/files and keys with
   the source bootstrap, cluster, hosted identity and CI unavailable.
2. Perform an [isolated VM restore](virtual-machines.md#restore-a-test-vm), then prove
   [bootstrap recovery](../recovery/bootstrap.md) and original-state/input recovery.
3. Test the selected product's data/identity restore separately. Record measured RPO/RTO and missing data.
4. Exercise [host loss](../recovery/host.md) or [platform loss](../recovery/platform.md) on approved
   isolated capacity, then record which independent copy and credentials supplied every prerequisite.

**Accepted:** the original service identity/data can be recovered within the recorded limits.
A successful copy/check command or fresh installation alone does not establish that result.
