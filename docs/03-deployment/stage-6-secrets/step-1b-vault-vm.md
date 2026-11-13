# Step 1b: Vault on a dedicated VM

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
Run repository scripts from this root; paths below are repository-relative.

<a id="vault-foundation-deployment"></a>

**Branch from:** [Step 1](README.md#step-1-deploy-the-secret-service), instead of deploying the cluster instance.
**Change:** Use the supplied VM-based secret-service deployment.
**Return:** [Action 9](README.md#step-9-install-independent-recovery-copies) for scheduled recovery copies and the common acceptance gates; do not run the Kubernetes installation.

**Design:** [secret-service responsibilities](../../01-architecture/08-cryptography/README.md).

<a id="figure-vault-vm"></a>

## Expected outcome: dedicated Vault runtime

```mermaid
%%{init: {"theme":"base","flowchart":{"nodeSpacing":20,"rankSpacing":24,"padding":12,"subGraphTitleMargin":{"top":4,"bottom":12}},"themeVariables":{"lineColor":"#627581","edgeLabelBackground":"#f8fafc"}}}%%
flowchart LR
  Operator["Authorized operator<br/>Manual initialization / unseal"]
  subgraph T0["Tier 0 / Control"]
    direction BT
    Recovery["Independent share and backup custody"]
    subgraph PVE["Existing Proxmox / cryptography network"]
      direction TB
      VM["vault-1<br/>Vault installed / initially sealed"]
      Data[("OS disk / local Raft data")]
      VM --> Data
    end
    Recovery -. Manual unseal / recovery transfer .-> PVE
  end
  Operator -->|Verified TLS / authorized bootstrap| T0
  classDef default fill:#f8fafc,stroke:#64748b,color:#1f2937
  classDef actor fill:#edf0f3,stroke:#697682,color:#293642
  classDef control fill:#e2f3ed,stroke:#397366,color:#173f36
  classDef data fill:#eeeafa,stroke:#78639b,color:#42325d
  classDef boundary fill:#eef2f6,stroke:#64748b,color:#1f2937
  classDef custody fill:#fff2d1,stroke:#926820,color:#584013
  class Operator actor
  class T0,VM control
  class PVE boundary
  class Data data
  class Recovery custody
```

**IaC:** *Figure: The VM installer leaves Vault sealed on its local Raft disk. Authorized custodians initialize and
unseal it using independently retained recovery material.*
Tier 0 [VM inputs](../../../tier-0/terraform/deployments/vault/terraform.tfvars.example)
and [Vault recipe](../../../tier-0/ansible/playbooks/deployment/vault-vm.yml).
Initialization, unseal and independent share custody are manual operations after installation.

## Table of contents

- [Purpose](#purpose)
- [Prerequisites](#prerequisites)
- [Step 1: Configure inputs](#configuration)
- [IaC used for this](#iac-used-for-this)
- [Step 2: Deploy](#plan-and-deploy)
- [Step 3: Initialize and unseal](#operator-bootstrap)
- [Step 4: Configure audit and SSO](#step-4-configure-audit-and-sso)
- [After deployment](#after-deployment)
- [Later hardening](#later-hardening)
- [Read more](#read-more)
- [References](#references)

## Purpose

Use this guide after identity, DNS, and PKI are available to
deploy Vault as the shared secret-platform service.


The [dedicated Vault figure](#figure-vault-vm) shows the sealed service installed after identity and PKI.
Initialization, audit/SSO configuration and recovery acceptance follow in separate numbered steps.

<a id="before-you-start"></a>

## Prerequisites

- identity, DNS, and the first PKI path already exist from this repo or from
  an existing environment
- the deployment machine already has `ansible-core` and `terraform`
- naming and the first TLS path for Vault already exist
- one dedicated Vault VM, or more when needed, is defined in the Vault
  environment
- each Vault host exists in the `vault` inventory group
- local copies of the example files exist before editing
- the current Vault role does not generate the first Vault certificate, key, or
  CA file automatically
- gateway and host-firewall policy permits only approved consumers/operators to
  the configured API listener (`8200/tcp` in the example); additional Raft peers
  need their selected cluster listener (`8201/tcp`). The role and Shared baseline
  do not install those network rules; follow the [firewall rollout](../foundation/network/firewall.md).

<a id="what-you-configure"></a>

<a id="configuration"></a>

## Step 1: Configure inputs

Initialize missing local files from Tier 0:

Run from **`<prefix>-tier-0/`**.

```bash
bash scripts/init-local-files.sh --setup vault
```

Edit the local copies **without `.example`** before deployment. The links below show their source shapes;
do not change the examples. This VM installer requires a qualified RedHat-family image, such as EL10;
it does not implement the Debian package path.

| Repository | Path inside that repository | Configuration |
| --- | --- | --- |
| Tier 0 | [`terraform/common.tfvars.example`](../../../tier-0/terraform/common.tfvars.example) | tier guest networks and optional platform overrides; shared storage and local SSH paths follow [platform inputs](../../08-reference/platform-inputs.md) |
| Tier 0 | [`terraform/deployments/vault/terraform.tfvars.example`](../../../tier-0/terraform/deployments/vault/terraform.tfvars.example) | Vault VM definitions in `vm_instances` |
| Tier 0 | [`ansible/inventory/hosts.yml.example`](../../../tier-0/ansible/inventory/hosts.yml.example) | stable Vault host key and inventory group |
| Tier 0 | [`ansible/group_vars/all.env.yml.example`](../../../tier-0/ansible/group_vars/all.env.yml.example) | environment-specific hostname decoration and domain when using `--env` |
| Tier 0 | [`ansible/group_vars/vault.yml.example`](../../../tier-0/ansible/group_vars/vault.yml.example) | Vault host IPs, `vault_api_addr`, `vault_cluster_addr`, `vault_node_id`, TLS source paths, and listener settings |

<a id="how-to-shape-the-deployment"></a>

### Deployment shape

The Vault environment can deploy one or more Vault nodes through
`vm_instances`, but this guide uses the default single-node path.

Use this default matrix:

| Component | Terraform default | Inventory action | Network / zone | Purpose |
| --- | --- | --- | --- | --- |
| Vault host | `vault-1` active | `vault-1` present by default | `cryptography` / Control | first dedicated Vault node |
| additional Vault hosts | not present, default `0` | add matching inventory and IP entries when added | `cryptography` / Control | optional multi-node Raft expansion |
| LXC helpers | `lxc_instances = {}` | not used | n/a | no helper containers by default |

The Terraform example for this path lives in
`terraform/deployments/vault/terraform.tfvars.example`. The Tier 0 Ansible
inventory includes `vault-1` because it matches the active Terraform default.
The foundation run does not touch it because the foundation playbook targets
only the foundation groups.

The starter places privileged secrets at `10.20.21.40` on the cryptography
network, not on the application subnet. Existing deployments keep their local
inputs during refresh; moving a live Vault service requires a separate reviewed
network, DNS, TLS, firewall, and recovery plan.

Use these first-node settings:

- keep `vault_raft_retry_join` empty for the first single-node deployment
- keep `vault_seal_hcl` empty for the default Shamir path; a selected seal integration must be qualified/configured before initialization
- keep TLS enabled from the first startup
- keep the Vault host dedicated to Vault

## IaC used for this

The inputs above stay in Tier 0. Follow these entry points to their implementation:

| Repository | Code path inside that repository | Responsibility |
| --- | --- | --- |
| Tier 0 | [terraform/deployments/vault/main.tf](../../../tier-0/terraform/deployments/vault/main.tf) | Dedicated Vault VMs through tier-local modules |
| Tier 0 | [ansible/playbooks/deployment/vault-vm.yml](../../../tier-0/ansible/playbooks/deployment/vault-vm.yml) and [ansible/roles/vault/](../../../tier-0/ansible/roles/vault) | Vault host preparation and installation |
| Tier 0 | [scripts/deploy.sh](../../../tier-0/scripts/deploy.sh) | Tier entry point; select `vault` |
| Shared | [scripts/deploy.sh](../../../shared/scripts/deploy.sh) | Reusable execution implementation, using Tier 0 inputs/state |
| Shared | [ansible/roles/baseline/](../../../shared/ansible/roles/baseline) | Common host preparation, reused by the Tier 0 recipe |

This deployment flow installs Vault and prepares the first node. Operator
initialization, unseal handling, and secret handoff stay manual.

Use the shared ownership rule from
[Infrastructure automation layout](../../04-development/code-layout.md):
Ansible inventory owns stable logical host keys and service groups. Ansible
`all` group vars own hostname decoration and domain. Vault group vars own the
Vault IP map, while the Vault Terraform environment owns hardware placement
and Proxmox tags.

<a id="plan-and-deploy"></a>

## Step 2: Deploy

Check the selected VM and local Raft placement against the [Vault runtime figure](#figure-vault-vm).

Prepare the TLS files and local inputs above, then deploy:

Run from **`<prefix>-tier-0/`**.

```bash
bash scripts/deploy.sh vault
```

Review the inline Terraform plan and enter `yes` only for the intended changes.
Add `--plan-only` for a preview without installation; approved unattended jobs use
`--auto-approve`.

**Result:** a new Vault service is installed, running and sealed; the wrapper does not initialize or unseal it.

<a id="operator-bootstrap"></a>

## Step 3: Initialize and unseal

Use a trusted operator terminal, not CI logs. Configure the CLI with the actual
HTTPS endpoint and local CA bundle from the chosen TLS configuration. [1]

Run from **`<prefix>-tier-0/`**.

```bash
read -r -p "Vault HTTPS URL from vault_api_addr: " VAULT_ADDR
read -r -p "Absolute path to the trusted Vault CA bundle: " VAULT_CACERT
export VAULT_ADDR VAULT_CACERT
vault status
```

A sealed server returns exit code 2 from `vault status`; inspect its `Initialized`
and `Sealed` fields. Initialize only a new, uninitialized service. Recovery of an
existing service uses its original data and keys, never another initialization. [2]
Prepare protected share/root-token custody first; PGP output encryption is supported. [3]
For the selected three-share/two-custodian Shamir example:

If a different seal was selected through [1c](step-1c-seal-integration.md), use that qualified provider's
initialization/recovery ceremony instead of the Shamir example below. Changing seals on an existing
initialized service requires the supported migration procedure and retained backups.

Run from **`<prefix>-tier-0/`**.

```bash
vault operator init -key-shares=3 -key-threshold=2
```

Retain the resulting material under the selected custody policy. Enter two distinct
shares interactively, then authenticate before configuring the audit device: [2][4]

Run from **`<prefix>-tier-0/`**.

```bash
vault operator unseal
vault operator unseal
vault login
```

The login uses the protected initial root token at the prompt; do not put it in a
command argument. Configure and test normal scoped administrative access before
revoking bootstrap authority. Forward audit records to protected logging before
storing important secrets; the local audit file alone is not the retained evidence archive.

## Step 4: Configure audit and SSO

In **`<prefix>-tier-0/ansible/group_vars/vault.yml`**, edit `control_applications_oidc_issuer`,
`control_applications_oidc_ca_pem`, `control_applications_oidc_client_secrets.vault`,
`control_applications_vault_policies` and `control_applications_vault_oidc_roles`.
Use the accepted Keycloak client with this VM's exact HTTPS callback, including its API port.
To register it through IaC, also set `control_applications_register_clients: true`,
`control_applications_hosts.keycloak`, `control_applications_keycloak_realm` and private
`control_applications_keycloak_auth` credentials. Otherwise retain the existing client owner.

From the **trusted bootstrap terminal**, supply the temporary bootstrap token without shell history:

```bash
read -r -s -p "Temporary Vault configuration token: " VAULT_TOKEN
export VAULT_TOKEN
```

Run from **`<prefix>-tier-0/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/deployment/vault-configure.yml -e @ansible/group_vars/vault.yml
```

**Expected:** native Vault API reconciliation enables persistent file/stdout audit, configures the
named bounded OIDC roles/policies and verifies actual Raft membership. No SSH session or Helm run is used.
Remove the temporary environment value after the configuration pass:

```bash
unset VAULT_TOKEN
```

Before returning to the main stage, enroll `/var/log/vault/audit.log` as a dedicated security file stream
through [Stage 2 forwarding](../stage-2-logging/procedures/sources.md). Test allowed and denied operations at intake,
qualify [human SSO](../stage-5-identity/procedures/service-sso.md), and commission
[scheduled independent snapshots](../../05-operations/06-resilience/backups/control-applications.md#configure-and-schedule).
Complete an [isolated restore](../../05-operations/06-resilience/recovery/vault.md) before accepting recovery.
These are controller-run integrations with independent recovery custody; initialization/unseal
remain the explicit human ceremony. After recording those checks, repeat `vault-configure.yml` with
`control_applications_vault_phase: accept` and the two matching acceptance fields set in private inputs.

## After deployment

After Vault is initialized:

- move shared service credentials and long-lived tokens into Vault
- keep root tokens and unseal material out of the repository and out of normal
  automation
- keep local Ansible Vault files as a fallback path, not the primary system of
  record
- continue the broader deployment only after Vault is reachable and audited

## Later hardening

Use this guide only for the first Vault shared-service deployment after the
identity and PKI layer exists.

For later hardening, higher availability, and future HSM-related paths, continue
with the security docs instead of extending this deployment guide:

- [Vault HSM hardening options](../../01-architecture/08-cryptography/06-vault-seal.md)
- [HSM getting started](../../01-architecture/08-cryptography/03-hsm-selection.md)
- [USB HSM active-active blueprint](../stage-3-trust/step-1b-usb-hsm.md)

## Read more

- [Identity foundation path](../stage-5-identity/procedures/freeipa.md)
- [Shared services model](../../01-architecture/02-organization/README.md)
- [Windows and AD support](../../01-architecture/09-identity/01-windows-integration.md)
- [Deployment readiness](../readiness.md)
- [Secret strategy](../../05-operations/03-cryptography/secret-handling.md)
- [Ansible Vault bootstrap fallback](../../05-operations/03-cryptography/ansible-vault.md)

## References

Operator command guidance checked 2026-10-16; use the installed release's documentation.

1. [Vault CLI address and CA configuration](https://developer.hashicorp.com/vault/docs/commands)
2. [Vault status and sealed exit code](https://developer.hashicorp.com/vault/docs/commands/status)
3. [Vault initialization and PGP protection](https://developer.hashicorp.com/vault/docs/commands/operator/init)
4. [Vault interactive authentication](https://developer.hashicorp.com/vault/docs/commands/login)
