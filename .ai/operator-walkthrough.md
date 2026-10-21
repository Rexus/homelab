# Operator walkthrough checklist

Rechecked 2026-10-19 against `20efefb` and the handoff corrections below, from the
perspective of a software engineer with newly installed servers and UniFi switches.
This is the maintainer's working checklist, not generated
project documentation or a claim of production readiness.

**Scope:** clone, generation, foundation, all seven stages and adjacent options,
ordinary users, applications, maintenance, expansion and total-loss recovery.
**Evidence boundary:** source/generator review and offline tests; no live gateway,
Proxmox, HSM, service deployment, failover or disaster restore was performed.

## Current journey verdict

The engineer can generate repositories and follow the foundation procedures, but
cannot obtain the complete reference platform merely by running the supplied IaC.
The first security gate is verified Proxmox API trust; all supplied Terraform roots
now verify TLS, and provisioning entry points reject inherited insecure flags.
Stage 1 now has a selected Linux/NAS main path: reviewed-CSR producer trust, native
host forwarding, create-only checkpoints, audited file views and independent encrypted
backup. NAS snapshots/accounts and the recovery filesystem require commissioning;
physical faults and access/restore results remain manual verification. This is
asynchronous bounded-loss custody, not replicated/lossless intake. The Stage 2 policy issues
TLS-server leaves, not producer client-auth certificates. Do not bypass that gate to
declare a production PKI or assume Stage 2 automatically replaces producer trust.

Since the prior walkthrough, software PKI and public HTTPS have concrete recipes,
not just designs. Fresh-shell controller commands now select their Ansible config;
edge setup links to HTTPS and recovery links directly to issuer restoration.
Package qualification and live acceptance remain distinct from supplied mechanisms.

The fresh generated collection keeps ownership and input paths aligned. The numbered
route is understandable, but not yet an uninterrupted deployable platform: after logging,
cluster endpoints/add-ons, control applications and protected delegated execution still
need implementations. Household/team use and a complete first-app restore remain the
outcome gaps below. A clean offline suite does not close those gaps.

## Corrected reading and execution gaps

- [x] Make the front door distinguish runnable workflows from integration starters.
- [x] Keep foundation prerequisites outside numbered capability stages; logging remains Stage 1.
- [x] Prevent the Proxmox preparation guide from skipping logging and jumping to identity/clusters.
- [x] Add gateway/controller adoption and VLAN/port preparation before the UniFi policy matrix.
- [x] Distinguish ordinary client access ports from server trunks and supported multi-switch aggregation.
- [x] Put the existing Linux-provider TLS exception in the API setup gate, not only the HA guide.
- [x] Document verified Proxmox bootstrap trust and optional API certificate migration after PKI.
- [x] Add a logging fault/restore drill, seed-owned evidence record and offline reconciliation checks.
- [x] Supply a Tier 0 syslog-ng receiver with mount/TLS guards, raw JSON records and native local tests.
- [x] Explain that `--env` does not allocate unique VMIDs, addresses, VIPs or security boundaries.
- [x] Keep directory deployment in the trust stage's existing context/state instead of silently switching to test.
- [x] Add initialization and plan/review/deploy commands to cache, edge and Vault paths.
- [x] Initialize test inputs before VM source-control, runner and image-builder commands.
- [x] Separate plan and apply blocks; retain a human input/allocation review between them.
- [x] Add Vault CLI endpoint/trust selection and authentication before audit configuration.
- [x] Remove repeated identity-authentication and Vault-shape explanations in favor of their authoritative homes.
- [x] Align generated setup ownership and template references with logging and unnumbered foundation.
- [x] Use an ignored Python virtual environment for the generator dependency instructions.
- [x] Reproduce and fix missing-role failures in direct PKI/scheduler commands; test the documented invocations.
- [x] Connect edge publication and total-loss recovery to the new HTTPS and issuer-restore procedures.
- [x] Separate NAS-backed trusted-admin retention from optional storage-enforced locks;
  link both Stage 1 branches and record custody/review triggers in the evidence template.
- [x] Use `syslog` in fresh Tier 0 README quick starts, in the same base state context as
  Stage 1; link environment isolation beside optional `--env`, and retain storage/TLS preparation gates.
- [x] Point test source-control, runner and image-builder instructions at their selected
  Ansible test vars and explicit complete-map Terraform overlays, including final conversion.
- [x] Prepare/test local-input recovery before provisioning; test guest restore after the
  first disposable clone, and accept verified existing backup services without requiring PBS.
- [x] Clarify the independent producer-authority handoff instead of assuming the software
  PKI's TLS-server profile also issues logging client certificates.
- [x] Align remaining IdP wording and the image-builder's shared-catalog comment with their authoritative contracts.

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
  Appliance firmware and Kubernetes collectors remain explicitly selected product integrations,
  not falsely implied host-role coverage. Register unsupported-device gaps in the live record.
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
  [Locked retention](../docs/deployment/stage-1-logging/step-3d-retention-lock.md), replicated intake
  and later Tier 1 search remain separate variants, not supplied by this NAS implementation.

## Remaining implementation before an end-to-end installation

