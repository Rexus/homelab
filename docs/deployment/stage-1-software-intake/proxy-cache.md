# Proxy/cache policy and sizing

**Working repository:** `<prefix>-tier-2` (source: `tier-2/`).
Run repository scripts from this root; paths below are repository-relative.

<a id="cache-path"></a>

**Prerequisites:** accepted VM/network prerequisites and independent bootstrap software access.
**Capability:** [Software intake](README.md).
**Return:** [Step 5: intake testing](README.md#step-5-test-the-selected-intake-path)
after proxy deployment and validation.

**Design:** [controlled software intake](../../architecture/software/software-intake.md).

## Contents

- [Configuration and deployment](#configuration)
- [Service and transport](#service-shape)
- [Cache storage](#cache-storage)
- [Sizing](#sizing-and-throttling)
- [Consumer behavior](#how-other-paths-use-it)
- [Consumer verification and failures](#consumer-verification-and-failure-behavior)
- [Update an existing cache](#update-an-existing-cache)
- [Security events](#security-events)
- [Validation](#validation)

Installation is part of the [Stage 1 main path](README.md), including the files to edit,
the deployment command and the existing-supply alternative. This page owns the policy,
storage and tuning reference.

## Purpose

The ordinary outbound proxy/cache belongs to Tier 2 / DMZ. It forwards approved
requests and holds rebuildable cache data, not authoritative software releases
or Tier 0 credentials. Authoritative mirrors remain Tier 1; bootstrap/recovery
must retain an approved supply path independent of this optional cache.

Use this path to deploy a shared cache pair for systems that need controlled
outbound repository and update access.

The reference implementation is `Squid` with `keepalived`. The first use case
is allowing connected, restricted systems to reach approved software
sources without building full internal mirrors for every operating system,
package source, Git remote, or registry endpoint. The same service can later
expand into broader policy-enforced egress.

Deploy this before identity, the secret platform, HSM, or system-control hosts when those
hosts cannot reach approved software repositories directly. With existing
direct egress, internal mirrors, Satellite-like services, or offline
repos, use those as the repository-access prerequisite instead.

This is not a full offline mirror by itself. A fully disconnected environment
still needs mirrored or offline repository content. The cache can sit in front
of that internal mirror or offline repo and give clients one controlled proxy
endpoint, but it cannot fetch content that is not reachable somewhere
upstream.

## Default deployment

The [capability deployment view](README.md#step-4-deploy-the-cache-pair)
owns the source-backed figure. The settings below configure those same guests and disks.

| Component | Terraform default | Inventory entry | Network / storage | Purpose |
| --- | --- | --- | --- | --- |
| caches | `cache-1`, `cache-2` active | present by default | `external_edge` | controlled outbound web access |
| cache data disks | one `scsi1` data disk per cache VM | mounted by Ansible | VM local/shared storage | Squid cache data |
| extra cache nodes | commented examples | add matching inventory and IP entries | `external_edge` | extra failover members, separate VIPs, or isolated policy sets |

The default is a pair behind one keepalived VIP. That is an HA endpoint, not
active-active load balancing. Add `cache-3` and higher for extra failover
members, or add separate VIPs/policy groups for true horizontal
capacity.

The example selects Linux/Proxmox acquisition sources, not general web access.
Replace client CIDRs and source domains with the actual site policy. Include approved mirror/CDN
redirect destinations deliberately; multi-tenant domains such as GitHub are broader than one project.
Add later registry sources when their capability is commissioned. Prefer exact source hostnames;
a leading dot allows a domain and all of its subdomains. IP URLs do not gain permission by reverse DNS.

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

<a id="hardening-todo"></a>

## Transport limits

The default proxy listener is HTTP on an internal, restricted network. That is
normal for repository proxy use: clients speak HTTP proxy protocol to Squid,
while HTTPS destinations still use CONNECT tunnels and remain encrypted to the
upstream site.

The supplied configuration uses CIDR/domain restrictions, not authenticated clients
or a TLS/mTLS proxy listener. Select another reviewed configuration when those are required.

CONNECT tunnels are forwarded, **not cached**. Plain HTTP responses may be cached;
transparent routing alone does not make HTTPS payloads visible. The supplied recipe
is an explicit proxy, not a transparent/intercepting proxy. Internal HTTP mirrors
are a separate [transport choice](../../architecture/software/software-intake.md#transport-and-integrity),
not a reason to disable public-source TLS or package verification.

Avoid TLS interception by default. It changes end-to-end trust and should only
be introduced with an explicit policy, internal CA rollout, and audit model.

<a id="what-you-configure"></a>

## Configuration

Follow [Stage 1, Step 1](README.md#step-1-prepare-the-cache-inputs) to initialize and edit
Shared references and Tier 2 inputs. Guest names, IPs and inventory stay Tier 2-owned.
The recipe uses Tier 2's [cache_proxy role](../../../tier-2/ansible/roles/cache_proxy);
Shared's [deploy helper](../../../shared/scripts/deploy.sh) executes it with local inputs.

An empty or whitespace-only domain list is rejected; there is no unrestricted
client fallback. Keep independent bootstrap software access for the cache hosts.
Local proxy requests use the same destination policy. Loopback/link-local destinations are denied,
apart from the local cache-manager interface. Client CIDRs are required; the role has no all-private-network default.

## Plan and deploy

Run the [Stage 1 deployment command](README.md#step-2-deploy-the-selected-intake-path).
It displays the Terraform plan and asks for confirmation before configuring the service.
Use `--plan-only` for an optional preview; `--auto-approve` is available for approved CI jobs.

## Cache storage

`storage_class = "local"` selects Shared's `proxmox_storage_classes.local`, not a
datastore literally named `local`. Set its `vm_disk` to an existing VM-image store,
such as `local-zfs`; see [VM disk storage](../../reference/platform-inputs.md#vm-disk-storage).
The mapping applies to the OS disk, extra cache disk and, unless overridden, CloudInit.
After a failed clone or disk move, follow the
[partial-apply contract](../../reference/repository-scripts.md#partial-terraform-apply).

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
`cache_squid_data_device` in `cache.yml` if the template exposes the disk under
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

The example uses the portable Squid `ufs` cache directory type. If the
installed Squid package supports `aufs`, it can be a better fit for busy local
SSD/NVMe caches. Change `cache_squid_cache_dir_type` only after testing the
generated config with the role's `squid -k parse` validation.
Source privacy, expiry and client reload instructions remain effective. Package/image extensions
do not force a cache entry. Repository metadata has no heuristic freshness extension. [2]

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

Keep `maximum_object_size` large enough for the selected HTTP artifacts. Keep `range_offset_limit -1` enabled for
resumable and ranged downloads.

Expansion usually follows this order:

1. Increase the local cache disk and `cache_squid_cache_mb` when capacity is
   the bottleneck.
2. Increase vCPU/RAM and keep the cache on local NVMe/SSD when concurrency is
   the bottleneck.
3. Add another cache VIP or policy group when one active proxy endpoint is
   saturated.

## How other paths use it

The cache setup owns its hosts. Consumers select the accepted endpoint in their own tier's
`ansible/group_vars/all.yml`, or `all.<env>.yml` for a different environment policy:

```yaml
repository_proxy_enabled: true
repository_proxy_fqdn: "cache.{{ platform_domain }}"
repository_proxy_url: "http://{{ repository_proxy_fqdn }}:3128"
```

Set `repository_proxy_ip` only when a temporary hosts entry is needed before independent DNS
resolves the FQDN. The role derives the VIP IP from `cache_proxy_vip_cidr`; consumer URLs contain
no subnet prefix. Follow the [bootstrap](bootstrap-consumer.md) and
[Proxmox host](../../administration/hosts/update-access.md) procedures for existing hosts.

| Consumer setting / behavior | Contract |
| --- | --- |
| `repository_proxy_enabled` and URL | Enable persistent DNF/APT proxy configuration; disabled/unset inputs do not create a route |
| `baseline_manage_shell_proxy` | Defaults to following repository proxy selection; set false for package-manager-only configuration |
| Login shell profile | New sessions load `/etc/profile.d/`; existing sessions need the documented activation step |
| Ansible artifact downloads | Native download tasks use the explicit proxy environment; they do not inherit an interactive shell profile [1] |
| Tool, registry and cluster clients | Use their selected native settings; a shell proxy is not universal client configuration |
| Another environment | Reuse accepted supply when policy permits; deploy another cache only for an actual isolation/capacity requirement |

Shared's baseline uses an INI-aware module for DNF and an owned APT proxy template. Its separate
package-policy tasks also apply without a proxy. No cache-to-Tier-0 management rule or update push
is required: Tier 0 initiates retrieval and installation. A mirror-only policy needs commissioned
repository endpoints; this role does not create mirrors or per-tier destination lists.
The [firewall contract](../../architecture/networking/firewall-policy.md#rule-contracts) must deny
bypass separately. Proxy configuration alone does not enforce egress.

Cache hosts are the bootstrap exception: keep `repository_proxy_enabled: false` in `cache.yml`
while building their own service. If initial acquisition uses another approved proxy, select that
upstream, never their own VIP. A disconnected site needs retained, reachable internal content;
an empty cache is insufficient and creates no route across an air gap.

## Consumer verification and failure behavior

| Consumer result | Required action |
| --- | --- |
| HTTP/CONNECT policy denial | Stop; review the destination and client scope rather than bypassing the proxy |
| Proxy or source outage | Stop; no silent direct-WAN retry |
| APT repository refresh error | Stop before upgrading; strict refresh must succeed for every enabled source |
| Invalid publisher signature / digest | Reject the content; do not disable verification |
| DNF unavailable required repository | Fail the refresh; do not treat a partial repository set as accepted |
| Artifact not published by a staged source | Keep the selected approved release; the proxy does not know a quarantine verdict |

Shared's [package-policy tasks](../../../shared/ansible/roles/baseline/tasks/package_policy.yml) and the
[Proxmox host recipe](../../../tier-0/ansible/roles/proxmox_host/tasks/main.yml) configure native verification defaults.
DNF repository overrides still take precedence; review enabled `.repo` files for `gpgcheck=1`,
`sslverify=1` and `skip_if_unavailable=False`. Enable `repo_gpgcheck=1` only for sources publishing
signed metadata. APT sources must retain their approved `Signed-By` key and must not use
`trusted=yes` or insecure overrides. This is publisher verification, not malware scanning. [3][4]

## Update an existing cache

1. [Refresh the collection](../../development/generated-repositories.md#refresh-and-local-ownership),
   then edit **`<prefix>-tier-2/ansible/group_vars/cache.yml`**.
   Local configuration is preserved. Narrow `cache_squid_allowed_cidrs` and `cache_squid_allowed_domains`,
   and replace the old `cache_squid_refresh_patterns` with the current example's list.
   Remove expiry/privacy/reload override options; the precheck rejects them. Review raw
   `cache_squid_extra_options` too, because they can alter the generated policy.
2. Reconcile the existing VMs from **`<prefix>-tier-2/`**:

   ```bash
   bash scripts/deploy.sh cache --ansible-only
   ```

3. Require approved retrieval, denied destination and VIP validation to pass. Repeat the checks
   below from each consumer network. Do not clear cache disks or recreate VMs for this policy change.
   Reapply bootstrap/Proxmox consumer recipes to install the updated native package policy.

## Security events

Squid writes JSON lines to `/var/log/squid/access.log`: timestamp, client IP, destination domain,
method, HTTP status, proxy result and error code. It omits URL paths/queries, headers and user credentials.
`TCP_DENIED` is an access decision; a tunnel success is not a scan verdict or package approval. [5]
Keep Squid diagnostics restricted separately; diagnostic files are not a sanitized event interface.

Once Stage 2 exists, follow [logging-source commissioning](../stage-2-logging/sources.md) for
each cache host. In **that host's Tier 2 `ansible/host_vars/<host>.yml`**, add this stream alongside
its security journal, with the matching host number:

```yaml
log_forwarder_streams:
  - {name: cache-1-os, kind: security, input: journal}
  - name: cache-1-proxy
    kind: security
    input: files
    files: [/var/log/squid/access.log]
```

Use the existing per-stream certificate/queue/receiver registration procedure; the cache installer
does not create logging trust. Retain local records before that commissioning. Later OpenSearch
uses approved read-only copies; update access and enforcement do not depend on its availability.

## Validation

Before accepting the path, test from each permitted consumer network: an approved
download succeeds, an unapproved destination is denied, and direct WAN bypass fails.
Test from a forbidden source as well. For HTTP caching, repeat a cacheable object
request and inspect Squid's access log; a successful HTTPS tunnel is not a cache hit.
Remove temporary bootstrap WAN exceptions only after the selected supply works.

The cache playbook waits for every cache host to accept an Ansible connection
before the baseline play gathers facts. This covers the normal fresh-clone
window where the guest already has its IP address but sshd is not ready yet.

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
`cache_validation_failover_enabled: false` only to skip the
temporary keepalived failover test.

For a manual proxy check from the deployment host, use lowercase `-x` or
`--proxy`:

Run on **the selected approved consumer host**.

```bash
curl -x "http://<cache-ip>:3128" -I "https://mirrors.fedoraproject.org/"
```

Keep this boundary:

- the cache setup owns the cache hosts
- software sources and allow-lists should be explicit
- restricted systems should use the cache VIP as their repository proxy
- air-gapped systems need a custody-local cache with transferred content, never a route across the air gap
- more cache nodes are added by extending `vm_instances`, inventory, and IP map

For Linux package managers managed by this repo, cache use is persistent
package-manager configuration applied by the baseline role, not a temporary
environment setting that only exists during one Ansible task.

## Read more

- [Shared services path](../../reference/implementation-support.md)
- [Using the cache from Proxmox](../../administration/hosts/update-access.md)
- [Network architecture](../../architecture/networking/README.md)
- [Security principles](../../architecture/principles.md)

## References

1. [Ansible native download proxy behavior](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/get_url_module.html)
   and [task environment](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_environment.html).
2. [Squid freshness controls](https://www.squid-cache.org/Doc/config/refresh_pattern/), checked 2026-11-10.
3. [DNF verification and repository defaults](https://dnf.readthedocs.io/en/latest/conf_ref.html), checked 2026-11-10.
4. [APT repository authentication](https://manpages.debian.org/trixie/apt/apt-secure.8.en.html), checked 2026-11-10.
5. [Squid structured log fields](https://www.squid-cache.org/Doc/config/logformat/), checked 2026-11-10.
