# Foundation and domain path

## Table of contents

- [Purpose](#purpose)
- [Minimum foundation inputs](#minimum-foundation-inputs)
- [Foundation result](#foundation-result)
- [Recommended flow](#recommended-flow)
- [What comes next](#what-comes-next)
- [Read more](#read-more)

## Purpose

This path uses minimal platform access and environment inputs to create the
first managed infrastructure or domain foundation, including the first domain
services, especially DNS, and the certificate prerequisites later services such
as Vault depend on.

## Minimum foundation inputs

This path assumes:

- local tooling is installed
- Proxmox API access is working
- local example files have been copied
- the Terraform foundation environment file has been filled with minimum deployment values
- the current shell has the required runtime variables exported

Typical minimum deployment values include:

- environment name
- one or more guest definitions in `vm_instances`
- optional helper definitions in `lxc_instances`
- storage class mappings
- network zones with at least the required bridge or subnet values
- VM template ID
- LXC template file ID when container provisioning is used
- instance and container size, storage class, disk size, and IP settings

## Foundation result

The foundation deployment is meant to establish the first managed building
blocks, such as:

- managed foundation or domain controller hosts
- the first DNS and certificate or PKI path for later shared services
- a managed container
- foundation post-provision configuration through Ansible
- a clean handoff point for later service deployments

This is the starting point for a real environment, not only a tool test.

## Recommended flow

Use the first managed deployment as the handoff point into later shared
services:

1. provision the first VM through the Terraform foundation environment
2. place that host in inventory for baseline configuration
3. run the baseline playbook so baseline configuration is applied
4. validate access, networking, and the first managed host state
5. continue with Vault once the naming, DNS, and PKI prerequisites are ready

## What comes next

After the foundation deployment succeeds:

1. validate access, networking, and foundation configuration
2. keep structured environment settings in local foundation environment files
3. keep bootstrap-only secrets out of Git and use environment variables only as a
   temporary secret path
4. deploy naming, DNS, certificate handling, and other domain or shared-service
   basics required by later services
5. continue with Vault foundation deployment once those prerequisites are ready
6. continue with backup, recovery, and broader shared or restricted platform
   services

## Read more

- [Local setup](../getting-started/local-setup.md)
- [Vault foundation deployment](vault-foundation-deployment.md)
- [Private cloud maturity path](../getting-started/private-cloud-maturity-path.md)
- [Secret strategy](../security/secret-strategy.md)
- [Environment variable conventions](../reference/environment-variables.md)
- [Network zones and IaC mapping](../architecture/network-zones-and-iac-mapping.md)
- [Proxmox reference platform](../platforms/proxmox/README.md)
