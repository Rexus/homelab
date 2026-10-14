# Identity foundation path

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
Run repository scripts from this root; paths below are repository-relative.

**Design:** [identity authority](../../../architecture/identity/README.md).

## Table of contents

- [Purpose](#purpose)
- [Prerequisites](#prerequisites)
- [Repository access](#repository-access)
- [Default private-domain shape](#default-private-domain-shape)
- [Authentication design](#authentication-design)
- [Using an existing domain](#using-an-existing-domain)
- [Configuration](#configuration)
- [IaC used for this](#iac-used-for-this)
- [Staged identity rollout](#staged-identity-rollout)
- [How to shape the deployment](#how-to-shape-the-deployment)
- [What comes next](#what-comes-next)
- [Read more](#read-more)

## Purpose

Use this path for the dedicated directory pair in [Step 1](../README.md#step-1-deploy-the-directory-pair).
The [cryptographic trust stage](../../stage-2-trust/README.md#step-1-prepare-issuer-and-key-custody) already supplies trust;
this procedure adds FreeIPA, DNS and replication rather than recreating that CA.

The combined foundation root contains:

- `2` dedicated FreeIPA VMs with DNS in `identity`: `idm-1` and `idm-2`
- `1` issuing CA in `cryptography`
- `0-1` offline root CA host in `ceremony`

FreeIPA runs outside Kubernetes. Keycloak runs inside the Tier 0 Kubernetes cluster
and connects to this pair for the [control-service identity path](../../stage-4-control-services/README.md#step-1-deploy-identity-federation).
The `foundation` setup owns the FreeIPA VMs; it does not install Keycloak.
Bootstrap access must work without either service being available.

When the issuer was provisioned in the trust stage using this root, add the identity VMs
to its existing desired configuration and state. Preserve the issuer's host key,
VMID and inputs; replacing the configuration with an identity-only map would plan
removal of the managed CA host. An existing external issuer needs no duplicate VM.

This is the default authority path for the repository, not a mandatory global
prerequisite. Existing identity, DNS, and PKI services can provide the shared
services for later paths.

A connected authority with domain-wide control is Tier 0; offline root-key
custody is separate. Guest
network keys must map to that tier's actual networks. See
[setup ownership](../../../development/generated-repositories.md#setup-ownership).

<a id="before-you-start"></a>

## Prerequisites

- local tooling is ready
- the deployment machine already has `ansible-core` and `terraform`
- Proxmox API access is working
- repo-local working files have been initialized with
  `bash scripts/init-local-files.sh --setup foundation`
- the local FreeIPA vars file has real non-secret values and protected password inputs
- the deployment environment file has the Proxmox API values, or the shell has
  equivalent variables set
- the network plan already includes at least `management`, `identity`, and
  `cryptography`
- the Enterprise Linux template is available for the first shared-service hosts
- repository/update access exists for the foundation hosts

## Repository access

Do not start this path until the foundation hosts can install required
software. That access can come from the existing network, mirrors, offline
repos, or the repository [Cache path](../../stage-1-foundation/step-3b-outbound-cache.md). The cache guide owns the
proxy design, variables, and bootstrap notes.

## Default private-domain shape

Use this as the starting point:

Use a private internal subdomain for the platform domain, such as
`corp.example.com` or `internal.example.com`. Do not use the same DNS name as
the public website, such as `example.com`, for the internal identity and PKI
domain.

| Component | Terraform default | Inventory entry | Network key | Purpose |
| --- | --- | --- | --- | --- |
| identity hosts | `idm-1`, `idm-2` active | `idm-1`, `idm-2` present by default | `identity` | `FreeIPA`, DNS, and the first identity authority |
| issuing CA host | `ca-1` active | `ca-1` present by default | `cryptography` | online issuing CA for the platform |
| root CA host | `ca-root-1` commented, default `0` | uncomment `ca-root-1` when enabled | `ceremony` | optional offline root CA host |

Keep the root CA host separate from the identity hosts when enabled. Treat
it as a ceremony system that should normally stay offline outside planned CA
operations.

Both CA layers can later be hardened with HSM-backed keys, but the default
identity path does not require HSM on day one.

The Terraform example for this path lives in
`terraform/deployments/foundation/terraform.tfvars.example`. Commented
`vm_instances` are default `0` and should stay commented until
the matching Ansible inventory group and IP entry are enabled.

## Authentication design

Use `FreeIPA` with Kerberos as the core identity authority. Anchor user, host,
and service trust in PKI, then harden privileged users with hardware-backed
authentication.

Apply these rules when designing the domain:

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
principals, certificates, secret-platform-issued credentials, or the access-layer SSO
path when that exists.

Use [Hardware-backed user authentication](../../stage-4-control-services/step-3b-hardware-authentication.md) when ready
to add YubiKey OTP or PIV authentication.

## Using an existing domain

This deployment can be omitted when an existing environment already provides the
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
- keep environment-specific domains in `all.<env>.yml`
- keep environment-specific IP maps in the matching setup overlay, such as
  `foundation.<env>.yml`
- override subnets and VLANs in Terraform only when that environment needs a
  different network shape
- avoid deploying duplicate identity systems for labs unless isolation is the
  goal

<a id="what-you-configure"></a>

## Configuration

Edit these local files before deployment:

| Repository | Path inside that repository | Configuration |
| --- | --- | --- |
| Tier 0 | [`terraform/common.tfvars.example`](../../../../tier-0/terraform/common.tfvars.example) | tier guest networks and optional platform overrides; shared storage and local SSH paths follow [platform inputs](../../../reference/platform-inputs.md) |
| Tier 0 | [`terraform/deployments/foundation/terraform.tfvars.example`](../../../../tier-0/terraform/deployments/foundation/terraform.tfvars.example) | foundation VM hardware shape, tags, storage class, disk size, and network zone |
| Tier 0 | [`ansible/inventory/hosts.yml.example`](../../../../tier-0/ansible/inventory/hosts.yml.example) | stable logical host keys and foundation groups |
| Tier 0 | [`ansible/group_vars/all.yml.example`](../../../../tier-0/ansible/group_vars/all.yml.example) | hostname prefix or suffix, domain, SSH user, port, and baseline defaults |
| Tier 0 | [`ansible/group_vars/all.env.yml.example`](../../../../tier-0/ansible/group_vars/all.env.yml.example) | optional environment overlay for `all.<env>.yml` when using `--env` |
| Tier 0 | [`ansible/group_vars/foundation.yml.example`](../../../../tier-0/ansible/group_vars/foundation.yml.example) | foundation host IPs, domain, realm, DNS behavior and controller-side secret lookups |

## IaC used for this

The inputs above stay in Tier 0. Follow these entry points to their implementation:

| Repository | Code path inside that repository | Responsibility |
| --- | --- | --- |
| Tier 0 | [terraform/deployments/foundation/main.tf](../../../../tier-0/terraform/deployments/foundation/main.tf) | Provisions the configured identity and PKI VMs through tier-local modules |
| Tier 0 | [ansible/playbooks/deployment/identity-freeipa.yml](../../../../tier-0/ansible/playbooks/deployment/identity-freeipa.yml) | Baseline, primary installation, verification and replica installation |
| Tier 0 | [scripts/deploy.sh](../../../../tier-0/scripts/deploy.sh) | Tier entry point; select `foundation` |
| Shared | [scripts/deploy.sh](../../../../shared/scripts/deploy.sh) | Reusable execution implementation, using Tier 0 inputs/state |
| Shared | [ansible/roles/baseline/](../../../../shared/ansible/roles/baseline/) | Common host preparation, reused by the Tier 0 recipe |

Current boundary:

- Ansible inventory owns stable logical host keys and service groups
- Ansible `all` group vars own hostname decoration and domain
- foundation group vars own the foundation guest IP map
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

Use the default shape unless the environment has a documented need for a
different authority layout.

- keep `management`, `identity`, and `cryptography` defined before adding
  other optional zones
- keep `2` identity hosts unless this is only a short-lived test environment
- place the identity hosts on different Proxmox nodes when the platform allows
  it
- keep the issuing CA on its own dedicated host in `cryptography`
- enable a root CA host in `ceremony` only for a separate offline
  ceremony system from the start
- keep the inventory groups aligned with the host intent:
  `identity_primary`, `identity_replicas`, `issuing_ca`, and optional
  `root_ca`

For environment separation within a tier, keep one stable inventory and separate ignored
local data files and state:

| Environment | Local var file | Wrapper command |
| --- | --- | --- |
| first validation run | `terraform/deployments/foundation/terraform.tfvars` plus `ansible/group_vars/all.test.yml` and `foundation.test.yml` | `bash scripts/deploy.sh foundation --env test` |
| lab, dev, or staging | `terraform/deployments/foundation/terraform.tfvars` plus matching Ansible env and setup vars | `bash scripts/deploy.sh foundation --env lab1` |
| production | `terraform/deployments/foundation/terraform.tfvars` | `bash scripts/deploy.sh foundation` |

The wrapper stores local Terraform state separately per setup and environment,
for example `.terraform/state/foundation/test/terraform.tfstate`.

Terraform uses the base `terraform/common.tfvars` and foundation
`terraform.tfvars` for every environment by default. Add
`terraform/common.<env>.tfvars` or
`terraform/deployments/foundation/terraform.<env>.tfvars` only when that
environment intentionally needs different platform values, VM sizes, or
placement.

Put the hostname prefix or suffix and domain in
`ansible/group_vars/all.<env>.yml`. Put foundation IPs in
`ansible/group_vars/foundation.<env>.yml`. Use DNS-safe environment names with
letters, numbers, and dashes. Do not add leading or trailing separators to the
prefix or suffix; the automation adds the dash when needed. The initializer
fills the prefix from `--env`; the domain and setup IPs still require configuration before
deployment. For suffix-style names, clear the prefix and set
`platform_hostname_suffix` instead.

No `--env` means production and uses the base local files:
`terraform/common.tfvars`, `terraform/deployments/foundation/terraform.tfvars`,
`ansible/group_vars/all.yml`, and `ansible/group_vars/foundation.yml`.

With `--env`, the wrapper automatically loads both environment-wide vars and
foundation setup vars, for example `ansible/group_vars/all.test.yml` and
`ansible/group_vars/foundation.test.yml`. Use `--ansible-vars` only for an
extra one-off plain-YAML override. Keep these files readable by Terraform.
Supply `FREEIPA_DM_PASSWORD` and `FREEIPA_ADMIN_PASSWORD` through protected
controller inputs. For encrypted secret-only files, use the separate
[Ansible-only workflow](../../../administration/secret-handling/ansible-vault.md#encrypted-secret-file).

Example with the recommended first `test` inputs:

```bash
bash scripts/init-local-files.sh --setup foundation --env test

bash scripts/deploy.sh foundation --env test
```

The wrapper automatically loads `.env.local` when it exists. Add
`--env-file path/to/file` to override that with another file.

To remove a disposable environment after testing, run the same setup with
`--destroy`:

```bash
bash scripts/deploy.sh foundation --env test --destroy
```

To deploy the setup, use the repository deployment wrapper with
the `foundation` setup. Keep the exact execution flow in the wrapper rather
than repeating it in this guide. That wrapper also checks the required local
config files for the setup before it runs.

## What comes next

Verify FreeIPA, DNS and replication from the deployment machine, including the
selected trust relationship with the existing issuer. Keep root custody offline. Continue
with the [Step 2: Kubernetes cluster](../README.md#step-2-create-the-kubernetes-cluster), then
[Stage 4: Control services](../../stage-4-control-services/README.md).
Windows integration and hardware-backed user authentication are optional later work.

## Read more

- [Infrastructure automation layout](../../../development/code-layout.md)
- [Repository scripts](../../../reference/repository-scripts.md)
- [Shared services model](../../../architecture/service-boundaries.md)
- [Windows and AD support](../../../architecture/identity/windows-integration.md)
- [Hardware-backed user authentication](../../stage-4-control-services/step-3b-hardware-authentication.md)
- [Edge proxy path](../../stage-5-delivery/procedures/edge-proxy.md)
- [Cache path](../../stage-1-foundation/step-3b-outbound-cache.md)
- [Vault foundation deployment](../../stage-4-control-services/step-2b-vault-vm.md)
- [Deployment readiness](../../readiness.md)
- [Secret strategy](../../../administration/secret-handling/strategy.md)
- [Environment variable conventions](../../../reference/environment-variables.md)
- [Network architecture](../../../architecture/networking/README.md)
- [Proxmox reference platform](../../stage-1-foundation/procedures/proxmox.md)
