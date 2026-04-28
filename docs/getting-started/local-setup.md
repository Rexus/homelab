# Local setup

## Table of contents

- [Purpose](#purpose)
- [Platform prerequisites](#platform-prerequisites)
- [Deployment machine](#deployment-machine)
- [Automation VM example](#automation-vm-example)
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

Use [`scripts/deploy.sh`](../../scripts/deploy.sh) as the default entry point
so that precheck always runs before the mapped Terraform and Ansible steps.
The current setup names are `foundation`, `lab`, `vault`, and `hsm-lab`.
Use [`scripts/init-local-files.sh`](../../scripts/init-local-files.sh) to
create repo-local config files from the shipped examples. Do this as a
separate setup step for the working copy, then let the deployment wrapper check
that the files exist before it runs Terraform or host playbooks.

For provider credentials, use one of these paths:

| Source | How to use it |
| --- | --- |
| existing shell or runner variables | run the wrapper without `--env-file` |
| local ignored env file | use the default `.env.local` file |
| another env file path | pass `--env-file path/to/file` |

No `--env` means production and uses the base local files. For a disposable run
before production, use `--env test`. You can also use custom environment names
such as `lab1`, `dev`, or `staging` when those match how you operate.

The wrapper keeps the same main inventory and loads
`ansible/group_vars/all.<env>.yml` for the environment prefix, domain, and IP
map when you pass `--env`. That file is generated from
`ansible/group_vars/all.env.yml.example`.
Use DNS-safe environment names with letters, numbers, and dashes.
The initializer fills the prefix from `--env`; you still edit the domain and
IPs before deployment.

Terraform uses the base `terraform/common.tfvars` and setup `terraform.tfvars`
for every environment by default. Create `common.<env>.tfvars` or
`terraform.<env>.tfvars` only when an environment intentionally needs different
platform values, sizing, or placement.
If one of those files already exists, the wrapper treats it as an override.

The wrapper keeps local Terraform state separate per setup and environment,
for example `.terraform/state/foundation/test/terraform.tfstate`. Keep every
environment state separate; do not reuse one state file for multiple
environments.

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

Use a private working copy of this repository and initialize local working
files from the shipped examples:

```bash
bash scripts/init-local-files.sh
```

These ignored files are expected to evolve as the environment matures. Keep
editing the same local files instead of recreating them for every run.
The deployment wrapper loads `terraform/common.tfvars` before the selected
setup `terraform.tfvars` file when the common file exists.

When the repo examples change later, you can refresh the local files from the
current examples and keep timestamped backups:

```bash
bash scripts/init-local-files.sh --overwrite
```

Review the refreshed files before deployment and move your local values back
from the `.bak.*` files where needed. The script does not try to merge YAML,
HCL, and dotenv content automatically.

After you have reviewed the backups, remove the timestamped files created by
the overwrite run:

```bash
bash scripts/init-local-files.sh --clean-backups
```

Keep live secrets out of Git.

## Run order

After local setup is ready:

1. prepare the VM template or image source
2. prepare the deployment machine or automation VM with `ansible-core` and
   `terraform`
3. initialize the repo-local files and the first disposable `test` environment:

```bash
bash scripts/init-local-files.sh --env test
```

4. edit `.env.local`, or provide the same values through the shell or runner
5. run the repository deployment wrapper for the first `test` setup:

```bash
bash scripts/deploy.sh foundation --env test \
  --ansible-vars ansible/group_vars/foundation.test.yml
```

That wrapper checks the required local working files first, then runs the
control-node precheck, and only after that runs the mapped Terraform and
Ansible steps.

Destroy the disposable foundation environment after validation:

```bash
bash scripts/deploy.sh foundation --env test --destroy
```

The `--env test` initializer creates the matching Ansible environment vars file
and setup vars files for that environment. Terraform keeps using the base
Terraform vars unless you create an environment-specific override.

6. run production without `--env` after the test path is understood:

```bash
bash scripts/deploy.sh foundation
```

7. continue with the identity foundation path, then the Vault foundation path and
   secret strategy

## Read more

- [Environment variable conventions](../reference/environment-variables.md)
- [Secret strategy](../security/secret-strategy.md)
- [Identity foundation path](../foundation/identity-foundation-path.md)
- [Windows and AD support](../foundation/windows-support.md)
- [Private cloud maturity path](private-cloud-maturity-path.md)
- [Proxmox reference platform](../platforms/proxmox/README.md)
