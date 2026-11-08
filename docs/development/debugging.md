# Find and fix a bug

Start with the first failing phase. The error's file path or Ansible task name
usually identifies the code owner; later failures may be consequences.

## Contents

- [1. Confirm the working repository](#1-confirm-the-working-repository)
- [2. Open the responsible files](#2-open-the-responsible-files)
- [3. Reproduce the smallest failing path](#3-reproduce-the-smallest-failing-path)
- [4. Verify the fix](#4-verify-the-fix)

## 1. Confirm the working repository

For a Linux deployment, start in the owning **tier repository root**:

```bash
# Run from the owning tier repository root
pwd
cat .deployment-setups
bash scripts/deploy.sh --help
```

The setup must appear in that repository's `.deployment-setups`. Kubernetes and
template lifecycle use their dedicated commands; find them in the
[script reference](../reference/repository-scripts.md).
Use the [repository map](README.md#which-repository) if the working directory is unclear.

## 2. Open the responsible files

The links below open the actual upstream code. In generated auto-docs, links to
tier and Shared payloads point into the corresponding generated repositories.

| First failure | Owner | Open first |
| --- | --- | --- |
| Missing Shared checkout or unknown setup | Owning tier, then Shared | [Tier entry point](../../tier-2/scripts/deploy.sh), `.deployment-setups`, then [context resolution](../../shared/scripts/lib/deployment-context.sh) |
| Wrong environment, input file or execution phase | Shared helper plus tier-local inputs | [Deployment helper](../../shared/scripts/deploy.sh) and the [input contract](../reference/platform-inputs.md) |
| Wrong guest name, missing IP or inventory key | Owning tier | [Inventory resolution](../../tier-2/terraform/modules/environment_guests/main.tf), `ansible/inventory/hosts.yml` and setup group vars |
| VM/LXC plan or provider resource error | Owning tier | Error's `terraform/deployments/<setup>/` or `terraform/modules/` file; [guest module](../../tier-2/terraform/modules/vm/main.tf) is one example |
| SDN lookup, TLS or API permission error | Tier inputs and Shared lookup | Tier `.env.local`, `terraform/common.tfvars`, [SDN lookup](../../shared/scripts/proxmox-sdn.py); [API/trust setup](../deployment/foundation/proxmox/api-access.md) |
| `TASK [role_name : ...]` | Tier-specific or Shared reusable role | Matching role's `tasks/`, `defaults/`, `templates/` and handlers; [cache role](../../tier-2/ansible/roles/cache_proxy/tasks/main.yml) is one example |
| Cluster add-on or application Helm/config error | Owning tier's recipe; tier or Shared role | [Cluster platform](../../shared/ansible/roles/cluster_platform/tasks/main.yml), [control applications](../../tier-0/ansible/roles/control_applications/tasks/main.yml) or [Observability](../../tier-1/ansible/roles/observability_platform/tasks/main.yml) |
| Generated file missing or preserved unexpectedly | Upstream kit | `scripts/tier-repos/payload.py`, `generated_files.py` in that directory, and the [preservation contract](generated-repositories.md#refresh-and-local-ownership) |

**Example: cache behavior.** From Tier 2, find the inventory group, recipe and
role references together:

```bash
# Run from <prefix>-tier-2/
rg -n 'cache_proxy|hosts: cache|platform_host_ips' ansible
```

Then open only the matching role task or template. Change a setting in the
private group vars when a supported input already exists; change the role when
the behavior itself is wrong. Shared roles are resolved through the tier's
`ansible/ansible.cfg`; Shared never supplies the live inventory.

## 3. Reproduce the smallest failing path

| Failure area | First reproduction |
| --- | --- |
| New generation | From the kit root: `bash scripts/init-tier-repos.sh --dry-run` |
| Refresh or preservation | From the kit root: `bash scripts/init-tier-repos.sh --refresh --dry-run` |
| Linux provisioning | Use the owning setup's wrapper with `--plan-only` |
| Service configuration | Follow that service's existing verification procedure; inspect the recipe before rerunning it |
| Kubernetes product | Use the named installer and kubeconfig from its deployment guide; identify whether the resource is Helm-, manifest- or controller-owned |

For a refresh reproduction, reuse the original `--prefix` and `--root` selections.
The [generator contract](generated-repositories.md) owns collection selection.

For the cache example, with accepted Tier 2 local inputs and verified Proxmox access:

```bash
# Run from <prefix>-tier-2/
bash scripts/deploy.sh cache --env-file .env.local --plan-only
```

This stops before applying resources. Its control-node precheck may install local
dependencies, and Terraform still reads the selected API, inventory and state.
Keep the same `--env` and input overrides as the failing run when reproducing it.

An Ansible recipe may include service restarts or failover validation. Inspect it
before using `--ansible-only`; check mode is not proof that every task is harmless
or supports simulation. Kubernetes starter directories are not necessarily the
installer: locate the role that creates the actual release.

## 4. Verify the fix

For an upstream helper change, a focused example is:

```bash
# Run from upstream kit root
python3 -B -m unittest discover -s tests -p 'test_tier_ci_execution.py' -v
git diff --check
```

Run from the **upstream kit root**, with the [test environment](testing.md) ready.
Choose the test module matching the changed component; generated tier repositories
do not contain the upstream suite. Add a regression check for a behavioral bug.

Record the command, first error, affected file and verification result. Keep
credentials, private environment files and raw Terraform state out of bug reports.
For a new path rather than a fix, follow [Add a service](adding-service.md).
