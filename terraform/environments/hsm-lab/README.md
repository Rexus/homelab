# HSM lab environment

## Table of contents

- [Purpose](#purpose)
- [Prerequisite](#prerequisite)
- [What it provisions](#what-it-provisions)
- [Lab tracks](#lab-tracks)
- [What stays manual](#what-stays-manual)
- [Continue reading](#continue-reading)

## Purpose

Use this environment to provision the host layout for the repository's PKCS#11
lab pattern.

It gives you a stable IaC entry point for the same topology whether you start
with a USB HSM such as Pico HSM or YubiHSM 2, or with a software-only PKCS#11
rehearsal path.

This environment uses the same `network_zones`, `vm_instances`, and
`lxc_instances` schema as the other Terraform environments so the network model
and guest placement stay consistent across the repository.

## Prerequisite

Use [`terraform/environments/foundation/`](../foundation/README.md) first when
you follow the repository default USB HSM path.

The shared edge proxy or load balancer belongs in that foundation layer on
`dmz`. This environment then adds the active gateway hosts in
`cryptography` and any restricted recovery or provisioning helpers in
`ceremony`.

## What it provisions

This environment provisions:

- `2` gateway or signer-adjacent VMs in the default example
- `0+` helper VMs for bootstrap, restore, or recovery work

This is the host layout around the HSM pattern. It does not try to model the
USB device itself inside Terraform.

You can still scale the same pattern up or down by changing `vm_instances`. The
default example starts at two gateway hosts because that is the repository's
reference active-active shape.

## Lab tracks

Use one of these tracks after the VMs exist:

- hardware-backed track: attach your chosen USB HSM devices to the intended
  gateway and helper hosts and follow the USB HSM blueprint
- software-only track: keep the same VMs and run a software PKCS#11 token on
  those hosts while you validate the service pattern before hardware arrives

Set `lab_variant` to reflect which track the environment represents.

Use `vm_instances` dynamically:

- tag signer or gateway VMs with role `gateway`
- tag bootstrap or recovery helpers with role `helper`

The default example keeps the edge proxy outside this environment, but the
map can still grow or shrink without changing the environment code.

## What stays manual

This environment does not automate:

- USB passthrough or physical device attachment
- PKCS#11 middleware or software-token package installation
- token initialization, PIN handling, DKEK custody, wrap, export, or restore
- signer, gateway, or PKI service configuration
- load balancer health checks for key inventory or signer readiness

Keep those steps in the operational guide rather than trying to hide them
inside Terraform.

## Continue reading

- [Foundation environment](../foundation/README.md)
- [Network zones and IaC mapping](../../../docs/architecture/network-zones-and-iac-mapping.md)
- [USB HSM active-active blueprint](../../../docs/security/usb-hsm-active-active-blueprint.md)
- [Vault HSM hardening options](../../../docs/security/vault-hsm-hardening-options.md)
- [Terraform overview](../../README.md)
