# Private cloud maturity path

## Table of contents

- [Purpose](#purpose)
- [Maturity overview](#maturity-overview)
- [Level 1 - Foundation and domain deployment](#level-1---foundation-and-domain-deployment)
- [Level 2 - Vault foundation deployment](#level-2---vault-foundation-deployment)
- [Level 3 - Backup and recovery](#level-3---backup-and-recovery)
- [Level 4 - Higher availability and production use](#level-4---higher-availability-and-production-use)

## Purpose

Use this as the authoritative maturity path for the repository. It grows the
environment from an initial working deployment toward a more resilient and
production-ready private cloud. Proxmox is the current reference foundation,
but the maturity path is about the broader platform.

## Maturity overview

| Level | Goal | Success criteria |
| --- | --- | --- |
| 1 | Foundation and domain deployment | First template, foundation or domain hosts, and the domain services Vault depends on, such as DNS and PKI, are in place |
| 2 | Vault foundation deployment | Vault is deployed as the early secret-platform foundation and ready for initialization |
| 3 | Backup and recovery | PBS is deployed, connected, and tested |
| 4 | Higher availability and production use | Backup, recovery, and platform patterns support more serious use |

## Level 1 - Foundation and domain deployment

Goal:

- copy the example files
- set the required environment variables
- build or prepare a template
- provision the first managed foundation or domain controller hosts
- establish the domain services Vault depends on, especially DNS and the first
  certificate or PKI path
- apply the baseline playbook so the hosts are managed
- keep the first deployment focused on the foundation Vault and later shared
  services depend on

Read more:

- [Platform guide](../platforms/proxmox/README.md)
- [Environment variable conventions](../reference/environment-variables.md)
- [Foundation and domain path](../foundation/foundation-and-domain-path.md)

## Level 2 - Vault foundation deployment

Goal:

- deploy Vault as a dedicated early shared service after the foundation or
  domain layer is ready
- initialize and unseal Vault
- move shared and long-lived secrets into Vault

Read more:

- [Vault foundation deployment](../foundation/vault-foundation-deployment.md)
- [Secret strategy](../security/secret-strategy.md)

## Level 3 - Backup and recovery

Goal:

- add Proxmox Backup Server before the environment becomes important
- create a datastore
- add PBS to Proxmox VE as storage
- run and validate at least one backup and one restore

Read more:

- [Backup foundation](../platforms/proxmox/backup-foundation.md)
- [Network prerequisites](../platforms/proxmox/network-prerequisites.md)
- [API setup](../platforms/proxmox/setup-api.md)

## Level 4 - Higher availability and production use

Goal:

- improve resilience, recovery, and operational confidence
- move beyond single-host assumptions where needed
- use the platform for more serious application and infrastructure services

Read more:

- [Architecture overview](../architecture/overview.md)
- [Security principles](../security/security-principles.md)
