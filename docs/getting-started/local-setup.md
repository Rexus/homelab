# Local setup

## Table of contents

- [Purpose](#purpose)
- [Platform prerequisites](#platform-prerequisites)
- [Local tools](#local-tools)
- [Local repository files](#local-repository-files)
- [Run order](#run-order)
- [Read more](#read-more)

## Purpose

This guide covers the minimum local setup needed before using the bootstrap fast
path in the root README.

## Platform prerequisites

Have these ready before running automation:

- access to the current platform, such as Proxmox
- an automation API token
- prepared network values such as bridge, subnet, gateway, or DHCP usage
- a prepared VM template or image source for managed instances
- an LXC template file if container provisioning will be used

For Proxmox token setup, read
[platforms/proxmox/setup-api.md](../../platforms/proxmox/setup-api.md).

## Local tools

Install these tools on the machine used to run automation:

- Git
- Terraform
- Packer
- Ansible
- SSH client tools

## Local repository files

Use a private working copy of this repository and follow the root README fast
path to create the required local working files from the shipped examples.

Keep live secrets out of Git.

## Run order

After local setup is ready:

1. prepare the VM template or image source
2. set the required environment variables
3. run Terraform to provision bootstrap infrastructure
4. run Ansible to apply bootstrap configuration
5. continue with the bootstrap path and secret strategy

## Read more

- [Environment variable conventions](../reference/environment-variables.md)
- [Secret strategy](../security/secret-strategy.md)
- [Bootstrap path](bootstrap-path.md)
- [Private cloud maturity path](private-cloud-maturity-path.md)
- [Proxmox reference platform](../../platforms/proxmox/README.md)
