# Proxmox update-access tasks

Connect Proxmox-managed downloads and host APT to the accepted repository proxy, then install
updates during maintenance. This is [Stage 1, Step 7](../../03-deployment/stage-1-software-intake/README.md#step-7-connect-proxmox-host-updates).
Hosts pull approved content; the cache does not push updates or receive host credentials.

**Working repository:** `<prefix>-tier-0` for managed configuration.
**Host commands:** run as root in an approved shell on the named Proxmox host.
**Before starting:** accepted cache endpoint, permitted host subnet/repository domains,
independent console and a known rollback configuration.
**Why:** [controlled software intake](../../01-architecture/07-software-intake/README.md).

## Find the task

- [How are managed hosts configured?](#how-are-managed-hosts-configured)
- [How are Proxmox updates installed?](#how-are-proxmox-updates-installed)
- [What if APT reports signature or hash errors?](apt-refresh.md)
- [How is the GUI download proxy configured manually?](#how-is-the-gui-download-proxy-configured-manually)
- [How is host APT configured manually?](#how-is-host-apt-configured-manually)
- [How are image downloads and builder VMs handled?](#how-are-image-downloads-and-builder-vms-handled)
- [How is a proxy change rolled back?](#how-is-a-proxy-change-rolled-back)

<a id="purpose"></a>
<a id="proxy-endpoint"></a>
<a id="configure-with-ansible"></a>

## How are managed hosts configured?

### 1. Permit the host update path

Include the Proxmox management subnet in the cache's permitted client CIDRs and allow the actual
Debian, Proxmox and selected Ceph repository domains. Keep the configured repository/subscription
choice; a proxy does not supply an enterprise subscription. [1]
Allow host-initiated traffic to the proxy's selected port, normally TCP 3128, with direct-WAN bypass denied.
DNS and the proxy must work without later FreeIPA, Vault or Kubernetes services.

### 2. Register the existing hosts and proxy

For first use, complete [host-management Steps 1–5](../01-hosting/README.md#1-initialize-the-local-files):
initialize the local files, register `hypervisors`, authorize the bootstrap public key and require
Ansible `pong`. Return here afterward. Existing accepted registrations can be reused.

Then edit **`<prefix>-tier-0/ansible/group_vars/all.yml`** with the accepted endpoint:

```yaml
repository_proxy_enabled: true
repository_proxy_url: "http://10.30.30.22:3128"
```

A DNS name is valid when every host already resolves it. This recipe does not create DNS or hosts entries.

<a id="3-verify-host-ssh-access"></a>

### 3. Review the selected targets

Select the SSH account verified during registration. List the play's targets before applying:

Run from **`<prefix>-tier-0/`** on the prepared execution host:

```bash
read -r -p "Proxmox host SSH user (example: root): " PVE_SSH_USER
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e "ansible_user=$PVE_SSH_USER" \
  ansible/playbooks/proxmox-hosts.yml --list-hosts
```

**Expected:** only the registered Proxmox hosts are listed. Stop for an empty or unexpected target list.
The account needs authorized root/sudo access for the next step; this listing changes no host.

### 4. Apply the proxy settings

Run from **`<prefix>-tier-0/`**, in the same shell:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i ansible/inventory/hosts.yml \
  -e @ansible/group_vars/all.yml -e "ansible_user=$PVE_SSH_USER" ansible/playbooks/proxmox-hosts.yml
```

Add `--ask-become-pass` only if the selected non-root account requires a sudo password.

**Expected:** the [host playbook](../../../tier-0/ansible/playbooks/proxmox-hosts.yml) and
[proxy role](../../../tier-0/ansible/roles/proxmox_host) reconcile the cluster-wide Datacenter proxy
and `/etc/apt/apt.conf.d/76pveproxy` on every selected host. They install no packages and reboot no host.
The recipe also owns `/etc/apt/apt.conf.d/90package-policy`, separate from Proxmox's generated
proxy file, for strict refresh and verification defaults.
Do not also maintain these settings through the manual alternatives below.

### 5. Verify APT on every host

Run as **root on each Proxmox host**:

```bash
apt-config dump | grep -i 'Acquire::.*Proxy'
apt-get -o APT::Update::Error-Mode=any update
```

**Expected:** the effective proxy points to the accepted endpoint and every enabled repository refreshes
successfully. Check requests in `/var/log/squid/access.log` on the active cache and repeat Stage 1's
direct-WAN denial check from the host network. Stop on proxy denial, subscription, signature or TLS errors.
For `Hash Sum mismatch` or an `InRelease` splitting error, follow the
[APT refresh checks](apt-refresh.md) before installing updates; downloaded byte counts alone do not establish success.

Proxmox GUI/API update refreshes can rewrite `76pveproxy` from the Datacenter setting.
Recheck after GUI refreshes; APT HTTPS inherits the HTTP setting when no HTTPS override exists. [2][3]
The Datacenter setting does not configure ordinary shell `curl`/Git commands.

**Continue:** install updates below, or return to [Stage 1](../../03-deployment/stage-1-software-intake/README.md#capability-available)
when this change only commissions update access.

## How are Proxmox updates installed?

1. Follow the [maintenance gate](../01-hosting/maintenance.md#upgrade-gate): current recoverable backups,
   console access, reviewed release path and enough surviving capacity. Keep the cache available;
   move affected guests or plan their outage. Update one cluster host at a time.
2. On the **selected Proxmox host**, complete action 5 above, then install within the same supported release:

   ```bash
   apt full-upgrade
   ```

   Review the proposed package changes and answer the native prompt. Proxmox specifies `full-upgrade`
   for its rolling package updates; do not substitute `apt upgrade`. [4]
3. Reboot that host during the maintenance window when required by the installed update, then verify:

   Run as **root on the updated Proxmox host**:

   ```bash
   pveversion -v
   systemctl --failed
   ```

   Confirm guest health and, where present, cluster quorum and Ceph health before the next host.
   A major Proxmox or Ceph release change uses its release-specific upgrade guide, not this routine step.

**Expected:** the host runs the accepted packages and guests/storage remain healthy.
Update access alone does not schedule or approve patch installation.

<a id="configure-the-proxmox-cluster"></a>

## How is the GUI download proxy configured manually?

1. Open **Datacenter > Options > HTTP proxy > Edit**.
2. Enter the accepted proxy, for example `http://cache.corp.example.com:3128`, and save.
3. On a Proxmox host, inspect the cluster-wide setting:

   Run on **the selected Proxmox host as an authorized root operator**.

   ```bash
   grep '^http_proxy:' /etc/pve/datacenter.cfg
   ```

4. Test an approved download workflow, then verify host APT using action 5 above.
   GUI/API update refreshes can generate APT proxy configuration; ordinary shell commands remain separate. [2]

<a id="optional-host-package-updates"></a>
<a id="test-from-a-proxmox-host"></a>
<a id="test-apt-through-the-proxy"></a>

## How is host APT configured manually?

1. On the **Proxmox host**, select the accepted endpoint and test it explicitly:

   Run on **the selected Proxmox host as an authorized root operator**.

   ```bash
   read -r -p "Approved proxy URL (example: http://cache.corp.example.com:3128): " CACHE_PROXY_URL
   read -r -p "Approved small repository metadata URL: " SOURCE_URL
   curl --fail --noproxy '' --proxy "$CACHE_PROXY_URL" --output /dev/null "$SOURCE_URL"
   apt-get -o APT::Update::Error-Mode=any -o Acquire::http::Proxy="$CACHE_PROXY_URL" \
     -o Acquire::https::Proxy="$CACHE_PROXY_URL" update
   ```

   Stop if either request fails. Check source policy, DNS and reachability before writing configuration.
2. As **root on that host**, preserve the prior owned file if present, then write the
   accepted literal endpoint. The shell expands the value in this block:

   Run on **the selected Proxmox host as an authorized root operator**.

   ```bash
   if [ -f /etc/apt/apt.conf.d/76pveproxy ]; then
     APT_PROXY_BACKUP="$(mktemp /root/76pveproxy.before-change.XXXXXX)" || exit 1
     cp -a /etc/apt/apt.conf.d/76pveproxy "$APT_PROXY_BACKUP" || exit 1
     printf 'Retained rollback file: %s\n' "$APT_PROXY_BACKUP"
   fi
   ```

   Record the printed rollback path, or record that no prior file existed. A new copy is retained
   for each change; do not overwrite an earlier rollback file. Then write on **the same Proxmox host**:

   ```bash
   cat > /etc/apt/apt.conf.d/76pveproxy <<EOF
   Acquire::http::Proxy "$CACHE_PROXY_URL";
   Acquire::https::Proxy "$CACHE_PROXY_URL";
   EOF
   apt-get -o APT::Update::Error-Mode=any update
   ```

3. Require successful repository metadata refresh from the intended sources. APT
   `update` refreshes metadata; install/upgrade decisions use the [maintenance runbook](../01-hosting/maintenance.md).

<a id="persist-the-apt-proxy"></a>

The same HTTP proxy URL can forward HTTPS using CONNECT. It does not decrypt/cache
HTTPS payloads. A separately approved HTTPS-proxy endpoint can use its own value;
see [transport limits](../../08-reference/proxy-cache.md#transport-limits).

<a id="image-downloads-on-proxmox-hosts"></a>
<a id="template-preparation-vms"></a>

## How are image downloads and builder VMs handled?

| Task | Action |
| --- | --- |
| Manual artifact download | On the download host, pass the accepted proxy explicitly; verify the vendor release and unpacked bytes before publication |
| Proxmox-managed downloads | Use the accepted Datacenter proxy above |
| Linux builder packages | Set `repository_proxy_*` in the builder's local Ansible inputs; use [staged refresh](../01-hosting/templates/template-refresh.md) |
| Reusable template cleanup | Clear machine-specific state/caches before conversion; clones receive their environment's proxy configuration |
| Offline custody | Use approved retained mirrors/artifacts; this recipe creates no route across an air gap |

For a manual image fetch in the current download shell:

Run on **the authorized acquisition host in its artifact download directory**.

```bash
read -r -p "Approved proxy URL: " CACHE_PROXY_URL
read -r -p "Approved artifact URL: " IMAGE_URL
no_proxy='' https_proxy="$CACHE_PROXY_URL" http_proxy="$CACHE_PROXY_URL" wget "$IMAGE_URL"
```

Follow [artifact verification and import](../../03-deployment/foundation/proxmox/templates.md#step-1-verify-unpack-and-upload).
A successful download alone is not release approval.

<a id="remove-the-apt-proxy"></a>

## How is a proxy change rolled back?

1. Retain the error and restore the previous accepted endpoint in its owner: Ansible
   inputs for managed hosts, or the GUI/file for the manual path.
2. For the manual APT path, restore the recorded `/root/76pveproxy.before-change.*` copy for that
   specific change if a prior file existed. Remove `76pveproxy` only when this task created it
   and another approved supply path exists. A host-local rollback file is not an independent backup.
3. Rerun the appropriate recipe/check. Require repository access through the selected
   policy before closing the change; do not open unrestricted WAN access to fix it.

<a id="read-more"></a>

**Related:** [template operations](../01-hosting/templates/template-lifecycle.md),
[guest package intake](../../03-deployment/stage-1-software-intake/README.md#step-3-connect-and-verify-consumers),
and [network policy](../../01-architecture/05-networking/01-firewall-policy.md).

## References

1. [Proxmox package repositories](https://github.com/proxmox/pve-docs/blob/master/pve-package-repos.adoc), checked 2026-11-09.
2. [Proxmox APT refresh and generated proxy file](https://github.com/proxmox/pve-manager/blob/master/PVE/API2/APT.pm), checked 2026-11-09.
3. [APT HTTPS options and HTTP inheritance](https://manpages.debian.org/trixie/apt/apt-transport-https.1.en.html), checked 2026-11-09.
4. [Proxmox system software updates](https://github.com/proxmox/pve-docs/blob/master/system-software-updates.adoc), checked 2026-11-09.
