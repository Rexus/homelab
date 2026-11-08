# Local development setup

Prepare a developer checkout to edit the kit, preview generated repositories and
run offline checks. No server, platform credentials or hosted source control is
required. Deployment uses a separately prepared execution host.

**Working directory:** the cloned upstream kit root, containing `tests/` and `scripts/`.
**Prerequisites:** Git and Python 3 with pip/venv support. Generator compatibility is
recorded in the [generation contract](generated-repositories.md#purpose-and-prerequisites).

<a id="table-of-contents"></a>

## Contents

- [Step 1: Prepare the developer environment](#step-1-prepare-the-developer-environment)
- [Step 2: Locate the change and preview generation](#step-2-locate-the-change-and-preview-generation)
- [Step 3: Run a focused offline check](#step-3-run-a-focused-offline-check)
- [Step 4: Select the deployment path when needed](#step-4-select-the-deployment-path-when-needed)
- [Which runtime does each command use?](#ansible-environment)
- [Where are private deployment inputs created?](#local-repository-files)
- [Read more](#read-more)
- [References](#references)

<a id="local-setup"></a>
<a id="purpose"></a>
<a id="developer-environment"></a>

## Step 1: Prepare the developer environment

For Linux/WSL Bash, from the kit root: [1]

```bash
# Run from upstream kit root
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r tests/requirements.txt
```

For native Windows PowerShell, use the environment's interpreter directly:

```powershell
# Run from upstream kit root
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tests/requirements.txt
```

The commands below use Bash. On native Windows, substitute
`.\.venv\Scripts\python.exe` for `python3`; Bash-wrapper/native checks use Linux/WSL.
If venv support is missing, install the OS Python venv package first, separately
from these Python commands. Do not use `sudo pip` or bypass managed-system Python.

The upstream kit's `tests/requirements.txt` lists PyYAML, Jinja2, jsonschema and
python-hcl2; see [repository testing](testing.md). It does not install Terraform,
Ansible or product tools. Generation alone needs only Python and PyYAML from the
kit's `scripts/tier-repos/requirements.txt`; see the [generation contract](generated-repositories.md#purpose-and-prerequisites).

## Step 2: Locate the change and preview generation

| Change | Start here |
| --- | --- |
| Tier-owned Terraform, Ansible or cluster inputs | [Code layout](code-layout.md); source is under `tier-0/`, `tier-1/` or `tier-2/` |
| Stateless shared helper, role or profile | `shared/`; it owns no inventory, resources or state |
| Generator, starter documents or refresh behavior | `scripts/tier-repos/`; [generated repository contract](generated-repositories.md) |
| Local environment/configuration only | The owning private generated repository; [repository workflow](repository-workflow.md) |

Preview without creating a collection:

```bash
# Run from upstream kit root
python3 scripts/tier-repos/generate.py --dry-run
```

When a generated checkout is needed, omit `--dry-run`:

```bash
# Run from upstream kit root
python3 scripts/tier-repos/generate.py
```

This creates `../<prefix>-iac/` with lowercase sibling repository folders.
It creates files, not remotes or infrastructure. Add the same `--prefix` and `--root`
selections to both commands when customized; the
[generator contract](generated-repositories.md#prefix-casing) defines prefix/default behavior.

## Step 3: Run a focused offline check

For generator/ownership/refresh changes, from the kit root:

```bash
# Run from upstream kit root
python3 -B -m unittest discover -s tests -p 'test_tier_repos.py' -v
```

Select the relevant module for other changes. [Repository testing](testing.md)
separates offline checks from native validators and their tool/cache requirements.
Inspect failures and skips; a passing generator test does not verify deployment.
Review the [secret-scanning checks](secret-scanning.md) before publication.

<a id="platform-prerequisites"></a>
<a id="deployment-machine"></a>
<a id="automation-vm-example"></a>

## Step 4: Select the deployment path when needed

For real infrastructure work, follow the [bootstrap execution-host guide](../deployment/foundation/proxmox/bootstrap.md).
It owns manual template/VM creation, verified API trust, SSH, artifacts and initial
state. An independent authorized workstation can also satisfy that contract;
Proxmox hosts and Talos nodes are not general-purpose execution hosts.

The [control-node reference](../reference/control-node-tooling.md#platform-prerequisites)
retains the platform prerequisites, tool list, approved package-install commands,
compatibility and offline preparation. The developer venv above is not a deployment
credential or a complete control-node installation.

<a id="ansible-environment"></a>
<a id="automatic-template-runtime"></a>

## Which runtime does each command use?

| Path | Runtime and preparation |
| --- | --- |
| Generator / offline developer checks | Developer venv above; no platform access |
| Linux `deploy.sh` | Accepted Ansible environment, Terraform and setup-aware precheck; [manual tooling details](../reference/control-node-tooling.md#ansible-environment) |
| Tier 0 template `setup`, `apply`, `verify`, `replace-disk` | Automatically prepares/selects its isolated runtime; [options, CI and offline behavior](../reference/control-node-tooling.md#automatic-template-runtime) |
| Kubernetes / direct product recipes | Their explicit Terraform/Talos/Kubernetes/Helm/Ansible prerequisites; [selected deployment guide](../deployment/README.md) |

Template runtime preparation does not configure the other paths automatically.
Its declared requirements and control-node compatibility remain in the reference.

<a id="local-repository-files"></a>

## Where are private deployment inputs created?

Follow the selected stage from the owning tier root, not the kit or collection root.
Initializers seed missing ignored files; existing inventory, inputs and original
state remain tier-owned. Keep editing those local files rather than recreating
state or expecting refresh to merge YAML/HCL/dotenv content.

The [local-input reference](../reference/control-node-tooling.md#local-repository-files)
preserves exact initialization, shared-profile precedence and permission details.
[Repository workflow](repository-workflow.md) identifies what belongs upstream,
in private project history, or in independent secret/state backups.

## Read more

- [Code layout](code-layout.md) and [repository workflow](repository-workflow.md)
- [Generator/refresh contract](generated-repositories.md)
- [Control-node tooling](../reference/control-node-tooling.md)
- [Environment inputs](../reference/environment-variables.md) and [secret handling](../administration/secret-handling/strategy.md)

## References

1. [Python virtual environments and interpreter/activation behavior](https://docs.python.org/3/library/venv.html), checked 2026-11-08.
