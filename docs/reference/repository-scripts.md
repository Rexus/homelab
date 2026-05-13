# Repository scripts

## Table of contents

- [Purpose](#purpose)
- [Script overview](#script-overview)
- [Cheat sheet](#cheat-sheet)
- [Initialize local files](#initialize-local-files)
- [Run a deployment](#run-a-deployment)
- [Available setups](#available-setups)
- [What the deployment wrapper does](#what-the-deployment-wrapper-does)
- [Manual equivalent](#manual-equivalent)
- [Read more](#read-more)

## Purpose

Use this reference when you want to understand the repository wrapper scripts or
when you want to run the same Terraform and Ansible flow manually.

The scripts do not replace the guides. They keep repeated safety checks,
environment loading, local state paths, and setup-specific run order in one
place so each guide can focus on what you are deploying.

Both scripts support `--help`.

## Script overview

| Script | What it solves | When you use it |
| --- | --- | --- |
| `scripts/init-local-files.sh` | creates ignored local files from the tracked examples | once when you set up the repo, and again when you add a new environment |
| `scripts/deploy.sh` | runs the control-node precheck, Terraform, and mapped Ansible playbooks | whenever you deploy, plan, or destroy a setup |

## Cheat sheet

Replace `<setup>` with a setup such as `foundation`, `cache`, `vault`, or
`observability`. Omit `--env <env>` for production.

| Goal | Command |
| --- | --- |
| Show init help | `bash scripts/init-local-files.sh --help` |
| Show deploy help | `bash scripts/deploy.sh --help` |
| Create all local files | `bash scripts/init-local-files.sh` |
| Create local files for one setup | `bash scripts/init-local-files.sh --setup <setup>` |
| Create local files for one environment | `bash scripts/init-local-files.sh --setup <setup> --env <env>` |
| Refresh local files from examples | `bash scripts/init-local-files.sh --overwrite` |
| Remove generated backup files | `bash scripts/init-local-files.sh --clean-backups` |
| Plan an environment deployment | `bash scripts/deploy.sh <setup> --env <env> --plan-only` |
| Deploy an environment | `bash scripts/deploy.sh <setup> --env <env>` |
| Deploy production | `bash scripts/deploy.sh <setup>` |
| Deploy without Terraform prompt | `bash scripts/deploy.sh <setup> --env <env> --auto-approve` |
| Rerun Ansible only | `bash scripts/deploy.sh <setup> --env <env> --ansible-only` |
| Run Terraform only | `bash scripts/deploy.sh <setup> --env <env> --terraform-only` |
| Destroy an environment | `bash scripts/deploy.sh <setup> --env <env> --destroy` |
| Reset rebuilt host SSH keys | `bash scripts/deploy.sh <setup> --env <env> --reset-known-hosts` |

## Initialize local files

Create the base production files:

```bash
bash scripts/init-local-files.sh
```

Create only the shared defaults and foundation files:

```bash
bash scripts/init-local-files.sh --setup foundation
```

Create foundation files plus a disposable `test` environment:

```bash
bash scripts/init-local-files.sh --setup foundation --env test
```

Refresh local files from current examples and keep timestamped backups:

```bash
bash scripts/init-local-files.sh --overwrite
```

Remove timestamped backups created by `--overwrite`:

```bash
bash scripts/init-local-files.sh --clean-backups
```

Use `--setup <name>` when you only want local files for one path. Repeat it
when you want several setups. Omit `--setup` to create every setup.

Use `--env <name>` for any environment name you want, such as `test`, `lab1`,
`dev`, or `stage`. Omit `--env` for production.

The initializer copies examples only. You still edit the generated local files
before deployment.

## Run a deployment

Plan the first foundation run for a disposable environment:

```bash
bash scripts/deploy.sh foundation --env test --plan-only
```

Deploy the same environment:

```bash
bash scripts/deploy.sh foundation --env test
```

Use a non-interactive Terraform apply after you have reviewed the plan:

```bash
bash scripts/deploy.sh foundation --env test --auto-approve
```

Destroy a disposable environment:

```bash
bash scripts/deploy.sh foundation --env test --destroy
```

If you destroy and recreate VMs with the same IPs, clear stale SSH host keys
for that setup before Ansible runs:

```bash
bash scripts/deploy.sh foundation --env test --reset-known-hosts
```

Run production by omitting `--env`:

```bash
bash scripts/deploy.sh foundation
```

Use another environment file when `.env.local` is not the right source:

```bash
bash scripts/deploy.sh foundation --env test --env-file secrets/proxmox-test.env
```

Useful options:

| Option | Use it when |
| --- | --- |
| `--env NAME` | you want separate Ansible environment vars and separate local Terraform state |
| `--env-file PATH` | you want to load provider credentials from another dotenv file |
| `--plan-only` | you want Terraform init and plan only |
| `--terraform-only` | you want provisioning only, without mapped host playbooks |
| `--ansible-only` | you want to rerun mapped host playbooks without Terraform |
| `--destroy` | you want Terraform to destroy the selected setup and environment |
| `--auto-approve` | you want Terraform apply or destroy to run without an interactive approval |
| `--reset-known-hosts` | you rebuilt guests and want to remove stale SSH known-host entries for the setup IPs |
| `--var-file PATH` | you want to replace the setup Terraform tfvars file |
| `--common-var-file PATH` | you want to replace the shared Terraform tfvars file |
| `--ansible-vars PATH` | you want one extra Ansible vars file after automatic vars |
| `--inventory PATH` | you want another Ansible inventory file |

## Available setups

| Setup | What it targets | Start with |
| --- | --- | --- |
| `foundation` | shared identity, DNS, issuing CA, and optional root CA hosts | [Identity foundation path](../paths/shared-services/identity.md) |
| `edge` | shared edge load-balancer pair or larger set | [Edge proxy path](../paths/shared-services/edge.md) |
| `cache` | shared cache pair or larger set for controlled outbound access | [Cache path](../paths/shared-services/cache.md) |
| `development` | GitLab on a dedicated Podman VM | [Development platform path](../paths/application-platform/development.md) |
| `vault` | early Vault foundation host or hosts | [Vault foundation deployment](../paths/shared-services/vault.md) |
| `observability` | system-control telemetry, syslog, metrics, logs, and archive hosts | [Observability path](../paths/system-control/observability.md) |
| `podman-runner` | application-platform runner hosts for Podman and bootc image builds | [Podman image runner guide](../paths/application-platform/podman-runner.md) |
| `image-template` | image-based Linux template builder hosts | [Image-based Linux path](../paths/application-platform/image-based-linux.md) |
| `template-refresh` | staged refresh of mutable Enterprise Linux templates | [Enterprise Linux template](../platforms/proxmox/enterprise-linux-template.md) |
| `hsm` | USB or software HSM gateway deployment pattern | [USB HSM active-active blueprint](../security/usb-hsm-active-active-blueprint.md) |
| `lab` | general-purpose lab guests | this reference and your local inventory |

## What the deployment wrapper does

For each setup, `scripts/deploy.sh`:

1. checks that required local files exist
2. loads `.env.local` when it exists, unless `--env-file` points elsewhere
3. maps `PROXMOX_*` values to the Terraform provider variables
4. runs the local Ansible control-node precheck
5. runs Terraform with setup-specific local state under `.terraform/state/`
6. layers `terraform/common.tfvars`, optional environment overlays, and setup
   tfvars in a predictable order
7. passes the Ansible inventory and group-vars paths into Terraform so guest
   names and IPs stay owned once
8. runs the mapped Ansible playbook or playbooks for the selected setup

When `--env test` is used, the wrapper automatically looks for:

| File | Purpose |
| --- | --- |
| `ansible/group_vars/foundation.yml` | base foundation setup settings and IP map |
| `ansible/group_vars/all.test.yml` | environment-wide domain and hostname decoration |
| `ansible/group_vars/foundation.test.yml` | foundation setup settings and IP map for that environment |
| `terraform/common.test.tfvars` | optional shared Terraform override |
| `terraform/environments/foundation/terraform.test.tfvars` | optional setup Terraform override |

Terraform override files are optional. Use them only when that environment
needs different platform values, VM sizes, storage, or placement.

## Manual equivalent

The wrapper is intentionally boring. This is the same idea when you run it by
hand for `foundation --env test`.

1. Prepare local files.

```bash
cp env.local.example .env.local
cp terraform/common.tfvars.example terraform/common.tfvars
cp terraform/environments/foundation/terraform.tfvars.example \
  terraform/environments/foundation/terraform.tfvars
cp ansible/inventory/hosts.yml.example ansible/inventory/hosts.yml
cp ansible/group_vars/all.yml.example ansible/group_vars/all.yml
cp ansible/group_vars/foundation.yml.example ansible/group_vars/foundation.yml
cp ansible/group_vars/all.env.yml.example ansible/group_vars/all.test.yml
cp ansible/group_vars/foundation.yml.example ansible/group_vars/foundation.test.yml
```

2. Load or export provider credentials.

```bash
set -a
. ./.env.local
set +a

export TF_VAR_proxmox_api_url="${PROXMOX_API_URL}"
export TF_VAR_proxmox_api_token_id="${PROXMOX_API_TOKEN_ID}"
export TF_VAR_proxmox_api_token_secret="${PROXMOX_API_TOKEN_SECRET}"
```

3. Prepare the deployment machine.

```bash
cd ansible
ansible-playbook -i localhost, playbooks/control-node.yml
cd ..
```

4. Run Terraform with the same state and var layering.

```bash
cd terraform/environments/foundation
export TF_DATA_DIR="../../../.terraform/data/foundation/test"

terraform init -reconfigure \
  -backend-config="path=../../../.terraform/state/foundation/test/terraform.tfstate"

terraform plan \
  -var-file=../../common.tfvars \
  -var='ansible_inventory_path=../../../ansible/inventory/hosts.yml' \
  -var='ansible_group_vars_paths=["../../../ansible/group_vars/all.yml","../../../ansible/group_vars/foundation.yml","../../../ansible/group_vars/all.test.yml","../../../ansible/group_vars/foundation.test.yml"]' \
  -var-file=terraform.tfvars

terraform apply \
  -var-file=../../common.tfvars \
  -var='ansible_inventory_path=../../../ansible/inventory/hosts.yml' \
  -var='ansible_group_vars_paths=["../../../ansible/group_vars/all.yml","../../../ansible/group_vars/foundation.yml","../../../ansible/group_vars/all.test.yml","../../../ansible/group_vars/foundation.test.yml"]' \
  -var-file=terraform.tfvars

cd ../../..
```

5. Run the mapped Ansible playbook.

```bash
cd ansible
ansible-playbook \
  -i inventory/hosts.yml \
  -e @group_vars/all.yml \
  -e @group_vars/foundation.yml \
  -e @group_vars/all.test.yml \
  -e @group_vars/foundation.test.yml \
  playbooks/foundation.yml
```

The manual flow is useful for learning and troubleshooting. For normal use,
prefer the wrapper so state paths, file checks, and setup run order stay
consistent.

## Read more

- [Local setup](../getting-started/local-setup.md)
- [Infrastructure automation layout](infrastructure-automation-layout.md)
- [Environment variable conventions](environment-variables.md)
- [Identity foundation path](../paths/shared-services/identity.md)
