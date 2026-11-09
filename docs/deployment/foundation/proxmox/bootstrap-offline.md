# Offline bootstrap preparation

Prepare dependencies on a connected, approved acquisition host, transfer one
reviewed bundle, then install on `boot-1` without public package access.
This supplies controller tooling and providers for templates and initial Linux
deployments; it does **not** make every platform stage disconnected-ready.

For a **new installation**, generate a fresh collection after [retiring old resources](../../../administration/provisioning.md)
where applicable. For recovery, [restore the bootstrap and original inputs/state](../../../administration/recovery/bootstrap.md)
instead of replacing them with generated examples.

**Working repositories:** reviewed upstream kit for acquisition; `<prefix>-tier-0`
and `<prefix>-tier-2` after generation, with sibling Shared automation.
**Branch from:** [Bootstrap Step 2b](bootstrap.md#2b-transfer-a-prepared-bundle--offline-alternative).
**Prerequisites:** [Bootstrap Step 2](bootstrap.md#step-2-prepare-tools-repositories-and-artifacts)
has prepared the selected workspace filesystem and private `automation`-owned directories
under `/srv/tier0`, including `offline/`; SSH/console and approved package-signing keys are available.
An existing mount such as `/srv/src` is valid: substitute absolute paths consistently.
For [workspace disk preparation](bootstrap-storage.md) or [root-LVM expansion](bootstrap-lvm.md), storage tools may be installed first from a verified
bundle on independently mounted media. In Step 7, set `BUNDLE` to that media path, then return
to storage preparation before transferring the full bundle to the completed workspace.
The connected host must match the target's **distribution, release, architecture
and Python minor version**. The main example uses Enterprise Linux 10 / Python 3.12.
Start from a clean matching VM with the same approved repositories and signing keys.

## Contents

- [1. Prepare the acquisition host](#1-prepare-the-acquisition-host)
- [2. Capture source and OS packages](#2-capture-source-and-os-packages)
- [3. Download wheels and collections](#3-download-wheels-and-collections)
- [4. Mirror providers and stage images](#4-mirror-providers-and-stage-images)
- [5. Pack and transfer the bundle](#5-pack-and-transfer-the-bundle)
- [6. Verify the transferred bundle](#6-verify-the-transferred-bundle)
- [7. Install signed OS packages](#7-install-signed-os-packages)
- [8. Restore the kit and install Ansible](#8-restore-the-kit-and-install-ansible)
- [9. Select local sources and verify](#9-select-local-sources-and-verify)
- [Use approved sources after bootstrap](#use-approved-sources-after-bootstrap)
- [Scope and acceptance limits](#scope-and-acceptance-limits)
- [References](#references)

<a id="1-prepare-on-the-connected-host"></a>

## 1. Prepare the acquisition host

Install acquisition tools separately from the Python environment:

Run on **the connected matching acquisition host**.

```bash
sudo dnf install -y dnf-plugins-core python3 python3-pip git gnupg2
```

Then use [Bootstrap 2a, action 2](bootstrap.md#2a-install-through-approved-sources)
to configure the approved Terraform package repository and install Terraform **on the connected host**.

<a id="1a-download-os-packages-and-reviewed-source"></a>

## 2. Capture source and OS packages

Run in Bash. Enter the absolute path to the reviewed upstream kit checkout;
require a clean committed revision. Use a new bundle directory for each release.

Run on **the connected matching acquisition host**.

```bash
set -euo pipefail
read -r -p "Reviewed kit checkout (absolute path): " KIT
test -z "$(git -C "$KIT" status --porcelain)"
BUNDLE="$HOME/homelab-bootstrap"
mkdir "$BUNDLE"
mkdir -p "$BUNDLE"/{rpms,keys,wheels,collections,providers,artifacts}
git -C "$KIT" rev-parse HEAD > "$BUNDLE/kit-revision.txt"
git -C "$KIT" bundle create "$BUNDLE/homelab.bundle" --all
cat /etc/os-release > "$BUNDLE/acquisition-os.txt"
uname -m > "$BUNDLE/acquisition-architecture.txt"
python3 --version > "$BUNDLE/acquisition-python.txt"
dnf repolist --enabled > "$BUNDLE/acquisition-repositories.txt"
dnf download --resolve --alldeps --destdir "$BUNDLE/rpms" \
  git bash python3 python3-pip python3-pyyaml openssh-clients ca-certificates \
  curl openssl gnupg2 xz unzip tar qemu-img terraform dnf-plugins-core rsync policycoreutils-python-utils \
  lvm2 parted xfsprogs
curl --fail --location https://rpm.releases.hashicorp.com/gpg \
  --output "$BUNDLE/keys/hashicorp.asc"
gpg --show-keys --with-fingerprint "$BUNDLE/keys/hashicorp.asc"
```

**Stop** if package resolution fails, the release/CPU/Python differs, or signing-key
fingerprints cannot be approved through the vendor's published signing-key reference. Retain
the reviewed key fingerprint with the acquisition record. `--alldeps` includes
dependencies already installed on the acquisition host. It is not a whole OS mirror. [1][2]

The bundle also includes `rsync` and Enterprise Linux 10's
`policycoreutils-python-utils` for the optional
[home-directory migration](bootstrap-home.md). Prepare these before restricting
package access; installing the tools does not move `/home` or change SELinux policy.
The LVM/partition/XFS tools support the optional root-capacity expansion; downloading
or installing them does not resize or partition any disk.

<a id="1b-download-python-wheels-and-collection-dependencies"></a>

## 3. Download wheels and collections

Keep this acquisition venv outside the bundle; virtual environments are rebuilt
on the target, not copied. Download binary wheels and all transitive collection
dependencies from the repository manifests. [3][4]

Run on **the connected matching acquisition host**.

```bash
python3 -m venv "$HOME/.local/share/homelab/acquisition-venv"
source "$HOME/.local/share/homelab/acquisition-venv/bin/activate"
python3 -m pip install -r "$KIT/tier-0/ansible/runtime-requirements.txt"
python3 -m pip download --only-binary=:all: --dest "$BUNDLE/wheels" \
  -r "$KIT/tier-0/ansible/runtime-requirements.txt" \
  -r "$KIT/tier-0/ansible/requirements.txt" \
  -r "$KIT/tier-1/ansible/requirements.txt" \
  -r "$KIT/tier-2/ansible/requirements.txt" \
  -r "$KIT/scripts/tier-repos/requirements.txt"
python3 - "$KIT" "$BUNDLE/collections-input.yml" <<'PY'
import pathlib, sys, yaml
kit = pathlib.Path(sys.argv[1])
collections = {}
for owner in ('shared', 'tier-0', 'tier-1', 'tier-2'):
    manifest = yaml.safe_load((kit / owner / 'ansible/requirements.yml').read_text())
    for entry in manifest['collections']:
        previous = collections.setdefault(entry['name'], entry)
        assert previous == entry, f"Conflicting declarations: {entry['name']}"
pathlib.Path(sys.argv[2]).write_text(yaml.safe_dump({'collections': list(collections.values())}))
PY
ansible-galaxy collection download -r "$BUNDLE/collections-input.yml" \
  --download-path "$BUNDLE/collections"
```

Keep the **generated** `collections/requirements.yml` beside its tarballs. That
file selects local archives; the source manifests select Galaxy names. Do not use
`--no-deps`. If a wheel is unavailable, stop and prepare an approved wheel on the
matching build platform; do not silently fall back to an offline source build.

<a id="1c-mirror-locked-providers-and-stage-guest-artifacts"></a>

## 4. Mirror providers and stage images

Use Terraform installed on the acquisition host in Step 1.
Mirror each intended root using its committed lockfile. The example covers the
template publisher, logging, trust VMs and the Tier 2 cache. Add other roots to
this array **before** transfer if required. No plan/apply or platform credentials
are needed. The local module sources remain in the transferred repositories. [5][6]

Run on **the connected matching acquisition host**.

```bash
TF_PLATFORM="$(terraform version -json | python3 -c 'import json,sys; print(json.load(sys.stdin)["platform"])')"
terraform version -json > "$BUNDLE/acquisition-terraform.json"
roots=(tier-0/terraform/deployments/{templates,syslog,foundation} tier-2/terraform/deployments/cache)
for root in "${roots[@]}"; do
  test -f "$KIT/$root/.terraform.lock.hcl"
  terraform -chdir="$KIT/$root" init -backend=false -input=false -lockfile=readonly
  terraform -chdir="$KIT/$root" providers mirror -platform="$TF_PLATFORM" "$BUNDLE/providers"
done
read -r -p "Approved unpacked image directory (absolute path): " IMAGE_DIR
cp -a "$IMAGE_DIR/." "$BUNDLE/artifacts/"
```

Stage the exact approved `.qcow2`/unpacked `.raw` images and their vendor
checksums/provenance required by the [template guide](templates.md). Include an
LXC template only when selected. Preserve the lockfiles; stop if `init` requests a
lock update and review/reissue the source revision rather than upgrading offline.
No API tokens, SSH private keys, existing state or ignored project inputs belong
in this **new-install** bundle. Recovery of an existing site also needs its separate
encrypted inputs/state backup.

<a id="2-transfer-and-verify"></a>

## 5. Pack and transfer the bundle

On the connected host, create checksums, pack the reviewed bundle and record the
archive checksum independently. Set `BOOTSTRAP` to the verified SSH destination.
SSH host-key verification must remain enabled.

Run on **the connected matching acquisition host**.

```bash
(cd "$BUNDLE" && find . -type f ! -path './SHA256SUMS' -print0 |
  sort -z | xargs -0 sha256sum > SHA256SUMS)
tar --sparse -C "$(dirname "$BUNDLE")" -cf "$HOME/homelab-bootstrap.tar" "$(basename "$BUNDLE")"
sha256sum "$HOME/homelab-bootstrap.tar"
read -r -p "Bootstrap SSH destination (automation@address): " BOOTSTRAP
ssh "$BOOTSTRAP" 'umask 077; mkdir -p /srv/tier0/offline'
scp "$HOME/homelab-bootstrap.tar" "$BOOTSTRAP:/srv/tier0/offline/"
```

<a id="2a-check-the-transferred-archive"></a>

## 6. Verify the transferred bundle

### 1. Check the archive

On **`boot-1`**, print the digest and inspect the archive listing:

Run on **`boot-1`** as automation.

```bash
set -euo pipefail
cd /srv/tier0/offline
sha256sum homelab-bootstrap.tar
tar -tf homelab-bootstrap.tar | sed -n '1,10p'
```

Compare the digest with the independent acquisition record **before unpacking**; stop on any mismatch.
A digest transferred with the archive detects corruption but does not independently authenticate its source.

<a id="2b-extract-and-verify-the-contents"></a>

### 2. Extract and verify the contents

On **`boot-1`**, in `/srv/tier0/offline` after the archive check passes:

```bash
test ! -e homelab-bootstrap
tar -xf homelab-bootstrap.tar
cd homelab-bootstrap
sha256sum --check SHA256SUMS
```

**Expected:** all checksums pass. Stop before installing if any file is missing or mismatched.

<a id="2c-match-the-target-platform"></a>

### 3. Match the target platform

On **`boot-1`**, in the extracted bundle directory:

```bash
cat acquisition-os.txt acquisition-architecture.txt acquisition-python.txt
cat /etc/os-release
uname -m
python3 --version
```

The initial VM must already provide SSH, tar, sha256sum and the matching base OS.
Compare recorded and local platform values before installing. Keep an independent
copy of the accepted archive outside this VM and its attached storage.

<a id="3-install-on-the-bootstrap-vm"></a>
<a id="3a-install-signed-os-packages"></a>

## 7. Install signed OS packages

Run as `automation` on `boot-1`. Import only the previously approved vendor
key; the base OS must already trust its distribution's keys. Require successful
RPM signature verification and retain signature checking during the local install.
Local-package signature checking is explicitly enabled. [9]
For the early storage-tools branch, keep `BUNDLE` set to the verified bundle on mounted media;
otherwise the default below selects the transferred workspace copy.

Run on **`boot-1`** as automation.

```bash
BUNDLE="${BUNDLE:-/srv/tier0/offline/homelab-bootstrap}"
sudo rpm --import "$BUNDLE/keys/hashicorp.asc"
rpmkeys --checksig "$BUNDLE"/rpms/*.rpm
sudo dnf --disablerepo='*' --setopt=localpkg_gpgcheck=1 install "$BUNDLE"/rpms/*.rpm
git --version
terraform version
qemu-img --version
```

Stop for `NOKEY`, bad signatures or unresolved dependencies. Rebuild the bundle on
the matching acquisition VM; never use `--nogpgcheck`, `--nodeps` or enable public
repositories to bypass an incomplete offline install.

<a id="3b-restore-the-kit-and-install-the-isolated-pythonansible-environment"></a>

## 8. Restore the kit and install Ansible

For a **new** installation only, follow **1–5** in the same Bash session.
During recovery, use the [bootstrap restore path](../../../administration/recovery/bootstrap.md)
to retain existing inputs and original state.

### 1. Restore the kit checkout

Run on **`boot-1`** as the bootstrap account:

```bash
BUNDLE=/srv/tier0/offline/homelab-bootstrap
mkdir -p /srv/tier0/src
git clone "$BUNDLE/homelab.bundle" /srv/tier0/src/homelab
test "$(git -C /srv/tier0/src/homelab rev-parse HEAD)" = "$(cat "$BUNDLE/kit-revision.txt")"
KIT=/srv/tier0/src/homelab
```

**Expected:** the restored Git revision matches `kit-revision.txt`.

### 2. Create the Python environment and install local wheels

On **`boot-1`**, in the same shell:

```bash
python3 -m venv "$HOME/.local/share/homelab/venv"
source "$HOME/.local/share/homelab/venv/bin/activate"
export PIP_NO_INDEX=1 PIP_FIND_LINKS="$BUNDLE/wheels"
python3 -m pip install -r "$KIT/tier-0/ansible/runtime-requirements.txt" \
  -r "$KIT/tier-0/ansible/requirements.txt" \
  -r "$KIT/tier-1/ansible/requirements.txt" -r "$KIT/tier-2/ansible/requirements.txt"
python3 -m pip check
```

**Expected:** local wheels satisfy all requirements; `pip check` reports no broken dependencies.

### 3. Install the downloaded Ansible collections

On **`boot-1`**, with that Python environment active:

```bash
export ANSIBLE_COLLECTIONS_PATH="$HOME/.local/share/homelab/collections"
(cd "$BUNDLE/collections" && ansible-galaxy collection install --offline \
  -r requirements.yml --collections-path "$ANSIBLE_COLLECTIONS_PATH")
```

### 4. Restore the approved images

On **`boot-1`**, copy the bundle's verified images into the prepared artifact directory:

```bash
mkdir -p /srv/tier0/artifacts
cp -a "$BUNDLE/artifacts/." /srv/tier0/artifacts/
```

### 5. Generate the repositories

Generate from the restored upstream kit checkout, keeping the same prepared shell:

Run from the reviewed upstream kit checkout on **`boot-1`** (`/srv/tier0/src/homelab`).

```bash
bash scripts/init-tier-repos.sh
```

Use the [generation options](../../../development/generated-repositories.md) for a custom prefix.
Do not clone over an existing site or regenerate
state during recovery. A transferred Git bundle is a local acquisition source,
not the eventual hosted remote.

<a id="3c-select-local-only-dependency-sources-and-verify"></a>

## 9. Select local sources and verify

Create a private shell setup file outside Git. Terraform's explicit filesystem
mirror has **no `direct` fallback**; a provider cache alone is insufficient. [6]

Run on **`boot-1`** as automation.

```bash
mkdir -p "$HOME/.config/homelab"
cat > "$HOME/.config/homelab/offline.tfrc" <<EOF
disable_checkpoint = true
provider_installation {
  filesystem_mirror { path = "$BUNDLE/providers" }
}
EOF
cat > "$HOME/.config/homelab/offline.env" <<EOF
source "$HOME/.local/share/homelab/venv/bin/activate"
export PIP_NO_INDEX=1
export PIP_FIND_LINKS="$BUNDLE/wheels"
export ANSIBLE_COLLECTIONS_PATH="$HOME/.local/share/homelab/collections"
export TF_CLI_CONFIG_FILE="$HOME/.config/homelab/offline.tfrc"
export TEMPLATE_RUNTIME_MODE=check
export CONTROL_NODE_COLLECTIONS_MODE=check
EOF
chmod 600 "$HOME/.config/homelab/"offline.*
source "$HOME/.config/homelab/offline.env"
```

Check Tier 0's template tooling and locked provider initialization:

Run from **`<prefix>-tier-0/`** on **`boot-1`**.

```bash
source "$HOME/.config/homelab/offline.env"
bash scripts/proxmox-templates.sh setup
terraform -chdir=terraform/deployments/templates init -backend=false -input=false -lockfile=readonly
```

Check the initial Linux cache's collection prerequisites separately:

Run from **`<prefix>-tier-2/`** on **`boot-1`**.

```bash
source "$HOME/.config/homelab/offline.env"
ansible-playbook -i localhost, ansible/playbooks/control-node.yml \
  -e control_node_setup=cache -e control_node_require_terraform=true
```

Repeat the last precheck with the owning tier/setup before other Linux deployments;
it verifies installed collection bounds, not API access or guest package sources.
Source `offline.env` in each new deployment shell. These variables belong to the
execution environment, not the scripts' allowlisted Proxmox `.env.local` file.
Both `check` modes refuse dependency acquisition; template runtime `auto` may
invoke Galaxy and must not be used for this disconnected path.

**Rejoin:** [Bootstrap Step 3](bootstrap.md#step-3-prepare-the-execution-accounts-ssh-key),
then configure verified Proxmox CA/API access, local inputs and approved images.
Retain the selected stage's review/approval gates; this guide does not deploy guests.

## Use approved sources after bootstrap

After [Stage 1 software intake](../../stage-1-software-intake/README.md#step-6-connect-the-bootstrap-host),
configure this manually created bootstrap VM too. It is not automatically enrolled
in the Shared baseline. Keep the disconnected recovery bundle independently.

| Native client | Accepted source configuration |
| --- | --- |
| DNF | Approved `baseurl`/repository definitions in `/etc/yum.repos.d/*.repo`, or `proxy=` in `/etc/dnf/dnf.conf`; retain GPG/TLS validation |
| Pip | `index-url` in `$HOME/.config/pip/pip.conf` for a complete approved index; keep `PIP_NO_INDEX`/`PIP_FIND_LINKS` for local wheels until tested |
| Galaxy | In the owning tier's selected `ansible/ansible.cfg`, configure an accepted `[galaxy] server_list` / `[galaxy_server.<name>]`; local downloaded requirements remain valid offline |
| Terraform | Keep the filesystem mirror or select an approved `network_mirror` in the private `*.tfrc`; retain root lockfiles and omit `direct` for restricted execution |

Test DNS, trust, permitted artifact retrieval and a selected setup precheck before
changing `CONTROL_NODE_COLLECTIONS_MODE` back to `auto` or removing the pip offline
variables. [7][8] An HTTP cache/proxy supplies policy-controlled retrieval, not a
complete offline repository; a cache miss still needs an approved upstream.

## Scope and acceptance limits

| Prepared here | Still required from a selected stage or approved existing service |
| --- | --- |
| Controller RPMs, Python wheels, collection archives/dependencies | Guest OS package repositories and setup-specific system packages |
| Reviewed source bundle and listed roots' locked provider packages | Any additional roots/providers, remote modules or backend connectivity |
| Explicitly staged VM/LXC artifacts | Kubernetes/Talos tools, charts/CRDs, OCI images, Flux/Git sources and application artifacts |
| Tool/template setup and control-node precheck commands | CA/API trust, secrets, actual installation, fault/restore and disconnected acceptance evidence |

Run these checks with public egress denied before accepting a bundle. A successful
controller check is not proof that a guest can install a package or that all ten
stages work offline. Native validation covers wheel and local collection installation,
collection-version prechecks and locked provider initialization. A matching Enterprise
Linux RPM installation, SCP to the target and real disconnected deployment still need
operator qualification. Debian/Ubuntu package acquisition is a separate integration:
prepare matching APT repository metadata, packages and signing keys; do not install
these RPMs there. The Python/Galaxy/provider handoff still requires matching targets.

## References

Sources checked 2026-11-08.

1. [DNF download: resolution and already-installed dependencies](https://dnf-plugins-core.readthedocs.io/en/latest/download.html).
2. [Terraform's official package repository installation](https://developer.hashicorp.com/terraform/install) and
   [HashiCorp's current Linux package-signing key](https://www.hashicorp.com/en/trust/security).
3. [Pip download and binary-wheel target requirements](https://pip.pypa.io/en/stable/cli/pip_download/).
4. [Galaxy collection/dependency download and generated local requirements](https://docs.ansible.com/projects/ansible-core/2.21/collections_guide/collections_downloading.html).
5. [Terraform provider mirror and lockfile selection](https://developer.hashicorp.com/terraform/cli/commands/providers/mirror).
6. [Terraform explicit provider installation and CLI configuration](https://developer.hashicorp.com/terraform/cli/config/config-file).
7. [Pip configuration and environment precedence](https://pip.pypa.io/en/stable/topics/configuration/).
8. [Galaxy CLI local-only installation](https://docs.ansible.com/projects/ansible-core/2.21/cli/ansible-galaxy.html) and
   [Galaxy server-list configuration](https://docs.ansible.com/projects/ansible/latest/collections_guide/collections_installing.html#configuring-the-ansible-galaxy-client).
9. [DNF signature verification, repository URLs and proxy configuration](https://dnf.readthedocs.io/en/latest/conf_ref.html) and
   [RPM key import/signature verification](https://rpm.org/docs/4.20.x/man/rpmkeys.8).
