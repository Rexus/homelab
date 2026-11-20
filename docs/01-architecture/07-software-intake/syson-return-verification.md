# SysON requirement/use-case return verification

Tested on 2026-11-19 with SysON 2026.11.0, the pinned SysML Pilot 0.63.1 parser/library and the actual
homelab model in a disposable checkout. Git remains the accepted baseline. This verifies selective
model integration; it does not establish requirement fulfillment or general SysML round-trip fidelity.

## Contents

- [Tested change](#tested-change)
- [Refusal and coverage checks](#refusal-and-coverage-checks)
- [Evidence and release limits](#evidence-and-release-limits)
- [Automation checks](#automation-checks)
- [References](#references)

## Tested change

The test began with the full publication and its two selected views. Existing requirement `REQ-policy`
and use-case `UC-update` documentation were edited in SysON's Details panel. SysON's textual insertion
API added `REQ-return-proof` and `UC-return-proof`, including a native objective requiring the new
requirement, a subject bound to the existing proxy and an actor bound to existing clients.

The ordinary return CLI identified exactly those four roots and proposed changes to two authored
files. The isolated full model build passed. A new SysON import preserved their complete stored
subtrees after normalizing tool UUIDs and documentation whitespace, including relationship endpoints,
subject/actor bindings and criteria. The importer archived and removed its own comparison project.

`apply-changes` wrote the reviewed source files in the disposable checkout; its full build and check
passed. A repeat application reported already applied without duplicates. The proof-only requirement
and use case were not added to the working project's accepted model.

Republishing the integrated model through the normal CLI succeeded with two representations and 307
named model identities. The four edited roots and their stored relationships also survived a fresh
review with no remaining source changes. Its final publication receipt is
`checkout/.tmp/syson/f47ba78f6bc254469181/receipt.json`; the repeat review is
`checkout/.tmp/syson-changes/d1ca19cd234f4b8c/plan.json` (`already_integrated`).

## Refusal and coverage checks

| Check | Observed result |
| --- | --- |
| Concurrent edit to `REQ-policy` in Git and SysON | Review blocked with an explicit conflict; concurrent bytes unchanged |
| Source changed after a ready plan | Application refused the stale plan without writing source |
| Existing requirement deletion or identity change | Regression test rejects the whole import |
| Unsupported part change alongside an intent edit | Regression test rejects the whole import |
| Duplicate or unidentified new stable identity | Rejected rather than silently omitted |
| Changed relationship binding after reimport | Semantic comparison rejects it |
| Source range with Unicode, CRLF and braces inside documentation | Native syntax locations preserve the complete declaration |
| New requirement without a verification case | Listed in `verification_gaps` and the generated intent inventory as uncovered |
| New use case without a modeled scenario | Inventory records pending scenario detail |

The inventory is supporting text. It does not expand the curated native diagrams or claim a passing
test. A native requirement-to-verification relationship is specification coverage, not execution evidence.

## Evidence and release limits

Local proof evidence is under
`C:/Users/vhaka/Documents/ChatGPT/Homelab/.syson-work/return-proof/`:

- `checkout/.tmp/syson/e15933e14fe76ad0076f/`: immutable published baseline.
- `checkout/.tmp/syson-changes/10f678742c3f4cb8/`: validated four-root diff, native indexes,
  candidate workspace, expected/actual stored semantics, archives and applied plan.
- `negative-results.json`: live concurrent-edit and stale-plan refusals.

These are local evidence paths, not portable backups. Preserve required ZIPs separately before cleanup.
The [working guide](../../04-development/model-change-workflow.md) defines supported operations.

The full SysON text export still loses dependencies and contains behavioral syntax unsupported by the
source parser. Only complete edited declarations are selected through native syntax nodes, followed
by full native validation and same-engine semantic comparison. Deletions, ownership/identity changes,
new packages and changes outside the supported roots are refused. Whole-element replacement can
normalize reference spelling, formatting and lexical comments; the original remains in the sealed
baseline and review diff. Review and retain useful author commentary in the accepted source.

The first proof publication also encountered a transient SysON event-processor failure: appearance
mutations returned success without persisting their result. Server logs reported a null representation
and an unavailable scheduler. Restarting only the SysON application container, retaining its database,
then reapplying and verifying the layout resolved it. The failure recurred on another fresh publication. Keeping the native editing-context and both diagram
subscriptions active through import and presentation updates produced a successful normal publication
without a browser-driven repair. The adapter now uses Sirius's `/subscriptions` endpoint and installed
`graphql-ws` protocol, through `websocket-client` 1.9.2. No automatic restart is part of the adapter.
This happened with a supported-only view, so it does not prove that the omitted cached-content item
caused the earlier appearance issue. Persisted-state checks remain required after successful API calls.

The existing native rendering gaps remain explicit: the Overall SVG enclosure and the contained
cached-content ItemUsage are not equivalent native renderings. Tier/zone annotations and colours
remain scoped to intake. A combined requirement-result runner, failure/skip/staleness aggregation,
untraced-code discovery and hosted CI gate remain separate work.

## Automation checks

The focused SysON regression suite passed 48 tests, including 14 return-boundary cases and three native
subscription lifecycle tests. The affected catalogue, model, use-case and reverse-impact checks passed
after correcting an older expected use-case set: the modeled repository-clone goal already depends on
the HTTPS intake scenario and must appear in reverse impact. That expectation was checked against its
native dependency; no implementation relationship was changed to satisfy the test.

The portable SVG/manual navigation suite also passed all five tests. The unchanged working model was
published through the corrected subscription path with 303 named elements and exactly two native views.
System Overall's complete saved presentation matches the accepted baseline. The four returned proof
roots match their edited SysON semantics in the republished proof. Required evidence and all retired
project archives are preserved in `C:/Users/vhaka/Documents/ChatGPT/Homelab/SysON-archives/2026-11-19-return/`.
The working receipt is `.tmp/syson/8fa58c5d364ab05bf8e3/receipt.json`.

The final browser reopening could not be completed: the in-app browser stopped attaching, and the
desktop browser control stopped because it could not establish the current URL confidently. No further
UI route was attempted. Existing Details edits were exercised in the browser earlier; the final
publication was assessed through fresh server archives, exact saved-state checks and repeat publication.
This record does not claim a final visual inspection of the new working publication.

## References

1. [Sirius GraphQL API](https://doc.mbse-syson.org/sirius-web/v2026.11.0/developer-guide/api-graphql.html).
2. [Official subscription protocol handler](https://github.com/eclipse-sirius/sirius-web/blob/master/packages/web/backend/sirius-components-graphql/src/main/java/org/eclipse/sirius/components/graphql/ws/GraphQLWebSocketHandler.java),
   inspected alongside the installed 2026.11 schema; upstream master can change.
