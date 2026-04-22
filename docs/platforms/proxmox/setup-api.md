# Proxmox API setup

## Table of contents

- [Purpose](#purpose)
- [Goal state](#goal-state)
- [Prerequisites](#prerequisites)
- [Setup pattern](#setup-pattern)
- [Least-privilege guidance](#least-privilege-guidance)
- [Validation](#validation)

## Purpose

Use a dedicated API identity for automation instead of relying on interactive
administrator logins. The goal is to give Packer, Terraform, and other tooling
a stable but scoped way to access the platform.

## Goal state

The preferred end state is a dedicated automation identity with only the access
required for current workflows.

## Prerequisites

Before creating automation access:

- complete the [host networking](network-prerequisites.md)
- review the [hardening baseline](hardening.md)
- define which operations automation must perform
- review the [secret strategy](../../security/secret-strategy.md)

## Setup pattern

Use this pattern:

1. create a dedicated automation identity
2. assign the smallest practical role or permission scope
3. create a token for that identity
4. store the token according to the [secret strategy](../../security/secret-strategy.md)
5. test read access first, then test only the required write paths

Keep the token separate from personal administrator access.

## Least-privilege guidance

Prefer:

- one automation identity per purpose where practical
- separate identities for image build and infrastructure provisioning if their
  scopes differ significantly
- explicit review of cluster, storage, VM, and network permissions
- rotation of tokens when ownership, scope, or trust boundaries change

For broader identity and secret guidance, read:

- [Security principles](../../security/security-principles.md)
- [Secret strategy](../../security/secret-strategy.md)

## Validation

Validate the API setup before proceeding:

- confirm the token can authenticate successfully
- confirm it can perform only the required actions
- confirm failed access for actions outside intended scope
- confirm secret handling follows the documented secret strategy
