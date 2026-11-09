# Administration and operations

Open the task that matches the current question. Each runbook identifies the working
repository or host, prerequisites, numbered actions, expected result and recovery path.
Use the architecture links for the design behind an operation.

## Recovery and resource retirement

| Question | Runbook |
| --- | --- |
| What must survive outside the platform? | [Recovery-set checklist](backups/recovery-set.md) |
| The bootstrap VM is unavailable | [Restore bootstrap execution](recovery/bootstrap.md) |
| One VM crashed or lost data | [Recover a VM](recovery/virtual-machines.md) |
| A Proxmox host died without HA | [Recover a host and its guests](recovery/host.md) |
| All Proxmox infrastructure is gone | [Recover the platform](recovery/platform.md) |
| A service needs its original database or keys | [Product recovery](recovery/README.md#service-data-and-identities) |
| How is a deployment destroyed deliberately? | [Destroy and retirement](provisioning.md) |
| An object was removed on its host; how is state corrected? | [Terraform state tasks](terraform-state.md) |

## Backups and recovery

| Question | Runbook |
| --- | --- |
| How to back up and restore a Proxmox guest? | [VM backup tasks](backups/virtual-machines.md) |
| How to schedule and verify control-service recovery copies? | [Control backups](backups/control-applications.md) |
| How to back up PostgreSQL to NAS and check the copy? | [PostgreSQL file backups](backups/postgresql.md) |
| How to back up the GitLab data VMs? | [GitLab data backups](backups/gitlab-data.md) |
| How to restore the original service identity and data? | [Product recovery](recovery/README.md) |

**Why:** [backup and recovery design](../architecture/operations/backup-recovery.md)
explains copy independence, retention authority, RPO/RTO and compatible recovery sets.

## Hosts

| Question | Runbook |
| --- | --- |
| How to initialize files and connect bootstrap to existing Proxmox hosts? | [Start host management](hosts/management.md) |
| How to review or restrict hypervisor access? | [Proxmox hardening](hosts/hardening.md) |
| How to configure or troubleshoot host update access? | [Repository proxy](hosts/update-access.md) |
| How to trust or rotate the Proxmox API certificate? | [Proxmox TLS](hosts/proxmox-tls.md) |
| How to reconcile host configuration safely? | [Ansible recipes](ansible-recipes.md) |
| How to update services or replace physical hardware? | [Planned maintenance](maintenance.md) |

## Virtual machines and Kubernetes

| Question | Runbook |
| --- | --- |
| How to publish, import, promote or recover a template? | [Template lifecycle](virtual-machines/template-lifecycle.md) |
| How to replace a template image and roll back? | [Boot-disk replacement](virtual-machines/template-disk.md) |
| How to remove a linked clone's base-disk dependency? | [Linked-clone tasks](virtual-machines/linked-clones.md) |
| How to add a Kubernetes worker or reserve a pool? | [Worker pools](kubernetes-pools.md) |

## Trust, access and evidence

| Question | Runbook |
| --- | --- |
| How to maintain CA policy, renewal and publication? | [CA operations](cryptography/certificate-authority.md) |
| How to rotate secrets or an Ansible Vault password? | [Secret handling](secret-handling/strategy.md), [Ansible Vault](secret-handling/ansible-vault.md) |
| How to maintain an HSM host or key replica? | [USB HSM operations](cryptography/usb-hsm.md) |
| How to move an existing issuer to another signing backend? | [Custody migration](cryptography/hardware-migration.md) |
| How to add/remove household or team access? | [Access lifecycle](access-lifecycle.md) |
| How to change Linux SSH, time, audit or firewall settings? | [Host security](host-security.md) |
| How to inspect protected evidence or test restoration? | [Security logging](security-logging.md), [logging drill](logging-drill.md) |

Record the selected targets, approvals, results and rollback evidence in the owning
project's administration records. First installation remains in [deployment](../deployment/README.md).
An operational command does not replace a product's version-specific upgrade or recovery contract.
