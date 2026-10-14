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
- `docs/deployment/stage-3-identity-runtime/procedures/kubernetes.md` owns cluster choices and common readiness;
  its `talos-terraform.md` sibling and stage's `step-2b-manual-cluster.md` own implementation procedures
- all three tiers own a Kubernetes root, inventory/IP map, state and credentials;
  shared/scripts/kubernetes-cluster.sh is execution only, with tier-local shortcuts
- new cluster examples use three schedulable control planes with optional workers;
  existing configs default to disabled control-plane scheduling; never remove live workers to match examples
- pool inputs emit node-pool labels; authorized Kubernetes operations own worker taints;
  pools are not independent security boundaries and no autoscaler is supplied
- Tier 0 uses Flux; Tier 1 delivery remains unselected between Argo CD and Spinnaker;
  Tier 1 delivery never owns Tier 0 credentials or cluster/infrastructure lifecycle
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
  shared code contains no inventory, Terraform resources, guest assignments, credentials, or state;
  shared/config/platform.tfvars holds project-owned storage/placement and common network references
- common network references use shared_network_zones; tier-local network_zones holds only
  tier-specific entries and complete per-network overrides; roots merge the two maps by name
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
- initial template publication is Stage 1 local automation, before managed VMs
  or hosted tooling; generated Tier 0 fast paths start with the template catalog
- AlmaLinux/Rocky/Talos publication uses verified local images; Talos templates
  contain no machine configuration; Tier 0's separate Talos deployment creates
  VMs, machine configuration, and the cluster without Ansible guest configuration
- dedicated Tier 0 template CI is optional hosted automation; local commands,
  provider artifacts and state must remain usable without the cluster or CI service
- retain Tier 1/2 workload definitions, inventories, and separate state roots;
  future privileged infrastructure execution is controlled by Tier 0
- future Tier 2 self-service uses bounded VM create/update requests to automation
  enabled in Tier 0 GitOps; it never runs arbitrary Tier 2 code with Tier 0 credentials
- Tier 0 operates and recovers without Tier 2; request-source loss pauses new
  requests, not control operations, and must not trigger workload deletion
- delegated provisioning is a design goal, not an implemented controller or API;
  its authoritative contract is docs/architecture/compute/provisioning.md
- docs/deployment/README.md indexes six capability stages: compute foundation, cryptographic trust,
  identity and Kubernetes, control services, delivery and handover, and workload provisioning
- each stage has a main README with numbered local steps, diagrams, a capability result,
  and links to the static architecture; only the initial compute foundation is bootstrap
- optional step-Nb/step-Nc guides sit beside the main README, identify their branch
  and return point; detailed configuration lives in that stage's procedures/ folder
- Trust Step 1b hardware protection is optional; the USB hsm setup provides VMs and OS baseline,
  not gateway software, key ceremonies, issuer integration, or edge configuration
- draw security layers left-to-right: Edge, Application, Control; distinguish
  the Control layer from the `management` network; infrastructure supports all layers
- draw tiers top-to-bottom: Tier 2, Tier 1, Tier 0; potential impact and required
  protection increase downward; classification lines do not imply connectivity
- tiers divide repository ownership by potential damage and actual privileges;
  network layers separately protect from the outside inward
- public edge load balancers and ordinary outbound proxy/cache belong to Tier 2 / DMZ;
  their roots, inventory, roles and recipes are Tier 2-owned, not Tier 1
- ordinary clients are Tier 2 / DMZ on a separate client subnet, not provisioned server guests;
  DMZ membership never allows peer access or unsolicited WAN publication
- authoritative mirrors and general Internet-facing build runners remain Tier 1 / DMZ,
  using the separate delivery_edge subnet; they hold no Tier 0 credentials
- privileged jump hosts, bootstrap VMs and infrastructure runners remain Tier 0 / Control;
  any remote perimeter entry is isolated from the privileged session host
- public edge never carries Tier 0 admin/control API or foundational signing/recovery traffic;
  optional consumer API publication is separately scoped and retains private Tier 0 operation
- replicated USB signing uses a capacity-sized pool of Tier 0 service VMs, one local token per host;
  the private endpoint is logical and co-hosted, never a mandatory extra LB pair or Tier 1 cluster
- two enabled service hosts are a starter, not a limit; choose N using measured traffic,
  operation/session mix, latency and failure/maintenance headroom; size VIP/proxy capacity separately
