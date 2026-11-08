# Administration and operations

Open the task that matches the current question. Each runbook identifies the working
repository or host, prerequisites, numbered actions, expected result and recovery path.
Use the architecture links for the design behind an operation.

## Common tasks

| Question | Runbook |
| --- | --- |
| How to check, run or rotate backups? | [Backup and restore tasks](compute/backup-restore.md) |
| How to restore a failed service or the whole platform? | [Recovery entry point](recovery.md), [product runbooks](recovery/README.md) |
| How to renew or revoke a certificate? | [CA operations](cryptography/certificate-authority.md) |
| How to rotate secrets or an Ansible Vault password? | [Secret handling](secret-handling/strategy.md), [Ansible Vault](secret-handling/ansible-vault.md) |
| How to replace a template image and roll back? | [Boot-disk replacement](compute/template-disk.md) |
| How to investigate missing logs or reader access? | [Security logging](security-logging.md), [fault/restore drill](logging-drill.md) |

## Backups and recovery

| Question | Runbook |
| --- | --- |
| How to back up and restore a Proxmox guest? | [VM backup tasks](compute/backup-restore.md) |
| How to schedule and verify control-service recovery copies? | [Control backups](backups/control-applications.md) |
| How to back up PostgreSQL to NAS and check the copy? | [PostgreSQL file backups](backups/postgresql.md) |
| How to back up the GitLab data VMs? | [GitLab data backups](backups/gitlab-data.md) |
| How to restore the original service identity and data? | [Product recovery](recovery/README.md) |

**Why:** [backup and recovery design](../architecture/operations/backup-recovery.md)
explains copy independence, retention authority, RPO/RTO and compatible recovery sets.

## Compute and updates

| Question | Runbook |
| --- | --- |
| How to review or restrict hypervisor access? | [Proxmox hardening](compute/hardening.md) |
| How to configure or troubleshoot host update access? | [Repository proxy](compute/update-access.md) |
| How to trust or rotate the Proxmox API certificate? | [Proxmox TLS](compute/proxmox-tls.md) |
| How to publish, import, promote or recover a template? | [Template lifecycle](compute/template-lifecycle.md) |
| How to remove a linked clone's base-disk dependency? | [Linked-clone tasks](compute/linked-clones.md) |
| How to add a Kubernetes worker or reserve a pool? | [Worker pools](compute/kubernetes-pools.md) |
| How to reconcile host configuration safely? | [Ansible recipes](ansible-recipes.md) |
| How to update services or replace a physical host? | [Maintenance](maintenance.md) |

## Trust, access and evidence

| Question | Runbook |
| --- | --- |
| How to maintain CA policy, renewal and publication? | [CA operations](cryptography/certificate-authority.md) |
| How to maintain an HSM host or key replica? | [USB HSM operations](cryptography/usb-hsm.md) |
| How to move an existing issuer to another signing backend? | [Custody migration](cryptography/hardware-migration.md) |
| How to add/remove household or team access? | [Access lifecycle](access-lifecycle.md) |
| How to change Linux SSH, time, audit or firewall settings? | [Host security](host-security.md) |
| How to inspect protected evidence or test restoration? | [Security logging](security-logging.md), [logging drill](logging-drill.md) |

Record the selected targets, approvals, results and rollback evidence in the owning
project's administration records. First installation remains in [deployment](../deployment/README.md).
An operational command does not replace a product's version-specific upgrade or recovery contract.
