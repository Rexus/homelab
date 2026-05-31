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
| extra cache nodes | commented examples | add matching inventory and IP entries | `external_edge` | extra failover members, separate VIPs, or isolated policy sets |

The default is a pair behind one keepalived VIP. That is an HA endpoint, not
active-active load balancing. Add `cache-3` and higher for extra failover
members, or add separate VIPs/policy groups when you need true horizontal
capacity.

The example allow-list is intentionally broad enough to cover common Linux
repos, Proxmox/Ceph sources, GitHub-hosted projects, HashiCorp tooling,
container registries, and Windows update endpoints. Treat it as a starting
policy and remove domains your environment does not need.

The Ansible role is written for Linux guests with systemd and supports
Red Hat-family/Fedora and Debian-family package managers. Rocky and Alma are
the reference feedback distros for the current cache path.

## Service shape

| Service | Default role |
| --- | --- |
| `Squid` | serves the repository/cache proxy on `cache_proxy_port` |
| `keepalived` | owns the shared cache VIP and fails it over between cache hosts |
| firewalld | opens the proxy port and keepalived VRRP when firewalld is active; reloads only when rules change |
| health check | keepalived runs `cache_squid_check_script_path` from `/usr/libexec/keepalived` |
| allowed CIDRs | defines which internal networks may use the cache |
| allowed domains | defines which external software-source domains are reachable |

## Hardening TODO

The default proxy listener is HTTP on an internal, restricted network. That is
normal for repository proxy use: clients speak HTTP proxy protocol to Squid,
while HTTPS destinations still use CONNECT tunnels and remain encrypted to the
upstream site.

Future hardening work can add:

- authenticated proxy access
- TLS on the client-to-proxy listener
- mTLS for selected high-security zones
- separate proxy pairs per security zone or policy boundary

Avoid TLS interception by default. It changes end-to-end trust and should only
be introduced with an explicit policy, internal CA rollout, and audit model.

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

Prefer local NVMe or local SSD storage for the cache data disk. Squid cache data
is hot, noisy, and rebuildable; it does not need replicated Ceph storage by
default, even when the Proxmox cluster has a Ceph NVMe pool. Using local storage
keeps replicated storage capacity and write amplification for data that must
survive a host failure.

Use shared or replicated storage only when policy explicitly requires it, for
example when cache warmness is more important than storage efficiency or when
local disks are not available. The normal recovery model is to fail over to the
other cache node and let the rebuilt node refill its local cache.

The example uses `/dev/sdb` because a Linux VM with one OS disk and one extra
`scsi1` disk often discovers the extra disk there. Change
`cache_squid_data_device` in `cache.yml` if your template exposes the disk under
a different stable device path.

For existing cache VMs, Terraform plans hardware changes and Ansible converges
the guest. Growing the extra cache disk should expand the Proxmox disk first;
the cache role then grows the mounted XFS filesystem when it detects more
device space. Shrinking disks is not automated.

Tune both sides together:

| Setting | Purpose |
| --- | --- |
| `vm_instances.<cache>.extra_disks[*].size_gb` | Proxmox data disk size |
| `cache_squid_data_device` | guest device to format and mount |
| `cache_squid_cache_dir` | mount point and Squid cache directory |
| `cache_squid_cache_mb` | Squid cache size inside that mounted filesystem |

The example uses the portable Squid `ufs` cache directory type. If your
installed Squid package supports `aufs`, it can be a better fit for busy local
SSD/NVMe caches. Change `cache_squid_cache_dir_type` only after testing the
generated config with the role's `squid -k parse` validation.

## Sizing and throttling

Start small and scale the cache where the bottleneck appears. Cache data is
rebuildable, so capacity and throughput matter more than replication.

| Size profile | VM shape | Cache disk | Active clients | `cache_squid_cache_mem` | Use case |
| --- | --- | --- | --- | --- | --- |
| `tiny-mem` | 1 vCPU, 4 GB RAM | 100-250 GB local NVMe/SSD | about 10-25 | 512-1024 MB | small test cache, single-site experiments |
| `small-mem` | 2 vCPU, 8 GB RAM | 200-500 GB local NVMe/SSD | about 25-100 | 1024-2048 MB | small homelab, first HA pair, package updates |
| `medium-mem` | 4 vCPU, 16 GB RAM | 1-2 TB local NVMe/SSD | about 100-500 | 4096 MB | several networks, more clients, template and image pulls |
| `large-mem` | 8 vCPU, 32 GB RAM | 2+ TB or multiple local NVMe devices | about 500-2000+ | 8192 MB | heavy enterprise update egress or many parallel pulls |

