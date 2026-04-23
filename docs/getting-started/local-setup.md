# Local setup

## Table of contents

- [Purpose](#purpose)
- [Platform prerequisites](#platform-prerequisites)
- [Local tools](#local-tools)
- [Local repository files](#local-repository-files)
- [Run order](#run-order)
- [Read more](#read-more)

## Purpose

This guide covers the minimum local setup needed before using the foundation
fast path in the root README.

## Platform prerequisites

Have these ready before running automation:

- access to the current platform, such as Proxmox
- an automation API token
- prepared network values for the shared `network_zones` map, such as bridge,
  VLAN, subnet, gateway, or DHCP usage
- a prepared VM template or image source for managed instances
- an LXC template file if container provisioning will be used

For Proxmox token setup, read
[Proxmox API setup](../platforms/proxmox/setup-api.md).
For the shared zone names and IaC mapping, read
[Network zones and IaC mapping](../architecture/network-zones-and-iac-mapping.md).

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
3. run Terraform to provision foundation infrastructure
4. run Ansible to apply foundation configuration
5. continue with the domain foundation path, then the Vault foundation path and
   secret strategy

## Read more

- [Environment variable conventions](../reference/environment-variables.md)
- [Secret strategy](../security/secret-strategy.md)
- [Domain foundation path](../foundation/foundation-and-domain-path.md)
- [Windows and AD support](../foundation/windows-support.md)
- [Private cloud maturity path](private-cloud-maturity-path.md)
- [Proxmox reference platform](../platforms/proxmox/README.md)
