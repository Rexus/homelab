# Repository context

## Table of contents

- [Purpose](#purpose)
- [Repository intent](#repository-intent)
- [Documentation intent](#documentation-intent)
- [Working rules](#working-rules)

## Purpose

This file keeps durable context for AI-assisted work across sessions.

## Repository intent

- Foundation and all ten stage owners end with an explicit numbered securing checkpoint linked to
  docs/05-operations/01-hosting/guest-hardening.md. Baselines apply during deployment; closeout accepts
  selected controls, temporary-access cleanup and independent recovery without requiring a later stage.
  Secure Boot, vTPM and encryption are separate qualified choices, not universal late toggles.
  docs/05-operations/deployment-commands.md owns the compact setup/configuration/command index.
- Foundation Step 11 explicitly commissions the physical Proxmox servers: management/MFA/TLS,
  the accepted signed host boot chain and physical TPM 2.0 where supported. Firmware activation
  is a vendor-console action, preferably before a fresh host install; Tier 0's native host recipe
  prepares inspection tools and performs read-only enforcement/local TPM proof from bootstrap.
  Keep host TPM, guest vTPM and USB HSM custody distinct. No implicit host disk-key sealing or
  remote attestation is claimed. Firmware/motherboard/dbx changes require independent consumer
  recovery, one-host maintenance and post-boot checks; never clear a TPM as a generic repair.
- Stage 2 supplies separate repository/pin-discovery and controller-only portal CSR recipes. They do
  not initialize a CA or approve issuance. Retire seven-day bootstrap portal TLS through the existing
  requester/approver workflow and issuer reconciliation, preserving the portal key and CA identity.
- Single USB can grow to a same-family provider pool at the Stage 6 decision point. Preserve original
  wrapping material and issuer identity from commissioning. The explicit openxpki-pkcs11-migrate
  recipe changes only the qualified provider binding, with fresh independent backup, planned outage
  and latest-history rollback; ordinary convergence remains immutable. One remote endpoint is an
  explicit temporary transition before moving the original device to the second host, never HA.
- Restricted package consumers select fixed official endpoints or commissioned internal mirrors.
  The Shared baseline source profile is preserve by default; fresh supported proxy consumers select
  official Rocky/Alma/Debian/Ubuntu sources without enabling repositories or weakening trust.
  Explicit DNF and complete APT selections take precedence. Debian cloud mirror+file sources are
  handled before package dependency installation. Keep source endpoints and proxy policy aligned;
  no automatic arbitrary mirror fallback or broad allowlist is added.

- Stage 2's fresh foundation input selects ca-1 only; directory members are an explicit Stage 5 choice.
  foundation initialization also creates missing issuer.yml, preserving existing local inputs/state.
  OpenXPKI currently requires Debian 12 amd64; HSM provider/ceremony hosts may use EL10. Keep the Debian
  cloud image, guest-agent preparation and per-VM template selection visible in Foundation.
  Step 1 establishes/restores the separate offline root; Step 11 returns to that same instance for
  subordinate signing. Root and issuer custody are independent choices: local USB protects ca-1's
  issuing key, not automatically the root. Never provision an online root VM as an implicit prerequisite.
- Bootstrap and ceremony host are distinct responsibilities. Prefer a dedicated trusted workstation
  for HSM commissioning/recovery. boot-1 is a deliberate constrained/learning choice for the online
  issuer's device, with paused jobs, restricted access and temporary recovery/USB cleanup. It is not
  offline root custody. Retain recovery independently of bootstrap, its snapshots and the issuer.
  PicoHSM commissioning preserves the original DKEK/wrapped key for later replicas. Read-only native
  preparation may discover an unknown serial, but normal deployment requires its exact accepted identity.
  HSM is a general key-protection capability: CA, secret-service and application consumers retain
  separate keys, permissions and recovery. Offline root devices are not online pool members. Raw
  token remoting has no per-object policy; do not promise shared-device isolation from key labels.
  Vault native PKCS#11 seal remains Enterprise/device-mechanism qualified; default unseal is Shamir.
- New compatible vendor Linux installations use the tested signed UEFI profile and fresh per-VM
  TPM 2.0 through the generic `tpm` object. TPM-free template evidence is explicit in the applied
  Shared catalog. Existing/adopted TPM state is preserved. Existing VM addition uses Tier 0's
  native controller-owned proxmox-guest-security recipe with inspect/prepare/check/apply operations.
  The tier-local guest-boot-security recipe installs native inspection packages when requested,
  then proves Linux Secure Boot and TPM 2.0 through normal Ansible access. It performs no key sealing.
  Stage 4 option 5a is fresh signed NoCloud ISO installation with unique EFI/vTPM, signed matching
  1.13.x installer and optional TPM-bound STATE/EPHEMERAL encryption, selected by default on this path.
  Option 5b retains the existing template route. The cluster wrapper guards existing boot/encryption
  policy and verifies signed nodes through authenticated Talos APIs after apply or verify-security.
  ISO ejection uses install_media_attached=false after installed-disk acceptance.
  Common maintenance retains signed trust, EFI/TPM state and independent recovery through changes.
  Physical TPM, software vTPM, USB HSM signing custody, PKI and restricted network access remain
  complementary controls. Boot/security checks and source tests do not qualify live recovery.
- Deployment stage folders use zero-padded two-digit numbers (stage-01 through stage-10) so
  lexical/GitHub sorting follows the installation sequence. Update references and migration targets
  together; retain former route keys so project-owned links survive generated-documentation refresh.
- Availability is explained in docs/01-architecture/04-hosting/05-availability.md. Distinguish
  active-active, active-passive and automatic VM restart (Proxmox HA); neither topology nor
  the product's HA label proves uninterrupted service. Tie acceptance to measured outage,
  data guarantees, independent failure domains and the scaling/headroom budget.
  Tier 0's ansible/playbooks/proxmox-ha.yml manages selected existing guests and affinity through native
  modules. Keep initial Terraform placement separate from continuing Proxmox placement.
  Use one separation rule per voter/replica set, and record rule-blocked degraded operation.
- In every diagram, choose boundaries for the reader's question. Logical service views show actual
  networks and runtimes, without decorative Proxmox-host wrappers. Include physical hosts for host
  placement, availability/failure domains, capacity, storage attachment, passthrough or host operations.
  Code/workflow views retain their own relevant boundaries; do not invent a physical or network layer.
- Diagram labels use short noun phrases: Tier 2; Cache Edge Network / external_edge; Cache Services.
  Keep useful exact IaC identifiers. Put instance counts, existing/new status, step references and scope
  explanations in captions or nearby inputs, not enclosing titles. Drawn instance counts illustrate
  the referenced configuration, not a fixed capability size. Preserve meaningful protocol/quorum contracts.
  Name cluster runtimes Tier 0 Kubernetes, Tier 1 Kubernetes or Tier 2 Kubernetes so the deployment is clear.
- Apply the existing global AGENTS.md visual reference to all block diagrams, not only IAM/IdP.
  Compose inside out: compact server/replica stacks vertically, peer service groups horizontally,
  and outer zones/ownership boundaries vertically where the model requires it. Preserve left-to-right
  consumer/provider order and the near-4:3 composition target. Use distinct routing symbols, dotted
  service groups and the project palette. Verify rendered geometry rather than merely declaring directions.
  Operations capability guides open with their complete selected deployment; focused task diagrams follow.
- Review rendered figures as reading tasks: trace the main path, check headings and connector labels,
  and split competing placement, request and health/recovery questions. Successful parsing, palette
  matching or collision checks alone do not establish a clear picture. Reuse one editable asset when
  deployment and operations show the same selected scope, so visual repairs reach both reader paths.
- Step 11's basic platform placement uses docs/08-reference/diagrams/kubernetes-platform.svg.
  Its service stacks, existing dependencies and source links retain one scope. Explicit node stacks
  in platform-cluster-runtime.svg and the control/workload runtime figures illustrate the linked starter
  inputs. Use editable SVG when Mermaid's compound ranks stretch cells or break the required placement;
  keep new assets registered with the generator and checked against actual inventory/module inputs.
- Static Mermaid block/flowchart figures declare Arial at 14px in both the root fontFamily setting and
  themeVariables; the root setting is required for consistent HTML labels in the reviewed renderer.
  Keep sequence/plot colours theme-aware. See docs/04-development/diagrams.md for the exact source contract.
- Sequence views order participants from consumer to authority and time downward, distinguish
  requests from responses, and group phases with `rect`. Keep service-local authorization separate
  from authentication and choose exchanges for the actual protocol. Reuse the
  [identity Service access reference](../docs/01-architecture/09-identity/README.md#service-access).
- In tiered placement views, keep Tier 2 as the top ownership row. Internet/upstream sources and external
  clients sit to its left. Tenants and users enter their target owner's listener from the left. Keep actual
  lower-tier consumers below their upper-tier provider. The project diagram guide owns this placement rule.
- Put the opening figure after a short introduction, before contents, long prerequisites or inputs.
  Architecture starts with context/placement; deployment starts with its expected result; operations
  starts with the selected running deployment. Introduce substantial enhancements at the start of
  their own section, keep alternatives separate, and refer to stable figure anchors from related steps.
  Focused procedures can link the owning overview instead of repeating it.
- Keep diagram colour roles distinct using docs/08-reference/diagrams/palette.json: pure gray tier shades
  (Tier 2 lightest, Tier 1 medium, Tier 0 strongest), independently styled protection zones
  (light rose DMZ/Edge, medium blue Services, stronger green Control),
  blue-gray Kubernetes, gray-rose networks, warm beige traffic interfaces with dark text, mauve policy/access rules,
  peach actions, violet data and amber offline custody. Incoming policy annotations sit outside the destination
  tier/zone/runtime, with a dashed association directly to its ingress/listener. The association leaves
  routing and policy ownership with their actual components.
  Actual controllers and native policy resources remain in their real hosting/configuration boundaries.
  Tier ownership is not a protection-zone colour; retain the existing zone/component palette inside it.
  Inner function/service, deployment and replica/failover groups use dotted light neutral gray.
  Actual networks, hosts and Kubernetes runtimes use solid outlines. Preserve violet storage and amber custody.
  Use dotted deploymentGroup boundaries for logical service collections, never label them as networks.
  Keep IdP state below its application; offline custody sits at the bottom outside connected runtimes.
- Identity deployment and operations share docs/08-reference/diagrams/identity-operations.svg for 4:3 placement:
  IdP state below Keycloak, and a full-width offline custody row below connected services.
  The SVG is editable source and a registered generated-documentation asset; its geometry is checked.
- Identity federation uses native Keycloak ordered LDAPS member URLs in `control_applications_ldap_url`.
  The starter tries idm-1 then idm-2, with bounded connection/read timeouts and member TLS identities.
  Diagrams show direct endpoint failover. Acceptance includes a real application login during member loss.
- Native SVG palette selectors target individual semantic classes. Combined outline resets change dash
  patterns only. Review computed browser colours to catch inherited overrides as well as source declarations.
  The cache block-beta trial obscured titles and crossed its VIP with the upstream arrow, so its SVG remains
  the compact service-layout reference. Mermaid remains appropriate where its actual render preserves layout.
- Cache deployment and operations share docs/08-reference/diagrams/cache-services.svg. Lower-tier callers
  sit below Tier 2 and request its VIP upward; Cache Services request approved sources or an optional
  parent proxy to the left. Preserve actual request direction when tier placement overrides the normal
  consumer-to-provider reading order. Replies use established connections, not invented routing hops.
- Number deployment actions by the edit/run/check the operator performs next, with as many
  sequential steps as the implementation needs. Do not compress a workflow into a few numbered
  phases with another numbered installation hidden behind each link. Keep the normal path on
  its owning page; use separate pages for actual selections, later maintenance or reusable detail.
  Name already completed IaC work explicitly when a later idempotent run verifies/reuses it.
- Service-facing DNS uses stable, familiar lowercase functional labels, usually 2–8 characters:
  iam/auth/idp/sso, ldap, dc where applicable, smtp/imap/pop/mx, proxy/cache, git, db, nfs,
  ca/secrets, registry, logs/metrics, cd/release. docs/02-conventions/service-dns.md owns this rule.
  Default <service>.<platform_internal_domain>; environment/project scopes are optional. Keep numbered machine
  identities separate and preserve required protocol member names, discovery records, TLS SANs
  and canonical issuer/client URLs. This preference is not a DNS limit or an automatic rename.
- Host-domain selection follows administrative status. `platform_internal_domain` owns standalone
  hosts and stable internal service aliases; `platform_domain` owns directory-enrolled host identities.
  Per-host `platform_domain_role` is standalone by default, member after enrollment, or authority for
  directory server commissioning. `platform_host_domain` selects the suffix; `platform_fqdn` combines it
  with the hostname. Put the role in inventory/host_vars or an inventory group, never all.yml extra vars.
  Fresh examples use internal.example.com and corp.example.com. A subdomain of a registered domain
  under the operator's control or a private .internal namespace is valid; avoid .local mDNS conflicts.
  IANA selected .internal; ICANN permanently reserved it from root delegation. Keep source examples generic.
  Older inputs without platform_internal_domain fall back to platform_domain. Shared defaults
  baseline_manage_hostname to false; fresh inputs enable it. Refresh preserves project inputs.
  Prepare DNS/TLS/consumers before deliberately changing hostname inputs and enabling hostname management.
  Naming-role selection requires the real enrollment/commissioning workflow; it supplies no enrollment itself.
  Existing FreeIPA/Kerberos enrollment material blocks baseline hostname changes. Use the directory's
  supported rename/re-enrollment procedure; fresh authority commissioning can receive its intended FQDN.
- Lead deployment guides with the expected result figure, before long contents or input tables.
  Introduce a major enhancement with its own result figure where that installation begins, and
  reference named figure anchors from the actions that create/configure/verify its parts.
  Architecture teaches the completed system through placement, request/response and dependency
  views with concise explanations; avoid replacing that journey with introductory link catalogs.
  Primary communication/dependency flow reads left to right, provider or authority to the right,
  while tier stacking, protection layers, real return/alert traffic and custody transfers retain
  their higher-priority meanings. Aim near 4:3 by composition and verify rendered placement.
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
- Delivery architecture describes release orchestration, change authorization, desired-state
  reconciliation and dependency readiness as logical capabilities. Product choices fulfill those
  roles; keep their exact mapping, versions and native control evidence in implementation references
  linked from deployment and the concise decision record. Flux is the selected reconciler with
  dependency ordering, not a general release-workflow orchestrator. Keep logical figures product-neutral.
- public homelab and small datacenter IaC baseline
- chosen virtualization platform is Proxmox; other hypervisors are not selectable implementations
- New deployments target Proxmox VE 9+; the selected 9.2+ path uses native HA/affinity
  and dynamic automatic rebalancing. ProxLB is an explicit alternative, never a second
  unqualified scheduler for the same guests. HA restarts fenced guests; it is not zero downtime.
- The common vm-template guide owns manual Alma/Rocky/Debian and retained Talos raw import.
  Debian 12 uses the full-kernel generic image with a prepared QEMU agent for Q35/ide2 compatibility;
  require cloud-init/media/network acceptance separately from a successful guest-agent response.
  Fresh Kubernetes starters instead select signed NoCloud ISO installation with unique EFI/TPM
  and encrypted system volumes; retained raw-template examples use unsigned UEFI-only boot.
  Both use q35, non-Single VirtIO SCSI, fixed RAM and the selected guest-agent schematic.
  Explicit vm_firmware matches the chosen boot route; omitted fields preserve legacy BIOS behavior.
- Fresh Talos nodes use a CloudInit/NoCloud drive at ide2 for static inventory IPs
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
- Foundation has eleven numbered actions: hosts/networks, first manual Linux template, bootstrap,
  then publication, clone/recovery qualification and selected HA acceptance in actions 4-10,
  followed by physical host and retained guest security commissioning in action 11.
  Bootstrap has nineteen sequential actions; template-refresh remains separate later maintenance/state. Select HA/SDN before guests, complete SDN
  authorization after bootstrap, and qualify guest HA/ProxLB before leaving Foundation. Old anchors remain.
  Linux host security belongs under docs/05-operations/01-hosting/linux-security.md and is first selected at
  Stage 1 option 8b after cache VMs exist, not a pre-guest Foundation deployment.
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
  This is Stage 2 option 15b after issuer acceptance, with persistent local audit records until Stage 3
  producer enrollment, not an unfinished Stage 1 option.
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
- Bootstrap Steps 6-9 own the copyable fresh OS-package and Terraform RPM-repository installation,
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
- Controller collection acquisition defaults to approved Git sources pinned by full commit and
  compatible release version in Shared's collection-sources.yml. Preserve compatible installed
  versions and native search precedence; batch native installs without distribution-server fallback.
  FreeIPA requires its pinned upstream release builder, automated in a private temporary workspace.
  Standalone template preparation mirrors only the Proxmox pin and stays independent of Shared.
  CONTROL_NODE_COLLECTIONS_SOURCE=galaxy retains explicit OS/Galaxy acquisition; dependency check
  mode stays acquisition-free. Changing sources never repairs an unavailable proxy or changes its ACLs.
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
- `docs/03-deployment/stage-04-kubernetes/procedures/kubernetes.md` owns cluster choices and common readiness;
  its `talos-terraform.md` sibling and stage's `step-1b-existing-cluster.md` own implementation procedures
- The complete supplied human-SSO rollout qualifies Talos 1.13.x and requires the original
  Terraform-owned plan. Manual cluster credentials survive later guides, but that alternative's
  SSO configuration persistence/rollout/recovery implementation is still a recorded gap.
- all three tiers own a Kubernetes root, inventory/IP map, state and credentials;
  shared/scripts/kubernetes-cluster.sh is execution only, with tier-local shortcuts
- all tiers use tier-owned cluster-platform playbooks/inputs with Shared's stateless
  cluster_platform, kubernetes_applications and helm_release roles. Tier 0 retains its Flux;
  D-041 selects independent Tier 1 Flux and Spinnaker promotion orchestration. Tier 2 remains
  separate explicit scope. Legacy local inputs keep Ansible ownership until accepted adoption. CNI/CSI, cert-manager,
  Traefik CRDs and CNPG are native pinned products, not empty GitOps starters;
  Barman is an explicit object/WAL backup selection, not required by scheduled NAS file copies
- Tier 0 control_applications installs Keycloak/LDAP, Vault/Raft/audit, NetBox and Headlamp;
  initialization/unseal and custody remain explicit. Tier 1 delivery/observability/development
  roles render Flux payloads for selected Kubernetes services, while external services retain their
  existing installers. Tier 2 lab/telemetry roles keep their separate owners and interfaces
- tier-local machine_config_patches supplies native Talos proxy, DNS/time and registry documents;
  default [] preserves existing behavior, not restricted-network readiness; Linux proxy inputs do not apply
- new cluster examples use three schedulable control planes with optional workers;
  existing configs default to disabled control-plane scheduling; never remove live workers to match examples
- pool inputs emit node-pool labels; authorized Kubernetes operations own worker taints;
  pools are not independent security boundaries and no autoscaler is supplied
- Tier 1 bootstraps initial networking, source/decryption credentials and Flux through the existing
  cluster_platform installer. Flux then owns its own matching Helm release and Tier 1 Kubernetes
  platform services; normal Ansible runs stop applying transferred components. Bootstrap `platform`
  stays immutable/canary-checked. `tier1-platform` is a separately approved exact Git revision,
  advanced by independent external maintenance. `tier1-applications` uses a protected delivery branch
  in another enforceably scoped project. No Tier 0 credentials are reused. Spinnaker orchestrates
  application promotion and observes exact Flux results, without direct workload/platform writes.
  Direct Spinnaker and Argo CD stay explicit alternatives, never co-writers.
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
  SQL/cache dependencies, scoped target identities, SSO and recovery jobs; Flux ownership preserves
  versioned initialization/backup gates, explicit adoption/data recovery and trigger fencing. Argo CD
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
  Starter IDs use T C NN with category 0 reserved in every guest allocation group.
  Categories 1-6 are control planes, workers, identity/trust/core services, network/edge,
  observability/logging, and administration/automation. Category is guest function, not criticality
  or deployment order; PKI issuer ca-1 is 311, while bootstrap is an administration tool.
  Tier 0 omits its leading zero and uses full hundred-ID blocks:
  1xx, 2xx, 3xx, 4xx, 5xx, 6xx (manual boot-1 601, runner 611, optional ceremony 621).
  3xxx labs and 4xxx clients remain Tier 2-owned, 9xxx templates/builders Tier 0-owned.
  Existing local IDs/state are never renumbered by refresh; new example IDs are not a migration.
- docs/05-operations/01-hosting/change-vmid.md owns planned full-clone renumbering with complete
  NIC/MAC preservation, independent host access, original-off cutover, ownership branches and rollback.
  The linked recovery/terraform-import.md owns single-resource Linux VM rebinding for clones/restores;
  retain logical keys and unrelated state. Select the actual owning setup/resource, not a service-specific recipe.
  Runnable state/VMID maintenance starts a dedicated child Bash shell so terminating checks cannot close
  the operator's SSH session. Prompt labels are navigation only. Shared selection offers the actual
  sibling checkout default and retries mistyped paths before Terraform runs.
- docs/05-operations/01-hosting/vmid-data-disks.md owns extra-disk choices during VMID cutover:
  preserve full-clone copies, reassign an original managed volume with native Proxmox ownership transfer,
  or deliberately rebuild disposable data through IaC. Preserved filesystems keep UUID pins and matching
  controller/device bindings. Clearing a pin is not a reset or permission to bypass persistent-mount guards.
  A transferred disk must return to the old VM before rollback; a fresh guest prints a new UUID to retain.
  Keep these runbooks service-neutral: old/new VM and actual owning inputs, with no named workload examples.
- docs/02-conventions/iac-inputs.md owns the public storage-input naming pattern:
  <service>_<volume>_uuid for new UUID pins and <service>_<volume>_device for selectors. Use the role's
  actual namespace/schema and printed key; existing expected-qualified inputs remain supported.
  A future public-key rename needs compatibility and evidence that preserved UUID guards still apply.
- terraform-state.md selects the actual owning repository/root, original state file and TF_DATA_DIR.
  Reusable state tasks must not require a specific service, tier or resource address. Keep local/default
  workspace commands separate from recorded remote/non-default contexts. Retired local state archival
  moves only the selected state file; retain provider/module caches and every unrelated deployment.
  Its FAQ sections are alternative tasks, not a linear procedure. VMID cutover routes directly through
  the complete VM-adoption procedure, including exact old-binding removal and replacement import before plan/apply.
  State inspection or an input edit alone does not adopt a clone; stop any unintended replacement plan.
  Adoption uses one numbered action per command/edit, with separate removal/import steps and expected results.
- Linux VM modules in all tiers treat clone source/node/type as creation-only, since provider import
  does not recover that provenance. Their lifecycle retains template-owned description, OS hint and
  serial ports alongside Proxmox-owned placement. BIOS/machine/SCSI/EFI disk/boot order are also
  creation-only: existing/imported guests preserve actual boot hardware, even with absent/different
  Shared profiles. Capacity, disk configuration and networking remain deployment-managed.
  Tier 0 publishes actual BIOS/machine/SCSI/EFI-key settings into Shared's template catalog; Linux
  consumers inherit the actual source ID's profile. A tag-only catalog alias or legacy tags override
  cannot select different hardware. Per-VM firmware replaces the complete creation profile only for
  an exception; it does not retrofit an existing VM. Older catalogs can synchronize metadata once,
  without duplicating it per service. Missing whole profiles retain legacy defaults for creation;
  partial selected profiles fail. Import does not require a boot-profile backfill. Deliberate boot
  migrations need separate review; do not hide entire disk blocks or resource changes to suppress drift.
  Changing template/full_clone inputs does not upgrade existing guests or remove linked-clone dependencies.
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
  remain project-owned configuration. Tier 1's selected Flux path receives real rendered service
  graphs with pinned Helm releases/native resources; legacy direct-owner paths remain explicit alternatives
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
  docs/01-architecture/11-operations/02-log-retention.md owns this choice; Stage 3 options 7a/7b guide it.
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
  docs/03-deployment/README.md indexes ten numbered capabilities: software intake, cryptographic trust,
  protected logging, Kubernetes, Identity, Secrets, Delivery, Observability, Development platform and Lab environments
- Stage 4 owns control-cluster bootstrap and common add-on/audit/recovery gates;
  Stage 5 owns dedicated directory VMs and federation on the existing cluster;
  independent bootstrap DNS/time/credentials avoid a Kubernetes/identity dependency cycle
- protected syslog/audit intake starts in Stage 3 on independent Tier 0 VMs;
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
- retain persistent local journal/audit records and independent recovery custody from first boot;
  Stage 2 establishes trust without a protected-network-logging prerequisite, then Stage 3 enrolls existing
  producers before FreeIPA and Kubernetes; independent logging authority remains a selected legacy option;
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
  and explicit working repository/machine. Commands use paths relative to that context; absolute
  paths remain only where required by a tool/configuration input. Preserve user-supplied sequences
  and meaning while editing.
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
- Stage 1 Steps 14–16 explicitly commission Proxmox host update access using Tier 0's existing
  proxmox-hosts.yml recipe (Datacenter download proxy plus per-host APT), then links controlled
  one-host-at-a-time maintenance. Hosts pull through the proxy; the cache gets no host authority.
- software intake is a separate early capability at docs/03-deployment/stage-01-software-intake/,
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

- docs/07-decisions/README.md keeps each decision in one concise table row with choice, status,
  rationale, consequences and review trigger. Supporting explanations belong in the owning design
  documents and are linked from the row. Keep compatibility anchors in the table entry, consolidate
  overlapping material, and preserve superseded decisions as history. Accepted architecture,
  implementation coverage and measured live qualification remain distinct records.
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
