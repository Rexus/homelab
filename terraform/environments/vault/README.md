# Vault foundation environment

Use this environment when you want to provision one or more dedicated Vault
VMs after the bootstrap domain foundation layer and its naming or
certificate prerequisites are already in place.

Use the shared Terraform shape here:

- define your local bridges, VLANs, and subnets in `network_zones`
- place one or more dedicated Vault VMs in `vm_instances`
- keep the default path small with one Vault node first
- add helper containers in `lxc_instances` only if you actually need them

The matching service deployment guide is
[Vault foundation deployment](../../../docs/foundation/vault-foundation-deployment.md).
