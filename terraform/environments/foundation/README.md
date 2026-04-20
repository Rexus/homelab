# Foundation environment

## Table of contents

- [Purpose](#purpose)
- [What it provisions](#what-it-provisions)
- [Default shape](#default-shape)
- [What stays manual](#what-stays-manual)
- [Continue reading](#continue-reading)

## Purpose

Use this environment to provision shared edge and foundation hosts that should
exist before service-specific environments build on top of them.

For the repository's USB HSM path, this is the home of the central
reverse proxy in `dmz`. Treat that shared proxy as a prerequisite for the
default HSM guide rather than placing it inside the HSM-specific environment.

This environment uses the same `network_zones`, `vm_instances`, and
`lxc_instances` schema as the other Terraform environments so the network model
and guest placement stay consistent across the repository.

## What it provisions

This environment provisions:

- shared edge or ingress hosts in `dmz`
- optional shared service helpers in `service`
- optional operator support hosts in `management`

The default example keeps this small on purpose: one shared DMZ proxy that
later environments can depend on.

## Default shape

Use the default example as the repository fast path:

- `1` central reverse proxy VM in `dmz`
- shared `network_zones` entries kept in one local `terraform.tfvars`
- room to add more proxies or foundation services later through `vm_instances`

The USB HSM guide assumes this shared proxy exists before you provision the
gateway hosts in `terraform/environments/hsm-lab/`.

## What stays manual

This environment does not automate:

- external DNS, certificates, or public routing
- detailed reverse-proxy product choice and package installation
- full frontend, WAF, or access-control policy
- service-specific backend registration outside the Ansible proxy playbook

Keep those steps in the service guide or platform operations runbooks rather
than trying to hide them inside Terraform.

## Continue reading

- [Network zones and IaC mapping](../../../docs/architecture/network-zones-and-iac-mapping.md)
- [USB HSM active-active blueprint](../../../docs/security/usb-hsm-active-active-blueprint.md)
- [Terraform overview](../../README.md)
