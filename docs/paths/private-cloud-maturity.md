# Private cloud maturity path

## Table of contents

- [Purpose](#purpose)
- [How to read this path](#how-to-read-this-path)
- [Maturity overview](#maturity-overview)
- [Level 0 - Platform preparation](#level-0---platform-preparation)
- [Level 1 - Shared private-domain services](#level-1---shared-private-domain-services)
- [Level 2 - Vault and secret management](#level-2---vault-and-secret-management)
- [Level 3 - Observability and syslog](#level-3---observability-and-syslog)
- [Level 4 - Backup and recovery](#level-4---backup-and-recovery)
- [Level 5 - Project and lab expansion](#level-5---project-and-lab-expansion)
- [Level 6 - Higher availability and application platform](#level-6---higher-availability-and-application-platform)

## Purpose

Use this as the authoritative maturity path for the repository. It grows the
environment from an initial working deployment toward a more resilient and
production-ready private cloud. The pattern is aimed at enterprise-style
operation on a homelab or small-datacenter scale. Proxmox is the current
reference foundation, but the maturity path is about the broader platform.

## How to read this path

The levels describe capabilities, not a mandatory install order.

For every shared service, choose one of these patterns:

| Pattern | Use it when |
| --- | --- |
| deploy from this repo | the environment starts clean and needs the reference path |
| connect to existing service | identity, DNS, PKI, Vault, or telemetry already exists |
| isolate for a lab or project | the project needs a separate trust boundary or subnet set |

The first production-quality shape is a shared private-domain service layer:
DNS, identity, PKI, Vault, syslog, and observability. Other labs and projects
can consume that layer instead of deploying their own identity system.

Use `--env` for disposable or parallel environments such as `test`, `dev`,
`stage`, or `lab1`. Omit `--env` for production. Override subnets, VLANs, IPs,
or VM sizes only when an environment needs a different shape.

## Maturity overview

| Level | Goal | Success criteria |
| --- | --- | --- |
| 0 | Platform preparation | Proxmox, API access, templates, local repo files, and deployment tooling are ready |
| 1 | Shared private-domain services | DNS, identity, and PKI are deployed here or mapped to existing services |
| 2 | Vault and secret management | Vault or an existing secret platform becomes the shared secret handoff |
| 3 | Observability and syslog | telemetry, syslog, metrics, traces, logs, and audit events have a shared path |
| 4 | Backup and recovery | PBS or another recovery path is deployed, connected, and tested |
| 5 | Project and lab expansion | isolated labs and projects consume shared services or define their own boundary |
| 6 | Higher availability and application platform | Kubernetes, GitOps, and HA patterns support broader application use |

## Level 0 - Platform preparation

Goal:

- prepare Proxmox, API access, and the first Linux template
- prepare the deployment machine with Terraform and Ansible
- initialize ignored local config files
- use a disposable environment before production

Read more:

- [Local setup](../getting-started/local-setup.md)
- [Repository scripts](../reference/repository-scripts.md)
- [Proxmox reference platform](../platforms/proxmox/README.md)
- [Enterprise Linux template](../platforms/proxmox/enterprise-linux-template.md)

## Level 1 - Shared private-domain services

Goal:

- copy the example files
- prepare the local deployment environment file
- build or prepare a template
- provision the private-domain hosts when you use the repo reference path
- establish or map the identity, DNS, and PKI services Vault depends on
- use the current reference shape of `2` identity hosts and `1` issuing CA
- apply the baseline playbook so the hosts are managed
- keep Windows or AD support as a separate path
- skip this deployment when existing identity, DNS, and PKI already satisfy
  the later paths

Read more:

- [Platform guide](../platforms/proxmox/README.md)
- [Environment variable conventions](../reference/environment-variables.md)
- [Shared services model](../architecture/shared-services.md)
- [Identity foundation path](shared-services/identity.md)
- [Windows and AD support](shared-services/windows-support.md)

## Level 2 - Vault and secret management

Goal:

- deploy Vault as a dedicated shared service after identity, DNS, and PKI are
  available, or map later paths to an existing secret platform
- initialize and unseal Vault
- move shared and long-lived secrets into Vault
- keep local Ansible Vault files as the fallback bootstrap path, not the main
  long-term secret system
- keep HSM hardening as an upgrade path for selected keys and seal patterns

Read more:

- [Vault foundation deployment](shared-services/vault.md)
- [Secret strategy](../security/secret-strategy.md)
- [Vault HSM hardening options](../security/vault-hsm-hardening-options.md)

## Level 3 - Observability and syslog

Goal:

- define the telemetry gateway and syslog intake pattern
- collect platform health, metrics, logs, traces, and security events through
  controlled collectors
- keep sources away from direct backend access
- establish the live health, metrics, APM, log search, and archive roles
- decide which parts are shared and which high-risk projects need isolated
  telemetry or archive paths

Read more:

- [Observability path](observability.md)
- [Network architecture](../architecture/network.md)
- [Security principles](../security/security-principles.md)

## Level 4 - Backup and recovery

Goal:

- add Proxmox Backup Server before the environment becomes important
- create a datastore
- add PBS to Proxmox VE as storage
- run and validate at least one backup and one restore

Read more:

- [Backup foundation](../platforms/proxmox/backup-foundation.md)
- [Host networking](../platforms/proxmox/network-prerequisites.md)
- [API setup](../platforms/proxmox/setup-api.md)

## Level 5 - Project and lab expansion

Goal:

- deploy labs and project environments without duplicating shared identity by
  default
- use separate state and environment overlays for test, dev, stage, lab, or
  production copies
- give isolated projects their own subnets, VLANs, Vault, telemetry, or
  identity only when the trust boundary requires it
- prepare the development path around GitLab or another source platform that
  consumes shared identity, PKI, Vault, and telemetry

Read more:

- [Shared services model](../architecture/shared-services.md)
- [Development platform path](development.md)
- [Infrastructure automation layout](../reference/infrastructure-automation-layout.md)
- [Network architecture](../architecture/network.md)

## Level 6 - Higher availability and application platform

Goal:

- improve resilience, recovery, and operational confidence
- move beyond single-host assumptions where needed
- use the platform for more serious application and infrastructure services
- introduce Kubernetes as the application platform when application scale,
  GitOps, namespaces, and worker-cluster isolation become the main need

Read more:

- [Architecture overview](../architecture/overview.md)
- [Private cloud model](../architecture/private-cloud.md)
- [Security principles](../security/security-principles.md)
