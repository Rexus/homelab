# Foundation and domain environment

Use this environment for the first managed deployment after you only have a
clean Proxmox setup and the required networks.

This environment is the bootstrap foundation or domain layer, not the Vault
deployment.

Use the shared Terraform shape here:

- define your local bridges, VLANs, and subnets in `network_zones`
- keep Day 1 small by filling only the zones you actually use
- place the first managed foundation or domain VMs in `vm_instances`
- add a helper container in `lxc_instances` only if you actually need one

Use the matching getting-started guide:
[Foundation and domain path](../../../docs/foundation/foundation-and-domain-path.md).
