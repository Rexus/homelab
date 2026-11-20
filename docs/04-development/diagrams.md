# Diagram conventions

Diagrams answer one question: placement, containment, interaction or deployment
progress. The [platform map](../01-architecture/README.md#functional-structure) owns
capability placement; domain designs expand it without changing tier or network
ownership. Deployment views show the capability added by a step, not a new architecture.

## Table of contents

- [Layout](#layout)
- [Sequence interactions](#sequence-interactions)
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

Block and flowchart figures use `Arial, sans-serif` at 14px. Set `fontFamily` at the configuration
root as well as in `themeVariables`, with `themeVariables.fontSize: "14px"`; the root setting also
governs HTML labels. [2][5] Theme-aware sequence and chart views retain their background-specific colours.

## Sequence interactions

Arrange participants from consumer to supporting service or authority across the page, with time
advancing downward. Label solid `->>` request arrows and dashed `-->>` response arrows, retaining
the actual direction of each exchange.

Group phases with lightly shaded `rect` regions and theme-aware text. Show authentication and the
consuming service's local authorization as separate decisions. Choose participants and exchanges
for the actual integration's protocol contract. Reuse the
[identity Service access sequence](../01-architecture/09-identity/README.md#service-access).

## Compact block composition

Use one visual language for architecture, deployment and operating views. Compose from the inside out:

Choose boundaries by the question in every diagram. Service and traffic views show the relevant zones,
networks and VM/container/Kubernetes runtimes. Omit a generic Proxmox-host wrapper when physical placement
does not explain the picture. Show named hosts for placement, host failure, capacity, storage attachment
or device passthrough; a deployment view does not automatically need the physical hosting layer.
Code and workflow views use their relevant module, authority or process boundaries instead.

### Keep labels simple

Name what each box represents with a short noun phrase. A tier boundary says `Tier 2`; a network says
`Cache Edge Network / external_edge`; the functional group inside says `Cache Services`.
Retain an exact IaC key, namespace, service or interface name when it helps readers find the configuration.
Identify each runtime deployment explicitly: `Tier 0 Kubernetes`, `Tier 1 Kubernetes` or `Tier 2 Kubernetes`.
Use the owning deployment's name consistently across design, deployment and operations.

Do not pad titles with ownership explanations, instance counts, deployment status, step numbers or
phrases such as "two existing VMs". Describe those details in the caption or nearby inputs when needed.
The instances drawn illustrate the referenced configuration; their number does not define the capability.
Keep names and counts on individual instances or concise aggregates when they are the figure's subject.
Retain contract details such as quorum or offline custody where they explain behavior, rather than
repeating them on every enclosing box. Name arrows by the interaction, such as `Proxy requests`.

### Arrange the groups

| Level | Placement | Visual treatment |
| --- | --- | --- |
| Servers, pods and replicas | Compact vertical stacks | Similar instance rectangles inside a dotted service group |
| Peer service groups | Side by side | Consumer on the left; supporting service or authority to the right |
| Zones and ownership boundaries | Stack where the model requires it | Solid outer boundaries; retain Tier 2 above Tier 1 above Tier 0 |
| Gateways and balancers | Close to the peers they connect | Distinct compact shapes; label their actual routing role |

In tiered placement views, Tier 2 is the highest ownership row. Place Internet services, upstream
providers and external clients to its left. Users and tenants enter their target API from the left
of that owner's boundary. Actual Tier 0/Tier 1 consumers remain below a Tier 2 provider and request
it upward. Sequence diagrams retain their chronological axes.

This nesting should produce a compact figure near 4:3. Do not turn every server group into a horizontal
row or spread a small deployment across a wide canvas. Use the project's palette, native component
names and actual containment. The [identity placement](../03-deployment/stage-05-identity/README.md#figure-identity-federation)
is a concrete application; its products and replica counts are not a template for other capabilities.

An operations capability guide opens with the complete selected deployment, before task navigation or
long input lists. Smaller diagrams later explain a particular task, failure or recovery path. A focused
runbook can point back to that overview instead of repeating the entire deployment. Match the operating
view to the accepted deployment and link its owning inputs; an installation sequence is not a runtime map.

Render before accepting the layout. Nested Mermaid directions can be overridden by external links:
confirm that replicas actually stack, peer groups actually read left to right, titles remain visible and
the figure stays readable at normal and narrow widths. A near-4:3 canvas alone does not prove compactness.

Review the picture as a reading task: trace its main path without jumping around the page. Keep connector
labels beside their own lines and leave space between headings, child boxes and unrelated links.
Long perimeter detours, several competing paths or health/recovery arrows crowding a retention view
are reasons to split the questions into focused figures. Remove enclosing boxes that add no useful
ownership, runtime or failure boundary. Palette, parsing and collision checks supplement this visual review.

When a placement row needs a non-semantic layout wrapper, use an empty `Layout` subgraph with
`style Layout fill:none,stroke:none`. It supplies placement only; it is not an ownership or network
boundary. Keep all visible components and groups on the shared palette.

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

When a higher tier serves lower-tier consumers, show those callers below it with requests pointing
up to the actual listener. Outbound requests may point left to an external source or upstream proxy.
Keep these peers outside the service's owner; label requests separately from returned responses.
The [cache service view](../05-operations/02-software-intake/README.md#figure-reference-cache-deployment)
shows this placement without changing tier ownership or inventing another routing hop.

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
for example, Kubernetes to the left of directory authority. External clients enter from the left
of the owner's actual interface. An Edge-facing privileged bootstrap
entry does not acquire Tier 2 ownership or a public administrative listener.

Offline root and recovery custody belong at the bottom inside Tier 0's ownership
boundary, but outside connected runtime/Proxmox boundaries. This is not another routed
zone or a formal negative-numbered tier. Signed-object transfers point upward from
custody; chronological ceremony/enrollment workflows can retain their natural sequence.

Deployment steps keep the relevant network and runtime context visible: the owning tier
contains its network zones, VMs and attached local volumes. Include physical hosts only when
the figure explains host-level placement or behavior. Use inventory names for deployed guests.
Show remote archives and independent recovery as
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

The [palette](../08-reference/diagrams/palette.json) defines reusable colours.
The [shared notation](../../architecture/views/notation.json) defines role shapes, model categories and
separate boundary styles. Portable SVGs of the connected model generate their keys from the categories
and enclosures actually displayed. Sequence notation retains lifelines, requests and responses; the same
participant identities bind back to structure. Native SysON presentations retain their renderer's
notation and coverage limits described in the [publication guide](syson.md#ownership-and-limitations).

For software intake, [type-to-role bindings](../../architecture/views/software-intake/roles.json) select
shapes; the shared notation's model categories select colours by native kind and explicit type or element
mapping. The proxy and rebuildable storage are blue logical components. Structural views show the proxy
as a rectangle and storage as a cylinder, with a separate mauve content item inside. Functions/actions
are peach, requirements and use-case intent violet, and verification cases green. These colours identify categories, not deployed
status, durability or passing results. Ports use the beige interface category; a listener part's hexagon
does not change its logical category. External participants stay muted neutral, with the appropriate
human or system actor symbol in use-case views. Physical equipment is warm grey; resource views use
double-outline equipment symbols and explicit backing or attachment relationships.

The builder checks reusable type-to-role shapes before applying category colours. Keep each element's
category consistent across views. Part or item kind alone does not establish software, hardware or
information meaning; use the explicit classification in the shared notation. Tier and zone classifications
use light dashed frames, networks solid pale grey-rose enclosures, runtime containment solid blue-grey
enclosures, and explanatory groups dotted neutral outlines. These view-local frames do not create parts,
allocations or network permissions. A physical storage device remains distinct from the virtual cache it backs.

Other capability diagrams use the palette roles below. Each Mermaid fence carries its own `classDef`
declarations so it remains portable; the documentation tests compare those declarations with the palette.

| Role | Treatment |
| --- | --- |
| Tier boundaries | Pure gray with `tier2` lightest, `tier1` medium and `tier0` strongest, consistent across figures |
| Other ownership boundary | Warm neutral gray `ownership`, independent of network protection zones |
| Protection zones | Light rose `zoneEdge`, medium blue `zoneServices`, stronger green `zoneControl`; separate from tiers |
| Site or ownership boundary | Warm neutral enclosing box, solid border |
| Network or subnet | Pale gray-rose `network`, solid border, useful input key in its short heading |
| Kubernetes runtime | Pale blue-gray `kubernetes`; contained inside its owner and actual network |
| Traffic interface | Warm beige `traffic` with dark text for ingress, gateways, VIPs, balancers and listeners |
| Policy / access rule | Mauve `policy`, dashed border; permitted traffic, authorization constraints or named policy resources |
| Action / approval | Pale peach `action`; workflow activity, distinct from deployed service instances |
| Inner function / service group | Light neutral gray `group`, dotted border inside its actual owner, zone or runtime |
| Logical deployment grouping | Light neutral gray `deploymentGroup`, dotted border; groups services without inventing a network |
| Replica / failover group | The same dotted light gray `replicas`; labels state the replication or failover contract |
| Boundary heading | Native title or content-sized unframed heading above its children, not a grid spacer row |
| Functional components | Preserve the component's rose, blue or green role; do not reuse zone fills for every child |
| Other runtime | Declared runtime treatment; Kubernetes always uses its dedicated blue-gray role |
| Offline custody / recovery | Amber, outside connected runtime boundaries |
| Data store | Violet; database or storage shape; durability and custody remain explicit |
| Client or external peer | Muted neutral box, explicitly labelled |

Colour distinguishes roles, not products or a universal tier classification. These are project conventions,
not standard SysML colours. Keep labels/shapes and a legend; the
[software-intake model guide](../01-architecture/07-software-intake/02-connected-model.md#read-the-colours)
explains the standards boundary and its sources.
For example, Tier 2 includes both DMZ entry points and Services workloads.
Labels, containment, shapes and line styles carry the same meaning without colour.
Gateways should sit near the boundary and peer they connect to.
Actual network boundaries share the same rose treatment across tiers and capabilities.
Protection-zone maps use the separate Edge, Services and Control palette roles.
Service collections use dotted outlines. Hosts, network boundaries and Kubernetes runtimes use solid outlines.
Distinguish the rule from its implementation. Put a traffic-rule annotation beside the incoming path,
outside the destination tier, zone and runtime. Point its dashed association directly to the actual
ingress or listener; placement does not assign policy ownership or add a traffic hop.
Keep ingress controllers, gateways and firewall appliances where they run.
Native policy resources such as NetworkPolicy, RBAC or an Argo CD
AppProject stay inside their configured runtime. Workflow approval decisions retain the peach action role.
Use a dotted deployment grouping for a functional collection such as Identity services; label only actual
network boundaries as networks. Stack an application's state beneath it when this keeps its attachment
clear. Offline custody remains at the bottom of its owner, outside connected runtimes.

Policy and health matrices retain their explicit green/amber/red legend. Their cells express
policy or severity, while coloured row and column headings identify the corresponding zones.

Use paired opaque fills and dark foregrounds for boxes. Flowcharts use a fixed
base theme with mid-tone connectors and pale edge-label backgrounds; charts and
sequences retain theme-aware axes and text. Mermaid's theme variables and classes
provide these native controls. [2]

In block and flowchart views, solid directional arrows represent traffic or a named
interface. Dashed, labelled arrows represent trust or another logical relationship. Double-headed arrows
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

SVG figures such as the [identity operating view](../08-reference/diagrams/identity-operations.svg)
are normally their own editable source. The two software-intake views are generated exceptions:
edit their [model and layout sources](../01-architecture/07-software-intake/02-connected-model.md), then run
the native build and snapshot checks. Explicit coordinates preserve required placement across renderers;
open the SVG in a browser or vector editor and inspect it at normal/narrow widths on both backgrounds.

The [bootstrap views and navigation runbook](../08-reference/diagrams/bootstrap-use-case.md)
connects the focused actor goal to the foundation figure and its shared rendering procedure.

The [availability storyboard](../08-reference/diagrams/availability-cases.svg) shows independent
before/during/after cases in rows. Read each row left to right; do not infer a single deployment
or additional running replica from an incoming migration target.
Keep its semantic colours aligned with the palette. Register new diagram assets with the documentation
generator so the generated manual carries the same image; geometry checks protect critical placement.

The [cache operating view](../05-operations/02-software-intake/README.md#figure-reference-cache-deployment)
is the reference for compact service grouping and inbound/outbound request placement.
A Mermaid 11.17.2 `block-beta` trial stretched peer cells, obscured group titles and routed the upstream
arrow through the VIP. Its separate SVG layout source preserves the required placement. Use Mermaid when its rendered
layout expresses the same relationships clearly.
Scope SVG palette rules to single semantic classes. Shared outline resets affect dash patterns only.
Check computed fills, foregrounds and borders in the browser to catch inherited colour overrides.

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

Mermaid syntax, theming and configuration sources checked 2026-11-14; CLI checked 2026-11-13;
contrast reference checked 2026-10-19.

1. [Mermaid: Block diagrams](https://mermaid.js.org/syntax/block.html)
2. [Mermaid: Theming](https://mermaid.js.org/config/theming.html)
3. [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)
4. [W3C: Understanding contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
5. [Mermaid configuration schema: fontFamily](https://mermaid.js.org/config/schema-docs/config.html#fontfamily)