- Vault consumes HSM-backed key generation/private-key operations where supported;
  the HSM service does not require Vault to bootstrap, and seal integration is a separate choice
- single-device custody plus independent backup can satisfy initial deployment;
  deployment adds the replicated variant when selected consumer availability requires it,
  not automatically because Vault or a registry exists; root custody stays offline
- integrated VIP/balancing means software on the existing HSM service hosts, not USB-device
  networking or additional frontend VMs; higher-tier service loss never blocks Tier 0 startup
- endpoint variants E1 client failover, E2 private VIP and E3 co-hosted VIP/proxies refine custody C;
  E3 requires a supported active-active application; VIP ownership is separately active/standby
- application state, key replication, sessions and device/key readiness have separate contracts;
  a TCP check or duplicated key material does not prove application HA
- optional HSM ingress targets hsm_gateways, defaults disabled and requires explicit HA/readiness
  acknowledgements; it renders a backend scaffold only, never a complete signing/VIP installer
- edge ownership refresh preserves old code, live inputs, registrations and state;
  migration is deliberate and must avoid a second state managing the same VM
- use purpose-named networks and example firewall zones DMZ, Services, and Control;
  shared zones do not imply shared subnets or unrestricted access
- `network_zones` remains a logical guest-network input, not a firewall zone;
  generation does not allocate subnets or configure gateway policy
- keep network placement and firewall contracts in architecture/networking/, and
  vendor-specific zone-matrix translation in deployment/stage-1-foundation/procedures/
- Tier 0 includes connected high-impact control systems; only selected custody
  and recovery assets are air-gapped; artifact handoffs do not create routed access
- protect the acceptance path, jobs, runners, and credentials for privileged
  changes at the target tier; a runner tag alone is not an isolation boundary
- use general capability terms in architecture docs, such as source control,
  identity authority, identity provider (IdP), OIDC interface, inventory source of
  truth, observability dashboard, and cluster management

## Documentation intent

- docs/architecture/README.md owns the capability placement map and technical-domain navigation;
  use named services, tiers vertically (2, 1, 0), and layers horizontally (Edge, Application, Control)
- domain diagrams expand the same capabilities into components, runtimes and cross-tier consumers;
  product names belong in reference realizations, not the top-level capability map
- IAM is the overall identity and access management capability, not a VM; directory authority/IdM
  and identity provider/IdP are separate roles; LDAP user federation is not identity brokering
- reference IdM and IdP remain Tier 0/Control; a consumed login interface does not move the IdP
  into Services or expose its administration; management is a network, not another layer
- reference-platform.md allocates components; runtime-flows.md owns cross-domain service interactions;
  domain designs expand those functions without becoming an installation sequence
- compute/runtime.md owns generic hosting/persistence; compute/kubernetes.md owns the three-tier topology;
  delivery/controllers.md owns the independent Flux, Argo CD and Spinnaker boundaries
- variants.md records stable consumer contracts and different guarantees; detailed alternatives stay
  inside their owning domain; project architecture records one compatible selected composition
- new project starters follow overview, relationships, domains and detailed variants;
  refresh preserves every existing owned record, even an unchanged starter
- networking/, compute/, identity/, cryptography/, delivery/ and operations/ own domain designs
- architecture is the static intended design: context, components, interfaces, variants and constraints
- docs/deployment/readiness.md owns capability progress and acceptance; the deployment index owns stages
- use direct IT-domain directories, not intermediate system-design/subsystem-design indexes
- design records contain required guarantees, never stage-based states or current readiness
- readiness is independent per capability, and option letters are not a ranking or CLI flags
- cryptography supports software, single USB, replicated USB and network-HSM designs;
  service seals are separate choices; do not imply every option has an installer
- deployment/, development/, and administration/ separate installation, code and operations;
  paths/ contains only short repository checklists; reference/ contains exact contracts
- every generated repo has seed-owned docs/architecture/, deployment/, development/, and
  administration/ records; auto-docs mirror the upstream tree as reference material
- refresh retains existing project records and links them from new starters; unchanged
  moved auto-docs become compatibility pointers only in existing collections
- Ansible deployment/ and maintenance/ recipes compose existing roles; legacy setup plays import
  deployment recipes, while --recipe maintenance is Ansible-only
- SSH key files stay outside Git; TF_VAR_ssh_public_key_files supplies local public-key paths
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
