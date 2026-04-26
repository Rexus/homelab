# Foundation environment

## Table of contents

- [Purpose](#purpose)
- [Identity and PKI strategy](#identity-and-pki-strategy)
- [Proxy strategy](#proxy-strategy)
- [What it provisions](#what-it-provisions)
- [Default shape](#default-shape)
- [What stays manual](#what-stays-manual)
- [Continue reading](#continue-reading)

## Purpose

Use this environment to provision the first domain foundation hosts that later
services build on top of.

The current default path is identity and PKI first, not the edge proxy first.

For the repository's current proxy strategy, this is the home of the early
edge-proxy and load-balancer layer in `dmz`. Treat that edge proxy as a
prerequisite for service guides such as the USB HSM deployment guide rather
than placing it inside service-specific environments.

This environment uses the same `network_zones`, `vm_instances`, and
`lxc_instances` schema as the other Terraform environments so the network model
and guest placement stay consistent across the repository.

## Identity and PKI strategy

Use this default shape:

- `2` `FreeIPA` and DNS hosts in `identity`
- `1` issuing CA host in `cryptography`
- optional offline root CA host in `ceremony`

Both CA layers can later move to HSM-backed keys, but the default foundation
path does not require HSM.

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

- domain identity hosts in `identity`
- issuing-CA hosts in `cryptography`
- optional ceremony hosts in `ceremony`
- optional shared edge-proxy ingress hosts in `dmz`
- optional operator support hosts in `management`

The default example keeps this focused on the domain foundation first.

Use separate ignored var files when you want disposable and production
deployments from the same environment folder:

| Environment | Local var file | Terraform workspace |
| --- | --- | --- |
| default | `terraform.tfvars` | `default` |
| test or staging | `terraform.test.tfvars` | `test` |
| production | `terraform.prod.tfvars` | `prod` |

The repository wrapper selects the matching workspace when you pass `--env`.

## Default shape

Use the default example as the repository fast path:

- `2` identity hosts in `identity`
- `1` issuing CA host in `cryptography`
- `0-1` root CA or ceremony host in `ceremony`
- `0-1` edge-proxy or load-balancer VM in `dmz`
- shared `network_zones` entries kept in the local var file for that
  environment
- room to add more foundation services later through `vm_instances`

The USB HSM guide assumes the edge proxy exists before you provision the
gateway hosts in `terraform/environments/hsm-lab/`, but the identity and PKI
foundation can be deployed before that proxy is enabled.

## What stays manual

This environment does not automate:

- issuing-CA installation and enrollment
- root-CA ceremony handling or offline power-state workflow
- external DNS, certificates, or public routing
- edge-proxy package installation and detailed frontend policy
- full frontend, WAF, or access-control policy
- service-specific backend registration outside the Ansible proxy playbook
- later internal cluster proxy deployment

Keep those steps in the service guide or platform operations runbooks rather
than trying to hide them inside Terraform.

## Continue reading

- [Domain foundation path](../../../docs/foundation/foundation-and-domain-path.md)
- [Network zones and IaC mapping](../../../docs/architecture/network-zones-and-iac-mapping.md)
- [USB HSM active-active blueprint](../../../docs/security/usb-hsm-active-active-blueprint.md)
- [Terraform overview](../../README.md)
