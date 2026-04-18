# Bootstrap path

## Table of contents

- [Purpose](#purpose)
- [Minimum bootstrap inputs](#minimum-bootstrap-inputs)
- [Bootstrap result](#bootstrap-result)
- [Recommended flow](#recommended-flow)
- [What comes next](#what-comes-next)
- [Read more](#read-more)

## Purpose

This path uses minimal platform access and environment inputs to create the
first managed infrastructure, establish Vault quickly on that foundation, and
then continue toward the longer-term operating model for recovery and broader
platform services.

## Minimum bootstrap inputs

The bootstrap path assumes:

- local tooling is installed
- Proxmox API access is working
- local example files have been copied
- the Terraform bootstrap environment file has been filled with minimum deployment values
- the bootstrap shell has the required runtime variables exported
- a DNS name, certificate, private key, and CA file are available for the first
  Vault node

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

- a dedicated managed VM sized for Vault
- a managed container
- bootstrap post-provision configuration through Ansible
- a Vault service installation ready for initialization and unseal

This is the starting point for a real environment, not only a tool test.

## Recommended flow

Use the first managed VM as the secret-platform handoff point:

1. provision the first VM through the Terraform bootstrap environment
2. place that host in the Ansible `vault` inventory group
3. run the bootstrap playbook so baseline configuration and the Vault role are applied
4. initialize and unseal Vault
5. move shared and long-lived secrets into Vault before broader deployment

## What comes next

After the bootstrap deployment succeeds:

1. validate access, networking, and bootstrap configuration
2. keep structured environment settings in local bootstrap environment files
3. keep bootstrap secrets out of Git and use environment variables only as a
   temporary secret path
4. initialize Vault and enable an audit device before storing shared secrets
5. reduce direct use of long-lived environment variables as Vault becomes the
   source of truth
6. continue with backup, recovery, and broader shared or restricted platform
   services

## Read more

- [Local setup](local-setup.md)
- [Vault bootstrap](vault-bootstrap.md)
- [Private cloud maturity path](private-cloud-maturity-path.md)
- [Secret strategy](../security/secret-strategy.md)
- [Environment variable conventions](../reference/environment-variables.md)
- [Proxmox reference platform](../../platforms/proxmox/README.md)
