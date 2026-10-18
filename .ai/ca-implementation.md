# CA implementation checklist

Design and contracts adopted 2026-10-17; implementation status rechecked 2026-10-18.
Tier 0 runtime, software policy/custody/recovery recipes and the external identity
CA sequence are supplied; live CA acceptance remains outstanding.
Routine convergence never creates keys or rechains identity. The software-first
path adds separately approved fresh-key and clean-target recovery recipes.
Parent: [operator walkthrough](operator-walkthrough.md).
Authoritative design: [certificate authority](../docs/architecture/cryptography/certificate-authority.md).

## Selected contract

- [x] Permanent OpenXPKI Community infrastructure issuer and portal on Tier 0 `ca-1`.
- [x] Offline clca root signs sibling OpenXPKI and FreeIPA CAs; the directory pair replicates one identity CA.
- [x] Vault remains the secret service; no intended CA migration or startup dependency.
- [x] Native Debian package exception; qualify package/configuration/schema as one recoverable set.
- [x] Community ACME requires a qualified adapter; OCSP is separate; neither is implied installed.
- [x] Independent custody, DataVault recovery and no silent replacement signing identity.
- [x] Selected first deployment: fresh root/FreeIPA domain, software issuer keys,
  public HTTP-01 and a documented new-key HSM migration path.
- [x] Pinned native policy builder, independent approval, DNS-scoped TLS profile,
  privileged CLI identity and explicit key/CSR preparation.
- [x] Native public ACME role, all-node challenges, production chain/name checks,
  verified origins and serialized controller renewal schedule.
- [x] Software backup/clean-target restore mechanisms and concrete offline root templates.
- [x] Current algorithm/PQC guidance and vendor HSM timing reference, checked 2026-10-18.
- [ ] Qualify the built policy against a live approved OpenXPKI package/schema set;
  prove denial, renewal, revocation, CRL scheduling and audit delivery.
- [ ] Rehearse live encrypted backup/clean-target restore, FreeIPA CA replication,
  public domain renewal, edge SELinux/failover and independent alerts.

## 1. Host and custody prerequisites

- [ ] Revalidate upstream package platforms and the approved OS lifecycle; current documented
  Debian 12 amd64 path reaches LTS end on 2028-06-30. Set an upgrade milestone before adoption.
- [x] Add a verified Tier 0 Debian template publication option or document a tested existing
  approved image; keep only consumer ID/title references in Shared. Never silently use EL10.
- [x] Expose/forward the existing guest module's `extra_disks` contract through the foundation
  root without changing existing resource addresses or state; test unchanged old inputs.
- [x] Define data-mount guards, software-key custody and encrypted application-consistent backup recipes.
- [ ] Prepare and live-verify encrypted volumes, independent recovery keys and off-host copies; no automatic formatting.
- [x] Remove root hosts from connected `foundation` execution scope. The existing separate
  ceremony runbook requires a disconnected inventory; the empty compatibility group remains empty.
- [ ] Qualify one provider path initially with disposable keys; test engine/provider versions,
  mechanisms, labels/attributes and same-identity recovery before touching real CA material.

## 2. Online issuer implementation

- [x] Add a Tier 0 `openxpki` role with native Ansible modules/collections, explicit Debian
  support checks, approved signed artifacts and local MariaDB/Apache/OpenXPKI configuration.
- [x] Add deployment and maintenance recipes with explicit issuer selection. Keep `ca-1`
  in existing foundation state; Stage 2 issuer operations must not install the identity pair.
- [x] Keep package/configuration convergence separate from schema changes, key creation,
  token import/activation, initial CA signing, rollover and recovery. Missing keys fail closed.
- [x] Supply restrictive profiles, independent requester/approver roles, privileged CLI identity,
  pinned bootstrap portal TLS and native CA/CRL publication configuration; no demo credentials.
- [ ] Replace bootstrap portal TLS, integrate Stage 1 audit forwarding and prove policy denials live.
- [x] Bind database/session/configuration inputs and supply encrypted backup/clean-target restore
  mechanisms preserving signing identity and DataVault material.
- [ ] Qualify recovery and a compatible application/configuration/schema upgrade on real services.

## 3. Root and identity integration

- [ ] Rehearse the complete root/issuer ceremony, subordinate constraints, CRLs, transfer
  records and offline restore using disposable material; serialize clca state operations.
- [x] Split external FreeIPA CA installation into CSR/stop, offline signing, certificate import/
  primary completion, health checks and replica deployment. Use upstream role interfaces.
- [ ] Live-test the explicitly configured `ipareplica_setup_ca: true`; verify CA functionality on both servers,
  not just LDAP replication or two running VMs.
- [ ] Preserve existing domains and signing identities. Existing-CA rechaining/renewal requires
  a separate migration, backups, client compatibility tests and rollback, never refresh-time conversion.

## 4. Enrollment and operational acceptance

- [ ] If internal automated enrollment is selected, qualify acme2certifier against authenticated
  OpenXPKI RPC: tier-scoped identities,
  restrictive default/allowed leaf profiles, name/SAN authorization and denied CA requests.
- [ ] For that internal adapter, correlate accounts/orders to backend workflows; test renewal, retries, timeout,
  cross-tier rejection and restoration of bridge state. EAB alone is insufficient authorization.
- [ ] Publish stable CA/CRL objects without exposing administration; test freshness, revocation
  at enforcing clients and required mirror availability. Select/test OCSP separately if needed.
- [ ] Test provider/device loss, same-identity recovery and CRL signing; more devices do not
  establish application HA. Add database/workflow/session failover only for a supported requirement.
- [ ] Restore onto replacement hardware with later tiers, cluster, normal SSO and Vault absent;
  retain issuance history, revocation, DataVault readability, audit continuity and measured RPO/RTO.
- [ ] Update the support map only for implemented coverage; preserve private live evidence
  separately from this public design checklist and generated reference documentation.
