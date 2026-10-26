# Manual operational verification

All checks are **Not tested** until an authorized operator records a real result.
This list is deliberately separate from [missing implementation](operator-walkthrough.md#remaining-implementation-before-an-end-to-end-installation).
Local tests prove mechanisms, not a deployed environment. No live infrastructure was
available during the 2026-10-18 preparation.
New platform installers use the focused [Stages 4-10 acceptance list](platform-verification.md).
Its rows remain unverified until an authorized operator records real results.

## Contents

- [Use this list](#use-this-list)
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

## 1. Secure provider defaults

**Implementation:** supplied. Fresh source/generated roots use verified TLS; the wrappers
reject current and legacy insecure environment flags. Existing project edits are preserved
by refresh and therefore still require review.
**Procedure:** [Proxmox bootstrap trust and PKI transition](../docs/administration/compute/proxmox-tls.md).

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
[pipeline contract](../docs/reference/logging-pipeline.md). Commission actual NAS
snapshots/accounts/audit, independent backup storage and external dead-man alerts
before these checks. Device-native and Kubernetes collector variants require their
selected integrations. Do not pass this section with only the local receiver.
Select [A: NAS-backed or B: retention-locked](../docs/architecture/operations/log-retention.md)
and record trusted administrators. One homelab operator may hold all roles under A
using separate credentials; this does not claim protection against that administrator.
**Procedure:** [fault/restore drill](../docs/administration/logging-drill.md).
**Record:** the Tier 0 project's `docs/administration/logging-evidence.md`.

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
**Procedures:** [software PKI](../docs/deployment/stage-3-trust/procedures/software-pki.md),
[CA operations](../docs/administration/cryptography/certificate-authority.md).
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

**Procedure:** [Stage 9](../docs/deployment/stage-9-development/README.md).
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
- [ ] Boot a disposable clone; verify SSH, DNS, time, network denials and backup restore.
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
