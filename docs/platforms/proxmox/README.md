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

## What this covers

Use the Proxmox platform layer for:

- API token setup and least-privilege access
- node, bridge, and storage naming conventions
- template publication from Packer
- VM provisioning from Terraform
- host and guest configuration touchpoints from Ansible

## Platform guides

- [Enterprise Linux template](enterprise-linux-template.md)
- [Backup foundation](backup-foundation.md)
- [API setup](setup-api.md)
- [Network prerequisites](network-prerequisites.md)
- [Hardening baseline](hardening.md)

## First deployment order

1. Create the automation API token.
2. Prepare the first Enterprise Linux template.
3. Run the first Terraform-based VM deployment.
4. Apply the first Ansible baseline.

Recommended next maturity step:

- add the [backup foundation](backup-foundation.md) before the environment
  becomes important

## Related references

- [Private cloud maturity path](../../getting-started/private-cloud-maturity-path.md)
- [Proxmox maturity path](../../getting-started/proxmox-maturity-path.md)
- [Safe repository usage](../../usage-model.md)
- [Secret strategy](../../security/secret-strategy.md)
- [Security principles](../../security/security-principles.md)
