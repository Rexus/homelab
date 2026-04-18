# Ansible

Use Ansible to apply bootstrap and baseline host and guest configuration after provisioning.

For repository usage and secret handling, read:

- `../docs/getting-started/vault-bootstrap.md`
- `../docs/usage-model.md`
- `../docs/security/secret-strategy.md`
- `../docs/reference/environment-variables.md`
- `../docs/reference/ansible-vault-bootstrap.md`

Key paths:

- `playbooks/bootstrap.yml` - bootstrap entry point
- `playbooks/site.yml` - broader baseline entry point
- `roles/baseline/` - security-first baseline role scaffold
- `roles/vault/` - early Vault bootstrap role for hosts in the `vault` group
- `inventory/hosts.yml.example` -> `inventory/hosts.yml`
- `group_vars/all.yml.example` -> `group_vars/all.yml`
- `group_vars/vault.yml.example` -> `group_vars/vault.yml`
