# Connect the bootstrap host to accepted software intake

Configure the manually created `boot-1` after the Stage 1 supply is accepted.
Use an internal policy proxy or commissioned native mirrors for subsequent updates;
temporary acquisition access is not the permanent update path.

**Working repository:** `<prefix>-tier-0`, on `boot-1` itself. The sibling Shared repository supplies
the reusable tasks. This local play creates no guest, inventory entry or Terraform state.
**Prerequisites:** the [prepared bootstrap environment](../foundation/proxmox/bootstrap.md),
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

Use the accepted VIP or existing endpoint. The recipe sets the DNF/APT proxy and login-shell
proxy variables. It does not change repository definitions, DNS or `/etc/hosts`.
HTTPS certificate verification remains enabled; HTTPS CONNECT does not cache encrypted content.
Keep native pip, Galaxy and Terraform source restrictions where required.

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
[offline preparation workflow](../foundation/proxmox/bootstrap-offline.md#use-approved-sources-after-bootstrap)
for retained artifacts and tool configuration. Then set:

```yaml
bootstrap_software_intake_mode: mirror
```

This removes the DNF `[main] proxy` setting and the owned APT/shell proxy files.
Existing repository definitions, pip configuration, Galaxy configuration and Terraform CLI
configuration remain intact. It installs no mirror service and does not make a cache an offline mirror.
Retain verified package signatures, TLS trust, provider lockfiles and independent recovery artifacts.

## 3. Apply the local configuration

Use the accepted Ansible installation; activate the venv only if that installation path was selected.
Verify [bootstrap sudo access](../foundation/proxmox/bootstrap.md#verify-sudo-access) first.
For disconnected execution, source the prepared `offline.env`.
The precheck below validates installed collections without attempting acquisition:

Run from **`<prefix>-tier-0/`**.

```bash
CONTROL_NODE_COLLECTIONS_MODE=check ANSIBLE_CONFIG=ansible/ansible.cfg \
  ansible-playbook -i localhost, ansible/playbooks/deployment/bootstrap-software-intake.yml \
  -e @ansible/group_vars/bootstrap.yml
```

**Expected:** local package/shell configuration is reconciled; a second run reports no changes.
The play imports only Shared's package and shell proxy tasks, leaving baseline timezone/IPv6
configuration untouched. Native role imports select those task files explicitly. [2][3]
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
sudo dnf makecache
```

For Debian/Ubuntu, use this block instead:

```bash
sudo apt-get update
```

Repeat the [explicit retrieval and policy checks](README.md#step-5-test-the-selected-intake-path) from the bootstrap network.
Verify required pip, Galaxy, Terraform and artifact access with their commissioned configurations.
A login-shell proxy alone does not configure every tool or CI service.
HTTPS Git remotes normally use these proxy variables; SSH remotes need their own permitted SSH path. [4]

**Expected:** approved package and tool retrieval succeeds. Stop if any required source fails.

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
Open a fresh session and repeat **4–6**. Do not substitute unrestricted egress or disable TLS/signature checks.

## References

1. [Python: proxy handling and hostname exclusions](https://docs.python.org/3/library/urllib.request.html#urllib.request.ProxyHandler)
2. [Ansible: import selected role task files](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/import_role_module.html)
3. [Ansible: manage individual INI settings](https://docs.ansible.com/projects/ansible/latest/collections/community/general/ini_file_module.html)
4. [Git: HTTP proxy environment and configuration overrides](https://git-scm.com/docs/git-config#Documentation/git-config.txt-httpproxy)
