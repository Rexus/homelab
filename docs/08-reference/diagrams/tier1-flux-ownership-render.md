# Flux diagram views and render record

Start with the Tier 1 ownership view to understand bootstrap, reconciliation and application promotion.
The other views explain the runtime or an independently owned Tier 0 capability.

## Choose a view

| Reader question | Editable source | Read it in context |
| --- | --- | --- |
| Who bootstraps, maintains and reconciles Tier 1, and who promotes applications? | [Tier 1 ownership](tier1-flux-ownership.svg) | [Delivery architecture](../../01-architecture/10-delivery/flux-ownership.md#figure-tier1-flux-ownership) |
| Which Tier 1 node VMs host the selected delivery runtime? | [Tier 1 runtime placement](platform-cluster-runtime.svg) | [Stage 7 expected outcome](../../03-deployment/stage-07-delivery/README.md#figure-platform-runtime) |
| Which platform services and Flux source belong to Tier 0 Kubernetes? | [Tier 0 platform placement](kubernetes-platform.svg) | [Stage 4 platform configuration](../../03-deployment/stage-04-kubernetes/README.md#figure-2-basic-platform-services) |
| How do protected infrastructure execution and Tier 0 recovery fit beside Flux? | [Infrastructure execution](infrastructure-runner-placement.svg) | [Stage 9 runner handover](../../03-deployment/stage-09-development/README.md#figure-infrastructure-handover) |

Each SVG has one current source at the linked path. Refresh copies it into
`<prefix>-architecture/docs/auto-docs/08-reference/diagrams/`. Older `reference/diagrams/` aliases
are retained while project-authored Markdown links use them and are removed when those links move.
Use the numbered `08-reference/` path for new links.

The controller comparison, approval sequence and operating map are editable Mermaid figures in their
owning pages. Their labels and scope follow those pages.

## Contents

- [Previews](#previews)
- [Reproduce](#reproduce)
- [Review and source correspondence](#review-and-source-correspondence)

## Previews

These four PNGs show the same Tier 1 ownership SVG at two reading widths and page backgrounds.
The SVG remains the source displayed in the guide.

| Reading width | Light page | Dark page |
| --- | --- | --- |
| 1100 px | [Preview](tier1-flux-ownership-1100-light.png) | [Preview](tier1-flux-ownership-1100-dark.png) |
| 760 px | [Preview](tier1-flux-ownership-760-light.png) | [Preview](tier1-flux-ownership-760-dark.png) |

## Reproduce

Reviewed 2026-11-14 with Node.js 24.14.1, Playwright `1.66.0-alpha-2026-11-09` and Microsoft Edge
`157.0.4341.46` on Windows, Arial/sans-serif. The SVG has explicit palette colours and coordinates;
no Mermaid dependency is used for the SVG figures. The inline controller/operating diagrams were rendered
with Mermaid `11.17.2`. The page backgrounds are `#ffffff` and `#0d1117`.
The approval-control sequence is included in the same renderer and final review.
The asset audit on 2026-11-15 rendered 28 cases in both upstream and a freshly generated architecture
repository. All 28 preview images and geometry reports matched byte for byte across those runs, with
no SVG text overflow. The four SVG views were visually reviewed at normal and narrow reading widths
on light/dark pages. Long sequence labels are wrapped.
The ownership source is 1200×900; the three placement sources are 960×720. Responsive images have
a 20 px page margin at each review width.

Prepare the same versioned renderer **from the upstream checkout**, using existing Microsoft Edge:

```powershell
npm install --prefix .tmp/tier1-flux-render-tools --no-save playwright@1.66.0-alpha-2026-11-09 mermaid@11.17.2
$env:DIAGRAM_PLAYWRIGHT = (Resolve-Path .tmp/tier1-flux-render-tools/node_modules/playwright).Path
$env:DIAGRAM_MERMAID = (Resolve-Path .tmp/tier1-flux-render-tools/node_modules/mermaid/dist/mermaid.min.js).Path
node docs/08-reference/diagrams/render-tier1-flux.cjs
```

In a generated collection, run the same dependency setup from **`<prefix>-architecture/`** and use
this renderer command instead.

```powershell
node docs/auto-docs/08-reference/diagrams/render-tier1-flux.cjs
```

[Rendering source](render-tier1-flux.cjs) exports the four previews and writes geometry, computed
palette, font and browser information to `.tmp/tier1-flux-render/report.json` beneath the working
directory. It resolves SVG and Markdown sources beside its own copied location. The reviewed run reused
an already installed copy of that exact Playwright version. Headless Edge required execution outside
the restricted sandbox; the first restricted launch failed before rendering. Hosted Markdown/GitHub
parity was not tested.

The Mermaid bundle SHA-256 was
`581ed7d74bd9048d0e3a91363927d72ef22942d7722546b27f7cc29e35390eb8`.
All four SVG views and the three inline Mermaid figures are checked at both widths and backgrounds,
giving 28 renders when `DIAGRAM_MERMAID` is set. Placement, controller, approval and operating previews
are temporary outputs under `.tmp/tier1-flux-render/`; the retained four PNGs above are regenerated
from the ownership SVG.

## Review and source correspondence

The selected view accounts for bootstrap, separate sources, Flux identities, platform services,
promotion Jobs, application namespaces, persistent state and independent custody. Tier 2 is separate
optional integration; Tier 0 has its own Flux/infrastructure owners. Placement implies no API access.

| Unit or flow | Source / contract |
| --- | --- |
| Bootstrap Cilium/Flux, exact RBAC/canary source | Shared `cluster_platform` tasks `tier1-gitops.yml`, templates `tier1-bootstrap.yml.j2`, `tier1-sources.yml.j2`; Tier 1 inputs |
| Platform/app identities and source separation | Same bootstrap/source templates; application RoleBindings and separate scoped source credentials |
| Flux2 self-management and service graphs | `platform-base` export plus Shared `flux_payload`; preserved Helm identities; selected native product renderers |
| Spinnaker and Job-only application promotion | `delivery_platform` Flux accounts; Tier 1 `delivery_promotion`, pipeline definitions and promotion worker |
| External maintenance / retained inputs | Shared `flux_maintenance`, `flux_recovery_git` and Tier 1 `scripts/flux-recovery.py`; source advancement and recovery custody |
| Persistent state | Native product restore procedures; Flux reconstructs resources, not their contents |
| Tier 0 / Tier 2 | Existing infrastructure/control-service ownership / separately approved Tier 2 integration |
| `pctl-1` through `pctl-3` in the runtime view | Tier 1 Kubernetes Terraform node inputs; logical services do not assign individual pods to those VMs |
| Operating delivery/data view | Tier 1 native delivery/development inputs and GitLab data-VM Terraform/inventory; external `db-1`, `kv-1`, `repo-1` retain their owners |

Checks include XML parsing, text within enclosing rectangles, computed palette, tier order and visual
inspection on both page backgrounds at both widths. Shared style resets affect dash patterns only.
The source-reading arrow targets the source collection; Flux reads each source, while only the
promotion Job writes the application project. External maintenance advances approved platform pins.
Live tests and service/pipeline behavior remain the separate deployment acceptance procedures.
