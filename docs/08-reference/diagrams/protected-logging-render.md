# Protected logging DNS and routing figures

The deployment distinguishes a stable service name from receiver machine identities. The single
receiver uses `logs` on `log-1`. The redundant-intake guide separates provisioned receivers from
sender-routing and shared-VIP integrations that the kit does not install.

| Figure source | Reader question |
| --- | --- |
| [Protected logging SVG](protected-logging.svg) | Where does the current `logs` endpoint run, and where are records retained? |
| [Stage 2 figures](../../03-deployment/stage-02-logging/README.md) | Which guest/storage and authenticated intake path does the main deployment create? |
| [Redundant intake figures](../../03-deployment/stage-02-logging/step-14b-redundant-intake.md) | What does adding a receiver create, and which routing integrations remain separate? |

The redundant-intake SVGs are [independent receivers](logging-receivers.svg),
[sender routing](logging-sender-routing.svg) and [shared endpoint](logging-shared-endpoint.svg).

The `logs` label is an example service name, not an extra gateway or DNS server in the traffic path.
Solid arrows show the configured main path; dashed alternative routing needs project integration.
Neither two receivers nor a VIP implies replicated stored records.

## Reproduce

Use Node.js, Microsoft Edge and the same pinned Playwright/Mermaid versions as the
[shared renderer setup](tier1-flux-ownership-render.md#reproduce). From **the upstream checkout**:

```powershell
$env:DIAGRAM_PLAYWRIGHT = (Resolve-Path .tmp/tier1-flux-render-tools/node_modules/playwright).Path
$env:DIAGRAM_MERMAID = (Resolve-Path .tmp/tier1-flux-render-tools/node_modules/mermaid/dist/mermaid.min.js).Path
node docs/08-reference/diagrams/render-protected-logging.cjs
```

In **`<prefix>-architecture/`**, use the same tool setup and run the copied renderer instead:

```powershell
node docs/auto-docs/08-reference/diagrams/render-protected-logging.cjs
```

The [renderer](render-protected-logging.cjs) resolves sources beside its own copied location.
It renders four SVGs and two Mermaid figures at 1100 px and 760 px on light/dark pages, writing
24 previews and geometry to `.tmp/logging-dns-render/`. Review labels, containment, connector
directions and the current-versus-integration distinction.

## Review record

Reviewed 2026-11-15 with Node.js 24.14.1, Playwright `1.66.0-alpha-2026-11-09`, Mermaid `11.17.2`
and Microsoft Edge `157.0.4341.46`. All 24 cases passed in both upstream and generated documentation;
the current previews matched byte for byte. SVG rectangle-label bounds passed, and visual review
covered normal/narrow widths on light/dark pages. Local Edge required execution outside the restricted
sandbox. Live DNS, TLS, failover, data replication and hosted GitHub rendering were not exercised.
