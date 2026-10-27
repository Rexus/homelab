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
- `docs/deployment/stage-4-kubernetes/procedures/kubernetes.md` owns cluster choices and common readiness;
  its `talos-terraform.md` sibling and stage's `step-1b-manual-cluster.md` own implementation procedures
- all three tiers own a Kubernetes root, inventory/IP map, state and credentials;
  shared/scripts/kubernetes-cluster.sh is execution only, with tier-local shortcuts
- all tiers use tier-owned cluster-platform playbooks/inputs with Shared's stateless
  cluster_platform, kubernetes_applications and helm_release roles. Tier 0 selects Flux;
  Tier 1/2 omit it unless a separate explicit design selects it. CNI/CSI, cert-manager,
  Traefik CRDs and CNPG are native pinned products, not empty GitOps starters;
  Barman is an explicit object/WAL backup selection, not required by scheduled NAS file copies
- Tier 0 control_applications installs Keycloak/LDAP, Vault/Raft/audit, NetBox and Headlamp;
  initialization/unseal and custody remain explicit. Tier 1 delivery/observability/development
  roles and Tier 2 lab/telemetry roles own their releases and interfaces
- tier-local machine_config_patches supplies native Talos proxy, DNS/time and registry documents;
  default [] preserves existing behavior, not restricted-network readiness; Linux proxy inputs do not apply
- new cluster examples use three schedulable control planes with optional workers;
  existing configs default to disabled control-plane scheduling; never remove live workers to match examples
- pool inputs emit node-pool labels; authorized Kubernetes operations own worker taints;
  pools are not independent security boundaries and no autoscaler is supplied
- Tier 0 uses Flux; Tier 1 delivery remains unselected between Argo CD and Spinnaker;
  Tier 1 delivery never owns Tier 0 credentials or cluster/infrastructure lifecycle
- Stage 9 supplies native GitLab and Kubernetes runner Helm recipes in Tier 1;
  its separate development-data setup supplies native PostgreSQL/Redis/Gitaly VMs,
  scoped object-storage handoff and backup jobs. The development setup retains
  its original standalone GitLab alternative/state; never migrate resources implicitly.
  Tier 0 owns infrastructure-runner provisioning/configuration and the separate Vault ci-auth root.
- Tier 0 supplies a separate cluster-endpoint setup with independent HAProxy/Keepalived
  API gateways. Existing qualified endpoints remain valid; replica count alone does not prove HA.
- Object storage names the capability; S3-compatible API names the selected interface,
  not an AWS dependency. Use direct NAS file interfaces where supported and existing
  qualified NAS/Ceph RGW/other object endpoints only where consumers require them.
  Do not add a NAS-to-object gateway, storage VM or imply missing infrastructure features.
  Ceph RBD supplies live VM disks; RGW is separate. UNAS outbound S3 backups do not
  establish an inbound object endpoint; confirm actual model/software support.
- Live databases stay on qualified Proxmox/Ceph-backed block volumes. NAS file areas
  receive backup copies, never replace PGDATA/WAL. Keep database/media/backup storage
  inputs distinct. Scheduled verified full PostgreSQL backups to NAS are accepted with
  recovery to a completed set, not continuous PITR; existing object/WAL mode remains valid.
  Shared's stateless postgresql_file_backup role executes the tier-owned database/backup
  contracts; it owns no inventory, storage server or resource state.
- Tier 1's complete native Spinnaker path includes the pinned upstream service base,
  SQL/cache dependencies, scoped target identities, SSO and recovery jobs. Argo CD
  remains a separate complete alternative; a custom Spinnaker overlay is no longer required.
- Direct infrastructure CI is opt-in: the dedicated project, GitLab control plane and
  administrators able to alter its hosting are accepted as Tier 0 authorities.
  Ordinary runners and application delivery controllers remain unprivileged.
  Independent recovery retains original tier-local inputs/state without GitLab/Vault/SSO.
