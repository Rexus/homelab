# Vault foundation deployment

## Table of contents

- [Purpose](#purpose)
- [Before you start](#before-you-start)
- [What you configure](#what-you-configure)
- [IaC used for this](#iac-used-for-this)
- [How to shape the deployment](#how-to-shape-the-deployment)
- [After deployment](#after-deployment)
- [Later hardening](#later-hardening)
- [Read more](#read-more)

## Purpose

Use this guide after the identity foundation layer is in place and you are
ready to deploy Vault as the early secret-platform foundation.

```mermaid
flowchart LR
  A[Identity foundation ready] --> B[Terraform creates dedicated Vault VM]
  B --> C[Ansible Vault playbook]
  C --> D[Vault service installed and sealed]
  D --> E[Operator init and unseal]
  E --> F[Shared secrets move into Vault]
  F --> G[Continue broader deployment]

  classDef mgmtNode fill:#fed7aa,stroke:#c2410c,color:#1f2937
  classDef buildNode fill:#dbeafe,stroke:#2563eb,color:#1f2937
  classDef vaultNode fill:#bbf7d0,stroke:#15803d,color:#1f2937

  class A,E mgmtNode
  class B,C,G buildNode
  class D,F vaultNode
```

Figure: Vault is deployed after the identity foundation layer exists and
becomes the handoff point from first-run secrets to the long-term secret
platform.

## Before you start

- the identity foundation deployment is already complete
- identity, DNS, and the first PKI path already exist
- the deployment machine already has `ansible-core` and `terraform`
- naming and the first TLS path for Vault already exist
- one dedicated Vault VM, or more when needed, is defined in the Vault
  environment
- each Vault host exists in the `vault` inventory group
- local copies of the example files exist before you edit them
- the current Vault role does not generate the first Vault certificate, key, or
  CA file for you

## What you configure

Edit these local files before you run the Vault foundation deployment:

| Path | What you configure |
| --- | --- |
| [`terraform/common.tfvars.example`](../../terraform/common.tfvars.example) | default Proxmox node, shared storage mappings, deployable guest networks, template IDs, and cloud-init SSH keys |
| [`terraform/environments/vault/terraform.tfvars.example`](../../terraform/environments/vault/terraform.tfvars.example) | Vault VM definitions in `vm_instances` |
| [`ansible/inventory/hosts.yml.example`](../../ansible/inventory/hosts.yml.example) | Vault host key, IP, and inventory group |
| [`ansible/group_vars/vault.yml.example`](../../ansible/group_vars/vault.yml.example) | `vault_api_addr`, `vault_cluster_addr`, `vault_node_id`, TLS source paths, and listener settings |

### Deployment shape

The Vault environment can deploy one or more Vault nodes through
`vm_instances`, but this guide uses the default single-node path.

Use this rule:

- keep `1` dedicated Vault VM for the default deployment flow
- add more Vault VMs in `vm_instances` only when you are intentionally starting
  with a multi-node Raft deployment
- add every Vault node to the Ansible `vault` inventory group

Use these first-node settings:

- keep `vault_raft_retry_join` empty for the first single-node deployment
- keep `vault_seal_hcl` empty for the first deployment
- keep TLS enabled from the first startup
- keep the Vault host dedicated to Vault

## IaC used for this

Use these repo paths for the Vault foundation deployment:

| IaC path | Used for here | You edit |
| --- | --- | --- |
| [`terraform/common.tfvars.example`](../../terraform/common.tfvars.example) | shared Terraform inputs used across environments, including the default Proxmox node | your local `terraform/common.tfvars` |
| [`terraform/environments/vault/terraform.tfvars.example`](../../terraform/environments/vault/terraform.tfvars.example) | provisions one or more dedicated Vault VMs | `terraform/environments/vault/terraform.tfvars` based on `.example` |
| [`ansible/inventory/hosts.yml.example`](../../ansible/inventory/hosts.yml.example) | starting point for the `vault` inventory group | your local `ansible/inventory/hosts.yml` |
| [`ansible/group_vars/vault.yml.example`](../../ansible/group_vars/vault.yml.example) | starting point for Vault listener, TLS, and node settings | your local `ansible/group_vars/vault.yml` |
| [`ansible/playbooks/vault.yml`](../../ansible/playbooks/vault.yml) | baseline host preparation and Vault installation on hosts in the `vault` group | inventory and Vault group variables |
| [`scripts/deploy.sh`](../../scripts/deploy.sh) | repository wrapper for the mapped precheck, Terraform, and Ansible flow | choose the `vault` setup when you are ready to run it |

This deployment flow installs Vault and prepares the first node. Operator
initialization, unseal handling, and secret handoff stay manual.

Use the shared ownership rule from
[Infrastructure automation layout](../reference/infrastructure-automation-layout.md):
Ansible inventory owns host keys, IPs, and service groups. Ansible group vars
append `platform_domain` for FQDNs, while the Vault Terraform environment owns
hardware placement and Proxmox tags.

## How to shape the deployment

Use the Vault environment as a dedicated service layer, not as a mixed-use VM.

- keep the default path at `1` dedicated Vault VM
- add more Vault nodes in `vm_instances` only when you intentionally want a
  multi-node Raft design from the start
- keep every Vault VM in the Ansible `vault` inventory group
- keep TLS enabled from the first startup and prepare the certificate inputs
  before the run
- leave `vault_raft_retry_join` empty for the first single-node deployment
- leave `vault_seal_hcl` empty for the first deployment and add seal changes
  later through the hardening path
- keep Vault on dedicated hosts instead of combining it with identity, PKI, or
  application roles

When you are ready to run the setup, use the repository deployment wrapper with
the `vault` setup. Keep the exact execution flow in the wrapper rather than
repeating it in this guide. That wrapper also checks the required local config
files for the setup before it runs.

After the wrapper run:

- verify the Vault service is running but still sealed
- initialize Vault with an operator-reviewed command, for example:

```bash
vault operator init -key-shares=3 -key-threshold=2
```

- unseal the first node and enable an audit device before storing shared
  secrets:

```bash
vault operator unseal
vault operator unseal
vault audit enable file file_path=/var/log/vault/audit.log
```

For stronger operator handling, use PGP encryption for unseal shares and the
initial root token during `vault operator init`.

## After deployment

After Vault is initialized:

- move shared service credentials and long-lived tokens into Vault
- keep root tokens and unseal material out of the repository and out of normal
  automation
- keep local Ansible Vault files as a fallback path, not the primary system of
  record
- continue the broader deployment only after Vault is reachable and audited

## Later hardening

Use this guide only for the first Vault foundation deployment after the
identity foundation layer.

For later hardening, higher availability, and future HSM-related paths, continue
with the security docs instead of extending this deployment guide:

- [Vault HSM hardening options](../security/vault-hsm-hardening-options.md)
- [HSM getting started](../security/hsm-planning-and-comparison.md)
- [USB HSM active-active blueprint](../security/usb-hsm-active-active-blueprint.md)

## Read more

- [Identity foundation path](identity-foundation-path.md)
- [Windows and AD support](windows-support.md)
- [Private cloud maturity path](../getting-started/private-cloud-maturity-path.md)
- [Secret strategy](../security/secret-strategy.md)
- [Ansible Vault bootstrap fallback](../reference/ansible-vault-bootstrap.md)
