# Cache path

## Purpose

Use this path to deploy a shared cache pair for systems that need controlled
outbound web access.

The reference implementation is `Squid`. A common use case is allowing
restricted or air-gapped systems to reach approved update sources without
building full internal mirrors for every operating system and package source.

## Default deployment

| Component | Terraform default | Inventory entry | Zone | Purpose |
| --- | --- | --- | --- | --- |
| caches | `cache-1`, `cache-2` active | present by default | `external_edge` | controlled outbound web access |
| extra cache nodes | commented examples | add matching inventory and IP entries | `external_edge` | horizontal scale or isolated policy sets |

The default is a pair. Add `cache-3` and higher when the environment needs more
horizontal capacity or separate egress policy sets.

## What you configure

| Path | What you configure |
| --- | --- |
| [`terraform/common.tfvars.example`](../../../terraform/common.tfvars.example) | `external_edge` network mapping, shared storage, template ID, and SSH keys |
| [`terraform/environments/cache/terraform.tfvars.example`](../../../terraform/environments/cache/terraform.tfvars.example) | cache VM count, size, storage, and tags |
| [`ansible/inventory/hosts.yml.example`](../../../ansible/inventory/hosts.yml.example) | `cache` host group |
| [`ansible/group_vars/all.yml.example`](../../../ansible/group_vars/all.yml.example) | cache host IP addresses |

## How other paths use it

Other paths can point restricted systems at the cache when they need approved
outbound update access. The cache path owns the hosts and base service policy;
consuming paths should only add their own allow-list or routing requirements
through documented variables.

Keep this boundary:

- the cache setup owns the cache hosts
- update sources and allow-lists should be explicit
- air-gapped systems should use the cache only when policy allows it
- more cache nodes are added by extending `vm_instances`, inventory, and IP map

## Read more

- [Shared services path](README.md)
- [Network architecture](../../architecture/network.md)
- [Security principles](../../security/security-principles.md)
