# Terraform

Use Terraform to provision platform resources, templates, networks, and virtual
machines.

For repository usage and secret handling, read:

- `../docs/usage-model.md`
- `../docs/security/secret-strategy.md`
- `../docs/reference/environment-variables.md`

Key paths:

- `modules/` - reusable building blocks
- `environments/bootstrap/` - bootstrap environment scaffold
- `environments/bootstrap/terraform.tfvars.example`
  -> `environments/bootstrap/terraform.tfvars`
