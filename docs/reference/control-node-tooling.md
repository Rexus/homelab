# Control-node tooling

Detailed tool installation, compatibility, prechecks and execution inputs for
Linux/WSL deployment. For source edits, generator previews and offline checks,
start with [local development setup](../development/local-setup.md).

## Table of contents

- [Purpose](#purpose)
- [Platform prerequisites](#platform-prerequisites)
- [Deployment machine](#deployment-machine)
- [Dependency inventory](#dependency-inventory)
- [Automation VM example](#automation-vm-example)
- [Ansible environment](#ansible-environment)
- [Automatic template runtime](#automatic-template-runtime)
- [Local repository files](#local-repository-files)
- [Read more](#read-more)
- [References](#references)

## Purpose

This reference covers Linux/WSL infrastructure execution. Repository generation
needs only the [declared Python/PyYAML prerequisites](../development/generated-repositories.md#purpose-and-prerequisites),
without platform access. Real deployment needs the inputs below. For the first installation, follow the
[bootstrap execution-host guide](../deployment/foundation/proxmox/bootstrap.md):
manual Linux template, bootstrap VM, tools/artifacts, verified CA/API access, then IaC.
The bootstrap guide owns first-install commands; this reference owns tool scope,
compatibility, runtime behavior and dependency declarations.

## Platform prerequisites

Have these ready before running automation:

- access to the current platform, such as Proxmox
- an automation API token
- prepared guest network attachment values for `network_zones`, such as bridge
  or SDN VNet ID, optional VLAN tag, subnet, and gateway
- a prepared VM template or image source for managed instances
- an LXC template file if container provisioning will be used

For Proxmox token setup, read
[Proxmox API setup](../deployment/foundation/proxmox/api-access.md).
For the shared zone names and IaC mapping, read
[Network architecture](../architecture/networking/README.md).

## Deployment machine

Use one active writer per Terraform state. Bootstrap and CI may use different authorized execution
hosts at different times; preserve the original inputs/state during their handover.

That machine can be:

- the local workstation
- a dedicated automation VM after the first template exists

Require these tools there:

- Git
- Bash (Linux or WSL for deployment)
- Python 3 and PyYAML for generation and repository helpers
- `terraform`
- `ansible-core`
- SSH client tools
- `ca-certificates`, curl and OpenSSL for verified API access
- `xz`, `unzip` and tar for approved artifact unpacking
- `qemu-img` for template boot-disk inspection/maintenance (`qemu-utils` on Debian/Ubuntu)

`Packer` is only needed when building templates from the same machine.

Each deployment run starts with a local Ansible precheck on that deployment
machine. That precheck is setup-aware: it verifies only the Ansible collections
needed by the selected setup. Default `auto` mode tries missing collections from
OS packages first, then uses Galaxy to converge declared version ranges; versioned
requirements can still invoke Galaxy when installed. Set
`CONTROL_NODE_COLLECTIONS_MODE=check` for a prepared disconnected controller:
missing/incompatible effective collections fail without installing packages or
contacting Galaxy for collection installation. This does not disable guest package tasks.
For example, `foundation` includes directory and issuer requirements:
`community.general`, `ansible.posix`, `freeipa.ansible_freeipa`, `community.crypto`
and `ansible.mariadb`, while `cache` needs `community.general` and
`ansible.posix`.

Run the tier's `ansible/playbooks/control-node.yml`, which imports shared checks
with tier-owned requirements. Follow the
[offline bootstrap workflow](../deployment/foundation/proxmox/bootstrap-offline.md)
for matching-host package/wheel preparation, transitive Galaxy archives, locked
providers, verified SCP transfer and local installation. Shared owns `community.crypto`
for private PKI and public ACME. Tier 0 adds `freeipa.ansible_freeipa` and
`ansible.mariadb`. Each tier adds `kubernetes.core` and Python client dependencies
for native cluster applications; network-scoped recipes also use `ansible.utils`
for address validation. Install the owning tier's `ansible/requirements.txt` in the
accepted virtual environment, not the operating system's Python environment.
Keep accepted artifacts independently and select collection `check` mode for recovery.
Tier 0 template `apply` and `verify` also use `community.proxmox` to complete and
inspect raw template settings; their [runtime setup](#automatic-template-runtime) is automatic
and requires no guest SSH or hosted control service.

The repository deployment wrapper runs that precheck before Terraform or host
playbooks. Follow the root README or the setup-specific guide for the actual
run commands.

For provider credentials, use one of these paths:

| Source | How to use it |
| --- | --- |
| existing shell or runner variables | useful for runners and pipeline jobs |
| local ignored env file | useful for a dedicated automation VM |
| another env file path | useful when the deployment machine handles several contexts |

Ansible is configured for bootstrap-friendly SSH. New host keys are accepted
automatically with OpenSSH `StrictHostKeyChecking=accept-new`, while changed
host keys still stop the run. When destroying and recreating test guests with the
same IPs, use the deployment wrapper's `--reset-known-hosts` option for that
setup.

### Dependency inventory

Use these declarations to prepare an execution host; retain the resolved artifacts
with its reviewed kit revision. The manifests, not a second version list in prose,
define package/collection bounds.

| Dependency | Authoritative source / installation scope |
| --- | --- |
| OS commands | [Bootstrap Step 2a](../deployment/foundation/proxmox/bootstrap.md#2a-install-through-approved-sources): Git, Bash, Python/pip, SSH, CA/curl/OpenSSL, archive/storage utilities, Terraform and `qemu-img`; [offline OS download/install](../deployment/foundation/proxmox/bootstrap-offline.md#1a-download-os-packages-and-reviewed-source) |
| Optional home-directory migration | Pre-stage `rsync` and, on Enterprise Linux 10, `policycoreutils-python-utils` before restricting package access; included in the offline RPM download list for the [home-directory guide](../deployment/foundation/proxmox/bootstrap-home.md) |
| Separate bootstrap workspace filesystem | Prepare `parted` and `xfsprogs` before creating the new data mount; follow [workspace disk preparation](../deployment/foundation/proxmox/bootstrap-storage.md) before copying artifacts or installing the full runtime |
| Optional root-LVM expansion | EL10: pre-stage `lvm2`, `parted` and `xfsprogs`, included in the offline RPM list; the [existing-disk or new-PV guide](../deployment/foundation/proxmox/bootstrap-lvm.md) also lists Debian/Ubuntu package names |
| Python execution runtime | Tier 0 [runtime requirements](../../tier-0/ansible/runtime-requirements.txt); accepted interpreter plus Ansible/PyYAML/HCL tooling |
| Python module clients | Owning tier's requirements: [Tier 0](../../tier-0/ansible/requirements.txt), [Tier 1](../../tier-1/ansible/requirements.txt), [Tier 2](../../tier-2/ansible/requirements.txt); install in the accepted venv |
| Ansible collections | [Shared](../../shared/ansible/requirements.yml) plus [Tier 0](../../tier-0/ansible/requirements.yml), [Tier 1](../../tier-1/ansible/requirements.yml), [Tier 2](../../tier-2/ansible/requirements.yml); include transitive archives |
| Generator only | Upstream kit `scripts/tier-repos/requirements.txt`; [generation prerequisite contract](../development/generated-repositories.md#purpose-and-prerequisites) |
| Terraform providers | Each selected tier-local `terraform/deployments/<setup>/.terraform.lock.hcl`; [mirror selected roots without upgrading](../deployment/foundation/proxmox/bootstrap-offline.md#1c-mirror-locked-providers-and-stage-guest-artifacts) |
| Guest/service and Kubernetes software | Selected stage's roles, group vars, chart/product inputs and image sources; **outside** the controller dependency bundle, even when controller Python clients are included |

## Automation VM example

After the first template exists, a small dedicated automation VM is often
easier to keep stable than using a personal workstation.
Create it with the [bootstrap deployment guide](../deployment/foundation/proxmox/bootstrap.md),
then follow its [package and Terraform installation steps](../deployment/foundation/proxmox/bootstrap.md#2a-install-through-approved-sources).
An accepted independent workstation is
also valid. Proxmox hosts and Talos nodes are not general-purpose deployment machines.

The AlmaLinux/Rocky Linux first-run path installs OS tools, adds HashiCorp's RPM
repository and verifies Terraform before cloning/generation. It then prepares
Ansible from the checked-out manifests. EPEL is not required by that path;
additional repositories remain an explicit software-intake choice. [1][2]
Use versions satisfying the selected Terraform roots and Ansible collections;
an installed executable alone is not compatibility evidence. For an offline host,
use the [connected-host bundle preparation and SCP handoff](../deployment/foundation/proxmox/bootstrap-offline.md).
Do not make
this initial tool setup depend on the proxy/cache or hosted registry being deployed.

For other distributions, follow the current official install guides for
[Terraform](https://developer.hashicorp.com/terraform/install) and
[ansible-core](https://docs.ansible.com/ansible/latest/installation_guide/installation_distros.html).

Keep the automation VM simple:

- store a private working copy of the repository there
- keep the local Terraform vars, inventory, and group vars there
- give it access to the Proxmox API, Git remotes, and the package or collection
  sources it needs

## Ansible environment

The [explicit Ansible installation step](../deployment/foundation/proxmox/bootstrap.md#4-install-ansible)
offers an OS-package path for cache/compatible Linux recipes and an isolated, manifest-based
reference runtime for the complete toolchain. OS-packaged Ansible does not need venv activation;
`deploy.sh` prepares the collections for its selected setup. Collection `requires_ansible`
metadata must match the core version, even when a basic recipe happens to run. [9]

The isolated path installs `ansible/runtime-requirements.txt`, tier-owned Python module
manifests and collections. It is not a universal prerequisite for the cache recipe.
The Proxmox maintenance collection
requires `ansible-core >=2.17`; an OS package may supply an older release. Installing
`ansible/requirements.txt` installs module dependencies, not Ansible itself. [3][4]

Only when the isolated path was selected, activate it in a new shell on the bootstrap/deployment host:

```bash
source "$HOME/.local/share/homelab/venv/bin/activate"
```

For the isolated path on Debian/Ubuntu, install `python3-venv` first if needed;
use the selected Python version's package where applicable. [5]
Activate that environment in each new deployment shell before invoking tier
scripts. Install the owning tier's `ansible/requirements.txt` there and its declared
collections through that environment's `ansible-galaxy`; avoid `sudo pip` and user-site
installs mixed with a different system Ansible. For local-only installation, use
the [offline workflow](../deployment/foundation/proxmox/bootstrap-offline.md#3b-restore-the-kit-and-install-the-isolated-pythonansible-environment).

### Automatic template runtime

Run the usual `scripts/proxmox-templates.sh apply`, `verify` or `replace-disk`
command from **Tier 0**. It selects Python 3.12–3.14 and prepares
`.venv/proxmox-templates-py<version>/`, using `ansible/runtime-requirements.txt`.
It then runs `ansible/playbooks/prepare-template-runtime.yml` to install the tier's
Python module requirements and the declared Proxmox collection. Disk maintenance
also installs `qemu-img` when missing. Collection downloads stay under `.venv/collections/`.
Later runs reuse compatible packages without forcing upgrades.

| Setting or condition | Behavior |
| --- | --- |
| Default | Prepare and select the isolated runtime automatically; no `source` step |
| Python missing or too old | Install bootstrap packages from configured DNF/APT repositories |
| Missing OS packages | Use root/sudo; prompt for sudo locally when needed, never prompt in CI |
| `TEMPLATE_PYTHON=/path/to/python` | Select an already installed Python 3.12–3.14 explicitly |
| `TEMPLATE_RUNTIME_MODE=check` | Use preinstalled tools and existing checks; perform no dependency installation |
| Offline package sources | Install local wheels/collection tarballs first, then select `check`; `PIP_NO_INDEX`/`PIP_FIND_LINKS` alone do not prevent Galaxy access |

Pip packages stay inside the isolated runtime; system Ansible and the default Python
selection are retained. New Python minor versions get separate runtime directories.
The current runtime uses the tested Ansible 2.21 line. [6]
Enterprise Linux 10 supplies Python 3.12 by default; Enterprise Linux 9 can install
it alongside system Python. [7][8] Debian/Ubuntu must supply a compatible interpreter
through their configured repositories; the bootstrap never adds third-party OS repositories.

CI uses the same template command and exits before Terraform/Proxmox operations if
runtime preparation fails. Preinstall OS tools in an unprivileged runner image, or
provide noninteractive sudo for missing packages. For a fully prebuilt or disconnected
runner, select `TEMPLATE_RUNTIME_MODE=check` and provide compatible Python, Ansible,
module dependencies and collections. Keep wheel/collection artifacts available for recovery;
generated repositories include the bootstrap code and dependency declarations.

To prepare a runner or recovery host before platform access, run from `<prefix>-tier-0/`:

```bash
bash scripts/proxmox-templates.sh setup
```

This prepares all template tooling without accessing Terraform state or Proxmox.
It is optional; normal Ansible-based template commands perform the same preparation.

## Local repository files

Use the generated repository for the owning tier, or enter `tier-0/`,
`tier-1/`, or `tier-2/` in a private source checkout. Create ignored local
working files from that tier's examples before the
first deployment. Each tier has separate inventory, group vars, and Terraform
state while using the sibling shared automation.

Run `bash scripts/init-local-files.sh` from that tier directory, not the kit
root. Shared code is in `../shared/` in the source checkout and
`../<prefix>-shared/` in a generated collection.

These ignored files are expected to evolve as the environment matures. Keep
editing the same local files instead of recreating them for every run.
The deployment wrapper loads the shared platform profile and image catalog,
then `terraform/common.tfvars` before the selected setup `terraform.tfvars`.
Configure common storage, initial placement and network references once in the shared
profile. Keep tier-specific networks and network overrides per tier, and public-key
paths in ignored local environment inputs.
See [platform inputs](platform-inputs.md) for precedence and SSH access.
Use `scripts/init-local-files.sh --setup <name>` to create only
the local files for one deployment path plus the shared defaults.

When the repo examples change later, refresh local files carefully and review
any backups before deployment. The repository does not try to merge YAML, HCL,
and dotenv content automatically.

Keep live secrets out of Git.
Initializers and deployment entry points use `umask 077` for newly created local
inputs, backups and working files. This does not tighten existing file permissions
or replace a Windows ACL review; restrict access to existing secrets/state and test
encrypted off-host recovery separately.

## Read more

- [Environment variable conventions](environment-variables.md)
- [Offline bootstrap preparation and later approved-source handover](../deployment/foundation/proxmox/bootstrap-offline.md)
- [Repository scripts](repository-scripts.md)
- [Secret strategy](../administration/secret-handling/strategy.md)
- [Identity foundation path](../deployment/stage-5-identity/procedures/freeipa.md)
- [Windows and AD support](../architecture/identity/windows-integration.md)
- [Deployment readiness](../deployment/readiness.md)
- [Proxmox reference platform](../deployment/foundation/proxmox/README.md)

## References

Sources checked 2026-11-08.

1. [HashiCorp Terraform installation](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli).
2. [Ansible distribution packages and EPEL](https://docs.ansible.com/projects/ansible/latest/installation_guide/installation_distros.html).
3. [Installing Ansible and extra Python dependencies](https://docs.ansible.com/projects/ansible/latest/installation_guide/intro_installation.html).
4. [Proxmox collection's Ansible runtime requirement](https://raw.githubusercontent.com/ansible-collections/community.proxmox/2.1.0/meta/runtime.yml).
5. [Python virtual environments](https://docs.python.org/3/library/venv.html).
6. [Ansible control-node Python support](https://docs.ansible.com/projects/ansible-core/2.21/reference_appendices/release_and_maintenance.html#ansible-core-support-matrix).
7. [Enterprise Linux 10 Python](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/installing_and_using_dynamic_programming_languages/installing-and-using-python).
8. [Enterprise Linux 9 Python](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/installing_and_using_dynamic_programming_languages/assembly_installing-and-using-python_installing-and-using-dynamic-programming-languages).
9. [Collection runtime metadata and requires_ansible](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_collections_structure.html#meta-directory).
