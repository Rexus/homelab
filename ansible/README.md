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

- `requirements.yml` - required Ansible collections for the deployment machine
- `playbooks/control-node.yml` - local control-node precheck that verifies
  `terraform` and installs required collections before each IaC run
- `playbooks/foundation.yml` - staged domain foundation playbook that prepares
  foundation hosts, installs the first FreeIPA identity host, verifies it, and
  then installs replica hosts
- `playbooks/bootstrap.yml` - baseline entry point for bootstrap-only host
  scaffolds
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
- `group_vars/foundation.yml.example` -> `group_vars/foundation.yml`
- `group_vars/vault.yml.example` -> `group_vars/vault.yml`

Preferred run pattern:

- use [`../scripts/init-local-files.sh`](../scripts/init-local-files.sh) once
  for the working copy to create ignored local files from shipped examples
- use `../scripts/init-local-files.sh --env test` when you want a separate
  ignored file set for a new environment name
- start setup runs through [`../scripts/deploy.sh`](../scripts/deploy.sh)
- let the wrapper auto-load `.env.local` when it exists, or use `--env-file`
  when the run should load another ignored environment file
- let that wrapper check the required local config files for the chosen setup
- let that wrapper run `playbooks/control-node.yml` before the mapped
  Terraform and host playbooks

Current proxy model:

- use the foundation layer for the early edge-proxy hosts
- keep any later internal cluster proxy outside this early host-based layer

Current control-node model:

- require `ansible-core` and `terraform` on the machine that runs deployment
- let `scripts/deploy.sh` call `ansible-playbook playbooks/control-node.yml`
  before each setup
