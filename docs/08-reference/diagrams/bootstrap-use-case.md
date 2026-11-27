# Bootstrap views and navigation

The [clone goal](../../../architecture/generated/platform/hosting/Boot1CloneRepository.svg) selects native
subject/actor roles. Its boot-1 subject binds to `BOOT-host`; its supporting system actor binds to
`SYS-intake`. Selecting each opens the respective foundation or intake design directly.

The [foundation SVG](../../../architecture/generated/platform/hosting/Boot1FoundationReference.svg) is generated
from Figure 1 in the [owning guide](../../03-deployment/foundation/bootstrap/README.md#figure-1-bootstrap-execution-host).
That Mermaid block remains authoritative. Only its boot-1 boundary is associated with the native
model; its internal topology is an existing mapped reference. It is not automatically added to the
native/SysON engineering-view catalogue. No full native foundation coverage or deployed state is claimed.

The native build refreshes this reference if its source hash changes. The check command rejects a stale
source hash or wrong destination identity. Rendering requires the same local browser/Mermaid setup as
the [existing diagram workflow](tier1-flux-ownership-render.md#reproduce): Mermaid 11.17.2
and Playwright with Edge. Set `DIAGRAM_PLAYWRIGHT` and `DIAGRAM_MERMAID` to the installed modules.

From the upstream checkout, with the [model environment](../../01-architecture/07-software-intake/02-connected-model.md#build-and-check) prepared:

```bash
node docs/08-reference/diagrams/render-bootstrap-reference.cjs
python -B scripts/architecture/software_intake.py build
node docs/08-reference/diagrams/verify-bootstrap-use-case.cjs
python -B scripts/architecture/software_intake.py check
```

The browser check follows boot-1 to its foundation figure and back, software intake to its separate
logical design, and the goal's supporting HTTPS behavior. Previews and results go to `.tmp/intake-render/`.
Navigation checks establish the intended reading path, not runtime behavior or requirement satisfaction.

Checked 2026-11-18 with Playwright 1.62.1 and Edge 157.0.4341.46: five focused contract
checks, four standalone navigation steps, and normal/narrow light/dark previews of both figures passed.
The native model/check and six existing HTTP executions also passed. The local architecture link
sweep checked 2,002 links/anchors without failures. These results do not claim native modeling of the
foundation internals, SysON republication or a live Git clone.
