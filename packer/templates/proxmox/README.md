# Proxmox image templates

This directory contains Packer templates for building reusable VM base images on
Proxmox. Keep templates and safe examples here.

Current template set:

- `debian-12.pkr.hcl`
- `el10.pkr.hcl`
- `talos-linux.pkr.hcl`

LXC note:

- use Terraform or Proxmox-native templates for LXC provisioning
- see [LXC note](lxc/README.md)

Preferred split:

- structured non-secret values in `packer/variables.auto.pkrvars.hcl`
- sensitive runtime values through environment variables or a secret system

Read more in
[Environment variable conventions](../../../docs/reference/environment-variables.md).
