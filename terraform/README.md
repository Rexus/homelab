# Terraform

Use Terraform to provision platform resources, templates, networks, and virtual
machines.

For repository usage and secret handling, read:

- [Safe repository usage](../docs/usage-model.md)
- [Secret strategy](../docs/security/secret-strategy.md)
- [Environment variable conventions](../docs/reference/environment-variables.md)

Key paths:

- `modules/` - reusable building blocks
- `environments/bootstrap/` - bootstrap environment scaffold
- `environments/bootstrap/terraform.tfvars.example`
  -> `environments/bootstrap/terraform.tfvars`
