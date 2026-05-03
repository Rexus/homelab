# Documentation

## Table of contents

- [Recommended path](#recommended-path)
- [Start here](#start-here)
- [Reader paths](#reader-paths)
- [Path guides](#path-guides)
- [Architecture and design](#architecture-and-design)
- [Platform guides](#platform-guides)
- [Security and hardening](#security-and-hardening)
- [Reference and decisions](#reference-and-decisions)

## Recommended path

Use this order when you are new to the repository or returning after time away:

1. [Safe repository usage](usage-model.md)
2. [Local setup](getting-started/local-setup.md)
3. [Repository scripts](reference/repository-scripts.md)
4. [Reader paths](paths/README.md)
5. [Shared services path](paths/shared-services/README.md)
6. [Private cloud maturity path](paths/private-cloud-maturity.md)
7. [Architecture overview](architecture/overview.md)
8. [Private cloud model](architecture/private-cloud.md)
9. [Platform index](platforms/README.md)
10. [Secret strategy](security/secret-strategy.md)
11. [Decision log](decisions/README.md)

## Start here

- [Safe repository usage](usage-model.md) - how to use this public upstream
  without publishing live configuration
- [Local setup](getting-started/local-setup.md) - prepare local tooling before
  the first run when needed
- [Repository scripts](reference/repository-scripts.md) - what the wrapper
  scripts do and how to run the equivalent Terraform and Ansible steps manually
- [Private cloud maturity path](paths/private-cloud-maturity.md) -
  capability-grouped path from platform preparation to shared services, system
  control, recovery, and application-platform growth

## Reader paths

- [Reader paths](paths/README.md) - task-oriented routes through the docs
  without duplicating the source documents

## Path guides

- [Shared services path](paths/shared-services/README.md) - entry point for
  identity, DNS, PKI, edge, cache, Vault, and optional Windows support
- [Identity foundation path](paths/shared-services/identity.md) - shortest
  path from local setup to the first managed identity and PKI foundation layer
- [Hardware-backed user authentication](paths/shared-services/hardware-keys.md) -
  optional YubiKey, OTP, and PIV hardening after identity is stable
- [Windows and AD support](paths/shared-services/windows-support.md) - optional
  secondary path for Windows clients and AD-compatible support
- [Vault foundation deployment](paths/shared-services/vault.md) -
  early secret-platform deployment after the identity, DNS, and PKI
  prerequisites exist
- [Edge proxy path](paths/shared-services/edge.md) - shared edge load
  balancing, ingress, egress, and service backend entry point
- [Cache path](paths/shared-services/cache.md) - optional outbound cache for
  restricted update access
- [System control path](paths/system-control/README.md) - telemetry backbone,
  syslog, metrics, traces, and log/event search after Vault
- [Application platform path](paths/application-platform/README.md) - source
  control, automation, runners, registry, image-based Linux, Kubernetes, and
  GitOps direction for internal projects
- [Development platform path](paths/application-platform/development.md) -
  GitLab on a dedicated Podman VM after identity and PKI exist
- [Podman image runner guide](paths/application-platform/podman-runner.md) -
  Terraform and Ansible shape for the first GitLab-stage bootc build runner
- [Container registry path](paths/application-platform/registry.md) - Harbor
  as the shared OCI artifact registry after GitLab
- [Image-based Linux path](paths/application-platform/image-based-linux.md) -
  bootc reference builds and the `image-template` Proxmox template lifecycle

## Architecture and design

- [Architecture overview](architecture/overview.md) - layered zones, automation
  flow, and trust boundaries
- [Private cloud model](architecture/private-cloud.md) - what private cloud
  means here and when Proxmox, Kubernetes, or OpenStack fit
- [Shared services model](architecture/shared-services.md) - why identity, PKI,
  Vault, and observability form the reusable private-domain backbone
- [Network architecture](architecture/network.md) - shared network reference
  for zones, VLAN strategy, bridges, and Terraform guest placement keys

## Platform guides

- [Platform index](platforms/README.md) - entry point for provider-specific
  guidance
- [Proxmox reference platform](platforms/proxmox/README.md) - current reference
  implementation and where to start if you are working on Proxmox
- [Proxmox API setup](platforms/proxmox/setup-api.md) - API access preparation
  for Terraform-driven foundation and platform bring-up
- [Proxmox backup foundation](platforms/proxmox/backup-foundation.md) -
  recommended recovery baseline before the environment becomes important
- [Proxmox host networking](platforms/proxmox/network-prerequisites.md) -
  network assumptions and preparation
- [Enterprise Linux template](platforms/proxmox/enterprise-linux-template.md) -
  guest template creation and refresh reference
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
- [USB HSM active-active blueprint](security/usb-hsm-active-active-blueprint.md) -
  concrete USB HSM deployment reference with active-active service, shared
  network mapping, and Pico HSM as the current reference implementation

## Reference and decisions

- [Environment variable conventions](reference/environment-variables.md) -
  authoritative env-var patterns for bootstrap and CI execution
- [Environment file example](reference/environment-file-example.md) - local
  foundation example that complements the env-var conventions
- [Infrastructure automation layout](reference/infrastructure-automation-layout.md) -
  where the Terraform, Ansible, Packer, and wrapper code lives
- [Repository scripts](reference/repository-scripts.md) - wrapper commands,
  environment handling, and manual command equivalents
- [Ansible Vault bootstrap](reference/ansible-vault-bootstrap.md) - local vault
  password and encrypted bootstrap vars pattern
- [Decision log](decisions/README.md) - concise record of architectural choices
