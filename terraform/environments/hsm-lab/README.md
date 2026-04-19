# HSM lab environment

## Table of contents

- [Purpose](#purpose)
- [What it provisions](#what-it-provisions)
- [Lab tracks](#lab-tracks)
- [What stays manual](#what-stays-manual)
- [Continue reading](#continue-reading)

## Purpose

Use this environment to provision the host layout for the repository's PKCS#11
lab pattern.

It gives you a stable IaC entry point for the same topology whether you start
with real Pico HSM hardware or with a software-only PKCS#11 rehearsal path.

This environment uses the same `network_zones`, `vm_instances`, and
`lxc_instances` schema as the other Terraform environments so the network model
and guest placement stay consistent across the repository.

## What it provisions

This environment provisions:

- `1-3` proxy or load-balancer VMs
- `1-8` gateway or signer-adjacent VMs
- `0+` helper VMs for bootstrap, restore, or recovery work

This is the host layout around the HSM pattern. It does not try to model the
USB device itself inside Terraform.

## Lab tracks

Use one of these tracks after the VMs exist:

- hardware-backed track: attach Pico HSM devices to the intended gateway and
  helper hosts and follow the Pico HSM blueprint
- software-only track: keep the same VMs and run a software PKCS#11 token on
  those hosts while you validate the service pattern before hardware arrives

Set `lab_variant` to reflect which track the environment represents.

Use `vm_instances` dynamically:

- tag proxy VMs with role `proxy`
- tag signer or gateway VMs with role `gateway`
- tag bootstrap or recovery helpers with role `helper`

The default example models the repository's drawn reference pattern, but the
map can grow or shrink without changing the environment code.

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

- [Network zones and IaC mapping](../../../docs/architecture/network-zones-and-iac-mapping.md)
- [Pico HSM active-active blueprint](../../../docs/security/picohsm-active-active-blueprint.md)
- [Vault HSM hardening options](../../../docs/security/vault-hsm-hardening-options.md)
- [Terraform overview](../../README.md)
