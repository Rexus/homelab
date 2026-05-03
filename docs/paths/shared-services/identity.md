# Identity foundation path

## Table of contents

- [Purpose](#purpose)
- [Before you start](#before-you-start)
- [Default private-domain shape](#default-private-domain-shape)
- [Authentication design](#authentication-design)
- [Using an existing domain](#using-an-existing-domain)
- [What you configure](#what-you-configure)
- [IaC used for this](#iac-used-for-this)
- [Staged identity rollout](#staged-identity-rollout)
- [How to shape the deployment](#how-to-shape-the-deployment)
- [What comes next](#what-comes-next)
- [Read more](#read-more)

## Purpose

Use this path when you want the repository to deploy the shared private-domain
identity and PKI layer after the Proxmox and network prerequisites exist.

The current reference shape is:

- `2` `FreeIPA` replicas with DNS in `identity`
- `1` issuing CA in `cryptography`
- `0-1` offline root CA host in `ceremony`

This is the default authority path for the repository, not a mandatory global
prerequisite. If you already operate identity, DNS, and PKI, use those as the
shared services for later paths.

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
- the Enterprise Linux template is available for the first shared-service hosts

## Default private-domain shape

Use this as the starting point:

Use a private internal subdomain for the platform domain, such as
`corp.example.com` or `internal.example.com`. Do not use the same DNS name as
the public website, such as `example.com`, for the internal identity and PKI
domain.

| Component | Terraform default | Inventory entry | Zone | Purpose |
| --- | --- | --- | --- | --- |
| identity hosts | `idm-1`, `idm-2` active | `idm-1`, `idm-2` present by default | `identity` | `FreeIPA`, DNS, and the first identity authority |
| issuing CA host | `ca-1` active | `ca-1` present by default | `cryptography` | online issuing CA for the platform |
| root CA host | `ca-root-1` commented, default `0` | uncomment `ca-root-1` when enabled | `ceremony` | optional offline root CA host |

Keep the root CA host separate from the identity hosts when you use it. Treat
it as a ceremony system that should normally stay offline outside planned CA
operations.

Both CA layers can later be hardened with HSM-backed keys, but the default
identity path does not require HSM on day one.

The Terraform example for this path lives in
`terraform/environments/foundation/terraform.tfvars.example`. Commented
`vm_instances` are default `0` and should stay commented until you also enable
the matching Ansible inventory group and IP entry.

## Authentication design

Use `FreeIPA` with Kerberos as the core identity authority. Anchor user, host,
and service trust in PKI, then harden privileged users with hardware-backed
authentication.

Apply these rules when you shape the domain:

| Rule | What it means for this path |
| --- | --- |
| hardware key = identity proof | Use YubiKey or compatible hardware tokens as the strongest proof of user identity once the domain is stable. |
| Kerberos = internal SSO | Use Kerberos for enrolled hosts and services, but avoid broad or unconstrained delegation. |
| SSH = short-lived or non-delegatable | Prefer short-lived OpenSSH user certificates, scoped keys, or credentials that services cannot reuse as the user. |
| assume every host can be compromised | Do not place reusable passwords or unrestricted credentials on managed hosts. |

Default behavior:

| Auth path | Default | Notes |
| --- | --- | --- |
| user passwords | enabled | needed for first deployment, recovery, and compatibility |
| Kerberos through SSSD | expected | normal Linux domain authentication path |
| SSH certificates | recommended hardening | stronger SSH access path after the domain and host enrollment are stable |
| YubiKey or hardware OTP | recommended hardening | optional after the first domain is stable |
| PIV or smart-card certificates | stronger hardening path | optional after PKI and recovery processes are ready |

Avoid credential delegation. Services should not collect reusable user
passwords so they can act as users later. Prefer Kerberos tickets, service
principals, certificates, Vault-issued credentials, or the access-layer SSO
path when that exists.

Use [Hardware-backed user authentication](hardware-keys.md) when you are ready
to add YubiKey OTP or PIV authentication.

## Using an existing domain

You can skip this deployment when an existing environment already provides the
services this path would create.

Use the existing environment as the source for:

| Existing service | Later paths need |
| --- | --- |
| DNS and private domain | stable FQDNs for platform hosts and services |
| identity | users, groups, service identities, and host enrollment model |
| PKI | trusted certificates for internal TLS and service identity |
| secrets platform | shared secret storage and token handoff |
| telemetry or syslog | audit, troubleshooting, and platform visibility |

Keep the same repo pattern even when the services already exist:

- keep stable inventory host keys such as `idm-1`, `vault-1`, or `logs-1`
- keep environment-specific domains and IP maps in `all.<env>.yml`
- override subnets and VLANs in Terraform only when that environment needs a
  different network shape
- avoid deploying duplicate identity systems for labs unless isolation is the
  goal

## What you configure

Edit these local files before you deploy:

| Path | What you configure |
| --- | --- |
| [`terraform/common.tfvars.example`](../../../terraform/common.tfvars.example) | default platform node, shared storage mappings, deployable guest networks, template IDs, and cloud-init SSH keys |
| [`terraform/environments/foundation/terraform.tfvars.example`](../../../terraform/environments/foundation/terraform.tfvars.example) | foundation VM hardware shape, tags, storage class, disk size, and network zone |
| [`ansible/inventory/hosts.yml.example`](../../../ansible/inventory/hosts.yml.example) | stable logical host keys and foundation groups |
| [`ansible/group_vars/all.yml.example`](../../../ansible/group_vars/all.yml.example) | hostname prefix or suffix, domain, guest IP map, SSH user, port, and baseline defaults |
| [`ansible/group_vars/all.env.yml.example`](../../../ansible/group_vars/all.env.yml.example) | optional environment overlay for `all.<env>.yml` when using `--env` |
| [`ansible/group_vars/foundation.yml.example`](../../../ansible/group_vars/foundation.yml.example) | FreeIPA domain, realm, DNS behavior, and encrypted FreeIPA passwords |

## IaC used for this

Use these repo paths here:

| IaC path | Used for here | You edit |
| --- | --- | --- |
| [`terraform/common.tfvars.example`](../../../terraform/common.tfvars.example) | shared Terraform inputs used across environments, including the default platform node | your local `terraform/common.tfvars` |
| [`terraform/environments/foundation/terraform.tfvars.example`](../../../terraform/environments/foundation/terraform.tfvars.example) | provisions the foundation VM layout for identity and PKI hosts | `terraform/environments/foundation/terraform.tfvars` based on `.example` |
| [`ansible/inventory/hosts.yml.example`](../../../ansible/inventory/hosts.yml.example) | starting point for the stable foundation inventory groups | your local `ansible/inventory/hosts.yml` |
| [`ansible/group_vars/all.yml.example`](../../../ansible/group_vars/all.yml.example) | starting point for shared Ansible defaults and the default environment | your local `ansible/group_vars/all.yml` |
| [`ansible/group_vars/all.env.yml.example`](../../../ansible/group_vars/all.env.yml.example) | starting point for environment-specific hostname decoration, domain, and IP maps | your local `ansible/group_vars/all.<env>.yml` |
| [`ansible/group_vars/foundation.yml.example`](../../../ansible/group_vars/foundation.yml.example) | starting point for FreeIPA and foundation service inputs | your local encrypted `ansible/group_vars/foundation.yml` |
| [`ansible/playbooks/foundation.yml`](../../../ansible/playbooks/foundation.yml) | applies baseline configuration, installs the first FreeIPA host, sanity-checks it, and then installs replicas | inventory and foundation group variables |
| [`scripts/deploy.sh`](../../../scripts/deploy.sh) | repository wrapper for the mapped precheck, Terraform, and Ansible flow | choose the `foundation` setup when you are ready to run it |

Current boundary:

- Ansible inventory owns stable logical host keys and service groups
- Ansible group vars own hostname decoration, domain, and guest IP map
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
- keep the inventory groups aligned with the host intent:
  `identity_primary`, `identity_replicas`, `issuing_ca`, and optional
  `root_ca`

For environment separation, keep one stable inventory and separate ignored
local data files and state:

| Environment | Local var file | Wrapper command |
| --- | --- | --- |
| first validation run | `terraform/environments/foundation/terraform.tfvars` plus `ansible/group_vars/all.test.yml` and `foundation.test.yml` | `bash scripts/deploy.sh foundation --env test` |
| lab, dev, or staging | `terraform/environments/foundation/terraform.tfvars` plus matching Ansible env and setup vars | `bash scripts/deploy.sh foundation --env lab1` |
| production | `terraform/environments/foundation/terraform.tfvars` | `bash scripts/deploy.sh foundation` |

The wrapper stores local Terraform state separately per setup and environment,
for example `.terraform/state/foundation/test/terraform.tfstate`.

Terraform uses the base `terraform/common.tfvars` and foundation
`terraform.tfvars` for every environment by default. Add
`terraform/common.<env>.tfvars` or
`terraform/environments/foundation/terraform.<env>.tfvars` only when that
environment intentionally needs different platform values, VM sizes, or
placement.

Put the hostname prefix or suffix, domain, and IP map in
`ansible/group_vars/all.<env>.yml`. Use DNS-safe environment names with
letters, numbers, and dashes. Do not add leading or trailing separators to the
prefix or suffix; the automation adds the dash when needed. The initializer
fills the prefix from `--env`; you still edit the domain and IPs before
deployment. If you prefer suffix-style names, clear the prefix and set
`platform_hostname_suffix` instead.

No `--env` means production and uses the base local files:
`terraform/common.tfvars`, `terraform/environments/foundation/terraform.tfvars`,
`ansible/group_vars/all.yml`, and `ansible/group_vars/foundation.yml`.

With `--env`, the wrapper automatically loads both environment-wide vars and
foundation setup vars, for example `ansible/group_vars/all.test.yml` and
`ansible/group_vars/foundation.test.yml`. Use `--ansible-vars` only for an
extra one-off override.

Example with the recommended first `test` inputs:

```bash
bash scripts/init-local-files.sh --env test

bash scripts/deploy.sh foundation --env test
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

After the shared-service hosts are ready:

1. verify `FreeIPA`, DNS, and replication health from the deployment machine
2. configure the issuing CA on the `cryptography` host and chain it to the root
   CA when you use one
3. keep the root CA host in `ceremony` offline except during planned CA
   ceremonies
4. add Windows support later only if the environment needs it
5. continue with Vault once identity, DNS, and PKI are ready

## Read more

- [Infrastructure automation layout](../../reference/infrastructure-automation-layout.md)
- [Repository scripts](../../reference/repository-scripts.md)
- [Shared services model](../../architecture/shared-services.md)
- [Windows and AD support](windows-support.md)
- [Hardware-backed user authentication](hardware-keys.md)
- [Edge proxy path](edge.md)
- [Vault foundation deployment](vault.md)
- [Private cloud maturity path](../private-cloud-maturity.md)
- [Secret strategy](../../security/secret-strategy.md)
- [Environment variable conventions](../../reference/environment-variables.md)
- [Network architecture](../../architecture/network.md)
- [Proxmox reference platform](../../platforms/proxmox/README.md)
