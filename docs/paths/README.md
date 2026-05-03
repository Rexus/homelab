# Reader paths

## Purpose

Use this page when you know what you want to accomplish but not which document
to open first.

Paths are navigation routes. They point you through the right topic documents
without copying the authoritative docs from `platforms`, `security`,
`architecture`, and `reference`.

## Capability groups

Use the same group names when reading the docs or browsing the repository:

| Capability group | Folder or source | What belongs there |
| --- | --- | --- |
| platform preparation | `docs/platforms/` | Proxmox, templates, API setup, networking, backup, and host operations |
| shared services | `docs/paths/shared-services/` | identity, DNS, PKI, edge, cache, Vault, and Windows support |
| system control | `docs/paths/system-control/` | telemetry, syslog, metrics, traces, logs, dashboards, and archive |
| application platform | `docs/paths/application-platform/` | development platform, registry, image-based Linux, Kubernetes, and app runtime patterns |
| security and cryptography | `docs/security/` | secret strategy, HSM planning, USB HSM topology, and Vault hardening |
| architecture and reference | `docs/architecture/`, `docs/reference/` | durable models, repo usage, scripts, variables, and layout |

## Paths

| Path | Start here | Then read |
| --- | --- | --- |
| Private cloud model | [Private cloud model](../architecture/private-cloud.md) | [Architecture overview](../architecture/overview.md), [Proxmox reference platform](../platforms/proxmox/README.md) |
| First shared-service run | [Local setup](../getting-started/local-setup.md) | [Repository scripts](../reference/repository-scripts.md), [Identity foundation path](shared-services/identity.md) |
| Proxmox platform preparation | [Proxmox reference platform](../platforms/proxmox/README.md) | [API setup](../platforms/proxmox/setup-api.md), [Enterprise Linux template](../platforms/proxmox/enterprise-linux-template.md), [Host networking](../platforms/proxmox/network-prerequisites.md) |
| Shared services model | [Shared services model](../architecture/shared-services.md) | [Shared services path](shared-services/README.md), [Private cloud maturity path](private-cloud-maturity.md) |
| Identity and PKI foundation | [Shared services path](shared-services/README.md) | [Identity foundation path](shared-services/identity.md), [Network architecture](../architecture/network.md) |
| Vault foundation | [Vault foundation deployment](shared-services/vault.md) | [Secret strategy](../security/secret-strategy.md), [Ansible Vault bootstrap](../reference/ansible-vault-bootstrap.md) |
| Edge proxy | [Edge proxy path](shared-services/edge.md) | [Network architecture](../architecture/network.md), [Shared services model](../architecture/shared-services.md) |
| Cache | [Cache path](shared-services/cache.md) | [Network architecture](../architecture/network.md), [Security principles](../security/security-principles.md) |
| System control | [System control path](system-control/README.md) | [Observability path](system-control/observability.md), [Network architecture](../architecture/network.md) |
| Application platform | [Application platform path](application-platform/README.md) | [Development platform path](application-platform/development.md), [Podman image runner guide](application-platform/podman-runner.md), [Container registry path](application-platform/registry.md), [Image-based Linux path](application-platform/image-based-linux.md), [Kubernetes platform path](application-platform/kubernetes.md) |
| Windows support | [Windows and AD support](shared-services/windows-support.md) | [Identity foundation path](shared-services/identity.md) |
| HSM and cryptography | [HSM getting started](../security/hsm-planning-and-comparison.md) | [USB HSM active-active blueprint](../security/usb-hsm-active-active-blueprint.md), [Vault HSM hardening options](../security/vault-hsm-hardening-options.md) |
| Maturing the private cloud | [Private cloud maturity path](private-cloud-maturity.md) | [Backup foundation](../platforms/proxmox/backup-foundation.md), [Security principles](../security/security-principles.md) |

## How to use paths

Start with the path, then follow the linked topic docs. If a topic doc owns a
configuration detail, keep the detail there and link back to it instead of
copying the same steps into another guide.
