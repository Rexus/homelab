# Ansible Vault bootstrap

## Table of contents

- [Purpose](#purpose)
- [Local file pattern](#local-file-pattern)
- [Suggested environment variable](#suggested-environment-variable)
- [Usage notes](#usage-notes)

## Purpose

This document defines a simple Ansible Vault bootstrap pattern that works before
the first Vault deployment is available and can later be replaced by a stronger
secret system.

## Local file pattern

Create local untracked files such as:

- `secrets/ansible-vault-password.txt`
- `secrets/ansible-bootstrap-vars.yml`

Both paths are already ignored by `.gitignore`.

## Suggested environment variable

Use this environment variable to point Ansible to the local vault password file:

```powershell
$env:ANSIBLE_VAULT_PASSWORD_FILE = "secrets/ansible-vault-password.txt"
```

## Usage notes

Keep the local pattern minimal:

- create `secrets/ansible-vault-password.txt`
- set `ANSIBLE_VAULT_PASSWORD_FILE`
- encrypt any bootstrap vars file before reuse
- move shared or long-lived secrets to Vault as soon as the first Vault deployment
  is available

Read more in [Secret strategy](../security/secret-strategy.md).

- keep the vault password file local and untracked
- encrypt the bootstrap vars file before using it broadly
- move shared or long-lived secrets to Vault as soon as the platform can host it
- do not treat this pattern as the final-state secret solution
