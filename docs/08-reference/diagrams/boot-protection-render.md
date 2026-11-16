# Boot integrity and key protection figure

The [editable SVG](boot-integrity-key-protection.svg) answers which security control protects each
part of an installation. It is a logical control view, not a network or physical placement map.
The [architecture explanation](../../01-architecture/04-hosting/01-runtime.md#figure-boot-integrity)
owns the concept; [guest commissioning](../../05-operations/01-hosting/guest-hardening.md) owns the
selected implementation, checks and recovery procedure.

## Reading the figure

Boot admission and service dependencies read left to right. Dotted groups collect responsibilities;
they do not imply a shared machine or network. Boot trust is applied independently to each host and
guest. The issuer uses an HSM only when that signing provider is selected. TPM-based storage unlock
requires enrollment; attaching a TPM alone supplies no encryption. A VM's software TPM remains
under hypervisor control. The offline-root link transfers an issuer certificate through a ceremony,
not through an online connection. Recovery includes the original identities and separately held
credentials; its contents depend on the selected controls.

## Reproduce

Use the repository's [pinned renderer setup](tier1-flux-ownership-render.md#reproduce): Node.js,
Playwright `1.66.0-alpha-2026-11-09` and installed Microsoft Edge. Mermaid is not needed for this SVG.
From **the upstream checkout**, after preparing those tools:

```powershell
$env:DIAGRAM_PLAYWRIGHT = (Resolve-Path .tmp/tier1-flux-render-tools/node_modules/playwright).Path
node docs/08-reference/diagrams/render-boot-protection.cjs
```

In **`<prefix>-architecture/`**, use the same tool preparation and run:

```powershell
node docs/auto-docs/08-reference/diagrams/render-boot-protection.cjs
```

The [renderer](render-boot-protection.cjs) writes four previews and a geometry report under
`.tmp/boot-protection-render/`: 1100 px and 760 px page widths, each on light and dark backgrounds.
The source uses the project [semantic palette](palette.json) and a 960×720 canvas. SVG is the editable
source and displayed artifact; screenshots are local review output, not additional maintained figures.

## Review record

Source correspondence follows the linked boot/TPM implementation contracts, issuer/HSM integration
and independently retained recovery inputs. Reviewed 2026-11-16 with Node.js 24.14.1, the pinned
Playwright above and Microsoft Edge `157.0.4341.46`. All four local cases rendered with no rectangle-label
overflow. Normal/narrow previews on light/dark backgrounds were visually inspected for left-to-right
reading, separate key consumers, connector styles and offline custody. Local rendering does not
establish hosted-renderer parity or operational enforcement of the illustrated controls.
