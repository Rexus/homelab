# Develop with the homelab model

Git holds the accepted model, implementation and verification definitions. Changes may begin in SysON,
in the authored model, or in code and IaC. Bring them together as one reviewable Git change, check their
effect on requirements and use cases, then publish the reconciled model to SysON and the portable SVGs.

The bounded return path supports additions and edits to package-owned requirements and use-case
definitions. It prepares a conflict-checked source diff, validates the full model and checks a fresh
SysON import before application. The [requirement runner and CI checks](requirement-reporting.md)
connect actual scoped results to every native requirement; importing a requirement alone does not
establish fulfillment. Hosted pipeline execution follows the normal signed push handoff.

## Contents

- [One baseline and two ways to start](#one-baseline-and-two-ways-to-start)
- [Bring a SysON change back](#bring-a-syson-change-back)
- [Develop and verify a requirement](#develop-and-verify-a-requirement)
- [Reconcile code into the model](#reconcile-code-into-the-model)
- [Current capabilities](#current-capabilities)
- [Further integration](#further-integration)

## One baseline and two ways to start

Start at [System Overall](../../architecture/README.md), follow the affected subsystem, and
identify the actor goal, constraints and intended observable outcome. Keep the explicitly selected SysON views
and their shared SVG selections; adding requirements or results does not automatically add diagrams.

| Starting point | Change to review |
| --- | --- |
| Requirement, use case or design edited in SysON | Proposed changes to the owning SysML sources, their consumers, implementation and verification |
| Model edited in Git | The same impact and verification review, followed by native publication |
| Code, IaC or configuration changed first | Actual behavior compared with intended design, including newly unmodeled responsibilities and missing tests |

Git remains the accepted baseline; SysON becomes a place to originate proposed edits. A working change
can be incomplete, but it must show what is planned, implemented and verified separately. Saving a draft
requirement does not assert that the released system meets it. Project commit and push remain the
normal reviewed handoff; importing a proposal must not commit or push unrelated pending work.

## Bring a SysON change back

Use a publication created by the current adapter. Its receipt seals the authored source baseline and
native project archive, including uncommitted source. Older receipts without that baseline cannot
recover it retrospectively from an already edited project. Preserve those projects for reconciliation.

From **the upstream homelab checkout**, with the pinned tools prepared as in [SysON setup](syson.md#prepare):

```bash
python scripts/architecture/syson.py review-changes --receipt .tmp/syson/<publication>/receipt.json
```

The command captures the edited project and compares it with both the publication baseline and current
Git sources. It prints a `changes.diff` and `plan.json` under `.tmp/syson-changes/<review>/`. Inspect the
diff, impact and `verification_gaps`. Status `ready` means the source proposal passed model checks and
the same-engine semantic comparison; it is not an implementation or release verdict.

```bash
python scripts/architecture/syson.py apply-changes --plan .tmp/syson-changes/<review>/plan.json
python scripts/architecture/syson.py publish
```

Application checks the tool snapshot, source inputs, adapter and pinned parser/library again. It writes
only the reviewed authored files, then builds and checks the model and generated outputs. Git changes
remain uncommitted. Repeating application does not duplicate elements. If a post-write build is
interrupted, the plan records `sources_applied`; rerunning can finish it when those sources still match.
An edited or stale candidate requires a new review rather than bypassing the checks.

| Supported scope | Required shape or behavior |
| --- | --- |
| Existing requirement/use-case changes | Package-owned `RequirementUsage` / `UseCaseDefinition`; stable `REQ-` / `UC-` identifier, kind and owner retained |
| New requirements/use cases | Unique stable ID in an existing uniquely located authored package; no automatic new package or file selection |
| Properties and owned relationships | Complete native subtree must survive source validation and same-engine reimport, including subject, actor, objective and reference bindings |
| New intake intent | Requirement criteria in required-constraint documentation; use-case subject/actors with stable IDs and explicit bindings to modeled roles |
| Concurrent edits | Changes elsewhere in the source file survive; concurrent changes within the same edited root are reported as conflicts |
| Unsupported changes | Deletes, identity/kind/owner changes, unidentified roots, new packages and changes to other semantic elements block the whole proposal |

SysON's native editor or supported textual insertion can originate changes. The proven test edited
existing requirement/objective documentation in Details and added a requirement and linked use-case
definition through SysON's textual insertion API. New scenario behavior must also meet the existing
scenario/verification conventions; this importer does not invent tests or implementations.

The adapter uses the official parser's syntax nodes to locate complete edited declarations. SysON's
export may normalize formatting and reference spelling and omit ordinary lexical comments inside
those declarations; inspect the diff and retain useful author commentary after integration. The sealed
baseline retains the original source text.
It never replaces the entire repository with the text export: that export loses dependencies and has
known behavioral syntax gaps outside this supported subset. A complete candidate build and comparison
of stored relationships detect loss inside the selected elements. See [recorded limits](syson.md#ownership-and-limitations).

Every requirement/use case remains visible in the generated [intent inventory](../../artifacts/architecture/generated/software-intake/intent.md).
Missing verification cases and missing scenario detail appear as gaps. New entries do not expand the
selected SysON views or the curated engineering diagram selection.

Complete the engineering change before treating it as delivered: reconcile implementation allocations,
acceptance criteria and test bindings, run relevant tests and retain their evidence. A draft requirement
may be integrated with its gaps explicitly recorded. Rebuild and publish after reconciliation. Keep the
edited origin until the new publication is verified and any remaining work has been preserved.

Archives, diffs and plans under `.tmp/` are ignored local evidence. Move required archives to durable
backup before cleanup. Full project ZIPs preserve tool state; they do not substitute for source review.

## Develop and verify a requirement

Follow the connected path from actor need/use-case scenario through requirement, responsible design,
implementation and observable verification. Preserve the actual typed relationships between them.
Use cases describe the need; requirements state the obligations; verification assesses those
obligations. Also validate that the scenario delivers the intended actor outcome.

For each accepted requirement, keep its stable ID, subject and applicability, rationale, measurable
criteria, responsible design and implementation targets connected. Link its native verification case
to real test identifiers or an explicit analysis, inspection or demonstration. A test must assert the
criterion in the relevant configuration; a linked test file alone establishes no result.

For intake, the existing [native verification cases](../../architecture/models/software-intake/SoftwareIntakeVerification.sysml)
and [implementation/test bindings](../../scripts/architecture/config/trace/software-intake.json) are the starting point.
The [test entry](../../artifacts/architecture/evidence/software-intake/README.md) separates source checks, executable
model behavior, isolated products and site obligations. For example, isolated Squid refusal tests can
support proxy-policy evidence; they cannot establish that a deployed network has no bypass path.

The planned report must start from **every applicable requirement**, including ones without tests:

| Result | Required meaning |
| --- | --- |
| Verified in declared scope | All mandatory criteria have current passing evidence from the required methods and environment |
| Failed | At least one mandatory criterion has a current observed failure |
| Not run | A required assessment is defined but has no completed result for this scope |
| Blocked | The assessment could not run or finish; state the missing prerequisite or error |
| Uncovered | A criterion lacks an adequate verification method or binding |
| Stale | Evidence no longer matches the relevant model, code, tests, configuration or environment |

Keep individual criterion outcomes alongside the requirement result so multiple gaps remain visible.
A passing test cannot hide another current failure. Skips, expected failures and missing manual checks
do not count as passes. Keep lifecycle and applicability separate: draft, deferred, excluded or waived
obligations remain visible with rationale. A waiver records an acceptance decision, not fulfillment.

Evidence must identify expected and observed results, requirement/case/test IDs, source and model
fingerprints, environment/configuration, tool versions, date and durable raw result links. Retain failed
and interrupted runs too. Rebuilding a model cannot renew old runtime evidence. A model's `satisfy`
assertion, `verify` objective, successful parse or simulation cannot prove implementation behavior.

Before release, the intended CI gate will reject broken model references, unresolved change conflicts,
failed mandatory checks, and missing or stale mandatory evidence for the selected scope. Draft design
work can still be saved. Any permitted exception needs an explicit scope, rationale and review point.
This gate is a planned integration; it is not currently wired into a hosted pipeline.

## Reconcile code into the model

Inspect the changed execution path and new files as well as the recorded traces. A reverse query can
only find known links; new untraced behavior must become an explicit finding in the selected scope.
Classify each discrepancy as missing design/trace, an intended design change, an implementation defect,
or a documented scope exclusion. Reuse existing shared definitions and identities when adding coverage.

Record inferred design as an observation of the implementation until checked against its intended
constraints. Confirm actual wiring through code/IaC and behavior through suitable runtime evidence.
Do not lower a requirement or change expected results merely to make an accidental implementation pass.
An intentional requirement change must explain its reason and review affected consumers and tests.

For an existing trace, run from **the upstream homelab checkout**, after the initial
[model build](../01-architecture/07-software-intake/02-connected-model.md#build-and-check):

```bash
python scripts/architecture/software_intake.py impact --file tier-2/ansible/roles/cache_proxy/templates/squid.conf.j2
```

**Expected:** functions, scenarios, use cases, requirements and verification cases reached through the
last built trace snapshot, plus a source-freshness statement. This is potential review scope, not a list
of failed tests. The query was checked on 2026-11-19 with matching source fingerprints and returned the
proxy-policy, integrity and custody requirements. It does not discover arbitrary untraced files.

After reconciling the affected sources, use the existing build/check path, run the relevant
[tests](testing.md), review their failures and skips, and [publish to SysON](syson.md).

## Current capabilities

| Capability | Current state |
| --- | --- |
| Native model validation, source/trace checks and reproducible SVGs | Available through `software_intake.py build` and `check` |
| Git model to six selected SysON views, repeat publication and drift detection | Available through `syson.py publish`; [coverage gaps](../../artifacts/architecture/evidence/syson-view-coverage.md) remain explicit |
| Reverse impact from known code/test bindings | Available through `software_intake.py impact --file`; bounded to recorded traces |
| Test-selector existence and scenario acceptance coverage | Checked; does not mean those tests were executed |
| Native model execution and isolated Squid/APT comparison | Available for the documented scenarios; source fingerprints detect stale evidence |
| Site egress, recovery and other operational obligations | Require their own environment-specific evidence; model/product tests do not fulfill them |
| SysON requirement/use-case changes returned as conflict-checked Git edits | Available through `review-changes` / `apply-changes` for the bounded scope above; full model validation and stored-subtree comparison required |
| Requirement verdicts from actual results, including failure/skip history | Available through `requirements.py run/report/gate`; all obligations remain visible across isolated and site scopes |
| Requirement CI gates | GitLab job wired to native validation, reporting regression tests and isolated implementation checks; locally rehearsed, hosted run awaits signed push |
| Discovery of new untraced behavior | Manual scoped diff and execution-path review; not automated |

## Further integration

The return slice is recorded in [return-path evidence](../01-architecture/07-software-intake/syson-return-verification.md).
Requirement evidence and CI are now covered by the [reporting workflow](requirement-reporting.md) and
its [verification record](../01-architecture/07-software-intake/requirement-reporting-verification.md).
Future slices can add reviewed site-evidence ingestion and scoped discovery of newly untraced behavior.
Preserve the existing change conflict, identity and relationship checks when extending those paths.
This does not establish lossless editing of all SysML constructs or deployed system correctness.
