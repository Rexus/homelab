# SysON integration verification

Checked on 2026-11-19 against `eclipsesyson/syson:v2026.11.0` at `http://localhost:8080`,
using the repository's pinned SysML Pilot toolchain. This is model integration evidence;
no homelab infrastructure was deployed and no runtime acceptance is claimed.

Use the [SysON workflow](../../04-development/syson.md) for publication and model changes.
Git holds the accepted semantic source and selected layouts. SysON contains editing working copies
with the two selected views. [Requirement/use-case return evidence](syson-return-verification.md)
records the bounded conflict-checked path back into Git.

## Contents

- [Current compact publication](#current-compact-publication)
- [Cleanup and recovery](#cleanup-and-recovery)
- [Earlier contract-change evidence](#earlier-contract-change-evidence)
- [Compatibility findings](#compatibility-findings)

## Current compact publication

The normal publication is explicitly limited to `VIEW-system-overall` and
`VIEW-software-intake-logical`. The portable engineering catalogue may contain other selected views;
reports, catalogue growth and SVG pages do not automatically create native representations.

- System Overall retains the accepted five subsystem identities, four dependencies and source-owned
  placement from `architecture/views/system-overall.json`.
- Software intake uses native **Interconnection View**, preserving the seven parts/reference roles,
  three nested client references and three actual flows selected by `logical.svg`. Each arrow resolves
  through its port to the expected selected source and target. The native ports remain intact while
  redundant captions and unrelated compartments are hidden.
- Tier 2 and Edge/DMZ are lightly coloured native comment enclosures around the proxy and cache. Their
  labels, nesting and selected members come from the same SVG. Each has a borderless native caption;
  all four comments live in the presentation package and add no parts or composition relationships.
  The accepted System Overall's surrounding SVG system frame remains absent in its native presentation.
- Import checks compare the full named model, including stable identity, ownership, types, contract
  text, bindings and supported relation endpoints. The native view bundle is validated before import.
- Saved-view checks reject missing or reversed flows, flattened nested references, misplaced children,
  extra native representations and an unknown or expanding publication selection. Annotation checks
  reject fake parts, missing notes, incorrect enclosure membership and undersized captions. Colour
  checks reject drift from the shared SVG fill, border, effective text and connector palette.
  Thirty-one SysON tests and four shared-catalogue tests passed. Diagram checks use persistence IDs,
  not display names.

Open [System Overall](http://localhost:8080/projects/05f042b5-45fd-4bae-9815-2db531cd1e86/edit/d78580cf-ae5e-4908-ba97-ce942f1dfd0d) or
[software intake](http://localhost:8080/projects/05f042b5-45fd-4bae-9815-2db531cd1e86/edit/1405526b-10bf-4152-92fe-d7a343eabd5c).

All **303 named identities** matched the bounded import projection. Both native presentations were
visually inspected; the final intake was reopened with its stable annotation dimensions, shared colours
and all three flows visible. The refinement adds five item-related identities while retaining every
existing identity and allocation. Only `DEF-cache` documentation and the `L-Cache` storage label changed
among the previous 298 identities. Repeating the complete native build and publication reused the same
project and representations. The final saved
archive also passed the layout, selection, flow and palette checks. System Overall's saved node/edge
styles, labels, positions and sizes match the accepted colour review archive. The current Git model and assembled
native source matched the tested snapshot, and the generated model/SVG consistency check passed.

The shared cached-content definition is `DEF-cached-content`. Its `DEF-cache-contents` feature and
contextual usages `L-cached-content`, `CONTENT-cache-1` and `CONTENT-cache-2` retain their ItemUsage
kind, storage ownership and CachedContent type through import. The SVG selects the logical item inside
blue storage with information styling. Native Interconnection View omits that item and its containment;
both remain reported as gaps. No substitute part or comment is introduced. The other selected parts,
three flows, boundary annotations and shared colours pass the saved-view checks.

Software intake explicitly opts into the shared notation palette; System Overall keeps its accepted
appearance. Tier, zone, network and other boundary treatments are reusable visual definitions. Frame
membership and placement remain local to each view, and the native comments add no engineering parts.
The [workflow](../../04-development/syson.md) describes the shared definitions and colour ownership.

The preceding cache-content refinement receipt and detailed check are `.tmp/syson/c5f1438a639ab27f121c/receipt.json` and
`cache-content-verification.json`. The [portable coverage report](../../../architecture/test/syson-view-coverage.md)
records the retained System Overall enclosure difference and the intake item/containment omission.
It does not claim full native rendering parity.

The original nine-box prototype also proved that Interconnection View renders real nested parts and
all three flows. General View had flattened those parts and omitted the flow edges. The subsequent
model correction removed the tier/zone parts rather than preserving false composition merely to keep
their boxes. Native renderer choice and semantic correctness are separate checks.

The current return-ready publication receipt is `.tmp/syson/8fa58c5d364ab05bf8e3/receipt.json`.
Its 303 named elements match that preceding model exactly. System Overall's saved presentation is
unchanged; intake's saved palette, annotations, nesting and flows pass the same checks. See the
[return-path evidence](syson-return-verification.md) for the separate four-root editing proof.

## Cleanup and recovery

The return-workflow pass archived and removed four disposable proof/trial projects and the superseded
accepted review. Current and proof archives, immutable baselines, source diff, negative results and
cleanup manifest are in `C:/Users/vhaka/Documents/ChatGPT/Homelab/SysON-archives/2026-11-19-return/`.
SysON retains the current two-view project and the two original user projects.

The earlier cleanup archived and removed twelve superseded generated projects. The annotation pass
also archived and retired the preceding compact review, an intermediate annotation revision and the
disposable annotation trial. Its initial rejected-import trial was archived and retired separately.
The colour pass archived and removed the preceding annotation review and one intermediate colour
revision. The cache-content pass archived and removed that colour review and two incomplete native
trials. SysON contains only the current two-view review plus the original `homelab` and `SysMLv2` projects.

The preceding cache-content review, receipt, verification record and cleanup manifest are in
`C:/Users/vhaka/Documents/ChatGPT/Homelab/SysON-archives/2026-11-19-cache-content/`.

The preceding colour archives, pre-colour baseline, receipt, verification record and cleanup manifest are in
`C:/Users/vhaka/Documents/ChatGPT/Homelab/SysON-archives/2026-11-19-colours/`.

Annotation archives, the final receipt and verification record are in
`C:/Users/vhaka/Documents/ChatGPT/Homelab/SysON-archives/2026-11-19-annotations/`.
The cleanup verified project provenance, current model fingerprints and archive integrity before removal.

The earlier durable local backup is
`C:/Users/vhaka/Documents/ChatGPT/Homelab/SysON-archives/2026-11-19-compact-cleanup/`.
It includes the cleanup manifest, original receipts, all twelve project ZIPs and the final compact ZIP.

Archives preserve each project's current model and representation state and have ZIP integrity and
SHA-256 checks recorded in `manifest.json`. Original `homelab` and `SysMLv2` projects were preserved.
Old review URLs in earlier evidence are historical identifiers; use the current coverage report's links.
The publisher itself never deletes projects. Cleanup targeted only explicit generated project IDs with
matching local receipt provenance, after their backups had been checked.

The run directory contains the assembled `.sysml`, native validation log and export, SysON API elements,
expected/actual structural projections, coverage, receipt and project ZIP. `.tmp/` is ignored evidence;
keep needed native archives outside it. The server database volume remains its persistence boundary.

## Earlier contract-change evidence

The earlier test clarified the existing
[PolicyProxy contract](../../../architecture/design/software-intake/policy-proxy/definition.sysml):
admit by client/destination/port before forwarding or cache lookup, and reject disallowed requests
without origin access or cached-content reads. The stable identity remained `DEF-proxy`.

The stored old/new projections changed exactly that definition's documentation. All nine typed uses
remained connected: `DEF-member-proxy`, `H-proxy`, `L-Proxy`, `R-Pair`, `RUN-cache-1`, `RUN-cache-2`,
`S-proxy`, `SYS-intake-proxy` and `UC-supply`. This clarified the contract without deploying Squid changes.
The native impact query also traversed related functions, scenarios, realization and verification.

The separate contract/impact experiment subsequently showed `DEF-proxy` with its owned obligations
and three ports, and the same object with its typed uses in a distinct impact view. Tests with a hidden
port, hidden obligations or displaced compartment were rejected. Both views resolved to the same model
object. These are retained historical checks, not additional default native views.

The broad catalogue experiment produced 185 view entries and many incomplete renderings. That
publication policy was rejected and replaced by the explicit subset above. Its archived results remain
diagnostic evidence and do not define the current navigation or view count.

Historical evidence locations in the owning checkout:

| Experiment | Local receipt/evidence directory |
| --- | --- |
| Initial publication and contract update | `.tmp/syson/e7fe1b0e920010a995f3/` |
| Separated contract and impact | `.tmp/syson/a639e56616973ddfefea/` |
| Broad catalogue and deterministic-order correction | `.tmp/syson/f35a774cadddd7a1ebce/` |

## Compatibility findings

1. SysON did not infer types on two bound system references. Explicit `PolicyProxy` and
   `DisposableCache` types preserved them in both engines; the comparison rejects their loss.
2. Requirement identifiers can serialize as `reqId`. Semantic `elementId`, persistence IDs and
   representation IDs differ; the receipt records correspondence.
3. The layout API can ignore geometry when supplied an arbitrary cause. Cause `layout` persisted
   changes in the tested release. Native compartment headers require space, and reopening can measure
   text and resize boxes; checks preserve meaningful placement and containment.
4. Top-level part/actor composition defaults differ. The bounded comparison checks composition within
   part owners and excludes those package/actor defaults.
5. Text export omitted Dependency declarations despite their presence in the model. Exported behavioral
   text also failed the pinned source parser. Do not replace authored source with that export.
6. Derived verification getters are incomplete and a verification-membership kind default differs.
   Explicit objective/reference-subsetting and subject-value paths survived and are checked separately;
   this proves retained references, not equivalent verification interpretation.
7. General View omitted some verification and sequence content. Test the appropriate renderer before
   generalizing that limitation: the intake FlowUsage connections work in Interconnection View.
8. Imported comments were explicitly added from the view's owning presentation package. Multi-target
   `about` references produced import errors in the trial; annotation membership stays in the shared SVG.
   Native note labels center vertically and captions have a minimum height of 70 after reopening.
   A separate caption keeps text above the actual parts. Selecting an enclosing note raises it over
   its contents; clicking blank canvas restores normal part selection. These are native interaction
   and styling differences, not extra model composition or a loss of selected content. Native comment
   markers, folded corners and solid outlines remain; matching colours does not imply pixel-identical
   SVG and native notation.

9. Interconnection View did not draw the contained `L-cached-content` ItemUsage. Exposing it also
   caused native appearance refreshes and palette retrieval to fail in the trial, despite success
   responses from appearance mutations. Keeping the item in the full imported model while omitting
   its unsupported native exposure restored saved colours and normal part palette interaction.
   The explicit `rendering_gaps` entry is restricted to this selected item kind; verification still
   rejects any missing visible part, flow, colour or boundary member. Remove/retest the exception if
   a later renderer supports the item. System Overall's exposure and presentation are unchanged.

This evidence does not establish lossless textual round trips, behavioral execution, simulation or
bidirectional synchronization. Recheck the version profile before upgrades or broader language use.
See the [earlier product/model verification](verification.md) for the separate implementation checks.
