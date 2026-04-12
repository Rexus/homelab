# Repository context

## Table of contents

- [Purpose](#purpose)
- [Repository intent](#repository-intent)
- [Documentation intent](#documentation-intent)
- [Working rules](#working-rules)

## Purpose

This file keeps durable context for AI-assisted work across sessions.

## Repository intent

- public homelab and small datacenter IaC baseline
- current reference platform is Proxmox
- platform-aware, not platform-locked
- security-first posture with strong separation of concerns
- public upstream is curated and not meant for operational changes

## Documentation intent

- keep the README short, stable, and durable
- put detailed material in `docs/`
- prefer diagrams, lists, and tables over long prose
- make example-to-live-file patterns explicit
- keep instructions fast to scan and easy to maintain

## Working rules

- do not encourage storing secrets in Git
- do not treat this upstream as the destination for live environment changes
- prefer private forks, mirrors, or local copies for operational work
- keep Packer, Terraform, and Ansible responsibilities separate
- preserve a high-security baseline by default
