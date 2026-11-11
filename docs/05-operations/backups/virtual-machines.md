# Proxmox backup and restore

<a id="proxmox-backup-foundation"></a>

Configure VM/CT backups and a complete recovery set, then prove recovery on isolated capacity.
Protect the bootstrap execution path as well as service data. Host snapshots, guest replicas
and copied files are not substitutes for an accepted restore.

**Run on:** Proxmox VE GUI or an authorized Proxmox host shell; PBS administration uses its own UI.
**Prerequisites:** independent console access, commissioned backup storage and recoverable credentials.
**Design:** [backup and recovery](../../01-architecture/24-operations/04-backup-recovery.md).

<a id="table-of-contents"></a>

## Operator tasks

- [How is a backup policy recorded?](#backup-policy)
- [What must a complete recovery set contain?](#recovery-set)
- [How is a recovery set captured before maintenance or destruction?](#capture-a-recovery-set)
- [How to prepare a backup target?](#quick-steps)
- [How to schedule and run a guest backup?](#schedule-and-run)
- [How to list backups and restore a test VM?](#restore-a-test-vm)
- [How to change retention or prune history?](#retention-and-pruning)
- [Which recovery routine applies after a failure?](#choose-a-recovery-routine)
- [When is the backup path accepted?](#done-criteria)
- [References](#references)

<a id="purpose"></a>
<a id="target-outcome"></a>

Prepare the destination and protect original inputs during
[Foundation Step 3](../../03-deployment/foundation/README.md#step-3-prepare-the-bootstrap-execution-host).
Guest backup/restore tests follow the first disposable clone in Step 4.
This guide configures existing products manually; no supplied role installs PBS or NAS storage.

<a id="backup-policy"></a>

## How is a backup policy recorded?

Record these selections in project operating records before enabling scheduled deletion.
The [design](../../01-architecture/24-operations/04-backup-recovery.md) owns 3-2-1, failure domains and custody. [1]

| Record | Required operational check |
| --- | --- |
| Dataset and owner | State/ignored inputs, application data and logs have named recovery procedures |
| RPO / RTO | Maximum acceptable data age and measured restore duration, per dataset |
| Included disks | Every required guest disk is enabled for backup; include bootstrap OS/data disks and the logger's separate data disk |
| Retention | Approved history, expiry, legal/incident holds and pruning custodian |
| Access | Separate creation/restore/retention duties; test actual storage permissions and record backup-writer/root deletion authority |
| Independent copy | Offsite/offline or independently protected copy and keys survive the selected source failure |
| Evidence | Isolated restore, key recovery and offline log-read results are recorded |

A writable backup credential, NAS administrator or recovery-host root may still remove or alter
repository contents even when the backup job never prunes. Record that trust and independently
enforced protection explicitly; a writable share or ordinary snapshot is not WORM storage. [2][3]

<a id="recovery-set"></a>
<a id="capture-a-recovery-set"></a>

## What must a complete recovery set contain?

Follow the [recovery-set checklist and capture routine](recovery-set.md). It covers the bootstrap
OS/workspace disks, original state/ignored inputs, code/artifacts, host/network/storage records,
application data and separately recoverable keys. Verify that set before relying on guest backup alone.

<a id="quick-steps"></a>

## How to prepare a backup target?

Choose **1a or 1b**, then continue to [scheduling](#schedule-and-run).
An existing qualified target is valid; neither path requires an object-storage API.

<a id="nas-file-target"></a>

### 1a: Existing NAS file target

1. Have the storage custodian prepare a dedicated export, capacity and scoped Proxmox access.
2. Open **Datacenter > Storage > Add > NFS** and enter:

   | Field | Enter |
   | --- | --- |
   | ID | Selected backup-storage ID, distinct from live VM disk storage |
   | Server / Export | Actual commissioned NAS endpoint/export |
   | Content | Backup-file content |
   | Nodes | Only nodes authorized and able to reach that target |

3. Check the added storage is available from its intended nodes. Proxmox manages the mount;
   no guest-side mount or storage gateway is required. [4][5]
4. Arrange the independent copy and recovery credentials with the storage custodian.
   A second share on the same NAS is not an independent copy.

<a id="pbs-reference"></a>

### 1b: PBS reference service

1. Install/commission PBS independently; open its UI on HTTPS port `8007`.
2. Create the selected datastore and namespace. Create a namespace-scoped backup token with
   `DatastoreBackup`; retain prune/admin authority under separate custody. [2]
3. In **Proxmox VE > Datacenter > Storage > Add > Proxmox Backup Server**, set the actual
   server, datastore, namespace and backup token. Verify the fingerprint independently
   against the PBS dashboard before accepting it.
4. Check target access and independently retain PBS recovery credentials/keys.
   Qualify offsite synchronization without propagating vanished-source deletions. [3]

<a id="schedule-and-run"></a>

## How to schedule and run a guest backup?

### 1. Check every required disk

In **Proxmox > guest > Hardware > disk**, inspect each **Backup** selection.
For `boot-1`, include every disk required by its OS/workspace or root-LVM layout.
For the collector, include its separate log-data disk.

External Kubernetes PVCs, NAS shares and application objects need their own
[product backup contracts](../../03-deployment/foundation/storage/README.md#choose-the-native-interface).

### 2. Create or edit the schedule

In **Datacenter > Backup > Add/Edit**, select the exact guests, backup storage, node scope,
approved frequency, consistency mode and notification target.

### 3a. Run the scheduled job now

In **Datacenter > Backup**, select the reviewed job and **Run now**. Read its task log.
After successful completion, continue to Step 4; Step 3b is an alternative.

### 3b. Run one disposable guest manually instead

Run on **the selected Proxmox host as an authorized root operator**.

```bash
read -r -p "Disposable guest VMID: " BACKUP_VMID
read -r -p "Commissioned backup-storage ID: " BACKUP_STORAGE
vzdump "$BACKUP_VMID" --storage "$BACKUP_STORAGE" --mode snapshot
pvesm list "$BACKUP_STORAGE" --content backup
```

This takes one immediate backup and lists the target's backup files; it creates no schedule.
Continue to Step 4 after successful completion.

### 4. Verify the finished recovery point

In **backup storage > Backups**, confirm the selected guest and new backup time.
A failed task, missing disk or unavailable destination is a failed recovery point;
do not silently redirect it to another directory.

A `snapshot` backup minimizes downtime but does not prove database/application consistency.
Use product-aware backups or an approved stopped-guest point when required. [4]
Next, [restore an isolated test VM](#restore-a-test-vm).

<a id="restore-a-test-vm"></a>

## How to list backups and restore a test VM?

**Run on:** the authorized Proxmox host. Select a known-good point, a genuinely unused VMID and
live-disk storage. Keep the original guest/state and backup intact.

### 1. List and select the backup

Run on **the selected Proxmox host as an authorized root operator**:

```bash
read -r -p "Backup-storage ID: " BACKUP_STORAGE
pvesm list "$BACKUP_STORAGE" --content backup
```

Record the selected volume/file ID and backup time.

### 2a. Restore through the GUI

In **backup storage > Backups**, select the backup and **Restore**.
Use a **new VMID** and approved live-disk storage. Leave **Start after restore** and **Live restore** off.
Wait for success, inspect the restored **Hardware** view, then continue to Step 3.

### 2b. Restore a VM through the CLI instead

Run on **the selected Proxmox host as an authorized root operator**:

```bash
read -r -p "Selected VM backup volume ID or archive path: " BACKUP_VOLUME
read -r -p "Unused test VMID, verified in Datacenter: " RESTORE_VMID
read -r -p "Approved live VM datastore ID: " RESTORE_STORAGE
qmrestore "$BACKUP_VOLUME" "$RESTORE_VMID" --storage "$RESTORE_STORAGE"
```

Wait for success. In **the same Proxmox host shell**, inspect the stopped VM:

```bash
qm config "$RESTORE_VMID"
```

Do not use `--force`, an existing VMID or live-restore. `qmrestore` is for VMs;
restore containers through their native GUI/`pct restore` procedure instead. [4][6]
Continue to Step 3; do not also perform Step 2a.

### 3. Isolate the restored guest

**Before starting**, disconnect production NICs or attach only the isolated recovery network.
Prevent duplicate IPs, directory authorities, scheduled jobs and outward integrations.

### 4. Boot and test recovery

Use **the restored guest's console**. Verify every required disk, known content, application recovery
and independent credential access. Test with hosted identity/Vault/CI unavailable.

For a bootstrap restore, check `/srv/tier0` and any `/home` bind mount, original tier inputs/state,
offline tools and independently verified API/SSH access before allowing an IaC writer to run.

### 5. Record the result and keep the test isolated

Record backup ID, checks and measured RPO/RTO. Keep the test isolated until the product's
own cutover procedure is accepted.

A disposable test restore stays outside live Terraform state. Use the
[VM recovery routine](../recovery/virtual-machines.md) for production identity/cutover and
state reconciliation; never import a test VM into the original deployment merely to pass a drill.

**Stop/rollback:** on failed restore or wrong target selection, leave the replacement stopped,
preserve its task log/disks and investigate. Retry on another clean target; do not delete the
original guest or backup to force a retry.

<a id="retention-and-pruning"></a>

## How to change retention or prune history?

1. Have the backup custodian approve retention and confirm independent copies/incident holds.
2. For **PBS**, review datastore/namespace **Prune Jobs** under its separate administration.
   Backup clients retain `DatastoreBackup`; `Datastore.Prune` is separate deletion authority. [2]
3. For **NAS backup files**, review the Proxmox backup job/storage retention settings under the
   identity authorized to delete those files. Inspect the product's preview before enabling deletion.
4. Verify retained recovery points and independent copies after the authorized operation.

These UI/product policies are separate from the supplied control-copy and database file-backup jobs.
Those jobs do not install backup-data pruning. Do not infer retention from job-history limits.
Deletion cannot be rolled back without another retained copy.

<a id="choose-a-recovery-routine"></a>

## Which recovery routine applies after a failure?

Start from independent console/storage access and the retained bootstrap kit. Preserve surviving
evidence and fence old automation before bringing a replacement online.

| Failure scope | Numbered recovery routine | First acceptance gate |
| --- | --- | --- |
| Bootstrap VM unavailable | [Restore bootstrap execution](../recovery/bootstrap.md) | OS/data disks or replacement tools, original inputs/state and independent credentials work |
| One guest lost or reset | [Recover virtual machines](../recovery/virtual-machines.md) | Isolated guest/data validation and original IaC resource/state identity are reconciled |
| Proxmox host failed | [Recover a host](../recovery/host.md) | Host/network/storage and HA membership are qualified; no duplicate guest execution |
| Entire platform unavailable | [Recover the platform](../recovery/platform.md) | Independent bootstrap and backups work before Tier 0, then dependent tiers resume |

These routines select the sequence; [product procedures](../recovery/README.md) own service-specific
consistency, original keys/history and cutover. A successful VM boot alone is not application recovery.

<a id="done-criteria"></a>

## When is the backup path accepted?

- [ ] Destination and independently held credentials work.
- [ ] Guest backup and isolated restore complete with every required data disk.
- [ ] The bootstrap recovery set, original tier state/inputs and network/storage records are recoverable independently.
- [ ] Product content and known protected data are readable within recorded RPO/RTO.
- [ ] Ordinary producer/query access is restricted; backup-writer/root deletion authority and independent protection are recorded and tested.
- [ ] Offsite/offline copy and key recovery are verified without the source environment.

<a id="read-more"></a>

Continue with [tier recovery order](../recovery.md#recovery-order),
[product recovery tasks](../recovery/README.md) or
[offline log investigation](../security-logging.md#offline-investigation).

## References

1. [HHS backup/recovery guidance](https://www.hhs.gov/hipaa/for-professionals/security/guidance/cybersecurity-newsletter-october-2022/index.html).
2. [PBS roles and namespace-scoped access](https://pbs.proxmox.com/docs/user-management.html).
3. [PBS independent-copy protection](https://pbs.proxmox.com/docs/storage.html#ransomware-protection-recovery).
4. [Proxmox backup modes, scheduling and restore](https://raw.githubusercontent.com/proxmox/pve-docs/master/vzdump.adoc).
5. [Proxmox NFS storage](https://github.com/proxmox/pve-docs/blob/master/pve-storage-nfs.adoc).
6. [Native qmrestore options](https://raw.githubusercontent.com/proxmox/qemu-server/master/src/PVE/CLI/qmrestore.pm).
