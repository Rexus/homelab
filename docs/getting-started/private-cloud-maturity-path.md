# Private cloud maturity path

## Table of contents

- [Purpose](#purpose)
- [Maturity overview](#maturity-overview)
- [Level 1 - Secure bootstrap foundation](#level-1---secure-bootstrap-foundation)
- [Level 2 - Backup and recovery](#level-2---backup-and-recovery)
- [Level 3 - Secret integration](#level-3---secret-integration)
- [Level 4 - Higher availability and production use](#level-4---higher-availability-and-production-use)

## Purpose

Use this path to grow the environment from an initial working deployment toward
 a more resilient and production-ready private cloud. Proxmox is the current
reference foundation, but the maturity path is about the broader platform.

## Maturity overview

| Level | Goal | Success criteria |
| --- | --- | --- |
| 1 | Secure bootstrap foundation | First template and VM work, and Vault is installed on the first managed node |
| 2 | Backup and recovery | PBS is deployed, connected, and tested |
| 3 | Secret integration | Shared and long-lived secrets move into Vault and out of bootstrap-only handling |
| 4 | Higher availability and production use | Backup, recovery, and platform patterns support more serious use |

## Level 1 - Secure bootstrap foundation

Goal:

- copy the example files
- set the required environment variables
- build or prepare a template
- provision the first managed VM as a dedicated Vault host
- apply the bootstrap playbook so Vault is installed and ready to initialize
- initialize Vault before broader shared-service and workload deployment

Read more:

- [Platform guide](../platforms/proxmox/README.md)
- [Environment variable conventions](../reference/environment-variables.md)
- [Vault bootstrap](vault-bootstrap.md)

## Level 2 - Backup and recovery

Goal:

- add Proxmox Backup Server before the environment becomes important
- create a datastore
- add PBS to Proxmox VE as storage
- run and validate at least one backup and one restore

Read more:

- [Backup foundation](../platforms/proxmox/backup-foundation.md)
- [Network prerequisites](../platforms/proxmox/network-prerequisites.md)
- [API setup](../platforms/proxmox/setup-api.md)

## Level 3 - Secret integration

Goal:

- move shared and long-lived secrets out of bootstrap-only handling
- establish operator and automation access methods that read from Vault
- reduce direct use of persistent secret environment variables

Read more:

- [Vault bootstrap](vault-bootstrap.md)
- [Secret strategy](../security/secret-strategy.md)

## Level 4 - Higher availability and production use

Goal:

- improve resilience, recovery, and operational confidence
- move beyond single-host assumptions where needed
- use the platform for more serious application and infrastructure services

Read more:

- [Architecture overview](../architecture/overview.md)
- [Security principles](../security/security-principles.md)
