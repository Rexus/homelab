# Local setup

## Table of contents

- [Purpose](#purpose)
- [Platform prerequisites](#platform-prerequisites)
- [Deployment machine](#deployment-machine)
- [Automation VM example](#automation-vm-example)
- [Local repository files](#local-repository-files)
- [Read more](#read-more)

## Purpose

This guide covers the minimum local setup needed before using the foundation
fast path in the root README.

## Platform prerequisites

Have these ready before running automation:

- access to the current platform, such as Proxmox
- an automation API token
- prepared network values for the shared deployable `network_zones` map, such
  as bridge, VLAN, subnet, gateway, or DHCP usage
- a prepared VM template or image source for managed instances
- an LXC template file if container provisioning will be used

For Proxmox token setup, read
[Proxmox API setup](../platforms/proxmox/setup-api.md).
For the shared zone names and IaC mapping, read
[Network zones and IaC mapping](../architecture/network-zones-and-iac-mapping.md).

## Deployment machine

Run this repository from one deployment machine.

That machine can be:

- your local workstation
- a dedicated automation VM after the first template exists

Require these tools there:

- Git
- `terraform`
- `ansible-core`
- SSH client tools

`Packer` is only needed when you build templates from this same machine.

Each deployment run starts with a local Ansible precheck on that deployment
machine. That precheck installs or refreshes required Ansible collections such
as `community.general` and `freeipa.ansible_freeipa`.

The repository deployment wrapper runs that precheck before Terraform or host
playbooks. Follow the root README or the setup-specific guide for the actual
run commands.

For provider credentials, use one of these paths:

| Source | How to use it |
| --- | --- |
| existing shell or runner variables | useful for runners and pipeline jobs |
| local ignored env file | useful for a dedicated automation VM |
| another env file path | useful when the deployment machine handles several contexts |

Ansible is configured for bootstrap-friendly SSH. New host keys are accepted
automatically with OpenSSH `StrictHostKeyChecking=accept-new`, while changed
host keys still stop the run.

## Automation VM example

After the first template exists, a small dedicated automation VM is often
easier to keep stable than using a personal workstation.

For a RHEL, CentOS Stream, AlmaLinux, or Rocky Linux automation VM, one current
example is:

```bash
sudo dnf install -y epel-release
sudo dnf install -y ansible-core
sudo dnf install -y yum-utils
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
sudo dnf install -y terraform
```

For other distributions, follow the current official install guides for
[Terraform](https://developer.hashicorp.com/terraform/install) and
[ansible-core](https://docs.ansible.com/ansible/latest/installation_guide/installation_distros.html).

Keep the automation VM simple:

- store a private working copy of the repository there
- keep the local Terraform vars, inventory, and group vars there
- give it access to the Proxmox API, Git remotes, and the package or collection
  sources it needs

## Local repository files

Use a private working copy of this repository and create the ignored local
working files from the shipped examples before the first deployment.

These ignored files are expected to evolve as the environment matures. Keep
editing the same local files instead of recreating them for every run.
The deployment wrapper loads `terraform/common.tfvars` before the selected
setup `terraform.tfvars` file when the common file exists.

When the repo examples change later, refresh local files carefully and review
any backups before deployment. The repository does not try to merge YAML, HCL,
and dotenv content automatically.

Keep live secrets out of Git.

## Read more

- [Environment variable conventions](../reference/environment-variables.md)
- [Secret strategy](../security/secret-strategy.md)
- [Identity foundation path](../foundation/identity-foundation-path.md)
- [Windows and AD support](../foundation/windows-support.md)
- [Private cloud maturity path](private-cloud-maturity-path.md)
- [Proxmox reference platform](../platforms/proxmox/README.md)
