# Certificate authority operations

Maintain the infrastructure issuer, offline root and identity CA as separate state
and authority boundaries. OpenXPKI is the reference infrastructure portal; it does not
replace FreeIPA's certificate administration or the secret service.

**Working repository:** `<prefix>-tier-0` (source: `tier-0/`) owns project runbooks,
approved configuration and acceptance records, not private CA state in Git.
**Design:** [certificate authority](../../architecture/cryptography/certificate-authority.md).
**Prerequisites:** completed [issuer integration](../../deployment/stage-3-trust/procedures/issuer.md),
independent access, application-consistent backups and authorized custodians.
The supplied read-only maintenance recipe checks native services, configuration and
the local backend API. It does not perform issuance, backup, restore or upgrades.
Separate [software backup/restore recipes](issuer-recovery.md) require explicit
inputs and a clean-target recovery gate:

```bash
bash scripts/deploy.sh foundation --recipe maintenance --playbook maintenance/openxpki.yml --ansible-vars ansible/group_vars/issuer.yml
```

## Contents

- [Routine controls](#routine-controls)
- [Change and recovery](#change-and-recovery)
- [Acceptance evidence](#acceptance-evidence)
- [References](#references)

## Routine controls

Use the [PKI/public-edge security controls](security-controls.md) for prevention,
event coverage, independent alerts and production exercises. A CA is not an IDS.

| Area | Required check |
| --- | --- |
| Portal and approval | Distinct requester/operator/custodian roles; request/approval/renewal/revocation history; independently retained recovery access |
| Profiles and enrollment | Allowed identities, SAN/name scopes, key usages and validity; reject forbidden profiles, CA requests and cross-tier enrollment |
| Publication | CA certificates and fresh issuer/root CRLs available at stable URLs; alert before next-update expiry; verify actual client revocation behavior |
| Key access | Selected provider ready with the approved key identity/mechanisms; missing key is a fault, not permission to initialize another |
| State and capacity | Database, session/workflow consistency, protected DataVault material, disk growth and backup status |
| Audit | Issuance, administrative actions, failures and approved exports reach Tier 0 evidence with source identity; analytics copies cannot erase originals |
| Independent alerts | Expiry, stale CRLs, failed signing, provider loss and restore failures remain visible without the portal, SSO or Tier 1 |

The ACME adapter, when accepted, retains separate accounts/order state and restricted
backend credentials. Monitor order-to-workflow correlation and renewal failures without
granting it portal administration or broad issuing profiles.

## Change and recovery

1. Record the exact application/configuration/schema/provider combination and take a
   verified pre-change backup. Separate configuration convergence from schema migration,
   token activation, CA rollover and custody ceremonies. Missing state must stop the change.
   Routine deployment pins this combination in `deployment.json`; a different archive,
   package set or database/session secret is deliberately rejected. Preserve the binding
   and schema receipt with backups. Do not delete them to force an upgrade or restore.
2. Rehearse the change on an isolated restored copy. Preserve current issuance history,
   serial allocation and revocation state; an old VM/image snapshot is not a safe
   substitute for application-consistent recovery. Never run two restored copies of
   the same CA identity as independent writers.
3. Restore onto a replacement host with Tier 1/2, the control cluster, normal SSO and
   the secret service unavailable. Verify identity continuity before enabling issuance,
   then verify portal workflows, publication, revocation, audit forwarding and alerting.

| Recovery set | Custody requirement |
| --- | --- |
| OpenXPKI database, approved configuration, schema and artifacts | Restore as one tested application set, including workflow/session requirements |
| OpenXPKI DataVault secret or token material | Recover independently with the database; unrelated to HashiCorp Vault; loss can make protected content unreadable [1] |
| Issuer provider/key backup and authorization | Prove recovery of the same signing identity, attributes and allowed operations; devices alone are not interchangeable |
| Portal/bootstrap administration and TLS | Recover without FreeIPA/Keycloak; rotate/revoke exposed credentials after recovery |
| ACME bridge state and credentials, when selected | Preserve account/order continuity and backend authorization under the bridge procedure |
| Root CA instance and separate device/key recovery | Update after each ceremony; verify encryption and custody separately from the clca backup archive [2] |

Application HA requires database/workflow/session/key-access coordination. A second HSM
or VIP alone does not make the CA application highly available. Introduce replicas only
under a supported application/storage design with tested failure and recovery semantics.

## Acceptance evidence

| Test | Required result |
| --- | --- |
| Everyday portal | Submit/upload CSR, approve, inspect, renew and revoke using intended roles |
| Hostile enrollment | Reject unapproved SANs/names, cross-tier scope, forbidden profiles and subordinate CA requests |
| Automated enrollment, if selected | cert-manager issuance/renewal, backend audit correlation, denial, timeout and bridge-state restoration |
| Revocation | Fresh CRL contains the revoked serial and an enforcing client rejects it; OCSP tested separately if selected |
| Provider failure | Real selected software/HSM path signs certificates and CRLs; restart/device loss/recovery preserve identity |
| Independent restoration | Replacement host retains issuance/revocation history and DataVault readability without later-tier services |
| Upgrade and rollback | Compatible application/configuration/schema update succeeds; recovery does not regress current CA state |

Keep transcripts, fingerprints, backup IDs, denied requests and RPO/RTO observations in
the private project's administration records. A design decision, running package or
successful VM apply is not evidence that this contract has passed.

## References

Sources checked 2026-10-17.

1. [OpenXPKI configuration and DataVault protection](https://github.com/openxpki/openxpki-config/blob/community/QUICKSTART.md)
2. [clca lifecycle, backup and provider interfaces](https://github.com/openxpki/clca/blob/master/README.md)
