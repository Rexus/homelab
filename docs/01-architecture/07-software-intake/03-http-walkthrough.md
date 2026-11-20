# Follow an HTTP retrieval through the design

Start in the [System Overall SVG](../../../architecture/views/system-overall.svg), opened directly
in a browser. Stay in the diagrams while exploring; use **Documentation** for supporting
text. Browser Back returns to the previous view, including its selected scenario/function.

## Contents

- [Read the design in familiar terms](#read-the-design-in-familiar-terms)
- [Walk the connected views](#walk-the-connected-views)
- [What realizes this behavior](#what-realizes-this-behavior)
- [What is verified](#what-is-verified)
- [Follow a file or test backwards](#follow-a-file-or-test-backwards)
- [How the connections stay current](#how-the-connections-stay-current)

## Read the design in familiar terms

There are three main roles: an **update client**, a **policy proxy with a cache**, and an **approved
software source**. The proxy checks access, reuses fresh content when allowed, or fetches it. The client
then verifies the content before use. The cache never grants trust by itself.

The model describes that same story at different levels; it does not introduce another running system.
Use the logical view to understand responsibilities, the deployment view to see Squid and its VMs,
and the resource view to inspect the platform and hardware beneath them.

| Term encountered in the model | Meaning here |
| --- | --- |
| Use case / scenario | The client's goal / one normal or failure path through it |
| Function | Work that must happen, such as **Check request access** or **Verify before use** |
| Admission | The access check on client, destination and port |
| Eligible response | Cached content that is fresh and allowed to be reused for this request |
| Realization / allocation | The chosen software or resources / the responsibility assigned to an owner |
| Custody | Keeping an independent recovery copy; a disposable cache is not that copy |
| Executable refinement | The runnable model of this behavior, linked to the expected sequence |
| `SC-`, `F-`, `H-`, `X-`, `RUN-` | Stable references for scenarios, functions, HTTP messages, runnable actions and experiments |

Read the descriptive names first. Stable references remain in sources, evidence and diagram tooltips
so names can improve without breaking the connections. Source files and test machinery are supporting
assets, not extra architecture components. The [implementation comparison](06-implementation-comparison.md)
shows the distinction between what the model expects and what real software did.

## Walk the connected views

The use case is **Retrieve and verify software** (`UC-update`). Follow its scenario
**Retrieve or revalidate HTTP content** (`SC-http-miss`): an update client requests allowed content
that is absent from the cache or needs revalidation.

| Open in the diagram | What the next view explains |
| --- | --- |
| System Overall → **Software intake** | The subsystem, its proxy/cache parts and scoped concerns |
| **Use cases** → **Retrieve or revalidate HTTP content** | Selected native scenario: admit, fetch/revalidate, apply cache rules, return, verify |
| Click **Fetch or conditionally revalidate** (`H-fetch`) | `F-http`: inputs, outputs, `REQ-policy`, logical allocation, source and test links |
| **Policy proxy / HTTP cache** | The logical owner and its sibling/cache and shared-provider context |
| **Realization** → **Software deployment** | The selected proxy service, two example VMs and their separate disposable cache volumes |
| **IaC and sources** | Actual Terraform, Ansible and template assets selected through logical/realization trace ownership |
| Back to the intake overview → **Verification** | Scenario acceptance, linked checks, recorded executions and remaining site acceptance |

Direct entry: [HTTP scenario SVG](../../../architecture/views/software-intake/scenario-views.svg#SC-http-miss).
The scenario retains source request/response direction and chronological order. Clicking a message
opens its assigned function, rather than an independently maintained description of that message.

The scenario also uses `F-admit`, `F-cache` and `F-verify`. Cache handling is allocated to the proxy
and rebuildable object store. **Client verification stays outside the proxy boundary**: the update
consumer checks publisher metadata/signatures and stops on failure. A successful retrieval does not
approve an artifact. Related egress enforcement and independent recovery keep their own owners.

## What realizes this behavior

| Design responsibility | Actual source and role |
| --- | --- |
| Admit accepted clients, destinations and ports; deny otherwise | [Squid configuration template](../../../tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2), rendered with [role defaults](../../../tier-2/ansible/roles/cache_proxy/defaults/main.yml) and selected site inputs |
| Retrieve/revalidate and reuse eligible HTTP responses | The same template configures Squid's cache and freshness behavior; [configuration tasks](../../../tier-2/ansible/roles/cache_proxy/tasks/squid.yml) render and validate it |
| Provide the selected VM resources | [Cache Terraform root](../../../tier-2/terraform/deployments/cache/main.tf) connects environment inputs to [VM resources](../../../tier-2/terraform/modules/vm/main.tf); [example inputs](../../../tier-2/terraform/deployments/cache/terraform.tfvars.example) select the instances |
| Provide disposable cache storage | [Cache storage tasks](../../../tier-2/ansible/roles/cache_proxy/tasks/storage.yml) use the shared data-volume role; independent recovery is a separate obligation |
| Verify before use at the client | [Baseline package-policy tasks](../../../shared/ansible/roles/baseline/tasks/package_policy.yml) and [APT policy template](../../../shared/ansible/roles/baseline/templates/apt-package-policy.conf.j2) configure verification and failure handling |

These are selected product and implementation choices. The logical function contracts remain
product independent. The shared platform provides execution, networking and storage, with their
physical backing visible through the linked resource view; VM instances are not physical servers.

## What is verified

The scenario's named implementation checks come from the message trace, rather than being selected
by matching filenames:

- [Integrated Squid/APT comparison](06-implementation-comparison.md): the same six modeled
  experiments run through real cache behavior and package verification with signed metadata.
- [NativeCachePolicy](../../../tests/test_tier_cache_policy.py), `test_source_policy` and
  `test_generated_policy`: run the actual Squid configuration against a local recording origin.
  They cover admission, source fetches, fresh reuse, expiry/revalidation and privacy handling.
- [PackagePolicy](../../../tests/test_tier_package_policy.py),
  `test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception`:
  exercises native APT verification failure and the explicit trusted-source exception.
- [Model contracts](../../../tests/test_tier_intake_model.py) check selected IaC/model alignment;
  [navigation contracts](../../../tests/test_tier_intake_navigation.py) check diagram destinations,
  scope preservation and the model-to-source/test journey.

Read the [verification record](verification.md) for executed checks, environment and outstanding
acceptance. A linked check is not a pass result; local fixture results do not establish deployed
retrieval, firewall enforcement, failover or independent recovery. The [integrated Squid/APT comparison](06-implementation-comparison.md) now follows package retrieval
through the cache to actual client verification in one isolated fixture. It does not test a deployed update.

## Follow a file or test backwards

Open **Change impact** at the bottom of [System Overall](../../../architecture/views/system-overall.svg),
or use the [file/test index](../../../architecture/views/software-intake/asset-impact.svg) directly.
Source and test attachments in the concern/function views also have an adjacent **Impact** link.
The original filename still opens its source; Impact opens its reverse model view.

Try these two paths:

| Start with | Follow backwards |
| --- | --- |
| Terraform → `deployments/cache/main.tf` | The direct `DEF-member` trace leads through selected VM usages, their proxy realization and logical allocations to `F-admit`, `F-cache`, `F-http` and `F-tunnel`, the connected intake scenarios, `UC-update`, and the relevant policy/integrity/custody guardrails. Client verification remains external. |
| Tests → `test_tier_package_policy.py` | The recorded verification messages lead to `F-verify`, the HTTP retrieval/verification alternatives and HTTPS retrieval, `UC-update` and `REQ-integrity`. Denial scenarios and proxy behavior are not assigned to this client check. |

Click a function or scenario to rejoin its diagram. **Trace paths** is a supporting report showing
the native relation behind each result. A test-file association describes evidence to review; changing
the test does not itself change runtime behavior. A whole test file can have a broader trace than a
specific method: use **Test methods** for the exact recorded selector. A linked HTTPS scenario does
not mean every exchange in that scenario was tested, or that successful CONNECT/TLS has been verified.

Starting from a file in the editor, run this from **the upstream kit checkout** with its existing
Python test dependencies installed:

```bash
python scripts/architecture/software_intake.py impact --file tier-2/terraform/deployments/cache/main.tf
python scripts/architecture/software_intake.py impact --file tests/test_tier_package_policy.py
python scripts/architecture/software_intake.py impact --file "tests/test_tier_cache_policy.py::NativeCachePolicy.test_source_policy"
```

This read-only query uses the last built model **and its matching recorded trace**. It still works
after an unfinished edit or file deletion, flags changed/missing inputs, and gives the SVG destination
and witness paths. Rebuild after reconciling the actual change. Unknown files/methods report missing
coverage; they do not silently return an empty impact set. The generated views represent that built
baseline, not a prediction of the current edit or a live system. Copied manuals keep links to their
own sibling IaC repositories and upstream test snapshots; command queries run against the upstream kit.

## How the connections stay current

`SC-http-miss` selects native branches in `B-HTTP`. Its messages depend on functions; functions
depend on guardrails and allocate to logical parts. Those parts allocate to selected realization
elements. Existing trace records associate behavior and reusable definitions with source files and
checks. The generator follows these relationships into the SVGs and supporting reports.

Change the owning SysML source, selected IaC inputs or trace, then rebuild. Consistency checks detect
stale outputs, broken destinations and missing allocations. Views do not edit code or prove that an
implementation meets a requirement; they expose the connected design and its evidence for review.
