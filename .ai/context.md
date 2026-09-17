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
- repository model is a Tier 0, Tier 1, and Tier 2 deployment kit
- expected downstream repos are `<prefix>-tier-0`, `<prefix>-tier-1`,
  `<prefix>-tier-2`, `<prefix>-shared`, and `<prefix>-architecture`
- those repos live inside `<prefix>-iac/`, a collection directory beside the
  upstream checkout by default; `--root` selects the collection's parent
- README fast paths start with one real generation command and nearby flag
  tips; downstream root READMEs are short, developer-owned starter templates
- all downstream root READMEs link to architecture's `docs/naming-conventions.md`;
  project templates record chosen names, IDs, networks, design, and recovery
- `docs/auto-docs/` holds upstream reference docs with visible refresh/do-not-edit
  notices; root READMEs and project templates are seeded once, never refreshed
- preserve existing README contents when promoting them to owned files;
  legacy `docs/generated/upstream/` stays untouched for manual link migration
- shared scripts can be called by relative path from a tier root and use that
  tier's inputs; tier-local script shortcuts delegate to the same code
- `scripts/init-tier-repos.sh` generates three tier-owned inventories and
  Terraform setup roots, shared modules/playbooks/roles/wrappers, and docs
- both tools consume the owning tier's inventory and ordered group vars;
  shared code contains no live inventory or state
- refresh uses `.generated-files.json` and preserves local edits and deletions;
  Talos and cluster resources remain seed-only skeletons
- Tier 0 must remain bootstrapable and recoverable without higher-tier services
- Tier 0 owns template catalogs, creation/update CD jobs, publication state,
  `template-refresh` and `immutable-template` builders; shared owns reusable code
- AlmaLinux/Rocky/Talos publication uses verified local images; Talos templates
  contain no machine configuration, and cluster bootstrap remains a separate skeleton
- dedicated custody-local template CI is optional Day 2 automation; local commands,
  provider artifacts and state must remain usable without the cluster or CI service
- draw security layers left-to-right: Edge, Application, Control; distinguish
  the Control layer from the `management` network; infrastructure supports all layers
- draw tiers top-to-bottom: Tier 2, Tier 1, Tier 0; dependencies point down
  toward providers, while capabilities are provided upward
- networks belong to tier/layer cells, not a separate band hierarchy;
  connected firewall zones use `T<tier>-<layer>` and group named subnets
- `network_zones` remains a logical guest-network input, not a firewall zone;
  generation does not allocate subnets or configure gateway policy
- keep network placement in architecture, rule contracts in security, and
  vendor-specific zone-matrix translation in platform guides
- Tier 0 lives only in air-gapped custody; approved artifact handoffs do not
  create routed connections into custody
- use general capability terms in architecture docs, such as source control,
  identity authority, identity broker, OIDC interface, inventory source of
  truth, observability dashboard, and cluster management

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
- lower tiers must recover without higher tiers; custody supplies offline
  outputs rather than live dependencies for connected tiers
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
