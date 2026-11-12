# Operator walkthrough checklist

Guide sequences rechecked 2026-11-11 against the current worktree, from the
perspective of a software engineer with newly installed servers and UniFi switches.
This is the maintainer's working checklist, not generated
project documentation or a claim of production readiness.

**Scope:** clone, generation, foundation, all ten capability stages and adjacent options,
ordinary users, applications, maintenance, expansion and total-loss recovery.
**Evidence boundary:** source/generator review and offline tests; no live gateway,
Proxmox, HSM, service deployment, failover or disaster restore was performed.

The 2026-11-09 workflow pass and host-management follow-up accounted for all 173 installation, administration,
development, reference and reader-path documents, including the front doors.
It re-derived required order, actual choices, branch rejoins and acceptance gates;
coherent procedures and lookup references were retained. It did not qualify live operations.
Validation: 75 distinct focused regression checks passed, with targeted navigation/link reruns after
the final correction; 576 Bash blocks passed syntax checks. Original Markdown anchors were retained.

## Current source consistency review

### Collection-source automation, 2026-11-12

Controller prechecks now default to native Git acquisition for missing or incompatible collections.
All twelve declared sources have verified release identities and full upstream commit pins. Compatible
installed copies remain in place; configured search precedence and final effective versions are checked.
The native batch resolves dependencies without consulting Galaxy distribution servers. FreeIPA's
upstream release builder is invoked automatically in temporary controller storage, cleaned after install.
The standalone Tier 0 template runtime mirrors only the Proxmox pin and retains its Shared-independent
bootstrap contract. Explicit Galaxy selection and acquisition-free dependency check mode remain available.

Validation includes real local Git installs with a distribution server that receives no requests,
dependency resolution, rerun preservation, incompatible-copy replacement and generated tier execution.
Thirteen existing version/cache/compatibility tests passed. The pinned upstream FreeIPA builder passed
41 native tasks, isolated installation, module discovery, repeat-build reuse and cleanup. Pin alignment,
source/generated documentation and bootstrap checks passed separately. Standalone template preparation
passed eight tests, with one wheelhouse-dependent repeat skipped. No running cache, proxy policy,
remote infrastructure or production controller environment was changed by these repository checks.
The complete parent FreeIPA flow also passed with only community.general pre-staged: install and
temporary workspace cleanup succeeded, then rerun made zero changes with no Git, build or Galaxy requests.

### Final handover review, 2026-11-11

Scope: the complete pending change set, all ten stage routes, generated repositories,
capability-to-source correspondence and maintenance/recovery handoffs. No live deployment was run.

- Align the optional hardware-provider/remoting and independent signing-API routes with their actual
  stages, separate state and recovery ownership; retain PKI/HashiCorp Vault as the initial path.
- Complete the project deployment checklist's CSI, human SSO, registry and hosting options without
  resetting existing completion records. Correct final architecture/operations and source links.
- Pass the selected ordered configuration overlays into controller prechecks as well as deployment;
  reject an unselected software-consumer group before contacting any guest.
- Preserve the saved template plan's context artifact in protected CI and reuse the tier-owned
  dependency catalog for immutable builds.
- Resolve extra-disk classes lazily: explicit datastores work with an empty class map, omitted classes
  inherit the VM datastore and unknown selected classes fail before resource changes.
- Refuse template replacement of ordinary VMs. Refuse backup initialization over partial repositories,
  linked configurations or recovered filesystem data; retain original files on rejection.
- Scan history with redacted Gitleaks output. Six exact historical public-stage-name test assertions
  are documented false positives; only those fingerprints are excluded, not their files or rules.
- Complete seal/signing option metadata and record the independent log-backup VM's reservation in
  the central VMID reference. Update assertions for readiness/prechecks and native product installers
  while retaining baseline ordering, controller-interpreter, evidence and ownership guarantees.

Validation is combined evidence, not one clean all-native suite:

- Broad portable run: 725 methods, 322 tool-dependent skips. Twelve failed methods exposed guide
  metadata/wording gaps and stale contract assumptions; all passed in the final ten-method and
  four-method reruns. The latter also rechecks every VMID allocation/category and collision guard.
- All 230 source/generated playbook syntax invocations and two baseline host-list checks passed.
- All 27 native Terraform VM mock cases passed across the three tiers. Four focused safety tests
  passed, including preservation of ordinary VM disks, partial repositories and recovered data.
- Native Ceph chart rendering passed for all three tiers, and the NFS contract passed, using the
  accepted Core 2.16.16/setuptools 81 environment. The newer fixture's incompatible setuptools
  stopped at precheck before rendering; no dependency guard was weakened.
- Controller execution/input-overlay, signing, bootstrap and source/generated navigation checks
  passed in their scoped runs. Redacted scans passed for 129 commits and staged source changes;
  whitespace checks passed. No runtime/private artifacts were selected for the index.

This handover prepares the index for the owner's signed commit. It does not commit or push.
Physical HSM qualification, live SSO/failover and clean-target recovery remain separate acceptance.

### Deployment automation audit, 2026-11-11

Scope: Foundation and every numbered deployment/option, source inputs through native resources and
generated repositories. No real infrastructure, key authority or remote state was changed.

- [x] Remove post-bootstrap guest SSH setup; retain explicit physical/offline custody interfaces.
- [x] Align all 16 Linux VM root contracts with native firmware, clone, NIC, media, disk and lifecycle
  settings. Preserve the private gateway's distinct-host guard. All 21 roots validate; 97 native
  provider-mocked VM/LXC/template/cluster/gateway cases passed across the final scoped runs.
- [x] Supply native Ceph RBD CSI alongside retained existing/NFS interfaces, with scoped credentials,
  Talos preparation and selected storage before consumers.
- [x] Supply seven-host native observability installation, protected persistence and scoped UIs.
- [x] Supply GitLab VM OIDC, scheduled encrypted exports, sensitive controller access and isolated recovery.
- [x] Supply Vault VM audit/OIDC API reconciliation and configurable VM/Kubernetes seal interfaces;
  refuse implicit seal changes. Independent recovery can mount a configured native NAS export.
- [x] Supply pre-Headlamp public PKCE/RBAC workflow and Kubernetes-native backup-repository commissioning.
- [x] Correct integrated controller-runtime fixtures and native Spinnaker commissioning rendering;
  preserve behavioral assertions and source/generated correspondence.
- [x] Supply initial bootc image build, shared PKCS#11 remoting and independent OpenBao external-key
  signing selected during this review. Keep PKI/HashiCorp Vault first and advanced options distinct.
- [x] Bound collection versions for the OS Ansible baseline, reject unsupported Proxmox runtimes before
  acquisition, align manifests/catalogs and include the OpenBao host client's cryptographic dependency.
- [x] Guard ordinary OpenXPKI PKCS#11 activation as well as direct key operations; reject unaccepted
  custody and factory credentials without preventing inactive installation.
- [ ] Complete physical HSM, live SSO/failover, NAS and clean-target recovery acceptance independently.

Native Collector and Data Prepper parsers accepted the dedicated VM inputs. Isolated native backup,
key-identity, seal-migration and original-state guards passed. Completed final scoped checks include:

- 18 controller/VM-contract/data-binding/Vault/bootc checks; 21 reader/navigation/source-view checks.
- 312 source/generated playbook and task syntax checks, plus 54 updated HSM task checks.
- 17 compatibility checks with 11 installed collection versions supporting Core 2.16; Proxmox refuses
  that runtime and requires its separately prepared newer environment.
- 15 final activation/Vault/OpenBao checks on the declared compatible runtime: 12 passed, three
  artifact-dependent repeats skipped. The separate native OpenBao run passed all nine tests using
  OpenBao 2.7.2, PKCS11 plugin 0.2.1 and SoftHSM 2.6.1, including real RSA-PSS/P-256 signing,
  certificate authorization, idempotence and the artifact-only route.
- Provider suite: eight passed; direct issuer guards: three passed including 12 rejection cases.
  Native remoting: four passed, one Node-dependent test skipped and passed separately on Windows.
  Native p11-kit/OpenSSH/SoftHSM tests cover SPKI identity, denial, extra-key refusal and reconnection.
- Eleven changed figures rendered in both light/normal and dark/narrow views; source/generated
  palette, allocation, link and diagram/input checks passed. Netdata CLI checking remains skipped
  without its matching executable; fourteen focused VM service tests and Collector validation passed.
- Native PKCS1-to-PKCS8 conversion also passed on the bounded crypto collection, preserving public
  identity through rerun and key rotation.

Physical YubiHSM/PicoHSM, live PC/SC, enforcing EL10 policy, application/HSM failover, SSO and disaster
recovery remain target acceptance. Automatic review blocked fixture cleanup of WSL's generic `sshd`
account because ownership was not uniquely established. It was left untouched; the fixture now
requires that OS account to exist and never creates/removes it.

### Controller-owned guest setup, 2026-11-11

- [x] Cross-check every active Terraform extra-disk reference against its service's stable
  by-id selector in source and generated repositories: cache, receiver, issuer and verified intake,
  plus the independent backup starter. Correct stale disk-letter references; preserve local UUID pins.
- [x] Replace Stage 2 action 1.4's interactive SSH with the storage-only Ansible recipe.
  Terraform allocates the guest/scsi1 disk; Shared prepares and verifies its filesystem/UUID mount
  before receiver TLS enrollment. Receiver verification and diagnostics run from the controller.
- [x] Wait for managed guests before facts/configuration, including issuer, logging, runner,
  VM delivery, lab and diagnostic paths. GitLab data-host waiting follows its controller checks.
  Prepare the receiver firewall and retained deployment SSH port through native modules.
- [x] Supply guarded public issuer-certificate transfer and separately selected native token
  operations from the controller. Offline signing/custody approval remains outside guest setup.
