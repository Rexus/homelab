# Domain foundation environment

Use this environment for the first managed deployment after you only have a
clean Proxmox setup and the required networks.

This environment is the bootstrap domain foundation layer, not the Vault
deployment or the optional Windows support layer.

Use the shared Terraform shape here:

- define shared storage, deployable guest networks, template IDs, and
  cloud-init SSH keys in `terraform/common.tfvars`
- keep Day 1 small by filling only the zones you actually use
- place the first managed domain foundation VMs in `vm_instances`
- add a helper container in `lxc_instances` only if you actually need one

Use the matching getting-started guide:
[Domain foundation path](../../../docs/foundation/foundation-and-domain-path.md).
