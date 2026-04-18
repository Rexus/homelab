# Bootstrap environment

This directory is the bootstrap entry point for initial private-cloud
deployments. Keep safe examples in Git and place live values in ignored files
such as `terraform/environments/bootstrap/terraform.tfvars`.

The intended first milestone is a dedicated VM that can host Vault before
broader shared-service and workload deployment.
