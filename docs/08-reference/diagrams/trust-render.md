# Offline root and issuer figure

The [editable SVG](stage2-trust.svg) opens the [trust deployment](../../03-deployment/stage-02-trust/README.md).
It shows the online issuer, its selected signing-provider interface and persistent application state.
ORCA remains in separate offline custody below the connected runtime. Its dashed link carries signed
public objects through controlled media; there is no network route to the root.

The provider box is an interface, not an additional VM or a claim of replicated key storage.
Software-token files belong to issuer storage. A selected USB device retains its key and independent
wrapped-key recovery material outside that volume. The [custody options](../../03-deployment/stage-02-trust/README.md#step-1-prepare-issuer-and-key-custody)
choose the actual realization.

## Reproduce

Use Node.js, the [pinned Playwright setup](tier1-flux-ownership-render.md#reproduce) and installed
Microsoft Edge. From **the upstream checkout**:

```powershell
$env:DIAGRAM_PLAYWRIGHT = (Resolve-Path .tmp/tier1-flux-render-tools/node_modules/playwright).Path
$env:DIAGRAM_MERMAID = (Resolve-Path .tmp/tier1-flux-render-tools/node_modules/mermaid/dist/mermaid.min.js).Path
node docs/08-reference/diagrams/render-trust.cjs
```

From **`<prefix>-architecture/`**, use the same tool preparation and run:

```powershell
node docs/auto-docs/08-reference/diagrams/render-trust.cjs
```

Four previews and a geometry report are written under `.tmp/trust-render/`: normal and narrow page
widths, each on light and dark backgrounds. SVG is both the editable source and displayed artifact.
The source uses the [semantic palette](palette.json) and a 960×720 canvas.
With `DIAGRAM_MERMAID` set as above, the renderer also checks the architecture's native sibling-issuer
hierarchy in four cases using pinned Mermaid `11.17.2`; its editable source stays in that Markdown page.

## Review record

Reviewed 2026-11-17 using Node.js 24.14.1, the pinned Playwright release above and Microsoft Edge
157.0.4341.46. Eight local cases rendered: four SVG cases with no rectangle-label overflow and
four native Mermaid hierarchy cases. Normal/light and narrow/dark previews were inspected for
readable labels, compact provider flow, sibling trust and offline custody below the runtime.
Local rendering does not establish hosted-renderer parity or
live issuer/root operation.
