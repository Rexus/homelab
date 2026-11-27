# Requirement assessment

Gate: **passed** in **isolated** scope.

A scoped pass does not establish deployed acceptance. Missing site evidence remains below.

| Requirement | Overall | By scope |
| --- | --- | --- |
| REQ-custody — independentRecovery | missing | site: missing |
| REQ-egress — noBypass | missing | site: missing |
| REQ-integrity — consumerVerification | missing | isolated: passed; site: missing |
| REQ-policy — admittedSources | missing | isolated: passed; site: missing |

| Requirement / case | Scope | Result | Claim / evidence checks |
| --- | --- | --- | --- |
| REQ-custody / VC-custody | site | missing | Recovery from independently retained supply after disposable cache removal.;  |
| REQ-egress / VC-egress | site | missing | Independent deployed network enforcement refuses direct bypass.;  |
| REQ-integrity / VC-http-cache-untrusted | isolated | passed | Real Squid/APT outcome matches the native retrieval experiment. Loopback only.; signed-retrieval |
| REQ-integrity / VC-http-untrusted | isolated | passed | Real Squid/APT outcome matches the native retrieval experiment. Loopback only.; signed-retrieval |
| REQ-integrity / VC-integrity | isolated | passed | APT signed metadata and package hashes, unknown publisher, expiry and trusted-source exception.; signed-retrieval, publisher-policy |
| REQ-integrity / VC-integrity | site | missing | Source TLS/hostname and selected client trust configuration on the deployed route.;  |
| REQ-policy / VC-http-denied | isolated | passed | Actual Squid policy/cache/privacy assertions; APT publisher checks where selected. Loopback only.; policy-source, policy-generated, signed-retrieval |
| REQ-policy / VC-http-hit | isolated | passed | Actual Squid policy/cache/privacy assertions; APT publisher checks where selected. Loopback only.; policy-source, policy-generated, signed-retrieval |
| REQ-policy / VC-http-miss | isolated | passed | Actual Squid policy/cache/privacy assertions; APT publisher checks where selected. Loopback only.; policy-source, policy-generated, signed-retrieval, publisher-policy |
| REQ-policy / VC-http-source-failure | isolated | passed | Real Squid/APT outcome matches the native retrieval experiment. Loopback only.; signed-retrieval |
| REQ-policy / VC-https | site | missing | Admitted end-to-end TLS, certificate/hostname validation and no encrypted-payload caching.;  |
| REQ-policy / VC-https-denied | isolated | passed | Actual Squid policy/cache/privacy assertions; APT publisher checks where selected. Loopback only.; policy-source, policy-generated |

## Executed checks

- policy-source: **passed**; attempt `20261120T082324465570Z-cba236d3`; unittest assertions and fixtures completed
- policy-generated: **passed**; attempt `20261120T082324465570Z-cba236d3`; unittest assertions and fixtures completed
- signed-retrieval: **passed**; attempt `20261120T082324465570Z-cba236d3`; unittest assertions and fixtures completed
- publisher-policy: **passed**; attempt `20261120T082324465570Z-cba236d3`; unittest assertions and fixtures completed
