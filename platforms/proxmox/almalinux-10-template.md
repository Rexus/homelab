# AlmaLinux 10 template on Proxmox

## Table of contents

- [Purpose](#purpose)
- [Recommended source](#recommended-source)
- [Quick path](#quick-path)
- [What to keep in the template](#what-to-keep-in-the-template)
- [What to configure later](#what-to-configure-later)
- [Read more](#read-more)

## Purpose

Use the official AlmaLinux 10 Generic Cloud image as the starting point for the
first reusable Proxmox VM template in this repository.

## Recommended source

Use the official AlmaLinux 10 Generic Cloud `qcow2` image. This image is built
for cloud-init-style initialization and is a good fit for Proxmox templates.

## Quick path

1. Download the official AlmaLinux 10 Generic Cloud `qcow2` image.
2. Upload it to storage reachable by your Proxmox node.
3. Create a new VM shell in Proxmox.
4. Import the `qcow2` disk into the VM.
5. Attach a cloud-init drive.
6. Set the VM boot disk and boot order.
7. Convert the VM to a template.
8. Use the template VM ID in `terraform/environments/lab/terraform.tfvars`.

## What to keep in the template

Keep the first template minimal:

- AlmaLinux 10 base image
- cloud-init support
- QEMU guest support when needed for your workflow
- no environment-specific IPs, names, or credentials

## What to configure later

Configure these at deploy time with Terraform and Ansible:

- hostname
- SSH keys
- DHCP or static IP configuration
- users beyond the initial automation path
- package and service baselines
- hardening beyond the base image

## Read more

- [Proxmox reference platform](README.md)
- [Private cloud maturity path](../../docs/getting-started/private-cloud-maturity-path.md)
- [Environment variable conventions](../../docs/reference/environment-variables.md)