Do not overallocate memory to Squid. Disk cache size and storage latency are
usually more important for repository, package, and image traffic.

Scale based on symptoms:

| Symptom | First action |
| --- | --- |
| cache disk fills quickly | increase `extra_disks[*].size_gb` and `cache_squid_cache_mb` |
| high disk latency or IO wait | move the cache disk to local NVMe/SSD |
| many simultaneous clients stall | increase vCPU, `cache_squid_limit_nofile`, and keep local NVMe |
| repeated downloads miss cache | review `cache_squid_allowed_domains` and `cache_squid_refresh_patterns` |
| one proxy pair is saturated | add another cache VIP/pair, load-balance multiple endpoints, or split policy zones |

Keep `maximum_object_size` large enough for ISO, cloud-image, Windows update,
and container-layer payloads. Keep `range_offset_limit -1` enabled for
resumable and ranged downloads.

Expansion usually follows this order:

1. Increase the local cache disk and `cache_squid_cache_mb` when capacity is
   the bottleneck.
2. Increase vCPU/RAM and keep the cache on local NVMe/SSD when concurrency is
   the bottleneck.
3. Add another cache VIP or policy group when one active proxy endpoint is
   saturated.

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

The repository proxy is opt-in for consumers. If `repository_proxy_enabled` is
false or `repository_proxy_url` is unset, the baseline role does not configure
a proxy. Any setup can opt out of a shared proxy by setting
`repository_proxy_enabled: false` in that setup's group vars file.

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

For managed Linux guests, enable only the repository proxy consumer values in
`all.yml` or `all.<env>.yml` before running paths that need controlled
software-source access:

```yaml
repository_proxy_enabled: true
repository_proxy_fqdn: "cache.{{ platform_domain }}"
repository_proxy_url: "http://{{ repository_proxy_fqdn }}:3128"
repository_proxy_ip: "<cache_proxy_vip>"
```

Managed Linux hosts use the `repository_proxy` baseline task when
`repository_proxy_enabled` is true and `repository_proxy_url` is set. By
default it writes package-manager proxy configuration for the host OS. Red
Hat-family hosts use an INI-aware Ansible module for `/etc/dnf/dnf.conf`;
Debian-family hosts get an owned APT template under `/etc/apt/apt.conf.d/`.

Package tasks then use the host package-manager configuration instead of
temporary Ansible task environment variables. That keeps repository egress as a
real host setting, which is easier to inspect and also works after the
deployment run.

Shell proxy profiles under `/etc/profile.d/` are handled by a separate baseline
task, but they follow `repository_proxy_enabled` by default. That means admins
and users who log in get `http_proxy`, `https_proxy`, and `no_proxy` without
editing individual `.bashrc` files. Set `baseline_manage_shell_proxy: false`
when a setup should configure package managers only.

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

When validation is enabled, each cache host first tests that it can reach
`cache_validation_url` directly. After the cache role finishes, the cache hosts
verify that exactly one node owns the VIP and that the VIP proxy port is
reachable from the cache network. When failover validation is enabled and at
least two cache hosts are present, the cache hosts stop keepalived on the
current VIP owner, verify that another host takes over, and then restart
keepalived on the original owner. The deployment-host validation then tests
each cache node proxy port, tests each cache node as a proxy, tests the cache
VIP by IP, and warns if the expected cache FQDN does not work.

Set `cache_validation_url` to a URL allowed by `cache_squid_allowed_domains`.
The default example uses `https://mirrors.fedoraproject.org/` because it is a
neutral mirror redirector and aligns with Fedora/EPEL repository access. For
disconnected environments, point it at an internal mirror or offline repo
endpoint reachable through the cache path. Set
`cache_validation_failover_enabled: false` only when you want to skip the
temporary keepalived failover test.

For a manual proxy check from the deployment host, use lowercase `-x` or
`--proxy`:

```bash
curl -x "http://<cache-ip>:3128" -I "https://mirrors.fedoraproject.org/"
```

Keep this boundary:

- the cache setup owns the cache hosts
- software sources and allow-lists should be explicit
- restricted systems should use the cache VIP as their repository proxy
- air-gapped systems should use the cache only when policy allows it
- more cache nodes are added by extending `vm_instances`, inventory, and IP map

For Linux package managers managed by this repo, cache use is persistent
package-manager configuration applied by the baseline role, not a temporary
environment setting that only exists during one Ansible task.

## Read more

- [Shared services path](README.md)
- [Using the cache from Proxmox](../../platforms/proxmox/cache-usage.md)
- [Network architecture](../../architecture/network.md)
- [Security principles](../../security/security-principles.md)
