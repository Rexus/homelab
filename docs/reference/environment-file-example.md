# Environment file example

## Table of contents

- [Purpose](#purpose)
- [Example](#example)
- [Read more](#read-more)

## Purpose

Use a local ignored file such as `.env.local` for bootstrap secrets and
deployment API values. The repo initializer creates it from
[`env.local.example`](../../env.local.example).

## Example

Minimal example:

```dotenv
PROXMOX_API_URL=https://proxmox.example.internal:8006/api2/json
PROXMOX_API_TOKEN_ID=automation@pve!packer
PROXMOX_API_TOKEN_SECRET=ChangeMe-Proxmox-Token-12345
ANSIBLE_VAULT_PASSWORD_FILE=secrets/ansible-vault-password.txt
```

The deployment wrapper maps the `PROXMOX_API_*` values to the Terraform
`TF_VAR_proxmox_*` inputs before it runs Terraform. It loads `.env.local`
automatically when that file exists.

## Read more

Read more in:

- [Environment variable conventions](environment-variables.md)
- [Secret strategy](../security/secret-strategy.md)
