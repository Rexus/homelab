# Software intake scenarios

Generated from the owning use case, native branch selections and test plan.
These are expected paths through the model, not simulated or observed executions.

[Use-case view](../../../../architecture/generated/software-intake/SoftwareIntakeUseCases.svg) Â· [Functions](functions.md) Â· [Test and evidence](../../evidence/software-intake/README.md)

## Contents

- [Retrieve or revalidate HTTP content](#sc-http-miss)
- [Reuse a fresh HTTP response](#sc-http-hit)
- [Reject a disallowed HTTP request](#sc-http-denied)
- [Stop when the source is unavailable](#sc-http-source-failure)
- [Reject untrusted source content](#sc-http-untrusted)
- [Reject untrusted cached content](#sc-http-cache-untrusted)
- [Retrieve through source TLS](#sc-https)
- [Reject a disallowed CONNECT request](#sc-https-denied)

<a id="sc-http-miss"></a>
## SC-http-miss

**Retrieve or revalidate HTTP content**

**Trigger:** An update client requests HTTP repository content.

**Preconditions:** The route and trust policy are configured; content is absent or needs revalidation.

**Outcome:** Receive an allowed response, then verify trusted metadata and signatures locally. Verification failure stops use; it never approves an artifact.

Behavior: `B-HTTP`. Functions: `F-admit`, `F-cache`, `F-http`, `F-verify`.

| Step | Expected interaction | Function | Logical owner |
| --- | --- | --- | --- |
| 1 Â· `H-request` | HTTP repository request | `F-admit` | Policy proxy / HTTP cache |
| 2 Â· `H-check` | Check client, destination and port | `F-admit` | Policy proxy / HTTP cache |
| 3 Â· `H-lookup` | Look up eligible fresh content | `F-cache` | Rebuildable cache storage, Policy proxy / HTTP cache |
| 4 Â· `H-fetch` | Fetch or conditionally revalidate | `F-http` | Policy proxy / HTTP cache |
| 5 Â· `H-origin` | Content or freshness response | `F-http` | Policy proxy / HTTP cache |
| 6 Â· `H-cache-rules` | Apply cache and privacy rules | `F-cache` | Rebuildable cache storage, Policy proxy / HTTP cache |
| 7 Â· `H-response` | Return response | `F-http` | Policy proxy / HTTP cache |
| 8 Â· `H-verify` | Verify trusted metadata / signatures | `F-verify` | Update Consumers |
| 9 Â· `H-accepted` | Accept verified content for use | `F-verify` | Update Consumers |

**Acceptance:** Both variants contact the source. Received content follows the configured cache/privacy policy and passes client verification before use; unsigned or expired metadata is rejected unless explicitly excepted.

**Implementation:** [baseline/tasks/package_policy.yml](../../../../shared/ansible/roles/baseline/tasks/package_policy.yml); [baseline/templates/apt-package-policy.conf.j2](../../../../shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2); [cache_proxy/defaults/main.yml](../../../../tier-2/ansible/roles/cache_proxy/defaults/main.yml); [cache_proxy/templates/squid.conf.j2](../../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2)

**Linked checks:** [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_generated_policy`; [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_source_policy`; [tests/test_tier_intake_execution.py](../../../../tests/test_tier_intake_execution.py) `IntakeExecutionContracts.test_observed_failure_and_verification_paths`; [tests/test_tier_intake_product.py](../../../../tests/test_tier_intake_product.py) `NativeIntakeScenarios.test_signed_package_retrieval_matches_model`; [tests/test_tier_package_policy.py](../../../../tests/test_tier_package_policy.py) `PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception`


<a id="sc-http-hit"></a>
## SC-http-hit

**Reuse a fresh HTTP response**

**Trigger:** An update client repeats an eligible HTTP request.

**Preconditions:** Policy admits the request and an eligible fresh cached response exists.

**Outcome:** Receive cached content without an origin fetch, then perform the same local verification as a miss.

Behavior: `B-HTTP`. Functions: `F-admit`, `F-cache`, `F-verify`.

| Step | Expected interaction | Function | Logical owner |
| --- | --- | --- | --- |
| 1 Â· `H-request` | HTTP repository request | `F-admit` | Policy proxy / HTTP cache |
| 2 Â· `H-check` | Check client, destination and port | `F-admit` | Policy proxy / HTTP cache |
| 3 Â· `H-lookup` | Look up eligible fresh content | `F-cache` | Rebuildable cache storage, Policy proxy / HTTP cache |
| 4 Â· `H-cached` | Return cached response | `F-cache` | Rebuildable cache storage, Policy proxy / HTTP cache |
| 5 Â· `H-verify` | Verify trusted metadata / signatures | `F-verify` | Update Consumers |
| 6 Â· `H-accepted` | Accept verified content for use | `F-verify` | Update Consumers |

**Acceptance:** No additional source request occurs. The client verifies the returned content before accepting it.

**Implementation:** [baseline/tasks/package_policy.yml](../../../../shared/ansible/roles/baseline/tasks/package_policy.yml); [baseline/templates/apt-package-policy.conf.j2](../../../../shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2); [cache_proxy/defaults/main.yml](../../../../tier-2/ansible/roles/cache_proxy/defaults/main.yml); [cache_proxy/templates/squid.conf.j2](../../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2)

**Linked checks:** [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_generated_policy`; [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_source_policy`; [tests/test_tier_intake_execution.py](../../../../tests/test_tier_intake_execution.py) `IntakeExecutionContracts.test_observed_failure_and_verification_paths`; [tests/test_tier_intake_product.py](../../../../tests/test_tier_intake_product.py) `NativeIntakeScenarios.test_signed_package_retrieval_matches_model`; [tests/test_tier_package_policy.py](../../../../tests/test_tier_package_policy.py) `PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception`


<a id="sc-http-denied"></a>
## SC-http-denied

**Reject a disallowed HTTP request**

**Trigger:** A client requests a disallowed HTTP destination, port or route.

**Preconditions:** At least one admission condition fails.

**Outcome:** Receive denial without a cache lookup or source fetch.

Behavior: `B-HTTP`. Functions: `F-admit`.

| Step | Expected interaction | Function | Logical owner |
| --- | --- | --- | --- |
| 1 Â· `H-request` | HTTP repository request | `F-admit` | Policy proxy / HTTP cache |
| 2 Â· `H-check` | Check client, destination and port | `F-admit` | Policy proxy / HTTP cache |
| 3 Â· `H-denied` | Deny without a cache lookup or source fetch | `F-admit` | Policy proxy / HTTP cache |

**Acceptance:** Each request is denied. The source records zero requests; cached content is not returned.

**Implementation:** [cache_proxy/defaults/main.yml](../../../../tier-2/ansible/roles/cache_proxy/defaults/main.yml); [cache_proxy/templates/squid.conf.j2](../../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2)

**Linked checks:** [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_generated_policy`; [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_source_policy`; [tests/test_tier_intake_product.py](../../../../tests/test_tier_intake_product.py) `NativeIntakeScenarios.test_signed_package_retrieval_matches_model`


<a id="sc-http-source-failure"></a>
## SC-http-source-failure

**Stop when the source is unavailable**

**Trigger:** An update client requests HTTP repository content.

**Preconditions:** An admitted request has no eligible fresh response and its source attempt fails.

**Outcome:** Return a retrieval error and stop without content verification.

Behavior: `B-HTTP`. Functions: `F-admit`, `F-cache`, `F-http`, `F-verify`.

| Step | Expected interaction | Function | Logical owner |
| --- | --- | --- | --- |
| 1 Â· `H-request` | HTTP repository request | `F-admit` | Policy proxy / HTTP cache |
| 2 Â· `H-check` | Check client, destination and port | `F-admit` | Policy proxy / HTTP cache |
| 3 Â· `H-lookup` | Look up eligible fresh content | `F-cache` | Rebuildable cache storage, Policy proxy / HTTP cache |
| 4 Â· `H-fetch` | Fetch or conditionally revalidate | `F-http` | Policy proxy / HTTP cache |
| 5 Â· `H-source-failure` | Observe source failure | `F-http` | Policy proxy / HTTP cache |
| 6 Â· `H-unavailable` | Return retrieval error without content | `F-http` | Policy proxy / HTTP cache |
| 7 Â· `H-stop` | Stop retrieval without verifying content | `F-verify` | Update Consumers |

**Acceptance:** Retrieval reports failure, delivers no usable content, performs zero content-verification checks and does not serve a stale fallback.

**Implementation:** [software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml](../../../../architecture/models/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml); [cache_proxy/defaults/main.yml](../../../../tier-2/ansible/roles/cache_proxy/defaults/main.yml); [cache_proxy/templates/squid.conf.j2](../../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2)

**Linked checks:** [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_generated_policy`; [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_source_policy`; [tests/test_tier_intake_execution.py](../../../../tests/test_tier_intake_execution.py) `IntakeExecutionContracts.test_observed_failure_and_verification_paths`; [tests/test_tier_intake_product.py](../../../../tests/test_tier_intake_product.py) `NativeIntakeScenarios.test_signed_package_retrieval_matches_model`


<a id="sc-http-untrusted"></a>
## SC-http-untrusted

**Reject untrusted source content**

**Trigger:** An update client requests HTTP repository content.

**Preconditions:** An admitted source retrieval completes but publisher verification fails.

**Outcome:** Reject received content before use.

Behavior: `B-HTTP`. Functions: `F-admit`, `F-cache`, `F-http`, `F-verify`.

| Step | Expected interaction | Function | Logical owner |
| --- | --- | --- | --- |
| 1 Â· `H-request` | HTTP repository request | `F-admit` | Policy proxy / HTTP cache |
| 2 Â· `H-check` | Check client, destination and port | `F-admit` | Policy proxy / HTTP cache |
| 3 Â· `H-lookup` | Look up eligible fresh content | `F-cache` | Rebuildable cache storage, Policy proxy / HTTP cache |
| 4 Â· `H-fetch` | Fetch or conditionally revalidate | `F-http` | Policy proxy / HTTP cache |
| 5 Â· `H-origin` | Content or freshness response | `F-http` | Policy proxy / HTTP cache |
| 6 Â· `H-cache-rules` | Apply cache and privacy rules | `F-cache` | Rebuildable cache storage, Policy proxy / HTTP cache |
| 7 Â· `H-response` | Return response | `F-http` | Policy proxy / HTTP cache |
| 8 Â· `H-verify` | Verify trusted metadata / signatures | `F-verify` | Update Consumers |
| 9 Â· `H-rejected` | Reject content; stop before use | `F-verify` | Update Consumers |

**Acceptance:** The client rejects the content before use; retrieval alone does not count as verification.

**Implementation:** [baseline/tasks/package_policy.yml](../../../../shared/ansible/roles/baseline/tasks/package_policy.yml); [baseline/templates/apt-package-policy.conf.j2](../../../../shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2); [cache_proxy/defaults/main.yml](../../../../tier-2/ansible/roles/cache_proxy/defaults/main.yml); [cache_proxy/templates/squid.conf.j2](../../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2)

**Linked checks:** [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_generated_policy`; [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_source_policy`; [tests/test_tier_intake_execution.py](../../../../tests/test_tier_intake_execution.py) `IntakeExecutionContracts.test_observed_failure_and_verification_paths`; [tests/test_tier_intake_product.py](../../../../tests/test_tier_intake_product.py) `NativeIntakeScenarios.test_signed_package_retrieval_matches_model`; [tests/test_tier_package_policy.py](../../../../tests/test_tier_package_policy.py) `PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception`


<a id="sc-http-cache-untrusted"></a>
## SC-http-cache-untrusted

**Reject untrusted cached content**

**Trigger:** An update client requests HTTP repository content.

**Preconditions:** A fresh eligible cached response is returned but publisher verification fails.

**Outcome:** Reject cached content before use; a cache hit does not imply trust.

Behavior: `B-HTTP`. Functions: `F-admit`, `F-cache`, `F-verify`.

| Step | Expected interaction | Function | Logical owner |
| --- | --- | --- | --- |
| 1 Â· `H-request` | HTTP repository request | `F-admit` | Policy proxy / HTTP cache |
| 2 Â· `H-check` | Check client, destination and port | `F-admit` | Policy proxy / HTTP cache |
| 3 Â· `H-lookup` | Look up eligible fresh content | `F-cache` | Rebuildable cache storage, Policy proxy / HTTP cache |
| 4 Â· `H-cached` | Return cached response | `F-cache` | Rebuildable cache storage, Policy proxy / HTTP cache |
| 5 Â· `H-verify` | Verify trusted metadata / signatures | `F-verify` | Update Consumers |
| 6 Â· `H-rejected` | Reject content; stop before use | `F-verify` | Update Consumers |

**Acceptance:** The client rejects the content before use and the source records zero new requests.

**Implementation:** [baseline/tasks/package_policy.yml](../../../../shared/ansible/roles/baseline/tasks/package_policy.yml); [baseline/templates/apt-package-policy.conf.j2](../../../../shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2); [cache_proxy/defaults/main.yml](../../../../tier-2/ansible/roles/cache_proxy/defaults/main.yml); [cache_proxy/templates/squid.conf.j2](../../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2)

**Linked checks:** [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_generated_policy`; [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_source_policy`; [tests/test_tier_intake_execution.py](../../../../tests/test_tier_intake_execution.py) `IntakeExecutionContracts.test_observed_failure_and_verification_paths`; [tests/test_tier_intake_product.py](../../../../tests/test_tier_intake_product.py) `NativeIntakeScenarios.test_signed_package_retrieval_matches_model`; [tests/test_tier_package_policy.py](../../../../tests/test_tier_package_policy.py) `PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception`


<a id="sc-https"></a>
## SC-https

**Retrieve through source TLS**

**Trigger:** An update client requests an HTTPS repository through CONNECT.

**Preconditions:** Admission succeeds; TCP and source-authenticated TLS can be established.

**Outcome:** Receive content through the tunnel and verify it at the client. No TLS interception, payload caching or scanning. Transport or verification failure stops retrieval; detailed transport error exchanges are outside this sequence.

Behavior: `B-HTTPS`. Functions: `F-admit`, `F-tunnel`, `F-verify`.

| Step | Expected interaction | Function | Logical owner |
| --- | --- | --- | --- |
| 1 Â· `S-connect` | CONNECT source:443 | `F-admit` | Policy proxy / HTTP cache |
| 2 Â· `S-check` | Check client, destination and port | `F-admit` | Policy proxy / HTTP cache |
| 3 Â· `S-open` | Open permitted TCP connection | `F-tunnel` | Policy proxy / HTTP cache |
| 4 Â· `S-established` | Connection established | `F-tunnel` | Policy proxy / HTTP cache |
| 5 Â· `S-ready` | 200 Connection Established | `F-tunnel` | Policy proxy / HTTP cache |
| 6 Â· `S-fetch` | Fetch through client-to-source TLS | `F-tunnel` | Policy proxy / HTTP cache |
| 7 Â· `S-response` | Encrypted response through the tunnel | `F-tunnel` | Policy proxy / HTTP cache |
| 8 Â· `S-verify` | Verify trusted metadata / signatures; stop on failure | `F-verify` | Update Consumers |

**Acceptance:** Client TLS authenticates the source certificate and hostname end to end. The proxy neither inspects nor caches decrypted payload; client content verification succeeds before use.

**Implementation:** [baseline/tasks/package_policy.yml](../../../../shared/ansible/roles/baseline/tasks/package_policy.yml); [baseline/templates/apt-package-policy.conf.j2](../../../../shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2); [playbooks/deployment/outbound-cache.yml](../../../../tier-2/ansible/playbooks/deployment/outbound-cache.yml); [cache_proxy/defaults/main.yml](../../../../tier-2/ansible/roles/cache_proxy/defaults/main.yml); [cache_proxy/templates/squid.conf.j2](../../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2)

**Linked checks:** [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_generated_policy`; [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_source_policy`; [tests/test_tier_package_policy.py](../../../../tests/test_tier_package_policy.py) `PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception`

**Additional manual acceptance:** Run the Stage 1 accepted-source HTTPS retrieval on the deployed route; verify source certificate/hostname, payload integrity and refusal of invalid trust. The isolated HTTP fixture does not forward CONNECT.


<a id="sc-https-denied"></a>
## SC-https-denied

**Reject a disallowed CONNECT request**

**Trigger:** A client attempts a disallowed CONNECT request.

**Preconditions:** At least one admission condition fails.

**Outcome:** Receive denial without a connection to the source.

Behavior: `B-HTTPS`. Functions: `F-admit`.

| Step | Expected interaction | Function | Logical owner |
| --- | --- | --- | --- |
| 1 Â· `S-connect` | CONNECT source:443 | `F-admit` | Policy proxy / HTTP cache |
| 2 Â· `S-check` | Check client, destination and port | `F-admit` | Policy proxy / HTTP cache |
| 3 Â· `S-denied` | Deny without a source connection | `F-admit` | Policy proxy / HTTP cache |

**Acceptance:** CONNECT is denied and the source records zero connections.

**Implementation:** [cache_proxy/defaults/main.yml](../../../../tier-2/ansible/roles/cache_proxy/defaults/main.yml); [cache_proxy/templates/squid.conf.j2](../../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2)

**Linked checks:** [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_generated_policy`; [tests/test_tier_cache_policy.py](../../../../tests/test_tier_cache_policy.py) `NativeCachePolicy.test_source_policy`

All named checks must be run in their declared environment. Links do not mean a test passed.
The test/evidence entry records actual executions and remaining site acceptance.
