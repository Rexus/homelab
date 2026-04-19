# Bootstrap environment

This directory is the bootstrap entry point for initial private-cloud
deployments. Keep safe examples in Git and place live values in ignored files
such as `terraform/environments/bootstrap/terraform.tfvars`.

The intended first milestone is a dedicated VM that can host Vault before
broader shared-service and workload deployment.

Use the shared Terraform shape here:

- define your local bridges, VLANs, and subnets in `network_zones`
- keep Day 1 small by filling only the zones you actually use
- place the first VM in `vm_instances`
- add a helper container in `lxc_instances` only if you need it
