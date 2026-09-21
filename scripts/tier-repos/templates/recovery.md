# ${prefix} Recovery Runbook

Complete and test this runbook before depending on the environment. Record
where protected material is held, not the credentials or key material itself.
Use the [naming conventions](../../naming-conventions.md) to interpret names and
ID ranges; use inventory and state backups for exact resource assignments.

## Recovery inputs

| Input | Location / custodian | Offline availability |
| --- | --- | --- |
| Tier repositories and reviewed shared-code revision | TBD | TBD |
| Images, providers, collections and artifacts | TBD | TBD |
| State backups and restore procedure | TBD | TBD |
| Credentials, trust material and recovery authorization | TBD | TBD |
| Network/platform plan and local console access | TBD | TBD |

## Recovery steps

| Order | Tier / component | Action or linked procedure | Verification | Owner |
| --- | --- | --- | --- | --- |
| 1 | Tier 0 control, plus separately isolated custody | TBD | recover without Tier 1 or Tier 2 services | TBD |
| 2 | Tier 1 platform | TBD | recover without Tier 2 workloads | TBD |
| 3 | Tier 2 workloads | TBD | service-specific health and access checks | TBD |

## Test record

| Date | Scenario and scope | Result / evidence | Follow-up owner |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

References: [Tier 0 bootstrap](../../auto-docs/paths/tier-0/bootstrap.md),
[shared-code recovery](../../auto-docs/reference/generated-repository-model.md#shared-code-and-recovery),
and [secret strategy](../../auto-docs/security/secret-strategy.md).