- Stage 10 keeps workload isolation and bounded profile requests separate from direct CI.
  Profile examples are design inputs, not a shipped allocator or self-service portal.
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
  remain project-owned adoption points, not the native application installers
- code ownership upgrades preserve retired shared files for manual review and
  do not port local edits into new tier paths, alter owned CI jobs, or move state
- Tier 0 must remain bootstrapable and recoverable without higher-tier services
- CA reference: permanent OpenXPKI Community infrastructure issuer/portal on ca-1,
  offline clca root and sibling FreeIPA CA with explicit CA replication; Vault retains the reference secret-service role
- CA runtime: Tier 0 Debian template option, foundation extra disks, OpenXPKI installer,
  pinned policy builder and guarded database/runtime activation; routine convergence never creates keys.
  Software-first setup has a separately approved encrypted-key/CSR recipe and offline clca templates
- FreeIPA supports external CSR/pause/completion and an explicit CA replica; live custody,
  signing and recovery qualification remain manual operational verification.
  Fresh foundation examples select external sibling-CA mode; existing internal-mode
  local inputs are preserved, and changing their mode is not an installed-domain migration.
  The selected Linux/NAS logging path now supplies forwarding and protected-copy jobs;
  actual NAS custody and live fault/access/restore results remain manual qualification.
- Log archive alternatives are NAS-managed snapshots/independent backups with trusted
  administrators, or qualified retention locks when privileged deletion must be prevented.
  One homelab operator may hold all roles with separate credentials; same-person custody
  is explicit, not WORM. Growth/access changes trigger review, not an automatic cloud dependency.
  docs/architecture/operations/log-retention.md owns this choice; Stage 2 options 3c/3d guide it.
- Logging implementation: Shared owns stateless `log_forwarder`; tier inventories,
  source keys/cursors and selectors stay local. Tier 0 owns reviewed-CSR signing,
  receiver, create-only NAS checkpoints, audited application filesystem views and
  independent restic jobs on a separate recovery host. NAS accounts/snapshots and
  independent storage are commissioned prerequisites, not collector privileges.
  Native sender release is transport-based; expose the unprotected tail explicitly.
  This bounded-loss main path is not replicated intake or WORM. See `docs/reference/logging-pipeline.md`.
- All source Linux, template and Kubernetes Terraform roots verify Proxmox TLS. Provisioning
  entry points reject current/legacy insecure environment flags; bootstrap trusts the Proxmox CA.
- .ai/operator-walkthrough.md tracks missing mechanisms separately from supplied code;
  .ai/operational-verification.md owns unchecked live pass conditions for the current priorities.
  .ai/v1-readiness.md records implementation qualification and its exact offline evidence.
- Internal ACME remains integration; public HTTP-01 has Tier 2 automation with verified origins,
  separate staging/production state and a serialized controller timer, still requiring live acceptance
- Tier 0 owns publication catalogs, creation/update CD jobs, publication state,
  `template-refresh` and `immutable-template` builders, all template modules,
  Packer definitions, and the local publication script; shared holds only approved
  consumer references, not image recipes or lifecycle ownership
- Tier 0 owns all hardware-facing control, including hypervisors, physical networks,
  storage administration, and every VM template lifecycle across all consuming tiers
- initial template publication is foundation local automation, before managed VMs
  or hosted tooling; generated Tier 0 fast paths start with the template catalog
- AlmaLinux/Rocky/Debian/Talos publication uses verified local images; Talos templates
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
- docs/deployment/foundation/ contains unnumbered host/network/access/template prerequisites;
  docs/deployment/README.md indexes ten numbered capabilities: software intake, protected logging,
  cryptographic trust, Kubernetes, Identity, Secrets, Delivery, Observability, Development platform and Lab environments
- Stage 4 owns control-cluster bootstrap and common add-on/audit/recovery gates;
  Stage 5 owns dedicated directory VMs and federation on the existing cluster;
  independent bootstrap DNS/time/credentials avoid a Kubernetes/identity dependency cycle
