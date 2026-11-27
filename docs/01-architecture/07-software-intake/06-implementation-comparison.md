# Compare the model with real software

<!-- BEGIN MODEL COMPARISON -->
No current implementation result. Retained results are historical; rerun the comparison.

| Experiment | Expected outcome | Observed outcome |
| --- | --- | --- |
| [Reject untrusted cached content](../../../architecture/generated/software-intake/SoftwareIntakeUseCases.svg#SC-http-cache-untrusted) | verification-failed | Not current |
| [Deny even when content is cached](../../../architecture/generated/software-intake/SoftwareIntakeUseCases.svg#SC-http-denied) | denied | Not current |
| [Reuse fresh content while source is offline](../../../architecture/generated/software-intake/SoftwareIntakeUseCases.svg#SC-http-hit) | accepted | Not current |
| [Retrieve from available source](../../../architecture/generated/software-intake/SoftwareIntakeUseCases.svg#SC-http-miss) | accepted | Not current |
| [Stop after source failure](../../../architecture/generated/software-intake/SoftwareIntakeUseCases.svg#SC-http-source-failure) | source-unavailable | Not current |
| [Reject untrusted source content](../../../architecture/generated/software-intake/SoftwareIntakeUseCases.svg#SC-http-untrusted) | verification-failed | Not current |
<!-- END MODEL COMPARISON -->

This comparison follows one concrete use of software intake: **download a package through the cache
and verify it before use**. Real Squid runs the project's proxy configuration. Real APT authenticates
repository metadata and checks the package against its trusted hash. Everything runs on local test
ports with temporary data; no package is installed and no host trust store is changed.

## Contents

- [Follow the same story](#follow-the-same-story)
- [What is measured](#what-is-measured)
- [Repeat the comparison](#repeat-the-comparison)
- [Interpret a difference](#interpret-a-difference)
- [Boundaries](#boundaries)
- [References](#references)

## Follow the same story

Start with the [plain-language walkthrough](03-http-walkthrough.md). The logical story is unchanged:
check request access, reuse fresh cached content or fetch it, then verify at the client.

| Logical responsibility | Software used in this test | Evidence |
| --- | --- | --- |
| Check request access | Squid, rendered from the [owned template](../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2) | A previously cached URL returns HTTP 403 after its destination is removed from the allow-list |
| Reuse fresh cached content | The same Squid process and its real cache | A cache hit and no request to the test source |
| Fetch content from source | Squid forwards to a recording source fixture | A cache miss, source request and source response/error |
| Verify before use | APT with the [owned package policy](../../../shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2) | Signed metadata is accepted; an unknown signing key and altered package bytes are rejected |

The fixture creates a temporary publisher key and a tiny package repository. APT first authenticates
its signed metadata through Squid. Each measured scenario then downloads one package using that
authenticated package index. APT verifies package hashes linked to signed metadata; this is not an
individual signature on each `.deb` file. [1]

The six experiments come from the [same SysML experiment usages](../../../architecture/models/software-intake/analysis/SoftwareIntakeRetrievalAnalysis.sysml)
as [model execution](05-retrieval-execution.md). Their inputs set up the fixture; their expected results
are compared with measured outcomes. The comparison does not implement a second expected-behavior list.

## What is measured

| Scenario | Expected and observed result |
| --- | --- |
| Cache miss, source available | Squid fetches once; APT accepts the correct package |
| Fresh cached package, source unavailable | Squid serves a cache hit without source traffic; APT accepts it |
| Destination denied after caching | Squid denies access; the cached object does not bypass policy |
| Cache miss, source failure | The source returns HTTP 503; retrieval fails without package verification |
| Altered package from source | Retrieval succeeds, but APT reports a hash mismatch and rejects the package |
| Altered package already cached | Squid returns a cache hit; APT still rejects the package |

The [recorded comparison](../../../artifacts/architecture/evidence/software-intake/implementation.json) retains tool
versions, source fingerprints, HTTP status, Squid result, source requests, APT exit/result and the
expected model outcome. Follow the experiment links in the comparison table to the expected sequence,
then follow a message to its function, implementation and tests.

Only observable outcomes are compared. Squid does not expose each internal model action, and its
privacy-preserving log does not record full package URLs. The serialized fixture correlates each
request with its bounded log slice and source counter; it does not fabricate a full internal sequence.
The model's cache-lookup counter is not claimed as an instrumented product measurement.

## Repeat the comparison

Use a Linux or WSL environment with Python, APT, GnuPG, `dpkg-deb` and an installed or unpacked Squid.
The test uses no elevated privileges. Prepare Python dependencies from `tests/requirements.txt` in a
virtual environment. An unpacked Squid needs its matching library, helper and shared-data payloads;
set `LD_LIBRARY_PATH` if required. The tested versions are recorded in the evidence.

First [rebuild the model](02-connected-model.md#build-and-check) if its authored sources changed.
Then, from **the upstream homelab checkout in Linux/WSL**:

```bash
export HOMELAB_SQUID="$(command -v squid)"
export PYTHONPATH="tests${PYTHONPATH:+:$PYTHONPATH}"
export INTAKE_IMPLEMENTATION_REPORT="$PWD/artifacts/architecture/evidence/software-intake/implementation.json"
python -B -m unittest -v test_tier_intake_product
```

For an unpacked Squid, set `HOMELAB_SQUID` to that executable instead. Use the prepared environment's
Python. All six cases run inside one integration test; a missing tool is reported as a skip, not a pass.
The command also tests rejection of metadata whose signing key is absent from the client's trust.

Refresh the views from the checkout with the existing native model build dependencies:

```bash
python scripts/architecture/software_intake.py build
python scripts/architecture/software_intake.py check
```

The product record is separate from model execution. Rebuilding views does not rerun APT or Squid.
Changed model/implementation/test inputs make previous product evidence visibly historical until the
comparison is run again. Raw comparison differences are saved even when the test fails.

For the linked view check, use the existing Playwright/Edge setup from the upstream checkout:

```bash
node docs/08-reference/diagrams/verify-intake-product.cjs
```

Set `DIAGRAM_PLAYWRIGHT` when Playwright is outside the normal module path. The browser report and
light/dark previews are written to ignored `.tmp/intake-render/`.

## Interpret a difference

Open the failed run's measured evidence and expected sequence. Check whether the fixture represents
the same preconditions, whether the model overstates behavior, or whether implementation violates the
accepted design. Correct the owning source and rerun; do not change an expectation just to obtain a pass.

“Eligible fresh cache content” has a precise meaning: the object is still fresh **and** the client's
request permits reuse. Request cache controls, expiry and privacy rules still matter. APT treats
package downloads and repository-index refreshes differently. [2] Passing the cached-package case
does not establish that a complete package update or installation works without a source.

## Boundaries

This verifies the actual Squid/APT programs with project-owned templates in an isolated fixture.
It does not apply Terraform or Ansible to the homelab, test its firewall/VIP/failover, run DNF or
HTTPS/CONNECT, install a package, or establish recovery custody. Source failure here is an HTTP 503,
not a cable failure, DNS failure or timeout. Cache hits use Squid's memory cache; disk persistence and
restart recovery are outside this comparison. Prior source/generated-policy tests cover additional
freshness, revalidation and privacy cases separately.

## References

1. [Debian APT archive authentication and package hash chain](https://manpages.debian.org/trixie/apt/apt-secure.8.en.html).
2. [APT configuration and HTTP cache controls](https://manpages.debian.org/trixie/apt/apt.conf.5.en.html).
