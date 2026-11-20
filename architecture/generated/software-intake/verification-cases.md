# Native verification cases

Generated from SysML verification definitions and their `verify` objectives.
These are test specifications. Executed outcomes and their scope live in the [evidence record](../../../docs/01-architecture/07-software-intake/verification.md).

[Engineering relationships](../../views/software-intake/engineering.svg) · [Authoring source](../../test/software-intake/verification.sysml)

<a id="vc-integrity"></a>
## VC-integrity

**Verify:** REQ-integrity. **Subject type:** DEF-client.

Client authenticates the source TLS endpoint and rejects untrusted publisher metadata before use; test the selected trust exceptions explicitly. Successful CONNECT/TLS still needs site evidence.

**Scenario trace:** Cross-scenario / site obligation.

<a id="vc-http-miss"></a>
## VC-http-miss

**Verify:** REQ-policy. **Subject type:** DEF-proxy.

An admitted miss or stale response reaches the source; cache/privacy rules are respected and the client verifies before use. Unsigned or expired metadata is rejected unless an explicit trusted-source exception was selected.

**Scenario trace:** SC-http-miss.

<a id="vc-http-cache-untrusted"></a>
## VC-http-cache-untrusted

**Verify:** REQ-integrity. **Subject type:** DEF-client.

Cached content is verified at the client and rejected when trust fails, without a source fetch. Model trust is an input, not a cryptographic check.

**Scenario trace:** SC-http-cache-untrusted.

<a id="vc-http-denied"></a>
## VC-http-denied

**Verify:** REQ-policy. **Subject type:** DEF-proxy.

A rejected client, destination or port receives denial and the recording source sees no request.

**Scenario trace:** SC-http-denied.

<a id="vc-custody"></a>
## VC-custody

**Verify:** REQ-custody. **Subject type:** DEF-cache.

Remove disposable cache data and demonstrate recovery from independently retained supply. This is a site recovery demonstration, not inferred from storage configuration.

**Scenario trace:** Cross-scenario / site obligation.

<a id="vc-http-untrusted"></a>
## VC-http-untrusted

**Verify:** REQ-integrity. **Subject type:** DEF-client.

When publisher verification fails after retrieval, the client rejects the content before use. Model trust is an input, not a cryptographic check.

**Scenario trace:** SC-http-untrusted.

<a id="vc-egress"></a>
## VC-egress

**Verify:** REQ-egress. **Subject type:** DEF-client.

Attempt direct external access bypassing the accepted route and show independent network enforcement rejects it. This requires the site network policy and deployed-route evidence.

**Scenario trace:** Cross-scenario / site obligation.

<a id="vc-http-source-failure"></a>
## VC-http-source-failure

**Verify:** REQ-policy. **Subject type:** DEF-proxy.

A source failure after an admitted miss produces no usable content, no client verification and no implicit stale fallback. The execution model supplies availability; deployed failure behavior needs separate evidence.

**Scenario trace:** SC-http-source-failure.

<a id="vc-https"></a>
## VC-https

**Verify:** REQ-policy. **Subject type:** DEF-proxy.

An admitted CONNECT establishes source-authenticated client TLS. Encrypted payload is neither cached nor inspected; client verification still applies.

**Scenario trace:** SC-https.

<a id="vc-https-denied"></a>
## VC-https-denied

**Verify:** REQ-policy. **Subject type:** DEF-proxy.

A disallowed CONNECT destination, client or port receives denial without opening a source connection.

**Scenario trace:** SC-https-denied.

<a id="vc-http-hit"></a>
## VC-http-hit

**Verify:** REQ-policy. **Subject type:** DEF-proxy.

A repeated eligible fresh response is served without another origin request. The client still verifies trusted metadata/signatures.

**Scenario trace:** SC-http-hit.
