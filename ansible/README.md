# Ansible

Use Ansible to apply bootstrap, baseline, and service-specific host and guest
configuration after provisioning.

For repository usage and secret handling, read:

- [Vault foundation deployment](../docs/foundation/vault-foundation-deployment.md)
- [USB HSM active-active blueprint](../docs/security/usb-hsm-active-active-blueprint.md)
- [Safe repository usage](../docs/usage-model.md)
- [Secret strategy](../docs/security/secret-strategy.md)
- [Environment variable conventions](../docs/reference/environment-variables.md)
- [Ansible Vault bootstrap](../docs/reference/ansible-vault-bootstrap.md)

Key paths:

- `playbooks/bootstrap.yml` - baseline entry point for the bootstrap
  domain foundation layer, including identity, PKI, and optional edge hosts
- `playbooks/vault.yml` - baseline plus Vault installation for hosts in the
  `vault` group
- `playbooks/site.yml` - broader baseline entry point
- `playbooks/ingress.yml` - proxy-only ingress backend registration for HSM
  gateways
- `roles/baseline/` - security-first baseline role scaffold
- `roles/hsm_proxy_ingress/` - proxy backend snippet scaffold for HSM
  gateways on foundation edge-proxy hosts
- `roles/vault/` - Vault service role for dedicated Vault hosts
- `playbooks/site.yml` also fits the baseline layer for foundation proxy,
  `hsm-lab` gateway, and helper hosts after Terraform provisioning
- `inventory/hosts.yml.example` -> `inventory/hosts.yml`
- `group_vars/all.yml.example` -> `group_vars/all.yml`
- `group_vars/vault.yml.example` -> `group_vars/vault.yml`

Current proxy model:

- use the foundation layer for the early edge-proxy hosts
- keep any later internal cluster proxy outside this early host-based layer
