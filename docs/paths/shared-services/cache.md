# Cache path

## Purpose

Use this path to deploy a shared cache pair for systems that need controlled
outbound repository and update access.

The reference implementation is `Squid` with `keepalived`. The first use case
is allowing restricted or air-gapped systems to reach approved software
sources without building full internal mirrors for every operating system,
package source, Git remote, or registry endpoint. The same service can later
expand into broader policy-enforced egress.

Deploy this before identity, Vault, HSM, or system-control hosts when those
hosts cannot reach approved software repositories directly. If you already
have direct egress, internal mirrors, Satellite-like services, or offline
repos, use those as the repository-access prerequisite instead.

This is not a full offline mirror by itself. A fully disconnected environment
still needs mirrored or offline repository content. The cache can sit in front
of that internal mirror or offline repo and give clients one controlled proxy
endpoint, but it cannot fetch content that is not reachable somewhere
upstream.

## Default deployment

| Component | Terraform default | Inventory entry | Zone | Purpose |
| --- | --- | --- | --- | --- |
| caches | `cache-1`, `cache-2` active | present by default | `external_edge` | controlled outbound web access |
| cache data disks | one `scsi1` data disk per cache VM | mounted by Ansible | VM local/shared storage | Squid cache data |
| extra cache nodes | commented examples | add matching inventory and IP entries | `external_edge` | horizontal scale or isolated policy sets |

The default is a pair. Add `cache-3` and higher when the environment needs more
horizontal capacity or separate egress policy sets.

## Service shape

| Service | Default role |
| --- | --- |
| `Squid` | serves the repository/cache proxy on `cache_proxy_port` |
| `keepalived` | owns the shared cache VIP and fails it over between cache hosts |
| allowed CIDRs | defines which internal networks may use the cache |
| allowed domains | defines which external software-source domains are reachable |

## What you configure

| Path | What you configure |
| --- | --- |
| [`terraform/common.tfvars.example`](../../../terraform/common.tfvars.example) | `external_edge` network mapping, shared storage, template ID, and SSH keys |
| [`terraform/environments/cache/terraform.tfvars.example`](../../../terraform/environments/cache/terraform.tfvars.example) | cache VM count, size, OS disk, cache data disk, storage, and tags |
| [`ansible/inventory/hosts.yml.example`](../../../ansible/inventory/hosts.yml.example) | `cache` host group |
| [`ansible/group_vars/all.yml.example`](../../../ansible/group_vars/all.yml.example) | shared hostname, domain, SSH, optional repository proxy URL, and baseline defaults |
| [`ansible/group_vars/cache.yml.example`](../../../ansible/group_vars/cache.yml.example) | cache host IPs, VIP, FQDN, port, keepalived router ID, allowed client CIDRs, allowed software-source domains, and optional upstream proxy |

## Cache storage

Keep Squid cache data off the OS disk. The Terraform example attaches a
dedicated `scsi1` data disk to each cache VM, and the Ansible cache role formats
and mounts it at `cache_squid_cache_dir`, which defaults to `/var/spool/squid`.

The example uses `/dev/sdb` because an Enterprise Linux VM with one OS disk and
one extra `scsi1` disk normally discovers the extra disk there. Change
`cache_squid_data_device` in `cache.yml` if your template exposes the disk under
a different stable device path.

Tune both sides together:

| Setting | Purpose |
| --- | --- |
| `vm_instances.<cache>.extra_disks[*].size_gb` | Proxmox data disk size |
| `cache_squid_data_device` | guest device to format and mount |
| `cache_squid_cache_dir` | mount point and Squid cache directory |
| `cache_squid_cache_mb` | Squid cache size inside that mounted filesystem |

## How other paths use it

Other paths can point restricted systems at the cache when they need approved
outbound repository/update access. The cache path owns the hosts and base
service policy; consuming paths should only add their own allow-list or routing
requirements through documented variables.

