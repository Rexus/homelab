# Software-intake model verification

Scope: the upstream Stage 1 example inputs and repository automation, checked on 2026-11-17–19.
This record separates model/source consistency, isolated product tests and live acceptance.
The separate [SysON verification record](syson-verification.md) covers import, native graphical
views, repeat publication, the proxy-contract update and text-export limitations.

## Contents

- [Focused views and element meaning](#focused-views-and-element-meaning)
- [Storage and content correction](#storage-and-content-correction)
- [Native model and source contracts](#native-model-and-source-contracts)
- [Use-case-led adoption](#use-case-led-adoption)
- [System Overall and design depth](#system-overall-and-design-depth)
- [Scoped engineering context](#scoped-engineering-context)
- [Diagram-first walkthrough](#diagram-first-walkthrough)
- [Reverse change review](#reverse-change-review)
- [Engineering relationships and design iteration](#engineering-relationships-and-design-iteration)
- [Native HTTP behavior execution](#native-http-behavior-execution)
- [Real Squid and APT comparison](#real-squid-and-apt-comparison)
- [Follow-up SysML semantic checks](#follow-up-sysml-semantic-checks)
- [Focused bootstrap use case](#focused-bootstrap-use-case)
- [Recorded results](#recorded-results)
- [Diagram review](#diagram-review)
- [Runtime checks](#runtime-checks)
- [Boundaries](#boundaries)

## Focused views and element meaning

Current portable presentation, checked 2026-11-19. This supersedes the older six-panel context
dashboards and the subsystem-specific colours recorded below. System Overall and intake link directly
to focused use-case, requirement and function views; intake also has a requirement/scenario-linked
verification view. Other areas retain mapped owners. The selected portable catalogue has 16 engineering
views; [SysON publication](syson-verification.md) deliberately selects two.

Tiers and zones are explanatory classifications in this example. Their composite model wrappers were
removed; the proxy/cache parts, native flows, allocations, VM resource obligations and platform backing
remain connected. Selected network membership is an explicit VM property. External repositories and
clients are reference roles, distinct from admission allowlists and locally implemented components.
Model part kind alone no longer selects the logical/software colour. Interfaces, information, physical
equipment, actions, intent and verification retain their own category; frames have separate styling.

| Check | Observed result |
| --- | --- |
| Native validation and source contracts | Passed with SysML Pilot 0.63.1 and Java 21; flattened relationships and external references resolve |
| Focused regression checks | 65 passed, including native edit/negative cases, role classification, lost allocations, trace selection, copied-manual links and catalogue checks |
| HTTP model execution | All six OpenSysML 0.12.1 runs match their scenario traces; availability and trust are supplied inputs, not live observations |
| Browser navigation | 11 actual transitions cover overall → intake → use case → scenario → function → design, requirement → test and boot-1 → supporting intake |
| Render review | 44 previews: 11 focused views at 1100/760px on light/dark backgrounds in Edge 157.0.4341.46; geometry checks passed |
| Visual inspection | Logical/deployment, System Overall, goals, requirements, functions and tests reviewed; explanatory enclosures and external references remain distinct |

From **the upstream kit checkout**, with the documented native and browser dependencies available:

```bash
python scripts/architecture/software_intake.py execute
python scripts/architecture/software_intake.py check
node docs/08-reference/diagrams/verify-intake-navigation.cjs
```

The browser report and previews are in ignored `.tmp/intake-focused/`. Regression modules are
`test_tier_focused_views`, `test_tier_design_context`, `test_tier_intake_navigation`,
`test_tier_system_overall`, `test_tier_intake_model`, `test_tier_intake_semantics`,
`test_tier_bootstrap_use_case`, `test_tier_view_catalog` and `test_tier_intake_use_cases`.
Use the test setup documented below; native tools enable the three native mutation/round-trip checks.
Removed generated context/concern SVGs and empty view folders are no longer linked or regenerated.
No infrastructure was applied, and no live cache or network acceptance is claimed by this refinement.
One native check exceeded its 120-second limit during parallel validation; the complete ten-test
use-case group subsequently passed when run without competing model builds.

## Storage and content correction

Follow-up checked 2026-11-19. `L-Cache` keeps its storage identity, logical allocations and virtual-disk
realizations, now named **Rebuildable cache storage**. `CachedContent` is a separate item definition;
the logical store and each selected disk have their own content usage. The native `contents[0..*]`
feature declares the multiplicity. This does not assert replication, shared contents or publisher trust.
The distinction follows [SysML 2.0 §§7.10–7.11](https://www.omg.org/spec/SysML/2.0/Language/PDF):
items can represent acted-on data or material; parts describe components. Item kind alone therefore
does not select the information colour. The reviewed information types do.

Logical and deployment views show blue storage and a mauve `«item»` for its content. Functions retain
their native component allocations. The follow-up layout shows each function and component once;
ordered endpoints keep all six allocation routes separate, without crossings or shared segments. The [storage contract](../../../architecture/design/software-intake/object-cache/README.md)
links the views, source and physical backing.

| Check | Observed result |
| --- | --- |
| Native validation and behavior | Model validates; all six OpenSysML runs still agree with their modeled scenarios |
| Focused and catalogue regressions | 15 passed, including new content ownership/typing, storage/data category, non-data item classification and unique-symbol/arrow endpoint checks |
| Negative checks | Removing native content ownership makes rendering fail; removing a native allocation removes its arrow |
| Browser navigation and geometry | 11 actual transitions and 11 focused views passed; 44 previews refreshed at both widths and backgrounds |
| Visual review | Logical/deployment storage and nested content inspected at normal/narrow widths; unique function/component symbols and uncrossed allocation routes inspected |

The later orthogonal-routing refinement preserves the accepted object positions. Two affected
regressions passed: unique elements with horizontal/vertical, uncrossed allocation routes, and removal
of an arrow when its native allocation is removed. Native validation and all six execution cases also
passed again. The earlier 15-test result above is the broader regression baseline.

The earlier 65-check run above is the preceding focused-view baseline, not a rerun of that full suite
for this correction. The current regression modules are `test_tier_focused_views` and
`test_tier_view_catalog`. No product configuration changed or infrastructure was applied. Native SysON
publication is tracked separately; updated SVGs do not claim that the new item is already published there.

## Native model and source contracts

The official SysML Pilot Implementation 2026-09.1 (kernel 0.63.1) and Java 21 validated the context,
structure, guardrails, behavior and IaC-derived realization together. The normalized export retains
stable identities, reusable types, flows, allocations, participant bindings, guarded alternatives and
native message succession. The example selects two cache VMs with separate local disks.
See the [model map](../model-map.md) and [tested toolchain](../../../architecture/toolchain.json).

Both HTTP/HTTPS sequences come from native model relationships. Each message has a checked trace to
implementation and/or acceptance evidence. Source contracts inspect the rendered Squid admission rules,
CONNECT restrictions, cache/privacy behavior and APT/DNF verification settings. Test references resolve
to named Python test methods; that check alone does not execute those tests.

## Use-case-led adoption

On 2026-11-18, intake moved into Use Cases, Requirements, Functions, Design and Test. Other capability
chapters remain mapped in place. One native use case owns five alternative scenario references;
explicit Boolean redefinitions select paths through the existing HTTP/HTTPS behavior. Five functions
own inputs/outputs, message dependencies, guardrails and logical allocations.

| Check | Result |
| --- | --- |
| Native model build | Passed with the moved sources, scenario references and functional allocations |
| Model/behavior/use-case integration suites | 28 passed, including two native round-trip checks |
| Existing diagram convention suite | 14 passed |
| Native message edit | Regenerated the sequence, README and scenario walkthrough with the same identity/function links |
| Removed native scenario condition | Rejected the incomplete scenario and preserved the previous valid export |
| Generated manual and migration | New engineering links resolve to copied docs/model, owning tier/shared code and upstream test/tool reference snapshots; retired model files pruned; project-owned site model preserved |
| Render review | 24 light/dark renders at 1100px and 760px across six views; no detected label overflow; new use-case and map views visually reviewed |

The main scenario is shown first; alternative paths remain owned by the same use case. The use-case
figure derives subject/actor membership from SysML and uses the shared notation key. It is a tailored
view, with association lines rather than traffic arrows. Product choices stay in software/deployment
design; the physical context maps the surrounding hardware.
This is model/source integration; no IaC behavior changed and no infrastructure was applied.
The earlier isolated Squid/Ansible/APT results below remain prior evidence and were not rerun for this
folder/model change. Successful deployed CONNECT/TLS, failover, egress and recovery remain separate acceptance.

The subsequent physical/software distinction was checked on 2026-11-18: native model validation,
26 fast model/behavior/use-case and manual-integration checks, and 24 light/dark renders passed.
The updated model map was visually reviewed. Software choices moved to `design/software/`; the
physical entry maps hosting/storage/network equipment to existing owners. Native definitions and the
selected realization now identify guest resources as virtual; no hardware topology was inferred.

The connected three-view overview was added on 2026-11-18. Its logical/software mappings resolve
native allocations and the shared client contract; software labels and counts use the checked IaC
inputs. Surrounding equipment is mapped to the hosting/network owners, without a native hardware
topology. The native build, source consistency check, 26 fast integration checks and 28 renders across
seven views passed. The overview and both detailed structural views were visually reviewed at 760px;
all seven views were rendered at 1100px and 760px on light/dark backgrounds.

The historical cross-view role refinement on 2026-11-18 bound reusable model types to visual roles.
Its colour assignments below were superseded by the element-kind profile on 2026-11-19.
Proxy functions remain rose rectangles, cached data remains violet cylinders, clients remain muted
rectangles and the VIP remains a separate beige interface. Physical equipment uses neutral double
outlines. Expanded collections retain grouping outlines around consistently styled members.
The native rebuild and consistency check passed, along with 40 model/behavior/use-case/manual and
diagram-convention checks. The role check rejected an intentionally misclassified proxy. All 28
light/dark renders passed the geometry checks; the overview, logical view and deployment view were
visually reviewed. No model behavior, IaC configuration or infrastructure was changed.

The subsequent subsystem-ownership correction on 2026-11-18 collects intake design under
`architecture/design/software-intake/`. A shared platform boundary now models virtualization,
local storage, guest attachments, logical fabrics and coarse physical connection with stable native
identities. The resource view/report derive those relationships from the model; provider and reverse
impact queries reach the selected VMs, logical contracts and scenarios. Platform detail and actual
site equipment identities remain with their existing owners.

The native build, source consistency check and 45 focused checks passed, including both native
round-trip checks and the new missing-resource/IaC-binding checks. The initial run exposed an old
path in the function-report generator; after fixing that source and rebuilding, the four affected
manual-refresh/diagram tests passed. All 330 local links resolved. The retired viewpoint folders,
layered overview and its renderer/config were removed; refresh removes obsolete copied sources while
preserving site-owned design. All 28 light/dark renders passed geometry checks; the resource view and
updated model map were visually reviewed. No infrastructure was applied or site topology discovered.

The use-case test module runs its two native checks when `SYSML_JAVA`, `SYSML_KERNEL` and
`SYSML_LIBRARY` name the tool locations documented in [Build and check](02-connected-model.md#build-and-check).
Without them those two checks explicitly skip; the eight fast use-case checks still run.

## System Overall and design depth

On 2026-11-18, Design gained a native system boundary and a five-box
[System Overall](../../../architecture/design/README.md). Each box opens its level 1 overview;
intake's policy-proxy/object-cache definitions live in level 2 folders. Shared platform folders map
hosting, networking and data without moving their existing detailed chapters. Native reference bindings
reuse the existing proxy, cache and provider parts. Other system boundaries remain documented maps.

| Check | Result |
| --- | --- |
| Native model build and regeneration | Passed; root references, moved definitions, provider contracts and IaC allocations resolve together |
| Focused model, behavior, use-case, diagram and overview suites | 51 passed, including two native round trips and six new overview consistency checks |
| Navigation | 464 local links/anchors across 28 pages checked at completion review; all 5 root and 8 platform SVG box links resolve |
| Broken connections and hierarchy | Missing native binding, missing/hidden dependency, omitted subsystem, broken link and skipped folder level are rejected |
| Generated manual and cleanup | Model assets and nested overviews copied; project design preserved; retired model path removed on refresh |
| Presentation | 36 renders across 9 views at 1100/760px on light/dark backgrounds; no detected label overflow; both new views visually reviewed |

The native parser retains warnings about repeated display names in provider/realization dependencies;
the stable short identities and their endpoint references remain distinct. Successful parsing is not
runtime acceptance. The compiled package keeps its legacy `SoftwareIntake` name; `SYS-homelab` is the
system design root. Top-level dependencies summarize responsibilities; the detailed intake resource
view retains selected provider obligations and excludes the unselected storage-network dependency.

No infrastructure was applied. The other boundaries do not claim complete native models, live service
integration or verification. SVG hyperlinks are available in standalone SVG viewers; adjacent Markdown
links provide equivalent navigation where embedded images disable interaction.

## Scoped engineering context

Historical 2026-11-18 presentation. The scoped trace-selection rules remain; its six-panel diagrams
were replaced by the [focused views](#focused-views-and-element-meaning).

On 2026-11-18, all 11 Design overviews gained six scoped concern links: Use Cases, Requirements,
Functions, Dependencies, Realization and Verification. The generated README sections retain actual
model identities, scenario selection, owning sources and evidence boundaries. Requirement/function
selection follows native relations; provider concerns and external-actor obligations remain distinct
from direct allocations. Root coverage explicitly identifies the current modeled intake slice.

The object-cache view selects `F-cache`, `REQ-custody` and the two relevant HTTP scenarios. It retains
`F-verify` as an external-client function and related integrity/egress obligations outside its ownership.
Native flows retain the proxy interaction, while resource traversal identifies selected storage backing
without adding the optional storage-network dependency. Mapped areas do not gain unrelated intake
allocations merely by appearing in System Overall.

| Check | Result |
| --- | --- |
| Native regeneration and model/source agreement | Passed; no requirement or behavior ownership was silently reassigned |
| Full focused integration suite | 58 passed, including native round trips, scoped concern selection and copied-manual SVG navigation |
| Final boundary refinement | Eight affected context/model checks rerun and passed after retaining native external interaction roles |
| Navigation | 606 Markdown links/anchors across 28 pages, plus all diagram links across 11 overviews, resolved |
| Rendering | 72 renders across 18 views passed; all 11 changed overviews rechecked in 44 final renders at 1100/760px on light/dark backgrounds |
| Visual review | System Overall, object-cache detail and provider/mapped coverage reviewed; context links are distinct from runtime/design relationships |

The [scope registry](../../../architecture/views/design-context.json) owns root selection and mapped
owner navigation; the [projection](../../../architecture/generated/design-context.json) retains the
complete scoped file/check sets. The six cards are trace-navigation summaries, not native satisfaction
assertions. Test links and accepted scenarios are not runtime pass evidence. No infrastructure was applied.

For a focused visual rerun from the upstream checkout, with the same renderer dependencies below:

```bash
node docs/08-reference/diagrams/render-intake.cjs --overviews
```

This writes the 44-render overview report under ignored `.tmp/intake-render/report-overviews.json`;
the full command retains its separate `report.json`. Regeneration replaces only the marked context
sections and declared generated outputs, preserving authored prose and site-owned models.

## Diagram-first walkthrough

On 2026-11-18, the [System Overall SVG](../../../architecture/views/system-overall.svg) became the
visual entry to linked subsystem and scoped concern views. Documentation remains a labelled asset.
The [HTTP example](03-http-walkthrough.md) follows `SC-http-miss` through its native messages, functions,
requirements, logical allocations, selected realization and implementation/test sources. All five
scenario paths and five functions reuse the same semantic identities. These are tailored, read-only
model-derived views; they do not implement graphical model editing or simulation.

Verification for this change:

- **63 architecture/integration tests passed** in 238.215 seconds, including native model round trips,
  copied manual navigation, generated-content ownership, scoped concerns and portable diagram roles.
- After the final sequence hit-area change, the **five navigation checks and model consistency check
  passed** together in a diagnostic repeat (41.550 seconds); the repository consistency check passed
  directly as well. One preceding fixture copy reported a `system.sysml` hash mismatch. The upstream
  hash matched its recorded snapshot, the isolated check passed, and the six-check repeat did not
  reproduce the mismatch. No model source was changed to silence the check.
- **Three native runtime checks passed** in 571.498 seconds in the existing Ubuntu/WSL environment:
  `NativeCachePolicy.test_source_policy`, `NativeCachePolicy.test_generated_policy`, and
  `PackagePolicy.test_native_apt_rejects_unsigned_and_expired_metadata_but_trusted_source_is_an_exception`.
  These use the actual Squid/APT implementations with temporary loopback fixtures. The HTTP and client
  verification fixtures are separate; they do not establish a deployed end-to-end update.
- **Eight browser navigation steps passed**, from System Overall to intake, use cases, HTTP miss,
  `F-http`, policy proxy, realization, deployment and source attachments. Browser Back and verification
  test attachments were checked. All **87 standalone views** passed selected-view visibility and card
  geometry checks in Edge 157.0.4341.46. Eight representative views were rendered at 1100/760 pixels on
  light/dark backgrounds (**32 previews**); the sequence, function, scoped concerns and mapped coverage
  were visually reviewed. This establishes local browser behavior, not GitHub image-preview support.

The generated-manual checks follow SVG and fragment destinations, IaC links into sibling tier/shared
repositories, and test links into upstream inspection snapshots. Graphic roles and geometry remain
unchanged when those hyperlinks are relocated. A broken destination/fragment fails the model build.
The example remains selected upstream inputs; no infrastructure was applied.

From **the upstream checkout**, with the existing Playwright/Edge setup:

```bash
node docs/08-reference/diagrams/verify-intake-navigation.cjs
```

Set `DIAGRAM_PLAYWRIGHT` to the installed Playwright module directory when it is not on the module path.
The click/geometry report and previews are written under ignored `.tmp/intake-render/`.
Open SVG files directly in a browser with their directory tree intact. Embedded image viewers may
disable navigation; source/document assets may open or download according to browser file handling.

## Reverse change review

On 2026-11-18, [Change impact](../../../architecture/views/software-intake/asset-impact.svg) added
reverse entry for **57 recorded source, check and test-method assets**. The index and each impact view
come from the existing trace map and the native model. Their
[supporting report](../../../architecture/generated/software-intake/reverse-trace.md) retains the
relationship path for each function, scenario, use case and guardrail shown.

**30 focused tests passed** in 128.663 seconds: reverse trace contracts, forward SVG navigation,
scoped design context and model/manual integration. They verify native realization-to-function paths,
exact scenario membership, external client responsibility, method/file distinctions, unknown/escaping
input handling, navigation after source edits/deletions, and copied SVG/source/fragment destinations.
The native SysML build and repository consistency checks passed. Terraform and the cache-policy test
received only a short query-entry comment/docstring; deployed behavior was not changed or rerun.

The standalone Edge 157.0.4341.46 browser check passed **six navigation steps** through the root index,
Terraform asset, function view, adjacent source Impact link and client-verification test view. All
**65 reverse viewports** passed card geometry checks. Index, Terraform and client-test views were
rendered at 1100/760 pixels on light/dark backgrounds (**12 previews**) and visually reviewed.

From **the upstream kit checkout**, with the existing Playwright/Edge setup:

```bash
node docs/08-reference/diagrams/verify-intake-impact.cjs
```

Use `DIAGRAM_PLAYWRIGHT` when Playwright is installed outside the normal module path. The report and
previews go under ignored `.tmp/intake-render/`. The [walkthrough](03-http-walkthrough.md#follow-a-file-or-test-backwards)
explains the two demonstrated paths and `impact --file` queries. The latter read the last built model
and matching trace snapshot even during unfinished source edits; they flag changed/missing inputs.
These results are potential review scope within the modeled intake slice, not failure simulation,
exhaustive repository dependency analysis, requirement satisfaction or fresh runtime evidence.

## Engineering relationships and design iteration

On 2026-11-18, the [MBSE review](04-mbse-review.md) strengthened three working capabilities:
understand the engineering argument, change the native design through diagram-led discussion, and
evaluate a bounded design alternative. Git remains authoritative by explicit authoring choice.
The folder map is unchanged, and other homelab areas remain mapped rather than fully modeled.

| Check | Observed result |
| --- | --- |
| Native model build and source agreement | Passed with four explicit required constraints, a use-case requirement, one satisfaction assertion, eight verification definitions, and native view/viewpoint exposure |
| Architecture integration checks | 46 passed, covering native semantics, reverse impact, navigation, scoped context, model/source contracts, generated manual copying and use-case behavior |
| SysON compatibility checks | Eight passed separately, including rejection of lost verify/satisfy targets, satisfying subjects and required-constraint text |
| Native semantic change | In an isolated fixture, changed a verification subject/objective from custody to egress; rebuilding moved its relationship to the correct requirement view while preserving case identity |
| Native expression analysis | All 16 Boolean combinations evaluated through the Pilot engine, including the analysis case itself; seven counterexamples reject the cache-before-admission candidate |
| Engineering view browser checks | Five viewports, two click journeys and 20 light/dark previews at 1100/760px passed; relationship labels and visual layout reviewed |
| Reverse review browser checks | Six navigation steps, 65 viewports and 12 previews passed for 57 traced assets |

The integration run initially could not import the separate SysON suite because its declared
`requests` dependency was absent. After preparing that dependency in the isolated test environment,
all eight SysON tests passed. In total, 54 distinct focused tests passed across those runs; this is
not a full-repository test result. Test-driven corrections also kept client integrity impact scoped
to its own obligation and included generated `.dot` assets in copied manuals.

The [dated analysis result](../../../architecture/test/software-intake/admission-analysis-2026-11-18.json)
retains its source-model SHA-256, input combinations and native outputs. It establishes only the stated
Boolean policy comparison. It does not execute HTTP/HTTPS sequences, simulate the network, establish
runtime performance or prove the deployed configuration. A changed model requires fresh evaluation.

The `requires`, `allocate`, `satisfy` and `verify` labels now have distinct native model sources.
Satisfaction is an assertion, verification cases are assessment intent, and source/test links identify
available evidence; none alone is an observed pass. Three guardrails explicitly lack a modeled
satisfaction assertion. This pass did not change deployed behavior, rerun native product fixtures,
apply infrastructure or publish the expanded model to a SysON server. The earlier runtime evidence
and documented CONNECT/TLS, custody and independent-egress gaps remain in force.

From the upstream checkout, use the [build setup](02-connected-model.md#build-and-check), then run
`python scripts/architecture/software_intake.py analyze`. Browser reruns use
`node docs/08-reference/diagrams/verify-intake-engineering.cjs` and
`node docs/08-reference/diagrams/verify-intake-impact.cjs` with the renderer setup below.
Their reports remain under ignored `.tmp/intake-render/`.

## Native HTTP behavior execution

On 2026-11-18, the [retrieval execution guide](05-retrieval-execution.md) added native action execution
for six HTTP experiments. OpenSysML MDK 0.12.1 ran its checksum-verified Linux build in AlmaLinux-10 WSL.
Windows Application Control blocked the Windows executable; the user approved WSL execution and no
Windows security setting was changed. The runtime installer and documented WSL path setup were tested.

The native action shares the admission calculation with `F-admit`. Execution actions retain explicit
correspondence to the expected HTTP messages; experiment usages link to their owning use-case scenarios.
The [execution view](../../../architecture/views/software-intake/execution.svg) uses observed
engine events and links them to the expected scenario, functions and existing implementation/test owners.
The [evidence record](../../../architecture/test/software-intake/execution.json) contains native output,
inputs, counters, tool identity, UTC execution time and source fingerprints.

| Experiment | Observed outcome | Source attempts | Client checks |
| --- | --- | --- | --- |
| Cache miss, available source | Accepted | 1 | 1 |
| Eligible fresh cache hit, source offline | Accepted | 0 | 1 |
| Disallowed destination, content cached | Denied before cache lookup | 0 | 0 |
| Cache miss, source unavailable | Stopped without usable content | 1 | 0 |
| Untrusted source content | Rejected before use | 1 | 1 |
| Untrusted cached content | Rejected before use | 0 | 1 |

Verification for this change:

- The complete model passed the official Pilot 0.63.1/Java 21 validation. Duplicate dependency display
  names were removed while preserving their short identities and endpoints; final native validation
  reported no model errors or warnings. Build/check confirmed model, expected behavior, IaC trace and
  generated views agree. The existing Boolean analysis still evaluated all 16 combinations and found
  the seven counterexamples to the deliberately incomplete admission candidate.
- **42 focused tests passed** in 433.975 seconds, covering execution, expected behavior, use cases,
  navigation, scoped context and native semantics. After narrowing the stop-without-content trace,
  **11 execution/reverse-impact tests passed** in 18.738 seconds. Five tests overlap these runs:
  **48 distinct focused tests passed**, including the configured native round-trip checks.
- The negative execution test changed the native admission branch in an isolated model copy. The
  engine then reached cached content for the denied experiment, and comparison with the expected
  scenario rejected that trace. Missing/reordered/unknown actions, wrong values, incomplete execution
  and stale evidence are also rejected or explicitly marked stale; canonical evidence was preserved.
- Reverse checks keep client verification separate from stopping without content. A package-policy
  test no longer implies source-failure or denial coverage; fetching still reaches source-failure and
  untrusted-source scenarios through their actual selected messages.
- All **seven execution viewports and four browser click journeys passed**, with **28 previews** at
  1100/760 pixels on light/dark backgrounds. The index, offline-cache and source-failure views were
  visually reviewed. Both expected HTTP/HTTPS diagrams passed **eight additional previews** with no
  detected label overflow; the expanded HTTP alternatives were visually reviewed.

Reproduce execution with the commands in the guide. From the upstream checkout with the existing
Playwright/Edge setup, review the observed navigation and expected sequences with:

```bash
node docs/08-reference/diagrams/verify-intake-execution.cjs
node docs/08-reference/diagrams/render-intake.cjs --sequences
```

Use `DIAGRAM_PLAYWRIGHT` and `DIAGRAM_MERMAID` for dependencies outside the normal module path.
Reports and previews are under ignored `.tmp/intake-render/`.

This is native execution of the declared action refinement, not execution of the complete interaction
notation: OpenSysML currently rejects the full model's `then message` shorthand. The executable subset
uses the same authored native sources included in the full Pilot validation. Availability, eligible
freshness and publisher trust are supplied inputs, not observed packets or cryptographic results.
There are no modeled timings, concurrency, retries or persistent cache state between experiments.
HTTPS remains expected behavior outside this execution subset. Prior Squid/APT product tests were not
rerun for this change, and no live infrastructure was applied or tested.

## Real Squid and APT comparison

On 2026-11-18, the [implementation comparison](06-implementation-comparison.md) ran the same six
modeled experiments against **Squid 6.14 and APT 2.8.4**, using GnuPG 2.4.4 to create disposable signed
repository metadata. Squid rendered the owned cache-role defaults/template; APT used the owned package
policy template in an isolated configuration. The source, cache, trust material, downloaded packages
and logs were temporary. No package was installed and no host trust or homelab infrastructure changed.

| Check | Observed result |
| --- | --- |
| Available source and cache miss | One source fetch; APT accepted the correct package |
| Fresh cached content with unavailable source | Squid memory-cache hit; no source request; APT accepted the package |
| Destination denied after warming the cache | HTTP 403 / TCP_DENIED; no source request or package verification |
| Source failure on cache miss | HTTP 503; retrieval stopped without package verification |
| Altered package from source | APT rejected the package with a hash mismatch |
| Altered package already cached | Cache hit without source traffic; APT still rejected the hash mismatch |
| Publisher authentication | Signed metadata accepted with the fixture key; missing publisher key rejected with NO_PUBKEY |

The [measured evidence](../../../architecture/test/software-intake/implementation.json) records versions,
inputs, model expectations, source fingerprints, HTTP/Squid outcomes, source requests and APT results.
It compares accepted/outcome/source-request/client-verification observations. Internal cache-lookup
steps are not instrumented or fabricated. APT authenticates metadata before the measured package
downloads; this does not establish an offline repository refresh or complete package installation.
Source unavailability is an HTTP 503 in this fixture, not a physical outage or timeout. The cache-hit
checks use memory; persistent disk/restart behavior is outside this comparison.

The model names and guide entry points were reconciled at the same time. **Check request access**,
**Fetch content from source**, **Reuse fresh cached content**, **Forward HTTPS traffic** and
**Verify before use** now lead the reading path. The use case is **Retrieve and verify software**.
Stable identities remain unchanged. The Boolean outcome input is now `contentVerified`, because it
represents the whole client verification result rather than publisher identity alone. Diagrams retain
technical references in tooltips/evidence and expose descriptive names first. The use-case front door
now links all eight paths, including source and verification failures. See the
[plain-language walkthrough](03-http-walkthrough.md#read-the-design-in-familiar-terms).

Verification performed:

- All **six native model executions and six real-software scenarios matched**. The integrated test
  also rejected metadata with an unknown publisher key. Product differences are recorded rather than
  silently changing model expectations; relevant source edits mark the evidence historical.
- **26 distinct contract/navigation checks passed across the initial and focused recheck runs**:
  product comparison, model execution, reverse impact, scoped context and generated-manual navigation.
  The native admission-mutation check initially timed out under WSL and passed on rerun. Copied-manual
  checks exposed superseded SVGs and an old reverse-report link during the concurrent view relocation;
  they passed after cleanup, link correction and completion of the SysON coverage record.
- The existing **source and generated Squid policy tests passed**, as did the APT check for unsigned
  and expired metadata and the explicit trusted-source exception. These remain separate evidence for
  policy/freshness/privacy and client configuration beyond the six integrated package cases.
- **Seven execution views, four click steps and 28 previews passed**. The implementation comparison,
  simplified scenario and function views passed **three click steps and 12 additional previews** at
  1100/760 pixels on light/dark backgrounds. Those three views were visually inspected. Model/source
  agreement and **1,879 local links/anchors** across 37 architecture/intake pages passed before this
  record was added.

The executable comparison and browser reproduction commands are in the implementation guide. Raw
check logs and previews remain under ignored `.tmp/intake-render/`; reviewed outcome evidence belongs
under Test. Successful deployment, HTTPS/CONNECT, DNF, firewall/VIP enforcement, failover and recovery
remain outside this result. Git retains the model as the authoring source; this test does not establish
graphical SysON parity or a live deployment.

## Follow-up SysML semantic checks

On 2026-11-18, the [further language review](04-mbse-review.md#further-language-semantic-review)
corrected seven bound feature values that were intended as initial state, and added two native merges
for alternative paths. These corrections preserve the expected retrieval outcomes and existing IDs.
The native-object checker inspected 11 assignments and the two alternative-path convergence points.

- **19 regression/semantic/evidence checks passed**: six language checks (including two real native
  builds that deliberately restore the binding/missing-merge mistakes), five engineering-relationship
  checks, five execution-evidence checks and three real-software comparison checks. The changed
  admission guard was also rejected by its expected scenario rather than silently accepted.
- **Six native executions and all six real Squid/APT cases passed again**, with fresh source
  fingerprints. The actual-software test also accepted signed metadata with its fixture key and
  rejected metadata whose publisher key was unavailable.
- **40 browser previews and seven navigation steps passed** across the seven execution views and
  three comparison/scenario/function views. The link check passed 1,899 local links/anchors across
  37 architecture/intake pages before this record was added.

The review used SysML 2.0 formal/2026-03-02, the pinned Pilot/library 0.63.1 and OpenSysML 0.12.1.
It establishes the documented bounded checks, not full language/tool conformance. Informal constraints,
planned verification cases, external software measurements and deployed system validation remain
distinct. No homelab deployment or new graphical SysON publication was performed in this follow-up.

## Focused bootstrap use case

Checked 2026-11-18. The [bootstrap goal](../../../architecture/use-cases/bootstrap/README.md)
binds its subject to the existing boot-1 boundary and its supporting actor to the existing software
intake subsystem. The native dependency links the goal to the expected HTTPS access scenario;
it is not an include across different subjects or an executable Git invocation.

- Native SysML validation and the generated-output consistency check passed.
- Sixteen focused checks passed: four bootstrap goal/binding/navigation/reverse-trace checks,
  four shared-catalogue checks and eight existing use-case contracts. The negative bootstrap check
  rejects the supporting service being rebound to boot-1.
- The six existing native HTTP execution cases were rerun successfully with current source evidence.
  The existing Squid/APT evidence remains current for its unchanged implementation inputs.
- Four previews passed at 1100 and 760 pixels on light and dark backgrounds. The service box opened
  the separate logical design, and the behavior link opened the HTTPS scenario. The normal/light
  and narrow/dark previews were also visually inspected. Local architecture links and anchors passed.
- The reverse trace from bootstrap configuration and its shell proxy template reaches `UC-clone`;
  the goal opens its own view. Its trace is documented context, not a Git runtime result.

The renderer was Playwright 1.62.1 with Edge 157.0.4341.46. From the upstream checkout, with the
[documented model environment](02-connected-model.md#build-and-check) and test imports prepared:

```bash
python -B -m unittest -v test_tier_bootstrap_use_case test_tier_view_catalog test_tier_intake_use_cases.IntakeUseCaseContracts
python -B scripts/architecture/software_intake.py check
node docs/08-reference/diagrams/verify-bootstrap-use-case.cjs
```

The browser check writes previews and its navigation report under `.tmp/intake-render/`.
No real Git clone, deployed HTTPS acceptance or SysON republication was performed. Other context
dashboards remain existing navigation; this bounded example demonstrates focused connected views.

## Recorded results

The following records the earlier structure/behavior baseline from 2026-11-17–18.

| Check | Result |
| --- | --- |
| Native SysML build and snapshot consistency | Passed; no model errors or warnings; tool logging-configuration warnings remain |
| Model/IaC drift, manual navigation and migration ownership | 9 passed |
| Behavior branches, trace ownership, policy drift and shared notation | 9 passed |
| Existing diagram/palette suite | 14 passed |
| Isolated semantic message edit | Native rebuild updated HTTP view, README and behavior trace; logical binding retained |
| Deliberately removed native succession | Projection rejected incomplete ordering; previous valid snapshot preserved |
| Proxy-contract impact query | Identified both HTTP/HTTPS behaviors, member runtimes and logical consumers |
| Generated manual refresh | Removed retired generated model asset; preserved project-owned site model; new links resolved |
| Native Squid source and generated-role tests | 2 passed under Ubuntu/WSL with unpacked Squid 6.14 |
| Native preflight input rejection | 1 passed, covering 16 invalid source/generated input cases |
| Native package-policy suite | 7 passed, including APT rejection and Ansible 2.16 entry-point compatibility |
| Light/dark review at two widths | 20 renders across five views; no detected label overflow; visual review completed |

The earlier structural adoption also passed an isolated three-member IaC variation and rejected an
unresolved proxy type. Its broader repository test attempt found unrelated failures in foundation/trust/
logging views and a software-intake stage-order assertion. This follow-up reports the focused checks
above; it does not claim a clean full-repository suite or completion of concurrent work.

## Diagram review

The two structural views retain the compact reference topology and existing palette. Their keys now
use shared function/element roles and matching symbols: a traffic hexagon, storage cylinder, boundaries,
functions and grouping. Instance-specific properties stay inside the figure or caption.

Both generated sequences retain chronological lifelines, requests, responses and explicit alternatives.
Their source leaves the host theme available; the local review uses neutral/light and dark Mermaid themes.
The repository map is a navigation view, not runtime topology. The use-case view places both actors
outside the subject boundary and shows a goal ellipse without internal product choices.

The 18 current views (including all 11 design overviews) were rendered with Playwright 1.62.1 and Microsoft Edge 157.0.4341.46 at 1100px and 760px.
Mermaid 11.17.2 rendered the sequences and map. Structural/use-case SVGs and the map retain their light canvas on
both page backgrounds. Palette contrast tests are not a complete accessibility assessment, and local
browser rendering does not establish GitHub renderer compatibility.

From **the upstream kit checkout**, with Playwright, Mermaid and Microsoft Edge available:

```bash
node docs/08-reference/diagrams/render-intake.cjs
```

Set `DIAGRAM_PLAYWRIGHT` to an external Playwright module directory and `DIAGRAM_MERMAID` to its external
`mermaid.min.js` when those dependencies are not on the normal module path. Screenshots, review SVGs for
the sequences/map and the browser/geometry report go under ignored `.tmp/intake-render/`.

## Runtime checks

The Squid tests run the actual source/generated configuration against a local recording HTTP fixture.
They exercise admission denial before origin access, exact/suffix domain rules, client CIDRs, fresh
cache hits, expiry, conditional revalidation, private/no-store/no-cache responses and log privacy.
Only loopback high ports and disposable test state are used; no host service is installed or deployed.

The fixture deliberately rejects CONNECT forwarding with HTTP 501. It checks denied CONNECT requests,
but does **not** prove a successful tunnel, TLS source authentication or encrypted payload retrieval.
Those exchanges remain `manual-acceptance` in the
[behavior trace](../../../architecture/generated/software-intake/behavior-trace.md).

From **the upstream kit checkout**, in Linux with the required test dependencies and an installed or
unpacked Squid binary selected through `HOMELAB_SQUID`:

```bash
PYTHONPATH=tests python -B -m unittest -v test_tier_cache_policy.NativeCachePolicy
```

Ansible checks additionally need a compatible `ANSIBLE_PLAYBOOK`, `netaddr`, and collections matching
`shared/ansible/requirements.yml` on `ANSIBLE_COLLECTIONS_PATH`. Package-policy fixtures use temporary
APT/DNF configuration and a local repository; they do not modify the host package configuration.
The recorded run used Ansible 2.16.16, netaddr 1.3.0, ansible.utils 6.1.1 and community.general 10.7.9.
Initial attempts lacked the required collections/dependency; the checks passed after preparing the
repository-declared versions in an isolated test directory. No source-policy changes were needed.

From **the upstream kit checkout**, with that native environment prepared:

```bash
PYTHONPATH=tests python -B -m unittest -v test_tier_cache_policy.NativeCachePreflight test_tier_package_policy.PackagePolicy
```

Set `ANSIBLE216_PLAYBOOK` to an Ansible 2.16 executable to include the compatibility case.
The APT checks verified failures for unsigned/expired metadata and incomplete refresh, and preserved
the explicitly trusted-source exception. Source overrides and deployed publisher trust still require
site acceptance; a local fixture does not establish the deployed policy.

## Boundaries

The model reads tracked upstream examples, not private site inputs, Terraform state or running hosts.
It does not evaluate arbitrary Terraform expressions, every Ansible precedence layer, every transport
failure or protocol retry. The generated manual is a reference snapshot; site models remain project-owned.

No infrastructure was applied. Successful CONNECT/TLS, deployed publisher verification, independent
firewall enforcement, failover, storage recovery and independent custody remain deployment/operations
acceptance obligations. Use the [maintenance guide](02-connected-model.md) to change and rebuild the model.
