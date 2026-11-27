# Work with the intake model

Start with the [engineering relationships](../../../architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml).
The folder map stays unchanged. The model is the design source; diagrams are connected views of it.
Use a diagram element's identity when discussing a change, then revise the owning SysML source and
check its affected implementation and verification before accepting the design.

## Contents

- [Review findings](#review-findings)
- [Further language-semantic review](#further-language-semantic-review)
- [Focused use-case boundary](#focused-use-case-boundary)
- [Read the relationships](#read-the-relationships)
- [Change the design from a view](#change-the-design-from-a-view)
- [Evaluate a design choice](#evaluate-a-design-choice)
- [Limits and next refinement](#limits-and-next-refinement)
- [References](#references)

## Review findings

Review date: 2026-11-18. The baseline was a useful native structural/behavioral model with extensive
navigation, but it did not yet provide a complete working MBSE loop. Passing its own consistency tests
established agreement between artifacts, not adequacy for design work.

MBSE uses models across requirements, behavior, structure and verification/validation; a document map
or set of clickable drawings is only a presentation mechanism. This review uses the INCOSE definition
and SEI's discussion of those engineering domains. [1][2] The user's EA references explain useful view
purposes, but SysML v1 relationship conventions are not an interchangeable v2 metamodel. [4][5]

| Finding in the existing intake slice | Correction / disposition |
| --- | --- |
| Context pages primarily listed nearby concerns; their links did not show the engineering argument | Added a focused relationship view with native element kinds and separately labelled requires, allocate, satisfy and verify links |
| Four requirements contained description text but no explicit required constraints | Added native required constraints, retaining the four guardrails; prose constraints remain intentionally informal |
| The use-case objective did not natively require the admission obligation | Added its native required constraint reference, preserving the external client obligations |
| Scenario acceptance was independently authored in JSON | Moved acceptance to eight native verification definitions with subject types and verify objectives; JSON is now generated |
| All relationships could look like equally strong evidence | Added one explicit policy-proxy satisfaction assertion; the other three requirements visibly have no satisfaction assertion. Neither an assertion nor a verify link is an observed pass |
| Behavior diagrams selected expected traces but could not evaluate the design | Added native admission calculations and an analysis case comparing a proposed cache shortcut with policy-first admission |
| Read-only SVGs and SysON snapshots did not provide an agreed authoring loop | Git remains authoritative by explicit user choice. Discuss changes through diagrams and apply semantic changes through the agent; keep SysON as a review tool |

These are corrections to this pilot, not a claim of full SysML conformance or complete homelab coverage.
Other system areas remain mapped. There is no mandatory folder layout or mandatory catalogue of diagram
types imposed by the language; the accepted repository map remains a navigation convention.

## Further language-semantic review

The follow-up review on 2026-11-18 checked the authored intake structure, use cases, requirements,
behavior, execution, verification, trace projection and view boundaries against **SysML 2.0,
formal/2026-03-02**. Pilot 0.63.1 and its matching library parse the model; OpenSysML 0.12.1 executes
the bounded retrieval experiment. These tool versions are separate from the language edition. [3]

| Finding | Correction or explicit boundary |
| --- | --- |
| Seven changing state/output features were written with `=`, which binds values rather than merely initialising them | Changed their initial values to `:=`. All 11 assignments now have changeable targets without conflicting bound values. See §7.13.4 and §7.17.9 |
| Alternative cache/source paths led directly to the same verification action; terminal alternatives led directly to `done` | Added native `merge` nodes for content delivery and completion. This explicitly models any-one-path convergence, rather than relying on runner behavior. See §§7.17.1–7.17.5 |
| A passing execution had hidden those semantic mistakes | Added checks over the native resolved objects, plus negative tests that reintroduce the mistakes. A successful parse or runner result is no longer the sole acceptance criterion |
| Four required constraints are prose, and verification definitions specify intent | Retained this useful abstraction. Neither the constraints nor their cases are claimed to have solver-proven satisfaction or native executed verdicts. Actual software results remain separate evidence |
| Generic dependencies connect scenarios, functions, execution steps and external assets | Retained as explicit trace/correspondence links. They do not assert native action performance, formal refinement, data transfer or requirement satisfaction |
| Sequence self-messages summarise internal processing; interfaces use a coarse `Transfer` type | These are declared interaction abstractions, not implemented function algorithms or complete protocol/interface contracts. Use native actions/performance and typed payloads when a question needs those semantics |
| Some case acceptance text spans more behavior than its `verify` objective | The objective identifies the specific guardrail; the scenario supplies additional acceptance intent. A passing six-case package comparison does not verify the complete TLS, network-egress or recovery obligations |

The native checker is [intake_language.py](../../../scripts/architecture/intake_language.py), called
from the owning model projection during `build`. Its convergence restriction applies to the
single-path retrieval experiment; it is not a universal ban on concurrent actions or joins.
The generated model index records the checked assignments/features and merge identities.
The [regression tests](../../../tests/test_tier_intake_language.py) include real native builds with
an incorrectly bound counter and a missing merge. They fail before new generated views are published.

The initial value and merge corrections preserve the actor-visible story and existing element IDs;
two internal merge IDs are added. Sequence diagrams continue to show meaningful interactions rather
than internal execution mechanics. The real-software comparison is rerun because its model source
fingerprints changed; expected outcomes are not rewritten to fit observed results.

For changes to this model, check the affected language construct against its specification, inspect
resolved native objects, and introduce a meaningful negative case where a missed semantic error is
plausible. Preserve subject/relationship meaning through the projection and keep unsupported semantics
explicit. This is a bounded correctness review, not certification of the entire language/toolchain.

## Focused use-case boundary

The [bootstrap clone example](../../../architecture/models/platform/hosting/Hosting.sysml) corrects the
presentation of connectivity: the use-case view selects an operator goal on boot-1 and a supporting
software-intake actor. The actor binds to the existing intake subsystem; selecting it opens the
separate logical design. It does not copy the internal proxy/cache or repeat the concern dashboard.

SysML v2 subject and actor memberships are retained as `has-subject` and `has-actor` projection
relations, distinct from composition. Roles are relative to this subject. The cross-subject link
to the intake HTTPS scenario is a dependency, not `include use case`, executable invocation or
formal refinement. Included use cases retain the including case's subject. [3, section 7.25]

The view is intentionally a goal view. The linked scenario explains expected behavior and identifies
the current configuration; the existing HTTP product experiment does not verify a Git clone.
The shared view catalogue includes this selection. SysON publication and graphical support for the
new membership relations have not been rechecked in this pass. Existing context dashboards remain
legacy navigation; this focused example establishes the corrected approach without a whole-map rewrite.

## Read the relationships

SysML v2 gives requirements constraints and subjects, use cases actor-visible objectives, verification
cases verified requirements, and views explicit exposure of model elements. A satisfy usage asserts a
requirement for its bound subject; it does not establish an empirical test result. [3, §§7.21–7.26]

| What the view says | Meaning here | Owning source |
| --- | --- | --- |
| Objective **requires** `REQ-policy` | Admission is part of the use-case objective | [use cases](../../../architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml) |
| `F-admit` **allocate** `L-Proxy` | This function is assigned to this logical part | [functions](../../../architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml) |
| `L-Proxy` **satisfy** `REQ-policy` | Explicit design assertion for the selected proxy, subject to verification | [policy requirement and assertion](../../../architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml) |
| `VC-http-denied` **verify** `REQ-policy` | The verification case assesses that obligation; no result is implied | [native cases](../../../architecture/models/software-intake/SoftwareIntakeVerification.sysml) |
| **Dependency** | A general design relationship; it does not silently become satisfaction, performance or a data flow | The declaring model package |
| Source/test attachment | Repository trace to implementation or a check; not a native runtime connection | [implementation trace](../../../scripts/architecture/config/trace/software-intake.json) |

The new view uses native [view exposure and a viewpoint](../../../architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml).
Its SVG retains the project palette but is a tailored rendering, not a claim to implement every standard
graphical notation. Colour never substitutes for the element kind or relationship label. Use the
[verification pages](../../../architecture/models/software-intake/SoftwareIntakeLogicalDesign.sysml) to see all
eight cases, their subjects, acceptance intent and the missing satisfaction claims.

## Change the design from a view

1. Open [System Overall](../../../architecture/generated/HomelabSystemOverview.svg), select software intake, and
   choose the use case, requirement, function or part relevant to the question. Use **Engineering
   relationships** from Requirements to inspect the connected argument.
2. State the desired outcome and selected identities, for example: “For `F-admit`, evaluate whether a
   warm cache may skip destination admission.” Include the scenario or constraint that motivates it.
3. The agent reads the owning native source, upstream intent, related allocations and every affected
   use. It presents a material design choice before changing the implementation. A layout adjustment
   changes presentation only; a new connection must identify its semantic kind and endpoints.
4. Update the SysML and any necessary IaC/code/tests as one reviewed change. Use **Change impact** for
   the reverse path; use the native element query for shared definitions. Preserve stable identities.
5. Rebuild, inspect changed relationships and evaluate the relevant model or implementation checks.
   Review the regenerated views and evidence limits. Keep the selected decision and rejected alternative
   with the design so the next iteration can reconsider it.

The [native build instructions](02-connected-model.md#build-and-check) own tool setup. Graphviz 14.0.5
renders the relationship graphs; install it on PATH or set `GRAPHVIZ_DOT`. Layout is generated from
native relations; `.dot` projections beside the SVG are outputs, not another model source.

From **the upstream homelab checkout**, with the existing SysML tool variables configured:

```sh
python scripts/architecture/software_intake.py build
python scripts/architecture/software_intake.py impact REQ-policy
python scripts/architecture/software_intake.py check
```

The [SysON publication workflow](../../04-development/syson.md) remains a separate snapshot review.
The tested release's export loses dependency/behavior information; it cannot be the automatic path back
to Git. Its General View supports graphical creation, but that alone does not establish a safe authoring
round trip for this model. [6] Read the [recorded compatibility findings](syson-verification.md) before
publishing a broader language subset. This revision's new native cases are not claimed to round-trip.

## Evaluate a design choice

**Question:** can a warm cache skip admission? The accepted policy checks client, destination and port
before any content access. The deliberately rejected candidate allows a cache hit to bypass that check.
Both expressions live in [admission.sysml](../../../architecture/models/software-intake/SoftwareIntakeBehavior.sysml).
`F-admit` uses the same accepted calculation; `AN-admission` owns the comparison intent.

From **the upstream homelab checkout**, using the same tool variables as the build:

```sh
python scripts/architecture/software_intake.py analyze
```

The command rebuilds and asks the pinned SysML Pilot expression evaluator to calculate both alternatives
and the analysis case itself for all 16 Boolean input combinations. Python supplies inputs and
records results; it does not implement
a second admission algorithm. The result and model fingerprint are saved in
`.tmp/software-intake-analysis/result.json`. Inspect counterexamples before accepting an alternative.
The official Pilot exposes native expression evaluation through its interactive API. [7]

This is finite Boolean analysis under stated assumptions. It does not simulate HTTP timing, execute
the sequence diagram, prove the requirement for arbitrary traffic, or establish the deployed policy.
The actual Squid tests and deployment acceptance remain separate evidence.
For executable retrieval paths, use the subsequent [native action execution](05-retrieval-execution.md).

The [recorded 2026-11-18 evaluation](../../../artifacts/architecture/evidence/software-intake/admission-analysis-2026-11-18.json)
contains 16 evaluated combinations and seven counterexamples to the cache shortcut, with the evaluated
model fingerprint. This is historical evidence; rerun analysis after changing the model. The
[verification record](verification.md#engineering-relationships-and-design-iteration) captures the checks
and the remaining evidence boundaries.

## Limits and next refinement

- The intake-only scope is intentionally bounded. System Overall is still a map of other subsystem
  responsibilities, not a complete functional or interface model of the homelab.
- Generic `Transfer` payloads and in/out ports remain coarse. Refine request/response types, direction,
  protocol failures and function performance when the next engineering question needs that precision.
- Scenario references select traces through existing behavior. They are not concurrent executions;
  the separate native action refinement now executes the selected HTTP paths, with checked correspondence.
  HTTPS remains an expected interaction model; see [execution scope](05-retrieval-execution.md#evidence-boundaries).
- Custody and independent egress need site-owned design and evidence. Their native verification cases
  expose those obligations; this review does not invent implementations or mark them satisfied.
- Full source TLS still requires runtime evidence; the [isolated Squid/APT comparison](06-implementation-comparison.md) now checks signed metadata and package hashes. The native admission
  calculation addresses a different, narrower question.
- Graphical drag-and-edit round trips remain outside the selected Git-owned workflow. Discussing and
  changing the model through its views is supported through the agent, with reviewed source changes.

Expand by engineering question, not by adding empty diagram types. For example, a failover question
needs failure states, timing assumptions and acceptance; a hardware-capacity question needs resource
quantities and backing relationships. Add only the detail that helps decide or verify something.

## References

1. [NAFEMS–INCOSE SMSWG: MBSE terms and definition](https://www.omgwiki.org/MBSE/doku.php?id=smswg:terms_definitions).
2. [SEI: An Introduction to Model-Based Systems Engineering](https://www.sei.cmu.edu/blog/an-introduction-to-model-based-systems-engineering-mbse/).
3. [OMG SysML 2.0 Part 1, formal/2026-03-02, §§7.21–7.26](https://www.omg.org/spec/SysML/2.0/Language/PDF).
4. [Sparx: SysML use-case models](https://sparxsystems.com/enterprise_architect_user_guide/17.1/modeling_languages/sysml_use_cases.html).
5. [Sparx: SysML model elements and relationships](https://www.sparxsystems.com/enterprise_architect_user_guide/17.2/modeling_languages/sysml_model_elements.html).
6. [SysON 2026.11 General View](https://doc.mbse-syson.org/syson/v2026.11.0/user-manual/features/general-view.html).
7. [SysML Pilot interactive expression evaluator](https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation/blob/master/org.omg.sysml.interactive/src/org/omg/sysml/interactive/SysMLInteractive.java).
