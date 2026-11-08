# Connect the bootstrap host to accepted software intake

Configure the manually created `boot-1` after the Stage 1 supply is accepted.
Use an internal policy proxy or commissioned native mirrors for subsequent updates;
temporary acquisition access is not the permanent update path.

**Working repository:** `<prefix>-tier-0`, on `boot-1` itself. The sibling Shared repository supplies
the reusable tasks. This local play creates no guest, inventory entry or Terraform state.
**Prerequisites:** the [prepared bootstrap environment](../foundation/proxmox/bootstrap.md),
its accepted Ansible venv and `community.general` collection, sudo access, working DNS/CA trust,
and a tested Stage 1 endpoint reachable from the bootstrap network.

## Contents

- [1. Select the accepted supply](#1-select-the-accepted-supply)
- [2. Apply the local configuration](#2-apply-the-local-configuration)
- [3. Verify and retire temporary egress](#3-verify-and-retire-temporary-egress)
- [Stop or restore the previous configuration](#stop-or-restore-the-previous-configuration)

## 1. Select the accepted supply

From the Tier 2 checkout used in Stage 1, return to Tier 0 and create the ignored local input:

```bash
cd ../homelab-tier-0
cp -n ansible/group_vars/bootstrap.yml.example ansible/group_vars/bootstrap.yml
vi ansible/group_vars/bootstrap.yml
```

Select **1a** or **1b**; both continue at **2**. This is not an `init-local-files.sh` deployment setup.

### 1a. Policy proxy

| Field | Set to |
| --- | --- |
| `bootstrap_software_intake_mode` | `proxy` |
| `repository_proxy_url` | Accepted internal URL, such as `http://10.30.30.22:3128`; no credentials |
| `shell_proxy_no_proxy_extra` | Required: actual Proxmox API hostname **and IP**, plus approved internal endpoints |
| `bootstrap_software_intake_accepted` | `true` after approved retrieval, policy and firewall checks pass |

Use the accepted VIP or existing endpoint. The recipe sets the DNF/APT proxy and login-shell
proxy variables. It does not change repository definitions, DNS or `/etc/hosts`.
HTTPS certificate verification remains enabled; HTTPS CONNECT does not cache encrypted content.
Keep native pip, Galaxy and Terraform source restrictions where required.
Replace the example exclusions (`pve01.example.internal`, `10.10.10.11`) with actual site values.
List names/IPs explicitly: private-network CIDRs in `no_proxy` are not understood by every client,
including Python's urllib used by SDN lookup. [1] This local play does not load a tier inventory's domain.

### 1b. Native mirrors or disconnected supply

Commission and test native client configurations first, using the
[offline preparation workflow](../foundation/proxmox/bootstrap-offline.md#use-approved-sources-after-bootstrap)
for retained artifacts and tool configuration. Then set:

```yaml
bootstrap_software_intake_mode: mirror
bootstrap_software_intake_accepted: true
```

This removes the DNF `[main] proxy` setting and the owned APT/shell proxy files.
Existing repository definitions, pip configuration, Galaxy configuration and Terraform CLI
configuration remain intact. It installs no mirror service and does not make a cache an offline mirror.
Retain verified package signatures, TLS trust, provider lockfiles and independent recovery artifacts.

## 2. Apply the local configuration

Use the accepted bootstrap venv. For disconnected execution, source its prepared `offline.env`
first. The precheck below validates installed collections without attempting acquisition:

```bash
CONTROL_NODE_COLLECTIONS_MODE=check ANSIBLE_CONFIG=ansible/ansible.cfg \
  ansible-playbook -i localhost, ansible/playbooks/deployment/bootstrap-software-intake.yml \
  -e @ansible/group_vars/bootstrap.yml --ask-become-pass
```

**Expected:** local package/shell configuration is reconciled; a second run reports no changes.
The play imports only Shared's package and shell proxy tasks, leaving baseline timezone/IPv6
configuration untouched. Native role imports select those task files explicitly. [2][3]
With accepted passwordless sudo, omit `--ask-become-pass`; this also permits noninteractive jobs.

**IaC:** Tier 0 [inputs](../../../tier-0/ansible/group_vars/bootstrap.yml.example) and
[local play](../../../tier-0/ansible/playbooks/deployment/bootstrap-software-intake.yml);
Shared [package proxy tasks](../../../shared/ansible/roles/baseline/tasks/repository_proxy.yml)
and [shell proxy tasks](../../../shared/ansible/roles/baseline/tasks/shell_proxy.yml).
Configuration is applied locally with sudo, without enrolling `boot-1` as a managed guest.

## 3. Verify and retire temporary egress

1. Open a fresh SSH login and reactivate the accepted venv/offline environment.
   Existing shells and running services retain their old environment.
2. Refresh package metadata through the accepted source using the installed OS's command:

   | Package manager | Command |
   | --- | --- |
   | DNF | `sudo dnf makecache` |
   | APT | `sudo apt-get update` |

   Repeat the [Stage 1 consumer checks](README.md#step-3-connect-and-verify-consumers)
   from the bootstrap network.
3. Verify the required pip, Galaxy, Terraform and artifact access with the commissioned native
   configurations. A login-shell proxy alone does not configure every tool or CI service.
4. Remove temporary bootstrap WAN allowance using the approved
   [firewall rules](../../architecture/networking/firewall-policy.md#rule-contracts), then repeat
   approved retrieval and direct-WAN denial checks. This play changes no firewall rules.

**Accepted:** updates use the selected internal supply with direct-WAN bypass denied.
Keep the independent full-VM backup, ignored inputs and offline recovery bundle; the accepted
cache/mirrors must not become prerequisites for recovering `boot-1`.
Return to [Stage 1 consumer acceptance](README.md#step-3-connect-and-verify-consumers), then Stage 2.

## Stop or restore the previous configuration

Stop if dependencies, trust, approved retrieval or bypass-denial checks fail. Keep console access
and the existing recovery material. Restore the last accepted `bootstrap.yml` and rerun **2**;
restore separately owned mirror/tool configurations from their retained copies if changed.
For a first switch without prior local inputs, restore the affected configurations from the independent backup.
Open a fresh session and repeat **3**. Do not substitute unrestricted egress or disable TLS/signature checks.

## References

1. [Python: proxy handling and hostname exclusions](https://docs.python.org/3/library/urllib.request.html#urllib.request.ProxyHandler)
2. [Ansible: import selected role task files](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/import_role_module.html)
3. [Ansible: manage individual INI settings](https://docs.ansible.com/projects/ansible/latest/collections/community/general/ini_file_module.html)
