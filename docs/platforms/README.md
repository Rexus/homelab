# Platforms

## Table of contents

- [Purpose](#purpose)
- [Current platforms](#current-platforms)

## Purpose

Platform documents connect capabilities to their implementation guides. Proxmox
is the chosen virtualization platform; Kubernetes is the cluster capability,
with Talos as its current node-OS example. The baseline remains centered on reusable workflows,
security posture, and tool separation across Packer, Terraform, and Ansible.

## Current platforms

- [Proxmox](proxmox/README.md) - chosen virtualization platform
- [Kubernetes clusters](kubernetes/README.md) - implementation choice and shared readiness checks
- [Kubernetes with Talos](talos/terraform.md) - current Tier 0 Terraform implementation
- [Manual bootstrap with Talos](talos/bootstrap.md) - Tier 0/Tier 1 implementation procedure
- [UniFi zone firewall](unifi/zone-firewall.md) - manual network-policy
  translation for the network-layer model, not a provisioning provider

Read [Private cloud model](../architecture/private-cloud.md) when you want to
understand why the current reference path starts with Proxmox and when a
heavier private-cloud control plane becomes a better fit.
