# Step 6: Connect the bootstrap host to accepted software intake

<a id="connect-the-bootstrap-host-to-accepted-software-intake"></a>

**Continue from:** [Stage 1, Step 6](README.md#step-6-connect-the-bootstrap-host).
**Return:** [Step 7](README.md#step-7-connect-proxmox-host-updates) after the selected consumer path passes.

Configure the manually created `boot-1` after the Stage 1 supply is accepted.
Use an internal policy proxy or commissioned native mirrors for subsequent updates;
temporary acquisition access is not the permanent update path.

**Working repository:** `<prefix>-tier-0`, on `boot-1` itself. The sibling Shared repository supplies
the reusable tasks. This local play creates no guest, inventory entry or Terraform state.
**Prerequisites:** the [prepared bootstrap environment](../foundation/bootstrap/README.md),
its accepted Ansible installation and `community.general` collection, sudo access, working DNS/CA trust,
and a tested Stage 1 endpoint reachable from the bootstrap network.

## Contents

- [1. Verify the software source](#1-verify-the-software-source)
- [2. Configure the local inputs](#2-configure-the-local-inputs)
- [3. Apply the local configuration](#3-apply-the-local-configuration)
- [4. Load the shell settings](#4-load-the-shell-settings)
- [5. Verify package and tool access](#5-verify-package-and-tool-access)
- [6. Retire temporary egress](#6-retire-temporary-egress)
- [Stop or restore the previous configuration](#stop-or-restore-the-previous-configuration)

## 1. Verify the software source

From `boot-1`, verify the chosen source using the
[explicit proxy retrieval and policy checks](README.md#step-5-test-the-selected-intake-path),
or the commissioned native-mirror checks. Continue when approved retrieval and access policy work.

## 2. Configure the local inputs

Create the ignored local input in **Tier 0**:

Run from **`<prefix>-tier-0/`**.

```bash
cp -n ansible/group_vars/bootstrap.yml.example ansible/group_vars/bootstrap.yml
```

Edit in **`<prefix>-tier-0/`**.

- `ansible/group_vars/bootstrap.yml`: Supply mode, accepted proxy/mirror settings and internal proxy-bypass
  destinations.

Select **2a** or **2b**, then continue at **3**. This is not an `init-local-files.sh` deployment setup.

### 2a. Policy proxy

| Field | Set to |
| --- | --- |
| `bootstrap_software_intake_mode` | `proxy` |
| `repository_proxy_url` | Accepted internal proxy URL using a hostname or IP, such as `http://10.30.30.22:3128`; no credentials |
| `shell_proxy_no_proxy_extra` | Internal websites and HTTP/HTTPS endpoints that should bypass the proxy |
| `repository_proxy_dnf_sources` | EL repositories that must use fixed approved HTTPS sources instead of dynamic mirrors |

Use the accepted VIP or existing endpoint. The recipe sets the DNF/APT proxy and login-shell
proxy variables. Only explicitly selected DNF source sections are edited; other repositories,
DNS and `/etc/hosts` remain unchanged.
HTTPS certificate verification remains enabled; HTTPS CONNECT does not cache encrypted content.
Keep native pip, Galaxy and Terraform source restrictions where required.

For **EL10**, mirror lists can select third-party hosts outside the proxy allowlist. Choose fixed
approved sources for every enabled repository that would otherwise use such mirrors. On **`boot-1`**,
find the actual files, section IDs and URLs:

```bash
grep -nE '^\[|^(metalink|mirrorlist|baseurl)=' /etc/yum.repos.d/*.repo
```

Edit **Tier 0 `ansible/group_vars/bootstrap.yml`**. This Rocky/EPEL example must match the installed
filenames and sections; include only selected repositories and add other enabled sources as needed:

```yaml
repository_proxy_dnf_sources:
  - file: rocky.repo
    section: baseos
    baseurl: 'https://dl.rockylinux.org/pub/rocky/$releasever/BaseOS/$basearch/os/'
  - file: rocky.repo
    section: appstream
    baseurl: 'https://dl.rockylinux.org/pub/rocky/$releasever/AppStream/$basearch/os/'
  - file: rocky-extras.repo
    section: extras
    baseurl: 'https://dl.rockylinux.org/pub/rocky/$releasever/extras/$basearch/os/'
  - file: epel.repo
    section: epel
    baseurl: 'https://dl.fedoraproject.org/pub/epel/$releasever/Everything/$basearch/'
```

Use the distribution's corresponding official source or an accepted internal mirror for another EL10
distribution. Keep its existing publisher keys and signature settings. The recipe removes `mirrorlist`
and `metalink` only from selected sections and retains timestamped file backups. The proxy must allow
the selected hosts and any actual redirects; allowing the mirror-list service alone is insufficient.
An unavailable selected source stops refresh; no automatic mirror or direct-WAN fallback is added.

Add internal websites and HTTP/HTTPS endpoints that should be reached directly to
`shell_proxy_no_proxy_extra`. For example, exclude the Proxmox endpoint in
`ansible/group_vars/bootstrap.yml` using its actual hostname and any IP used directly: [1]

```yaml
shell_proxy_no_proxy_extra:
  - pve01.example.internal
  - 10.10.10.11
```

Use hostnames or IPs without `http://`, `https://` or a path.

### 2b. Native mirrors or disconnected supply

Commission and test native client configurations first, using the
[offline preparation workflow](../foundation/bootstrap/step-3e-bootstrap-offline.md#use-approved-sources-after-bootstrap)
for retained artifacts and tool configuration. Then set:

```yaml
bootstrap_software_intake_mode: mirror
```

This removes the DNF `[main] proxy` setting and the owned APT/shell proxy files.
Other repository definitions, pip configuration, Galaxy configuration and Terraform CLI
configuration remain intact. Explicit DNF source selections still apply. It installs no mirror service
and does not make a cache an offline mirror.
Retain verified package signatures, TLS trust, provider lockfiles and independent recovery artifacts.

## 3. Apply the local configuration

Use the accepted Ansible installation; activate the venv only if that installation path was selected.
Verify [bootstrap sudo access](../foundation/bootstrap/README.md#verify-sudo-access) first.
For disconnected execution, source the prepared `offline.env`.
The precheck below validates installed collections without attempting acquisition:

Run from **`<prefix>-tier-0/`**.

```bash
CONTROL_NODE_COLLECTIONS_MODE=check ANSIBLE_CONFIG=ansible/ansible.cfg \
  ansible-playbook -i localhost, ansible/playbooks/deployment/bootstrap-software-intake.yml \
  -e @ansible/group_vars/bootstrap.yml
```

**Expected:** local package/shell configuration is reconciled; a second run reports no changes.
The play imports Shared's package-policy and package/shell proxy tasks, leaving baseline timezone/IPv6
configuration untouched. The package-policy tasks apply native verification/failure defaults;
only explicitly selected DNF source sections are edited; publisher-key choices remain owned locally. [2][3]
The play uses sudo through `become: true`; no password prompt is needed with authorized
passwordless sudo. Add `--ask-become-pass` (`-K`) only when sudo requires an account password.

**IaC:** Tier 0 [inputs](../../../tier-0/ansible/group_vars/bootstrap.yml.example) and
[local play](../../../tier-0/ansible/playbooks/deployment/bootstrap-software-intake.yml);
Shared [package proxy tasks](../../../shared/ansible/roles/baseline/tasks/repository_proxy.yml)
and [shell proxy tasks](../../../shared/ansible/roles/baseline/tasks/shell_proxy.yml).
Configuration is applied locally with sudo, without enrolling `boot-1` as a managed guest.

<a id="4-verify-and-retire-temporary-egress"></a>

## 4. Load the shell settings

For **proxy mode**, load the settings in the current Bash terminal on **`boot-1`**:

```bash
source /etc/profile.d/shell-proxy.sh
```

A fresh SSH login is also valid. For **mirror mode**, use a fresh login to discard the old shell's
proxy variables; the recipe removes the proxy file. No reboot is needed. Ansible cannot change
its parent terminal's environment. Reactivate the selected venv/offline environment if used.
Existing running services retain their old environment.

## 5. Verify package and tool access

On **`boot-1`**, refresh metadata using the installed OS's command. For EL10:

```bash
sudo dnf --refresh --setopt='*.skip_if_unavailable=False' makecache
```

For Debian/Ubuntu, use this block instead:

```bash
sudo apt-get -o APT::Update::Error-Mode=any update
```

Repeat the [explicit retrieval and policy checks](README.md#step-5-test-the-selected-intake-path) from the bootstrap network.
Verify required pip, Galaxy, Terraform and artifact access with their commissioned configurations.
For Galaxy, use the [API and artifact download check](../../reference/control-node-tooling.md#galaxy-through-a-policy-proxy);
the cache must allow both destinations even when a collection is already installed.
A login-shell proxy alone does not configure every tool or CI service.
HTTPS Git remotes normally use these proxy variables; SSH remotes need their own permitted SSH path. [4]

**Expected:** approved package and tool retrieval succeeds. Stop if any required source fails.
Review [repository-specific verification settings](../../reference/proxy-cache.md#consumer-verification-and-failure-behavior)
before accepting the path; global defaults cannot override a deliberately weakened repository entry.

## 6. Retire temporary egress

Remove the temporary bootstrap WAN allowance using the approved
[firewall rules](../../architecture/networking/firewall-policy.md#rule-contracts).
Repeat **5**'s retrieval checks and the direct-WAN denial check from Stage 1.
This play changes no firewall rules.

**Accepted:** updates use the selected internal supply with direct-WAN bypass denied.
Keep the independent full-VM backup, ignored inputs and offline recovery bundle; the accepted
cache/mirrors must not become prerequisites for recovering `boot-1`.
Return to [Stage 1, Step 7](README.md#step-7-connect-proxmox-host-updates) to connect Proxmox hosts
before completing the stage.

## Stop or restore the previous configuration

Stop if dependencies, trust, approved retrieval or bypass-denial checks fail. Keep console access
and the existing recovery material. Restore the last accepted `bootstrap.yml` and rerun **3**;
restore separately owned mirror/tool configurations from their retained copies if changed.
For a first switch without prior local inputs, restore the affected configurations from the independent backup.
Removing a DNF source entry stops managing it; it does not restore its previous mirror list.
Restore selected repository files from their retained backups when reverting that source change.
Open a fresh session and repeat **4–6**. Do not substitute unrestricted egress or disable TLS/signature checks.

## References

1. [Python: proxy handling and hostname exclusions](https://docs.python.org/3/library/urllib.request.html#urllib.request.ProxyHandler)
2. [Ansible: import selected role task files](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/import_role_module.html)
3. [Ansible: manage individual INI settings](https://docs.ansible.com/projects/ansible/latest/collections/community/general/ini_file_module.html)
4. [Git: HTTP proxy environment and configuration overrides](https://git-scm.com/docs/git-config#Documentation/git-config.txt-httpproxy)
