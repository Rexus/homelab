# Environment variable conventions

## Table of contents

- [Purpose](#purpose)
- [When to use environment variables](#when-to-use-environment-variables)
- [Naming examples](#naming-examples)
- [Related references](#related-references)

## Purpose

This document defines the preferred environment variable patterns for bootstrap
secrets and runtime-sensitive values. Use it together with the
[secret strategy](../security/secret-strategy.md).

## When to use environment variables

Use environment variables for secrets and runtime-sensitive values. Keep
structured non-secret configuration in the example-based local files.

For normal local runs, keep those values in `.env.local`; the deployment
wrapper loads that file when it exists. Runners can provide the same variables
directly, and `--env-file` can point the wrapper at another file path.

## Naming examples

These are conventions, not hard requirements:

| Purpose | Example |
| --- | --- |
| platform API endpoint | `PROXMOX_API_URL` |
| platform token ID | `PROXMOX_API_TOKEN_ID` |
| platform token secret | `PROXMOX_API_TOKEN_SECRET` |
| Terraform secret input | `TF_VAR_proxmox_api_token_secret` |
| Ansible vault password source | `ANSIBLE_VAULT_PASSWORD_FILE` |
| Vault address | `VAULT_ADDR` |
| Vault token for bootstrap only | `VAULT_TOKEN` |

## Related references

- [Environment file example](environment-file-example.md)
- [Ansible Vault bootstrap](ansible-vault-bootstrap.md)
