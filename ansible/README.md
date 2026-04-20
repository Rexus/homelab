# Ansible

Use Ansible to apply bootstrap and baseline host and guest configuration after
provisioning.

For repository usage and secret handling, read:

- [Vault bootstrap](../docs/getting-started/vault-bootstrap.md)
- [USB HSM active-active blueprint](../docs/security/usb-hsm-active-active-blueprint.md)
- [Safe repository usage](../docs/usage-model.md)
- [Secret strategy](../docs/security/secret-strategy.md)
- [Environment variable conventions](../docs/reference/environment-variables.md)
- [Ansible Vault bootstrap](../docs/reference/ansible-vault-bootstrap.md)

Key paths:

- `playbooks/bootstrap.yml` - bootstrap entry point
- `playbooks/site.yml` - broader baseline entry point
- `playbooks/ingress.yml` - proxy-only ingress backend registration for HSM
  gateways
- `roles/baseline/` - security-first baseline role scaffold
- `roles/hsm_proxy_ingress/` - HAProxy backend snippet scaffold for HSM
  gateways
- `roles/vault/` - early Vault bootstrap role for hosts in the `vault` group
- `playbooks/site.yml` also fits the baseline layer for foundation proxy,
  `hsm-lab` gateway, and helper hosts after Terraform provisioning
- `inventory/hosts.yml.example` -> `inventory/hosts.yml`
- `group_vars/all.yml.example` -> `group_vars/all.yml`
- `group_vars/vault.yml.example` -> `group_vars/vault.yml`
