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

- a running Proxmox Backup Server
- a datastore created on PBS
- PBS added to Proxmox VE as storage
- at least one successful VM or LXC backup
- at least one successful restore test

## Quick steps

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

- PBS is reachable from Proxmox VE
- the datastore is visible and usable
- a backup completes successfully
- a restore completes successfully
- the restored workload can boot or otherwise be validated
- required data disks and keys are recoverable within the recorded RPO/RTO
- client/query identities cannot prune backups or alter protected retention
- the offsite/offline copy is verified independently of the source environment

## Read more

- [Deployment readiness](../../deployment/readiness.md)
- [Host networking](../../deployment/foundation/procedures/host-network.md)
- [Hardening baseline](hardening.md)
- [Offline security-log investigation](../security-logging.md#offline-investigation)
- [Tier recovery order](../recovery.md#recovery-order)

## References

Sources checked 2026-10-16.

1. [HHS backup and recovery guidance: 3-2-1 and offline copies](https://www.hhs.gov/hipaa/for-professionals/security/guidance/cybersecurity-newsletter-october-2022/index.html)
2. [PBS roles, privileges and namespace-scoped access](https://pbs.proxmox.com/docs/user-management.html)
3. [PBS ransomware protection and independent copies](https://pbs.proxmox.com/docs/storage.html#ransomware-protection-recovery)
