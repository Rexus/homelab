# Proxmox cache usage

## Purpose

Use this guide when the shared cache path already exists and you want Proxmox
hosts or Proxmox template workflows to consume it for controlled repository and
image access.

This is not a Proxmox prerequisite. It is an optional operating mode for
environments where Proxmox hosts, template builders, or restricted networks
should use the same repository/cache proxy as other managed systems.

The cache service itself is owned by the
[cache path](../../paths/shared-services/cache.md). This guide only shows how
Proxmox-facing workflows can consume that proxy.

## Proxy endpoint

Set `CACHE_PROXY_URL` to the cache endpoint for your environment. Use the FQDN
or VIP IP that Proxmox should reach:

```bash
CACHE_PROXY_URL="http://cache.corp.example.com:3128"
```

## Configure the Proxmox cluster

Use the Proxmox Datacenter setting when you want the Proxmox cluster itself to
use the cache for Proxmox-managed downloads.

In the Proxmox UI:

1. Open `Datacenter`.
2. Select `Options`.
3. Select the `HTTP proxy` row.
4. Click `Edit`.
5. Enter the value you use for `CACHE_PROXY_URL`.
6. Save.

The setting is cluster-wide and is stored in `/etc/pve/datacenter.cfg` as
`http_proxy`. You can verify it from any Proxmox node:

```bash
grep '^http_proxy:' /etc/pve/datacenter.cfg
```

This setting is for Proxmox download workflows. If you also want host shell
commands or `apt update` to use the cache, configure the host package manager as
shown below.

## Configure with Ansible

If `ansible/inventory/hosts.yml` has Proxmox hosts in the `hypervisors` group,
Ansible can manage the Datacenter HTTP proxy and the per-host APT proxy file.

Set the shared proxy URL in `ansible/group_vars/all.yml`:

```yaml
repository_proxy_enabled: true
repository_proxy_fqdn: "cache.{{ platform_domain }}"
repository_proxy_url: "http://{{ repository_proxy_fqdn }}:3128"
```

Then run:

```bash
cd ansible
ansible-playbook -i inventory/hosts.yml playbooks/proxmox-hosts.yml
```

## Test from a Proxmox host

Run this from a Proxmox host shell:

```bash
curl -x "$CACHE_PROXY_URL" -I "https://mirrors.fedoraproject.org/"
```

## Optional host package updates

Proxmox hosts use Debian package tooling. If host package updates should also
use the cache, first test APT with the proxy without writing host config.

### Test APT through the proxy

```bash
apt \
  -o Acquire::http::Proxy="$CACHE_PROXY_URL" \
  -o Acquire::https::Proxy="$CACHE_PROXY_URL" \
  update
```

### Persist the APT proxy

Create or update `/etc/apt/apt.conf.d/76pveproxy` as `root` on each Proxmox
host:

```aptconf
Acquire::http::Proxy "${CACHE_PROXY_URL}";
Acquire::https::Proxy "${CACHE_PROXY_URL}";
```

Use a different HTTPS proxy URL only when your environment provides one.
Otherwise, keep the same cache endpoint for both entries. In Ansible, set
`repository_proxy_https_url` only when it should differ from
`repository_proxy_url`.

Then confirm package metadata access still works through the persisted config:

```bash
apt update
```

### Remove the APT proxy

Delete the proxy config file:

```bash
rm -f /etc/apt/apt.conf.d/76pveproxy
apt update
```

## Image downloads on Proxmox hosts

For manual cloud image, ISO, or checksum downloads from a Proxmox host shell,
use standard proxy environment variables:

```bash
export http_proxy="$CACHE_PROXY_URL"
export https_proxy="$CACHE_PROXY_URL"

wget "<image-url>"
wget "<checksum-url>"
```

Unset them after the download window:

```bash
unset http_proxy https_proxy
```

For controlled egress, the most predictable manual path is to download from the
Proxmox host shell with explicit proxy variables, verify checksums, then use the
local file.

## Template preparation VMs

For temporary template preparation VMs, prefer the normal repository proxy
variables consumed by the Ansible baseline role:

```yaml
repository_proxy_enabled: true
repository_proxy_fqdn: "cache.{{ platform_domain }}"
repository_proxy_url: "http://{{ repository_proxy_fqdn }}:3128"
```

Keep permanent proxy settings out of reusable templates unless every future
clone should inherit that exact proxy. The safer default is:

- use the proxy while preparing or refreshing the template
- clean package caches and cloud-init state before converting to template
- let deployed guests receive environment-specific proxy settings from Ansible

For manual Enterprise Linux template prep, a one-off DNF command is often
enough:

```bash
sudo dnf \
  --setopt=proxy="$CACHE_PROXY_URL" \
  install -y acpid qemu-guest-agent
```

## Read more

- [Cache path](../../paths/shared-services/cache.md)
- [Enterprise Linux template](enterprise-linux-template.md)
- [Proxmox hardening baseline](hardening.md)
- [Proxmox datacenter configuration](https://pve.proxmox.com/pve-docs/datacenter.cfg.5.html)
