# Diagram conventions

Diagrams answer one question: placement, containment, interaction or deployment
progress. The [platform map](../architecture/README.md#functional-structure) owns
capability placement; domain designs expand it without changing tier or network
ownership. Deployment views show the capability added by a step, not a new architecture.

## Table of contents

- [Layout](#layout)
- [Abstraction and implementation](#abstraction-and-implementation)
- [Boundaries and colour](#boundaries-and-colour)
- [Verification](#verification)
- [References](#references)

## Layout

| Question | Mermaid form | Convention |
| --- | --- | --- |
| Where does a capability belong? | `block-beta` | Explicit columns, spans and empty cells; Tier 2 above Tier 1 above Tier 0 |
| Which networks or layers contain it? | Block grid or nested flowchart | Edge / DMZ on the left, Application / Services in the middle, Control on the right |
| What contains or consumes a service? | Nested flowchart | Trust boundary around zones; runtime and replica groups inside their actual owner |
| How does a request proceed? | Flowchart or sequence | Arrows describe real interactions; sequence diagrams retain chronological order |
| What does a deployment step add? | Content-sized nested flowchart | Retain tier, host/VM and storage boundaries; distinguish existing components from additions |

Block diagrams support explicit placement through columns, spans and spaces. [1]
Use them for matrices and placement maps. Keep a flowchart when routing and nested
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

Use short, wrapped labels. Separate dense placement and interaction questions
instead of shrinking one diagram until its text becomes unreadable.

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

## Boundaries and colour

The [palette](../reference/diagrams/palette.json) defines reusable visual roles.
Each Mermaid fence carries its own `classDef` declarations so it remains portable;
the documentation tests compare those declarations with the palette.

| Role | Treatment |
| --- | --- |
| Site, network or ownership boundary | Pale neutral enclosing box, solid border |
| Boundary heading | Native title or content-sized unframed heading above its children, not a grid spacer row |
| Edge / DMZ | Rose zone or capability |
| Application / Services | Blue zone or capability |
| Control | Green zone or capability |
| Nested control runtime | Related teal shade; for example, Kubernetes inside Tier 0 |
| Offline custody / recovery | Amber, outside connected runtime boundaries |
| Persistent data | Violet; database or storage shape where useful |
| Replica group | Pale inner box with dashed border and compact peer instances |
| Client or external peer | Muted neutral box, explicitly labelled |

Colour distinguishes roles, not products or a universal tier classification.
For example, Tier 2 includes both DMZ entry points and Services workloads.
Labels, containment, shapes and line styles carry the same meaning without colour.
Gateways should sit near the boundary and peer they connect to.

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
   links. Refresh must preserve project-owned records and locally edited files.

Palette tests require at least 4.5:1 contrast between box text and its fill, following
the normal-text threshold. [4] This is a colour-pair check, not a claim that all
renderers or complete diagrams meet accessibility requirements.

## References

Sources checked 2026-10-19.

1. [Mermaid: Block diagrams](https://mermaid.js.org/syntax/block.html)
2. [Mermaid: Theming](https://mermaid.js.org/config/theming.html)
3. [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)
4. [W3C: Understanding contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
