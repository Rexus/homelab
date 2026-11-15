# VMID quick-reference rendering

The [editable SVG](../../02-conventions/vmid-convention.svg) and
[allocation guide](../../02-conventions/vmid-convention.md) share the same category names and examples.
This is an allocation reference, not a deployment topology or security-policy figure.

## Reproduce

Use Node.js, existing Microsoft Edge and the same pinned Playwright version as the
[diagram tool setup](tier1-flux-ownership-render.md#reproduce).
From **the upstream repository**, after installing that toolchain:

```powershell
$env:DIAGRAM_PLAYWRIGHT = (Resolve-Path .tmp/tier1-flux-render-tools/node_modules/playwright).Path
node docs/08-reference/diagrams/render-vmid.cjs
```

From **`<prefix>-architecture/`**, with the same toolchain prepared:

```powershell
$env:DIAGRAM_PLAYWRIGHT = (Resolve-Path .tmp/tier1-flux-render-tools/node_modules/playwright).Path
node docs/auto-docs/08-reference/diagrams/render-vmid.cjs
```

The renderer resolves the copied SVG relative to its own location. It writes four image previews
and a bounds/collision report to `.tmp/vmid-convention-render/`; it requires no Mermaid dependency.

## Review record

Reviewed 2026-11-15 with Node.js 24.14.1, Playwright `1.66.0-alpha-2026-11-09`,
Microsoft Edge `157.0.4341.46`, Arial/Consolas, a 20 px page margin and device scale 1.
The source is 1080 × 810 (4:3). Normal/narrow viewports are 1100/760 px, on white and
`#0d1117` backgrounds. Text bounds and label collisions passed; light/dark previews were inspected.
These checks establish local layout and source correspondence, not hosted-renderer parity or live allocation.

The VMID regression checks parse all starter Terraform VM/container/node allocations, optional guests,
template catalogs and reservations. They check category membership, cluster-wide collisions,
generated-reference parity and preservation of existing local inputs/state during refresh.

[Return to the convention](../../02-conventions/vmid-convention.md).
