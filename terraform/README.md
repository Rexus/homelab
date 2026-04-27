# Terraform

Use Terraform to provision platform resources, templates, networks, and virtual
machines.

For repository usage and secret handling, read:

- [Safe repository usage](../docs/usage-model.md)
- [Secret strategy](../docs/security/secret-strategy.md)
- [Environment variable conventions](../docs/reference/environment-variables.md)
- [Network zones and IaC mapping](../docs/architecture/network-zones-and-iac-mapping.md)

Key paths:

- `modules/` - reusable building blocks
- `environments/bootstrap/` - bootstrap environment scaffold
- `environments/foundation/` - domain foundation scaffold for identity, PKI,
  and optional edge-proxy hosts
- `environments/hsm-lab/` - gateway and custody-host scaffold for USB HSM or
  software PKCS#11 lab patterns
- `common.tfvars.example` -> `common.tfvars`
- `environments/foundation/terraform.tfvars.example`
  -> `environments/foundation/terraform.tfvars`

Shared Terraform pattern:

- use [`../scripts/init-local-files.sh`](../scripts/init-local-files.sh) once
  for the working copy to create ignored local files from shipped examples
- use `../scripts/init-local-files.sh --env test` when you want a separate
  ignored file set for a new environment name
- start each environment run through [`../scripts/deploy.sh`](../scripts/deploy.sh)
- let the wrapper auto-load `.env.local` when it exists, or use `--env-file`
  to override it with another path
- let that wrapper verify the required local working files for the chosen setup
- keep shared platform values in `common.tfvars`, such as storage classes,
  deployable guest networks, template IDs, and cloud-init SSH keys
- the wrapper loads `common.tfvars` first when it exists, then the
  environment-specific var file so local deployment values can override shared
  defaults
- use `--env test` or `--env prod` when you want separate Terraform workspaces
  and matching `terraform.test.tfvars` or `terraform.prod.tfvars` files
- use `--inventory` and `--ansible-vars` with the wrapper when Ansible inputs
  differ between environments
- use `--destroy` with the same setup and environment when you need to clean up
  a disposable test deployment
- define only guest networks that automation may use in `network_zones`
- place guests with `vm_instances` and `lxc_instances`
- keep deployment-specific guest definitions in the environment
  `terraform.tfvars`

Current proxy model:

- use `environments/foundation/` for the early `dmz` edge-proxy layer
- keep any later internal cluster proxy outside the foundation layer
