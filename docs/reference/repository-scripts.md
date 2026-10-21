# Repository scripts

## Table of contents

- [Purpose](#purpose)
- [Script overview](#script-overview)
- [Cheat sheet](#cheat-sheet)
- [Initialize tier repositories](#initialize-tier-repositories)
- [Initialize local files](#initialize-local-files)
- [Environment isolation](#environment-isolation)
- [Run a deployment](#run-a-deployment)
- [Available setups](#available-setups)
- [What the deployment wrapper does](#what-the-deployment-wrapper-does)
- [Manual equivalent](#manual-equivalent)
- [Read more](#read-more)

## Purpose

Use this reference to understand the repository wrapper scripts or
to run the same Terraform and Ansible flow manually.

The scripts do not replace the guides. They keep repeated safety checks,
environment loading, local state paths, and setup-specific run order in one
place so each guide can focus on the deployment.

User-facing scripts support `--help`. Run generation from the kit root and
operational commands from the owning tier root (`tier-N/` in the source
checkout, `<prefix>-tier-N/` in a generated collection).

## Script overview

Paths in this table are relative to the source kit root. The tier-local
`scripts/init-local-files.sh` and `scripts/deploy.sh` files are shortcuts to
these shared implementations.

| Script | What it solves | Use case |
| --- | --- | --- |
| `scripts/init-tier-repos.sh` | generates tier-owned inputs and shared automation | to generate the repo set |
| `shared/scripts/init-local-files.sh` | creates ignored local files | when setting up the repo or an environment |
| `shared/scripts/deploy.sh` | runs precheck, Terraform, and Ansible | to deploy, plan, or destroy a setup |
| `tier-0/scripts/proxmox-templates.sh` | initializes, plans, or publishes Tier 0 templates | local recovery or template CD jobs |
| `shared/scripts/log-evidence.py` via Tier 0's `scripts/log-evidence.sh` | generates synthetic manifests and reconciles received/restored records | [Logging drill](../administration/logging-drill.md); no faults or service changes |
| `shared/scripts/kubernetes-cluster.sh` via each tier's `scripts/kubernetes-cluster.sh` | initializes cluster inputs, plans, bootstraps, and exports credentials; currently Talos | [Kubernetes cluster](../deployment/stage-3-identity/procedures/kubernetes.md) |

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
| Run a supported maintenance recipe | `bash scripts/deploy.sh <setup> --env <env> --recipe maintenance` |
| Run Terraform only | `bash scripts/deploy.sh <setup> --env <env> --terraform-only` |
| Destroy an environment | `bash scripts/deploy.sh <setup> --env <env> --destroy` |
| Reset rebuilt host SSH keys | `bash scripts/deploy.sh <setup> --env <env> --reset-known-hosts` |

Template publication uses the separate
[Tier 0 template workflow](../administration/compute/template-lifecycle.md#local-workflow),
not `deploy.sh`. It uses provider-native environment variables, a local image
catalog, and its own state; it never configures a Talos guest through Ansible.

Each tier's independent Kubernetes cluster currently uses the [Talos implementation](../deployment/stage-3-identity/procedures/talos-terraform.md)
and `bash scripts/kubernetes-cluster.sh init` from its own root. It owns a separate state
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

Read [Generated repository model](../development/generated-repositories.md) for the
authoritative ownership, inventory, prerequisite, and refresh contracts.
From a tier root, call shared automation directly with a relative path:

```bash
bash ../homelab-shared/scripts/init-local-files.sh --setup foundation --env test
```

Use the selected prefix in that path. The tier-local `scripts/` shortcuts used
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

Use `--setup <name>` to create local files for one path. Repeat it
to select several setups. Omit `--setup` to create every setup.

Use `--env <name>` for any supported environment name, such as `test`, `lab1`,
`dev`, or `stage`. Omit `--env` for production.

The initializer copies examples only. The generated local files still require configuration
before deployment.

## Environment isolation

**`--env` separates state and selects overlays; it does not allocate independent resources.**
Never apply a second state to VMIDs already managed by another environment.
The initializer copies setup IPs from the same examples and does not create Terraform
environment overlays. Before running test and production on the same platform:

| Input | Required separation |
| --- | --- |
| VM/LXC identifiers | Allocate unused VMIDs in `terraform/deployments/<setup>/terraform.<env>.tfvars`; a supplied `vm_instances` or `lxc_instances` map replaces that complete base map |
| Host IPs | Set the complete `platform_host_ips` map in `ansible/group_vars/<stem>.<env>.yml` |
| Names and domains | Review `all.<env>.yml`; generated prefixes do not reserve DNS or addresses |
| VIPs, VRRP IDs, MACs and listeners | Allocate non-conflicting service values in the setup overlay; different hostnames alone do not isolate them |
| Network and credentials | Select isolated networks/scopes where required; `--env` creates neither firewall policy nor permissions |

For one disposable run, the base hardware file may hold its allocations. Before using
the base files for production, retire that test deployment under its original state
or keep explicit non-overlapping overlays for both. Do not solve a collision by importing
the same live resource into another state. Review every plan against the allocation record.

## Run a deployment

After completing [environment isolation](#environment-isolation), plan the first
foundation run for a disposable environment:

```bash
bash scripts/deploy.sh foundation --env test --plan-only
```

Deploy the same environment:

```bash
bash scripts/deploy.sh foundation --env test
```

Use a non-interactive Terraform apply after reviewing the plan:

```bash
bash scripts/deploy.sh foundation --env test --auto-approve
```

Destroy a disposable environment:

```bash
bash scripts/deploy.sh foundation --env test --destroy
```

When destroying and recreating VMs with the same IPs, clear stale SSH host keys
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

All supplied Terraform roots verify Proxmox TLS. Provisioning entry points reject
`PROXMOX_VE_INSECURE` and `PM_VE_INSECURE` values that enable or ambiguously request
a bypass, including values loaded from the Linux wrapper's environment file.
Install independently verified [bootstrap trust](../administration/compute/proxmox-tls.md)
before planning; platform PKI is not required. Ansible-only work and local initialization
do not need Proxmox API verification exceptions.

| Option | Purpose |
| --- | --- |
| `--env NAME` | separate Ansible environment vars and separate local Terraform state |
| `--env-file PATH` | load provider credentials from another dotenv file |
| `--plan-only` | run Terraform init and plan only |
| `--terraform-only` | provisioning only, without mapped host playbooks |
| `--ansible-only` | rerun mapped host playbooks without Terraform |
| `--playbook PATH` | select an existing tier-local `deployment/<name>.yml` or `maintenance/<name>.yml`; requires Ansible-only execution, leaves Terraform root/state unchanged |
| `--recipe deployment\|maintenance` | default deployment; maintenance implies Ansible-only and rejects Terraform plan/apply/destroy modes |
| `--destroy` | destroy the selected setup and environment |
| `--auto-approve` | run Terraform apply or destroy without an interactive approval |
| `--reset-known-hosts` | after rebuilding guests, remove stale SSH known-host entries for the setup IPs |
| `--var-file PATH` | replace the setup Terraform tfvars file |
| `--common-var-file PATH` | replace the tier-wide Terraform tfvars file, not the shared template catalog |
| `--ansible-vars PATH` | add a plain YAML layer consumed by both tools; encrypted secret-only files require `--ansible-only` or maintenance |
| `--inventory PATH` | select another Ansible inventory file |

## Available setups

This is the capability catalog. Source and generated tiers enable the subset in
their `.deployment-setups`; see [setup ownership](../development/generated-repositories.md#setup-ownership).

| Setup | What it targets | Start with |
| --- | --- | --- |
| `foundation` | shared identity, DNS, issuing CA, and optional root CA hosts | [Identity foundation path](../deployment/stage-3-identity/procedures/freeipa.md) |
| `syslog` | Tier 0 VMs/disks, baseline and isolated TLS receiver after mount/certificate preparation; not an HA/WORM installer | [Foundational logging](../deployment/stage-1-logging/README.md) |
| `edge` | Tier 2 public edge load-balancer set with rotated VIP ownership | [Edge proxy path](../deployment/stage-5-delivery/procedures/edge-proxy.md) |
| `cache` | shared cache pair or larger set for controlled outbound access | [Cache path](../deployment/foundation/step-3b-outbound-cache.md) |
| `development` | GitLab on a dedicated Podman VM | [Development platform path](../deployment/stage-5-delivery/step-1b-source-control-vm.md) |
| `vault` | early Vault foundation host or hosts | [Vault foundation deployment](../deployment/stage-4-secrets/step-1b-vault-vm.md) |
| `observability` | Optional Tier 1 gateway, metrics and search VMs; OS baseline only, not the Kubernetes product deployment or Tier 0 evidence | [Observability VM alternative](../deployment/stage-6-observability/step-1b-dedicated-vms.md) |
| `podman-runner` | application-platform runner hosts for Podman and bootc image builds | [Podman image runner guide](../deployment/stage-5-delivery/step-1c-podman-runner.md) |
| `immutable-template` | image-based Linux template builder hosts | [Image-based Linux path](../deployment/stage-5-delivery/step-1d-image-based-linux.md) |
| `template-refresh` | staged refresh of mutable Enterprise Linux templates | [Enterprise Linux template](../deployment/foundation/procedures/enterprise-linux-template.md) |
| `hsm` | USB or software HSM gateway deployment pattern | [USB HSM active-active blueprint](../deployment/stage-2-trust/step-1b-usb-hsm.md) |
| `lab` | general-purpose lab guests | this reference and the local inventory |

## What the deployment wrapper does

For each setup, `scripts/deploy.sh`:

1. checks that required local files exist
2. loads `.env.local` when it exists, unless `--env-file` points elsewhere
3. maps `PROXMOX_*` values to the Terraform provider variables
4. runs the setup-aware local Ansible control-node precheck, preferring OS
   packages for missing collections before falling back to Galaxy
5. runs Terraform with setup-specific local state under `.terraform/state/`
6. loads the shared platform profile and image catalog, then tier common inputs,
   optional environment overlays, and setup tfvars in a predictable order
7. passes the Ansible inventory and group-vars paths into Terraform so guest
   names and IPs stay owned once
8. runs the mapped Ansible playbook or playbooks for the selected setup

Maintenance skips provisioning and uses `ansible/playbooks/maintenance/<setup>.yml`.
See [recipe scope](../administration/ansible-recipes.md) before running it; reconciliation can
restart services. [Platform inputs](platform-inputs.md) owns the complete
precedence and local SSH-key contract.

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

The shared [platform profile](platform-inputs.md) and
[template catalog](template-catalog.md) load before tier inputs.
In these commands, `homelab-shared` is the generated sibling; substitute
the prefix, or use `shared` in the source layout.

```bash
cd terraform/deployments/foundation
export TF_DATA_DIR="../../../.terraform/data/foundation/test"

terraform init -reconfigure \
  -backend-config="path=../../../.terraform/state/foundation/test/terraform.tfstate"

terraform plan \
  -var-file=../../../../homelab-shared/config/platform.tfvars \
  -var-file=../../../../homelab-shared/templates/proxmox-catalog.tfvars \
  -var-file=../../common.tfvars \
  -var-file=terraform.tfvars \
  -var='ansible_inventory_path=../../../ansible/inventory/hosts.yml' \
  -var='ansible_group_vars_paths=["../../../ansible/group_vars/all.yml","../../../ansible/group_vars/foundation.yml","../../../ansible/group_vars/all.test.yml","../../../ansible/group_vars/foundation.test.yml"]'

terraform apply \
  -var-file=../../../../homelab-shared/config/platform.tfvars \
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

- [Local setup](../development/local-setup.md)
- [Infrastructure automation layout](../development/code-layout.md)
- [Environment variable conventions](environment-variables.md)
- [Identity foundation path](../deployment/stage-3-identity/procedures/freeipa.md)
