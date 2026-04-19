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

- keep the root `README.md` short, stable, and durable
- treat the root `README.md` as the repo fast path for developers
- keep practical IaC getting-started steps and command snippets in the root
  `README.md`
- use the root `README.md` to point into deeper `docs/` material without
  replacing the fast path with a docs-style index
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
- use compact numeric citations like `[1]` for non-trivial external claims in
  docs
- keep `## References` as the last header and list sources as numbered markdown
  links with accessed dates
- present prices in documentation in `EUR` by default, with a date note near
  the price text or below the table
- if prices come from another currency, make any `EUR` conversion clearly dated
  and non-durable
- revalidate cited links when they are added or edited, and say so if that
  validation was not possible
