# Domain foundation path

## Table of contents

- [Purpose](#purpose)
- [Before you start](#before-you-start)
- [Default foundation shape](#default-foundation-shape)
- [What you configure](#what-you-configure)
- [IaC used for this](#iac-used-for-this)
- [How to deploy it](#how-to-deploy-it)
- [What comes next](#what-comes-next)
- [Read more](#read-more)

## Purpose

Use this path for the first managed domain foundation after the Proxmox and
network prerequisites exist.

The current reference shape is:

- `2` `FreeIPA` replicas with DNS in `identity`
- `1` issuing CA in `cryptography`
- `0-1` offline root CA host in `ceremony`

This is the default authority path for the repository. Keep Windows support as
an optional layer after the domain foundation is stable.

## Before you start

- local tooling is ready
- Proxmox API access is working
- the example files have been copied to local working files
- the shell has the required Terraform environment variables set
- the network plan already includes at least `management`, `identity`, and
  `cryptography`
- the Enterprise Linux template is available for the first foundation hosts

## Default foundation shape

Use this as the starting point:

| Component | Default | Zone | Purpose |
| --- | --- | --- | --- |
| identity hosts | `2` | `identity` | `FreeIPA`, DNS, and the first identity authority |
| issuing CA host | `1` | `cryptography` | online issuing CA for the platform |
| root CA host | `0` enabled by default | `ceremony` | optional offline root CA or ceremony host |
| edge proxy host | `0` enabled by default | `dmz` | optional later edge or ingress layer |

Keep the root CA host separate from the identity hosts when you use it. Treat
it as a ceremony system that should normally stay offline outside planned CA
operations.

Both CA layers can later be hardened with HSM-backed keys, but the default
foundation path does not require HSM on day one.

## What you configure

Edit these local files before you deploy:

| Path | What you configure |
| --- | --- |
| [`terraform/environments/foundation/terraform.tfvars.example`](../../terraform/environments/foundation/terraform.tfvars.example) | `network_zones`, storage mappings, and the foundation VMs in `vm_instances` |
| [`ansible/inventory/hosts.yml.example`](../../ansible/inventory/hosts.yml.example) | `identity`, `pki_issuers`, optional `pki_ceremony`, and optional `proxies` groups |

## IaC used for this

Use these repo paths here:

| IaC path | Used for here | You edit |
| --- | --- | --- |
| [`terraform/environments/foundation/`](../../terraform/environments/foundation/README.md) | provisions the foundation VM layout for identity, PKI, and optional edge hosts | `terraform/environments/foundation/terraform.tfvars` based on `.example` |
| [`ansible/inventory/hosts.yml.example`](../../ansible/inventory/hosts.yml.example) | starting point for the foundation inventory groups | your local `ansible/inventory/hosts.yml` |
| [`ansible/playbooks/bootstrap.yml`](../../ansible/playbooks/bootstrap.yml) | applies the baseline OS configuration to the foundation hosts | inventory and shared variables |

Current boundary:

- Terraform prepares the domain foundation host layout
- the baseline playbook prepares those hosts for managed operation
- dedicated `FreeIPA` and PKI service roles can be layered onto that same host
  shape without changing the network or Terraform model

## How to deploy it

Deploy the domain foundation in this order:

1. Copy the foundation example files to local working files.
2. Fill in `network_zones` for at least `management`, `identity`, and
   `cryptography`. Add `ceremony` when you want a separate offline root CA
   host.
3. Keep the default `2` identity hosts and `1` issuing CA host in
   `vm_instances` unless you intentionally need a different shape.
4. Keep the optional root CA and edge proxy hosts commented until you are ready
   to use them.
5. Update [`ansible/inventory/hosts.yml`](../../ansible/inventory/hosts.yml) so
   the foundation hosts are in `identity`, `pki_issuers`, and optional
   `pki_ceremony` or `proxies`.
6. Apply the foundation Terraform environment.
7. Run the baseline playbook from the `ansible/` directory:

```bash
ansible-playbook -i inventory/hosts.yml playbooks/bootstrap.yml
```

8. Continue with `FreeIPA`, DNS, and issuing-CA installation on the prepared
   hosts.

## What comes next

After the foundation hosts are ready:

1. configure the `2` `FreeIPA` replicas and DNS on the `identity` hosts
2. configure the issuing CA on the `cryptography` host and chain it to the root
   CA when you use one
3. keep the root CA host in `ceremony` offline except during planned CA
   ceremonies
4. add Windows support later only if the environment needs it
5. continue with Vault once identity, DNS, and PKI are ready

## Read more

- [Foundation environment](../../terraform/environments/foundation/README.md)
- [Windows and AD support](windows-support.md)
- [Vault foundation deployment](vault-foundation-deployment.md)
- [Private cloud maturity path](../getting-started/private-cloud-maturity-path.md)
- [Secret strategy](../security/secret-strategy.md)
- [Environment variable conventions](../reference/environment-variables.md)
- [Network zones and IaC mapping](../architecture/network-zones-and-iac-mapping.md)
- [Proxmox reference platform](../platforms/proxmox/README.md)
