# Manual operational verification

All checks are **Not tested** until an authorized operator records a real result.
This list is deliberately separate from [missing implementation](operator-walkthrough.md#remaining-implementation-before-an-end-to-end-installation).
Local tests prove mechanisms, not a deployed environment. No live infrastructure was
available during the 2026-10-18 preparation.
New platform installers use the focused [Stages 4-10 acceptance list](platform-verification.md).
Its rows remain unverified until an authorized operator records real results.

## Contents

- [Use this list](#use-this-list)
- [Software intake](#software-intake)
- [Secure provider defaults](#1-secure-provider-defaults)
- [Logging integration](#2-logging-integration)
- [Initial Trust](#3-initial-trust)
- [Development platform and CI handover](#4-development-platform-and-ci-handover)
- [Wider walkthrough](#wider-walkthrough)

## Use this list

1. Complete the implementation prerequisites for the selected path.
2. Use disposable targets, independent backups, a change window and recorded undo steps.
3. Record Passed, Failed, Not tested or Not applicable (with a reason), UTC time,
   deployed revision, evidence location and reviewer in private project administration
   records. Check a box only after its pass condition is demonstrated. Never place raw
   logs, credentials or keys in Git.

The order is API trust, early logging, then Initial Trust. PKI must not be used as a
prerequisite for the logging path that records its own bootstrap ceremony.

## Software intake

**Implementation:** hardened proxy/native consumer policy and optional Tier 1 RPM/APT/artifact
verification, ClamAV quarantine and immutable publication are supplied. OCI vulnerability policy
and automatic patch rollout remain separate integrations.
**Procedure:** [Stage 1](../docs/03-deployment/stage-1-software-intake/README.md) and
[existing-cache migration](../docs/03-deployment/stage-1-software-intake/step-2b-adopt-update.md#3-reconcile-the-existing-cache).
The first five checks cover the basic route; the remaining checks apply to the selected
[verified extension](../docs/03-deployment/stage-3-trust/step-3b-verified-intake.md). None qualify patch rollout.

- [ ] **INTAKE-1: Real network enforcement.** From every selected subnet, approve actual sources and
  redirects; deny another source, a forbidden client and direct WAN bypass. Check HTTP and CONNECT,
  both nodes and the VIP. No unrestricted fallback may appear when the proxy is unavailable.
- [ ] **INTAKE-2: Native consumer failures.** On disposable Debian/Proxmox and EL targets, reject an
  unavailable required repository, unsigned/invalid content and expired applicable metadata. Prove
  installation stops; retain valid publisher keys and audit per-repository overrides separately.
- [ ] **INTAKE-3: Cache semantics and events.** Exercise cacheable, private, no-store and refreshed
  test content. Confirm only eligible objects hit cache. Use dummy URL credentials/query markers
  and require sanitized access events without them. CONNECT does not produce a scan verdict.
- [ ] **INTAKE-4: Availability and recovery.** Fail Squid/its VM and test actual VIP takeover, then
  rebuild a cache without recovering its disposable data. Qualify host placement and outage limits;
  boot-1's independent tools/artifacts must remain usable without the pair.
- [ ] **INTAKE-5: Protected decisions.** After Stage 2 commissioning, retain each cache's security
  journal/access stream in Tier 0. Verify scoped reads and queued delivery through a logging outage;
  repeat with OpenSearch unavailable. Do not interpret later search availability as durable custody.
- [ ] **INTAKE-6: Real repository fixtures.** On the selected EL10/Debian worker, acquire a small
  vendor-signed RPM and APT subset and a trusted artifact. Verify immutable HTTPS publication and
  native consumer refresh. Reject changed metadata/packages, wrong keys, expiry and bad hashes.
- [ ] **INTAKE-7: Gate and isolation.** In a disposable source, reject EICAR, unsupported/encrypted/
  oversized files and stale/missing/erroring scanners. Fetch/scan/web identities cannot write accepted
  bytes; denied clients/methods and direct WAN bypass fail. Preserve prior selection on rejection.
- [ ] **INTAKE-8: Service/storage failure.** Qualify real systemd/SELinux, boot, timer and definition
  updates; interrupt jobs and lose/fill the data mount. Private remnants never become served content.
  Check hold/expiry behavior and protected Tier 0 decision delivery independently of the search UI.
- [ ] **INTAKE-9: Recovery and selection.** Restore OS/data disks and policy/trust to an isolated
  target, verify retained hashes and current definitions, then select a still-valid previous version
  in a consumer. Retain usable Tier 0 supply without the worker or proxy.

## 1. Secure provider defaults

**Implementation:** supplied. Fresh source/generated roots use verified TLS; the wrappers
reject current and legacy insecure environment flags. Refresh preserves project inputs;
review local overrides and the refresh report before accepting existing TLS configuration.
**Procedure:** [Proxmox bootstrap trust and PKI transition](../docs/05-operations/hosts/proxmox-tls.md).

- [ ] **TLS-1: Verified bootstrap.** Independently verify the Proxmox CA fingerprint, install
  its public trust on every execution host/container and use a name covered by the certificate.
  Pass when a normal plan succeeds against each eligible node without a bypass.
- [ ] **TLS-2: Negative verification.** On a disposable target/context, try an untrusted CA,
  wrong hostname and an expired test certificate. Pass when the real caller rejects each
  TLS failure; retain the errors, not API credentials. Restore the approved context afterward.
- [ ] **TLS-3: Every caller.** Check Linux provisioning, template publication, each tier's
  Kubernetes plan, runners and Packer separately. Pass when none inherits a verification
  bypass and each uses the intended trust store. Do not apply unrelated infrastructure changes.
- [ ] **TLS-4: Rotation and recovery.** If platform-issued API certificates are selected,
  distribute trust before rotating the leaf; test renewal, rollback and a replacement runner.
  Pass when the same state/resources remain usable without restoring an insecure setting.

## 2. Logging integration

**Implementation:** selected Linux/NAS recipes are supplied; follow the
[pipeline contract](../docs/08-reference/logging-pipeline.md). Commission actual NAS
snapshots/accounts/audit, independent backup storage and external dead-man alerts
before these checks. Device-native and Kubernetes collector variants require their
selected integrations. Do not pass this section with only the local receiver.
Select [A: NAS-backed or B: retention-locked](../docs/01-architecture/24-operations/02-log-retention.md)
and record trusted administrators. One homelab operator may hold all roles under A
using separate credentials; this does not claim protection against that administrator.
**Procedure:** [fault/restore drill](../docs/05-operations/logging-drill.md).
**Record:** the Tier 0 project's `docs/05-operations/logging-evidence.md`.

- [ ] **LOG-1: Real source delivery.** Emit numbered records from Proxmox, supported network
  devices, collector OS and the CA host; extend to every tier as it exists. Pass when retained
  records preserve identity/timestamps and the authenticated source catalogue matches.
  Include the first burst immediately after a fresh TLS handshake, without warm-up;
  verify the deployed 4.11+ receiver preserves every expected source identity then.
  Document every unauthenticated or unbuffered first-hop exception.
- [ ] **LOG-2: Authorization and retention.** Exercise producer, approved reader and custodian
  roles. Pass when forged ownership, cross-scope reads and producer/query overwrite or
  deletion are denied; authorized reads/exports are audited. Under A, also deny snapshot/
  backup administration to the transfer identity and prove checkpoint restoration;
  under B, prove retained-version deletion and early retention shortening are denied.
  Collector or application administration must not erase the independent retained copies.
  If app-owner reads are exposed, test their scope with dummy streams; otherwise keep
  raw access denied and qualify later analytics views separately.
- [ ] **LOG-3: Declared durability.** Reconcile before/during/after batches across process,
  host/power, network and archive failures within the approved failure envelope. Pass when
  independently protected checkpoints survive and measured loss/replay/duplicates meet the
  declared RPO. NAS main-path native queues release on transport; measure that exposed tail,
  source retention and snapshot/backup lag, never claim application-acknowledged replication.
  The stronger intake variant must separately prove its release/commit contract.
- [ ] **LOG-4: Bounded exhaustion and independence.** On capped disposable storage, test queue
  pressure and a Tier 1/cluster/SSO outage. Pass when the recorded backpressure policy and
  independent alerts operate, and authorized Tier 0 investigation remains possible.
- [ ] **LOG-5: Disk-only and independent-backup restore.** Inspect a preserved volume copy,
  then extract the covered event set from an independent backup on a clean isolated target.
  Pass when original digests/source metadata and expected records match, keys/tools work
  without the original platform, and observed RPO/RTO meet the selected policy.

There is no unconditional "never lose any event" pass. Record the tested failure
envelope, accepted-event boundary, queue limits and any source-side gaps explicitly.

## 3. Initial Trust

**Implementation:** the selected software-first path is supplied; package/runtime and
security behavior still need live qualification. Hardware custody, internal automated
ACME and public edge HTTPS are separate selections, not hidden bootstrap requirements.
**Procedures:** [software PKI](../docs/03-deployment/stage-3-trust/procedures/software-pki.md),
[CA operations](../docs/05-operations/cryptography/certificate-authority.md).
**Coverage and variants:** [CA implementation checklist](ca-implementation.md).

- [ ] **TRUST-1: Qualified runtime.** Deploy the pinned package/configuration/schema set on
  the approved OS with prepared encrypted storage and independently held recovery keys.
  Pass when restart/cold boot work without higher
  tiers, SSO or Vault, the portal verifies TLS, and missing storage/state/key material fails closed.
  Record the package/OS upgrade milestone and recovery artifacts.
- [ ] **TRUST-2: Custody and hierarchy.** Rehearse root initialization/restore and subordinate
  signing with disposable material. Pass when approved keys, constraints, issuer fingerprints
  and infrastructure chain match; the root remains offline and no routine rerun creates
  replacement keys. Verify the sibling identity chain when its Stage 5 CA is added.
  Keep ceremony approval and transfer records independently.
- [ ] **TRUST-3: Policy and revocation.** Submit approved and forbidden requests with real
  requester/approver identities. Pass when unauthorized SANs/profiles/CA requests and
  self-approval are denied; renewal works, scheduled CRLs stay fresh and an enforcing client
  rejects a revoked leaf. Replace bootstrap portal TLS under the approved trust transition,
  retain independent recovery access and audit operations through the accepted logging path.
- [ ] **TRUST-4: Same-identity recovery.** Make an encrypted application-consistent backup,
  restore on a clean isolated target and disable the original service/later-tier dependencies.
  Pass when signing identity, issuance/revocation history and DataVault readability survive,
  issuance/CRL signing resume, and observed RPO/RTO meet policy. Never run both restored writers.
  Rehearse a compatible application/configuration/schema upgrade and rollback without
  rewinding issuance or revocation history.
- [ ] **TRUST-5: Identity replica (Stage 5).** Complete the external FreeIPA CSR/sign/import flow and
  explicitly CA-enabled replica. Pass when both hosts issue under the same expected identity
  CA, directory/DNS replication work and loss of either host is tolerated. Two healthy VMs
  or LDAP replication alone do not prove this. This extends trust in Stage 5; it is not
  a prerequisite for accepting the independent Stage 3 issuer.

## 4. Development platform and CI handover

**Procedure:** [Stage 9](../docs/03-deployment/stage-9-development/README.md).
The supplied charts, runner role, Vault policy and saved-plan helpers have no live acceptance yet.

- [ ] **CI-1: Application and recovery.** Verify external PostgreSQL/Redis/Gitaly/object
  storage, approved TLS, SSO membership and clone/push. Restore GitLab data and secrets
  on a clean target, including repository/object-store consistency; two web pods prove no HA.
- [ ] **CI-2: General job isolation.** Verify ephemeral pod cleanup, image limits, non-root
  execution and actual CNI egress denial. A job must not obtain manager/API credentials
  or reach Tier 0 control services. Check server-side runner/project assignments.
- [ ] **CI-3: Trust and Vault denials.** Record accepted Tier 0 trust for GitLab and hosting
  administrators. Test exact audience/project/namespace/protected-branch claims, role expiry
  and forbidden secret paths. Confirm ordinary projects cannot use the protected runner.
- [ ] **CI-4: Original-state handover.** Restore the persistent collection, plan without
  replacement, apply the reviewed saved plan once, and reject stale/mismatched plans.
  Verify private files, revoked job Vault tokens, no sensitive artifacts and protected audit intake.
- [ ] **CI-5: Independent recovery.** With GitLab, Vault and normal SSO unavailable, use
  the disconnected recovery kit and original state to regain authorized control.
  Restore normal CI only after verifying credentials, state continuity and audit evidence.

## Wider walkthrough

The focused sections above do not accept the rest of the platform. After those
gates pass, continue the broader operator journey:

- [ ] Cold-start gateway/controller, switches and the first server with only the offline kit.
- [ ] Restore the full-clone bootstrap backup on a recovery host with the original platform
  unavailable. Include its OS and workspace disks, original state, ignored inputs and key
  custody. Verify logins for the approved workstation keys and outbound deployment access.
  If data-disk homes are selected, verify mount order, SELinux/SSH permissions and recovery
  with the data disk unavailable; stale homes must not silently become the active account data.
- [ ] Install the bootstrap tools from the transferred bundle with public egress denied.
  Record OS/Python/architecture and kit revision, dependency resolution, verified provider
  initialization and a non-mutating API plan. After intake acceptance, verify bootstrap
  updates through the approved proxy/mirrors and rejected direct WAN bypass.
- [ ] Boot a disposable clone; verify SSH, DNS, time, network denials and backup restore.
- [ ] If [SDN subnet lookup](../docs/08-reference/network-inputs.md#sdn-subnet-lookup) is selected,
  verify a disposable Linux/container and Kubernetes plan against applied Proxmox metadata.
  Pass when inventory IPs retain the expected prefix/gateway, the token needs only scoped
  read/attachment permissions, and missing permissions or ambiguous subnets fail the plan.
  Record the SDN backup and explicit-input recovery path; never apply unrelated resources.
- [ ] Run test and production concurrently with non-overlapping allocations and separate state.
- [ ] Repeat plans after Proxmox migration and after an approved host-failure exercise.
- [ ] Disable Tier 1/2 and normal SSO; verify Tier 0 logging, administration and critical alerts.
- [ ] Verify app-owner reads and rejected cross-app reads, deletion and archive/backup administration.
- [ ] Restore one service and its data onto replacement hardware inside recorded RPO/RTO.
- [ ] Read protected logs with infrastructure offline using only a preserved volume and reader/key kit.
- [ ] Perform a clean-room total-loss recovery from independent copies; record every missing input.
- [ ] Recheck user-visible functions, credentials, audit continuity and failure alarms after recovery.

Public HTTPS renewal, hardware-specific custody and an existing-domain CA migration
need their selected procedures and separate evidence when those options are used.
