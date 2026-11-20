# Modeled requirements and use cases

Generated from the accepted model sources. Links identify specification coverage, not executed results.

[Working workflow](../../../docs/04-development/model-change-workflow.md) · [Verification evidence](../../../docs/01-architecture/07-software-intake/verification.md)

## Contents

- [REQ-custody](#req-custody)
- [REQ-egress](#req-egress)
- [REQ-integrity](#req-integrity)
- [REQ-policy](#req-policy)
- [UC-clone](#uc-clone)
- [UC-update](#uc-update)

<a id="req-custody"></a>
## REQ-custody — independentRecovery

Losing rebuildable cache data must not erase the independently retained recovery supply.

Verification cases: VC-custody

<a id="req-egress"></a>
## REQ-egress — noBypass

Independently enforce the accepted network egress policy. Proxy configuration alone cannot deny bypass.

Verification cases: VC-egress

<a id="req-integrity"></a>
## REQ-integrity — consumerVerification

Preserve source TLS through CONNECT and consumer verification. Cache presence is not approval.

Verification cases: VC-http-cache-untrusted, VC-http-untrusted, VC-integrity

<a id="req-policy"></a>
## REQ-policy — admittedSources

Remote access requires the accepted client, destination and port policy; otherwise deny.

Verification cases: VC-http-denied, VC-http-hit, VC-http-miss, VC-http-source-failure, VC-https, VC-https-denied

<a id="uc-clone"></a>
## UC-clone — Clone a Git repository over HTTPS

Subject: BOOT-host.
Actors: ACT-operator, ACT-intake.
Required obligations: None recorded.
Scenarios: None recorded; scenario detail is pending.

<a id="uc-update"></a>
## UC-update — Retrieve and verify software

Subject: L-Proxy.
Actors: ACT-client, ACT-source.
Required obligations: REQ-policy.
Scenarios: SC-http-cache-untrusted, SC-http-denied, SC-http-hit, SC-http-miss, SC-http-source-failure, SC-http-untrusted, SC-https, SC-https-denied.
