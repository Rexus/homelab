# Environment file example

## Table of contents

- [Purpose](#purpose)
- [Example](#example)
- [Read more](#read-more)

## Purpose

Use a local ignored file such as `.env.local` for bootstrap secrets and
deployment API values. The initializer creates it from `env.local.example` in
the owning tier repository (or `tier-N/` inside a private source checkout).

## Example

Edit in the owning **`<prefix>-tier-N/`** repository.

- `.env.local`: actual API endpoint, token ID/secret and local vault-password path

Minimal provider contents; replace the endpoint and both token fields with the approved values:

```dotenv
PROXMOX_API_URL=https://proxmox.example.internal:8006/
PROXMOX_API_TOKEN_ID=automation@pve!provision
PROXMOX_API_TOKEN_SECRET=REPLACE_WITH_SCOPED_TOKEN_SECRET
```

Only when using encrypted Ansible inputs, add `ANSIBLE_VAULT_PASSWORD_FILE` with an existing
authorized private password-file path. An example path does not create that file.
Linux guest deployment also needs the selected local SSH public-key inputs from the
[platform access contract](platform-inputs.md#local-ssh-access); provider credentials alone do not configure guest access.

The deployment wrapper maps the `PROXMOX_API_*` values to the Terraform
`TF_VAR_proxmox_*` inputs before it runs Terraform. It loads `.env.local`
automatically when that file exists.

That automatic loading is specific to `scripts/deploy.sh`. The
[template publisher](template-publication.md#state-and-execution) needs `--env-file .env.local`;
the [Kubernetes lifecycle](../03-deployment/stage-4-kubernetes/procedures/talos-terraform.md#configure)
uses exported native provider variables. Direct Ansible invocations need their own documented inputs.

`PROXMOX_API_URL` is for the Terraform `bpg/proxmox` provider and should not
include `/api2/json`. When running the HashiCorp Packer Proxmox plugin,
use its own `PROXMOX_URL` value with the full `/api2/json` path.

## Read more

Read more in:

- [Environment variable conventions](environment-variables.md)
- [Secret strategy](../05-operations/03-cryptography/secret-handling.md)