- protected syslog/audit intake starts in Stage 2 on independent Tier 0 VMs;
  syslog setup provisions VMs/disks and installs Tier 0's isolated syslog-ng OSE receiver after
  explicit data-mount UUID, client catalogue and independent TLS preparation; OS logger is untouched;
  local JSON records/reliable queues are not HA, protected retention or independent backup integration
- receiver starter names are `log-1` and optional `log-2`, never deployment-stage prefixes;
  retain existing local guest/state/TLS/archive identities on refresh rather than renaming them;
  deployment diagrams link to owning IaC and distinguish new resources from existing/manual prerequisites
- apply one diagram language across docs: architecture uses stable capabilities/roles without guest keys;
  deployment uses exact starter instances and counts, linked inputs and executing code;
  explicitly bound manual/existing/project integration rather than implying an empty starter installs services;
  workflow and acceptance diagrams describe actions, not additional infrastructure
- retain local logs from first boot; central intake precedes PKI/FreeIPA and Kubernetes;
  portable evidence and an independent reader/key kit support offline data-volume inspection
- critical-data recovery follows 3-2-1 with independent offline/immutable custody;
  preserve evidence before tier recovery, and separate query roles from all deletion/pruning authority
- all tiers submit security records to narrow authenticated Tier 0 intake; producers append only,
  explicitly authorized administrator/security roles read raw evidence, and retention custody is separate
- Tier 1 holds approved searchable projections with per-application developer scopes, never raw archive authority;
  trusted source attribution, index permissions and read auditing enforce segmentation, not UI tenants alone
- independent Tier 0 critical monitoring/Netdata parent complements Tier 1 Observability and Tier 2
  collectors; no default SigNoZ/ClickHouse or full per-tier stack
- one receiver is bootstrap only; HA acceptance specifies durable acknowledgement/replication semantics,
  independent failure domains, bounded queues and protected retention; UDP and source-loss gaps stay explicit
- each stage has a main README with numbered local steps, diagrams, a capability result,
  and links to the static architecture; named monitoring/Observability/collection deployments
  belong to their owning stages, not one cross-stage procedure
- deployment guides name the working generated repository and upstream source directory near the top;
  IaC tables distinguish tier-owned inputs/resources from Shared helper implementations;
  docs/deployment/README.md#repository-locations owns the checkout/path convention
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
- controlled software intake is documented in docs/architecture/delivery/software-intake.md;
  Squid/VIP supplies the existing explicit proxy/cache, not a mirror or patch controller
- software intake is a separate early capability at docs/deployment/stage-1-software-intake/,
  not a foundation option; it is numbered Stage 1 and
  the later Stage 7 Harbor/OCI path extends this capability without becoming a bootstrap dependency
- connected Tier 0 clients may initiate approved update pulls without granting lower-tier
  administration; retain independent bootstrap/recovery artifacts and block direct WAN bypass
- internal HTTP mirrors are an explicit signed-content option, not a global TLS exception;
  transparent proxying does not decrypt HTTPS, and Windows update protocols need qualification
- multi-distro repository management and patch scheduling are requested capabilities;
  Pulp is under evaluation, not selected/installed; Windows is outside the current intake scope
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
  vendor-specific zone-matrix translation in deployment/foundation/procedures/
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
- hardware signing-custody rollover is an administration procedure, not an architecture page;
  implementation-support.md#stage-coverage owns the concise installer-coverage verdict
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
- follow [diagram conventions](../docs/development/diagrams.md): Tier 2/1/0 top-down,
  Edge/Services/Control left-to-right; use block grids for placement and nested flowcharts
  for interfaces; validate the shared palette and render both light and dark themes
- make it easy to do right: avoid encoding tier, zone, VLAN, and IP into names
- use one outer box per tier; foundational authority sits lower or farther right;
  directory authority sits to the right of the Tier 0 Kubernetes runtime
- aim for a rendered 4:3 figure with readable labels and room for adjacent page text;
  rearrange or split content rather than add blank padding or force every flow into that ratio