- [x] Supply native RPM/APT consumer source/trust configuration and strict refresh through
  tier-owned entry points using Shared execution code. Retain vendor keyrings and backup replaced APT files.
- [x] Supply runner collection handover, state digest validation, public keys, known-host trust
  and non-secret CI environment deployment. Preserve executability, exclude bootstrap environment
  and provider/plan caches, distinguish authoritative state from disposable backend metadata,
  refuse different destination state and retain the stopped-writer boundary.
- [x] Add the optional managed recovery VM/disk definition to syslog inputs; use the stable
  scsi1 device instead of Linux letter ordering. Existing independent hosts remain adoption interfaces.
  Replace manual Kubernetes clone/bootstrap instructions with accepted existing-cluster adoption.
- [x] Pass final targeted controller/guard/syntax and reader-route checks with Ansible Core 2.16,
  generated-source link checks and native rsync copy verification. Exercise real filesystem creation,
  persistent UUID mount, rerun, growth and replacement-disk refusal on disposable XFS and ext4 loops
  in private mount namespaces. Render and inspect the compact syslog provisioning view.

These are source/offline checks; no live Proxmox, issuer, runner or service deployment was performed.

### Numbering and operations follow-through, 2026-11-11

- [x] Renumber architecture chapters 01–11 and close gaps in the nested Hosting and
  Software Intake files. Keep installation order with the ten deployment stages.
- [x] Consolidate Operations into six domain entries matching the designs, with local
  configuration, executable tasks and recovery links before deeper reference material.
  Replace thin per-stage landing folders with the actual runbook or shared task home.
- [x] Update incoming links, source-side guide references, generated templates and migration
  destinations. Keep retired numbered aliases only while project-owned records reference
  them; retain legacy routes separately and preserve original section anchors.
- [x] Pass focused documentation, graph/reachability, refresh, reader-journey, diagram and
  ten-stage correspondence checks across the final runs. Correct the new migration test's
  existing-parent fixture and rerun it successfully with the final links and review checks.
- [x] Validate all 21 Terraform roots and pass 94 native mock cases in isolation.
  Render 47 architecture figures; inspect the updated HTTP/HTTPS sequence on light/normal
  and dark/narrow pages. No live deployment or hosted-renderer acceptance was performed.

### Architecture reading and consolidation, 2026-11-11

- [x] Group architecture by substantive domain rather than duplicating deployment-stage
  landing pages: Hosting owns Kubernetes/labs, Cryptography owns trust/secrets,
  Delivery owns development, and Operations owns logging/observability.
- [x] Separate background from organizational authority; place communication sequences
  beside their capability and explain which decision each chapter supports.
- [x] Reduce 46 pages/15 chapter folders to 37 pages/10 folders, update current links and
  migration targets, and retain needed numbered aliases for project-owned Markdown links.
- [x] Check the 81 documentation, navigation, migration, refresh and correspondence cases
  across focused runs after fixes. Render all 47 architecture figures locally; inspect
  changed views at normal/narrow widths on light/dark pages. Hosted-renderer parity is unverified.

No infrastructure definitions or live resources were changed by this documentation work.

### Template OS classification, 2026-11-11

- [x] Expand Linux-family choices with generic Linux, Windows and other guests;
  keep distribution identifiers open-ended and legacy Alma/Rocky inputs valid.
- [x] Match uploaded raw/qcow2 filenames, guest OS types, optional EFI keys/TPM and
  Shared catalog synchronization; reject non-Linux images in the Linux guest resolver.
- [x] Pass 13 focused regression checks, including 28 locked-provider template mock plans,
  native discovery/adoption fixtures, consumer placement guards and generated documentation links.
- [ ] Clone-test each selected new OS image on the target platform. Windows guest preparation
  and OS-specific consumers remain separate from publishing an approved disk image.

### Final repository correspondence review, 2026-11-11

- [x] Restore the deployment-picture checks to the numbered source directories and
  reject empty architecture discovery, so retired paths cannot silently bypass the audit.
- [x] Check the depicted starter guests, selected runtime releases and cluster log streams
  against the actual inputs, inventory and native release configuration.
- [x] Align the generated Tier 1 software-supply starter with the supplied verified-intake installer.
- [x] Bind the issuer, protected receiver and verified-intake reference volumes to the
  Proxmox scsi1 by-id identity rather than boot-dependent Linux disk letters.
- [x] Retain the architecture figure/caption convention in the project diagram guide.
- [x] Validate all 21 Terraform roots with their locked provider schemas in an isolated copy;
  run the supplied VM, LXC, template, cluster and API-endpoint mock plans.
- [ ] Complete live stage acceptance, failover and clean-target recovery on the selected infrastructure.
- [ ] Supply or qualify an independent pre-Headlamp OIDC login client/token and namespace RBAC.
  The serial API rollout does not create that verification path; do not mark API human SSO
  accepted simply to pass the later Headlamp installation gate.

No deployment state or remote infrastructure was changed by this source review.

Validation completed in isolated WSL copies: all 21 Terraform roots passed schema
validation and 86 native mock plan cases passed; 94 source playbooks and their generated
copies passed 188 syntax checks. Clean focused runs passed 72 documentation/journey
checks, 30 source/payload/first-run checks, 26 figure/correspondence checks and seven
late-stage/PKI command checks. A final 20-check refresh/link/correspondence run passed
after correcting the retired-route fixture. These runs overlap. Snapshot secret scans
reported no leaks. This is source qualification, not live service or recovery acceptance.

After the stable-disk correction, the volume/issuer/receiver/intake and payload run completed
29 tests: 20 passed and nine root/private-mount/loop-device cases were skipped. Guard probes,
source/generated syntax and mocked VM/disk plans passed; actual formatting, mounts and
growth still need the isolated native storage fixture or target acceptance.

### Capability and reader-journey review, 2026-11-11

- [x] Trace Foundation and all ten deployment stages to their IaC entry points, architecture
  and operations routes. Align the readiness and implementation-support tables with those names.
- [x] Correct the Stage 9 VM option's return to runner selection and separate the Stage 8
  VM integration requirements from the Kubernetes path.
- [x] Align the generated software-intake checklist with the new-cache and existing-supply
  alternatives. Preserve compatibility links to the headings of locally retained documents.
- [x] Clarify the logging receiver count, database availability, optional integrations and
  Windows client acceptance without treating a design or local check as a live result.
- [ ] Qualify the selected paths on the target infrastructure, including recovery and failover.

The follow-up automation audit above supersedes this pass's observability, HSM-provider and
GitLab VM OIDC implementation gaps. Lab self-service allocation and its portal are not supplied.
Foundation hosts, networking and storage remain commissioned prerequisites.

Verification: focused WSL runs passed 27 navigation/migration/ownership checks and
32 capability, generated-documentation and deployment-path checks (the runs overlap).
The source sweep checked local links and 21 documented IaC entry points. The full
regression run was interrupted; its initial ownership-test failure was corrected and
passed separately, while native environment-dependent checks were skipped. No live
deployment, failure or recovery was performed in this review.

### Controller and cache repair follow-up, 2026-11-10

- [x] Check the selected network-filter Python dependency independently of collection presence.
  Install OS `python3-netaddr` or the active venv's declared requirement; `check` remains acquisition-free.
- [x] Expose explicit approved DNF baseurls for existing selected sections, preserving keys,
  verification settings, other repositories and timestamped backups. Explain dynamic-mirror limitations
  in the bootstrap path and distinguish source selection from the cache allowlist.
- [x] Select cache `scsi1` by its existing stable by-id identity. Replace the legacy unguarded
  filesystem sequence with Shared data-volume qualification before stopping Squid or preparing storage.
- [x] Reject malformed VIP prefixes, including a retained placeholder marker and `/0`.
  Require every keepalived member in the active play/batch before gathering facts or stopping its owner.
- [ ] Finish live acceptance after correcting site disk/prefix inputs: qualify both service members,
  VIP prefix/ownership, source retrieval, takeover/restoration, denied destinations and ordinary OS refresh.

Evidence so far: 10 controller/dependency/syntax checks passed; five Python-runtime checks passed
(OS acquisition simulated, venv pip/filter execution native); four source-selection checks passed
against temporary files; four VIP-gate checks covered 14 native inventory/play scenarios. Native
invalid-input and source/generated-link checks passed. Live feedback confirmed OS netaddr 1.3.0;
remaining cache/storage/network acceptance is separate from those local fixtures.
The cache-volume follow-up passed six regressions and eight Shared volume checks without skips:
OS/partitioned/root devices stop before service/storage changes, accepted volumes retain identity,
and blank-volume preparation uses the Shared UUID path. Device/service/filesystem boundaries in
the cache integration fixture are simulated; no live block writes or mounts were performed locally.
Live inspection identified reversed Linux disk letters and the existing scsi1 by-id link on both guests.
The malformed VIP input retained a placeholder marker; the unconfigured peer still had stock keepalived
addresses. Corrected site inputs and a complete pair rerun remain required for operational acceptance.

### Galaxy acquisition behind the cache, 2026-11-10

- [x] Select `ansible.utils` for cache CIDR validation before guest changes, retaining its
  collection bounds and controller `netaddr` dependency in source/generated output.
- [x] Include the Galaxy API and document explicit artifact-route approval or prepared archives;
  do not make one observed regional redirect hostname a universal dependency. Document retained-policy
  adoption and the one-time approved-source repair for an existing cache.
- [x] Use native Galaxy `--no-cache` acquisition to bypass malformed API-response metadata;
  preserve installed collections, version bounds, TLS/proxy policy and offline `check` behavior.
- [x] Reproduce the poisoned-response failure and real collection installation through a loopback
  proxy; verify retained collection/cache files and an idempotent, network-free second run.
