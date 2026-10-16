# ${prefix} Recovery Runbook

Complete and test this runbook before depending on the environment. Record
where protected material is held, not the credentials or key material itself.
Use the [naming conventions](../naming-conventions.md) to interpret names and
ID ranges; use inventory and state backups for exact resource assignments.

## Recovery inputs

| Input | Location / custodian | Offline availability |
| --- | --- | --- |
| Tier repositories and reviewed shared-code revision | TBD | TBD |
| Images, providers, collections and artifacts | TBD | TBD |
| State backups and restore procedure | TBD | TBD |
| Credentials, trust material and recovery authorization | TBD | TBD |
| Network/platform plan and local console access | TBD | TBD |
| Protected log-data copies, schema/source catalogue and offline reader kit | TBD | TBD |
| Separate log/backup decryption keys and recovery authorization | TBD | TBD |
| Backup copy/media locations, retention, RPO/RTO and pruning custodian | TBD | TBD |

## Recovery steps

| Order | Tier / component | Action or linked procedure | Verification | Owner |
| --- | --- | --- | --- | --- |
| 1 | Surviving evidence | TBD | preserve originals; inspect a data-volume copy with only the offline reader/key kit | TBD |
| 2 | Tier 0 access and logging | TBD | local credentials and intake work without identity, Kubernetes or Tier 1/2 | TBD |
| 3 | Tier 0 trust and control, plus separately isolated custody | TBD | recover without Tier 1 or Tier 2 services | TBD |
| 4 | Tier 1 platform | TBD | recover without Tier 2; rebuild scoped search copies without modifying original evidence | TBD |
| 5 | Tier 2 workloads | TBD | service-specific health, read scopes and collection checks | TBD |

## Test record

| Date | Scenario and scope | Result / evidence | Follow-up owner |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

References: [Recovery principles](../auto-docs/administration/recovery.md),
[offline log investigation](../auto-docs/administration/security-logging.md#offline-investigation),
[backup policy](../auto-docs/administration/compute/backup-restore.md#backup-policy),
[shared-code recovery](../auto-docs/development/generated-repositories.md#shared-code-and-recovery),
and [secret strategy](../auto-docs/administration/secret-handling/strategy.md).
