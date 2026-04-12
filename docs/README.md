# Documentation

## Table of contents

- [Start here](#start-here)
- [Usage and architecture](#usage-and-architecture)
- [Security and decisions](#security-and-decisions)
- [Platform references](#platform-references)

## Start here

- [Private cloud maturity path](getting-started/private-cloud-maturity-path.md) -
  path from first test to backup, secrets, and more serious use
- [Safe repository usage](usage-model.md) - how to use this public upstream
  without publishing live configuration

## Usage and architecture

- [Architecture overview](architecture/overview.md) - layered zones, automation
  flow, and trust boundaries

## Security and decisions

- [Security principles](security/security-principles.md) - durable baseline for
  hardening, identity, and guardrails
- [Secret strategy](security/secret-strategy.md) - authoritative source for
  bootstrap secrets, ignored files, and the move to Vault
- [Environment variable conventions](reference/environment-variables.md) -
  preferred env-var patterns for bootstrap and CI execution
- [Environment file example](reference/environment-file-example.md) - local
  bootstrap example for ignored env files and runner variables
- [Ansible Vault bootstrap](reference/ansible-vault-bootstrap.md) - local vault
  password and encrypted bootstrap vars pattern
- [Decision log](decisions/README.md) - concise record of architectural choices

## Platform references

- [Platform index](../platforms/README.md)
- [Proxmox reference platform](../platforms/proxmox/README.md)
