# Implementation release qualification

## Contents

- [Scope](#scope)
- [Implementation work](#implementation-work)
- [Release gates](#release-gates)
- [Qualification record](#qualification-record)
- [Deferred scope](#deferred-scope)

## Scope

The target is implementation/documentation maturity for the ten selected capability stages,
not a claim of live security, availability or disaster-recovery acceptance.
Foundation hardware, Proxmox, network equipment and independent custody remain commissioned inputs.
The separate [operational verification](operational-verification.md) and
[platform verification](platform-verification.md) lists remain unchecked until live evidence exists.

Confirmed selections for this work:

- Use direct NAS file storage for supported backup/data paths; do not add a storage gateway.
  Existing qualified object storage is required only by consumers that actually need its API.
- Keep live databases on Proxmox/Ceph-backed block storage. Scheduled NAS full copies are
  accepted with completed-set recovery, not continuous PITR; legacy object/WAL inputs remain valid.
- Include the complete Spinnaker reference installation, retaining Argo CD as an alternative.
- Keep protected originals in Tier 0; export only approved copies into Tier 1 search.
- Keep direct infrastructure CI opt-in, with GitLab/control-hosting administrators trusted at Tier 0.
- Use parallel agents for bounded implementation and independent native checks.

## Implementation work

| Area | Current work / qualification |
| --- | --- |
| Linux host controls | Guarded SSH/chrony/firewalld/audit profile, source-scoped VRRP and effective collection-version gates; native render/refusal/idempotence checks passed |
| Independent API endpoint | Separate Tier 0 gateway VM pair, native HAProxy/Keepalived and SELinux permission; native parsers, ownership and three mocked endpoint plans passed |
| Protected-log projection | Create-only policy-pinned field copies, non-root persistent mTLS export and native JSON decoding; real replay/TLS/routing/permission checks passed |
| NetBox audit | GET-only retained ledger; real HTTPS pagination, redirects, trust failure and late commits tested; localized action labels do not rewrite evidence |
| Recovery | Native scheduled Vault snapshot authentication, encrypted original-input/media transport and product clean-target procedures; real restic extraction and refusal tests passed |
| GitLab data | Separate development-data root/recipe for matching native package roles, scoped object storage and backups; standalone development state preserved; chart backup schedule survives reconciliation |
| Storage interfaces | Existing NAS/file and object endpoints are explicit prerequisites, not an added gateway or VM; consumer contracts distinguish real API features, file mounts and independent recovery custody |
| PostgreSQL NAS copies | Reusable stateless role with tier-owned inputs, separate block/media/backup classes, guarded preparation, verified physical copies and clean-target recovery; 24 focused native/contract checks passed |
| GitLab VM copies | Direct filesystem or retained SFTP transport; real encrypted restic roundtrip, mount/capacity/permission/refusal and cold-copy timeout checks passed; NAS outage/readiness remains live acceptance |
| Spinnaker | Complete native reference and encrypted NAS-file/object backup choices; 26 distinct methods passed across completed focused runs and the broader interrupted run, not one clean full-module invocation |
| Reproducibility | All 20 retained Terraform roots have locks and passed isolated provider-schema validation; the Proxmox 9 follow-up passed 66 mocked cases, including explicit UEFI/static NoCloud and preserved legacy defaults |
| Secret scanning | Redacted native staged/history/artifact scanner, explicit unprivileged CI inheritance and image admission; synthetic-secret tests and public-source snapshot scans passed |
| Reading and diagrams | Capability map, native storage choices and source ownership aligned; source/generated links pass; updated storage/backup figures inspected on light/dark pages at normal/narrow widths |

## Release gates

- [x] All selected reference dependencies have supplied automation or an explicit commissioned foundation contract.
- [x] Source and fresh generated repositories include every role helper, policy, example and required collection.
- [x] Refresh preserves developer-owned/live inputs and original state; no implicit rename, import or deletion.
- [x] Portable regressions pass; failed native scopes pass focused reruns; exact exclusions are recorded below.
- [x] Terraform roots validate and selected mocked plan cases pass with tracked locks.
- [x] Generated documentation links and source-correspondence tests pass.
- [x] New implementation diagrams render legibly on normal/narrow light/dark pages; hosted parity remains manual.
- [x] Secret scan, syntax/format and scoped diff review pass; synthetic fixtures are not real credentials.
- [x] Implementation coverage and operator checklist distinguish shipped mechanisms, optional integrations and live acceptance.

## Qualification record

Review date: 2026-10-27. Tests use isolated public-source copies, synthetic credentials,
temporary local services and approved native artifacts. No infrastructure apply occurred.

Proxmox 9 and documentation follow-up:

- Selected native HA/dynamic rebalancing for Proxmox VE 9.2+, with ProxLB as an
  explicitly separate alternative. Host fencing, Ceph and actual failover remain manual gates.
- Unified Alma/Rocky/Talos image import in `foundation/proxmox/templates.md`;
  fresh cluster examples use UEFI and network-only static NoCloud, leaving accounts unset.
  Original BIOS/DHCP inputs retain their behavior; no firmware or network migration is implied.
- Grouped foundation docs by Proxmox/network/storage. Fresh architecture repositories
  seed only a short README, one selection/progress record and naming conventions beside auto-docs.
  Legacy local docs/deletions are preserved; managed old guide paths redirect to their current home.
- Full portable suite: **372 cases, 232 passed and 140 tool-dependent skips**, no failures/errors.
  All 20 roots validated and all 66 mocked Terraform cases passed. Local theme/width previews
  were inspected for HA before/after and the static-network cluster view; hosted parity remains manual.

- The 354-case full sweep reported 16 failure events across 12 cases, with four skipped cases.
  External DNS, a missing extracted syslog library, DNS-dependent loopback fixtures and an
  obsolete no-processor assertion account for those failures. All failed scopes passed focused
  reruns after corrections; this is combined evidence, not one clean 354-case native run.
- The isolated portable baseline completed 367 cases: **227 passed, 140 tool-dependent skips**,
  zero failures/errors. Optional native tools were deliberately absent from that baseline.
  Native results below overlap the full sweep and are not additional unique test counts.
- The NAS follow-up initially found two documentation mismatches, corrected before the clean rerun.
  The PostgreSQL timeout fixture initially compared formatted units rather than the canonical setting;
  after correction, all 24 focused checks passed, including disabled-timeout refusal and real TLS
  backup, verification, standalone recovery and a second physical clone. Local directories are not
  evidence of live CSI/NAS permissions, OCI-image behavior or a running CNPG operator.
- GitLab's direct file-backup work passed 17 focused native checks, including actual restic extraction,
  source/generated Ansible, ENOSPC, missing mounts, wrong passwords and timeout handling. GitLab control
  was stubbed; kernel-stalled NFS, quota/UID mapping and actual service readiness remain live gates.
- Spinnaker's 22 distinct passing methods were supplemented by four completed native methods
  covering source/generated admission, changed-review rejection, vendored provenance and selectors.
  The final four passed in 124.9 seconds; all 26 distinct methods have combined passing evidence.
- All 20 retained Terraform roots validated; 52 native mocked guest/template/cluster/endpoint cases passed.
  Generated provider-built cluster configurations also passed using a local provider mirror.
- The final native Collector rerun passed all four cases: persisted replay after abrupt termination,
  wrong CA/name/client rejection and authenticated fixed-scope routing through actual Data Prepper.
  Loopback IP transport still verifies the certificate's DNS SAN; production endpoints are unchanged.
- All seven native receiver checks passed with matching extracted libraries, including revoked
  producer rejection and actual rsyslog disk-queue outage/restart. A separate dropped-privilege
  reader test passed under umask `0077`; approved copies were readable but not writable/deletable,
  and originals remained inaccessible.
- The experimental storage-gateway implementation and its six native cases were removed after
  the storage-interface decision; those results do not qualify the retained existing-service path.
  The native PKI policy builder passed with dereferenced links, private permissions,
  immutable output and refusal checks after using the already-local copy mode.
- New source/generated artifact-download checks passed through a loopback proxy, including native
  checksum handling and a no-change rerun. Host package-manager policy remains persistent.
- Five final native chart/CA methods passed, followed by a clean three-method Helm rerun for
  source/generated Harbor, Argo CD, GitLab/runner and scoped lab collection. Exact unchanged
  cached archives were served through verified HTTPS; an unrelated CA was rejected.
- The sweep's skipped PKI policy builder, dropped-privilege reader and native rsyslog sender
  cases passed separately. The pinned offline clca fixture was **not rerun** in this pass;
  earlier evidence remains historical. Actual root ceremonies still require manual acceptance.
- Final public-source Gitleaks scanning reported no leaks. Syntax/duplicate-key checks covered
  483 YAML files, 25 Bash scripts and 91 Python files; `git diff --check` passed.
- Changed figures passed 92 Mermaid 11.17.2 renders at normal/narrow widths on light/dark pages.
  Later storage-related figures were rerendered in both themes/widths, including exact file jobs,
  live block volumes and distinct NAS backup destinations.
  Local inspection does not prove GitHub parity or deployed availability.

## Deferred scope

Tenant self-service allocation/expiry/portal, hardware HSM variants, Windows patch management,
transparent/TLS-intercepting proxy modes and replicated zero-loss logging are not part of the
selected installation. Do not describe them as shipped by checking the reference installation gates.
A turnkey SSO application, VPN automation and a universal patch controller likewise remain integrations.
Routine upgrade, hardware replacement and household/team operating guidance must remain explicit
where not automated; they do not become operationally verified through documentation changes.
