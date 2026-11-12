# Control-node tooling

Detailed tool installation, compatibility, prechecks and execution inputs for
Linux/WSL deployment. For source edits, generator previews and offline checks,
start with [local development setup](../04-development/local-setup.md).

## Table of contents

- [Purpose](#purpose)
- [Platform prerequisites](#platform-prerequisites)
- [Deployment machine](#deployment-machine)
- [Collection sources](#collection-sources)
- [Dependency inventory](#dependency-inventory)
- [Automation VM example](#automation-vm-example)
- [Ansible environment](#ansible-environment)
- [Automatic template runtime](#automatic-template-runtime)
- [Galaxy through a policy proxy](#galaxy-through-a-policy-proxy)
- [Local repository files](#local-repository-files)
- [Read more](#read-more)
- [References](#references)

## Purpose

This reference covers Linux/WSL infrastructure execution. Repository generation
needs only the [declared Python/PyYAML prerequisites](../04-development/generated-repositories.md#purpose-and-prerequisites),
without platform access. Real deployment needs the inputs below. For the first installation, follow the
[bootstrap execution-host guide](../03-deployment/foundation/bootstrap/README.md):
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
[Proxmox API setup](../03-deployment/foundation/proxmox/api-access.md).
For the shared zone names and IaC mapping, read
[Network architecture](../01-architecture/05-networking/README.md).

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
machine. That precheck is setup-aware: it verifies the Ansible collections, controller Python
clients and native CLI tools needed by the selected setup. Direct localhost deployment plays import
the same tier-owned precheck before their roles run; Terraform is not required by those imports.
Default `auto` mode installs missing/incompatible collections from approved, commit-pinned
Git repositories. Compatible installed versions within the declared bounds are retained.
Set `CONTROL_NODE_COLLECTIONS_MODE=check` for a prepared disconnected controller:
missing/incompatible effective collections fail without dependency acquisition.
This does not disable guest package tasks.
For example, `foundation` includes directory and issuer requirements:
`community.general`, `ansible.posix`, `freeipa.ansible_freeipa`, `community.crypto`
and `ansible.mariadb`, while `cache` needs `community.general`,
`ansible.posix`, `ansible.utils` and controller Python's `netaddr`.

Python checks run in `ansible_playbook_python`, independently of collection presence.
The selected clients are checked for compatible versions and working imports before deployment.
The network filter also runs a real `ipaddr` check. [14][15][16][17]

Collection ranges include upper bounds to retain the release lines qualified with
OS-packaged `ansible-core` 2.16. A newer installed collection outside those ranges is
incompatible, even if Galaxy lists it successfully. Prepare the ranges in the owning
manifests; the effective first copy on Ansible's collection path must satisfy them.
The Proxmox collection separately requires core 2.17 or newer; template commands
prepare the accepted isolated runtime. [4][9]

### Collection sources

The Shared [source pins](../../shared/ansible/playbooks/vars/collection-sources.yml) map all declared
collections to approved repositories, full commit SHAs and release versions. The
[Git preparation tasks](../../shared/ansible/playbooks/tasks/control-node-git.yml) install the selected
missing/incompatible collections together with native `ansible-galaxy collection install --offline`.
When selected, FreeIPA is packaged automatically with its pinned upstream release builder before
joining that batch; the other collections install directly from Git. No manual packaging is required.
Here `--offline` suppresses Galaxy distribution-server requests; **remote Git still uses the network**
through the process's configured proxy. Git must already be installed and its source allowed. [12][23]

| Selection | Behavior |
| --- | --- |
| Default `control_node_collections_source: git` | Use pinned Git sources only when a required collection is missing or outside its bounds; no automatic Galaxy fallback |
| `control_node_collections_source: galaxy` | Use the previous OS-package-first path, then converge declared Galaxy ranges; approve API and artifact destinations |
| `CONTROL_NODE_COLLECTIONS_SOURCE=galaxy` | Select the same Galaxy path through the environment when no Ansible variable overrides it |
| `CONTROL_NODE_COLLECTIONS_MODE=check` or Ansible `--check` | Validate prepared dependencies without acquisition, regardless of source selection |

Set an optional source choice in the owning **tier's `ansible/group_vars/all.yml`**; the deployment
wrapper passes it to the precheck. Direct Ansible runs must load the same inputs. To use an accepted
private mirror, add `control_node_collection_git_overrides` there: a map keyed by `namespace.collection`,
with `repository`, `revision` and `version` for each override. Use credential-free `https://…git`
or an absolute `file:///…` Git repository, a full 40-character commit SHA and its exact compatible
release version. Branches, embedded credentials and automatic source fallback are rejected.
Keep private access credentials in the accepted Git credential mechanism, outside repository URLs.
Git pins identify reviewed source; Galaxy artifact-signature verification does not apply to Git installs. [12]

### Python and native tools

| Selected collection | Controller libraries | Native OS packages (RedHat / Debian families) |
| --- | --- | --- |
| `ansible.utils` | `netaddr` | `python3-netaddr` |
| `kubernetes.core` | `kubernetes`, `jsonpatch`, `PyYAML` | `python3-kubernetes`, `python3-jsonpatch`, `python3-pyyaml` / `python3-yaml` |
| `community.hashi_vault` | `hvac` | `python3-hvac` |
| `community.crypto` | `cryptography` | `python3-cryptography` |
| `amazon.aws` | `boto3`, `botocore` | `python3-boto3`, `python3-botocore` |

`auto` installs missing/incompatible clients with the native package manager for system Python on
RedHat/Debian families, or with `ansible.builtin.pip` inside Ansible's existing virtual environment.
It detects the interpreter's actual environment rather than trusting `$VIRTUAL_ENV`. No system pip
installation or new virtual environment is used. Native packages that cannot satisfy the declared
versions fail with the interpreter and requirements to prepare; select the accepted isolated runtime
in that case. Exact requirements live in
[shared Python checks](../../shared/ansible/playbooks/tasks/control-node-python.yml),
[network-filter checks](../../shared/ansible/playbooks/tasks/control-node-network-filters.yml)
and each tier's `ansible/requirements.txt`. [18]

Older `community.general` releases also need `pkg_resources` to inspect package versions.
If that probe is unavailable, `auto` adds native `python3-setuptools`, or `setuptools<82` inside
the existing venv. Dependency `check` mode instead reports the missing metadata support. [19]

`CONTROL_NODE_COLLECTIONS_MODE=check` rejects missing/incompatible collections or Python clients
without acquisition. Ansible `--check` also validates prepared dependencies without installing them.
For disconnected execution, install matching OS packages or prepared local wheels and collections
first, then select dependency `check` mode. Acquisition inherits the process's existing proxy and
pip source settings, including `PIP_NO_INDEX` and `PIP_FIND_LINKS`; these do not constrain Git or Galaxy.
Missing network-filter dependencies fail at the preparation check rather than continuing into
tasks whose installation results would be unavailable in Ansible check mode. [20]

Native tool checks run only the selected commands: Helm for chart-based cluster/platform plays,
and Talos client versions for the control-applications Kubernetes SSO workflow, plus kubectl on apply.
The lab-environment manifest play does not require Helm. Missing tools fail before deployment
changes; the precheck never fetches standalone binaries. Use the bootstrap guide's approved
artifact/package inputs to prepare them. Tier-owned `control_node_setup_tool_commands` declares
the commands; SSO checks honor `control_applications_sso_talosctl` and
`control_applications_sso_kubectl` when passed with the deployment inputs.

Run the tier's `ansible/playbooks/control-node.yml`, which imports shared checks
with tier-owned requirements. Follow the
[offline bootstrap workflow](../03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md)
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
playbooks. It passes the same ordered variable files as the deployment: `all.yml`, setup
inputs, optional environment inputs, then each `--ansible-vars` override. The precheck
still targets only `localhost`; `--inventory` selects the managed-host inventory used
by Terraform and the service recipe. `--env-file` is loaded before the precheck, including
its proxy/source settings and dependency-check mode. Follow the root README or the
setup-specific guide for the actual run commands.

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
| OS commands | [Bootstrap Step 2a](../03-deployment/foundation/bootstrap/README.md#2a-install-through-approved-sources): Git, Bash, Python/pip, SSH, CA/curl/OpenSSL, archive/storage utilities, Terraform and `qemu-img`; [offline OS download/install](../03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md#1a-download-os-packages-and-reviewed-source) |
| Optional home-directory migration | Pre-stage `rsync` and, on Enterprise Linux 10, `policycoreutils-python-utils` before restricting package access; included in the offline RPM download list for the [home-directory guide](../03-deployment/foundation/bootstrap/step-3c-bootstrap-home.md) |
| Separate bootstrap workspace filesystem | Prepare `parted` and `xfsprogs` before creating the new data mount; follow [workspace disk preparation](../03-deployment/foundation/bootstrap/step-3a-bootstrap-storage.md) before copying artifacts or installing the full runtime |
| Optional root-LVM expansion | EL10: pre-stage `lvm2`, `parted` and `xfsprogs`, included in the offline RPM list; the [existing-disk or new-PV guide](../03-deployment/foundation/bootstrap/step-3b-bootstrap-lvm.md) also lists Debian/Ubuntu package names |
| Python execution runtime | Tier 0 [runtime requirements](../../tier-0/ansible/runtime-requirements.txt); accepted interpreter plus Ansible/PyYAML/HCL tooling |
| Python module clients | Owning tier's requirements: [Tier 0](../../tier-0/ansible/requirements.txt), [Tier 1](../../tier-1/ansible/requirements.txt), [Tier 2](../../tier-2/ansible/requirements.txt); install in the accepted venv |
| Ansible collections | Bounds: [Shared](../../shared/ansible/requirements.yml), [Tier 0](../../tier-0/ansible/requirements.yml), [Tier 1](../../tier-1/ansible/requirements.yml), [Tier 2](../../tier-2/ansible/requirements.yml); automatic [Git source pins](../../shared/ansible/playbooks/vars/collection-sources.yml). Offline bundles include transitive archives |
| Generator only | Upstream kit `scripts/tier-repos/requirements.txt`; [generation prerequisite contract](../04-development/generated-repositories.md#purpose-and-prerequisites) |
| Terraform providers | Each selected tier-local `terraform/deployments/<setup>/.terraform.lock.hcl`; [mirror selected roots without upgrading](../03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md#1c-mirror-locked-providers-and-stage-guest-artifacts) |
| Guest/service and Kubernetes software | Selected stage's roles, group vars, chart/product inputs and image sources; **outside** the controller dependency bundle, even when controller Python clients are included |

## Automation VM example

After the first template exists, a small dedicated automation VM is often
easier to keep stable than using a personal workstation.
Create it with the [bootstrap deployment guide](../03-deployment/foundation/bootstrap/README.md),
then follow its [package and Terraform installation steps](../03-deployment/foundation/bootstrap/README.md#2a-install-through-approved-sources).
An accepted independent workstation is
also valid. Proxmox hosts and Talos nodes are not general-purpose deployment machines.

The AlmaLinux/Rocky Linux first-run path installs OS tools, adds HashiCorp's RPM
repository and verifies Terraform before cloning/generation. It then prepares
Ansible from the checked-out manifests. EPEL is not required by that path;
additional repositories remain an explicit software-intake choice. [1][2]
Use versions satisfying the selected Terraform roots and Ansible collections;
an installed executable alone is not compatibility evidence. For an offline host,
use the [connected-host bundle preparation and SCP handoff](../03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md).
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

The [explicit Ansible installation step](../03-deployment/foundation/bootstrap/README.md#4-install-ansible)
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
the [offline workflow](../03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md#3b-restore-the-kit-and-install-the-isolated-pythonansible-environment).

### Automatic template runtime

Run the usual `scripts/proxmox-templates.sh apply`, `verify` or `replace-disk`
command from **Tier 0**. It selects Python 3.12–3.14 and prepares
`.venv/proxmox-templates-py<version>/`, using `ansible/runtime-requirements.txt`.
It then runs `ansible/playbooks/prepare-template-runtime.yml` to install the tier's
Python module requirements and the declared Proxmox collection. Disk maintenance
also installs `qemu-img` when missing. Collection downloads stay under `.venv/collections/`.
Later runs reuse compatible packages without forcing upgrades.

The template runtime also defaults to pinned Git collection acquisition and honors
`CONTROL_NODE_COLLECTIONS_SOURCE=galaxy` for explicit Galaxy acquisition. Its standalone
[Proxmox pin](../../tier-0/ansible/playbooks/vars/template-collection-source.yml) lives in Tier 0's
`ansible/playbooks/vars/template-collection-source.yml` so template bootstrap does not depend on
Shared. See [collection source behavior](#collection-sources).

| Setting or condition | Behavior |
| --- | --- |
| Default | Prepare and select the isolated runtime automatically; no `source` step |
| Python missing or too old | Install bootstrap packages from configured DNF/APT repositories |
| Missing OS packages | Use root/sudo; prompt for sudo locally when needed, never prompt in CI |
| `TEMPLATE_PYTHON=/path/to/python` | Select an already installed Python 3.12–3.14 explicitly |
| `TEMPLATE_RUNTIME_MODE=check` | Use preinstalled tools and existing checks; perform no dependency installation |
| Offline package sources | Install local wheels/collection tarballs first, then select `check`; pip source restrictions alone do not prevent Git/Galaxy access |

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

The protected template CI example retains both the reviewed `.tfplan` and its `.context`
file for the publish job. Its target state, inputs and absolute workspace paths must
match the planning job; a changed context requires a new plan. Neither file replaces
independent state and artifact recovery copies. [21]

To prepare a runner or recovery host before platform access, run from `<prefix>-tier-0/`:

```bash
bash scripts/proxmox-templates.sh setup
```

This prepares all template tooling without accessing Terraform state or Proxmox.
It is optional; normal Ansible-based template commands perform the same preparation.

## Galaxy through a policy proxy

The default Git path avoids Galaxy API and artifact redirects; allow the selected Git repositories
through the proxy. Git and explicit Galaxy acquisition use the deployment process's `http_proxy`,
`https_proxy` and `no_proxy` environment. APT/DNF proxy settings alone do not configure these tools.
The following applies when **Galaxy is explicitly selected**, or when preparing Galaxy archives. The
[cache example](../../tier-2/ansible/group_vars/cache.yml.example) permits `galaxy.ansible.com` for metadata.
Public artifact downloads can redirect to CDN/object-storage hosts outside `ansible.com`;
those destinations can change and are not a stable global hostname contract.
Select either reviewed artifact destinations in `cache_squid_allowed_domains`, or prepared archives
from an accepted acquisition host/internal distribution through the
[offline controller workflow](../03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md).
Do not substitute an unrestricted cloud-provider wildcard for that source choice.

The Galaxy path uses native `ansible-galaxy --no-cache` to avoid reusing incomplete local API-response
metadata. This preserves installed collections and the Squid cache; it does not bypass the proxy or
TLS verification. The default Git path retains compatible installed versions without downloading. [10]

| Failure | Meaning / action |
| --- | --- |
| `Tunnel connection failed: 403 Forbidden` | The proxy denies CONNECT; check its source/client policy and the exact denied destination |
| `Unexpected Exception ... 'results'` | A known Galaxy client failure can mask an earlier request error; retry with `--clear-response-cache` to expose the underlying failure [11] |
| Connection timeout or TLS verification failure | Check the approved proxy route, DNS and CA trust before retrying |

### Repair a blocked cryptographic collection download

For **older kit versions** without automatic Git acquisition, retain this one-time repair.
Current deployment prechecks perform the selected pinned Git installation automatically.

If syslog preparation resolves `community.crypto` but its artifact download receives a proxy 403,
install the same official release through the separately approved GitHub route. This is an explicit
source choice, not an automatic proxy bypass or fallback. The 2.26.9 tag satisfies the declared
`>=2.26.0,<3.0.0` range. [12][22]

On **`boot-1`**, as the same deployment user and in the same Ansible runtime:

```bash
source /etc/profile.d/shell-proxy.sh
ansible-galaxy collection install 'git+https://github.com/ansible-collections/community.crypto.git,2.26.9'
```

**Expected:** `community.crypto:2.26.9` installs successfully. Rerun the interrupted syslog command;
the precheck accepts an effective compatible installed version without another artifact download.
For disconnected or CI execution, prepare collection archives through the
[offline controller workflow](../03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md).
Normal public Galaxy acquisition still needs its actual approved artifact destinations.

### Recover an existing cache that blocks Galaxy

This repair is for older kit versions or an explicitly selected Galaxy path. For the current
default, allow the [pinned Git sources](#collection-sources) and rerun the original deployment.

1. On **`boot-1`**, as the deployment user, load the proxy and install the official release tag
   through the existing approved GitHub path. This resolves the `ansible.utils` dependency needed
   to update an older cache policy; it is a one-time repair, not an automatic source fallback. [12]

   ```bash
   source /etc/profile.d/shell-proxy.sh
   ansible-galaxy collection install 'git+https://github.com/ansible-collections/ansible.utils.git,v6.0.0'
   ```

   For OS-packaged Ansible, install its controller library if it was not prepared earlier.
   On **EL10 boot-1**:

   ```bash
   sudo dnf install -y python3-netaddr
   ```

   Debian/Ubuntu uses `sudo apt-get install -y python3-netaddr`. An active venv instead uses
   its tier-owned Python requirements; an OS package is not installed inside that venv.

2. Edit **`<prefix>-tier-2/ansible/group_vars/cache.yml`**. Keep `galaxy.ansible.com` in
   `cache_squid_allowed_domains` when selecting public Galaxy. Approve the actual artifact redirect
   hosts for that route, or retain prepared archives instead. A regional hostname observed for one
   download is not a universal default. Preserve other required sources.

3. From **`<prefix>-tier-2/`**, reconcile the existing cache pair:

   ```bash
   bash scripts/deploy.sh cache --ansible-only
   ```

4. On **`boot-1`**, as the same user, verify API access and the actual artifact download.
   Merely listing the now-installed collection would not test either route:

   ```bash
   mkdir -p "$HOME/.cache/homelab/collections"
   ansible-galaxy collection download --no-cache --download-path "$HOME/.cache/homelab/collections" \
     'ansible.utils:>=6.0.0,<7.0.0'
   ```

   **Expected:** the collection archive and local requirements file are saved successfully.
   Retain them with the [offline controller bundle](../03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md).
   Return to the interrupted deployment. If GitHub is also denied, transfer prepared collection
   archives through that offline workflow instead of widening general internet access.

## Local repository files

Ad-hoc `ansible` commands from a tier root need `--playbook-dir ansible` to discover
`ansible/group_vars/`. The deployment wrapper passes its selected variable files explicitly.
Environment overrides still need their matching extra-variable files. [13]

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
- [Offline bootstrap preparation and later approved-source handover](../03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md)
- [Repository scripts](repository-scripts.md)
- [Secret strategy](../05-operations/03-cryptography/secret-handling.md)
- [Identity foundation path](../03-deployment/stage-5-identity/procedures/freeipa.md)
- [Windows and AD support](../01-architecture/09-identity/01-windows-integration.md)
- [Deployment readiness](../03-deployment/readiness.md)
- [Proxmox reference platform](../03-deployment/foundation/proxmox/README.md)

## References

Sources checked 2026-11-08.

Controller Python module, pip, metadata and execution references [15]–[21] checked 2026-11-11.
Git collection acquisition, offline behavior and release metadata [12][22][23] checked 2026-11-12.

1. [HashiCorp Terraform installation](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli).
2. [Ansible distribution packages and EPEL](https://docs.ansible.com/projects/ansible/latest/installation_guide/installation_distros.html).
3. [Installing Ansible and extra Python dependencies](https://docs.ansible.com/projects/ansible/latest/installation_guide/intro_installation.html).
4. [Proxmox collection's Ansible runtime requirement](https://raw.githubusercontent.com/ansible-collections/community.proxmox/2.1.0/meta/runtime.yml).
5. [Python virtual environments](https://docs.python.org/3/library/venv.html).
6. [Ansible control-node Python support](https://docs.ansible.com/projects/ansible-core/2.21/reference_appendices/release_and_maintenance.html#ansible-core-support-matrix).
7. [Enterprise Linux 10 Python](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/installing_and_using_dynamic_programming_languages/installing-and-using-python).
8. [Enterprise Linux 9 Python](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/installing_and_using_dynamic_programming_languages/assembly_installing-and-using-python_installing-and-using-dynamic-programming-languages).
9. [Collection runtime metadata and requires_ansible](https://docs.ansible.com/projects/ansible/latest/dev_guide/developing_collections_structure.html#meta-directory).
10. [Native Galaxy acquisition and cache flags](https://docs.ansible.com/projects/ansible/latest/cli/ansible-galaxy.html#collection-install).
11. [Upstream Galaxy cached-response failure](https://github.com/ansible/ansible/issues/85918).
12. [Native Git collection installation](https://docs.ansible.com/projects/ansible/latest/collections_guide/collections_installing.html#installing-a-collection-from-a-git-repository)
    and [the official 6.0.0 release metadata](https://github.com/ansible-collections/ansible.utils/blob/v6.0.0/galaxy.yml).
13. [Ad-hoc Ansible playbook directory and variable discovery](https://docs.ansible.com/projects/ansible/latest/cli/ansible.html#cmdoption-ansible-playbook-dir).
14. [Controller-side IP filter requirements](https://docs.ansible.com/projects/ansible/latest/collections/ansible/utils/ipaddr_filter.html#requirements).
15. [Native Kubernetes module requirements](https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/k8s_module.html#requirements).
16. [Native Vault module requirements](https://docs.ansible.com/projects/ansible/latest/collections/community/hashi_vault/vault_read_module.html#requirements).
17. [Native certificate module requirements](https://docs.ansible.com/projects/ansible/latest/collections/community/crypto/x509_certificate_module.html#requirements).
18. [Ansible pip and existing virtual environments](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/pip_module.html).
19. [Setuptools removal of pkg_resources](https://setuptools.pypa.io/en/latest/history.html#v82-0-0).
20. [Ansible check-mode behavior and registered results](https://docs.ansible.com/projects/ansible-core/2.16/playbook_guide/playbooks_checkmode.html).
21. [GitLab job artifacts and cross-job handoff](https://docs.gitlab.com/ci/jobs/job_artifacts/).
22. [Official community.crypto 2.26.9 release metadata](https://github.com/ansible-collections/community.crypto/blob/2.26.9/galaxy.yml).
23. [Ansible 2.16 collection installation: scope of --offline](https://docs.ansible.com/projects/ansible-core/2.16/cli/ansible-galaxy.html#collection-install).
