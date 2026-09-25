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
- chosen virtualization platform is Proxmox; other hypervisors are not selectable implementations
- name capabilities by the goal, keeping implementation products explicit only where relevant
- Kubernetes is the cluster goal; Talos is the current node-OS implementation example,
  not an architecture requirement. Immutable AlmaLinux or other OS support needs future lifecycle code
- public cluster entry points are `terraform/deployments/kubernetes/` and
  `scripts/kubernetes-cluster.sh`; retain existing Talos state, inventory, provider,
  and credential contracts. The old script delegates; old roots require deliberate migration
- `docs/platforms/kubernetes/README.md` owns cluster choices and common readiness;
  `docs/platforms/talos/` owns the current implementation procedures
- security-first posture with strong separation of concerns
- public upstream is curated and not meant for operational changes
- repository model is a Tier 0, Tier 1, and Tier 2 deployment kit
- source `tier-0/`, `tier-1/`, `tier-2/`, and `shared/` mirror generated repos;
  each tier visibly owns Terraform roots, service playbooks/roles, inputs, and `.deployment-setups`
- root `scripts/` is generation tooling only; common deployment helpers live in
  `shared/scripts/` with tier-local shortcuts; the template publisher is Tier 0-local
- expected downstream repos are `<prefix>-tier-0`, `<prefix>-tier-1`,
  `<prefix>-tier-2`, `<prefix>-shared`, and `<prefix>-architecture`
- those repos live inside `<prefix>-iac/`, a collection directory beside the
  upstream checkout by default; `--root` selects the collection's parent
- README fast paths start with one real generation command and nearby flag
  tips; downstream root READMEs are short, developer-owned starter templates
- all downstream root READMEs link to architecture's `docs/naming-conventions.md`;
  this short worksheet records VM names, tags, VMID ranges, and VLAN conventions;
  full live assignments stay in inventory, with design and recovery in separate docs
- `docs/auto-docs/` holds upstream reference docs with visible refresh/do-not-edit
  notices; root READMEs and project templates are seeded once, never refreshed
- preserve existing README contents when promoting them to owned files;
  legacy `docs/generated/upstream/` stays untouched for manual link migration
- shared scripts can be called by relative path from a tier root and use that
  tier's inputs; tier-local script shortcuts delegate to the same code
- `scripts/init-tier-repos.sh` generates three tier-owned inventories and
  Terraform deployment roots, tier service code/modules, shared helpers, and docs
- runnable Terraform roots live in `terraform/deployments/<name>/`; child modules
  stay in `terraform/modules/`; state remains independent per deployment
- both tools consume the owning tier's inventory and ordered group vars;
  shared code contains no inventory, Terraform resources, deployment inputs, or state
- refresh uses `.generated-files.json` and preserves local edits and deletions;
  Kubernetes Terraform currently uses Talos in tier-owned automation; `clusters/` service starters
  remain project-owned skeletons, not installed services
- code ownership upgrades preserve retired shared files for manual review and
  do not port local edits into new tier paths, alter owned CI jobs, or move state
- Tier 0 must remain bootstrapable and recoverable without higher-tier services
- Tier 0 owns publication catalogs, creation/update CD jobs, publication state,
  `template-refresh` and `immutable-template` builders, all template modules,
  Packer definitions, and the local publication script; shared holds only approved
  consumer references, not image recipes or lifecycle ownership
- Tier 0 owns all hardware-facing control, including hypervisors, physical networks,
  storage administration, and every VM template lifecycle across all consuming tiers
- initial template publication is Day 0-1 local automation, before managed VMs
  or hosted tooling; generated Tier 0 fast paths start with the template catalog
- AlmaLinux/Rocky/Talos publication uses verified local images; Talos templates
  contain no machine configuration; Tier 0's separate Talos deployment creates
  VMs, machine configuration, and the cluster without Ansible guest configuration
- dedicated Tier 0 template CI is optional Day 2 automation; local commands,
  provider artifacts and state must remain usable without the cluster or CI service
- retain Tier 1/2 workload definitions, inventories, and separate state roots;
  future privileged infrastructure execution is controlled by Tier 0
- future Tier 2 self-service uses bounded VM create/update requests to automation
  enabled in Tier 0 GitOps; it never runs arbitrary Tier 2 code with Tier 0 credentials
- Tier 0 operates and recovers without Tier 2; request-source loss pauses new
  requests, not control operations, and must not trigger workload deletion
- delegated provisioning is a design goal, not an implemented controller or API;
  its authoritative contract is docs/architecture/infrastructure-control.md
- draw security layers left-to-right: Edge, Application, Control; distinguish
  the Control layer from the `management` network; infrastructure supports all layers
- draw tiers top-to-bottom: Tier 2, Tier 1, Tier 0; potential impact and required
  protection increase downward; classification lines do not imply connectivity
- tiers divide repository ownership by potential damage and actual privileges;
  network layers separately protect from the outside inward
- use purpose-named networks and example firewall zones DMZ, Services, and Control;
  shared zones do not imply shared subnets or unrestricted access
- `network_zones` remains a logical guest-network input, not a firewall zone;
  generation does not allocate subnets or configure gateway policy
- keep network placement in architecture, rule contracts in security, and
  vendor-specific zone-matrix translation in platform guides
- Tier 0 includes connected high-impact control systems; only selected custody
  and recovery assets are air-gapped; artifact handoffs do not create routed access
- protect the acceptance path, jobs, runners, and credentials for privileged
  changes at the target tier; a runner tag alone is not an isolation boundary
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
- make it easy to do right: avoid encoding tier, zone, VLAN, and IP into names

## Working rules

- do not encourage storing secrets in Git
- do not treat this upstream as the destination for live environment changes
- prefer private forks, mirrors, or local copies for operational work
- lower-numbered tiers must recover without higher-numbered tiers; normal
  consumers use scoped service endpoints, while offline custody supplies transfers
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