- [ ] Complete site acceptance after proxy denial and subsequent VIP connection timeout:
  verify services/VIP ownership, approved API plus redirected artifact download and denied destinations.

Validation: 11 focused controller/version/link/preflight checks passed; two Squid-binary checks were
explicitly skipped in that harness. The new native metadata-cache regression passed on Ansible
2.16 and 2.21; removing `--no-cache` reproduced the failure. No live cache changes were executed.

### Numbered guide ownership follow-up, 2026-11-10

- [x] Name the dedicated bootstrap consumer guide for Stage 1 Step 6 and the infrastructure
  monitoring guide for Stage 8 Step 3; keep their README entry and return points explicit.
- [x] Keep cache installation in the Stage 1 README and update reconciliation in option 2b.
  Move policy/tuning lookup to reference, removing repeated installation instructions.
- [x] Group reusable logging, monitoring, Observability and isolated-cluster guides under
  their stage's procedures directory. Preserve diagrams, implementation and lifecycle scope.
- [x] Update source/generated links, source pointers and direct refresh-migration targets;
  check numbered filenames/titles and separation of steps, procedures and references.

Validation: 564 portable cases, including 240 explicit tool-dependent skips. The first run exposed
two documentation-coverage checks: an option-only filename assumption and missing checklist rows.
Both were corrected and passed focused reruns; all other executed portable cases passed.
All 20 focused navigation, source/generated-link, graph and source-pointer checks passed.
The guide-command/monitoring fixture run passed 12 checks with three explicit root-only skips.
All 220 public pages remain reachable/referenced; moved Mermaid bodies are unchanged.
No live deployment or hosted-renderer acceptance is implied.

### Connectivity and consolidation follow-up, 2026-11-10

- [x] Trace all 220 public Markdown pages, including the root README, from the front door;
  no unreachable pages or pages without incoming references remain.
- [x] Add whole-manual source/generated reachability checks, including diagram assets and
  detection of orphan cycles. Keep selectable deployment-path checks separate and stricter.
- [x] Consolidate refresh, developer dependency setup, host registration and partial-publication
  recovery into their existing authoritative guides, with explicit return points.
- [x] Remove the repeated architecture service inventory and centralize search permissions,
  tenant separation and retention detail. Retain task-local commands, prerequisites and short summaries.
- [x] Recheck affected local links and the consolidated OpenSearch access references.

Validation: **561 portable cases; 322 passed and 239 explicit native/tool-dependent skips**.
All 12 targeted security-contract, source/generated link and reachability checks passed.
The isolated redacted secret scan and final staged-file whitespace check also passed.

The earlier operational and external-link exclusions still apply. Publication is explicitly
authorized in this follow-up; preserve the configured signed-commit policy.

### Repository audit, 2026-11-10

Reviewed the front doors, all 219 public documentation pages, generated repository
navigation and all ten stage-to-IaC paths. The deployment subtree has 91 guides,
including 30 numbered option files. This is source/local qualification, not live acceptance.

- [x] Align numbered choices, dedicated filenames, branch returns and legacy link migration;
  separate bootstrap preparation from Proxmox-specific guides.
- [x] Place verified intake after accepted logging/trust at Stage 3 option 3b, and host hardening
  after service hosts exist. Correct detailed coverage tables and retired source/runtime doc links.
- [x] Preserve manual-cluster credentials through later guides, qualify Talos 1.13.x before
  image/node selection, and disclose the manual-cluster SSO implementation gap before that choice.
- [x] Supply the optional Stage 6 `mon-1` VM/disks through the existing foundation root/state;
  preserve issuer/directory maps, run Terraform only, then baseline, enroll logging and install monitoring.
  Keep the existing-host alternative and single-monitor outage limits explicit.
- [x] Correct receiver/export target selection, actual host connection inputs, native render commands,
  accepted-registry pipeline examples and required certificate enrollment handoffs.
- [x] Align implementation diagrams, source/input links, completion records and VMID reservations;
  keep deployment allocations out of figures and retain stable architecture role labels.
- [x] Replace three missing external references: Flux community chart documentation, Vault snapshot
  commands and the RHEL bootc catalog page. HEAD false negatives were retried with GET.

Validation:

- Full portable suite: **558 cases; 319 passed, 239 explicit native/tool-dependent skips**.
- **21 Terraform roots** validated with tracked locks and cached providers; **86 mocked cases** passed.
  The optional monitor also passed before/after mocked plans, retaining the original three guests.
- Two bounded native/source/generated runs passed: **81 cases (10 explicit skips)** and **34 cases**.
  These include real module/task/configuration paths against disposable local fixtures, not remote hosts.
  The final documentation-only changes passed **25 targeted monitoring, diagram, link and navigation checks**.
- **543 YAML files, 27 Bash scripts and 133 Python files** passed source syntax/duplicate-key checks.
- Amended figures rendered locally with Mermaid 11.17.2 on light/dark backgrounds at normal/narrow
  widths; nested-heading clipping was corrected. Hosted-renderer parity remains a separate review.
- **550 distinct public pages** were probed. Three confirmed missing links were replaced;
  26 pages remain unverified because of access controls, throttling, TLS trust or timeout.
  URL reachability does not establish that every cited claim or remote fragment is correct.

Live outage, recovery, identity, durability and denial checks remain unchecked in
[operational verification](operational-verification.md) and
[platform acceptance](platform-verification.md). Remaining alternative implementations
and intake integration work stay in their respective unchecked lists below.

<details>
<summary>External pages requiring manual verification (26)</summary>