- offline custody is at the bottom inside Tier 0 ownership, outside connected runtimes;
  authority containment never implies a network route or shared physical administration
- Tier 1 enrollment clients use Tier 0 infrastructure issuance; optional application CAs
  can be shared in Tier 1 or local to a Tier 2 lab without automatic infrastructure trust
- prefer native Kubernetes deployments when product support, storage, capacity and recovery qualify;
  a container image alone is insufficient; bootstrap and independent outage visibility stay external
- Observability uses logs, metrics and distributed traces; Security Logging and Audit is the
  earlier Tier 0 traceability/evidence capability, not the same as distributed tracing
- Identity federation belongs to Stage 5: Identity; Stage 6: Secrets begins with Vault/audit/recovery.
  Stage folders use capability names, not implementation/runtime suffixes.
- Observability has its own Stage 8 after Secrets and the Tier 1 runtime; Development platform is Stage 9 and Lab environments is Stage 10
- Tier 1 Observability uses the existing Kubernetes cluster with separately scalable Collector,
  VictoriaMetrics, Data Prepper, OpenSearch and UI workloads; OpenSearch is included initially
- Netdata is also part of Stage 8: tier-local children, Tier 1 parents/live diagnostics and
  explicit metric bridging. Proxmox/BMC pollers and credentials remain Tier 0-owned;
  approved metrics may flow to Tier 1, never raw control access or Tier 0 Functions.
  The independent Tier 0 Netdata parent/critical alerts remain outside observed clusters.
- no all-in-one observability VM default or second Tier 1 syslog/archive; dedicated VM alternatives
  separate otel-N, metrics-N and search-N roles; their recipe supplies hosts/baseline only
- OpenSearch indexes approved scoped copies, without Tier 0 write/delete/retention/backup authority;
  document/field read filters do not revoke write privileges; native product installation is supplied,
  and Tier 0 supplies create-only approved field projections plus non-root persistent mTLS push.
  Each scope pins its approval policy; broadening it requires a new scope and review.
- Tier 0 supplies GET-only retained NetBox audit collection and independent Vault snapshot/input/media
  recovery transport. Separate source exports, source retention, credentials and physical recovery
  custody remain commissioned interfaces, not evidence of live acceptance.
- Cluster security collection uses Shared native Fluent Bit execution with per-node TLS identities,
  tier-local source catalogs and Talos patches; no signing key enters Kubernetes.
- Kubernetes OIDC is a Tier 0-owned guarded serial integration from each target tier's sensitive plan;
  original X509/Talos access and backend/state remain authoritative and independently recoverable.

## Working rules

- after major changes and before release handover, repeat the new-operator journey
  from hardware/network setup through every deployment option, operation and total-loss recovery;
  record unresolved work in [the hidden operator checklist](operator-walkthrough.md), not public roadmap text
- use the established software-engineer perspective for that walkthrough: newly installed servers
  and UniFi switches, programming experience but no assumed infrastructure-specialist knowledge;
  follow actual commands and handoffs, not only architecture roles or passing regression tests
- prepare and validate changes, review and stage the intended files, then hand the user exact
  signed commit and push commands. Never execute commit or push; signing is a manual user operation
- do not encourage storing secrets in Git
- do not treat this upstream as the destination for live environment changes
- prefer private forks, mirrors, or local copies for operational work
- lower-numbered tiers must recover without higher-numbered tiers; normal
  consumers use scoped service endpoints, while offline custody supplies transfers
- keep Packer, Terraform, and Ansible responsibilities separate
- the Shared baseline implements proxy settings, timezone and IPv6 policy only;
  a separate opt-in host_security role supplies SSH/chrony/firewalld/audit with tier-owned
  allowlists and access gates. It does not imply appliance, Kubernetes-host or egress enforcement.
- initializers and deployment entry points use umask 077 for new local files and backups;
  existing files and Windows ACLs need separate permission checks
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
