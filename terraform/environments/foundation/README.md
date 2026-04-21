# Foundation environment

## Table of contents

- [Purpose](#purpose)
- [Proxy strategy](#proxy-strategy)
- [What it provisions](#what-it-provisions)
- [Default shape](#default-shape)
- [What stays manual](#what-stays-manual)
- [Continue reading](#continue-reading)

## Purpose

Use this environment to provision shared edge and foundation hosts that should
exist before service-specific environments build on top of them.

For the repository's current proxy strategy, this is the home of the early
edge-proxy and load-balancer layer in `dmz`. Treat that edge proxy as a
prerequisite for service guides such as the USB HSM deployment guide rather
than placing it inside service-specific environments.

This environment uses the same `network_zones`, `vm_instances`, and
`lxc_instances` schema as the other Terraform environments so the network model
and guest placement stay consistent across the repository.

## Proxy strategy

Use this split:

- an edge proxy in `dmz` handles early ingress and controlled egress for
  infrastructure and host-based services
- a separate internal cluster proxy can be added later when Kubernetes becomes
  part of the platform
- `HAProxy` is the current foundation candidate for the edge-proxy role

This keeps the host-based edge simple before Kubernetes exists, while leaving
cluster-native ingress decisions to the later platform layer.

## What it provisions

This environment provisions:

- shared edge-proxy ingress hosts in `dmz`
- optional shared service helpers in `service`
- optional operator support hosts in `management`

The default example keeps this small on purpose: one shared edge-proxy host
that later environments can depend on.

## Default shape

Use the default example as the repository fast path:

- `1` edge-proxy or load-balancer VM in `dmz`
- shared `network_zones` entries kept in one local `terraform.tfvars`
- room to add more proxies or foundation services later through `vm_instances`

The USB HSM guide assumes this edge proxy exists before you provision the
gateway hosts in `terraform/environments/hsm-lab/`.

## What stays manual

This environment does not automate:

- external DNS, certificates, or public routing
- edge-proxy package installation and detailed frontend policy
- full frontend, WAF, or access-control policy
- service-specific backend registration outside the Ansible proxy playbook
- later internal cluster proxy deployment

Keep those steps in the service guide or platform operations runbooks rather
than trying to hide them inside Terraform.

## Continue reading

- [Network zones and IaC mapping](../../../docs/architecture/network-zones-and-iac-mapping.md)
- [USB HSM active-active blueprint](../../../docs/security/usb-hsm-active-active-blueprint.md)
- [Terraform overview](../../README.md)
