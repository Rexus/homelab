# Documentation

## Table of contents

- [Recommended path](#recommended-path)
- [Overview and onboarding](#overview-and-onboarding)
- [Architecture and design](#architecture-and-design)
- [Platform guides](#platform-guides)
- [Security and hardening](#security-and-hardening)
- [Reference and decisions](#reference-and-decisions)

## Recommended path

Use this order when you are new to the repository or returning after time away:

1. [Safe repository usage](usage-model.md)
2. [Bootstrap path](getting-started/bootstrap-path.md)
3. [Vault bootstrap](getting-started/vault-bootstrap.md)
4. [Private cloud maturity path](getting-started/private-cloud-maturity-path.md)
5. [Architecture overview](architecture/overview.md)
6. [Platform index](platforms/README.md)
7. [Secret strategy](security/secret-strategy.md)
8. [Decision log](decisions/README.md)

If local tooling is not ready yet, insert
[Local setup](getting-started/local-setup.md) before the bootstrap path.

## Overview and onboarding

- [Safe repository usage](usage-model.md) - how to use this public upstream
  without publishing live configuration
- [Local setup](getting-started/local-setup.md) - prepare local tooling before
  the first run when needed
- [Bootstrap path](getting-started/bootstrap-path.md) - shortest path from local
  setup to the first managed platform services
- [Vault bootstrap](getting-started/vault-bootstrap.md) - recommended early
  secret-platform handoff for the first managed VM
- [Private cloud maturity path](getting-started/private-cloud-maturity-path.md) -
  path from initial deployment to backup, secrets, and more serious use

## Architecture and design

- [Architecture overview](architecture/overview.md) - layered zones, automation
  flow, and trust boundaries
- [Network zones and IaC mapping](architecture/network-zones-and-iac-mapping.md) -
  shared network reference for subnets, VLANs, bridges, and Terraform zone keys

## Platform guides

- [Platform index](platforms/README.md) - entry point for provider-specific
  guidance
- [Proxmox reference platform](platforms/proxmox/README.md) - current reference
  implementation and where to start if you are working on Proxmox
- [Proxmox API setup](platforms/proxmox/setup-api.md) - API access preparation
  for Terraform-driven bootstrap
- [Proxmox backup foundation](platforms/proxmox/backup-foundation.md) -
  recommended recovery baseline before the environment becomes important
- [Proxmox network prerequisites](platforms/proxmox/network-prerequisites.md) -
  network assumptions and preparation
- [Enterprise Linux template](platforms/proxmox/enterprise-linux-template.md) -
  guest template reference
- [Proxmox hardening](platforms/proxmox/hardening.md) - later-stage platform
  hardening guidance

## Security and hardening

- [Security principles](security/security-principles.md) - durable baseline for
  hardening, identity, and guardrails
- [Secret strategy](security/secret-strategy.md) - authoritative source for
  bootstrap secrets, ignored files, and the move to Vault
- [Vault HSM hardening options](security/vault-hsm-hardening-options.md) -
  Vault-focused note for later HSM hardening and PKCS#11 paths
- [HSM getting started](security/hsm-planning-and-comparison.md) - short guide
  with a practical use, scale, and cost matrix
- [Pico HSM active-active blueprint](security/picohsm-active-active-blueprint.md) -
  concrete USB HSM deployment reference with active-active service, shared
  network mapping, and offline backup

## Reference and decisions

- [Environment variable conventions](reference/environment-variables.md) -
  authoritative env-var patterns for bootstrap and CI execution
- [Environment file example](reference/environment-file-example.md) - local
  bootstrap example that complements the env-var conventions
- [Ansible Vault bootstrap](reference/ansible-vault-bootstrap.md) - local vault
  password and encrypted bootstrap vars pattern
- [Decision log](decisions/README.md) - concise record of architectural choices
