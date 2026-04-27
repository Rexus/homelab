# Environment scaffold

This directory is a reusable starting point for private-cloud environment
configuration. Keep safe examples in Git and place live values in ignored files
such as `terraform/environments/lab/terraform.tfvars`.

Use the shared Terraform shape here too:

- keep shared platform values in `terraform/common.tfvars`
- place VMs in `vm_instances`
- place containers in `lxc_instances`
- keep environment-specific values in this folder's `terraform.tfvars`
