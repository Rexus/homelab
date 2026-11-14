# Diagram conventions

Diagrams answer one question: placement, containment, interaction or deployment
progress. The [platform map](../01-architecture/README.md#functional-structure) owns
capability placement; domain designs expand it without changing tier or network
ownership. Deployment views show the capability added by a step, not a new architecture.

## Table of contents

- [Layout](#layout)
- [Compact block composition](#compact-block-composition)
- [Abstraction and implementation](#abstraction-and-implementation)
- [Boundaries and colour](#boundaries-and-colour)
- [Verification](#verification)
- [References](#references)

## Layout

| Question | Mermaid form | Convention |
| --- | --- | --- |
| Where does a capability belong? | `block-beta` | Explicit columns, spans and empty cells; Tier 2 above Tier 1 above Tier 0 |
| Which networks or layers contain it? | Block grid or nested flowchart | Edge / DMZ on the left, Application / Services in the middle, Control on the right |
| What contains or consumes a service? | Grouped block view or nested flowchart | Trust boundary around zones; runtime and replica groups inside their actual owner |
| How does a request proceed? | Flowchart or sequence | Arrows describe real interactions; sequence diagrams retain chronological order |
| What does a deployment step add? | Content-sized nested flowchart | Retain tier, host/VM and storage boundaries; distinguish existing components from additions |

## Compact block composition

Use one visual language for architecture, deployment and operating views. Compose from the inside out:

| Level | Placement | Visual treatment |
| --- | --- | --- |
| Servers, pods and replicas | Compact vertical stacks | Similar instance rectangles inside a dashed service group |
| Peer service groups | Side by side | Consumer on the left; supporting service or authority to the right |
| Zones and ownership boundaries | Stack where the model requires it | Solid outer boundaries; retain Tier 2 above Tier 1 above Tier 0 |
| Gateways and balancers | Close to the peers they connect | Distinct compact shapes; label their actual routing role |

This nesting should produce a compact figure near 4:3. Do not turn every server group into a horizontal
row or spread a small deployment across a wide canvas. Use the project's palette, native component
names and actual containment. The [identity placement](../03-deployment/stage-5-identity/README.md#figure-identity-federation)
is a concrete application; its products and replica counts are not a template for other capabilities.

An operations capability guide opens with the complete selected deployment, before task navigation or
long input lists. Smaller diagrams later explain a particular task, failure or recovery path. A focused
runbook can point back to that overview instead of repeating the entire deployment. Match the operating
view to the accepted deployment and link its owning inputs; an installation sequence is not a runtime map.

Render before accepting the layout. Nested Mermaid directions can be overridden by external links:
confirm that replicas actually stack, peer groups actually read left to right, titles remain visible and
the figure stays readable at normal and narrow widths. A near-4:3 canvas alone does not prove compactness.

### Start with the result

Capability guides show the opening figure immediately after a short introduction,
before long prerequisites, contents or configuration tables. Deployment shows the expected
result; operations shows the complete selected deployment. Give that picture a
stable figure anchor and a descriptive caption. Refer to it from the actions that
create, configure or verify its components.

When a later section adds a substantial capability, put its result figure at the
start of that section. A reader should see the enhancement before its installation
commands. Keep the base result and selectable alternatives separate; a small
reusable procedure can refer to its caller's figure instead of repeating it.

Architecture follows a related reading path: show the capability, explain how its
participants communicate, then describe decisions and failure boundaries. Place
detailed input/source links beside the relevant detail, after the explanation.
Use block views for placement and sequence diagrams for request/response behavior;
avoid an introductory catalog of links standing in for either explanation.

### Read toward the dependency

Use left-to-right flow for ordinary communication and dependencies: consumer on the
left, provider or supporting authority to its right. Preserve higher-priority
ownership, tier and protection-layer placement rules. Returned results, alerts and
offline trust transfers retain their actual direction rather than being reversed
to satisfy the page layout. Sequence participants follow the same consumer-to-provider
order across the page; time still advances downward.

Block diagrams support explicit placement through columns, spans and spaces. [1]
Use them for placement maps and compact hosting views. Keep a flowchart when routing and nested
relationships are clearer there. Nested headings and subgraph directions still
need a render check; source order alone does not prove the resulting layout.

Do not use grid spacer cells or full-width heading rows to size unequal nested
deployment groups. They can stretch unrelated rows and shrink readable labels.
Use native subgraph titles and content-sized groups for these views; keep spacing
small and verify the rendered bounds rather than treating successful parsing as acceptance.
If external group links obscure a nested title, isolate the content direction in
an unframed placement group and give the boundary a compact, unframed heading.

Do not add traffic arrows merely to enforce placement. Invisible flowchart links
may constrain layout, but convey no dependency. A layer sequence is not a firewall
allow rule, and tiers are ownership boundaries rather than a network path.

Compact boundaries from the inside out: stack the smallest peer boxes vertically
when that reduces width and whitespace, for example a directory primary above its
replica or diagnostic components inside one runtime. Keep labels and connectors
readable and larger service boundaries in their intended left-to-right order;
not every child group needs a horizontal row.

When physical hosting is in scope, show Proxmox/hypervisor hosts as the foundation:
beneath their hosted systems in a hosting view, or to the right of dependent
services in an interaction view. Do not move the host left merely because it
produces metrics; the actual telemetry can flow left toward a collector.

Place administrators and readers to the left of the systems they access. A query
arrow enters the system; an unsolicited alert or heartbeat can correctly travel
right-to-left. Keep independent critical monitoring to the right of observed systems,
and keep human recipients outside external notification-service boundaries.
Earlier deployment alone does not establish greater authority: verify actual
bootstrap/recovery dependencies before using foundational placement.

Within one tier, review the consumer/provider pair, not only the arrow direction.
Place a delivery controller left of its authoritative inputs, and the control cluster
left of dedicated infrastructure execution. Input delivery can point left while
scoped requests point right. Keep explicitly chronological workflows in sequence.

Use short, wrapped labels. Separate dense placement and interaction questions
instead of shrinking one diagram until its text becomes unreadable.

Aim for a rendered width-to-height ratio near **4:3**, suitable for a figure and
its explanation on the same book or printed page. This is a composition target,
not a fixed canvas: rearrange or split dense views rather than stretch the image,
add empty padding or shrink labels. Small workflows can remain naturally wider.
Review the rendered figure, not only its source, at the intended reading size.

Wrap long chronological workflows into a serpentine (snake) layout: left-to-right,
down, then right-to-left, repeating as needed. Use numbered steps and arrows at row
turns so the continuation is unambiguous. Keep rows compact instead of shrinking a
single long strip. This is a sequence convention, not a reversal of tier/layer placement.

Use one enclosing boundary per tier in a view; place that tier's zones and runtimes
inside it. More foundational or privileged dependencies belong lower or farther right:
for example, Kubernetes to the left of directory authority. Clients enter from Tier 2
above or from an external access area on the left. An Edge-facing privileged bootstrap
entry does not acquire Tier 2 ownership or a public administrative listener.

Offline root and recovery custody belong at the bottom inside Tier 0's ownership
boundary, but outside connected runtime/Proxmox boundaries. This is not another routed
zone or a formal negative-numbered tier. Signed-object transfers point upward from
custody; chronological ceremony/enrollment workflows can retain their natural sequence.

Deployment steps keep the physical and runtime context visible: the owning tier
contains the actual Proxmox hosts, VMs and attached local volumes. Use inventory
names for deployed guests. Show remote archives and independent recovery as
separate boundaries, not another disk inside the receiver. An optional second
host must be labelled optional; adding a replica does not imply replication or HA.

Place direct links to the owning IaC beside each deployment view. Match guest labels
to inventory and hardware keys, and mark existing prerequisites, manual commissioning
and later integrations separately from the resources or configuration that the step installs.

## Abstraction and implementation

Use the same visual language throughout documentation, but keep the level of detail
appropriate to the question. A capability is not a guest, and a deployment stage is not a namespace.

| Document | Boxes represent | Connection to implementation |
| --- | --- | --- |
| Architecture overview/domain | Stable capabilities, authority and interfaces; for example, Tier 0 protected log services | Link to variants and realization guides; no inventory names, VMIDs or site addresses in diagrams |
| Architecture variant/reference | A named hosting or product choice within the parent contract | State the choice explicitly; use roles, not site-specific instance names |
| Deployment | Resources and configuration of the selected implementation, within their actual tier/host/runtime boundaries | Use exact starter inventory keys and replica counts; link inputs and executing code immediately below the diagram |
| Administration | Existing services, data custody and the operation or failure being examined | Reference the selected deployment; distinguish a proposed change from existing resources |
| Development/reference | Code ownership, input contracts or tool behavior | Link the files that implement the illustrated contract |

Each architecture page includes a figure that explains its subject. Introduce the
main visual early, then use the surrounding text for decisions, constraints and
details that the picture cannot express clearly. Add a short italic caption directly
beneath each architecture figure, using `Figure:` or a numbered `Figure 1 -` prefix.
State what it shows and the meaning of its main relationships. Keep source and realization links nearby.

Deployment captions identify **IaC**, **Manual**, **Integration** or **Workflow** scope.
Use an explicit `Project integration` boundary for services without an installer;
an empty manifest folder must not look like a deployed application. Existing and optional
components are labelled in the picture, not only in surrounding prose. A VM baseline
does not install the service shown inside a future integration boundary.

One-to-one correspondence applies to the selected view: every deployed instance shown
has a matching input, and every active instance in the illustrated starter root is accounted for.
Linked alternatives are separate views, not extra components silently deployed together.
Local configuration may change counts or names; the generated project's owned design
records must describe those selections. Upstream diagrams describe the linked examples,
not live-state discovery. Keep source, diagrams and contract tests in the same change.

Keep figure labels stable and clean: omit VMIDs, literal IP/MAC allocations and configured disk/RAM/CPU sizes.
Identify instances by their inventory/resource names and relationships; keep exact IDs in the linked
Terraform inputs or reference tables. One-to-one correspondence uses those resource keys, not a numeric
allocation printed in the picture. Keep interfaces, roles, protocol names and actual containment visible.
A convention figure explaining an allocation format is the reference exception.

## Boundaries and colour

The [palette](../08-reference/diagrams/palette.json) defines reusable visual roles.
Each Mermaid fence carries its own `classDef` declarations so it remains portable;
the documentation tests compare those declarations with the palette.

| Role | Treatment |
| --- | --- |
| Tier boundaries | Warm neutrals: light `tier2`, medium `tier1`, strongest `tier0`; the same shade everywhere |
| Other ownership boundary | Warm neutral gray `ownership`, independent of network protection zones |
| Protection zones | Light rose `zoneEdge`, medium blue `zoneServices`, stronger green `zoneControl`; separate from tiers |
| Site or network boundary | Pale neutral enclosing box, solid border |
| Kubernetes runtime | Pale blue-gray `kubernetes`; contained inside its owner and actual network |
| Traffic interface | Pale cyan `traffic`; ingress, gateways, balancers and routing entry points |
| Action / approval | Pale peach `action`; workflow activity, distinct from deployed service instances |
| Inner function / service group | Light neutral gray `group`, solid border; works inside any owner, zone or runtime |
| Replica / failover group | The same light gray `replicas`, dashed border; labels state the actual contract |
| Boundary heading | Native title or content-sized unframed heading above its children, not a grid spacer row |
| Functional components | Preserve the component's rose, blue or green role; do not reuse zone fills for every child |
| Other runtime | Declared runtime treatment; Kubernetes always uses its dedicated blue-gray role |
| Offline custody / recovery | Amber, outside connected runtime boundaries |
| Persistent data | Violet; database or storage shape where useful |
| Client or external peer | Muted neutral box, explicitly labelled |

Colour distinguishes roles, not products or a universal tier classification.
For example, Tier 2 includes both DMZ entry points and Services workloads.
Labels, containment, shapes and line styles carry the same meaning without colour.
Gateways should sit near the boundary and peer they connect to.
Policy and health matrices retain their explicit green/amber/red legend. Their cells express
policy or severity, while coloured row and column headings identify the corresponding zones.

Use paired opaque fills and dark foregrounds for boxes. Flowcharts use a fixed
base theme with mid-tone connectors and pale edge-label backgrounds; charts and
sequences retain theme-aware axes and text. Mermaid's theme variables and classes
provide these native controls. [2]

Solid directional arrows represent traffic or a named interface; dashed, labelled
arrows represent trust or another logical relationship. Double-headed arrows
require a genuinely bidirectional relationship. Omit connections in placement-only
views rather than implying routes or permissions.

## Verification

1. Run `python -B -m unittest discover -s tests -p test_tier_diagrams.py` for palette,
   placement-source and generated-copy checks. These do not render Mermaid.
   Also run `python -B -m unittest discover -s tests -p test_tier_deployment_views.py`
   for diagram scope and inventory/input correspondence.
2. Render changed fences with the target Markdown renderer or Mermaid CLI. [3]
   Check both light and dark themes on their corresponding page backgrounds.
3. Inspect at the intended reading width: no clipped labels, colliding connectors,
   obscured headings or misleading containment. Confirm actual tier/layer order,
   not only successful parsing. Review at a narrow documentation viewport too.
4. Generate an architecture repository and follow its diagram-guide and palette
   links. Refresh must preserve project-owned records and locally edited diagrams/documentation.

Palette tests require at least 4.5:1 contrast between box text and its fill, following
the normal-text threshold. [4] This is a colour-pair check, not a claim that all
renderers or complete diagrams meet accessibility requirements.

### Export a review copy

With an accepted Mermaid CLI installation, render the Markdown directly; the
native CLI extracts its diagram fences and creates SVGs beside the review copy. [3]
Run from **the upstream checkout**:

```bash
mkdir -p .tmp/diagram-review
mmdc --version
mmdc -i docs/01-architecture/README.md -o .tmp/diagram-review/architecture-light.md -t default -b white
mmdc -i docs/01-architecture/README.md -o .tmp/diagram-review/architecture-dark.md -t dark -b '#0d1117'
```

View the exports at normal and narrow reading widths, such as 1100 and 760 pixels.
Keep the Markdown fences authoritative. For retained exports, record the CLI and
Mermaid dependency versions from the prepared toolchain, browser/fonts, command,
backgrounds, widths and inspected results. A parse pass does not establish correct
placement, and local rendering does not establish GitHub rendering parity.

## References

Mermaid syntax, theming and CLI sources checked 2026-11-13; contrast reference checked 2026-10-19.

1. [Mermaid: Block diagrams](https://mermaid.js.org/syntax/block.html)
2. [Mermaid: Theming](https://mermaid.js.org/config/theming.html)
3. [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)
4. [W3C: Understanding contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
