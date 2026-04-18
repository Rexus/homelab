# Proxmox maturity path

## Table of contents

- [Purpose](#purpose)
- [Maturity overview](#maturity-overview)
- [Level 1 - Initial deployment](#level-1---initial-deployment)
- [Level 2 - Backup foundation](#level-2---backup-foundation)
- [Level 3 - Secret platform](#level-3---secret-platform)
- [Level 4 - Higher availability and production use](#level-4---higher-availability-and-production-use)

## Purpose

Use this path to grow the platform from an initial working deployment toward a
more resilient and production-ready private cloud.

## Maturity overview

| Level | Goal | Success criteria |
| --- | --- | --- |
| 1 | Initial deployment | First template, VM, and baseline flow works |
| 2 | Backup foundation | PBS is deployed, connected, and tested |
| 3 | Secret platform | Vault replaces bootstrap-only secret handling |
| 4 | Higher availability and production use | Backup, recovery, and platform patterns support more serious use |

## Level 1 - Initial deployment

Goal:

- copy the example files
- set the required environment variables
- build or prepare a template
- provision the first managed VM
- apply the first Ansible baseline run

Read more:

- [Platform guide](../platforms/proxmox/README.md)
- [Environment variable conventions](../reference/environment-variables.md)

## Level 2 - Backup foundation

Goal:

- deploy Proxmox Backup Server
- create a datastore
- add PBS to Proxmox VE as storage
- run and validate at least one backup and one restore

Read more:

- [Backup foundation](../platforms/proxmox/backup-foundation.md)
- [Network prerequisites](../platforms/proxmox/network-prerequisites.md)
- [API setup](../platforms/proxmox/setup-api.md)

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
- use the platform for more serious application and infrastructure services

Read more:

- [Architecture overview](../architecture/overview.md)
- [Security principles](../security/security-principles.md)
