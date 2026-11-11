# Repository context

## Table of contents

- [Purpose](#purpose)
- [Repository intent](#repository-intent)
- [Documentation intent](#documentation-intent)
- [Working rules](#working-rules)

## Purpose

This file keeps durable context for AI-assisted work across sessions.

## Repository intent

- Architecture groups related functions into substantive domain chapters: Hosting includes Kubernetes
  and lab isolation; Cryptography includes trust and secrets; Delivery includes the development
  platform; Operations includes protected logging and observability. Stage names link directly to
  these designs rather than thin parallel landing folders. Background and organizational authority
  precede implementation choices. Keep request/response sequences beside the capability that owns
  their behavior, and explain when each design should be read to make a decision.
- Architecture chapters use continuous 01–11 numbering, with technical domains after context,
  ownership and the reference view. Operations uses the same domain names in six task groups,
  with configuration and executable tasks directly at the entry point. Its chapter numbers
  are independent of architecture chapters and deployment stages. Avoid rebuilding thin
  per-stage index folders; map all ten stages to their actual design and runbook homes.
- public homelab and small datacenter IaC baseline
- chosen virtualization platform is Proxmox; other hypervisors are not selectable implementations
- New deployments target Proxmox VE 9+; the selected 9.2+ path uses native HA/affinity
  and dynamic automatic rebalancing. ProxLB is an explicit alternative, never a second
  unqualified scheduler for the same guests. HA restarts fenced guests; it is not zero downtime.
- The common vm-template guide owns manual Alma/Rocky/Talos import. Fresh Talos examples
  select NoCloud UEFI-only, q35, non-Single VirtIO SCSI, fixed RAM and the guest-agent
  schematic. Explicit vm_firmware matches clones to publication; omitted fields preserve
  legacy BIOS behavior, not implicit firmware migration.
- Fresh Talos clones use a CloudInit/NoCloud drive at ide2 for static inventory IPs
  and gateway only; user/password/SSH/custom user-data remain unset. Optional DNS override
  is explicit; otherwise qualify Proxmox's inherited defaults. bootstrap_network = null
  retains the previous DHCP path. The Talos API still owns machine configuration.
- name capabilities by the goal, keeping implementation products explicit only where relevant
- Deployment READMEs own the complete numbered path and alphabetic choices. Link every child guide
  from its owning README at the actual action/decision; each option states its branch and rejoin.
  Dedicated filenames and titles match that route: step-<number>-<task>.md for main steps,
  step-<number><letter>-<task>.md for options. Companion guides share the path prefix;
  reusable guides spanning several steps or lifecycle operations live under procedures/.
  Optional lookup material belongs in docs/08-reference/, not beside numbered installation steps.
  Renumbering updates filenames, links and refresh-move targets together, not just README labels.
  Complete all selected paths before the next stage. Enhancements are scheduled after their real
  prerequisites, even when they extend earlier capabilities; never send a fresh operator to a future
  stage and back to finish a supposedly completed stage. Qualified existing/manual interfaces remain explicit.
- Foundation now has four numbered actions: hosts/networks, first manual Linux template, bootstrap,
  then managed publication/clone/recovery qualification. Select HA/SDN before guests, complete SDN
  authorization after bootstrap, and qualify guest HA/ProxLB before leaving Foundation. Old anchors remain.
  Linux host security belongs under docs/05-operations/01-hosting/linux-security.md and is first selected at
  Stage 1 option 4b after cache VMs exist, not a pre-guest Foundation deployment.
- Normal post-bootstrap deployment provisions the complete selected realization through IaC:
  Terraform owns guests, attached disks and state; Ansible owns guest filesystems, persistent mounts
  and service configuration. Reuse Shared's guarded data_volume role for dedicated XFS/ext4 volumes.
  Never turn guest mkfs/fstab work into an undocumented manual prerequisite. Existing data, UUID
  pins and mount declarations are preserved; missing storage requires recovery, not silent replacement.
  NAS-side exports/access/snapshots and offline signing/recovery custody remain explicit prerequisites.
- Apply stable extra-disk selection to every guest consumer, not only cache: match the
  Ansible device selector to the configured Terraform interface, using the scsiN by-id link
  for the reference SCSI disks, then persist by filesystem UUID. Kernel letters may reorder.
  Preserve local overrides and identity pins; test supplied extra-disk definitions against
  the actual service inputs, including generated output.
- Trace supported Linux VM settings through root types, environment normalization, module arguments
  and native resources. Terraform object conversions can silently discard fields. Retain root-specific
  placement/identity guards when extending common contracts; full clones and NIC filtering stay defaults.
- HSM guidance starts with an offline root, one hardware-backed issuer and independent recovery.
  Primary hardware profiles are YubiHSM 2 and PicoHSM; keep each replicated key/recovery domain
  within one qualified family unless cross-vendor transfer is independently qualified. Match
  original public SPKI, serial and object identity; labels alone do not establish key equality.
  PKI and HashiCorp Vault are the first path. Vault stays the reference secret service with
  default Shamir unseal; OpenBao signing is optional and must not silently replace or migrate it.
  Optional shared access comprises restricted native PKCS#11 remoting and an open-source signing API.
  The selected API direction is OpenBao stable external keys/PKCS#11 as a Stage 6 secret-service option,
  with actual HSM signing rather than software Transit keys protected only by an HSM seal.
  Keep state/quorum, physical key copies and client retry semantics separate. Avoid paid SignServer
  dependencies or stale Community forks; qualify recent integrations without claiming proven security.
- New guest deployment and diagnostic commands run from the controller: use native Ansible
  connection waits before facts, provision guest storage through Terraform plus guarded roles,
  and perform remote checks through Ansible/product APIs. Never require interactive SSH, manual
  guest package/repository setup or guest filesystem edits to complete a normal installation.
  Shared's baseline can install explicitly selected RPM sources and public OS trust anchors;
  custody approval remains separate from controller-driven certificate transfer/token commands.
- Prefer 3–8 character unqualified guest hostnames, including the instance suffix: boot-1,
  idm-1, log-1. Keep role abbreviations in docs/02-conventions/proxmox-conventions.md.
  This is a readability preference, not the DNS limit or SDN VNet's hard naming restriction;
  template/build titles and Kubernetes release/object names have separate contracts.
  Starter key/name changes never rename deployed guests, inventory or Terraform state automatically.
- The manual bootstrap example is boot-1 with Cloud-Init user automation and one or more
  approved workstation public keys, one per line. Their private keys stay on those workstations;
  the bootstrap execution account's outbound deployment key is configured separately.
- Verify bootstrap sudo independently of SSH-key login. Authorized passwordless sudo needs no
  account password or Ansible --ask-become-pass; keep that flag optional for password-based sudo.
- Software intake keeps the Tier 2 Squid/Keepalived pair small: explicit client/source policy,
  preserved HTTP freshness/privacy, sanitized structured decisions and native consumer verification.
  Reference cache storage selects the scsi1 by-id link, never assumes Linux disk letters match
  across clones, and uses Shared data_volume inspection/validation before stopping Squid or
  creating filesystems. Persist accepted mounts by UUID. VIP checks require the complete active
  member group before any disruptive test; malformed/missing IPv4 VIP prefixes are rejected early.
  A mirror-list service's domain does not cover returned mirror hosts. Explicit DNF source selections
  pin existing stanzas to approved HTTPS baseurls while preserving publisher trust settings.
  Galaxy's regional artifact redirects are reviewed choices or replaced by prepared collection
  archives; do not hardcode one observed regional hostname as a universal source contract.
  CONNECT is unscanned. The optional Tier 1 intake-1 realization uses native reposync/debmirror,
  pinned publisher verification, ClamAV on a sealed copy and immutable read-only HTTPS publication.
  Normal deployment uses one deploy.sh intake: Terraform provisions VM/disks and Ansible uses Shared's
  data_volume role to initialize only verified new blank storage, mount by UUID and grow XFS/ext4.
  This is Stage 3 option 3b after issuer/logging acceptance, not an unfinished Stage 1 option.
  Intake defaults select the scsi1 by-id link, xfs and /srv/intake; software_intake_data_uuid optionally pins existing
  data. Preserve recognized filesystems; an absent declared volume or conflicting fstab identity fails
  rather than formatting a replacement. Do not add manual mkfs/fstab prerequisites to normal
  post-bootstrap deployments. Approved feature-compatible packages/definitions, publisher keys and
  existing TLS remain external inputs; no signing keys are created. Fetch, scan and web identities cannot write
  accepted content. OCI/Trivy gates and opaque guest-filesystem scanning remain separate integrations.
  Keep publisher trust, malware assessment and vulnerability policy distinct;
  Tier 0 selects/verifies updates and retains independently usable supply. See
  docs/01-architecture/07-software-intake/01-verification.md. Do not reject every OS update for any CVE.
- Create boot-1 as a full clone, never a linked clone. Retain an offline VM backup with
  both OS/workspace disks and a tested restore path outside the failed platform. A full
  clone alone is not disaster recovery; original state, keys and approved tooling must survive.
- Reference bootstrap examples keep repos, private inputs/state, artifacts and upload staging on an
  attached data filesystem (/srv/tier0), with independent recovery copies. Prepare OS tools,
  Python wheels, Ansible collections and provider artifacts before restricted/offline deployment;
  transfer bundles by verified SCP/media rather than depending on the cache being installed.
  After Stage 1 acceptance, boot-1 consumes the approved internal proxy/mirrors for updates.
- Bootstrap Step 2a owns the copyable fresh OS-package and Terraform RPM-repository installation,
  followed by kit checkout and an explicit OS-package or isolated manifest-based Ansible path.
  Keep that sequence visible in the main path; control-node-tooling is its scope/compatibility
  reference, not a competing install recipe. Offline preparation follows the same dependency inputs.
  Name Ansible installation explicitly before verification/generation. OS-packaged ansible-core
  with compatible collections is valid for cache/compatible Linux recipes; a manual venv is not
  universally required. Keep the isolated manifest-based path for the full reference toolchain
  and explicit module/client needs; template commands prepare their own runtime automatically.
  Keep the local bootstrap intake recipe parseable on OS-packaged ansible-core 2.16;
  import_role already exposes defaults there, so do not add the 2.17-only public option.
  Verify intake readiness as a guide step before local configuration; do not require a separate
  true/false confirmation input in the playbook.
- An optional pre-install bootstrap-home path bind-mounts /srv/tier0/home at /home;
  preserve original homes for initial rollback, numeric ownership/ACLs/SSH keys and SELinux
  home contexts. Require data-mount ordering and independent console/reboot acceptance;
  both OS and data disks remain necessary for backup/restore. Do not change account paths.
- Bootstrap storage has an explicit Rocky LVM alternative: prefer enlarging the existing virtual
  disk, growing its PV partition, pvresize and lvextend -r. A new PV/vgextend is optional and makes
  root depend on all participating disks. For this layout /srv/tier0 is on root, so separate-data
  mountpoint and home bind-mount steps do not apply; backup/recovery follows the actual PV layout.
- Offline controller preparation uses source manifests, matching OS/Python/CPU, transferred
  RPMs/wheels/collection archives and locked provider mirrors. CONTROL_NODE_COLLECTIONS_MODE=check
  verifies installed collection bounds without acquisition; TEMPLATE_RUNTIME_MODE=check uses
  accepted preinstalled tooling. Controller preparation is not all-stage disconnected readiness.
- Administration groups host operations under hosts/, VM/templates under virtual-machines/,
  backups under backups/, and failure scenarios/product recovery under recovery/. Avoid the vague compute label.
- hosts/management.md owns first-use Proxmox registration from bootstrap: initialize common files with
  init-local-files.sh --setup foundation, edit hypervisors, authorize the execution key and test SSH/Ansible.
  Initialization creates no resources; deploy.sh foundation targets CA/directory guests, not physical hosts.
  Proxmox host recipes use separately authorized SSH/root or sudo, not the provisioning API token.
  Preserve Proxmox's cluster-managed root authorized_keys symlink and existing keys.
- provisioning.md owns destroy/retirement and terraform-state.md owns inspection, exact binding removal
  and per-deployment retirement. Recovery retains original state, keys and data; new installations
  use fresh collections after accepted teardown. Never forget resources awaiting restoration.
- Recover a VM, failed non-HA host or whole Proxmox platform through the bootstrap and independent
  recovery set. Restore both bootstrap disks and compare its state age with the latest independent
  copy. Establish cluster membership on empty nodes before restoring guests; never generate new
  service identities to disguise missing data. Offline tooling does not supply guest repositories.
- Kubernetes is the cluster goal; Talos is the current node-OS implementation example,
  not an architecture requirement. Immutable AlmaLinux or other OS support needs future lifecycle code
- public cluster entry points are `terraform/deployments/kubernetes/` and
  `scripts/kubernetes-cluster.sh`; retain existing Talos state, inventory, provider,
  and credential contracts. The old script delegates; old roots require deliberate migration
- `docs/03-deployment/stage-4-kubernetes/procedures/kubernetes.md` owns cluster choices and common readiness;
  its `talos-terraform.md` sibling and stage's `step-1b-existing-cluster.md` own implementation procedures
- The complete supplied human-SSO rollout qualifies Talos 1.13.x and requires the original
  Terraform-owned plan. Manual cluster credentials survive later guides, but that alternative's
  SSO configuration persistence/rollout/recovery implementation is still a recorded gap.
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
- all downstream root READMEs link to architecture's root `platform-standards.md`, beside README.md;
  this worksheet records only local naming/tag choices and the selected per-zone
  network plan (VLAN, short VNet ID, alias, subnet and gateway). Individual guest
  assignments stay in inventory, with design and recovery in separate docs
- link VMID and other maintained conventions rather than repeating their allocation rules;
  network tables distinguish SDN VNet ID (2-8 lowercase alphanumeric characters, no hyphens/underscores)
  from the readable network label/Alias and VM/DNS names
- docs/02-conventions/ is the shallow front door for maintained VMID, naming/tag and network-allocation guides;
  platform-standards.md is the project-owned selection sheet beside the generated architecture README.
  Preserve older naming-conventions.md records on refresh; link them for manual review.
- docs/02-conventions/vmid-convention.md owns the central VMID quick reference and editable SVG.
  Starter IDs use T C NN; Tier 0 uses the same category hundreds, with a Kubernetes exception:
  control planes 100-149, workers 150-199, infrastructure 2xx, network 3xx, logging 4xx,
  bootstrap/automation 5xx (manual boot-1 501, runner 511, optional ceremony 521).
  3xxx labs and 4xxx clients remain Tier 2-owned, 9xxx templates/builders Tier 0-owned.
  Existing local IDs/state are never renumbered by refresh; new example IDs are not a migration.
- `docs/auto-docs/` holds upstream reference docs with visible refresh/do-not-edit
  notices; existing root READMEs/project templates remain project-owned and are not overwritten;
  refresh recreates missing current starters
- Fresh architecture repositories contain a short README, docs/README.md design/navigation record,
  platform-standards.md and a root deployments.md completion checklist, plus the full auto-docs manual.
  The checklist uses real Markdown tasks for main deployments and nested options, with guide and
  owning-repository links. Check after completing the linked path, not merely Terraform provisioning;
  keep acceptance evidence separate. Preserve local checks/notes on refresh and seed missing records.
  Do not seed a second domain/workflow/site hierarchy. Preserve old project documents
  on refresh; consolidation is manual, with local runbooks added only when needed.
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
- optional SDN subnet lookup uses one applied IPv4 subnet/gateway per selected VNet:
  Linux network entries select sdn_lookup; Kubernetes bootstrap_network selects sdn_vnet.
  Tier-owned Terraform calls Shared's stateless read-only helper through the external provider;
  token/TLS environment, SDN.Audit and tier-local IP inventory remain required. Explicit inputs still work.
- refresh uses `.generated-files.json`, updates kit automation and preserves configuration/project edits.
  Current *.example targets are kit-owned references: always replace them on --refresh, even if edited,
  formerly owned or unrecorded. Never overwrite their live counterparts. Flag changed/restored examples
  with adjacent live files in the final yellow review, linking the refreshed example; env.local.example
  maps to .env.local. Print paths only, avoid unchanged-example noise, and keep dry runs write-free.
  Back up edited tracked automation under collection-level .refresh-backups/ before replacement;
  --code-conflicts preserve keeps local code, while ask offers an interactive choice (Enter preserves).
  Unknown existing paths and new project files remain protected. Recreate missing current
  generated targets, including owned starters. Deletion resets a target to its current template;
  Kubernetes Terraform currently uses Talos in tier-owned automation; `clusters/` service starters
  remain project-owned adoption points, not the native application installers
- Refresh ends with a manifest-scoped review: yellow preserved differences get current rendered
  templates under collection-level .refresh-review/, outside Git repositories; red identifies
  retained retired outputs outside auto-docs; REPLACED prints the previous code's backup path.
  Under docs/auto-docs/ only, remove all obsolete/extra
  files (including edited/untracked files and old redirects), prune empty directories and clear
  their manifest entries. Print REMOVED / WOULD REMOVE with known replacement guides.
  Preserve edited current auto-docs. Never classify private inputs or arbitrary project additions
  outside that managed tree as obsolete. Dry runs remain write-free, including cleanup.
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
  docs/01-architecture/11-operations/02-log-retention.md owns this choice; Stage 2 options 3c/3d guide it.
- Logging implementation: Shared owns stateless `log_forwarder`; tier inventories,
  source keys/cursors and selectors stay local. Tier 0 owns reviewed-CSR signing,
  receiver, create-only NAS checkpoints, audited application filesystem views and
  independent restic jobs on a separate recovery host. NAS accounts/snapshots and
  independent storage are commissioned prerequisites, not collector privileges.
  Native sender release is transport-based; expose the unprotected tail explicitly.
  This bounded-loss main path is not replicated intake or WORM. See `docs/08-reference/logging-pipeline.md`.
- All source Linux, template and Kubernetes Terraform roots verify Proxmox TLS. Provisioning
  entry points reject current/legacy insecure environment flags; bootstrap trusts the Proxmox CA.
- Linux VM, Kubernetes and LXC NIC resources explicitly enable Proxmox firewall participation;
  provider omission defaults false and must not silently clear a clone's flag. Template
  nic_firewall defaults true with explicit catalog overrides. This does not enable the
  Datacenter/guest firewall or install rules; preserve the separate policy/acceptance gates.
- .ai/operator-walkthrough.md tracks missing mechanisms separately from supplied code;
  .ai/operational-verification.md owns unchecked live pass conditions for the current priorities.
  .ai/v1-readiness.md records implementation qualification and its exact offline evidence.
- Internal ACME remains integration; public HTTP-01 has Tier 2 automation with verified origins,
  separate staging/production state and a serialized controller timer, still requiring live acceptance
- Tier 0 owns publication catalogs, creation/update CD jobs, publication state,
  `template-refresh` and `immutable-template` builders, all template modules,
  Packer definitions, and the local publication script; shared holds only approved
  consumer references, not image recipes or lifecycle ownership
- Template tags describe reusable images: `el10` plus `alma`/`rocky`/`rhel`, configured
  guest CPU model, conditional `cloud-init` and explicit per-build extras. Use the CPU
  model tag alone, without a redundant generic architecture tag such as `x86_64`.
  Leave x86 CPU architecture implicit; explicitly setting it requests a root-restricted API operation.
  Do not inject `template`, tier ownership, bare `el` or redundant `rocky10`/`alma10` tags.
  Successful template apply synchronizes consumer references into the existing sibling Shared catalog
  after Terraform, policy checks and state refresh succeed. It preserves the default selection and
  older entries; clone tests and selecting a default/per-VM image remain explicit. No Git commit or push occurs.
  Standalone publication without Shared reports skipped synchronization; exported absolute
  TEMPLATE_SHARED_CATALOG_FILE selects another existing catalog for CI. Consumers never read Tier 0 state.
- Tier 0 owns all hardware-facing control, including hypervisors, physical networks,
  storage administration, and every VM template lifecycle across all consuming tiers
- initial template publication is foundation local automation, before managed VMs
  or hosted tooling; generated Tier 0 fast paths start with the template catalog
- Template Ansible actions automatically prepare a tier-local ignored `.venv/` runtime;
  `setup` prepares it without platform access. Keep bootstrap Python/Ansible separate
  from native Ansible dependency convergence. `TEMPLATE_RUNTIME_MODE=check` uses
  prebuilt tooling; CI never prompts for OS privilege escalation. Tier 0 remains standalone.
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
  its authoritative contract is docs/01-architecture/04-hosting/02-provisioning.md
- docs/03-deployment/foundation/ contains unnumbered host/network/access/template prerequisites;
  docs/03-deployment/README.md indexes ten numbered capabilities: software intake, protected logging,
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
- Keep figures free of VMIDs, literal IP/MAC allocations and configured disk/RAM/CPU sizes. Use stable
  role/resource labels, interfaces and source links for correspondence; exact allocations and sizing
  belong in inputs/reference tables. Convention format illustrations remain reference exceptions.
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
- Stage 6 can provision optional `mon-1` through the original Tier 0 foundation root with
  `--terraform-only`; preserve the issuer/directory guest and IP maps/state. Its commented starter
  stays disabled earlier. Baseline, producer enrollment and monitoring installation follow separately;
  an accepted existing host is the alternative, and one VM is not HA.
- one receiver is bootstrap only; HA acceptance specifies durable acknowledgement/replication semantics,
  independent failure domains, bounded queues and protected retention; UDP and source-loss gaps stay explicit
- each stage has a main README with numbered local steps, diagrams, a capability result,
  and links to the static architecture; named monitoring/Observability/collection deployments
  belong to their owning stages, not one cross-stage procedure
- tutorials follow the historical May-era manual Rocky/Alma template guide's action-by-action style,
  not a fixed three-step program. Use as many numbered actions as required in their real execution
  order, with one copyable block per concrete action, short expected results, exact local files/fields
  and explicit working repository/machine. Preserve user-supplied sequences and meaning while editing.
  Keep OS packages separate from Python environments; put EL10/Debian/Ubuntu differences beside
  the affected action and retain Talos only where it is the actual implementation.
  Re-derive guide workflows from actual prerequisites, installer order, operator state and completion
  criteria; don't preserve inherited phase headings merely while polishing their prose. Future-client
  defaults are distinct from configuring current hosts. Keep coherent capability milestones when sound.
  Required procedures are named parts of the main path; alternatives branch/rejoin as 2a/2b.
  Keep design explanations in their authoritative homes instead of burying actions in prose.
  End copyable blocks before manual comparison/acceptance gates; checksum display and extraction
  must be separate actions. Required sub-actions use consecutive numbers, with choices/rejoin explicit.
- Prefer standard OS tools already required by the workflow. The bootstrap LVM guide uses
  parted for both existing-partition resizing and new-disk partitioning, with native LVM commands;
  do not add growpart as a prerequisite. The supplied new-disk sequence remains distinct from
  enlarging an existing disk/PV.
- Configuration examples name their variable definitions near the top, with paths relative to the
  identified repository root. Terraform `.tfvars` points to its deployment's `variables.tf`;
  shared profiles identify the consuming tier, and template YAML points to its build schema and
  catalog mapping. Keep defaults/types in source rather than duplicating a variable catalog.
- Command examples use `<prefix>` for the generated folder prefix (default homelab),
  separate from hostname/environment prefixes. Put the owning root/machine in bold above each
  command/configuration block; use inline code for exact file paths and variable names.
  Prefer short prose or file lists for editing instructions, not commented path blocks.
  Use the actual fence language (bash/yaml/hcl/dotenv); text is for output/file trees.
  Avoid comments when prose is clearer. If retained comments explain the code, separate logical
  groups with blank lines and indent wrapped comment text consistently.
  Preserve shebangs, Cloud-Init headers and literal file content. Replace pure repository-navigation cd lines
  with that context. Retain operational cwd changes when command semantics require them.
  Do not assume vi/vim/nano or another editor. Do not execute path lists as shell.
- Present deployment commands in operational order. Linux deploy.sh already displays its
  plan before interactive apply; a separate preview is optional. Template/Kubernetes saved
  plans retain their dedicated sequence. Label post-apply plans with their verification
  purpose and required/optional status. Preserve explicit state-reconciliation and identity
  acceptance gates; never present a later check as the prerequisite plan for an earlier apply.
- administration uses task/FAQ navigation and short operator runbooks: execution host/repository,
  prerequisites, exact inputs, numbered commands, expected result and stop/rollback paths.
  Preserve recovery/custody gates; link design rationale to architecture. Backup theory lives in
  docs/01-architecture/11-operations/04-backup-recovery.md; provider field details belong in reference docs.
- normal Linux deploy.sh calls Terraform apply once, with its native inline plan/approval;
  --plan-only is optional and --auto-approve uses -input=false for approved CI. Dedicated
  template/Kubernetes saved-plan workflows and manual signing/activation gates remain explicit.
- deployment guides name the working generated repository and upstream source directory near the top;
  IaC tables distinguish tier-owned inputs/resources from Shared helper implementations;
  docs/03-deployment/README.md#repository-locations owns the checkout/path convention
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
- controlled software intake is documented in docs/01-architecture/07-software-intake/README.md;
  Squid/VIP supplies the existing explicit proxy/cache, not a mirror or patch controller
- Stage 1 Step 7 explicitly commissions Proxmox host update access using Tier 0's existing
  proxmox-hosts.yml recipe (Datacenter download proxy plus per-host APT), then links controlled
  one-host-at-a-time maintenance. Hosts pull through the proxy; the cache gets no host authority.
- software intake is a separate early capability at docs/03-deployment/stage-1-software-intake/,
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
- shared USB access uses Tier 0 device VMs with one local token per host and pinned private endpoints;
  native remoting has no mandatory VIP, extra load-balancer pair or Tier 1 dependency
- two enabled service hosts are a starter, not a limit; choose N using measured traffic,
  operation/session mix, latency and failure/maintenance headroom; size VIP/proxy capacity separately
- Vault consumes HSM-backed key generation/private-key operations where supported;
  the HSM service does not require Vault to bootstrap, and seal integration is a separate choice
- single-device custody plus independent backup can satisfy initial deployment;
  deployment adds the replicated variant when selected consumer availability requires it,
  not automatically because Vault or a registry exists; root custody stays offline
- external application endpoint variants E1 client failover, E2 private VIP and E3 co-hosted
  VIP/proxies remain qualified integration choices. They are not the native SSH remoting path.
  E3 requires supported application HA; VIP ownership is separately active/standby
- application state, key replication, sessions and device/key readiness have separate contracts;
  a TCP check or duplicated key material does not prove application HA
- optional HSM ingress targets hsm_gateways, defaults disabled and requires explicit HA/readiness
  acknowledgements; it renders a backend scaffold only, never a complete signing/VIP installer
- edge ownership refresh preserves old code, live inputs, registrations and state;
  migration is deliberate and must avoid a second state managing the same VM
- use purpose-named networks and example firewall zones DMZ, Services, and Control;
  Fabric groups hardware management, Corosync and Ceph host transport, outside guest SDN.
  Control is the privileged VM-services zone; do not introduce Infrastructure as a zone alias.
  Layers can contain several policy zones; tier ownership never names a zone.
  shared zones do not imply shared subnets or unrestricted access
- `network_zones` remains a logical guest-network input, not a firewall zone;
  generation does not allocate subnets or configure gateway policy
- keep network placement and firewall contracts in architecture/networking/, and
  vendor-specific zone-matrix translation in deployment/foundation/network/
- Tier 0 includes connected high-impact control systems; only selected custody
  and recovery assets are air-gapped; artifact handoffs do not create routed access
- protect the acceptance path, jobs, runners, and credentials for privileged
  changes at the target tier; a runner tag alone is not an isolation boundary
- use general capability terms in architecture docs, such as source control,
  identity authority, identity provider (IdP), OIDC interface, inventory source of
  truth, observability dashboard, and cluster management

## Documentation intent

- docs/01-architecture/README.md owns the seven foundational capabilities and reference placement map;
  use named services, tiers vertically (2, 1, 0), and layers horizontally (Edge, Application, Control)
- domain diagrams expand the same capabilities into components, runtimes and cross-tier consumers;
  product names belong in reference realizations, not the top-level capability map
- IAM is the overall identity and access management capability, not a VM; directory authority/IdM
  and identity provider/IdP are separate roles; LDAP user federation is not identity brokering
- reference IdM and IdP remain Tier 0/Control; a consumed login interface does not move the IdP
  into Services or expose its administration; management is a network, not another layer
- reference-platform.md allocates components; runtime-flows.md owns cross-domain service interactions;
  domain designs expand those functions without becoming an installation sequence
- hosting/ owns execution, virtualization, orchestration and protected resource lifecycle;
  hosting/kubernetes.md owns the three-tier topology; data/ owns storage interfaces and persistence;
  software/ owns software lifecycle, intake, source/build/artifact/release functions;
  networking/ owns service reachability and publication, distinct from software delivery
- delivery/controllers.md owns the independent Flux, Argo CD and Spinnaker boundaries
- variants.md records stable consumer contracts and different guarantees; detailed alternatives stay
  inside their owning domain; project architecture records one compatible selected composition
- upstream reference views follow overview, relationships, domains and detailed variants;
  project starters link them from compact design and deployment records, without duplicating the tree
- hosting/, networking/, data/, identity/, cryptography/, software/ and operations/ own capability designs;
  zero-trust access, scaling, failure domains and recovery constrain all seven rather than form stages
- architecture is the static intended design: context, components, interfaces, variants and constraints
- docs/03-deployment/readiness.md owns acceptance criteria; generated deployments.md owns site completion
  tracking and selected options; the deployment index owns stages
- use direct IT-domain directories, not intermediate system-design/subsystem-design indexes
- design records contain required guarantees, never stage-based states or current readiness
- hardware signing-custody rollover is an administration procedure, not an architecture page;
  implementation-support.md#stage-coverage owns the concise installer-coverage verdict
- readiness is independent per capability, and option letters are not a ranking or CLI flags
- cryptography supports software, single USB, replicated USB and network-HSM designs;
  service seals are separate choices; do not imply every option has an installer
- deployment/, development/, and administration/ separate installation, code and operations;
  06-paths/ contains only short repository checklists; 08-reference/ contains exact contracts
- development/ opens with a visual repository map and fast edit routes; code-layout.md maps real
  entry points, tier inputs and Shared calls, while adding-service.md and debugging.md give short recipes
- developer examples name the working repository, distinguish private live inputs from upstream examples,
  reuse actual modules/roles and link exact contracts instead of repeating long input/tooling explanations
- Tier/Shared generated repos retain seed-owned code-specific workflow records;
  the architecture repo has a platform record, deployment checklist and standards; auto-docs is the main manual
- foundation docs are grouped in bootstrap/, proxmox/, network/ and storage/.
  bootstrap/README.md owns independent execution/recovery tooling and its numbered storage/offline paths;
  Proxmox hosts, templates, HA, SDN and API setup belong under proxmox/. Reference VM hosting does not
  make bootstrap a hypervisor capability. proxmox/templates.md
  owns the shared Alma/Rocky/Talos wizard. Mutable Linux refresh belongs in administration.
- refresh retains existing project records and links them from new starters; unchanged
  moved auto-docs become compatibility pointers only in existing collections
- Refresh review focuses on automation/configuration: omit README and prose-document differences
  from yellow/red warnings and routine preserve messages, without changing their ownership.
  Keep configuration/requirement comparisons, replacement backups and actual auto-doc cleanup visible.
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
- follow [diagram conventions](../docs/04-development/diagrams.md): Tier 2/1/0 top-down,
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
- the Shared baseline implements proxy/package-source policy, explicit public trust anchors,
  timezone and IPv6 settings;
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
