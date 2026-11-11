# Secrets and control services operations

Maintain secret custody and recovery along with NetBox, Headlamp and the independent
monitoring introduced in Stage 6.

**Related:** [Architecture](../../01-architecture/19-secrets/README.md) ·
[Stage 6: Secrets](../../03-deployment/stage-6-secrets/README.md).

| Task | Guide |
| --- | --- |
| Handle and rotate credentials | [Secret strategy](../secret-handling/strategy.md) |
| Maintain encrypted Ansible secret files | [Ansible Vault](../secret-handling/ansible-vault.md) |
| Schedule control copies and authorize Vault snapshots | [Control backups](../backups/control-applications.md), [snapshot authentication](../recovery/vault-backup-auth.md) |
| Restore Vault or NetBox | [Vault recovery](../recovery/vault.md), [NetBox recovery](../recovery/netbox.md) |
| Review NetBox and Headlamp installation and checks | [Control applications](../../03-deployment/stage-6-secrets/procedures/control-applications.md) |
| Inspect maintenance scope | [Ansible recipe map](../ansible-recipes.md#recipe-map) |
| Install and verify independent monitoring | [Monitoring procedure](../../03-deployment/stage-6-secrets/procedures/independent-monitoring.md) |

Control-service and monitoring operations beyond these linked tasks have general coverage;
initialization, unseal and recovery acceptance remain operator tasks under Stage 6.
Installation or a backup job alone does not prove recovery.