- [ ] [HTTP 403](https://developers.redhat.com/articles/2026/02/12/how-build-image-mode-pipeline-gitlab)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/installing_and_using_dynamic_programming_languages/installing-and-using-python)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_file_systems/index)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_external_red_hat_utilities_with_identity_management/setting-up-samba-on-an-idm-domain-member)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_idm_users_groups_hosts_and_access_control_rules/managing-public-ssh-keys-for-users-and-hosts)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_image_mode_for_rhel_to_build_deploy_and_manage_operating_systems/introducing-image-mode-for-rhel)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/managing_smart_card_authentication/managing_smart_card_authentication)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/installing_and_using_dynamic_programming_languages/assembly_installing-and-using-python_installing-and-using-dynamic-programming-languages)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/securing_networks/using-shared-system-certificates_securing-networks)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_satellite/6.18/html/configuring_capsules_with_a_load_balancer/installing-and-configuring-the-load-balancer)
- [ ] [HTTP 403](https://files.openstack.org/docs/keystone/latest/index.html)
- [ ] [HTTP 403](https://fedora.gitlab.io/bootc/docs/bootc/base-images/)
- [ ] [HTTP 403](https://help.ui.com/hc/en-us/articles/19133507506711-Configuring-MC-LAG-in-UniFi-Network)
- [ ] [HTTP 403](https://help.ui.com/hc/en-us/articles/26136855808919-Switch-Port-VLAN-Assignment-Trunk-Access-Ports)
- [ ] [HTTP 403](https://help.ui.com/hc/en-us/articles/360007279753-Port-Aggregation-FAQs)
- [ ] [HTTP 403](https://help.ui.com/hc/en-us/articles/360012622613-UniFi-Device-Adoption)
- [ ] [HTTP 403](https://static.openstack.org/docs/keystone/2024.1/admin/cli-manage-projects-users-and-roles.html)
- [ ] [HTTP 403](https://support.hashicorp.com/hc/en-us/articles/10773573595923-How-to-restore-a-snapshot-to-a-Vault-cluster-running-on-Kubernetes)
- [ ] [HTTP 403](https://www.cisa.gov/audiences/small-and-medium-businesses/secure-your-business/back-up-business-data)
- [ ] [HTTP 403](https://www.cisa.gov/sites/default/files/2023-01/fact-sheet-implementing-phishing-resistant-mfa-508c.pdf)
- [ ] [TLS trust](https://www.haproxy.com/documentation/haproxy-configuration-manual/new/latest/management/)
- [ ] [TLS trust](https://www.haproxy.com/documentation/haproxy-configuration-tutorials/protocol-support/tcp/)
- [ ] [TLS trust](https://www.haproxy.com/documentation/haproxy-configuration-tutorials/reliability/health-checks/)
- [ ] [HTTP 403](https://www.hhs.gov/hipaa/for-professionals/security/guidance/cybersecurity-newsletter-october-2022/index.html)
- [ ] [HTTP 429](https://www.hashicorp.com/en/trust/security)
- [ ] [Timeout](https://www.cyber.gov.au/publication/best-practices-for-event-logging-and-threat-detection)

</details>

### Previous review, 2026-11-09

The 2026-11-09 repository-wide follow-up traces the ten stages and alternatives from
documentation through generated repositories, local inputs, entry points and actual
Terraform/Ansible implementation. It also checks architecture placement, backup custody
and recovery state. The earlier guide-only results above are historical evidence.

- [x] Correct selection-scoped database preparation so Vault/Headlamp-only runs install and configure their products.
- [x] Install the logging verifier's complete dependency set on independent recovery hosts.
- [x] Bind saved template plans to reviewed inputs, configuration and execution targets before apply/refresh.
- [x] Stop template publication when cloud-init cleanup fails.
- [x] Correct runner registration for package-created empty configs and modern authentication tokens;
  enforce the selected Kubernetes context and required GitLab TLS Secret type.
- [x] Align Observability source/API/kubelet CIDRs and Netdata ACLs to current cluster inputs;
  keep independent Tier 0 monitoring on Management with later-tier export disabled initially.
- [x] Align architecture placement, Grafana/registry coverage, bootstrap recovery and direct-CI trust
  with their installers. Keep resource ownership separate from hosting and network access.
- [x] Correct fresh repository quick starts and retired source-side documentation links;
  retain project inputs/state and the explicit refresh conflict policy.
- [x] Move the Tier 1 service-capacity decision before cluster provisioning; the compact bootstrap
  profile alone is insufficient for the complete Delivery/Observability/development stack.

Validation of the integrated changes:

- Full portable suite: **458 cases; 286 passed, 172 explicit native/tool-dependent skips**.
  Final Management monitoring inputs also passed their two focused source/generated checks.
- All **20 Terraform deployment roots** validated using tracked locks and cached providers;
  **86 mocked Terraform cases** passed. No real provider apply or original state was used.
- **495 YAML files, 26 Bash scripts and 113 Python files** passed source syntax checks;
  **583 documentation Bash blocks** parsed without execution.
- Five figures in the three amended architecture pages rendered in **20 theme/width combinations**
  and were visually inspected. Local Mermaid 11.17.2 does not establish hosted-renderer parity.
- Native phase/selection, template-plan invalidation, cleanup refusal, runner/Secret/network gates,
  encrypted backup/restore and scoped telemetry replay checks exercise actual task/helper paths
  against disposable local fixtures. They do not accept live infrastructure.
- Native qualification was split across bounded runs, not one clean full-native invocation.
  Expired Collector/chart paths and missing syslog validator libraries were repaired in the local
  harness; affected Collector, Observability and receiver cases passed reruns. The unchanged extended
  Spinnaker variant sweep was stopped after main-reference source/generated rendering passed.
  Root/mount-namespace backup tests, native rsyslog/GnuTLS sender tests and unavailable-tool cases
  remain explicit exclusions; do not interpret the portable skip count as native acceptance.

The [implementation map](../docs/08-reference/implementation-support.md#stage-coverage)
remains the public source of truth. Client-auth certificate issuance is a commissioned
integration; the default issuer profile supplies server certificates. Kubernetes SSO
qualifies Talos 1.13, not 1.14. Hardware HSM/ACME and tenant allocation retain their
explicit integration boundaries. Follow [platform acceptance](platform-verification.md)
and [operational verification](operational-verification.md) before checking live results.

## Software-intake review, 2026-11-10

- [x] Keep the existing Tier 2 cache pair; require explicit clients/sources, preserve HTTP
  privacy/freshness, reject unsafe retained rules, and test denied requests as well as successful retrieval.
- [x] Emit sanitized JSON access decisions and document later per-host Tier 0 forwarding.
- [x] Apply native package verification/failure defaults independently of proxy selection, including
  bootstrap mirror mode and Proxmox's separate policy file. Repository overrides remain a reviewed boundary.
- [x] Define staged verification, quarantine and promotion as an optional Tier 1 design, not an installer.
  Keep malware detection, publisher authentication and vulnerability assessment distinct.

The subsequent verified-intake implementation adds the optional Tier 1 `intake` setup and
source-mapped [deployment guide](../docs/03-deployment/stage-3-trust/step-3b-verified-intake.md).
It supplies native RPM/APT acquisition, copied-content verification, ClamAV gates, private quarantine,
immutable HTTPS publication and scheduling. Terraform supplies its VM/disks; guarded Ansible supplies
the dedicated filesystem and UUID mount. The single worker still requires approved native tools,
trust material and current definitions; it is not HA or automatic patch management.
Live acceptance remains [INTAKE-6–9](operational-verification.md#software-intake).

Proposal-completeness review, 2026-11-10: the core staged-intake installer is supplied;
the following implementation/integration work remains before the entire proposal is covered:

- [x] Supply [tier-owned native consumer recipes](../docs/03-deployment/stage-3-trust/step-3b-verified-consumers.md)
  for RPM/APT selections, publisher keyrings, public trust and strict metadata refresh.
  Independent network bypass denial remains a live acceptance check, not an Ansible assertion.
- [ ] Add intake-specific health metrics and severity-based alerts: definition age, scanner/job
  failure, last successful intake and quarantine/storage capacity. Generic Netdata/OpenSearch
  installation and local error-priority syslog events do not supply these rules.
- [ ] Connect the worker/cache decision streams to explicit Tier 0 source registrations and
  approved OpenSearch projections. Existing logging automation is reusable, but the intake installer
  does not commission that path. Add run/incident and candidate-hash correlation without inventing
  a requesting client for a scheduled pull or exposing private URLs/scanner diagnostics.
- [ ] Automate or accept an existing independently retained Tier 0 critical-software supply.
  Selecting a URL on intake-1 alone does not retain usable packages/tools outside Tier 1/2 failure.
- [ ] Complete the optional OCI publisher-verification and vulnerability-policy promotion path.
  Harbor installs Trivy later; that does not connect Cosign or a Trivy gate to this worker.
- [ ] Define and qualify a separate VM-image intake path if templates are included in staged supply.
  The current worker deliberately holds raw/qcow2/ISO and other opaque images; scanning the outer
  file must never be described as checking every guest file.
- [ ] Record the proposal's selected NIST control-to-implementation/test/evidence mapping.
  Product selection and design descriptions alone are not an accepted control-evidence record.

Live network/failover, current-definition scans, confinement, delivery and restore results remain
in [INTAKE-1–9](operational-verification.md#software-intake), separate from this implementation list.

Guest-storage automation review, 2026-11-10: normal intake, logging and issuer deployment now
prepares dedicated filesystems and persistent UUID mounts through Shared's guarded data-volume
role. The issuer also manages its database bind; backup recipes manage their selected client/disk
mounts. No manual guest mkfs/fstab prerequisite remains on those new-install paths. Independent
NAS commissioning, existing-service adoption and signing/recovery custody remain explicit.
Native disposable XFS (Ansible 2.16.16) and ext4 lifecycle tests passed creation, unchanged reruns,
growth, retained data/UUIDs, declared binds and refusal of missing-volume replacements.
Nineteen focused native storage/NAS/backup checks passed; CA loopback provisioning, retained
database ownership, refusal gates and source/generated syntax passed separately.
The portable suite ran 518 cases with 226 explicit skips and one stale guide-wording assertion;
that assertion was corrected and the five affected correspondence/documentation checks passed.
Source syntax and light/dark intake figures at normal/narrow widths also passed local checks.
These results do not satisfy [STORE-3](platform-verification.md#capability-gates) or any live
reboot, Proxmox, NAS-outage or recovery acceptance gate.

Verified-extension evidence: the portable regression run completed **493 cases: 287 passed,
206 explicit native/tool skips**. Separate native fixtures passed 19 RPM/APT adapter cases,
12 artifact-pipeline cases (one current-definition positive explicitly skipped), nine focused
runtime gates, source/generated installer checks and Terraform mocks/correspondence. These use
disposable local HTTPS, GPG, RPM/APT, ClamAV and Nginx fixtures, not a live deployment. Positive
artifact scans used a disclosed old upstream CVD with fixture-only age relaxation; production
still enforces its configured 1–7 day bound, and the default two-day stale rejection passed.
Current official database download returned HTTP 403. Real EL10/RPM6, systemd confinement,
SELinux, network cutover, independent forwarding and restore remain unverified.
The final source/generated HTTPS timestamp and private native logrotate checks also passed;
local rotation does not replace protected forwarding. All 600 guide Bash blocks passed syntax
checking; YAML/Python/Bash source validation and diff whitespace checks passed. The three new/
updated figures were inspected in light/dark at normal and narrow widths; hosted parity remains manual.

Evidence: the portable suite passed **468 cases: 286 passed, 182 explicit native/tool skips**.
The integrated native profile reported **18 passed and four explicit root/parser skips**;
the separate 12-case package/bootstrap run passed those Ansible 2.16 and root fixtures too.
Real Squid exercises source/generated ACLs, caching/revalidation and JSON privacy. Native APT exercises
transient refresh failures, unsigned/expired metadata and the source-level `trusted=yes` exception.
DNF configuration/idempotence is tested; a native DNF engine and live hosts were not available.
The new architecture figure was rendered/inspected in four light/dark and reading-width combinations;
hosted-renderer parity and [INTAKE-1–5](operational-verification.md#software-intake) remain manual.

## Current journey verdict

The engineer can generate repositories and follow native installation recipes for
all ten selected capability stages. This is a staged, commissioned platform, not
a zero-touch appliance or an operationally accepted deployment.
The first security gate is verified Proxmox API trust; all supplied Terraform roots
now verify TLS, and provisioning entry points reject inherited insecure flags.
Stage 2 now has a selected Linux/NAS main path: reviewed-CSR producer trust, native
host forwarding, create-only checkpoints, audited file views and independent encrypted
backup. NAS snapshots/accounts and the recovery filesystem require commissioning;
physical faults and access/restore results remain manual verification. This is
asynchronous bounded-loss custody, not replicated/lossless intake. The Stage 3 policy issues
TLS-server leaves, not producer client-auth certificates. Do not bypass that gate to
declare a production PKI or assume Stage 3 automatically replaces producer trust.

The generated collection keeps resources, inventory, inputs and state tier-local.
Shared owns native chart execution and reusable cluster roles. Tier-owned application
recipes now cover platform add-ons, Identity, Secrets, Delivery, Observability,
the development platform and a bounded lab application. Empty GitOps directories
remain adoption points, not the installation executor. Direct infrastructure CI
explicitly trusts the dedicated GitLab project and its control/hosting authorities.

The [stage coverage](../docs/08-reference/implementation-support.md#stage-coverage)
is the authoritative installation/prerequisite map. Independent API endpoints,
prepared storage, approved images, certificate custody, external GitLab data services
and selected product interfaces still require commissioning. Separate API-endpoint and
GitLab data-service setups supply those reference realizations. Storage uses its actual
commissioned native interface, without a NAS object gateway. Existing qualified services
remain valid. Native Spinnaker and Argo CD are explicit alternatives.
Optional HSM and tenant allocation are not silently supplied. Household/team,
maintenance and product-recovery procedures exist; live qualification remains open.
No live acceptance box is checked by this consistency review.

## Corrected reading and execution gaps

- [x] Review complete task sequences, not only wording within inherited phase headings.
- [x] Test intake before host cutover; retire temporary WAN access only after its replacement works.
- [x] Complete foundation checks after HA/SDN branches; document actual workspace disk preparation.
- [x] Initialize and register existing Proxmox hosts before host recipes; separate SSH administration
  from API provisioning and the foundation guest deployment.
- [x] Prepare receivers before exporters, product runtimes before their backup tests, and original
  state before CI handover. Keep incomplete alternatives separate from runnable installers.
- [x] Make the front door distinguish runnable workflows from integration starters.
- [x] Keep foundation prerequisites outside numbered capability stages; logging remains Stage 2.
- [x] Prevent the Proxmox preparation guide from skipping logging and jumping to identity/clusters.
- [x] Add gateway/controller adoption and VLAN/port preparation before the UniFi policy matrix.
- [x] Distinguish ordinary client access ports from server trunks and supported multi-switch aggregation.
- [x] Put the existing Linux-provider TLS exception in the API setup gate, not only the HA guide.
- [x] Document verified Proxmox bootstrap trust and optional API certificate migration after PKI.
- [x] Add a logging fault/restore drill, seed-owned evidence record and offline reconciliation checks.
- [x] Supply a Tier 0 syslog-ng receiver with mount/TLS guards, raw JSON records and native local tests.
- [x] Explain that `--env` does not allocate unique VMIDs, addresses, VIPs or security boundaries.
- [x] Keep directory deployment in the trust stage's existing context/state instead of silently switching to test.
- [x] Put cache initialization, exact input edits and deployment directly in Stage 1's main path;
  expose existing approved supply as branch 1b, rejoining at intake testing before host configuration.
- [x] Initialize test inputs before VM source-control, runner and image-builder commands.
- [x] Use one normal Linux deployment command with Terraform's inline plan/approval;
  keep preview opt-in, unattended CI explicit, and dedicated saved-plan/signing/activation gates intact.
- [x] Add Vault CLI endpoint/trust selection and authentication before audit configuration.
- [x] Remove repeated identity-authentication and Vault-shape explanations in favor of their authoritative homes.
- [x] Align generated setup ownership and template references with logging and unnumbered foundation.
- [x] Use an ignored Python virtual environment for the generator dependency instructions.
- [x] Reproduce and fix missing-role failures in direct PKI/scheduler commands; test the documented invocations.
- [x] Connect edge publication and total-loss recovery to the new HTTPS and issuer-restore procedures.
- [x] Separate NAS-backed trusted-admin retention from optional storage-enforced locks;
  link both Stage 2 branches and record custody/review triggers in the evidence template.
- [x] Use `syslog` in fresh Tier 0 README quick starts, in the same base state context as
  Stage 2; link environment isolation beside optional `--env`, and retain storage/TLS preparation gates.
- [x] Point test source-control, runner and image-builder instructions at their selected
  Ansible test vars and explicit complete-map Terraform overlays, including final conversion.
- [x] Prepare/test local-input recovery before provisioning; test guest restore after the
  first disposable clone, and accept verified existing backup services without requiring PBS.
- [x] Clarify the independent producer-authority handoff instead of assuming the software
  PKI's TLS-server profile also issues logging client certificates.
- [x] Align remaining IdP wording and the image-builder's shared-catalog comment with their authoritative contracts.
- [x] Align fresh FreeIPA inputs with the sibling-CA design; preserve existing internal-mode local inputs.
- [x] Keep Stage 3 issuer acceptance separate from Stage 5 identity and later public-edge deployment.
- [x] Move the numbered hardware-rollover procedure into administration and preserve managed-guide redirects.
- [x] Disclose installer coverage before every main path; make the delivery outcome conditional.
- [x] Rejoin the observability VM alternative at source/reader checks after its project-owned service
  installation, never the Kubernetes installer; disclose missing Netdata capacity/installation.
- [x] Check the moved Stage 5 IdP and actual Stage 6 Vault/NetBox/Headlamp starters against deployment figures.
- [x] Default newly initialized local files/backups and deployment working files to private permissions;
  existing file access, Windows ACLs and off-host recovery still require manual verification.
- [x] Remove unused baseline SSH/package/firewall/NTP switches and disclose the implemented baseline scope.
- [x] Keep new-host security logging early; add explicit directory/delivery handoffs and a cluster audit gate.
- [x] Keep the logging recovery host/copies inside Tier 0 ownership while retaining separate failure/custody boundaries.
- [x] Restore the May software-intake intent as an explicit design; distinguish HTTP caching,
  HTTPS forwarding, retained mirrors, internal HTTP and target-tier update authority.
- [x] Reject empty software-source lists and remove Squid's unrestricted remote-client fallback.
- [x] Number Software intake as Stage 1 and Kubernetes as Stage 4, separate from foundation and identity;
  connect later Stage 7 Harbor/OCI supply without creating a bootstrap dependency.
- [x] Expose native Kubernetes-node image-access inputs in all three tier roots;
  retain Linux/Talos separation and require live supply/egress acceptance separately.
- [x] Preserve LF endings in source Bash entry points and compare generated text independent of checkout endings.

## Implemented priority mechanisms

- [x] **P1: Secure provider defaults (implementation).** All supplied Terraform roots explicitly
  verify Proxmox TLS. Linux, Kubernetes and template entry points reject true or malformed
  current/legacy insecure environment flags before Terraform. Bootstrap uses independently
  verified Proxmox CA trust; no automatic verification bypass is needed.
- [x] **P1: Initial trust (selected software implementation).** Native policy construction,
  explicit key/CSR preparation, offline root templates, token/CRL procedures, encrypted
  backup/clean-target restore and phased FreeIPA installation are supplied.
  Optional HSM/internal-ACME work remains separate in the [CA checklist](ca-implementation.md).
  This checks mechanism coverage, not package qualification or operational acceptance.

- [x] **P1: Logging integration - sources (selected Linux path).** Shared isolated native
  rsyslog journal/file instances with host-local keys, disk queues, cursors and independent
  source health checks; tier-local recipes/inputs include collector OS, audit and CA files.
  Native cluster-source collection has its own recipe and per-node identities;
  appliance firmware still requires product-native configuration. Register unsupported
  devices and actual kernel/runtime source gaps in the live record.
- [x] **P1: Logging integration - producer trust.** Protected Tier 0 native CSR signing,
  explicit initialization, encrypted CA key, bounded leaf renewal and cumulative CRLs;
  source private keys never leave their hosts. Client/server profiles and key fingerprints
  are explicitly approved. Existing-session withdrawal/CRL distribution remain operator recipes.
- [x] **P1: Logging integration - durable archive (NAS main path).** Create-only complete
  JSONL chunks, source catalogue, hashed linked checkpoints, cursor-after-NAS ordering,
  bounded source queues and independent health gates. Native sender release is transport-based;
  exposed tails and replay windows are explicit. No replicated-intake or zero-loss claim.
- [x] **P1: Logging integration - custody (trusted-admin NAS).** Separate transfer/read/backup
  credentials, NAS-owned snapshot commissioning contract, independent restic jobs with no prune,
  offline verifier and restore procedure, native raw/view read audit and fixed application-only
  filesystem views. Actual NAS grants/snapshots/audit and physical independence need live proof.
  [Locked retention](../docs/03-deployment/stage-2-logging/step-3d-retention-lock.md), replicated intake
  remain separate variants, not supplied by this NAS implementation. Tier 1 search is
  independently installed; approved projections and their scoped persistent exporter
  have a separate Tier 0 recipe and require live access/replay qualification.

## Remaining implementation before an end-to-end installation

Secure provider defaults and the selected software-first Initial Trust mechanisms are
supplied. Their live proof is tracked in the separate
[manual verification list](operational-verification.md), not mixed with missing implementation.

- [x] **P1: Cluster endpoint contract.** Private independent endpoint, DHCP/MAC, DNS/time
  and storage are explicit pre-bootstrap prerequisites; no public Tier 2 edge dependency.
- [x] **P1: Cluster services.** Native pinned platform, SOPS/decryption and per-node
  protected collection recipes replace the empty-starter installation gap. The
  [cluster foundation](../docs/03-deployment/stage-4-kubernetes/procedures/kubernetes.md#cluster-foundation)
  still requires live endpoint, persistence, audit and recovery acceptance.
- [x] **P1: Control application installers.** Native Keycloak, Vault, NetBox and Headlamp
  recipes include data dependencies, scoped authentication and explicit recovery gates.
  Manual initialization, enrollment and independently commissioned backup custody remain visible.
- [x] **P1: Independent monitoring and Observability installers.** Tier 1 native product
  releases and Tier 0 scoped infrastructure polling/export are supplied. Their budgets,
  replication/read routing and source coverage are explicit, not inferred from pod count.
- [ ] **Alternative: manual-cluster human SSO.** The guarded supplied rollout requires
  the original Terraform-owned plan. The manual cluster branch needs its own configuration
  persistence, reviewed rollout and recovery implementation before it can pass the complete
  Identity/Headlamp path. This is an implementation gap, not merely an unperformed live test.
- [x] **P1: Product integration mechanisms.** Tier 0 supplies approved-copy publication,
  non-root mTLS export, GET-only NetBox audit capture and independent native Vault
  snapshot/input/media transport. Search copies never acquire original-archive authority.
  Exact native qualifications and release gates are tracked in [implementation readiness](v1-readiness.md).
- [x] **P1: Recovery procedures.** Product-specific clean-target procedures cover original
  inputs/state/etcd, Vault, databases/media, identity and shared products. They do not
  equate a new bootstrap, replica count or successful backup with recovery acceptance.
- [x] **P1: Host security implementation.** Separate guarded tier-local recipes call
  Shared's native key-only SSH, chrony, firewalld and audit profile. Site allowlists,
  effective controls, out-of-band access and product compatibility still require verification.

Destructive-change drills, actual exposure enforcement and clean-room restores belong
to [manual operational verification](operational-verification.md) and
[platform acceptance](platform-verification.md). None is checked by supplying these mechanisms.
The separate tenant request dispatcher/allocation/expiry/portal is deferred, not part of
the selected v1 reference. The direct trusted-CI path is not an ordinary-user self-service boundary.

## Paths reviewed

"Reviewed" below means the entry, owner, branch/return and automation boundary were
inspected. Every selected path still needs its own live acceptance evidence.

| Path | Entry | Review outcome / remaining proof |
| --- | --- | --- |
| Bootstrap workspace | [Foundation 3a](../docs/03-deployment/foundation/bootstrap/step-3a-bootstrap-storage.md) | Local filesystem, persistent UUID mount and reboot path; independent backup/restore proof remains manual |
| Bootstrap LVM root | [Foundation 3b](../docs/03-deployment/foundation/bootstrap/step-3b-bootstrap-lvm.md) | Disk/PV/root growth or added PV; verify the real layout and retain every required disk in recovery copies |
| Bootstrap home bind | [Foundation 3c](../docs/03-deployment/foundation/bootstrap/step-3c-bootstrap-home.md) | Ownership, SSH and SELinux checks before repository/key creation; console/reboot/rollback proof remains manual |
| Offline bootstrap tooling | [Foundation 3e](../docs/03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md) | Matching OS/Python/CPU, verified bundle/provider artifacts; does not imply every later stage is disconnected-ready |
| Alternative balancing | [Foundation 4c](../docs/03-deployment/foundation/proxmox/step-4c-proxlb.md) | ProxLB qualification after API and a movable guest exist; one scheduling owner and live failover proof required |
| Existing cache update | [Software intake 2b](../docs/03-deployment/stage-1-software-intake/step-2b-adopt-update.md) | Preserve original inputs/state, refresh automation and retest consumers; verified worker installation remains Stage 3 |
| Windows Update | [Software intake 3b](../docs/03-deployment/stage-1-software-intake/step-3b-windows-update.md) | Review source and client scope, configure the chosen route and validate a representative Windows consumer |
| Bootstrap intake | [Software intake Step 6](../docs/03-deployment/stage-1-software-intake/step-6-bootstrap-consumer.md) | Apply the accepted endpoint, activate the shell and prove package/tool access before retiring temporary egress |
| Infrastructure health | [Observability Step 3](../docs/03-deployment/stage-8-observability/step-3-infrastructure-monitoring.md) | Connect Tier 0-owned hardware/host collection and approved Tier 1 metric delivery; verify alerts and isolation |
| Protected search projections | [Observability 4b](../docs/03-deployment/stage-8-observability/step-4b-protected-log-search.md) | Tier 0-approved copies and scoped ingestion; test denial/replay without granting original-archive authority |
| Private application | [Lab 3a](../docs/03-deployment/stage-10-lab-environments/step-3a-application.md) | Native namespace/application path; verify access isolation, update/rollback and recovery |
| Public website | [Lab 3b](../docs/03-deployment/stage-10-lab-environments/step-3b-public-https.md) | Existing edge or explicitly provision it first; real DNS, origin TLS, renewal/failover and denied-route proof required |
| Workload signals | [Lab 3c](../docs/03-deployment/stage-10-lab-environments/step-3c-telemetry.md) | Scoped Collector, queues and distinct credentials; verify source-to-query delivery and recovery |
| Foundation | [Preparation](../docs/03-deployment/foundation/README.md) | Network, access, templates and recovery precede capability deployment; live commissioning required |
| Software intake | [Stage 1](../docs/03-deployment/stage-1-software-intake/README.md) | Early Squid/VIP path; independent bootstrap supply and later repository/Harbor extensions; no complete patch controller |
| Logging | [Stage 2](../docs/03-deployment/stage-2-logging/README.md) | Linux/NAS recipes supplied; actual NAS custody, devices, bounded-loss fault and restore acceptance outstanding |
| Trust | [Stage 3](../docs/03-deployment/stage-3-trust/README.md) | Software PKI, native YubiHSM/PicoHSM provider and original-key issuer operations supplied; qualify physical mechanisms, CA audit, ceremonies and live recovery |
| Kubernetes | [Stage 4](../docs/03-deployment/stage-4-kubernetes/README.md) | Native node/platform/audit recipes; independent endpoint, storage, enrollment and live acceptance required |
| Identity | [Stage 5](../docs/03-deployment/stage-5-identity/README.md) | Dedicated directory, Keycloak/LDAP and staged Kubernetes SSO; ceremony, accounts and live denial/recovery acceptance required |
| Secrets | [Stage 6](../docs/03-deployment/stage-6-secrets/README.md) | Native cluster Vault/NetBox/Headlamp and independent monitoring; initialization and qualified recovery custody required |
| Delivery | [Stage 7](../docs/03-deployment/stage-7-delivery/README.md) | Native platform/Harbor plus Argo CD or complete native Spinnaker; exact selected controller, targets and live acceptance remain explicit |
| Observability | [Stage 8](../docs/03-deployment/stage-8-observability/README.md) | Native Kubernetes signal backends/UIs and independent Tier 0 polling; scoped projections and live availability/access tests remain required |
| Development platform | [Stage 9](../docs/03-deployment/stage-9-development/README.md) | Native GitLab/runner charts and separate native data VMs, dedicated infrastructure runner, Vault JWT root and saved-plan handover; data/backup commissioning and live acceptance required |
| Lab environments | [Stage 10](../docs/03-deployment/stage-10-lab-environments/README.md) | VM/cluster, bounded application/policy/RBAC, scoped telemetry and opt-in HTTPS; profiles are not an allocator; live tenant acceptance required |
| Proxmox HA | [Foundation 1b](../docs/03-deployment/foundation/proxmox/step-1b-cluster-ha.md) | Quorum/storage/fencing separate from VM creation; physical failure tests outstanding |
| Guest SDN | [Foundation 1c](../docs/03-deployment/foundation/proxmox/step-1c-sdn.md) | Manual VNet setup; verify every eligible node and one tagging owner |
| Redundant logging | [Logging 3b](../docs/03-deployment/stage-2-logging/step-3b-redundant-intake.md) | Added hosts do not establish replicated commitment or retention |
| NAS-backed evidence | [Logging 3c](../docs/03-deployment/stage-2-logging/step-3c-nas-archive.md) | Checkpoint/backup/audit-view recipes supplied; NAS-owned snapshots/accounts and live failure/access proof remain commissioning |
| Retention-locked evidence | [Logging 3d](../docs/03-deployment/stage-2-logging/step-3d-retention-lock.md) | Stronger deletion boundary documented; actual lock mode, publication, replica and recovery integration still required |
| Shared USB HSM | [Trust 1b](../docs/03-deployment/stage-3-trust/step-1b-usb-hsm.md) | Native host/provider/remoting installation and original-key checks; physical key copies, application sessions and actual failure recovery remain acceptance |
| Network HSM | [Trust 1c](../docs/03-deployment/stage-3-trust/step-1c-network-hsm.md) | Vendor commissioning/client/HA procedure required |
| Single USB device | [Trust 1d](../docs/03-deployment/stage-3-trust/step-1d-single-usb.md) | Custody/backup procedure required; availability is not inferred from a token |
| Existing managed cluster | [Kubernetes 1b](../docs/03-deployment/stage-4-kubernetes/step-1b-existing-cluster.md) | Existing IaC lifecycle owner; adoption/restore distinct from fresh bootstrap |
| Vault VM | [Secrets 1b](../docs/03-deployment/stage-6-secrets/step-1b-vault-vm.md) | Supplied host/service recipe; initialization, authorization, audit forwarding and restore remain explicit |
| Seal choice | [Secrets 1c](../docs/03-deployment/stage-6-secrets/step-1c-seal-integration.md) | Shamir/Transit/PKCS#11 capability and edition checks; no automatic migration |
| Observability VMs | [Observability 1b](../docs/03-deployment/stage-8-observability/step-1b-dedicated-vms.md) | Native seven-host products, data mounts and two-parent/five-child Netdata; live service/recovery checks remain separate from Tier 0 monitoring |
| Independent signing API | [Secrets 1d](../docs/03-deployment/stage-6-secrets/step-1d-openbao.md) | Native OpenBao/plugin and original external-key mappings, scoped certificate clients and audit; native software-token integration passed, actual Yubi/Pico/HA/recovery proof remains |
| Operator hardware authentication | [Secrets 3b](../docs/03-deployment/stage-6-secrets/step-3b-hardware-authentication.md) | Enrollment and lost-token recovery are manual; retain break-glass access |
| Argo CD | [Delivery 2a](../docs/03-deployment/stage-7-delivery/step-2a-argocd.md) | Native installation guide; restricted projects, SSO, destination and rollback acceptance required |
| Spinnaker | [Delivery 2b](../docs/03-deployment/stage-7-delivery/step-2b-spinnaker.md) | Native installation guide; storage, service identities and pipeline commissioning required |
| Source-control VM | [Development 1b](../docs/03-deployment/stage-9-development/step-1b-source-control-vm.md) | Supplied container recipe; pin image, prepare TLS and verify product backup/restore |
| General build runner | [Development 2b](../docs/03-deployment/stage-9-development/step-2b-podman-runner.md) | Supplied host recipe; registration/credentials/trust required; no Tier 0 authority |
| Image-based Linux | [Development 2c](../docs/03-deployment/stage-9-development/step-2c-image-based-linux.md) | Conversion is distro/product-specific; retain source image and test rollback |

## User and operating paths still needed

- [ ] **P2: First useful private app.** Provide one small, complete service example from
  owner/allocation through deployment, authentication, TLS, scoped logs and restoration;
  avoid requiring every optional platform service merely to validate an application.
- [x] **P2: Household/team procedures.** [Access lifecycle](../docs/05-operations/04-identity.md)
  covers client/guest/IoT networks, outage behavior, role scopes and join/leave duties.
  Actual per-product mappings, session/token withdrawal and denied access remain live checks;
  no automatic cross-product role synchronizer is claimed.
- [ ] **P2: Remote entry and publication.** Public HTTP-01, origin verification and renewal
  now have a concrete guide/recipes. A chosen VPN/admin-entry path, complete private-app path
  and live DNS/NAT/IPv6, expiry-alert and failover checks are still needed.
- [x] **P2: Upgrade and hardware procedures.** [Maintenance](../docs/05-operations/01-hosting/maintenance.md)
  defines compatibility, recovery, canary/serial health gates and host replacement.
  No universal automatic patch or rolling-upgrade controller is supplied.
- [ ] **P2: State and local inputs.** Test OS file permissions, encrypted off-host copies,
  one writer per state and retained ignored inputs. Git history alone excludes live inventory,
  secrets and state, so cloning the private repositories alone is not a disaster recovery.
- [x] **P2: Secret scanning mechanism.** Native redacted staged/history/artifact commands
  and an unprivileged fail-closed CI example are supplied. Project merge enforcement,
  runner image admission and live leakage-response exercises remain administration duties.
- [x] **P2: Provider reproducibility.** All 20 retained deployment roots have tracked provider
  locks and pass isolated provider-schema validation. Retain these locks and qualify
  future updates deliberately; no live infrastructure plan or OpenTofu parity is implied.
- [ ] **P2: Cache hardening variants.** Implement client authentication or TLS/mTLS listener
  only for a selected requirement, with support/acceptance documented; keep the HTTP proxy
  reference's limits visible and avoid implying TLS interception is required.
- [ ] **P2: Wider software intake and patch management.** The selected Linux repository/artifact
  worker is supplied; Windows, OCI vulnerability gates and broader repository-management products
  remain optional integrations. Qualify retained releases without direct client WAN access.
  Add tier-owned maintenance recipes, test rings, reboot/health gates and patch-status evidence;
  Tier 1 content services must not acquire Tier 0 execution credentials. Product selection and
  implementation for those additions remain open; transparent/TLS-intercepting proxy modes are not supplied.
  The [staged verification/quarantine contract](../docs/01-architecture/07-software-intake/01-verification.md)
  defines policy, ownership and failure behavior; distinguish its implemented Linux reference from
  unimplemented target types and from site acceptance.
- [ ] **P3: Reading density.** Split historic generated-repository upgrade detail away from
  first-use contracts; separate advanced direct-mesh storage and large cache-sizing material
  from the main path. Preserve old anchors and generated-project edits when moving content.
- [ ] **P3: GitHub diagram review.** Inspect the hosted rendering and refine layout details
  separately. Local rendering does not prove hosted parity. Check labels, replica groups,
  tier ordering and layer placement rather than equating local render success with hosted visual acceptance.

## Manual operational verification

Follow the [manual verification list](operational-verification.md) for provider trust,
Initial Trust, protected logging and development-platform handover, then the wider walkthrough.
It states prerequisites,
pass conditions and evidence for each check. No live infrastructure was available for
this preparation; all operational checks remain unchecked.

Keep private evidence in the generated project's administration records. The logging
drill already has a seed-owned record; a source review or passing local test must never
be relabelled as a deployed-system pass.


## Repeat cadence

Implementation release review, 2026-10-27: added native Spinnaker with SQL/cache and
independent backup jobs, separate GitLab data services, native storage-interface contracts, private
cluster API gateways, host controls, approved log-copy export, NetBox audit and recovery
transport. The [release qualification](v1-readiness.md) records exact tests, corrected
fixture failures, exclusions and remaining gates; historical results below are not a
claim of a single clean current run. The platform/manual operational lists remain open.

Native platform implementation review, 2026-10-26: all ten selected stages now have
explicit native execution paths and commissioning contracts. Shared supplies reusable
platform/chart/cluster-source roles; tiers retain resources, inventory, inputs and state.
Added guarded serial Kubernetes OIDC, native control applications, Delivery and
Observability, scoped lab application/telemetry and protected infrastructure CI.
Native checks found and corrected the Talos hostname-document conflict and OpenSearch
discovery/first-cluster bootstrap configuration. Database schemas now match the selected
platform operator version.

The initial **256-case** full sweep reported six documentation/visual-contract failures,
all corrected; the final **91 affected regressions passed, zero skipped**. A separate
final **38 native application/configuration checks passed, zero skipped**, including
actual provider-generated Talos configurations and matching database schemas. All
**18 Terraform roots** validated and **33 mocked plan cases** passed. Repository syntax/
duplicate-key checks covered **357 YAML files, 21 Bash scripts and 66 Python files**.
Native cluster logging also exercised local mTLS rejection and crash/queue replay.

The full sweep skipped two existing fixture-dependent cases: native offline clca
and rsyslog/GnuTLS sender recovery. These are not closed by Fluent Bit replay tests.
Selected figures were rendered on light/dark pages at normal and narrow widths;
GitHub parity and live deployment, authorization, durability, failover and restoration
remain unverified. Use [platform acceptance](platform-verification.md) for live results;
optional/remaining integrations stay listed above rather than being called installed.

Development-platform review, 2026-10-26: Stage 7 selects Argo CD or Spinnaker;
Stage 9 owns GitLab/ephemeral runners, Vault CI roles and the dedicated `iac-1` runner;
lab environments move to Stage 10. Direct CI explicitly accepts GitLab and hosting
administrators as Tier 0 authorities. A bounded tenant allocator is not supplied.
External GitLab PostgreSQL, Redis, Gitaly and object storage remain commissioned prerequisites.

Offline evidence: **181 regression cases: 179 passed, two fixture-dependent skips**
(offline clca and native rsyslog fixtures). **36 subsequent focused checks passed,
zero skipped**, covering final
installer/dependency, source/generated payload, CI safety, documentation and refresh changes.
All **18 Terraform roots** passed provider-schema validation; **30 cluster mocks and
three Vault authorization mocks** passed. The five changed figures rendered in light/dark
themes at 1100px and 760px reading widths (20 combinations). GitHub renderer parity,
live installation, SSO, policy enforcement and recovery remain unverified.

Capability and IaC alignment, 2026-10-23: foundation remains unnumbered. The nine
capabilities are Software intake, Protected logging, Cryptographic trust, Kubernetes,
Identity, Secrets, Delivery and handover, Observability and Workloads. Kubernetes now
owns node/bootstrap and add-on/audit/recovery gates; Identity consumes that platform.
Updated indexes, source pointers, generated templates and managed-guide redirects.
Existing project records, local edits/deletions, inventories and original state paths
remain protected; stage renumbering does not rename infrastructure or resource addresses.

Found and fixed missing native cluster image-access inputs and CRLF source Bash entry
points. All three roots now accept ordered Talos proxy/DNS/time/mirror patches; default
`[]` preserves the prior configuration. Native multi-document parsing checks the actual
generated configuration, including retained hostname/disk and disabled mirror fallback.
These tests do not prove routing, image availability or live policy enforcement.

**175 regression cases: 173 passed, two fixture-dependent skips** in a fresh Linux
scratch checkout. Skips were native offline clca and rsyslog/GnuTLS sender recovery;
their previous evidence is not substituted for a current run. All **16 Terraform
deployment roots** passed provider-schema validation, preserving existing locks and
resolving missing locks only in scratch. All **30 source-cluster cases** passed;
the generated-root test repeats those suites with structured native-output assertions,
not 30 additional unique mechanisms. Proxmox was mocked and all remote Talos resources
overridden; only local configuration/key generation used the real Talos provider.
Affected figures produced **36 local renders** across light/dark themes and desktop/
760px widths. HCL formatting and `git diff --check` passed. GitHub parity and all live
bootstrap, failover, access and restore acceptance remain unverified.

The support map still identifies missing product installers: the private API endpoint
is an explicit prerequisite, Stage 4 Step 2 add-ons remain the first main-path application
gap, and later cluster applications, delivery/registry, protected execution and
Observability are not installed by their empty starters. This review does not close
those implementation boxes or turn the reference into an end-to-end installer.

Software-intake capability placement, 2026-10-22: moved the proxy/cache guide out
of foundation into `deployment/stage-1-software-intake/`, with a short numbered capability
overview and the existing source-backed deployment figure. Foundation now links
to intake; Stage 5's registry procedure extends it with OCI supply without adding
a second proxy or making early bootstrap depend on Harbor. Stage numbers, resource
names and state paths are unchanged. Managed-guide moves preserve legacy anchors
and locally owned edits/deletions. **63 affected tests passed, zero skipped** in a
fresh Linux scratch repository. Both deployment figures render in light/dark themes
at normal and 760px widths. No new product installer, hosted-renderer parity or live
acceptance is established by this organization change.

Software-intake review, 2026-10-22: compared the May cache path and Squid template
at `5801e46` with the Tier 2 implementation; the template had survived unchanged.
Restored the controlled-intake design and linked foundation, host-update and
firewall references without selecting a new repository-manager product. Empty
software-source policies now fail preflight and cannot render an unrestricted
remote-client allow rule. **44 affected tests passed, zero skipped**, including
native Ansible rejection/render checks in source and freshly generated repositories.
The new architecture figure renders in both themes at desktop and 760px widths;
GitHub parity and live proxy/cache, gateway, Windows-update and patch acceptance
remain unverified. No Pulp/WSUS installer or automatic patch workflow was added.

Full consistency review, 2026-10-22: **170 native regression tests: 168 passed,
2 tool-dependent skips**, in a fresh Linux scratch copy. Skipped the offline clca
fixture and rsyslog sender outage/restart fixture; they are not new acceptance proof.
The run covered source/generated ownership and navigation, Terraform input resolution,
Ansible syntax and FreeIPA phase orchestration, native PKI policy/TLS/CRL behavior,
syslog-ng TLS/raw identity/crash restart, HAProxy parsing and restic backup/clean restore.
After final handoff/diagram changes, **45 affected tests passed, zero skipped**;
these overlap the full suite rather than adding unique cases.

All **16 Terraform deployment roots** passed provider-schema validation; existing
locks were retained, with missing locks resolved only in scratch. All three cluster
roots passed their **24 mocked plan tests**. No real infrastructure plan/apply ran.
All **76 Mermaid figures** rendered in both themes (**152 renders**). Reviewed
contact sheets and rerendered the corrected logging figures at desktop and 760px;
coordinate checks confirm tier order and Tier 0 recovery custody outside the
collector/NAS runtimes. The audit corrected reader handoffs, misplaced hardware
administration, fresh FreeIPA CA mode, private-file defaults and no-op baseline
controls. The coverage map now discloses missing installers before each main path.
Live product qualification, fault/access/restore acceptance and GitHub renderer
parity remain unverified; no operational box is checked by this review.

Stage capability naming, 2026-10-21: **163 tests: 134 passed, 29 tool-dependent skips**
in a fresh Linux scratch copy. Stage 3 is Identity, including directory authority,
the supporting cluster foundation and Keycloak/OIDC federation. Stage 4 is Secrets,
starting with Vault/audit/recovery and its renamed 1b/1c options. Removed the empty
retired workload directory: source and fresh generated trees contain exactly seven
uniquely numbered stages. Refresh redirects unchanged old guides, while preserving
local edits/deletions and project-owned records. New federation figures distinguish
existing services from an unimplemented IdP integration; no installer or live
acceptance is implied by the reorganization. Changed figures render in both themes
at desktop and 760px reading widths; hosted review remains separate.

Dependency-placement and compactness review, 2026-10-21: inventoried all **74 diagrams**
and rendered their baseline in both themes (**148 renders**). Corrected same-tier
source/controller, cluster/dedicated-control, foundation/add-on and runner/source
placement. The Vault operator now enters from the left, with recovery custody below
and outside its connected runtime. Tier 1 application starters are contained inside
Kubernetes, not beside it. Selected control-plane and edge replicas stack vertically;
protected state stacks below its runner without changing instance counts or ownership.
The **161-test** offline suite passed **132 tests, with 29 tool-dependent skips**.
New tests guard declared placement; separate Mermaid 11.17.2 coordinate checks confirm
the actual dependency order, tier stacking, compact peers and runtime containment on
light/dark pages at desktop and 760px widths. Chronological workflows, alerts and
signal-delivery arrows retain their real semantics. No infrastructure was changed;
hosted rendering and live acceptance remain separate.

Capability-stage and layout review, 2026-10-21: **154 tests: 125 passed, 29 tool-dependent skips**
in a fresh Linux scratch copy. Observability now has its own Stage 6 after control
services and the Tier 1 runtime; workloads move to Stage 7. Source/generated navigation,
managed-document redirects and local ownership preservation pass the offline suite.
Changed figures render with Mermaid 11.17.2 in light/dark themes at desktop and 760px
reading widths. Rendered coordinates confirm stacked directory peers, infrastructure
CA placement right of IdM, and administrators left of the protected alert runtime and
outside its external notification service. Heartbeats retain their actual direction.
Global diagram goals and the local diagram guide record these conventions.
No product installer, live acceptance or hosted-renderer parity is established by this review.

Observability review, 2026-10-21: **152 tests: 123 passed, 29 tool-dependent skips**
in a fresh Linux scratch copy. A separate **12-test native Terraform/Ansible run passed,
zero skipped**, covering source/generated inventory resolution, network references,
local key validation and playbook syntax; it overlaps the full suite, not an additional
12 unique cases. HCL formatting and `git diff --check` passed. Changed observability
figures render in light/dark themes at desktop and narrower reading widths.
The design is Kubernetes-first with separate workload budgets and OpenSearch initially;
the product starter remains empty. No runtime installation, failure/restore qualification,
GitHub visual acceptance or manual operational box is satisfied by these checks.

Logging installation, 2026-10-19: **142 full regression tests passed, zero skipped**;
after final probe-credential/audit changes, **37 affected tests passed, zero skipped**.
Coverage includes native reviewed-CSR client/server issuance, actual expiry-window renewal,
CRL rejection, rsyslog outage plus abrupt process restart, first-batch source identity,
create-only NAS checkpoint fixtures, application-scope denial, tamper detection, native
encrypted restic backup/clean restore, generated ownership and source/generated syntax/links.
`git diff --check` passed. No live hosts, SMB server, physical faults or NAS grants were exercised.

Native tools: syslog-ng **4.11.0**, rsyslog **8.2312.0** with GnuTLS, restic **0.16.4**,
Ansible core **2.21.5** and Python **3.12.3**. The older cached 4.3.1 receiver exposed
upstream first-read missing TLS metadata (syslog-ng #5603); the runtime now requires 4.11+.
The official Ubuntu test package was extracted, not installed; SHA-256 matched its
official index: `49d548107fcfac677892284c879d73b72bc78213bb52c202c3aca76a7c237052`.
This qualifies local interoperability, not the selected EL 10 package/SELinux/SMB deployment.
NAS snapshots, external dead-man services, independent storage and all manual operational
checks remain commissioning/acceptance work. Existing diagrams were not changed in this pass.

Operator journey, 2026-10-19: **129 baseline tests passed, zero skipped** in the isolated
Linux/WSL checkout. After handoff corrections and three new tests, **42 affected tests
passed, zero skipped**. Source/generated links, formal language, branch metadata,
state/input ownership and preservation of owned records were included.
Exercised a separate fresh five-repository collection, Tier 0 template/syslog/cluster
initialization and Tier 1 named-test initialization; no live plan or apply was run.
The test setup creates Ansible overlays but no Terraform environment overlay, matching
the corrected guide. Existing owned READMEs remain unchanged on refresh.
Diagrams were not changed or reaccepted in this pass; GitHub visual review remains separate.

Diagram review, 2026-10-19: all **65 Mermaid diagrams** render in light and dark themes
with Mermaid 11.17.2 (**130 renders**). Placement views use six block grids; interaction
views retain flowcharts and the existing sequence. Reviewed overview sheets and detailed
figures at 1100px; key placement/containment views also render at 760px without canvas
clipping. Identity coordinates verify Tier 2 above Tier 1 above the Tier 0 boundary,
with enrolled hosts to its left. Dense diagrams still require zoom at narrow widths.

The 129-case offline run passed 125 cases; one old literal signing-edge assertion needed
the new wrapped/dashed form, and three native invocations used stale local fixture paths.
All four cases passed on recheck: **16 PKI/logging/diagram tests**, then **27 final
documentation/diagram tests**, zero skipped. This is combined evidence, not a single clean
129-case run. The new palette asset follows managed auto-docs refresh/preservation rules;
no live acceptance box is satisfied by diagram or repository tests.

Archive-choice review, 2026-10-19: the full 124-case run exposed two new-option navigation
gaps. After correcting branch metadata and checklist links, **all 46 affected tests passed,
zero skipped**; the other 78 cases passed in the full run. Coverage includes both archive
choices, source/generated navigation, formal language and preservation of project records.
This archive-choice update changes documentation/templates, not receiver or storage runtime.

Previous clean full run, 2026-10-18: **123 tests passed, zero skipped** in an isolated Linux/WSL
copy. Coverage includes source/generated provider TLS defaults, environment-bypass rejection,
manual-verification separation, fresh-shell documented commands, generator refresh/link contracts,
native Terraform inputs, FreeIPA sequencing, policy construction, offline clca constraints,
HAProxy parsing and loopback syslog-ng TLS/raw-record/crash recovery.

Test tools: Python 3.12.3, Ansible core 2.21.5, Terraform 1.16.6, HAProxy 2.8.16 and
syslog-ng 4.3.1 with matching extracted modules. The latter checks isolated engine
behavior, not qualification of the documented EL 10/syslog-ng 4.8+ deployment target.
Native PKI tests used `PKI_CONFIG_REPOSITORY` at `0aa2db093e6f0573dd296c69c98c0e61d03bdf48`,
`PKI_CLCA_REPOSITORY` at `d560135cf4bbdc1916fa4c5545012085b96d4a21`,
`PKI_HAPROXY_BINARY` and `SYSLOG_NG_TEST_BINARY`/`SYSLOG_NG_TEST_MODULE_PATH`.
Those earlier changes did not alter diagrams; the 64-diagram render remains historical evidence.
No live infrastructure acceptance box above is satisfied by these results.

From an upstream checkout on Linux/WSL with the documented test tools/collections:

```bash
python3 -B -m unittest discover -s tests -p 'test_tier*.py' -v
```

Review skipped tests explicitly. For permission-sensitive WSL tests, use a checkout
on the Linux filesystem. Render changed diagrams and inspect their labels/flow in
addition to checking Markdown links and command wiring.

Repeat this walkthrough after meaningful documentation, topology, generator, inventory
or execution changes and before a release/operational handover. Reopen checks when their
contracts change. Offline tests validate the repository; only recorded live exercises
validate the selected installation. No scheduled automation is configured by this checklist.
