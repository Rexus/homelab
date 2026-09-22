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

1. [Generate the collection](reference/generated-repository-model.md#purpose-and-prerequisites).
2. [Record project choices](reference/project-documentation.md#start-with-project-values).
3. Follow your repo's deployment checklist: [Tier 0](paths/tier-0/README.md),
   [Tier 1](paths/tier-1/README.md), [Tier 2](paths/tier-2/README.md), or
   [shared automation](paths/shared/README.md).

For a new environment, the Tier 0 checklist takes you through **Proxmox ->
optional HA/SDN -> templates -> Talos or Linux services -> Day 2 services**.
Read the [architecture overview](architecture/overview.md) when you need the
ownership and network design behind those steps.

For the first command, use the [generation quick start](reference/generated-repository-model.md#purpose-and-prerequisites).
Use the sections below as a reference map, not a required reading list.

## Start here

- [Safe repository usage](usage-model.md) - how to use this public upstream
  without publishing live configuration
- [Local setup](getting-started/local-setup.md) - prepare local tooling before
  the first run when needed
- [Repository scripts](reference/repository-scripts.md) - what the wrapper
  scripts do and how to run the equivalent Terraform and Ansible steps manually
- [Tier model](architecture/tier-model.md) - Tier 0, Tier 1, Tier 2, shared,
  and architecture ownership language for this repository
- [Generated repository model](reference/generated-repository-model.md) -
  per-tier inventories and state, shared automation, generation, and refresh
- [Private cloud maturity path](paths/private-cloud-maturity.md) -
  capability-grouped path from platform preparation to shared services, system
  control, recovery, and application-platform growth

## Reader paths

- [Reader paths](paths/README.md) - task-oriented routes through the docs
  without duplicating the source documents

## Path guides

- [Tier 0 path](paths/tier-0/README.md) - hosts, templates, control cluster, and trust services
- [Tier 1 path](paths/tier-1/README.md) - shared platform capabilities and optional Kubernetes
- [Tier 2 path](paths/tier-2/README.md) - project and lab workloads
- [Shared automation](paths/shared/README.md) - common code, not a standalone deployment
- [Shared services path](paths/shared-services/README.md) - entry point for
  identity, DNS, PKI, edge, cache, secrets, and optional Windows support
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
  syslog, metrics, traces, and log/event search after the secret platform
- [Application platform path](paths/application-platform/README.md) - source
  control, automation, runners, registry, image-based Linux, Kubernetes, and
  GitOps direction for internal projects
- [Development platform path](paths/application-platform/development.md) -
  source control and CI/CD on a dedicated Podman VM after identity and PKI exist
- [Podman image runner guide](paths/application-platform/podman-runner.md) -
  Terraform and Ansible shape for the first source-control runner
- [Container registry path](paths/application-platform/registry.md) - Harbor
  as the shared OCI artifact registry after source control
- [Image-based Linux path](paths/application-platform/image-based-linux.md) -
  bootc reference builds and the `immutable-template` Proxmox template lifecycle

## Architecture and design

- [Architecture overview](architecture/overview.md) - horizontal security layers,
  vertical tiers, automation flow, and trust boundaries
- [Tier model](architecture/tier-model.md) - potential impact, recovery, and ownership
  boundaries for Tier 0, Tier 1, Tier 2, shared, and architecture repositories
- [Infrastructure control](architecture/infrastructure-control.md) - Tier 0 hardware authority,
  Day 0-1 templates, and the future contract for Tier 2 VM requests
- [Private cloud model](architecture/private-cloud.md) - what private cloud
  means here and when Proxmox, Kubernetes, or OpenStack fit
- [Shared services model](architecture/shared-services.md) - why identity, PKI,
  secrets, and observability form the reusable private-domain backbone
- [Network placement](architecture/network.md) - simple purpose-based zones,
  subnet placement, and VLAN conventions, independent of repo tiers

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
- [Proxmox cluster and HA](platforms/proxmox/cluster-ha.md) - optional early cluster,
  failover, movable guests, and Terraform placement
- [Talos cluster bootstrap](platforms/talos/bootstrap.md) - one operator procedure
  shared by Tier 0 and Tier 1
- [UniFi zone firewall](platforms/unifi/zone-firewall.md) - translate the
  architecture's zones and rule matrix into gateway configuration
- [Enterprise Linux template](platforms/proxmox/enterprise-linux-template.md) -
  guest template creation and refresh reference
- [Tier 0 template lifecycle](platforms/proxmox/template-lifecycle.md) - image
  publication, updates, GitLab CD example, local recovery, and ownership migration
- [Shared template references](platforms/proxmox/template-catalog.md) - one consumer
  catalog for approved IDs/titles and image metadata; recipes stay in Tier 0
- [Talos template](platforms/proxmox/talos-template.md) - unconfigured NoCloud
  image publication and its boundary with Tier 0 cluster bootstrap
- [Proxmox hardening](platforms/proxmox/hardening.md) - later-stage platform
  hardening guidance

## Security and hardening

- [Security principles](security/security-principles.md) - durable baseline for
  hardening, identity, and guardrails
- [Firewall policy](security/firewall-policy.md) - source/destination matrix,
  scoped rule contracts, enforcement boundaries, and validation
- [Secret strategy](security/secret-strategy.md) - authoritative source for
  bootstrap secrets, ignored files, and the move to a secret platform
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
- [Network inputs](reference/network-inputs.md) - map each tier's guests into
  Terraform guest attachments without confusing them with firewall zones
- [Generated repository model](reference/generated-repository-model.md) -
  private downstream repository set and generated-vs-owned content model
- [Project documentation](reference/project-documentation.md) - developer-owned
  READMEs, a short naming/tag/VMID/VLAN worksheet, and refreshable auto-docs
- [Repository scripts](reference/repository-scripts.md) - wrapper commands,
  environment handling, and manual command equivalents
- [Ansible Vault bootstrap](reference/ansible-vault-bootstrap.md) - local
  Ansible Vault password and encrypted bootstrap vars pattern
- [Decision log](decisions/README.md) - concise record of architectural choices