Unlike identity or Vault, the cache does not always need one deployment per
environment. It is valid to run one shared production cache and let other
environment deployments use it for repository access, as long as policy allows
those environments to share the same outbound path.

Deploy a separate cache per environment only when you need isolated egress
policy, isolated testing of the cache service itself, or an environment that
must not depend on production shared services.

This is intentional in the Ansible layout. The cache service settings live in
`cache.yml`, and consumers enable `repository_proxy_url` in `all.yml` or
`all.<env>.yml`. That lets any setup use a cache that was deployed somewhere
else.

The repository proxy is opt-in for consumers. If `repository_proxy_url` is
unset or blank, the baseline role does not configure a proxy. Any setup can
opt out of a shared proxy by setting `repository_proxy_enabled: false` in that
setup's group vars file.

For the cache service itself, set the cache VIP and service endpoint in
`cache.yml`. Use CIDR form for the VIP because keepalived assigns this address
to the interface:

```yaml
cache_proxy_vip_cidr: "<cache_proxy_vip>/<prefix>"
cache_proxy_name: cache
cache_proxy_fqdn: "{{ cache_proxy_name }}.{{ platform_domain }}"
cache_proxy_port: 3128
```

The role derives the plain VIP IP from `cache_proxy_vip_cidr` for consumers
that must not include a prefix, such as `/etc/hosts` entries.

For Enterprise Linux guests managed by this repo, enable only the repository
proxy consumer values in `all.yml` or `all.<env>.yml` before running paths that
need controlled software-source access:

```yaml
repository_proxy_enabled: true
repository_proxy_fqdn: "cache.{{ platform_domain }}"
repository_proxy_url: "http://{{ repository_proxy_fqdn }}:3128"
repository_proxy_ip: "<cache_proxy_vip>"
```

Use `all.yml` when the cache should be shared by default. Use `all.<env>.yml`
only when an environment should use a different cache or explicitly consume a
shared cache by FQDN.

The URL should use the FQDN. `repository_proxy_ip` can stay unset when DNS
resolves `repository_proxy_fqdn`. Set it only when the baseline role must write
a temporary `/etc/hosts` entry before identity DNS exists.

The cache hosts are the bootstrap exception. They do not use the shared
repository proxy from `all.yml` while Squid is being installed. The cache setup
sets `repository_proxy_enabled: false` by default so cache hosts do not point
at their own VIP. If cache hosts must chain through an existing upstream proxy
while being built, set `repository_proxy_enabled: true` and
`repository_proxy_url` in `cache.yml` to that upstream proxy, not to the cache
VIP.

For disconnected environments, point the cache at internal mirrors or offline
repository content. In that shape, clients are still isolated from direct
software sources, but the cache upstream is private instead of internet-facing.

## Validation

After the cache role finishes, the cache playbook runs a validation step from
the deployment host. It tests each cache node directly, tests the cache VIP by
IP, warns if the expected cache FQDN does not work, then stops keepalived on
the current VIP owner to verify failover before starting keepalived again.

Set `cache_validation_url` to a URL allowed by `cache_squid_allowed_domains`.
For disconnected environments, point it at an internal mirror or offline repo
endpoint reachable through the cache path. Set
`cache_validation_failover_enabled: false` only when you want to skip the
temporary keepalived failover test.

Keep this boundary:

- the cache setup owns the cache hosts
- software sources and allow-lists should be explicit
- restricted systems should use the cache VIP as their repository proxy
- air-gapped systems should use the cache only when policy allows it
- more cache nodes are added by extending `vm_instances`, inventory, and IP map

For Enterprise Linux package managers, client systems can use the cache as a
global DNF/YUM proxy or set it only on selected repository files. Use
repository-specific proxy settings when internal repositories should remain
direct while external update repositories go through the cache.

## Read more

- [Shared services path](README.md)
- [Network architecture](../../architecture/network.md)
- [Security principles](../../security/security-principles.md)
- [Set proxy for YUM/DNF repositories](https://www.baeldung.com/linux/yum-dnf-repositories-set-proxy)
