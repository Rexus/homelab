# Repository scripts

## Table of contents

- [Purpose](#purpose)
- [Script overview](#script-overview)
- [Cheat sheet](#cheat-sheet)
- [Initialize tier repositories](#initialize-tier-repositories)
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

User-facing scripts support `--help`. Run generation from the kit root and
operational commands from the owning tier root (`tier-N/` in the source
checkout, `<prefix>-tier-N/` in a generated collection).

## Script overview

Paths in this table are relative to the source kit root. The tier-local
`scripts/init-local-files.sh` and `scripts/deploy.sh` files are shortcuts to
these shared implementations.

| Script | What it solves | When you use it |
| --- | --- | --- |
| `scripts/init-tier-repos.sh` | generates tier-owned inputs and shared automation | when you want the generated repo set |
| `shared/scripts/init-local-files.sh` | creates ignored local files | when setting up the repo or an environment |
| `shared/scripts/deploy.sh` | runs precheck, Terraform, and Ansible | when you deploy, plan, or destroy a setup |
| `tier-0/scripts/proxmox-templates.sh` | initializes, plans, or publishes Tier 0 templates | local recovery or template CD jobs |
| `tier-0/scripts/kubernetes-cluster.sh` | initializes cluster inputs, plans, bootstraps, and exports credentials; currently Talos | [Kubernetes cluster](../platforms/kubernetes/README.md) |

## Cheat sheet

Commands containing `init-tier-repos.sh` run from the kit root. Other commands
use tier-local shortcuts from the owning tier root. Replace `<setup>` with a
registered setup such as `foundation`, `cache`, `vault`, or `observability`.
Omit `--env <env>` for production.

| Goal | Command |
| --- | --- |
| Show tier-repo generator help | `bash scripts/init-tier-repos.sh --help` |
| Show init help | `bash scripts/init-local-files.sh --help` |
| Show deploy help | `bash scripts/deploy.sh --help` |
| Preview generated tier repositories | `bash scripts/init-tier-repos.sh --dry-run` |
| Generate the repository collection | `bash scripts/init-tier-repos.sh` |
| Generate only shared and Tier 0 repositories | `bash scripts/init-tier-repos.sh --repo shared --repo tier-0` |
| Refresh generated tier-repo files | `bash scripts/init-tier-repos.sh --refresh` |
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

Template publication uses the separate
[Tier 0 template workflow](../platforms/proxmox/template-lifecycle.md#local-workflow),
not `deploy.sh`. It uses provider-native environment variables, a local image
catalog, and its own state; it never configures a Talos guest through Ansible.

The Kubernetes control cluster currently uses the [Talos implementation](../platforms/talos/terraform.md)
and `bash scripts/kubernetes-cluster.sh init` from Tier 0. It owns a separate state
root, uses tier-local inventory, and does not use the Linux setup/environment wrapper.

## Initialize tier repositories

Create `../homelab-iac/` with the five repositories inside:

```bash
bash scripts/init-tier-repos.sh
```

Use `--prefix mylab` to rename the collection and repos, `--root /path/to/parent`
to choose the collection's parent, and `--dry-run` to preview without writing.

Generate only shared automation and Tier 0:

```bash
bash scripts/init-tier-repos.sh --repo shared --repo tier-0
```

Refresh generated files only:

```bash
bash scripts/init-tier-repos.sh --refresh
```

Run refresh from the updated upstream checkout with the same custom root and
prefix flags used at creation. It preserves local edits and recorded deletions.

The generator creates `<prefix>-tier-0`, `<prefix>-tier-1`,
`<prefix>-tier-2`, `<prefix>-shared`, and `<prefix>-architecture` inside
`<prefix>-iac/`. Only the child directories are repository homes.
It populates tier-owned service code and common modules/helpers, plus separate
inventory examples, group vars, and Terraform setups in each tier. Python and
PyYAML are required. Refresh uses recorded hashes and preserves locally edited
files. Root READMEs, project documentation, and cluster/bootstrap skeletons are
seeded only once; `docs/auto-docs/` holds refreshable upstream guidance.

Read [Generated repository model](generated-repository-model.md) for the
authoritative ownership, inventory, prerequisite, and refresh contracts.
From a tier root, call shared automation directly with a relative path:

```bash
bash ../homelab-shared/scripts/init-local-files.sh --setup foundation --env test
```

Use your chosen prefix in that path. The tier-local `scripts/` shortcuts used
below delegate to the same shared code. The same local shortcut commands also
work from `tier-0/`, `tier-1/`, or `tier-2/` in a private source checkout,
where the sibling is named `shared/`. Omitted `--setup` initializes
only the setups registered in the current tier.

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

This uses the selected environment's merged `platform_host_ips` through the
shared `ansible/playbooks/reset-known-hosts.yml` playbook. It removes only
static IP and `[IP]:22` entries from the operator's `~/.ssh/known_hosts`;
DHCP names and other environments are untouched. Use it only after a known
rebuild and verify replacement fingerprints through a trusted channel.

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
| `--common-var-file PATH` | you want to replace the tier-wide Terraform tfvars file, not the shared template catalog |
| `--ansible-vars PATH` | you want an extra YAML vars layer consumed by both Terraform and Ansible |
| `--inventory PATH` | you want another Ansible inventory file |

## Available setups

This is the capability catalog. Source and generated tiers enable the subset in
their `.deployment-setups`; see [setup ownership](generated-repository-model.md#setup-ownership).

| Setup | What it targets | Start with |
| --- | --- | --- |
| `foundation` | shared identity, DNS, issuing CA, and optional root CA hosts | [Identity foundation path](../paths/shared-services/identity.md) |
| `edge` | shared edge load-balancer set with rotated VIP ownership | [Edge proxy path](../paths/shared-services/edge.md) |
| `cache` | shared cache pair or larger set for controlled outbound access | [Cache path](../paths/shared-services/cache.md) |
| `development` | GitLab on a dedicated Podman VM | [Development platform path](../paths/application-platform/development.md) |
| `vault` | early Vault foundation host or hosts | [Vault foundation deployment](../paths/shared-services/vault.md) |
| `observability` | system-control telemetry, syslog, metrics, logs, and archive hosts | [Observability path](../paths/system-control/observability.md) |
| `podman-runner` | application-platform runner hosts for Podman and bootc image builds | [Podman image runner guide](../paths/application-platform/podman-runner.md) |
| `immutable-template` | image-based Linux template builder hosts | [Image-based Linux path](../paths/application-platform/image-based-linux.md) |
| `template-refresh` | staged refresh of mutable Enterprise Linux templates | [Enterprise Linux template](../platforms/proxmox/enterprise-linux-template.md) |
| `hsm` | USB or software HSM gateway deployment pattern | [USB HSM active-active blueprint](../security/usb-hsm-active-active-blueprint.md) |
| `lab` | general-purpose lab guests | this reference and your local inventory |

## What the deployment wrapper does

For each setup, `scripts/deploy.sh`:

1. checks that required local files exist
2. loads `.env.local` when it exists, unless `--env-file` points elsewhere
3. maps `PROXMOX_*` values to the Terraform provider variables
4. runs the setup-aware local Ansible control-node precheck, preferring OS
   packages for missing collections before falling back to Galaxy
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
| `terraform/common.test.tfvars` | optional tier-wide Terraform override |
| `terraform/deployments/foundation/terraform.test.tfvars` | optional setup Terraform override |

Terraform override files are optional. Use them only when that environment
needs different platform values, VM sizes, storage, or placement.

## Manual equivalent

For `foundation --env test`, start in the Tier 0 repository root, or `tier-0/`
in a private source checkout. Its Ansible config resolves local service roles
and shared baseline roles without setting an extra path variable.

1. Prepare local files.

```bash
cp env.local.example .env.local
cp terraform/common.tfvars.example terraform/common.tfvars
cp terraform/deployments/foundation/terraform.tfvars.example \
  terraform/deployments/foundation/terraform.tfvars
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
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
ansible-playbook -i localhost, playbooks/control-node.yml \
  -e control_node_setup=foundation
cd ..
```

4. Run Terraform with the same state and var layering.

The shared [template catalog](../platforms/proxmox/template-catalog.md) is loaded
first. In these commands, `homelab-shared` is the generated sibling; substitute
your prefix, or use `shared` in the source layout.

```bash
cd terraform/deployments/foundation
export TF_DATA_DIR="../../../.terraform/data/foundation/test"

terraform init -reconfigure \
  -backend-config="path=../../../.terraform/state/foundation/test/terraform.tfstate"

terraform plan \
  -var-file=../../../../homelab-shared/templates/proxmox-catalog.tfvars \
  -var-file=../../common.tfvars \
  -var-file=terraform.tfvars \
  -var='ansible_inventory_path=../../../ansible/inventory/hosts.yml' \
  -var='ansible_group_vars_paths=["../../../ansible/group_vars/all.yml","../../../ansible/group_vars/foundation.yml","../../../ansible/group_vars/all.test.yml","../../../ansible/group_vars/foundation.test.yml"]'

terraform apply \
  -var-file=../../../../homelab-shared/templates/proxmox-catalog.tfvars \
  -var-file=../../common.tfvars \
  -var-file=terraform.tfvars \
  -var='ansible_inventory_path=../../../ansible/inventory/hosts.yml' \
  -var='ansible_group_vars_paths=["../../../ansible/group_vars/all.yml","../../../ansible/group_vars/foundation.yml","../../../ansible/group_vars/all.test.yml","../../../ansible/group_vars/foundation.test.yml"]'

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
