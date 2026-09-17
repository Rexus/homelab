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

For Linux deployments through `deploy.sh`, set `PROXMOX_API_URL` to the Proxmox
web/API root, such as `https://pve.example.com:8006/`. Do not append
`/api2/json`; that full path is used by the HashiCorp Packer Proxmox plugin
through its own `PROXMOX_URL` variable.

The separate [template publisher](../platforms/proxmox/template-lifecycle.md#local-workflow)
uses the provider-native `PROXMOX_VE_ENDPOINT` and `PROXMOX_VE_API_TOKEN`
environment variables. It does not load `.env.local` or map the Linux wrapper's aliases.

## Naming examples

These are conventions, not hard requirements:

| Purpose | Example |
| --- | --- |
| Linux deployment Proxmox endpoint | `PROXMOX_API_URL` |
| Template publication endpoint and combined token | `PROXMOX_VE_ENDPOINT`, `PROXMOX_VE_API_TOKEN` |
| platform token ID | `PROXMOX_API_TOKEN_ID` |
| platform token secret | `PROXMOX_API_TOKEN_SECRET` |
| Packer Proxmox endpoint | `PROXMOX_URL` |
| Terraform secret input | `TF_VAR_proxmox_api_token_secret` |
| Ansible vault password source | `ANSIBLE_VAULT_PASSWORD_FILE` |
| Vault address | `VAULT_ADDR` |
| Vault token for bootstrap only | `VAULT_TOKEN` |

## Related references

- [Environment file example](environment-file-example.md)
- [Ansible Vault bootstrap](ansible-vault-bootstrap.md)
