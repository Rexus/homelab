# Reader paths

## Purpose

Use this page when you know what you want to accomplish but not which document
to open first.

Paths are navigation routes. They point you through the right topic documents
without copying the authoritative docs from `platforms`, `security`,
`architecture`, and `reference`.

## Paths

| Path | Start here | Then read |
| --- | --- | --- |
| Private cloud model | [Private cloud model](../architecture/private-cloud.md) | [Architecture overview](../architecture/overview.md), [Proxmox reference platform](../platforms/proxmox/README.md) |
| First shared-service run | [Local setup](../getting-started/local-setup.md) | [Repository scripts](../reference/repository-scripts.md), [Identity foundation path](shared-services/identity.md) |
| Proxmox platform preparation | [Proxmox reference platform](../platforms/proxmox/README.md) | [API setup](../platforms/proxmox/setup-api.md), [Enterprise Linux template](../platforms/proxmox/enterprise-linux-template.md), [Host networking](../platforms/proxmox/network-prerequisites.md) |
| Shared services model | [Shared services model](../architecture/shared-services.md) | [Shared services path](shared-services/README.md), [Private cloud maturity path](private-cloud-maturity.md) |
| Identity and PKI foundation | [Shared services path](shared-services/README.md) | [Identity foundation path](shared-services/identity.md), [Network architecture](../architecture/network.md) |
| Vault foundation | [Vault foundation deployment](shared-services/vault.md) | [Secret strategy](../security/secret-strategy.md), [Ansible Vault bootstrap](../reference/ansible-vault-bootstrap.md) |
| Observability foundation | [Observability path](observability.md) | [Shared services model](../architecture/shared-services.md), [Network architecture](../architecture/network.md) |
| Development platform | [Development platform path](development.md) | [Shared services model](../architecture/shared-services.md), [Private cloud model](../architecture/private-cloud.md) |
| Windows support | [Windows and AD support](shared-services/windows-support.md) | [Identity foundation path](shared-services/identity.md) |
| HSM and cryptography lab | [HSM getting started](../security/hsm-planning-and-comparison.md) | [USB HSM active-active blueprint](../security/usb-hsm-active-active-blueprint.md), [Vault HSM hardening options](../security/vault-hsm-hardening-options.md) |
| Maturing the private cloud | [Private cloud maturity path](private-cloud-maturity.md) | [Backup foundation](../platforms/proxmox/backup-foundation.md), [Security principles](../security/security-principles.md) |

## How to use paths

Start with the path, then follow the linked topic docs. If a topic doc owns a
configuration detail, keep the detail there and link back to it instead of
copying the same steps into another guide.
