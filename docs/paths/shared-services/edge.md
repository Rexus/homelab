# Edge proxy path

## Purpose

Use this path to deploy the shared `external_edge` load-balancer layer. This
is the north-south boundary for services that need controlled ingress,
controlled egress, or load balancing from the edge network into internal
service networks.

The reference implementation is `HAProxy` with `keepalived`. The default is a
3-node edge set with multiple VIPs. Each VIP has a different preferred owner,
so healthy traffic is spread while every VIP can still fail over.

## Default deployment

| Component | Terraform default | Inventory entry | Zone | Purpose |
| --- | --- | --- | --- | --- |
| edge load balancers | `edge-lb-1`, `edge-lb-2`, `edge-lb-3` active | present by default | `external_edge` | ingress, egress, and load balancing |
| extra edge nodes | add matching inventory and IP entries | not present by default | `external_edge` | more capacity, site spread, or policy separation |

The default uses three nodes so one edge host can be updated or changed while
traffic still has two remaining edge hosts. This is not cluster quorum in the
database sense; it is an operational HA pattern for maintenance headroom and
better VIP distribution.

## VIP distribution

Use one keepalived `vrrp_instance` per VIP. Each VIP needs its own
`virtual_router_id`, and all nodes stay in `BACKUP` state so priority decides
ownership after restarts.

The example rotates priority ownership:

| VIP | Preferred owner | First backup | Second backup |
| --- | --- | --- | --- |
| `internal_prod` | `edge-lb-1` | `edge-lb-2` | `edge-lb-3` |
| `internal_mgmt` | `edge-lb-2` | `edge-lb-3` | `edge-lb-1` |
| `dmz_ingress` | `edge-lb-3` | `edge-lb-1` | `edge-lb-2` |

Normal state:

```text
edge-lb-1 owns internal_prod
edge-lb-2 owns internal_mgmt
edge-lb-3 owns dmz_ingress
```

During a failure, the affected VIP moves to its next highest-priority backup.
That gives the edge layer "spread when healthy, consolidate only during
failure" behavior.

HAProxy uses nonlocal bind by default, so every edge node can load the same
frontend configuration even when it does not currently own every VIP.

Use VIP names as policy boundaries, not only as addresses:

| VIP type | Typical traffic | Why it is separate |
| --- | --- | --- |
| `internal_prod` | internal apps, APIs, Kubernetes ingress, GitLab, Keycloak, service UIs | stable application delivery and user/service traffic |
| `internal_mgmt` | Proxmox, SSH jump paths, Vault admin, PKI admin, Rancher, Kubernetes API | stricter ACLs, MFA, logging, and reduced management-plane blast radius |
| `dmz_ingress` | internet-facing or externally reachable services | tighter exposure control and separate firewall/TLS policy |

Larger environments may add VIPs for storage, observability, identity, or CI
when those traffic classes need their own firewall rules, certificates, logging,
or maintenance ownership. The important rule is to avoid one giant VIP for
everything when traffic purpose and trust level differ.

## Service shape

| Service | Default role |
| --- | --- |
| `HAProxy` | runs the edge load-balancer configuration |
| `keepalived` | owns edge VIPs and fails them over between edge hosts |
| local HAProxy stats | enabled on `127.0.0.1:8404` for local checks |

## What you configure

| Path | What you configure |
| --- | --- |
| [`terraform/common.tfvars.example`](../../../terraform/common.tfvars.example) | `external_edge` network mapping, shared storage, template ID, and SSH keys |
| [`terraform/environments/edge/terraform.tfvars.example`](../../../terraform/environments/edge/terraform.tfvars.example) | edge VM count, size, storage, and tags |
| [`ansible/inventory/hosts.yml.example`](../../../ansible/inventory/hosts.yml.example) | `edge_load_balancers` host group |
| [`ansible/group_vars/all.yml.example`](../../../ansible/group_vars/all.yml.example) | edge host IP addresses |
| [`ansible/group_vars/edge.yml.example`](../../../ansible/group_vars/edge.yml.example) | VIPs, keepalived router IDs, rotated priorities, HAProxy stats listener, and frontend/backend entries |

## How other paths use it

Other paths should append or refresh only the configuration they own. For
example, the HSM path can rerun edge configuration to add HSM gateway backends
without redeploying the edge VMs.

Keep this boundary:

- the edge setup owns the edge hosts
- service paths own their backend snippets or routing entries
- edge VIPs are stable addresses other services consume
- raw service protocols should not be exposed directly through the edge layer
- more edge nodes are added by extending `vm_instances`, inventory, and IP map

## Read more

- [Shared services path](README.md)
- [Network architecture](../../architecture/network.md)
- [USB HSM active-active blueprint](../../security/usb-hsm-active-active-blueprint.md)
