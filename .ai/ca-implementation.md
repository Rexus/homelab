# CA implementation checklist

Design adopted 2026-10-17; implementation coverage rechecked 2026-11-16.
Software-first mechanisms and original-key PKCS#11 installation are supplied; live CA acceptance remains outstanding.
Operational tests are in the separate [manual verification list](operational-verification.md#3-initial-trust).
This file tracks code coverage and optional integrations, not deployed-system acceptance.

Parent: [operator walkthrough](operator-walkthrough.md).
Design: [certificate authority](../docs/01-architecture/08-cryptography/01-certificate-authority.md).
Deployment: [software-first PKI](../docs/03-deployment/stage-02-trust/procedures/software-pki.md).

## Selected boundaries

- [x] Permanent OpenXPKI Community infrastructure issuer/portal on Tier 0 `ca-1`.
- [x] Separate offline clca root signs sibling infrastructure and FreeIPA CAs.
  The FreeIPA pair replicates one identity CA, not one independent CA per VM.
- [x] Vault remains a secret service, not the issuer's startup dependency or migration destination.
- [x] Native Debian package exception with a pinned application/configuration/schema set.
  The documented Debian 12 amd64 path reaches LTS end on 2028-06-30; live qualification
  must record the supported package platform and an upgrade milestone.
- [x] Tier 0 owns CA inventory/resources/state. Shared owns only reusable execution/data.
- [x] Routine convergence creates no CA keys, activates no replacement identity and rechains no domain.
- [x] Software custody is the initial path. Hardware custody and internal automated enrollment
  are separate options; they do not block acceptance of the selected software capability.
- [x] Public HTTPS uses a separate public ACME path; a public edge is not required for Tier 0 trust.

CRLs are the reference revocation path. An OCSP responder is a separate selection
and is not implied installed by the supplied issuer runtime.

## Supplied implementation

- [x] Separate signed-repository preparation and native package-candidate discovery before installation,
  requiring the publisher's independently approved key checksum. Controller-only portal CSR generation
  retains the original portal key; the normal approval and runtime recipes retire bootstrap TLS.
- [x] Tier 0 Debian template option, consumer ID/title references in Shared and foundation
  extra-disk forwarding without resource-address/state migration.
- [x] Guarded blank-disk filesystem/UUID preparation and separate offline root execution scope;
  existing, mounted and pinned-volume identities are preserved rather than reformatted.
- [x] OpenXPKI native package/database/TLS runtime with pinned input binding, empty-schema
  initialization guard and explicit runtime/key-state checks.
- [x] Deployment and maintenance recipes scoped to the issuer, independent of identity deployment.
- [x] Pinned native software/PKCS#11 policy construction, independent requester/approver roles, scoped TLS profile,
  local bootstrap administration, privileged CLI identity and CA/CRL publication settings.
- [x] Explicit encrypted software-key/CSR preparation, offline clca templates and controlled
  token import/CRL scheduling; key creation is a separately approved operation.
- [x] Encrypted application-consistent backup and clean-target restore mechanisms preserving
  issuer identity, database/history, configuration and DataVault material.
  Native backend selection covers software and exact-original-provider PKCS#11; the hardware key
  is checked through its provider and never exported. Explicit controller staging is supplied.
  Replacement-device serial rebinding uses the separate ceremony below, not automatic restore;
  PIN rotation requires its own qualified transition.
- [x] Explicit same-key PKCS#11 local-to-remote provider migration: constrained immutable-bundle revision,
  actual key/signature proof, paused encrypted recovery capture, original-state drift guards and
  prepare/apply/rollback with the latest database retained. Preserve the existing application PIN;
  rekeying, PIN rotation and schema/package upgrades are outside this recipe. A two-board upgrade
  admits one remote endpoint explicitly before freeing the original local device for the second host.
- [x] FreeIPA external CSR/pause/completion sequence with explicit CA-enabled replica.
  Existing domains are preserved; renewal/rechaining requires a separate migration procedure.
- [x] Public HTTP-01, production chain/name checks, verified origins and serialized renewal
  scheduling are supplied for the later selected HTTPS path.
- [x] [Algorithm/PQC and custody guidance](../docs/05-operations/03-cryptography/security-controls.md),
  vendor HSM timing references and a documented new-key HSM migration path.
- [x] Native local regression checks cover policy construction, ceremony constraints, inputs
  and execution boundaries. They are not live package, custody or recovery qualification.

## Optional implementation still needed

- [ ] If internal automated ACME is selected, qualify an authenticated acme2certifier RPC adapter
  with tier-scoped credentials, backend profile/name authorization, restrictive defaults,
  order/workflow correlation and restored bridge state. Community native ACME is Enterprise-only;
  EAB registration alone does not authorize arbitrary certificate requests.
- [x] Supply native YubiHSM 2/PicoHSM provider installation, original-key issuer CSR/token operations,
  restricted PKCS#11 remoting and guarded ordinary issuer activation. Native protocol fixtures pass.
- [x] Supply native PicoHSM read-only middleware/CCID preparation, public serial/reader discovery,
  blank-device commissioning instructions and original DKEK/wrapped-key replica restoration.
  Discovery of an unknown serial does not accept it for ordinary service deployment.
- [ ] Qualify physical provider/device permissions, mechanisms and independent same-key recovery.
  Gateway/device counts do not establish CA application HA or remove state/session dependencies.
- [ ] If CA application HA is required beyond tested single-writer recovery, select a supported
  database/workflow/session/key-access design and implement its coordinated failover.

## Manual acceptance

All live work remains unchecked in one authoritative place:

| Gate | Required proof |
| --- | --- |
| [TRUST-1](operational-verification.md#3-initial-trust) | Approved package/OS/configuration/schema set, independent cold start and fail-closed state guards |
| [TRUST-2](operational-verification.md#3-initial-trust) | Offline custody, approved hierarchy/constraints and unchanged signing identity |
| [TRUST-3](operational-verification.md#3-initial-trust) | Real issuance/denial/approval/renewal/revocation, fresh CRLs and accepted audit delivery |
| [TRUST-4](operational-verification.md#3-initial-trust) | Independent encrypted recovery, DataVault readability and measured RPO/RTO |
| [TRUST-5](operational-verification.md#3-initial-trust) | Same identity CA on both FreeIPA hosts and real replica/failure behavior |

Initial Trust retains local journal/audit records during bootstrap. Stage 3 then enrolls signed
network logging using the accepted infrastructure issuer; it is not an earlier trust dependency.
Forwarding/retention mechanisms are supplied but require their own live acceptance.
Hardware, an existing-domain migration,
internal ACME or public HTTPS require their own acceptance only when selected.

Keep private transcripts, fingerprints, backup IDs and reviewer decisions outside public
Git history. Update the support map only for supplied and demonstrated scope.
