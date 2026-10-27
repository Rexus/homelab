# Proxmox backup foundation

## Table of contents

- [Purpose](#purpose)
- [Backup policy](#backup-policy)
- [Target outcome](#target-outcome)
- [Quick steps](#quick-steps)
- [Done criteria](#done-criteria)
- [Read more](#read-more)
- [References](#references)

## Purpose

Protect recovery data before depending on the environment. Proxmox Backup Server
(PBS) is the reference VM backup service; a verified existing service is also valid.
Neither backup access nor recovery keys may depend solely on the systems being restored.

## Backup policy

Use **3-2-1** for critical data: three copies including the primary, two different
media types and one copy offsite. Retain an offline or independently immutable copy
against compromise of connected systems. Test restoration, not only job success. [1]

| Control | Required record or check |
| --- | --- |
| Scope | IaC state/inventory, bootstrap material, application data and protected logs; include the collector's separate data disk and evidence metadata |
| Recovery point objective (RPO) | Maximum acceptable data age/loss per dataset; scheduled backup intervals do not provide zero-loss logging |
| Recovery time objective (RTO) | Time to inspect evidence and restore each tier, including access to offsite media and keys |
| Retention | Approved history and expiry per dataset; security-evidence retention also follows the [archive contract](../../architecture/operations/security-logging.md#protected-retention) |
| Authority | Separate backup creation, restoration and pruning identities; query users and producers receive no backup deletion/admin credentials |
| Independence | Copies and keys survive the selected source-host/site loss and compromise envelope; collector/query credentials cannot delete every copy; trusted custodians are recorded explicitly |
| Verification | Periodic isolated restore, offline log inspection and key-recovery test; record gaps or media-policy exceptions explicitly |

Receiver replicas provide availability, not historical backups. RAID, same-pool
snapshots and Tier 1 search copies do not substitute for independent recovery copies.
Backups also do not turn a mutable archive into WORM storage.
One homelab operator may hold several custody roles using separate credentials;
the [log retention choices](../../architecture/operations/log-retention.md) distinguish
that trusted-administrator model from enforced protection against privileged deletion.

For PBS, use separate namespace-scoped client tokens with `DatastoreBackup`, not
`DatastorePowerUser` or administrator roles. `Datastore.Backup` permits creation and
read/verification of owned backups; `Datastore.Prune` adds deletion authority. [2]
Keep pruning under separate backup custody, and configure offsite synchronization
not to propagate vanished-source deletions. PBS itself still needs independent protection
against backup-server compromise. [3]

## Target outcome

This phase requires the following outcomes:

- an approved backup destination with independently recoverable access and keys
- protected copies of local state, inventory and bootstrap inputs before guest creation
- at least one successful VM or LXC backup
- at least one successful restore test

Guest tests require a disposable clone. In the
[foundation checklist](../../deployment/foundation/README.md), prepare the destination
and test local-input recovery in Step 2, then test guest backup/restore in Step 3.
A NAS or another existing service is valid when its selected backup tooling preserves
the required data and passes the same recovery and authority checks. A shared folder
or successful file transfer alone does not establish that result.

## Quick steps

Choose an existing NAS file target or the PBS reference service. Both must pass
the same restore and custody checks; neither requires an object-storage API.
With a qualified existing target, installing PBS is not mandatory.

### NAS file target

1. Commission a dedicated NAS export with restricted Proxmox access and enough
   capacity. In Proxmox, add it under `Datacenter -> Storage -> Add -> NFS`, select
   the actual server/export and enable backup-file content. Proxmox manages the
   mount; no gateway service or guest-side object API is required. [4][5]
2. Under `Datacenter -> Backup`, select that target, guests, included disks,
   consistency mode and schedule. Run the job and check the resulting backup
   files. Snapshot mode is not proof of application-consistent database recovery;
   use product-aware backups or an approved stopped-guest recovery point. [4]
3. Restore a disposable guest under a new identity and verify its data. Arrange
   an independently retained/offsite copy of the files and recovery credentials;
   a second share on the same NAS does not provide that independence.

VM backups do not automatically include external Kubernetes PVCs or NAS shares.
Protect those datasets through their [application backup contracts](../../deployment/foundation/storage/README.md#choose-the-native-interface).
The mounted file destination is not a claim of WORM, deduplication or HA.

### PBS reference

1. Install Proxmox Backup Server.
2. Log in to the PBS web UI on port `8007`.
3. Create a datastore.
4. Add PBS to Proxmox VE under `Datacenter -> Storage`.
5. Copy the PBS fingerprint from the PBS dashboard and use it when adding the
   storage entry.
6. Create a backup job in Proxmox VE under `Datacenter -> Backup`.
7. Run the backup job.
8. Restore one test VM or container from PBS.
9. Verify inclusion and readability of every required data disk; test the independent
   copy and recovery credentials with identity, secret and hosted delivery services unavailable.

## Done criteria

Do not continue until all of these are true:

- the selected backup destination is reachable from its intended client
- storage and independently held recovery credentials are usable
- a backup completes successfully
- a restore completes successfully
- the restored workload can boot or otherwise be validated
- required data disks and keys are recoverable within the recorded RPO/RTO
- client/query identities cannot prune backups or alter protected retention
- the offsite/offline copy is verified independently of the source environment

## Read more

- [Deployment readiness](../../deployment/readiness.md)
- [Host networking](../../deployment/foundation/proxmox/network.md)
- [Hardening baseline](hardening.md)
- [Offline security-log investigation](../security-logging.md#offline-investigation)
- [Tier recovery order](../recovery.md#recovery-order)

## References

Policy sources checked 2026-10-19; native NAS backup path checked 2026-10-27.

1. [HHS backup and recovery guidance: 3-2-1 and offline copies](https://www.hhs.gov/hipaa/for-professionals/security/guidance/cybersecurity-newsletter-october-2022/index.html)
2. [PBS roles, privileges and namespace-scoped access](https://pbs.proxmox.com/docs/user-management.html)
3. [PBS ransomware protection and independent copies](https://pbs.proxmox.com/docs/storage.html#ransomware-protection-recovery)
4. [Proxmox native backup targets and consistency modes](https://github.com/proxmox/pve-docs/blob/master/vzdump.adoc)
5. [Proxmox native NFS storage backend](https://github.com/proxmox/pve-docs/blob/master/pve-storage-nfs.adoc)
