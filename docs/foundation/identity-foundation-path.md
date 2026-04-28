# Identity foundation path

## Table of contents

- [Purpose](#purpose)
- [Before you start](#before-you-start)
- [Default foundation shape](#default-foundation-shape)
- [What you configure](#what-you-configure)
- [IaC used for this](#iac-used-for-this)
- [Staged identity rollout](#staged-identity-rollout)
- [How to shape the deployment](#how-to-shape-the-deployment)
- [What comes next](#what-comes-next)
- [Read more](#read-more)

## Purpose

Use this path for the first managed identity foundation after the Proxmox and
network prerequisites exist.

The current reference shape is:

- `2` `FreeIPA` replicas with DNS in `identity`
- `1` issuing CA in `cryptography`
- `0-1` offline root CA host in `ceremony`

This is the default authority path for the repository. Keep Windows support as
an optional layer after the identity foundation is stable.

## Before you start

- local tooling is ready
- the deployment machine already has `ansible-core` and `terraform`
- Proxmox API access is working
- repo-local working files have been initialized with
  `bash scripts/init-local-files.sh`
- the local FreeIPA vars file has real values and encrypted passwords
- the deployment environment file has the Proxmox API values, or the shell has
  equivalent variables set
- the network plan already includes at least `management`, `identity`, and
  `cryptography`
- the Enterprise Linux template is available for the first foundation hosts

## Default foundation shape

Use this as the starting point:

| Component | Default | Zone | Purpose |
| --- | --- | --- | --- |
| identity hosts | `2` | `identity` | `FreeIPA`, DNS, and the first identity authority |
| issuing CA host | `1` | `cryptography` | online issuing CA for the platform |
| root CA host | `0` by default | `ceremony` | optional offline root CA or ceremony host |
| edge proxy host | `0` by default | `external_ingress` | optional later edge or ingress layer |

Keep the root CA host separate from the identity hosts when you use it. Treat
it as a ceremony system that should normally stay offline outside planned CA
operations.

Both CA layers can later be hardened with HSM-backed keys, but the default
foundation path does not require HSM on day one.

## What you configure

Edit these local files before you deploy:

| Path | What you configure |
| --- | --- |
| [`terraform/common.tfvars.example`](../../terraform/common.tfvars.example) | default Proxmox node, shared storage mappings, deployable guest networks, template IDs, and cloud-init SSH keys |
| [`terraform/environments/foundation/terraform.tfvars.example`](../../terraform/environments/foundation/terraform.tfvars.example) | foundation VM hardware shape, tags, storage class, disk size, and network zone |
| [`ansible/inventory/hosts.yml.example`](../../ansible/inventory/hosts.yml.example) | stable logical host keys and foundation groups |
| [`ansible/group_vars/all.yml.example`](../../ansible/group_vars/all.yml.example) | environment prefix, domain, guest IP map, SSH user, port, and baseline defaults |
| [`ansible/group_vars/all.env.yml.example`](../../ansible/group_vars/all.env.yml.example) | optional environment overlay for `all.<env>.yml` when using `--env` |
| [`ansible/group_vars/foundation.yml.example`](../../ansible/group_vars/foundation.yml.example) | FreeIPA domain, realm, DNS behavior, and encrypted FreeIPA passwords |

## IaC used for this

Use these repo paths here:

| IaC path | Used for here | You edit |
| --- | --- | --- |
| [`terraform/common.tfvars.example`](../../terraform/common.tfvars.example) | shared Terraform inputs used across environments, including the default Proxmox node | your local `terraform/common.tfvars` |
| [`terraform/environments/foundation/terraform.tfvars.example`](../../terraform/environments/foundation/terraform.tfvars.example) | provisions the foundation VM layout for identity, PKI, and optional edge hosts | `terraform/environments/foundation/terraform.tfvars` based on `.example` |
| [`ansible/inventory/hosts.yml.example`](../../ansible/inventory/hosts.yml.example) | starting point for the stable foundation inventory groups | your local `ansible/inventory/hosts.yml` |
| [`ansible/group_vars/all.yml.example`](../../ansible/group_vars/all.yml.example) | starting point for shared Ansible defaults and the default environment | your local `ansible/group_vars/all.yml` |
| [`ansible/group_vars/all.env.yml.example`](../../ansible/group_vars/all.env.yml.example) | starting point for environment-specific prefix, domain, and IP maps | your local `ansible/group_vars/all.<env>.yml` |
| [`ansible/group_vars/foundation.yml.example`](../../ansible/group_vars/foundation.yml.example) | starting point for FreeIPA and foundation service inputs | your local encrypted `ansible/group_vars/foundation.yml` |
| [`ansible/playbooks/foundation.yml`](../../ansible/playbooks/foundation.yml) | applies baseline configuration, installs the first FreeIPA host, sanity-checks it, and then installs replicas | inventory and foundation group variables |
| [`scripts/deploy.sh`](../../scripts/deploy.sh) | repository wrapper for the mapped precheck, Terraform, and Ansible flow | choose the `foundation` setup when you are ready to run it |

Current boundary:

- Ansible inventory owns stable logical host keys and service groups
- Ansible group vars own the environment prefix, domain, and guest IP map
- Terraform prepares the identity foundation hardware layout and Proxmox tags
- Terraform reads the Ansible group vars to derive the Proxmox VM names and IPs
- the foundation playbook prepares those hosts for managed operation
- the foundation playbook installs the first `FreeIPA` host, verifies it, and
  then installs the replica hosts
- the issuing CA host is provisioned in `cryptography`; detailed issuing-CA
  service policy remains a PKI operations step

## Staged identity rollout

The foundation playbook handles `FreeIPA` as a staged deployment:

| Stage | What happens | Sanity gate |
| --- | --- | --- |
| baseline | all hosts in `foundation` get the baseline role | SSH and baseline tasks complete |
| primary identity | the single host in `identity_primary` gets the first `FreeIPA` server | `ipactl status` and `ipa ping` pass |
| replica identity | hosts in `identity_replicas` are configured one at a time | the same checks pass on every identity host |

Keep exactly one host in `identity_primary`. Add additional identity replicas
under `identity_replicas` so the first authority is always verified before the
redundant pair is completed.

## How to shape the deployment

Use the default shape unless you already know why your environment needs a
different authority layout.

- keep `management`, `identity`, and `cryptography` defined before you add
  other optional zones
- keep `2` identity hosts unless this is only a short-lived test environment
- place the identity hosts on different Proxmox nodes when the platform allows
  it
- keep the issuing CA on its own dedicated host in `cryptography`
- enable a root CA host in `ceremony` only when you want a separate offline
  ceremony system from the start
- keep the edge proxy commented until your environment actually needs external
  ingress
- keep the inventory groups aligned with the host intent:
  `identity_primary`, `identity_replicas`, `pki_issuers`, optional
  `pki_ceremony`, and optional `proxies`

For environment separation, keep one stable inventory and separate ignored
local data files and state:

| Environment | Local var file | Wrapper command |
| --- | --- | --- |
| first validation run | `terraform/environments/foundation/terraform.tfvars` plus `ansible/group_vars/all.test.yml` | `bash scripts/deploy.sh foundation --env test` |
| lab, dev, or staging | `terraform/environments/foundation/terraform.tfvars` plus `ansible/group_vars/all.lab1.yml` | `bash scripts/deploy.sh foundation --env lab1` |
| production | `terraform/environments/foundation/terraform.tfvars` | `bash scripts/deploy.sh foundation` |

The wrapper stores local Terraform state separately per setup and environment,
for example `.terraform/state/foundation/test/terraform.tfstate`.

Terraform uses the base `terraform/common.tfvars` and foundation
`terraform.tfvars` for every environment by default. Add
`terraform/common.<env>.tfvars` or
`terraform/environments/foundation/terraform.<env>.tfvars` only when that
environment intentionally needs different platform values, VM sizes, or
placement.

Put the environment prefix, domain, and IP map in
`ansible/group_vars/all.<env>.yml`. Use DNS-safe environment names with
letters, numbers, and dashes. The initializer fills the prefix from `--env`;
you still edit the domain and IPs before deployment.

No `--env` means production and uses the base local files:
`terraform/common.tfvars`, `terraform/environments/foundation/terraform.tfvars`,
`ansible/group_vars/all.yml`, and `ansible/group_vars/foundation.yml`.

If FreeIPA values differ between disposable environments, pass an ignored vars
file with `--ansible-vars`, such as
`ansible/group_vars/foundation.test.yml`.

Example with the recommended first `test` inputs:

```bash
bash scripts/init-local-files.sh --env test

bash scripts/deploy.sh foundation --env test \
  --ansible-vars ansible/group_vars/foundation.test.yml
```

The wrapper automatically loads `.env.local` when it exists. Add
`--env-file path/to/file` when you want to override that with another file.

To remove a disposable environment after testing, run the same setup with
`--destroy`:

```bash
bash scripts/deploy.sh foundation --env test --destroy
```

When you are ready to run the setup, use the repository deployment wrapper with
the `foundation` setup. Keep the exact execution flow in the wrapper rather
than repeating it in this guide. That wrapper also checks the required local
config files for the setup before it runs.

## What comes next

After the foundation hosts are ready:

1. verify `FreeIPA`, DNS, and replication health from the deployment machine
2. configure the issuing CA on the `cryptography` host and chain it to the root
   CA when you use one
3. keep the root CA host in `ceremony` offline except during planned CA
   ceremonies
4. add Windows support later only if the environment needs it
5. continue with Vault once identity, DNS, and PKI are ready

## Read more

- [Infrastructure automation layout](../reference/infrastructure-automation-layout.md)
- [Windows and AD support](windows-support.md)
- [Vault foundation deployment](vault-foundation-deployment.md)
- [Private cloud maturity path](../getting-started/private-cloud-maturity-path.md)
- [Secret strategy](../security/secret-strategy.md)
- [Environment variable conventions](../reference/environment-variables.md)
- [Network zones and IaC mapping](../architecture/network-zones-and-iac-mapping.md)
- [Proxmox reference platform](../platforms/proxmox/README.md)
