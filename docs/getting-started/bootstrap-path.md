# Bootstrap path

## Table of contents

- [Purpose](#purpose)
- [Minimum bootstrap inputs](#minimum-bootstrap-inputs)
- [Bootstrap result](#bootstrap-result)
- [What comes next](#what-comes-next)
- [Read more](#read-more)

## Purpose

This path uses minimal platform access and environment inputs to create the
first managed infrastructure and then move toward the longer-term operating
model for secrets, recovery, and broader platform services.

## Minimum bootstrap inputs

The bootstrap path assumes:

- local tooling is installed
- Proxmox API access is working
- local example files have been copied
- the Terraform bootstrap environment file has been filled with minimum deployment values
- the bootstrap shell has the required runtime variables exported

Typical minimum deployment values include:

- environment name
- Proxmox node name
- storage class mappings
- network bridge
- VM template ID
- LXC template file ID when container provisioning is used
- instance and container size, storage class, disk size, and IP settings

## Bootstrap result

The bootstrap deployment is meant to establish the first managed building
blocks, such as:

- a managed VM
- a managed container
- bootstrap post-provision configuration through Ansible

This is the starting point for a real environment, not only a tool test.

## What comes next

After the bootstrap deployment succeeds:

1. validate access, networking, and bootstrap configuration
2. keep structured environment settings in local bootstrap environment files
3. keep bootstrap secrets out of Git and use environment variables only as a
   temporary secret path
4. move toward the intended secret model, such as Vault, when the environment is
   ready to host it
5. continue with backup, recovery, and broader shared or restricted platform
   services

## Read more

- [Local setup](local-setup.md)
- [Private cloud maturity path](private-cloud-maturity-path.md)
- [Secret strategy](../security/secret-strategy.md)
- [Environment variable conventions](../reference/environment-variables.md)
- [Proxmox reference platform](../../platforms/proxmox/README.md)
