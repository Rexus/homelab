# PKI and public-edge security controls

PKI authenticates identities and protects transport; it does not detect every
intrusion, stop botnets or repair a compromised endpoint. Defend against behavior
and exposure, not an attacker's claimed nationality. No configuration guarantees
that man-in-the-middle attacks are impossible.

**Prerequisites:** [private PKI](../../deployment/stage-3-trust/procedures/software-pki.md),
[public HTTPS](../../deployment/stage-9-workloads/public-https.md), accepted
[protected logging](../security-logging.md) and named incident responders.

## Contents

- [Prevent and contain](#prevent-and-contain)
- [Detect and respond](#detect-and-respond)
- [Production gate](#production-gate)
- [References](#references)

## Prevent and contain

| Boundary | Required control |
| --- | --- |
| Public client to edge | Trusted public chain, hostname checks, modern TLS, HSTS; no certificate-warning bypass |
| Edge to origin | Private CA validation and exact hostname; restricted origin network paths |
| Administrative access | Private management path, MFA at access boundary, named least-privilege operators and independent recovery |
| CA authority | Offline root, distinct requester/approver, restricted names/profiles, audited signing and key access |
| Public DNS/registrar | MFA, protected recovery contacts, scoped API credentials and reviewed CAA |
| Workloads | Patch OS/proxy/application, authorization, secure sessions, input validation and least privilege |
| Volumetric attacks | Upstream ISP/CDN/DDoS arrangement; local request limits cannot protect a saturated link |
| Trust stores | Deliberate root installation and inventory; reject unknown/expired/revoked identities where the client enforces it |

TLS 1.3 is preferred; keep TLS 1.2 only for justified compatibility using ECDHE/AEAD.
Do not enable obsolete/static RSA key exchange or weaken verification to fix a
failed integration. PQC changes need a separate
[end-to-end qualification](../../architecture/cryptography/post-quantum.md). [1]

## Detect and respond

The following is the project's acceptance policy, not a claim that a SIEM, IDS,
WAF or notification service is installed by the certificate roles. Centralize
high-value events, preserve independent evidence and test detection with benign
injected events. Logging without reviewed alerts and responders is insufficient. [2]

| Signal | Collection and required response |
| --- | --- |
| CA authentication/privilege changes | Forward native audit/workflow/auth logs; alert on repeated failures and unexpected role/config/token changes |
| Issuance anomaly | Correlate requester, approver, SANs, profile and serial; alert on unusual volume, scope or custodian CLI use |
| Native audit coverage | Forward /var/log/openxpki-server/audit.log and workflows.log plus OS/service logs to accepted Tier 0 intake |
| Public proxy/application | Forward HAProxy, nginx, app, firewall and administrator events; investigate spikes, 4xx/5xx and origin verification failures |
| Lost evidence | Alert on missing source heartbeat, queue/disk exhaustion, clock skew or stopped forwarding |
| Renewal failure | Monitor systemd failure/missed success independently; alert before externally observed certificate expiry |
| CRL failure | Fetch and verify issuer/root CRLs independently; alert before nextUpdate, not merely when a timer stops |
| Domain/public issuance | Monitor DNS/CAA changes and Certificate Transparency for unexpected certificates; CT detects issuance, not all active interception |
| Host compromise | Monitor endpoint/network behavior and privileged access; isolate, preserve evidence and use incident revocation/reissuance |

Bootstrap local password authentication is independent of FreeIPA/SSO but is not
application MFA. Restrict the portal to an MFA-protected management boundary.
Protect logs against secrets and unnecessary personal data; do not log private
keys, passwords, session tokens or complete sensitive HTTP payloads.

## Production gate

| Exercise | Pass condition |
| --- | --- |
| Wrong CA/SAN and expired cert | Both public/client and origin checks fail closed; no bypass fallback |
| Forbidden request/self-approval | Denied with attributable audit event |
| Revocation | Updated signed CRL and an enforcing client reject a revoked serial |
| Alert outage | Test notification reaches a responder without CA portal, SSO or Tier 1 |
| Recovery | Same signing identity and current history restored on an isolated replacement |
| Public load/abuse | Rate-limit tuning, origin isolation and upstream mitigation tested |
| Loss of controller/provider | Existing valid service survives within its budget; timely alerts and documented recovery |

Check actual browser/client revocation behavior; publishing a CRL does not mean
all consumers consult it. Public certificate status is the public CA's service,
not the private issuer's CRL or an unimplemented OCSP endpoint.

## References

Sources checked 2026-10-18.

1. [IETF TLS recommendations and updates](https://www.rfc-editor.org/info/rfc9325/)
2. [Joint ASD/ACSC, CISA, FBI, NSA and partner logging/detection guidance](https://www.cyber.gov.au/publication/best-practices-for-event-logging-and-threat-detection)
3. [Let's Encrypt HTTP-01 behavior](https://letsencrypt.org/docs/challenge-types/)