Secure provider defaults and the selected software-first Initial Trust mechanisms are
supplied. Their live proof is tracked in the separate
[manual verification list](operational-verification.md), not mixed with missing implementation.

- [ ] **P1: Cluster API endpoint.** Supply a tested private endpoint recipe or a clearly
  verified existing prerequisite before cluster bootstrap. It must not require the public
  Tier 2 edge or the cluster it serves. Include DHCP/MAC reservations and bootstrap DNS/time.
- [ ] **P1: Cluster services.** Add release-pinned delivery, decryption, persistence,
  certificate/ingress and database manifests with health/dependency gates. Empty Kustomize
  directories do not implement the [cluster foundation](../docs/deployment/stage-3-identity/procedures/kubernetes.md#cluster-foundation).
- [ ] **P1: Control applications.** Implement and verify the selected IdP, inventory
  application, cluster interface and cluster-based secret service, including scoped roles,
  data dependencies, audit forwarding and backups. The Vault VM alternative is a different runtime.
- [ ] **P1: Independent monitoring and Observability.** Supply native Tier 1 Kubernetes
  product manifests/values for Collector gateways, VictoriaMetrics, Data Prepper,
  OpenSearch and UIs; the current starter is empty. Budget/scale each workload separately.
  Configure replicated writes, query failover, search quorum/shards and restore paths.
  Keep Tier 0 evidence and critical external alerts independent. Test scoped read-only
  copies, forged ownership and outages; diagrams are not configured controls.
- [ ] **P1: Protected execution.** Implement the approved Tier 0 runner/controller path
  before delegated provisioning. General runner registration and source-control branch
  protection must not be treated as that authorization boundary.
- [ ] **P1: Destructive-change protection.** Rehearse allocation collisions, state
  ownership, complete-map overlays and accidentally removed definitions. Consider a focused
  preflight for concurrent environments; current naming/state separation is not an allocation service.
- [ ] **P1: Clean-room recovery.** Write and execute product-specific restores for
  directory/CA data, original cluster secrets/state plus etcd, persistent application data,
  secret-service data/keys and protected logs. Restore is not another fresh-cluster bootstrap.
- [ ] **P1: Exposure acceptance.** Verify gateway, host and workload enforcement, actual
  TLS/listeners, IPv4/IPv6, VPN and same-subnet isolation before opening any service externally.
  A firewall design or Ansible baseline is not an attack-resistance certification.

## Paths reviewed

"Reviewed" below means the entry, owner, branch/return and automation boundary were
inspected. Every selected path still needs its own live acceptance evidence.

| Path | Entry | Review outcome / remaining proof |
| --- | --- | --- |
| Foundation | [Preparation](../docs/deployment/foundation/README.md) | Network, access, templates and recovery precede capability deployment; live commissioning required |
| Logging | [Stage 1](../docs/deployment/stage-1-logging/README.md) | Linux/NAS recipes supplied; actual NAS custody, devices, bounded-loss fault and restore acceptance outstanding |
| Trust | [Stage 2](../docs/deployment/stage-2-trust/README.md) | Software PKI and file/journal forwarding supplied; qualify packages, actual CA audit scope, ceremonies and live acceptance; hardware remains integration |
| Identity | [Stage 3](../docs/deployment/stage-3-identity/README.md) | Directory recipe and new-cluster lifecycle supplied; endpoint/add-ons and federation manifests still required |
| Secrets | [Stage 4](../docs/deployment/stage-4-secrets/README.md) | Secret-service and supporting cluster integrations are starters; independent monitoring has its own path |
| Delivery | [Stage 5](../docs/deployment/stage-5-delivery/README.md) | VM alternatives supplied; controller, registry and protected execution require selected integrations |
| Observability | [Stage 6](../docs/deployment/stage-6-observability/README.md) | Separate capability after control and platform runtime; Kubernetes product starter is empty, with dedicated-VM baseline as an alternative |
| Workloads | [Stage 7](../docs/deployment/stage-7-workloads/README.md) | VM/cluster resources and opt-in public HTTPS supplied; application manifests, policies, alerts and live publication acceptance remain project work |
| Proxmox HA | [Foundation 1b](../docs/deployment/foundation/step-1b-cluster-ha.md) | Quorum/storage/fencing separate from VM creation; physical failure tests outstanding |
| Guest SDN | [Foundation 1c](../docs/deployment/foundation/step-1c-sdn.md) | Manual VNet setup; verify every eligible node and one tagging owner |
| Outbound cache | [Foundation 3b](../docs/deployment/foundation/step-3b-outbound-cache.md) | Supplied Squid/VIP recipe; independent bootstrap egress and declared transport limits |
| Redundant logging | [Logging 3b](../docs/deployment/stage-1-logging/step-3b-redundant-intake.md) | Added hosts do not establish replicated commitment or retention |
| NAS-backed evidence | [Logging 3c](../docs/deployment/stage-1-logging/step-3c-nas-archive.md) | Checkpoint/backup/audit-view recipes supplied; NAS-owned snapshots/accounts and live failure/access proof remain commissioning |
| Retention-locked evidence | [Logging 3d](../docs/deployment/stage-1-logging/step-3d-retention-lock.md) | Stronger deletion boundary documented; actual lock mode, publication, replica and recovery integration still required |
| Replicated USB HSM | [Trust 1b](../docs/deployment/stage-2-trust/step-1b-usb-hsm.md) | Host pool and optional snippet only; provider/application/key readiness and endpoint require implementation |
| Network HSM | [Trust 1c](../docs/deployment/stage-2-trust/step-1c-network-hsm.md) | Vendor commissioning/client/HA procedure required |
| Single USB device | [Trust 1d](../docs/deployment/stage-2-trust/step-1d-single-usb.md) | Custody/backup procedure required; availability is not inferred from a token |
| Manual cluster | [Runtime 2b](../docs/deployment/stage-3-identity/step-2b-manual-cluster.md) | Valid alternative lifecycle owner; adoption/restore distinct from fresh bootstrap |
| Vault VM | [Secrets 1b](../docs/deployment/stage-4-secrets/step-1b-vault-vm.md) | Supplied host/service recipe; initialization, authorization, audit forwarding and restore remain explicit |
| Seal choice | [Secrets 1c](../docs/deployment/stage-4-secrets/step-1c-seal-integration.md) | Shamir/Transit/PKCS#11 capability and edition checks; no automatic migration |
| Observability VMs | [Observability 1b](../docs/deployment/stage-6-observability/step-1b-dedicated-vms.md) | Separate-role fallback to Tier 1 Kubernetes; baseline only, not Tier 0 monitoring |
| Operator hardware authentication | [Secrets 3b](../docs/deployment/stage-4-secrets/step-3b-hardware-authentication.md) | Enrollment and lost-token recovery are manual; retain break-glass access |
| Source-control VM | [Delivery 1b](../docs/deployment/stage-5-delivery/step-1b-source-control-vm.md) | Supplied container recipe; pin image, prepare TLS and verify product backup/restore |
| General build runner | [Delivery 1c](../docs/deployment/stage-5-delivery/step-1c-podman-runner.md) | Supplied host recipe; registration/credentials/trust required; no Tier 0 authority |
| Image-based Linux | [Delivery 1d](../docs/deployment/stage-5-delivery/step-1d-image-based-linux.md) | Conversion is distro/product-specific; retain source image and test rollback |

## User and operating paths still needed

- [ ] **P2: First useful private app.** Provide one small, complete service example from
  owner/allocation through deployment, authentication, TLS, scoped logs and restoration;
  avoid requiring every optional platform service merely to validate an application.
- [ ] **P2: Household access.** Add a short outcome path for family, guest and IoT devices:
  client networks, Wi-Fi/ports, permitted apps, optional discovery/printers and denied Control
  access. Include local Internet/DHCP/DNS behavior during platform outages.
- [ ] **P2: Small-team access.** Add onboarding/offboarding and a tested role matrix for
  administrator, developer, employee and guest. Verify repository/app/log scopes and session,
  token and device removal; a shared identity source does not implement application authorization.
- [ ] **P2: Remote entry and publication.** Public HTTP-01, origin verification and renewal
  now have a concrete guide/recipes. A chosen VPN/admin-entry path, complete private-app path
  and live DNS/NAT/IPv6, expiry-alert and failover checks are still needed.
- [ ] **P2: Upgrade and hardware replacement.** Supply a routine calendar/runbook with
  release compatibility, serial health gates, rollback, node/storage retirement and recovery
  on replacement hardware. Existing worker-pool guidance is not a rolling-upgrade controller.
- [ ] **P2: State and local inputs.** Test OS file permissions, encrypted off-host copies,
  one writer per state and retained ignored inputs. Git history alone excludes live inventory,
  secrets and state, so cloning the private repositories alone is not a disaster recovery.
- [ ] **P2: Secret scanning.** Select a project enforcement mechanism for staged content,
  CI output and artifacts; `.gitignore` does not prevent forced additions or tracked secrets.
- [ ] **P2: Cache hardening variants.** Implement client authentication or TLS/mTLS listener
  only for a selected requirement, with support/acceptance documented; keep the HTTP proxy
  reference's limits visible and avoid implying TLS interception is required.
- [ ] **P3: Reading density.** Split historic generated-repository upgrade detail away from
  first-use contracts; separate advanced direct-mesh storage and large cache-sizing material
  from the main path. Preserve old anchors and generated-project edits when moving content.
- [ ] **P3: GitHub diagram review.** Inspect the hosted rendering and refine layout details
  separately; no topology redraw is part of this operator pass. Check labels, replica groups,
  tier ordering and layer placement rather than equating local render success with hosted visual acceptance.

## Manual operational verification

Follow the [manual verification list](operational-verification.md) for provider trust,
Initial Trust and protected logging, then the wider walkthrough. It states prerequisites,
pass conditions and evidence for each check. No live infrastructure was available for
this preparation; all operational checks remain unchecked.

Keep private evidence in the generated project's administration records. The logging
drill already has a seed-owned record; a source review or passing local test must never
be relabelled as a deployed-system pass.


## Repeat cadence

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
