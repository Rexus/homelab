# Proxmox update-access tasks

Connect Proxmox-managed downloads and host APT to an accepted repository proxy.
This consumes [Stage 1 software intake](../../deployment/stage-1-software-intake/README.md);
it neither installs the cache nor schedules package upgrades.

**Working repository:** `<prefix>-tier-0` for managed configuration.
**Host commands:** run as root in an approved shell on the named Proxmox host.
**Before starting:** accepted cache endpoint, permitted host subnet/repository domains,
independent console and a known rollback configuration.
**Why:** [controlled software intake](../../architecture/software/software-intake.md).

## Find the task

- [How are managed hosts configured?](#how-are-managed-hosts-configured)
- [How is the GUI download proxy configured manually?](#how-is-the-gui-download-proxy-configured-manually)
- [How is host APT configured manually?](#how-is-host-apt-configured-manually)
- [How are image downloads and builder VMs handled?](#how-are-image-downloads-and-builder-vms-handled)
- [How is a proxy change rolled back?](#how-is-a-proxy-change-rolled-back)

<a id="purpose"></a>
<a id="proxy-endpoint"></a>
<a id="configure-with-ansible"></a>

## How are managed hosts configured?

1. On the prepared execution host, use the **Tier 0 root**. Add existing Proxmox hosts
   to `hypervisors` in `ansible/inventory/hosts.yml`; this does not provision hosts.
2. Set these fields in ignored `ansible/group_vars/all.yml`, using the accepted endpoint:

   ```yaml
   repository_proxy_enabled: true
   repository_proxy_fqdn: "cache.{{ platform_domain }}"
   repository_proxy_url: "http://{{ repository_proxy_fqdn }}:3128"
   ```

3. Run the supplied host recipe:

   ```bash
   # Run from <prefix>-tier-0/ on the protected execution host.
   export ANSIBLE_CONFIG="$PWD/ansible/ansible.cfg"
   read -r -p "Proxmox host SSH user (example: root): " PVE_SSH_USER
   ansible-playbook -i ansible/inventory/hosts.yml -e @ansible/group_vars/all.yml -e "ansible_user=$PVE_SSH_USER" ansible/playbooks/proxmox-hosts.yml
   ```

   Select a host SSH account with the required privilege; it is separate from a Proxmox API token.
4. On each affected host, verify Datacenter and APT behavior using the checks below.
   Do not also maintain the same settings manually.

**Expected:** the [Proxmox host role](../../../tier-0/ansible/roles/proxmox_host)
reconciles the Datacenter proxy and per-host APT configuration. The Tier 2 cache
receives download requests, not Tier 0 administrative authority.

<a id="configure-the-proxmox-cluster"></a>

## How is the GUI download proxy configured manually?

1. Open **Datacenter > Options > HTTP proxy > Edit**.
2. Enter the accepted proxy, for example `http://cache.corp.example.com:3128`, and save.
3. On a Proxmox host, inspect the cluster-wide setting:

   Run on the selected Proxmox host as an authorized root operator.

   ```bash
   grep '^http_proxy:' /etc/pve/datacenter.cfg
   ```

4. Test an approved download workflow. Require the selected endpoint and a successful
   download. This GUI setting does not configure host shell commands or APT.

<a id="optional-host-package-updates"></a>
<a id="test-from-a-proxmox-host"></a>
<a id="test-apt-through-the-proxy"></a>

## How is host APT configured manually?

1. On the **Proxmox host**, select the accepted endpoint and test it explicitly:

   ```bash
   # Run on the selected Proxmox host as an authorized root operator.
   read -r -p "Approved proxy URL (example: http://cache.corp.example.com:3128): " CACHE_PROXY_URL
   read -r -p "Approved small repository metadata URL: " SOURCE_URL
   curl --fail --noproxy '' --proxy "$CACHE_PROXY_URL" --output /dev/null "$SOURCE_URL"
   apt-get -o Acquire::http::Proxy="$CACHE_PROXY_URL" -o Acquire::https::Proxy="$CACHE_PROXY_URL" update
   ```

   Stop if either request fails. Check source policy, DNS and reachability before writing configuration.
2. As **root on that host**, preserve the prior owned file if present, then write the
   accepted literal endpoint. The shell expands the value in this block:

   ```bash
   # Run on the selected Proxmox host as an authorized root operator.
   if [ -f /etc/apt/apt.conf.d/76pveproxy ]; then
     cp -a /etc/apt/apt.conf.d/76pveproxy /etc/apt/apt.conf.d/76pveproxy.before-change
   fi
   cat > /etc/apt/apt.conf.d/76pveproxy <<EOF
   Acquire::http::Proxy "$CACHE_PROXY_URL";
   Acquire::https::Proxy "$CACHE_PROXY_URL";
   EOF
   apt-get update
   ```

3. Require successful repository metadata refresh from the intended sources. APT
   `update` refreshes metadata; install/upgrade decisions use the [maintenance runbook](../maintenance.md).

<a id="persist-the-apt-proxy"></a>

The same HTTP proxy URL can forward HTTPS using CONNECT. It does not decrypt/cache
HTTPS payloads. A separately approved HTTPS-proxy endpoint can use its own value;
see [transport limits](../../deployment/stage-1-software-intake/proxy-cache.md#transport-limits).

<a id="image-downloads-on-proxmox-hosts"></a>
<a id="template-preparation-vms"></a>

## How are image downloads and builder VMs handled?

| Task | Action |
| --- | --- |
| Manual artifact download | On the download host, pass the accepted proxy explicitly; verify the vendor release and unpacked bytes before publication |
| Proxmox-managed downloads | Use the accepted Datacenter proxy above |
| Linux builder packages | Set `repository_proxy_*` in the builder's local Ansible inputs; use [staged refresh](../virtual-machines/template-refresh.md) |
| Reusable template cleanup | Clear machine-specific state/caches before conversion; clones receive their environment's proxy configuration |
| Offline custody | Use approved retained mirrors/artifacts; this recipe creates no route across an air gap |

For a manual image fetch in the current download shell:

```bash
# Run on the authorized acquisition host in its artifact download directory.
read -r -p "Approved proxy URL: " CACHE_PROXY_URL
read -r -p "Approved artifact URL: " IMAGE_URL
no_proxy='' https_proxy="$CACHE_PROXY_URL" http_proxy="$CACHE_PROXY_URL" wget "$IMAGE_URL"
```

Follow [artifact verification and import](../../deployment/foundation/proxmox/templates.md#step-1-verify-unpack-and-upload).
A successful download alone is not release approval.

<a id="remove-the-apt-proxy"></a>

## How is a proxy change rolled back?

1. Retain the error and restore the previous accepted endpoint in its owner: Ansible
   inputs for managed hosts, or the GUI/file for the manual path.
2. For the manual APT path, restore `76pveproxy.before-change` if it existed. Remove
   `76pveproxy` only when this task created it and another approved supply path exists.
3. Rerun the appropriate recipe/check. Require repository access through the selected
   policy before closing the change; do not open unrestricted WAN access to fix it.

<a id="read-more"></a>

**Related:** [template operations](../virtual-machines/template-lifecycle.md),
[guest package intake](../../deployment/stage-1-software-intake/README.md#step-3-connect-and-verify-consumers),
and [network policy](../../architecture/networking/firewall-policy.md).
