# Cache path

## Purpose

Use this path to deploy a shared cache pair for systems that need controlled
outbound web access.

The reference implementation is `Squid` with `keepalived`. The first use case
is allowing restricted or air-gapped systems to reach approved update sources
without building full internal mirrors for every operating system and package
source. The same service can later expand into broader policy-enforced egress.

Deploy this before identity, Vault, HSM, or system-control hosts when those
hosts cannot reach approved package repositories directly. If you already have
direct egress, internal mirrors, Satellite-like services, or offline repos, use
those as the package-access prerequisite instead.

This is not a full offline mirror by itself. A fully disconnected environment
still needs mirrored or offline package content. The cache can sit in front of
that internal mirror or offline repo and give clients one controlled proxy
endpoint, but it cannot fetch packages that are not reachable somewhere
upstream.

## Default deployment

| Component | Terraform default | Inventory entry | Zone | Purpose |
| --- | --- | --- | --- | --- |
| caches | `cache-1`, `cache-2` active | present by default | `external_edge` | controlled outbound web access |
| extra cache nodes | commented examples | add matching inventory and IP entries | `external_edge` | horizontal scale or isolated policy sets |

The default is a pair. Add `cache-3` and higher when the environment needs more
horizontal capacity or separate egress policy sets.

## Service shape

| Service | Default role |
| --- | --- |
| `Squid` | serves the update/cache proxy on `cache_proxy_port` |
| `keepalived` | owns the shared cache VIP and fails it over between cache hosts |
| allowed CIDRs | defines which internal networks may use the cache |
| allowed domains | defines which external package/update domains are reachable |

## What you configure

| Path | What you configure |
| --- | --- |
| [`terraform/common.tfvars.example`](../../../terraform/common.tfvars.example) | `external_edge` network mapping, shared storage, template ID, and SSH keys |
| [`terraform/environments/cache/terraform.tfvars.example`](../../../terraform/environments/cache/terraform.tfvars.example) | cache VM count, size, storage, and tags |
| [`ansible/inventory/hosts.yml.example`](../../../ansible/inventory/hosts.yml.example) | `cache` host group |
| [`ansible/group_vars/all.yml.example`](../../../ansible/group_vars/all.yml.example) | shared hostname, domain, SSH, cache proxy VIP, and baseline defaults |
| [`ansible/group_vars/cache.yml.example`](../../../ansible/group_vars/cache.yml.example) | cache host IPs, VIP, keepalived router ID, allowed client CIDRs, allowed update domains, and optional upstream proxy |

## How other paths use it

Other paths can point restricted systems at the cache when they need approved
outbound update access. The cache path owns the hosts and base service policy;
consuming paths should only add their own allow-list or routing requirements
through documented variables.

Unlike identity or Vault, the cache does not always need one deployment per
environment. It is valid to run one shared production cache and let other
environment deployments use it for package access, as long as policy allows
those environments to share the same outbound path.

Deploy a separate cache per environment only when you need isolated egress
policy, isolated testing of the cache service itself, or an environment that
must not depend on production shared services.

This is intentional in the Ansible layout. Cache consumer settings live in
`all.yml` or `all.<env>.yml`, not only in the cache setup vars, so any setup can
use a cache that was deployed somewhere else.

For Enterprise Linux guests managed by this repo, set the shared cache VIP
before running package-installing paths:

```yaml
cache_proxy_vip_cidr: "<cache_proxy_vip>/<prefix>"
cache_proxy_name: cache
cache_proxy_fqdn: "{{ cache_proxy_name }}.{{ platform_domain }}"
cache_proxy_port: 3128
```

Put that value in `ansible/group_vars/all.yml` for production or in
`ansible/group_vars/all.<env>.yml` for a test, lab, or staging environment.
The cache path uses the same VIP for `keepalived`, and the baseline role
uses the derived `cache_proxy_url` before later roles install packages. You
normally set the VIP only; the default FQDN becomes `cache.<platform_domain>`.
Override `cache_proxy_name` or `cache_proxy_fqdn` when your DNS naming differs.
If an environment consumes a shared cache from another environment, set
`cache_proxy_fqdn` to that shared cache DNS name.

The URL should use the FQDN. If identity DNS is not online yet, the baseline
role can write a temporary `/etc/hosts` entry from `cache_proxy_vip_cidr` to
`cache_proxy_fqdn` before it configures DNF.

The cache hosts are the bootstrap exception. They do not use their own cache
VIP while Squid is being installed. Use direct egress, internal mirrors,
offline repos, or `cache_upstream_proxy_url` in `cache.yml` if the cache hosts
must chain through another proxy while being built.

For disconnected environments, point the cache at internal mirrors or offline
repository content. In that shape, clients are still isolated from direct
package sources, but the cache upstream is private instead of internet-facing.

Keep this boundary:

- the cache setup owns the cache hosts
- update sources and allow-lists should be explicit
- restricted systems should use the cache VIP as their package manager proxy
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
