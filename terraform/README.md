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
- `environments/hsm-lab/` - host-layout scaffold for Pico HSM or software
  PKCS#11 lab patterns
- `environments/bootstrap/terraform.tfvars.example`
  -> `environments/bootstrap/terraform.tfvars`

Shared Terraform pattern:

- define logical networks in `network_zones`
- place guests with `vm_instances` and `lxc_instances`
- keep bridge, VLAN, and subnet values local to your own `terraform.tfvars`
