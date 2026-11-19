# Root, issuer and ceremony figures

The [editable SVG](stage2-trust.svg) opens the [trust deployment](../../03-deployment/stage-02-trust/README.md).
It shows the online issuer, its selected signing-provider interface and persistent application state.
ORCA remains in separate offline custody below the connected runtime. Its dashed link carries signed
public objects through controlled media; there is no network route to the root.

The provider box is an interface, not an additional VM or a claim of replicated key storage.
Software-token files belong to issuer storage. A selected USB device retains its key and independent
wrapped-key recovery material outside that volume. The [custody options](../../03-deployment/stage-02-trust/README.md#step-1-prepare-issuer-and-key-custody)
choose the actual realization.

The [ceremony placement](ceremony-environment.svg) is a second editable SVG, used by the
[deployment procedure](../../03-deployment/stage-02-trust/procedures/ceremony-environment.md) and
[USB-key architecture](../../01-architecture/08-cryptography/04-usb-hsm.md#ceremony-and-deployment-hosts).
It separates connected public builds, on-demand device administration and bottom offline root custody.
The root has independent working, transfer and backup media. Its transfer lines are controlled
copies, not network access or root authority granted to the stager. The actual optional VM path
still trusts its hypervisor and does not bypass physical-media checks.

| Depicted unit | Source / contract |
| --- | --- |
| `boot-1` | Existing Foundation controller; public kit staging and IaC |
| `cbuild-1` | Tier 0 `terraform/deployments/ceremony-build/terraform.tfvars.example`; `ceremony_builders` inventory |
| Live image / kit | `ceremony_image` role and `scripts/offline-root.sh bundle`; public-only image content |
| `cadm-1` | Selected physical runtime or optional `ceremony_sessions` administration VM |
| Selected HSM / recovery | Device commissioning procedure; vendor-wrapped object recovery, independent administrative secrets |
| ORCA / retained media | Local `offline-root.sh` lifecycle and independent physical-media guard; optional VM is `orca-1` |

The native sequence in the ceremony architecture explains operator-assisted root maintenance.
It keeps media unlock, signing and public publication distinct; optional shutdown follows verified
renewal and an encrypted backup. The scheduled public CRL checker does not start/unlock the root.

## Disposable runtime and retained identity

**Workflow:** [Live-image lifecycle](ceremony-live-cycle.svg) reads left to right: public preparation,
selected live session, then shutdown/replacement. Its phase panels are functional groups, not networks
or security tiers. State stays in bottom custody while writable runtime RAM is discarded.
`cadm-1` loads HSM administration tools; it is not an empty VM. The same public ISO boots the separate
ORCA session. OpenSC/PicoHSM tools are included; the YubiHSM SDK exists only when explicitly selected.
The HSM's retained issuer/application objects are distinct from ORCA's current software-root key.

| Lifecycle unit | Implementing source |
| --- | --- |
| Public build / ISO contents | Tier 0 `ceremony_image/tasks/main.yml`, its native live-build recipe and public-input validator |
| No persistent OS disk / NIC-less VM | `terraform/deployments/ceremony/main.tf`; selected physical boot has its separate disconnection procedure |
| Writable RAM / later image | Native `live-boot`, `nopersistence` / `noswap` recipe; no CA state in the public image |
| Original root state | `offline-root.sh` original-instance checks, encrypted working-media requirement and retained policy/history |
| Retained HSM objects | Selected device commissioning and wrapped-key recovery; image replacement does not initialize a token |

## Separate credentials and public exchanges

**Code / custody:** [ORCA key custody](orca-key-custody.svg) separates three credentials. Each row
reads **credential → local operation → protected object**; arrows show authorized use, not export of
the depicted secret. A LUKS passphrase or selected FIDO2 key + PIN/touch opens the volume;
a separate root-key passphrase authorizes
native OpenSSL use of its encrypted PEM; the independent private age identity decrypts a backup.
The public age recipient may be bundled. Restore returns the original encrypted root key and history,
so its root-key passphrase is still needed to sign.

The root wrapper's `genkey --protect passphrase`, encrypted-key assertion and age-encrypted complete
native archive are the source contracts. The guide's `cryptsetup` procedure owns volume unlock.
Normal signing returns public objects; an encrypted complete backup is a separate custody transfer.
The [FIDO2 unlock procedure](../../03-deployment/stage-02-trust/procedures/orca-disk-unlock.md) uses
native image tools and local custodian approval, with retained passphrase recovery. Selected-device
enrollment/unlock still requires hardware qualification; it is distinct from YubiHSM 2 key operations.

**Workflow:** the native [root-signing exchange](../../01-architecture/08-cryptography/01-certificate-authority.md#figure-root-signing-exchange)
shows the public CSR, signed issuer certificate, root certificate/CRL, independent trust distribution
and the separate publication role. The baseline places publication on `ca-1`; the logical separation
does not claim provisioned publication replicas or issuer HA.
The renderer selects this sequence by its explicit anchor, separately from the issuer hierarchy.

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

Sixteen SVG previews and a geometry report are written under `.tmp/trust-render/`: the two placement
views and two explanatory views at normal and narrow page widths, each on light and dark backgrounds.
SVG is both editable source and displayed artifact, using the [semantic palette](palette.json)
and a 960×720 canvas.
With `DIAGRAM_MERMAID` set as above, the renderer also checks the architecture's native sibling-issuer
hierarchy, local-maintenance sequence and root-signing exchange in four cases each using pinned Mermaid `11.17.2`;
their editable sources stay in their owning Markdown pages.

## Review record

Reviewed 2026-11-17 using Node.js 24.14.1, the pinned Playwright release above and Microsoft Edge
157.0.4341.46. Twenty-eight local cases rendered: sixteen SVG cases with no shape-label overflow and
twelve native Mermaid hierarchy/maintenance/root-signing cases. Normal/light and narrow/dark previews were inspected
for readable labels, compact provider flow, sibling trust, independent custody below the runtimes,
disposable image/state separation, the three credential layers, the public signing exchange and
maintenance success/failure branches.
The opaque amber sequence phase keeps labels legible on a dark page.
An absent explicit sequence anchor is a render error; it cannot silently remove that view from review.
The renderer preserves completed-case geometry in `report.json` even when a later native source fails.
Local rendering does not establish hosted-renderer parity or
live issuer/root operation.
