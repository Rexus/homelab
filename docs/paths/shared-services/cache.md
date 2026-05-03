# Cache path

## Purpose

Use this path to deploy a shared cache pair for systems that need controlled
outbound web access.

The reference implementation is `Squid` with `keepalived`. The first use case
is allowing restricted or air-gapped systems to reach approved update sources
without building full internal mirrors for every operating system and package
source. The same service can later expand into broader policy-enforced egress.

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
| `Squid` | serves the update/cache proxy on port `3128` |
| `keepalived` | owns the shared cache VIP and fails it over between cache hosts |
| allowed CIDRs | defines which internal networks may use the cache |
| allowed domains | defines which external package/update domains are reachable |

## What you configure

| Path | What you configure |
| --- | --- |
| [`terraform/common.tfvars.example`](../../../terraform/common.tfvars.example) | `external_edge` network mapping, shared storage, template ID, and SSH keys |
| [`terraform/environments/cache/terraform.tfvars.example`](../../../terraform/environments/cache/terraform.tfvars.example) | cache VM count, size, storage, and tags |
| [`ansible/inventory/hosts.yml.example`](../../../ansible/inventory/hosts.yml.example) | `cache` host group |
| [`ansible/group_vars/all.yml.example`](../../../ansible/group_vars/all.yml.example) | cache host IP addresses |
| [`ansible/group_vars/cache.yml.example`](../../../ansible/group_vars/cache.yml.example) | VIP, keepalived router ID, allowed client CIDRs, allowed update domains, and optional upstream proxy |

## How other paths use it

Other paths can point restricted systems at the cache when they need approved
outbound update access. The cache path owns the hosts and base service policy;
consuming paths should only add their own allow-list or routing requirements
through documented variables.

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
