# Proxmox hardening baseline

## Table of contents

- [Purpose](#purpose)
- [Baseline posture](#baseline-posture)
- [Host-management access](#host-management-access)
- [API and identity](#api-and-identity)
- [Host and cluster hygiene](#host-and-cluster-hygiene)
- [Before automation](#before-automation)

## Purpose

Harden the Proxmox foundation before scaling automation use. The platform layer
should be trusted enough to host image builds, infrastructure provisioning, and
sensitive workloads without relying on broad default access.

## Baseline posture

Apply the repository security baseline to the Proxmox foundation before broad
automation use.

Read more in [Security principles](../../security/security-principles.md).

## Host-management access

Recommended practices:

- restrict the management interface to a dedicated host-management network
- avoid exposing administrative access through edge or public-facing paths
- use trusted jump paths if remote administration is required
- keep administrative source ranges small and documented
- review firewall policy between host-management and other zones

## API and identity

Use dedicated automation identities and keep API access aligned to actual tool
requirements.

Read more in:

- [API setup](setup-api.md)
- [Secret strategy](../../security/secret-strategy.md)

## Host and cluster hygiene

Before broad automation use:

- apply updates and confirm expected package sources
- review [Proxmox planning guidelines](conventions.md) and confirm cluster
  node, storage, and bridge naming are finalized
- disable or avoid unused services where practical
- review logs, time sync, and certificate handling
- keep host access limited to trusted operators and automation identities

## Before automation

Confirm the following before using Packer, Terraform, or Ansible broadly:

- host-management network access is restricted
- API automation access is tested and scoped
- external network prerequisites are working end-to-end
- storage targets and bridge names are finalized
- secret handling follows the documented secret strategy
