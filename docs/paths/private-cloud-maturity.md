# Private cloud maturity path

## Table of contents

- [Purpose](#purpose)
- [How to read this path](#how-to-read-this-path)
- [Capability groups](#capability-groups)
- [Dependency order](#dependency-order)
- [Maturity levels](#maturity-levels)
- [Platform preparation](#platform-preparation)
- [Shared services](#shared-services)
- [System control](#system-control)
- [Recovery](#recovery)
- [Application platform](#application-platform)
- [Security and cryptography](#security-and-cryptography)

## Purpose

Use this as the repository-wide maturity map for an enterprise-style private
cloud on homelab or small-datacenter scale.

The maturity model is grouped by capability. Each capability has its own
`Level 0`, `Level 1`, and `Level 2`. A level describes how mature that
capability is, not where it sits in the deployment order.

## How to read this path

Use this page in two ways:

- use [Dependency order](#dependency-order) to see what normally needs to exist
  before another setup can run
- use the capability sections to decide how far to mature each area

For every capability, choose one of these patterns:

| Pattern | Use it when |
| --- | --- |
| deploy from this repo | the environment starts clean and needs the reference path |
| connect to existing service | the capability already exists outside this repo |
| isolate for a project | the project needs a separate trust boundary, subnet set, or operator group |

Use `--env` for disposable or parallel environments such as `test`, `dev`,
`stage`, or `lab1`. Omit `--env` for production. Override subnets, VLANs, IPs,
or VM sizes only when an environment needs a different shape.

Read [Private cloud model](../architecture/private-cloud.md) before choosing
how much belongs on your own infrastructure and what should be offloaded to
public cloud.

## Capability groups

| Capability group | Owns | Main path |
| --- | --- | --- |
| platform preparation | Proxmox, API access, templates, networking, deployment tooling | [Proxmox reference platform](../platforms/proxmox/README.md) |
| shared services | identity, DNS, PKI, edge, cache, Vault, and optional Windows support | [Shared services path](shared-services/README.md) |
| system control | telemetry, syslog, metrics, traces, logs, dashboards, and archive | [System control path](system-control/README.md) |
| recovery | backup, restore, and disaster recovery readiness | [Backup foundation](../platforms/proxmox/backup-foundation.md) |
| application platform | development platform, registry, image-based Linux, Kubernetes, and project runtimes | [Application platform path](application-platform/README.md) |
| security and cryptography | HSM planning, USB HSM topology, Vault hardening, and secret strategy | [Security and hardening](../security/security-principles.md) |

## Dependency order

This is the normal dependency flow for a clean environment:

| Step | Capability | Why it comes here |
| --- | --- | --- |
| 1 | platform preparation | Terraform, Ansible, API access, networks, and templates must exist first |
| 2 | shared services: identity and PKI | DNS, identity, and certificates become prerequisites for later services |
| 3 | shared services: edge | ingress and controlled north-south routing become available early |
| 4 | shared services: Vault | secrets move out of local bootstrap files after identity and PKI exist |
| 5 | shared services: cache | restricted systems can get controlled outbound update access when needed |
| 6 | system control | telemetry and logs become shared before the platform grows too far |
| 7 | recovery | backups and restore tests protect the environment before it becomes important |
| 8 | application platform | development, registry, image-based Linux, GitOps, Kubernetes, and projects consume the shared foundation |
| 9 | security and cryptography | HSM and stronger key custody can harden selected PKI and Vault paths |

If a dependency already exists, map the repo to that service instead of
deploying a duplicate.

## Maturity levels

Use the same level meaning inside each capability group:

| Level | Meaning |
| --- | --- |
| 0 | prerequisites, planning, or mapping to an existing service |
| 1 | first useful deployment that other paths can consume |
| 2 | hardened, redundant, scaled, or isolated production-style shape |

## Platform preparation

| Level | Meaning | Read |
| --- | --- | --- |
| 0 | Proxmox, networks, storage, and local tooling are planned | [Local setup](../getting-started/local-setup.md), [Host networking](../platforms/proxmox/network-prerequisites.md) |
| 1 | API access, templates, and deployment wrapper are ready | [API setup](../platforms/proxmox/setup-api.md), [Enterprise Linux template](../platforms/proxmox/enterprise-linux-template.md) |
| 2 | platform conventions, hardening, and operational patterns are established | [Planning guidelines](../platforms/proxmox/conventions.md), [Proxmox hardening](../platforms/proxmox/hardening.md) |

## Shared services

| Level | Meaning | Read |
| --- | --- | --- |
| 0 | existing identity, DNS, PKI, edge, Vault, or cache services are mapped | [Shared services model](../architecture/shared-services.md) |
| 1 | identity, DNS, issuing CA, edge, and Vault are deployed or connected | [Identity foundation path](shared-services/identity.md), [Edge proxy path](shared-services/edge.md), [Vault foundation deployment](shared-services/vault.md) |
| 2 | shared services are redundant, hardened, and expanded with cache or Windows support where needed | [Cache path](shared-services/cache.md), [Windows and AD support](shared-services/windows-support.md), [Secret strategy](../security/secret-strategy.md) |

## System control

| Level | Meaning | Read |
| --- | --- | --- |
| 0 | telemetry and log sources are identified | [System control path](system-control/README.md) |
| 1 | first telemetry, syslog, metrics, logs, dashboards, and archive hosts exist | [Observability path](system-control/observability.md) |
| 2 | collectors, log stores, retention, alerting, and isolated project telemetry are scaled where needed | [Observability path](system-control/observability.md), [Network architecture](../architecture/network.md) |

## Recovery

| Level | Meaning | Read |
| --- | --- | --- |
| 0 | backup targets and restore expectations are planned | [Backup foundation](../platforms/proxmox/backup-foundation.md) |
| 1 | Proxmox Backup Server or another recovery target is connected and tested | [Backup foundation](../platforms/proxmox/backup-foundation.md) |
| 2 | restore drills, retention, offsite copies, and service-specific recovery paths are proven | [Secret strategy](../security/secret-strategy.md), [Security principles](../security/security-principles.md) |

## Application platform

| Level | Meaning | Read |
| --- | --- | --- |
| 0 | project and lab boundaries are planned | [Private cloud model](../architecture/private-cloud.md), [Infrastructure automation layout](../reference/infrastructure-automation-layout.md) |
| 1 | first development platform, Podman runner, registry, image-based Linux path, or project environment consumes shared services | [Development platform path](application-platform/development.md), [Podman image runner guide](application-platform/podman-runner.md), [Container registry path](application-platform/registry.md), [Image-based Linux path](application-platform/image-based-linux.md) |
| 2 | Kubernetes, GitOps, runners, registries, OS image promotion, and isolated worker clusters support broader application use | [Kubernetes platform path](application-platform/kubernetes.md) |

## Security and cryptography

| Level | Meaning | Read |
| --- | --- | --- |
| 0 | secret ownership, key custody, and HSM need are planned | [Secret strategy](../security/secret-strategy.md), [HSM getting started](../security/hsm-planning-and-comparison.md) |
| 1 | local secret handling is reduced and selected keys have clear custody | [Vault HSM hardening options](../security/vault-hsm-hardening-options.md) |
| 2 | HSM-backed or ceremony-backed paths protect selected PKI, Vault, or signing workflows | [USB HSM active-active blueprint](../security/usb-hsm-active-active-blueprint.md) |
