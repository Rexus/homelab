# Private cloud maturity path

## Table of contents

- [Purpose](#purpose)
- [Maturity overview](#maturity-overview)
- [Level 1 - First repo test](#level-1---first-repo-test)
- [Level 2 - Backup and recovery](#level-2---backup-and-recovery)
- [Level 3 - Secret platform](#level-3---secret-platform)
- [Level 4 - Higher availability and production use](#level-4---higher-availability-and-production-use)

## Purpose

Use this path to grow the environment from a first working test toward a more
resilient and production-ready private cloud. Proxmox is the current reference
foundation, but the maturity path is about the broader platform.

## Maturity overview

| Level | Goal | Success criteria |
| --- | --- | --- |
| 1 | First repo test | First template, VM, and baseline flow works |
| 2 | Backup and recovery | PBS is deployed, connected, and tested |
| 3 | Secret platform | Vault replaces bootstrap-only secret handling |
| 4 | Higher availability and production use | Backup, recovery, and platform patterns support more serious use |

## Level 1 - First repo test

Goal:

- copy the example files
- set the required environment variables
- build or prepare a template
- provision a first test VM
- apply the first Ansible baseline run

Read more:

- [Platform guide](../../platforms/proxmox/README.md)
- [Environment variable conventions](../reference/environment-variables.md)

## Level 2 - Backup and recovery

Goal:

- add Proxmox Backup Server before the environment becomes important
- create a datastore
- add PBS to Proxmox VE as storage
- run and validate at least one backup and one restore

Read more:

- [Backup foundation](../../platforms/proxmox/backup-foundation.md)
- [Network prerequisites](../../platforms/proxmox/network-prerequisites.md)
- [API setup](../../platforms/proxmox/setup-api.md)

## Level 3 - Secret platform

Goal:

- deploy Vault after the platform foundation is stable
- move shared and long-lived secrets out of bootstrap-only handling

Read more:

- [Secret strategy](../security/secret-strategy.md)

## Level 4 - Higher availability and production use

Goal:

- improve resilience, recovery, and operational confidence
- move beyond single-host assumptions where needed
- use the platform for more serious shared services and workloads

Read more:

- [Architecture overview](../architecture/overview.md)
- [Security principles](../security/security-principles.md)
