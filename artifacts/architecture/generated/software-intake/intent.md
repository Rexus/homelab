# Modeled requirements and use cases

Generated from the accepted model sources. Links identify specification coverage, not executed results.

[Working workflow](../../../../docs/04-development/model-change-workflow.md) Â· [Verification evidence](../../../../docs/01-architecture/07-software-intake/verification.md)

## Contents

- [REQ-custody](#req-custody)
- [REQ-egress](#req-egress)
- [REQ-integrity](#req-integrity)
- [REQ-policy](#req-policy)
- [UC-clone](#uc-clone)
- [UC-update](#uc-update)

<a id="req-custody"></a>
## REQ-custody â€” independentRecovery

The disposable cache shall keep the effects of losing its rebuildable data isolated from the independently retained recovery supply.

Verification cases: VC-custody

<a id="req-egress"></a>
## REQ-egress â€” noBypass

The update client shall be unable to retrieve external software through a path that bypasses the independently enforced egress policy.

Verification cases: VC-egress

<a id="req-integrity"></a>
## REQ-integrity â€” consumerVerification

The update client shall accept retrieved software for use only after the applicable source and publisher authenticity checks succeed, retaining end-to-end source TLS through CONNECT for HTTPS.

Verification cases: VC-http-cache-untrusted, VC-http-untrusted, VC-integrity

<a id="req-policy"></a>
## REQ-policy â€” admittedSources

The policy proxy shall deny external retrieval requests that fail the accepted client, destination or port policy.

Verification cases: VC-http-denied, VC-http-hit, VC-http-miss, VC-http-source-failure, VC-https, VC-https-denied

<a id="uc-clone"></a>
## UC-clone â€” Clone a Git repository over HTTPS

Subject: BOOT-host.
Actors: ACT-operator, ACT-intake.
Required obligations: None recorded.
Scenarios: None recorded; scenario detail is pending.

<a id="uc-update"></a>
## UC-update â€” Retrieve and verify software

Subject: L-Proxy.
Actors: ACT-client, ACT-source.
Required obligations: REQ-policy.
Scenarios: SC-http-cache-untrusted, SC-http-denied, SC-http-hit, SC-http-miss, SC-http-source-failure, SC-http-untrusted, SC-https, SC-https-denied.
