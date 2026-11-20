# Review the homelab model in SysON

Git holds the accepted model baseline. The normal SysON publication contains **two compact views**:
[System Overall](../../architecture/views/system-overall.svg) and
[software intake](../../architecture/views/software-intake/logical.svg).
The styled SVGs remain the portable repository presentation of those selections.

The broader [engineering catalogue](../../architecture/views/README.md) is available in Git.
Only the explicit `publication_views` list in
[`architecture/views/syson.json`](../../architecture/views/syson.json) is published to SysON.
Adding an SVG, report, page or catalogue entry does not add a native view.

## Contents

- [Prepare](#prepare)
- [Publish and browse](#publish-and-browse)
- [Change the model](#change-the-model)
- [Return requirement/use-case edits](#return-requirementuse-case-edits)
- [Repeat and recover](#repeat-and-recover)
- [Ownership and limitations](#ownership-and-limitations)
- [References](#references)

## Prepare

Run SysON `eclipsesyson/syson:v2026.11.0` with its PostgreSQL data in a persistent volume.
The default address is `http://localhost:8080`; `--url` selects another server explicitly.
The publisher does not install SysON or change access controls.

From **the upstream homelab checkout**, install the declared Python dependencies:

```bash
python -m pip install -r tests/requirements.txt
```

Prepare the pinned Java and SysML Pilot tools using
[Build and check](../01-architecture/07-software-intake/02-connected-model.md#build-and-check).
Set `SYSML_JAVA`, `SYSML_KERNEL` and `SYSML_LIBRARY` to their installed locations.
A missing tool or invalid model stops publication before project creation. The declared WebSocket
client keeps SysON's native editing context and both diagram subscriptions active during publication;
HTTP success alone is insufficient. The adapter still verifies the saved state before accepting it.

## Publish and browse

From **the upstream homelab checkout**, with the tool variables set:

```bash
python scripts/architecture/syson.py publish
```

Alternatively, pass `--java /path/to/jdk/bin/java`,
`--kernel /path/to/jupyter-sysml-kernel-0.63.1-all.jar` and `--library /path/to/sysml.library`.

**Expected:** a `Homelab review - <revision>` project containing the full model and exactly two
representations. The command prints both view URLs and a linked coverage report.
Open those links, or browse `Views` and its `software-intake` package.

| View | Native presentation | Selected content |
| --- | --- | --- |
| System Overall | General View | The accepted five subsystems, four dependencies and saved placement. |
| Software intake | Interconnection View | Seven parts/reference roles, three nested client references and three actual flows. Update Consumers contains its three client groups; the proxy, cache and external source role remain individually inspectable. |

The intake diagram selects the same identities and relationships as `logical.svg`; the release-specific
item omission below remains visible in coverage. SysON shows flow
endpoints as small ports; the SVG attaches those same connections to box boundaries. Repeated port
captions and unrelated compartments are hidden. The original semantic ports and flows remain intact.
Tier 2 and Edge/DMZ appear as lightly coloured native comment enclosures around the same proxy and cache
selected by the SVG. They are annotations in the `Views/software-intake` presentation package, with
no owned parts or network enforcement semantics. Interconnection View supports the nested parts,
connections and comment annotations needed by this picture. [1]

Cache storage and stored data are distinct in the model. The blue `L-Cache` part is rebuildable
storage, while `L-cached-content` is an item typed by the shared `DEF-cached-content` definition.
The SVG shows that item in the information colour inside storage. SysON 2026.11 imports its kind,
ownership and type, but Interconnection View does not render the contained item. The view therefore
has an explicit `rendering_gaps` entry for that ItemUsage and its containment. It does not substitute
a part or comment for the data. The exception preserves checks on all visible parts and flows;
coverage continues to report the missing item and relationship. The unsupported item is omitted from
native view exposures because exposing it coincided with failed appearance refreshes in the earlier test.
A later supported-only model also encountered a transient server event-processor failure; therefore
appearance failure alone does not prove that the item is its cause.
It remains in the complete imported model. Recheck this limitation on upgrades.

The publisher reads each enclosure's label, members and nesting from the SVG; `syson.json` supplies
native geometry and the explicit colour-profile choice. Each boundary uses a frame comment and a borderless caption
comment because this release centers note text vertically. This preserves readable headings above the
parts without changing the architecture. Native comments retain SysON's folded-corner notation and
comment marker, so the presentations share content rather than identical styling. Native note
captions reserve the tested minimum height of 70, including after the browser measures their labels.
Selecting an enclosing note brings it to the front in SysON; click blank canvas before selecting a
part inside it. Normal part selection and the model's ownership are unaffected.

Reusable boundary treatments live in [the project notation](../../architecture/views/notation.json):
tier, zone, network, runtime, group and subject. Component categories use the linked
[palette](../08-reference/diagrams/palette.json). These are reusable visual definitions; each frame
keeps its view-local placement and selected members. Actual components reuse their SysML identity.
A frame with the same tier or zone label is not itself a shared model component or proof of the same
network. Model an actual network or enforcement mechanism once when its engineering meaning is needed,
then reference that identity across views.

Software intake opts into `colour_profile: shared-notation`. Both renderers consume the same role
definitions for fills, borders, text and connectors: logical components are blue, external roles are
muted grey, and tier/zone enclosures use their separate pale boundary colours. No colour values are
copied into the native layout configuration. System Overall retains its accepted native appearance.
The publisher checks stored colours on first and repeat publication, and the live view was inspected
to confirm that coloured note fills leave all three flows visible. Native shapes and line patterns
remain SysON's presentation of the shared content.

On 2026.11, explicit multi-target `comment ... about ...` references produced import errors, and
view-owned imported comments did not appear through the tested drop operation. The adapter instead
imports comments into the view's owning presentation package and explicitly adds them to that diagram.
The shared SVG remains authoritative for annotation membership; no `about` or composition links are
invented as a workaround. Check this release-specific behavior again when upgrading.

Select a part to inspect its Details. Adding an existing element to a diagram changes its presentation;
creating a new part changes the model. [2] SysON edits can originate proposed model changes, but the
current publisher does not bring them back into Git automatically. Follow the
[model development workflow](model-change-workflow.md) to preserve and reconcile those changes into
the owning Git sources, implementation and verification before publishing again.

Publication performs these checks:

1. Build the full native model, including selected IaC realization and SVG projections.
2. Read the explicit native publication subset from the shared catalogue. Unknown, empty or duplicate
   selections fail; there is no fallback that publishes the entire catalogue.
3. Assemble native view usages under `Views`, preserving their Design-owner hierarchy, and validate
   the complete bundle with the pinned native parser.
4. Import one document into a new revision project and compare stable identities, ownership, typing,
   documentation, bindings and supported relationship endpoints against the native source.
5. Create each selected native representation using its appropriate view definition. Save placement
   and visibility, then check nested containment, flow endpoints/direction and persisted geometry.
   Validate annotation kinds, captions, enclosure membership, nested boundary placement and shared colours.
6. Record gaps honestly and save a receipt, project ZIP, comparisons and coverage report under
   `.tmp/syson/`. Publish the portable report under `architecture/test/`.

See the [current coverage report](../../architecture/test/syson-view-coverage.md) and
[verification record](../01-architecture/07-software-intake/syson-verification.md).
System Overall intentionally retains its accepted presentation: the SVG system boundary has no
matching enclosing native frame. That boundary difference remains an explicit coverage gap.
Intake parts, nested references, flows, colours and explanatory boundaries match. Its cached-content
item and containment remain an explicit native rendering gap; inspect the item in the model explorer
or the portable SVG.

## Change the model

Edit the owning source, preserving its stable short identifiers. For example, change
[PolicyProxy](../../architecture/design/software-intake/policy-proxy/definition.sysml), then run:

```bash
python scripts/architecture/syson.py publish
python scripts/architecture/software_intake.py impact DEF-proxy
```

**Expected:** the changed model imports into a new revision with the same two selected views.
The impact query identifies consumers and related functions, scenarios, realization and verification.
Inspect the definition and its typed uses through model Details and repository links.
Contract and impact remain separate concerns; neither is added as another native view automatically.
The earlier contract-change test is recorded in the verification evidence.

To publish an additional engineering view deliberately, add its existing catalogue key to
`publication_views`, choose an appropriate native renderer/layout, and verify the resulting picture.
Keep each view focused on a distinct engineering question. Native layout configuration refers to the
shared selection; it must not introduce a second inventory of model content.

## Return requirement/use-case edits

SysON may originate proposed requirement and use-case changes while Git holds the accepted baseline.
Follow [the change workflow](model-change-workflow.md#bring-a-syson-change-back) to capture an edited
publication, review its validated source diff and apply it without committing. Keep its receipt and
immutable `return-baseline.json` / `.zip`. Do not run publication over unreconciled tool changes.

The return adapter supports a checked subset, not arbitrary model synchronization. The
[tested return slice](../01-architecture/07-software-intake/syson-return-verification.md) includes existing
intent edits, new linked intent, conflict refusal and repeat application. Uncovered requirements stay
visible in the intent inventory without creating extra diagrams or claiming passing tests.

## Repeat and recover

Publishing identical inputs with the same server and `--name` reuses the verified receipt and rechecks
the stored model, visible content and placement. It must not create another project. A changed source,
layout or adapter creates a new revision. `--name "Homelab experiment"` starts a separate review series.
If the stored snapshot was edited, reuse reports drift instead of overwriting it.

A failed import or comparison leaves its project and receipt for diagnosis. Inspect
`.tmp/syson/<run>/receipt.json`; do not repeatedly upload into the same populated project.
The publisher itself never deletes projects. Return review archives and removes only its own
uniquely named temporary semantic-check project. Retire superseded generated projects after exporting and
checking their current ZIP archives; retain original user projects and needed review evidence.

Project ZIPs preserve model and representation state. Text exports do not preserve the whole project. [3]
Back up the persistent database for ongoing work. `.tmp/` is ignored local evidence: copy required
archives to a durable backup before clearing it. Reconcile meaningful SysON edits into the authored
model before replacing a snapshot; do not replace the repository with its text export.

## Ownership and limitations

| Artifact | Owning source |
| --- | --- |
| Semantic model and implementation traces | `architecture/` sources and native build |
| Overall selection and placement | `architecture/views/system-overall.json` |
| Selected native views, geometry and colour-profile opt-in | `architecture/views/syson.json` |
| Shared visual roles, boundary treatments and colours | `architecture/views/notation.json` and its linked palette |
| Shared view identities and selected content | Renderer declarations compiled into `architecture/views/catalog.json` |
| Portable SVG presentation | `architecture/views/`, following Design ownership |
| Import, placement and repeat-publication checks | `scripts/architecture/syson*.py` |
| Current correspondence and rendering gaps | `architecture/test/syson-view-coverage.json` and `.md` |
| Snapshot IDs and native review state | SysON project and local receipt/archive |

SysON 2026.11 General View does not render all imported verification and sequence content. That finding
does not apply indiscriminately to every renderer: the actual intake flows work in Interconnection View.
Test the appropriate native renderer before declaring an unsupported kind or proposing an extension.

The tested text exporter omitted Dependency declarations, and behavioral text did not pass the source
parser unchanged. Verification checks prove preservation of explicit objective/reference and
subject-value paths; incomplete derived getters prevent claiming equivalent verification semantics.
These checks establish neither lossless round trips nor behavioral execution or live infrastructure
operation. Git remains authoritative. SysON's REST API is partial; import and representation operations
use the installed GraphQL API. [3][4]

Run focused checks from **the upstream homelab checkout**:

```bash
python -B -m unittest discover -s tests -p 'test_tier_syson*.py'
python -B -m unittest discover -s tests -p test_tier_view_catalog.py
```

## References

Checked against SysON 2026.11.0 on 2026-11-19.

1. [Interconnection View](https://doc.mbse-syson.org/syson/v2026.11.0/user-manual/features/interconnection-view.html).
2. [General View](https://doc.mbse-syson.org/syson/v2026.11.0/user-manual/features/general-view.html).
3. [API cookbook: import, archives and export](https://doc.mbse-syson.org/syson/v2026.11.0/developer-guide/api/api-cookbook.html).
4. [API availability and limitations](https://doc.mbse-syson.org/syson/v2026.11.0/developer-guide/api/api.html).
