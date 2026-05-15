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

Use the cache VIP FQDN when DNS exists:

```bash
CACHE_PROXY_URL="http://cache.corp.example.com:3128"
```

Use the VIP IP only when DNS is not ready yet:

```bash
CACHE_PROXY_URL="http://<cache_proxy_vip>:3128"
```

The proxy URL is `http://` even when the destination URL is HTTPS. Clients
speak HTTP proxy protocol to Squid, and HTTPS destinations use CONNECT tunnels.

Test from a Proxmox host:

```bash
curl -x "$CACHE_PROXY_URL" -I "https://mirrors.fedoraproject.org/"
```

## Proxmox host package updates

Proxmox hosts use Debian package tooling. Run these commands as `root` on the
Proxmox host. To make the host use the cache for package updates, create an
APT proxy config:

```bash
cat >/etc/apt/apt.conf.d/80homelab-repository-proxy <<EOF
Acquire::http::Proxy "${CACHE_PROXY_URL}";
Acquire::https::Proxy "${CACHE_PROXY_URL}";
EOF
```

Then test package metadata access:

```bash
apt update
```

Remove the host-level proxy by deleting the managed file:

```bash
rm -f /etc/apt/apt.conf.d/80homelab-repository-proxy
apt update
```

For a one-off test without writing host config:

```bash
apt \
  -o Acquire::http::Proxy="$CACHE_PROXY_URL" \
  -o Acquire::https::Proxy="$CACHE_PROXY_URL" \
  update
```

## Image downloads on Proxmox hosts

When downloading cloud images, ISOs, or checksum files from a Proxmox host
shell, use standard proxy environment variables:

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

If you use the Proxmox GUI `Download from URL` workflow, verify in your own
environment whether that task uses the host proxy configuration. For controlled
egress, the more predictable path is to download from the Proxmox host shell
with explicit proxy variables, verify checksums, then use the local file.

## Template preparation VMs

For temporary template preparation VMs, prefer the normal repository proxy
variables consumed by the Ansible baseline role:

```yaml
repository_proxy_enabled: true
repository_proxy_fqdn: "cache.{{ platform_domain }}"
repository_proxy_url: "http://{{ repository_proxy_fqdn }}:3128"
repository_proxy_ip: "<cache_proxy_vip>"
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
