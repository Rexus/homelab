# PKI security checks and incident actions

<a id="pki-and-public-edge-security-controls"></a>


Verify the selected private PKI and public-edge controls, preserve evidence and
record who responds. The certificate roles do not install a SIEM, IDS, WAF or
external alerting service. Use the [trust design](../../01-architecture/16-cryptography/README.md)
and [network policy](../../01-architecture/11-networking/01-firewall-policy.md) for the rationale.

**Run from:** an authorized client for TLS tests, the issuer for local test events,
and the owning Tier 0/Tier 2 repository for its existing inputs.
**Before starting:** accepted PKI/logging, independently retained recovery access,
public HTTPS only when selected, and named incident responders.

<a id="contents"></a>

## Tasks

- [How are trust and access checked before a change?](#prevent-and-contain)
- [How are evidence delivery and alerts checked?](#how-are-evidence-delivery-and-alerts-checked)
- [What happens after a suspected compromise?](#detect-and-respond)
- [What evidence is required before returning to service?](#production-gate)
- [References](#references)

<a id="prevent-and-contain"></a>

## How are trust and access checked before a change?

1. Confirm the actual 06-paths/owners before editing configuration:

   | Owner / file | Verify |
   | --- | --- |
   | Tier 0 `ansible/group_vars/issuer.yml` | Existing portal/publication networks, issuer identity and immutable runtime binding |
   | Tier 0 `ansible/group_vars/logging_producers.yml` and per-host overrides | CA journal/audit stream identities, real file paths and independent watchdogs |
   | Tier 2 `ansible/group_vars/public-https.yml`, when selected | Exact public domains, ACME state custody and verified origin CA/hostname |
   | Private access/registrar records | MFA boundary, named operators, scoped DNS credentials and independent recovery contacts |

2. From an approved client, test the actual HTTPS listener without verification bypass:

   Run on **an approved HTTPS client**.

   ```bash
   read -r -p 'Approved HTTPS service URL: ' SERVICE_URL
   curl --proto '=https' --head --show-error "$SERVICE_URL"
   ```

   A deliberate HTTP 401/403 can be correct; this is a connection/trust check,
   not application authorization acceptance. Never add `--insecure` to make it pass.
3. Use [CA renewal/publication checks](certificate-authority.md) for the private issuer
   and the [public HTTPS acceptance](../../03-deployment/stage-10-lab-environments/step-3b-public-https.md#accept-and-operate)
   for edge/origin chains. Test wrong CA/SAN, expiry and denied-origin paths with
   disposable material, never by replacing live trust with an unverified root.

Keep the accepted TLS policy and client compatibility; do not enable obsolete/static
RSA exchange or weaken checks to repair an integration. Protocol/PQC changes require
[algorithm qualification](../../01-architecture/16-cryptography/02-algorithm-selection.md). [1]

## How are evidence delivery and alerts checked?

1. On the issuer, emit a harmless OS marker:

   Run on **the existing issuer host**.

   ```bash
   logger -t pki-acceptance 'pki-security-check-001'
   ```

2. Find that marker at the protected Tier 0 receiver under the enrolled host identity.
   Then exercise a benign actual portal request/denial and confirm its native audit
   records. The OS marker does **not** verify the product audit-file stream.
3. Confirm the enrolled native files include actual
   `/var/log/openxpki-server/audit.log` and `workflows.log`, plus OS/service events.
   Follow [source forwarding](../../03-deployment/stage-2-logging/procedures/sources.md) for explicit
   file streams; submitted labels cannot authorize access to another evidence scope.
4. Trigger the independent test notification and a controlled missed-heartbeat test.
   Confirm a responder receives it with portal, normal SSO and Tier 1 unavailable.
   Restore the test condition, record delivery time and verify health recovers. [2]

| Signal | Required operating response |
| --- | --- |
| Unexpected CA auth/role/config/token change | Correlate identity, approval and time; investigate privileged CLI use |
| Issuance volume/name/profile anomaly | Correlate requester, approver, SANs, profile and serial; reject unapproved scope |
| Missing events, queue/disk pressure or skew | Investigate source/forwarder/checkpoint health; preserve backlog and original records |
| Renewal/CRL failure | Alert before observed certificate expiry or CRL nextUpdate, not merely on stopped timers |
| Edge/origin verification errors or abuse | Correlate proxy/app/firewall events; retain raw evidence and apply the approved response |
| DNS/CAA or unexpected public issuance | Review registrar audit and Certificate Transparency; CT is not proof of every interception attempt |

Keep private keys, passwords, session tokens and sensitive payloads out of test
markers and exported diagnostics. Authentication/audit records themselves need restricted reads.

<a id="detect-and-respond"></a>

## What happens after a suspected compromise?

1. Stop routine changes. Use independent privileged access, isolate affected
   endpoints through the accepted network response and preserve Tier 0 evidence.
   Do not delete queues, restore an old snapshot or initialize replacement trust.
2. Identify the exposed authority: service leaf, account/token, issuer/provider,
   offline root or recovery key. Involve its custodian; their revocation scopes differ.
3. Revoke and reissue through the [CA operation](certificate-authority.md#how-is-a-certificate-revoked-and-its-crl-published)
   or the credential issuer's native procedure. Issuer/root compromise requires a
   separately approved trust rollover; moving the same suspect key into hardware is not recovery.
4. Recover on clean targets from the latest qualified state, verify denial of exposed
   credentials and protect new credentials before readmitting traffic.

**Stop/rollback:** never roll back to a known exposed or revoked credential. Retain
current issuance/revocation history and only one CA writer. Missing recovery proof
keeps the affected service isolated; a successful redeploy does not close the incident.

<a id="production-gate"></a>

## What evidence is required before returning to service?

| Exercise | Required result |
| --- | --- |
| Wrong CA/SAN, expiry, revocation | Selected enforcing clients reject the invalid identity; no bypass fallback |
| Forbidden request/self-approval | Denied with attributable audit event and independent review |
| Administrative boundary | Named least-privilege access, MFA at the management boundary and separate recovery; bootstrap passwords alone are not application MFA |
| Evidence/alert outage | Expected source events and external notifications survive loss of portal, SSO and Tier 1 |
| Independent recovery | Same accepted signing identity and latest history restored; separate key/controller custody works |
| Public exposure, when selected | Origin isolation, scoped DNS/CAA control, patched services, measured request limits and the selected upstream volumetric-mitigation arrangement |
| Provider/controller loss | Recorded failure budget, alerts and tested restoration; neither replica count nor TLS alone proves availability |

Retain results in private project records. A CRL must be enforced by the actual
client; public certificate status belongs to the public CA, not the private issuer.
Local rate limits do not protect a saturated upstream link. No extra protection
service is implied by this checklist.

## References

Interfaces and guidance checked 2026-11-08.

1. [IETF TLS recommendations and subsequent updates](https://www.rfc-editor.org/info/rfc9325/).
2. [Joint event logging and detection guidance](https://www.cyber.gov.au/publication/best-practices-for-event-logging-and-threat-detection).
