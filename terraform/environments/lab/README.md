# Environment scaffold

This directory is a reusable starting point for private-cloud environment
configuration. Keep safe examples in Git and place live values in ignored files
such as `terraform/environments/lab/terraform.tfvars`.

Use the shared Terraform shape here too:

- define the environment network map in `network_zones`
- place VMs in `vm_instances`
- place containers in `lxc_instances`
- keep unused future zones as comments or planning placeholders until needed
