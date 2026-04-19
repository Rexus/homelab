# Packer

Use Packer to build hardened, reusable VM base images as a later maturity step
when upstream cloud images are no longer enough.

For repository usage and secret handling, read:

- [Safe repository usage](../docs/usage-model.md)
- [Secret strategy](../docs/security/secret-strategy.md)
- [Environment variable conventions](../docs/reference/environment-variables.md)

Key paths:

- `templates/proxmox/` - optional VM template scaffolds for later custom image
  work
- `templates/proxmox/lxc/` - notes for LXC provisioning direction
- `variables.auto.pkrvars.hcl.example`
  -> `variables.auto.pkrvars.hcl`
