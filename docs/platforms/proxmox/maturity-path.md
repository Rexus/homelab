# Proxmox maturity path

## Table of contents

- [Purpose](#purpose)
- [Maturity overview](#maturity-overview)
- [Level 1 - Identity foundation deployment](#level-1---identity-foundation-deployment)
- [Level 2 - Vault foundation deployment](#level-2---vault-foundation-deployment)
- [Level 3 - Backup foundation](#level-3---backup-foundation)
- [Level 4 - Higher availability and production use](#level-4---higher-availability-and-production-use)

## Purpose

Use this as a Proxmox-specific view of the broader
[private cloud maturity path](../../getting-started/private-cloud-maturity-path.md). The private
cloud path is the authoritative repository-wide source of truth; this page
keeps the same milestones in Proxmox terms.

## Maturity overview

| Level | Goal | Success criteria |
| --- | --- | --- |
| 1 | Identity foundation deployment | First template, foundation hosts, and the identity, DNS, and PKI services Vault depends on are in place |
| 2 | Vault foundation deployment | Vault is deployed as the early secret-platform foundation and ready for initialization |
| 3 | Backup foundation | PBS is deployed, connected, and tested |
| 4 | Higher availability and production use | Backup, recovery, and platform patterns support more serious use |

## Level 1 - Identity foundation deployment

Goal:

- copy the example files
- prepare the local deployment environment file
- build or prepare a template
- provision the first managed foundation hosts
- establish the identity, DNS, and certificate or PKI services Vault depends on
- apply the first Ansible baseline run
- keep Windows or AD support as a later optional path

Read more:

- [Platform guide](README.md)
- [Proxmox planning guidelines](conventions.md)
- [Environment variable conventions](../../reference/environment-variables.md)
- [Identity foundation path](../../foundation/identity-foundation-path.md)
- [Windows and AD support](../../foundation/windows-support.md)

## Level 2 - Vault foundation deployment

Goal:

- deploy Vault as a dedicated early shared service after the first Proxmox
  foundation hosts are ready
- initialize and unseal Vault
- move shared and long-lived secrets into Vault

Read more:

- [Vault foundation deployment](../../foundation/vault-foundation-deployment.md)
- [Secret strategy](../../security/secret-strategy.md)

## Level 3 - Backup foundation

Goal:

- deploy Proxmox Backup Server
- create a datastore
- add PBS to Proxmox VE as storage
- run and validate at least one backup and one restore

Read more:

- [Backup foundation](backup-foundation.md)
- [Host networking](network-prerequisites.md)
- [API setup](setup-api.md)

## Level 4 - Higher availability and production use

Goal:

- improve resilience, recovery, and operational confidence
- move beyond single-host assumptions where needed
- use the platform for more serious application and infrastructure services

Read more:

- [Architecture overview](../../architecture/overview.md)
- [Security principles](../../security/security-principles.md)
