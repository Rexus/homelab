# Proxy/cache inputs and behavior

Optional lookup for [Stage 1, Step 3](../03-deployment/stage-1-software-intake/README.md#step-3-configure-the-cache-deployment).
The [Stage 1 README](../03-deployment/stage-1-software-intake/README.md) is the complete installation path.
This page explains settings and behavior; it is not another deployment to perform.

**Working repository:** `<prefix>-tier-2` for cache inputs. Each consumer's owning tier selects its endpoint.
**Design:** [controlled software intake](../01-architecture/07-software-intake/README.md).

## Contents

- [Input locations](#input-locations)
- [Service and transport](#service-shape)
- [Cache storage](#cache-storage)
- [Sizing and throttling](#sizing-and-throttling)
- [Consumer settings](#how-other-paths-use-it)
- [Verification and failures](#consumer-verification-and-failure-behavior)
- [Update an existing cache](#update-an-existing-cache)
- [Security events](#security-events)
- [Automatic validation](#validation)

<a id="cache-path"></a>
<a id="purpose"></a>
<a id="configuration"></a>
<a id="what-you-configure"></a>
<a id="plan-and-deploy"></a>
<a id="default-deployment"></a>

## Input locations

| File or source | Owns |
| --- | --- |
| Tier 2 `terraform/deployments/cache/terraform.tfvars` | Guest names, hardware, storage class and attached `scsi1` cache disks |
| Tier 2 `ansible/group_vars/cache.yml` | Host IPs, VIP, client/source policy, storage and validation settings |
| Tier 2 `ansible/roles/cache_proxy/defaults/main.yml` | Complete role defaults and optional settings |
| Shared `config/platform.tfvars` | Logical storage classes and default placement |
| Shared `config/guest-sizes.json` | VM size-profile definitions |

[Terraform examples](../../tier-2/terraform/deployments/cache/terraform.tfvars.example),
[cache inputs](../../tier-2/ansible/group_vars/cache.yml.example) and
[role defaults](../../tier-2/ansible/roles/cache_proxy/defaults/main.yml) are the maintained definitions.
Configure and deploy through [Stage 1, Steps 2 to 5](../03-deployment/stage-1-software-intake/README.md#step-2-initialize-cache-inputs).

## Service shape

| Component | Contract |
| --- | --- |
| Squid | Explicit repository proxy on `cache_squid_http_port`; scoped clients and source hostnames |
| keepalived | One active owner of the VIP; failover, not active-active load balancing |
| Cache disks | Independent rebuildable data on each cache VM; no content replication between peers |
| Firewall | Proxy and VRRP rules are managed when guest firewalld is active; network bypass denial remains separate |
| Health check | `cache_squid_check_script_path` runs from `/usr/libexec/keepalived` |

An empty domain list is rejected: there is no unrestricted client fallback.
Client CIDRs are explicit; the role supplies no all-private-network default.
Loopback/link-local destinations are denied apart from the local cache-manager interface.

## Transport limits

The internal listener uses HTTP proxy protocol. HTTPS destinations use encrypted CONNECT tunnels:
these are **not cached** or scanned. Plain HTTP responses may be cached; a tunnel success is not a cache hit.
The supplied installer is an explicit proxy, not a transparent/intercepting proxy.
For authenticated or TLS/mTLS proxy listeners, select a separately reviewed implementation.
See [transport and integrity](../01-architecture/07-software-intake/README.md#transport-and-integrity) for trust choices.

A leading dot in an allowed domain includes its subdomains. Include approved CDN/redirect targets deliberately;
shared domains such as GitHub permit more than one project. IP URLs do not gain permission through reverse DNS.
Keep publisher signature and digest checks enabled independently of the proxy.

## Cache storage

`storage_class = "local"` selects Shared's logical class, not a datastore literally called `local`.
Its `vm_disk` must support VM images; see [storage mapping](platform-inputs.md#vm-disk-storage).
The mapping applies to OS, cache and inherited CloudInit storage. Use the
[partial-apply contract](repository-scripts.md#partial-terraform-apply) after a failed clone or disk move.

The reference attaches `scsi1` separately from the OS disk. Its default guest identity is
`/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1`; verify that link for an existing deployment.
Linux disk letters can differ between clones. Shared's guarded volume role rejects an OS/partitioned
disk, foreign mount or hidden target data before stopping Squid or creating a filesystem. It initializes
only an undeclared signature-free disk, preserves accepted existing filesystems and persists mounts by UUID
at `cache_squid_cache_dir`, normally `/var/spool/squid`. Data mounts include `nodev,nosuid,noexec`.
Growing a cache means enlarging its Proxmox disk first, then allowing the role to grow the mounted XFS filesystem.
Shrinking is not automated.

| Setting | Purpose |
| --- | --- |
| `vm_instances.<cache>.extra_disks[*].size_gb` | Attached Proxmox data-disk capacity |
| `cache_squid_data_device` | Guest device selected for the cache filesystem |
| `cache_squid_data_uuid` | Optional expected UUID for an existing cache filesystem |
| `cache_squid_cache_dir` | Persistent mount and Squid cache directory |
| `cache_squid_cache_mb` | Squid cache allocation; keep below available filesystem capacity |
| `cache_squid_cache_dir_type` | Portable `ufs` by default; use `aufs` only when the installed package supports it |

Local SSD/NVMe is the normal starting point for hot, rebuildable cache data. Retain replicated storage for
requirements that justify its capacity/write cost. A failed node normally refills its cache after rebuilding;
shared storage is a selected policy/capacity alternative, not required cache replication.
Validate changed Squid options with the role's `squid -k parse` gate.

## Sizing and throttling

The [Shared profiles](../../shared/config/guest-sizes.json) define CPU/RAM; the Terraform/cache examples define
initial disk and Squid allocations. They are starting inputs, not measured client-capacity guarantees.
Size each active endpoint from observed IO, concurrency, memory and object reuse.

| Symptom | Review |
| --- | --- |
| Disk fills | `extra_disks[*].size_gb` and `cache_squid_cache_mb` |
| High disk latency/IO wait | Local storage latency, cache device and filesystem |
| Concurrent clients stall | vCPU, `cache_squid_limit_nofile` and storage throughput |
| Repeated HTTP downloads miss | Source policy, response cacheability and `cache_squid_refresh_patterns` |
| One active endpoint is saturated | Another VIP/policy group or explicitly qualified endpoint balancing |

Keep `cache_squid_max_object_size` suitable for selected HTTP artifacts and `cache_squid_range_offset_limit: -1`
for ranged/resumable downloads. Increase disk capacity, then CPU/RAM where measured demand requires it.
Add cache instances by extending the tier-owned VM map, inventory and IP map together.
Never force caching through expiry/privacy/reload overrides; repository metadata has no heuristic freshness extension. [2]

## How other paths use it

Each consumer selects `repository_proxy_enabled`, `repository_proxy_url` and optionally
`repository_proxy_fqdn` in its own `ansible/group_vars/all.yml` or `all.<env>.yml`.
Use `repository_proxy_ip` only for a temporary hosts entry before independent DNS works;
consumer URLs contain no subnet prefix. Follow [bootstrap Step 6](../03-deployment/stage-1-software-intake/step-6-bootstrap-consumer.md)
and the [Proxmox host procedure](../05-operations/02-software-intake/host-updates.md) for existing hosts.

| Consumer | Behavior |
| --- | --- |
| DNF/APT | Persistent native package-manager proxy settings |
| Shell | `baseline_manage_shell_proxy` follows proxy selection by default; existing terminals need the documented activation |
| Ansible downloads | Explicit task proxy environment, independent of login-shell state [1] |
| Other tools, registries and clusters | Their selected native proxy/repository settings; a shell proxy is not universal configuration |

Shared's baseline manages DNF through an INI-aware module and APT through an owned template.
Package verification policy also applies without a proxy.
No cache-to-Tier-0 management rule or update push is required; Tier 0 initiates retrieval.
Enforce direct-WAN bypass denial through the
[firewall contract](../01-architecture/05-networking/01-firewall-policy.md#rule-contracts), then test it.

Cache hosts build the service: retain `repository_proxy_enabled: false` in `cache.yml`, or use a different
accepted upstream proxy. They cannot install through their own unfinished VIP.
Disconnected use needs retained reachable mirror/repository content; an empty cache creates no route across an air gap.

## Consumer verification and failure behavior

| Result | Required handling |
| --- | --- |
| HTTP/CONNECT denial | Review destination/client scope; never bypass the policy |
| Proxy/source outage | Stop; no silent direct-WAN retry |
| APT refresh error | Stop before upgrades; strict refresh must accept every enabled source |
| Invalid signature/digest | Reject content; preserve verification |
| DNF required repository unavailable | Fail refresh; do not accept a partial source set |
| Artifact not approved by staged intake | Keep the accepted release; the proxy supplies no quarantine verdict |

[Package-policy tasks](../../shared/ansible/roles/baseline/tasks/package_policy.yml) and the
[Proxmox host role](../../tier-0/ansible/roles/proxmox_host/tasks/main.yml) apply native defaults.
Review repository-specific overrides: DNF `gpgcheck=1`, `sslverify=1`, `skip_if_unavailable=False`,
and `repo_gpgcheck=1` only where signed metadata exists. APT retains its approved `Signed-By` key
without `trusted=yes` or insecure overrides. Publisher verification is not malware scanning. [3][4]

## Update an existing cache

Use [Stage 1 option 2b](../03-deployment/stage-1-software-intake/step-2b-adopt-update.md#3-reconcile-the-existing-cache).
That guide owns refresh, retained-policy review, reconciliation and consumer revalidation.

## Security events

Squid emits JSON Lines at `/var/log/squid/access.log`: timestamp, client IP, destination domain, method,
HTTP status, proxy result and error code. URL 06-paths/queries, headers and credentials are omitted. [5]
`TCP_DENIED` records an access decision; CONNECT success is not scanning or package approval.
Keep diagnostics restricted separately; they are not the sanitized event interface.

After Stage 2 is accepted, commission each cache's streams through the
[logging-source procedure](../03-deployment/stage-2-logging/procedures/sources.md).
In the owning Tier 2 `ansible/host_vars/<host>.yml`, retain its security journal and add its proxy file stream:

```yaml
log_forwarder_streams:
  - {name: cache-1-os, kind: security, input: journal}
  - name: cache-1-proxy
    kind: security
    input: files
    files: [/var/log/squid/access.log]
```

Use the matching host number and existing per-stream certificates, queues and receiver registration.
The cache installer creates no logging authority. Keep local records until enrollment;
later OpenSearch reads only approved copies and is not an update-access dependency.

## Validation

[Stage 1, Step 5](../03-deployment/stage-1-software-intake/README.md#step-5-test-the-selected-intake-path)
owns manual acceptance from permitted/forbidden source networks: approved retrieval,
unapproved-destination denial, direct-WAN denial and HTTP cache-hit checks when caching is selected.
Acceptance requires that direct WAN bypass fails.

| Automatic phase | Actual check |
| --- | --- |
| Before baseline | Every guest accepts SSH; each cache can reach `cache_validation_url` upstream |
| Each cache host | Local proxy accepts an approved request and denies an unapproved destination |
| After configuration | Exactly one VIP owner; proxy port reachable from cache hosts |
| Selected failover test | Stop keepalived on its owner, verify takeover, restart the original owner |
| Deployment-host validation | VIP port and approved request by IP, denied destination; report FQDN failures |

`cache_validation_url` must be allowed by the source policy; use an internal URL for disconnected supply.
`cache_validation_failover_enabled: false` skips the temporary keepalived takeover test only.
The deployment host needs proxy access to the VIP; direct proxy access to each node is not required.
The failover test checks VIP reachability from the cache hosts, not from each consumer network.
No cache disks need clearing for a policy update. The guest connection wait covers a fresh clone's sshd startup.

<a id="read-more"></a>

## References

1. [Ansible native downloads](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/get_url_module.html)
   and [task environment](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_environment.html).
2. [Squid freshness controls](https://www.squid-cache.org/Doc/config/refresh_pattern/), checked 2026-11-10.
3. [DNF verification defaults](https://dnf.readthedocs.io/en/latest/conf_ref.html), checked 2026-11-10.
4. [APT repository authentication](https://manpages.debian.org/trixie/apt/apt-secure.8.en.html), checked 2026-11-10.
5. [Squid structured log fields](https://www.squid-cache.org/Doc/config/logformat/), checked 2026-11-10.
