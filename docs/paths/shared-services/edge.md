# Edge proxy path

## Purpose

Use this path to deploy the shared `external_edge` proxy layer. This is the
north-south boundary for services that need controlled ingress, controlled
egress, or load balancing from the edge network into internal service networks.

The reference implementation is `HAProxy`, but the path keeps the role generic
as edge load balancing. Product-specific configuration belongs in Ansible roles
and service variables.

## Default deployment

| Component | Terraform default | Inventory entry | Zone | Purpose |
| --- | --- | --- | --- | --- |
| edge load balancers | `edge-lb-1`, `edge-lb-2` active | present by default | `external_edge` | ingress, egress, and load balancing |
| extra edge nodes | commented examples | add matching inventory and IP entries | `external_edge` | horizontal scale or maintenance capacity |

The default is a pair. Add `edge-lb-3` and higher when the environment needs
more horizontal capacity, site spread, or maintenance headroom.

## What you configure

| Path | What you configure |
| --- | --- |
| [`terraform/common.tfvars.example`](../../../terraform/common.tfvars.example) | `external_edge` network mapping, shared storage, template ID, and SSH keys |
| [`terraform/environments/edge/terraform.tfvars.example`](../../../terraform/environments/edge/terraform.tfvars.example) | edge VM count, size, storage, and tags |
| [`ansible/inventory/hosts.yml.example`](../../../ansible/inventory/hosts.yml.example) | `edge_load_balancers` host group |
| [`ansible/group_vars/all.yml.example`](../../../ansible/group_vars/all.yml.example) | edge host IP addresses |

## How other paths use it

Other paths should append or refresh only the configuration they own. For
example, the HSM path can rerun edge configuration to add HSM gateway backends
without redeploying the edge VMs.

Keep this boundary:

- the edge setup owns the edge hosts
- service paths own their backend snippets or routing entries
- raw service protocols should not be exposed directly through the edge layer
- more edge nodes are added by extending `vm_instances`, inventory, and IP map

## Read more

- [Shared services path](README.md)
- [Network architecture](../../architecture/network.md)
- [USB HSM active-active blueprint](../../security/usb-hsm-active-active-blueprint.md)
