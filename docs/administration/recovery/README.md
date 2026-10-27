# Product recovery procedures

Restore on isolated clean targets with independently held credentials and known-good recovery IDs.
The [tier recovery order](../recovery.md) owns incident sequencing and evidence preservation;
the [backup policy](../compute/backup-restore.md#backup-policy) owns custody and RPO/RTO.
These procedures are executable operator recipes, not evidence of a completed live restore.

| Task | Procedure |
| --- | --- |
| Extract encrypted control copies | [Clean file extraction](files.md) |
| Verify storage custody and provider recovery | [Existing storage contract](../../deployment/foundation/storage/README.md#recovery-and-existing-installations) |
| Transport original ignored provisioning inputs | [Input custody](input-custody.md) |
| Authorize scheduled Vault snapshots | [Snapshot authentication](vault-backup-auth.md) |
| Recover original inputs/state and Kubernetes state | [Original state and etcd](original-state-etcd.md) |
| Restore Vault Raft state | [Vault](vault.md) |
| Restore PostgreSQL from a completed NAS file set | [NAS-file CNPG recovery](cnpg-files.md) |
| Restore CNPG PostgreSQL from object/WAL backups | [Barman recovery](cnpg.md) |
| Restore NetBox database and media together | [NetBox](netbox.md) |
| Restore identity federation | [Keycloak](keycloak.md) |
| Restore FreeIPA and preserve CA identity | [FreeIPA and CA](freeipa-ca.md) |
| Restore shared product data | [Tier 1 products](tier-1-products.md) |

Install scheduled snapshot/copy transport through
[control application backups](../backups/control-applications.md). An empty application installer,
database readiness, replica count, successful snapshot command or restic check is not a product restore.
