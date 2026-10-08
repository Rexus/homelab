# Recovery

Retain these outside the system being restored:

| Material | Purpose |
| --- | --- |
| Tier/shared code, tools, provider artifacts, images | Bootstrap without hosted source control, CI, or registry |
| State, inventory, network/storage records | Recreate resources without an inventory application |
| Machine configuration, credentials, SOPS and recovery keys | Restore without unavailable identity or secret services |
| etcd and application-data backups | Restore data, not merely empty VMs |
| Working API, DNS/time, image access, and runbook | Execute recovery independently of the target |

Record owners, backup locations, and restore results in project-owned runbooks.
Offline custody has no routed access from the connected management network.

Follow the [deployment stages](../deployment/README.md) to restore prerequisites,
then verify the selected service and its data before restoring consumers.
Use the [backup guide](compute/backup-restore.md) for VM restore validation and
[secret strategy](secret-handling/strategy.md) for protected recovery material.
