# Proxmox reference platform

## Table of contents

- [Purpose](#purpose)
- [What this covers](#what-this-covers)
- [Platform guides](#platform-guides)
- [First deployment order](#first-deployment-order)
- [Related references](#related-references)

## Purpose

Proxmox is the current reference foundation for the hypervisor and initial
infrastructure layer in this repository. It provides the cluster, storage,
networking, and API surface used by the first image build, provisioning, and
configuration workflows.

Use [Private cloud model](../../architecture/private-cloud.md) to understand
where Proxmox fits compared with a later Kubernetes layer or an OpenStack-style
private cloud.

## What this covers

Use the Proxmox platform layer for:

- shared Proxmox planning guidelines such as VM ID ranges and template naming
- API token setup and least-privilege access
- node, bridge, and storage naming conventions
- template publication from Packer
- VM provisioning from Terraform
- host and guest configuration touchpoints from Ansible

## Platform guides

- [Planning guidelines](conventions.md)
- [Enterprise Linux template](enterprise-linux-template.md)
- [Backup foundation](backup-foundation.md)
- [API setup](setup-api.md)
- [Host networking](network-prerequisites.md)
- [Hardening baseline](hardening.md)

## First deployment order

1. Review the shared Proxmox planning guidelines.
2. Create the automation API token.
3. Prepare the first Enterprise Linux template.
4. Run the first identity foundation Terraform deployment.
5. Apply the first Ansible baseline.

Recommended next maturity step:

- continue with the
  [Identity foundation path](../../paths/shared-services/identity.md)
- add
  [Windows and AD support](../../paths/shared-services/windows-support.md) only when
  the environment needs Windows support
- continue with the
  [Vault foundation deployment](../../paths/shared-services/vault.md)
- add the [backup foundation](backup-foundation.md) before the environment
  becomes important

## Related references

- [Private cloud maturity path](../../paths/private-cloud-maturity.md)
- [Proxmox maturity path](maturity-path.md)
- [Safe repository usage](../../usage-model.md)
- [Secret strategy](../../security/secret-strategy.md)
- [Security principles](../../security/security-principles.md)
