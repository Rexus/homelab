# Vault foundation deployment

## Table of contents

- [Purpose](#purpose)
- [Before you start](#before-you-start)
- [What you configure](#what-you-configure)
- [IaC used for this](#iac-used-for-this)
- [How to deploy it](#how-to-deploy-it)
- [After deployment](#after-deployment)
- [Later hardening](#later-hardening)
- [Read more](#read-more)

## Purpose

Use this guide after the domain foundation layer is in place and you are
ready to deploy Vault as the early secret-platform foundation.

```mermaid
flowchart LR
  A[Domain foundation ready] --> B[Terraform creates dedicated Vault VM]
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

Figure: Vault is deployed after the domain foundation layer exists and
becomes the handoff point from bootstrap-only secrets to the long-term secret
platform.

## Before you start

- the domain foundation deployment is already complete
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
| [`terraform/environments/vault/terraform.tfvars.example`](../../terraform/environments/vault/terraform.tfvars.example) | Vault `network_zones`, storage mappings, and the Vault VM definitions in `vm_instances` |
| [`ansible/inventory/hosts.yml.example`](../../ansible/inventory/hosts.yml.example) | the first Vault host in the `vault` inventory group |
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
| [`terraform/environments/vault/`](../../terraform/environments/vault/) | provisions one or more dedicated Vault VMs | `terraform/environments/vault/terraform.tfvars` based on `.example` |
| [`ansible/inventory/hosts.yml.example`](../../ansible/inventory/hosts.yml.example) | starting point for the `vault` inventory group | your local `ansible/inventory/hosts.yml` |
| [`ansible/group_vars/vault.yml.example`](../../ansible/group_vars/vault.yml.example) | starting point for Vault listener, TLS, and node settings | your local `ansible/group_vars/vault.yml` |
| [`ansible/playbooks/vault.yml`](../../ansible/playbooks/vault.yml) | baseline host preparation and Vault installation on hosts in the `vault` group | inventory and Vault group variables |

This deployment flow installs Vault and prepares the first node. Operator
initialization, unseal handling, and secret handoff stay manual.

## How to deploy it

Deploy Vault in this order:

1. Copy the example files to your local working files and fill in the Vault
   values.
2. Confirm the Vault node count you want is defined in
   [`terraform/environments/vault/terraform.tfvars`](../../terraform/environments/vault/terraform.tfvars).
   The default path in this guide is one dedicated Vault VM.
3. Confirm that host is present in the `vault` group in
   [`ansible/inventory/hosts.yml`](../../ansible/inventory/hosts.yml).
4. Fill in [`ansible/group_vars/vault.yml`](../../ansible/group_vars/vault.yml)
   with the Vault API address, cluster address, node ID, and TLS file paths.
5. Apply the Vault Terraform environment.
6. Run the Vault playbook from the `ansible/` directory:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/vault.yml
```

7. Verify the Vault service is running but still sealed.
8. Initialize Vault with an operator-reviewed command, for example:

```bash
vault operator init -key-shares=3 -key-threshold=2
```

9. Unseal the first node and enable an audit device before storing shared
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

Use this guide only for the first Vault foundation deployment after the domain
foundation layer.

For later hardening, higher availability, and future HSM-related paths, continue
with the security docs instead of extending this deployment guide:

- [Vault HSM hardening options](../security/vault-hsm-hardening-options.md)
- [HSM getting started](../security/hsm-planning-and-comparison.md)
- [USB HSM active-active blueprint](../security/usb-hsm-active-active-blueprint.md)

## Read more

- [Domain foundation path](foundation-and-domain-path.md)
- [Windows and AD support](windows-ad-support.md)
- [Private cloud maturity path](../getting-started/private-cloud-maturity-path.md)
- [Secret strategy](../security/secret-strategy.md)
- [Ansible Vault bootstrap fallback](../reference/ansible-vault-bootstrap.md)
