# Operator walkthrough checklist

Guide sequences rechecked 2026-11-13 against the current worktree, from the
perspective of a software engineer with newly installed servers and UniFi switches.
This is the maintainer's working checklist, not generated
project documentation or a claim of production readiness.

**Scope:** clone, generation, foundation, all ten capability stages and adjacent options,
ordinary users, applications, maintenance, expansion and total-loss recovery.
**Evidence boundary:** source/generator review and offline tests; no live gateway,
Proxmox, HSM, service deployment, failover or disaster restore was performed.

The 2026-11-09 workflow pass and host-management follow-up accounted for all 173 installation, administration,
development, reference and reader-path documents, including the front doors.
It re-derived required order, actual choices, branch rejoins and acceptance gates;
coherent procedures and lookup references were retained. It did not qualify live operations.
Validation: 75 distinct focused regression checks passed, with targeted navigation/link reruns after
the final correction; 576 Bash blocks passed syntax checks. Original Markdown anchors were retained.

## Current source consistency review

### Independent Tier 1 Flux ownership, 2026-11-14

D-041 supersedes only D-036's unselected Tier 1 product status. Tier 0 immutable source/canary
validation and its independent credentials stay intact. Fresh Tier 1 inputs select independent Flux;
legacy defaults and preserved downstream inputs remain Ansible until explicit stopped-writer adoption.

- Ansible installs initial Cilium/Flux and source/decryption access. A pinned bootstrap source owns
  RBAC/canary only; a separate approved platform revision owns Flux itself and selected services.
- Delivery, registry, security collectors, observability, GitLab and Kubernetes runners export real
  native Flux resources. Later stages remain selected explicitly in the authored platform root.
- Spinnaker promotes separate application Git through versioned pipelines and confined Jobs, with
  exact diff/judgment/CAS/revision/health checks. Old direct-writer credentials require explicit revocation.
- External maintenance, exact Git bundles, copied artifact checksums, retained keys and read-only
  recovery Git remain available independently of Spinnaker/GitLab/Harbor/runners.
- Stateful initialization, schema verification, first-backup gates and recovery fencing stay separate;
  resource reconstruction does not restore service contents or reverse database migrations.
- Generated cluster/pipeline/project inputs survive refresh. Current examples/automation refresh;
  local secret files are initialized only when absent. Legacy diagram assets are retained when referenced.

The implementation record in [tier1-flux-implementation.md](tier1-flux-implementation.md) records native
checks and their exact limits. Fresh install, adoption, direct API/Git bypasses, drift, upgrades,
compatible rollback, service outages and clean-host full recovery remain unperformed live gates.
Rancher is unselected with no supplied installer. Existing Argo CD/direct Spinnaker retain their
explicit alternative scope; no live owner is migrated by repository refresh.

### Imported VM clone provenance and firmware, 2026-11-14

All three Linux VM modules retain Proxmox-owned placement and creation-only clone provenance on updates.
BIOS, machine, SCSI controller, EFI disk, boot order, description, OS hint and serial devices are preserved
for existing/imported guests. VM source/full-clone selectors and boot profiles initialize new VMs;
capacity, disk configuration and NICs remain managed. Disk I/O-thread defaults still follow the configured
controller profile; these managed disk options are separate from the ignored boot fields.
The template publisher now carries applied BIOS/machine/controller/EFI-key settings into Shared.
All three Linux guest resolvers inherit the actual source ID's profile without a service-local firmware
block. A complete per-VM override is reserved for a creation exception; tag aliases and legacy
tag overrides cannot select a different profile. Older catalogs can synchronize metadata once;
wholly absent profiles retain legacy defaults for creation, while partial selected profiles fail clearly.
The adoption guide needs no boot-profile backfill and explains that a correct imported ID with a
clone/boot-setting replacement is a module-version issue, not another state rebind.

The preceding catalog pass ran nineteen distinct focused checks, including native plans using cached
bpg/proxmox 0.112.0 across all three tier modules, catalog synchronization, resolver precedence,
the publisher's mocked template plans and source/generated intake plans. The intake starter now
inherits its profile instead of duplicating it. Its update test retains creation-only clone mode.
Synthetic imported state reproduced replacement under the previous lifecycle and retained existing
data-disk identities, EFI, description, OS hint and console using only Shared template hardware.
The preservation follow-up passed eight focused checks: imported plans across all three tier modules,
source/generated intake plans, catalog resolution, all Linux root contracts and documentation links/language.
Changed and absent Shared profiles retain imported boot hardware;
new-resource/replacement plans use the selected profile. RAM/data-disk growth stays visible, and changed
VMIDs still force replacement. Catalog writes remain
idempotent and preserve consumer selections/old entries; invalid hardware leaves Shared unchanged.
Root forwarding, source/generated documentation links, formal language, native HCL formatting and
`git diff --check` passed. Unselected incomplete profiles do not block unrelated consumers.
These were offline `-refresh=false` plans, not a live provider import/apply or Proxmox acceptance test.

### Service-neutral VMID guides and UUID input names, 2026-11-14

VMID and data-disk instructions use the old/new VM and actual owning inputs. Named workload examples
and the workload-specific volume-adoption detour were removed. The conventions index now routes to
IaC input names, defining <service>_<volume>_uuid and stable device selection while retaining established
public keys and per-host pins. Developer extension guidance and the storage reference link that home.
The generic runbooks require the actual schema/printed UUID key, not a literal placeholder or inferred prefix.

Source/generated links and every starter extra-disk/device correspondence passed. NIC transfer,
disk detach/reassignment/rollback argument fixtures and stopped-VM guards passed. Documentation language
checking found personal-pronoun wording in the earlier maintenance edits; it was corrected and rechecked.
No input keys, role behavior, live VM or storage contents were changed by this generalization.

### Generic Terraform state tasks, 2026-11-14

The state runbook now selects the original Terraform root, state file and TF_DATA_DIR from the owning
repository instead of hard-coding cache/Tier 2. It maps VM/container, Kubernetes and template layouts,
retains custom backend/workspace boundaries and routes planning through the original entry point.
Resource removal uses the exact listed leaf address; retirement archives only the selected local
state file, preserving working-data caches and all unrelated deployments.

The VMID caller and state FAQ explicitly route cloned replacements through the complete numbered
adoption sequence. Inspection/backup returns to its caller; deleted-resource removal is an alternative
task and cannot substitute for removal plus replacement import. The adoption page explains declining
an unintended VMID-forced replacement plan. Four targeted documentation/native state checks passed
after this handoff correction; no real provider import or live recovery was performed.

Adoption was expanded into thirteen concrete numbered actions, retaining earlier anchors. Each edit
or command has its own step; removal explicitly changes only state, and import immediately records the
existing replacement. The caller links directly to the preview, removal and import commands. Isolated
success/failure fixtures verified exact address rebinding, original input ordering, paths with spaces
and refusal to reach plan/apply after an import error. No live VM/state was changed.

Six focused checks passed, including native Terraform selection/backup across six repository layouts,
exact removal with another binding retained, isolated state archival, Bash-login survival and
source/generated documentation links. The two native state-task tests passed again after adding
missing-working-data reconstruction coverage. These use disposable built-in terraform_data resources;
no Proxmox provider, live guest, remote backend or non-default workspace was exercised.

### VMID data-disk choices, 2026-11-14

The full-clone guide opens with a data-loss caution and routes three storage paths before Step 5:
keep copied managed disks, reassign an original volume while both VMs are stopped, or intentionally
rebuild disposable guest/data storage through IaC. The focused procedure distinguishes Proxmox volume
ownership, stable guest device paths and filesystem UUID pins. Original-volume transfer includes rollback
and retains the detached clone; existing mount declarations remain enforced. Fresh replacement must be
limited to the accepted resource, with its new UUID saved after Ansible prints the verified binding.

Four focused tests passed: source/generated links, every starter extra-disk/device binding, accepted
new/existing filesystems and rejection of unsafe storage, including missing pinned/fstab-declared disks.
Separate command fixtures passed Bash syntax, stopped-VM guards, detach-without-delete, transfer and
reverse-transfer argument checks. Native Proxmox CLI/API and pinned provider replacement behavior were
checked against upstream source. No live disk reassignment, guest rebuild or provider apply was exercised.

### Maintenance-shell failure handling, 2026-11-14

VMID change, state inspection and VM adoption now isolate terminating checks in an explicitly opened
child Bash shell. The prompt label is explained as navigation only. A failed prerequisite returns
to the parent SSH shell; the operator restarts the selected task instead of continuing without context.
Adoption uses the actual original setup/resource, offers a sibling Shared checkout default and retries
invalid Shared paths before invoking Terraform. Import failure retains the original address/ID record
and separates a retry from the already completed state removal.

All four focused checks passed: three native Bash PTY tests cover invalid Shared paths, missing state
and failed initialization while preserving the parent login and original state; source/generated links
also resolve. Bash syntax and complete multi-NIC transfer/stop guards passed isolated fixture checks.
No live VM, Proxmox API, provider import or operator SSH session was changed.

### Full-clone VMID cutover and state rebinding, 2026-11-14

Hosting operations now owns a general numbered VMID-change procedure, with manual and Terraform
ownership branches, full netN transfer before boot, validation, job/ACL/HA review, retirement and
rollback. The dependency on releasing an occupied target ID is explicit.
Linked-clone maintenance and the central VMID reference route to the same guide.
The existing Linux VM adoption procedure now covers both clones and restores, preserving the exact
resource address and all unrelated state. Original state/context, private backups and normal plan
review surround the state rm/import operation. Custom environments/backends retain their own context.

All 27 distinct focused checks passed after one targeted correction to the figure's metadata:
source/generated links, diagram roles, reader routes and VMID ownership/preservation. Every Bash
block in both guides passed syntax checks. Isolated command fixtures verified complete multi-NIC
values, running-source/replacement guards, exact single-resource rebinding, input ordering and paths
with spaces. Simulated import failure prevents the plan step. These are command-contract checks,
not a live Proxmox clone or provider import exercise.

The native SVG renders in four 1100/760-pixel light/dark contexts with matching computed palette
roles. Reviewed previews retain compact groups, left-to-right copy/identity transfer and a legible
connector label on dark pages. The new SVG is registered in generated documentation. No live VM,
MAC, state, HA membership, commit or remote branch was changed.

### Gray tier boundaries and service-access reference, 2026-11-14

Tier 2/1/0 now use progressively stronger pure-gray boundaries. Routing interfaces use the former
strong-tier warm beige with dark text; policy, action, network, runtime, storage and custody roles
retain their existing meanings. Updated all 92 affected repository figures through their semantic
style declarations, without changing topology, counts, source bindings or physical placement.
The global AGENTS.md, shared palette and current cache/identity reference previews use the same rules.

The architecture identity Service access sequence is now a self-contained global reference with
its exact editable Mermaid source, versioned provenance, light/dark previews and a reproducible
renderer. Guidance distinguishes chronological request/response exchanges and service-local
authorization from block-placement and authentication concerns.

All 78 focused diagram, source/generated correspondence, reader-role, navigation and documentation
checks passed without skips. Ninety-five figures (92 changed repository figures, two global placement
references and the sequence reference) rendered in all four width/background contexts: 380 renders,
no errors or computed SVG palette mismatches. Cache, identity and sequence previews were inspected
at normal/narrow reading widths across light/dark backgrounds. Portable reference scripts were also
exercised. This does not establish hosted-renderer parity or live behavior. No commit or push performed.

### Uniform VMID categories, 2026-11-14

The central convention now reserves category 0 in every guest allocation group. Categories 1-6
are control planes, workers, infrastructure services, network/edge, observability/logging and
bootstrap/automation. Tier 0 omits its leading zero and uses the same full hundred-ID ranges;
its former split Kubernetes range is retired. Template/builder catalog allocations remain independent.
Starter Terraform inputs, optional reservations, Kubernetes fixtures, guides and the editable SVG agree.
Existing local inputs, inventory and state remain preserved; the convention explains occupied-ID
collisions and the separate recovery/rebinding path before deliberate renumbering.

All five allocation/reference/refresh checks and eleven affected provisioning checks passed in an
isolated Linux workspace. Native Terraform mocked plans cover source/generated intake, optional
monitoring and cluster placement; real Talos configuration generation and validation cover all
three cluster roots. Corrected monitoring-test expectations to the existing 10.10.10.70 starter input.
The reference SVG was rendered and inspected at 1100/760 px on light/dark pages with no overlap
or clipping. The broader source/generated documentation, navigation and bootstrap checks exposed
one stale physical-host/SSH-target assertion; it now checks the existing management boundary and
actual bootstrap listener. After that targeted recheck, all 54 distinct focused checks passed,
with no skips. Git diff whitespace validation passed. No live resource renumbering, state migration,
commit or push was performed.

### Malformed inventory handling, 2026-11-14

A reported syslog run fell back to implicit localhost after rejecting a scalar where the inventory
required a mapping. All three tier configurations now enable Ansible's native
inventory.any_unparsed_is_failed option. The syslog guide shows explicit host entries and an inventory
graph check before provisioning. Existing local inventory remains project-owned and is not rewritten.
Native Ansible 2.16.16 verified fatal rejection, valid host selection and explicit localhost parsing in
each source/generated tier. No guest configuration or live inventory repair was performed locally.

### Complete compact diagram review, 2026-11-14

Reviewed every current documentation figure: 128 Mermaid diagrams and 23 SVG sources, including
the convention reference. All 604 width/theme combinations rendered without errors at 1100/760 px
on light/dark pages. Contact sheets covered the full scope; changed pictures were inspected individually.
Geometry checks confirm that control/workload node VMs and per-node collectors actually stack vertically.
The shared SVG palette checks passed. This does not establish GitHub-renderer parity or live operation.

Stage 4 action 11 now uses a compact 4:3 native SVG: five installed chart releases, reconciliation
objects and the accepted CSI prerequisite sit in separate groups; existing Git/block dependencies
remain below the runtime. Platform and workload node views retain three named starter VMs in stacks.
The telemetry path and USB-provider view use SVG to keep interfaces and offline custody legible without
compound-layout routing errors. New assets are included in generated documentation and correspondence
checks; the tests retain real replica counts, resource names, endpoints and containment.

Architecture and operations repairs cover intake, HSMs, evidence authority, hosting, publication and
delivery. Clear short interactions and chronological sequences retain their reading axes. The final
83 focused diagram/source, generated-link, capability-navigation and reader-journey checks passed.
No infrastructure changes, commit or push were performed.

### Guided Kubernetes HA selections, 2026-11-14

Stage 4 now branches at action 9 into retained recovery ownership or the dedicated option 9b.
The new guide maps the actual starter's three existing voters to explicit HA resource inputs,
one Keep Separate rule and the corresponding Proxmox dialog fields. Optional eligible-host
restrictions remain a separate rule; each later cluster gets its own voter selection. Operations
and the generated deployment checklist link the same procedure. GUI-only scheduling controls
remain explicitly outside the current collection's supported fields.

All 77 distinct focused documentation, reader-route and diagram checks passed after targeted
prose/palette corrections. Both copyable YAML selections passed the actual role's validation
without API calls. The opening figure was rendered and inspected at normal/narrow widths on light
and dark pages. No live HA changes, commit or push were performed.

### Padded deployment stage folders, 2026-11-14

The nine single-digit stage folders now use stage-01 through stage-09; stage-10 remains the final
stage. Ordinary lexical sorting in the source and freshly generated manual follows installation
order. Stage titles and action numbers retain their existing meaning. Local links, generated
front doors/checklists, source-side guide pointers and tests use the padded canonical paths.

Migration-map targets were updated while historical keys were retained. Seventy formerly current
guide paths now have direct mappings to their padded destinations. A manifest-backed refresh test
preserves a project-owned old-path link and its historical anchor through a compatibility page,
removes an unreferenced old copy, and verifies that dry-run performs no migration writes.

All 83 distinct focused checks passed after targeted corrections: source/generated links, reader
journeys, lexical stage ordering, refresh ownership/cleanup and diagram/source correspondence.
Two earlier reader checks were adapted to the existing native SVGs rather than counting only
Mermaid fences. No diagram labels changed, so this path-only change required no new visual render.
No deployment, state migration, commit or push was performed.

### Availability, placement and native HA policy, 2026-11-14

Hosting now connects scaling/headroom to redundancy, active-active, active-passive,
automatic VM restart (Proxmox HA), application failover and independent recovery. A shared
before/during/after storyboard distinguishes planned live migration from host-loss restart
and already-running application members. Failure never transfers a dead host's memory.
The architecture names the protected layer and measured service objective rather than
treating an HA label or replica count as proof of continuity.

Foundation routes to an operations edit/run/check procedure, with detailed field lookup
remaining in the HA reference. Operations illustrates fencing, start retries, node preference,
resource separation and rebalancing, with separate maintenance and recovery tasks. Three voters
kept on distinct hosts may preserve quorum after one host loss while the third waits; a fourth
eligible host is needed to recover all three without relaxing that separation.

The Tier 0 Ansible-only proxmox-ha setup initializes local selections and uses native
community.proxmox resources/rules/info modules. It resolves exact guest names or explicit VMIDs,
rejects ambiguous/template selections, protects unrelated rules and removes selected rules before
memberships. Preview validates inputs and identities; it does not predict placement or reserve
capacity. Native controller checks prepare the Proxmox Python clients. A separate HA identity
has the API-required Sys.Audit/Sys.Console and VM.Audit visibility; ordinary provisioning rights
are unchanged. Existing node-exclusion rules cannot silently become preference rules, and
HTTPS endpoint ports are honored. Failback, Auto-Rebalance and negative node-affinity remain
explicit GUI settings outside this collection's supported input schema.

Verification: 71 diagram/documentation/reader-route/generated-link checks and ten HA contract/native
checks passed. Thirteen controller-dependency checks passed; one optional prepared-wheel test
was skipped because its fixture was unavailable. HA tests used Ansible 2.21.5 and community.proxmox
2.1.0. The nine affected Mermaid figures rendered in 36 theme/width combinations; the shared SVG
rendered in four combinations with matching computed palette roles. Normal/narrow layouts were
inspected, including routed arrows avoiding host headings. Browser rendering used the existing
Mermaid 11.17.2 and Edge 157.0.4341.46 tooling documented in the diagram guide.

No live enrollment, host migration/failure, fencing, application failover, re-arm or recovery was
performed. Cluster/storage/watchdog commissioning, surviving capacity and service acceptance remain
target obligations. No commit or push was performed for this change.

### Rendered clutter and shared logging overview, 2026-11-14

The follow-up started from the actual pictures rather than treating successful rendering or
collision checks as visual acceptance. Logging still had competing perimeter routes and crowded
archive labels. Its retention view now has aligned receiver, NAS and independent-backup columns,
with offline custody below. Health/checkpoint reporting has a separate sequence. Stage 2 had retained
a different opening Mermaid figure; it now shares the editable protected-logging.svg with operations.

The wider review split tangled request and placement views in intake, delivery, public certificates,
development and observability, and wrapped overflowing sequence notes. Five compact editable SVGs
replace crowded reference-platform, hosting-runtime, observability-design, control-application and
observability-operations overviews. Per-parent history volumes remain separate, and focused sequences
retain the real ingestion, query, backup and diagnostic interactions. Runner polling and telemetry
export no longer need perimeter detours on their placement figures. The diagram guide records this
reading test and the limits of palette, parsing and collision checks.

All 71 distinct focused regression checks passed, including targeted reruns after correcting the
new figure captions and a repeated guest label. They cover source/count correspondence, scopes,
asset registration, reader routes and source/generated documentation links. The current manual has
124 Mermaid figures and seventeen native context/deployment SVGs, besides the VMID reference.
All 496 Mermaid and 68 SVG renders succeeded at 1100px/760px on light/dark backgrounds; final label
refinements were rerendered separately. SVG computed colours matched the semantic palette. Changed
layouts were visually inspected; these local checks do not qualify hosted rendering or live operations.

Tooling remains Node 24.14.1, Mermaid 11.17.2 and headless Edge 157.0.4341.46. Reproduction and canonical
source formats are documented in docs/04-development/diagrams.md. No runtime deployment, failover,
restore, remote update, commit or push was performed in this visual follow-up.

### Complete documentation diagram sweep, 2026-11-14

Reviewed architecture, deployment, development and operations figures against their source contracts,
with local rendering across both page themes and normal/narrow widths. Tier rows, actual interfaces,
source identity, storage attachment, recovery custody and selected instance counts were traced.
The operations/deployment sidecar reviews inspected their complete baseline inventories and retained
source evidence privately; no structural runtime-code bug or new manual-SSH setup gap was identified.

Concrete corrections include separate public/admin network endpoints; distinct registry publishers
and pull clients; the Windows identity label override; host SSH versus independent console access;
the Control API VIP; issuer portal versus public-download interfaces; worker versus publication reads;
SQL/GitLab backup initiation and storage; and observability writes, queries and diagnostic export.
Deployment views now separate placement from request chronology where cross-boundary arrows prevented
correct tier order. Workload collection shows the namespace Service selecting a replica, its own queue
PVC, and separate metrics/application client identities rather than application fan-out to both replicas.

Static Mermaid figures declare both root and theme font settings, fixing the observed Arial-to-Times
fallback in HTML labels. Source overrides no longer silently change node labels. Opening architecture
figures precede their contents lists, and data recovery links to one authoritative recovery figure.
Explicit SVGs replace unstable cryptography, runner and workload-collection layouts; visible palette
roles stay separate and generated documentation copies all twelve native context/deployment assets.
The one empty, invisible Layout wrapper is a placement aid, not a new system boundary.

Final verification passed all 71 focused checks with no skips, including source/count correspondence,
geometry and palette contracts, reader routes, all generated-documentation/refresh tests and local links.
The final manual contains 122 Mermaid figures and twelve native context/deployment SVGs, alongside the
separate VMID reference. All 488 Mermaid renders and 48 SVG renders succeeded at 1100px/760px on light/dark
backgrounds; SVG computed colours/outlines matched the palette. Rendered corrections were inspected,
including the two layouts that parsed correctly but still required explicit composition.

Tooling: Node 24.14.1, cached Mermaid 11.17.2, Playwright and headless Edge 157.0.4341.46.
Source formats and public reproduction commands are documented in docs/04-development/diagrams.md;
editable SVGs are authoritative vector sources. Small request chains remain naturally wide without
artificial padding. The right-hand origins in the edge-proxy view are backend dependencies, not
Internet sources. Hosted-renderer presentation and live deployment/failover/recovery remain unqualified.

### Top ownership row and external entry, 2026-11-14

Tier 2 remains the top ownership row in placement views. Internet/upstream sources sit to its left;
tenants and other external clients enter the target owner's interface from the left. Actual lower-tier
consumers stay below a higher-tier provider and request upward. Chronological diagrams retain their
time axis. Global AGENTS.md, its standalone reference, the project guide and context now agree;
the older instruction permitting external clients above the ownership rows was removed.

Explicit editable SVGs repair the lab, verified-intake, software-intake overview and secrets views.
Their source-backed interactions, independent owners, storage and custody are retained. The identity
architecture figure also moves enrolled hosts to the left using the real directory-protocol link.
The wider architecture review used the existing 57-figure geometry inventory and external-actor sources.
Mermaid trials could not hold the intake placement compactly, so those views use explicit SVG geometry.
All seven native deployment/context SVGs are copied into generated architecture documentation.

All 45 focused checks passed with no skips: placement and palette contracts, source/generated assets,
reader roles and source/generated links. The four new SVGs produced 16 successful browser renders
at 1100px/760px on light/dark backgrounds with no computed-style mismatches; accepted previews were
inspected for layout and labels. The identity page's two Mermaid figures produced eight successful
renders, with the changed opening view inspected at both widths/backgrounds. No live deployment or
hosted-renderer acceptance was performed in this placement review.

### Boundary palette, reference figures and directory failover, 2026-11-14

Actual networks now share the solid gray-rose network role. Logical service/function collections and
replica groups use dotted neutral gray, while ingress, VIPs and other routing interfaces use charcoal
with white text. Protection-zone maps retain their explicit zone roles. The global AGENTS.md and its
standalone cache/identity source snapshots, previews, palette and render record capture this grammar.
The project guide and context use the same roles.

Identity deployment and operations share the explicit SVG. Traefik routes through keycloak-http,
state sits below the IdP, and primary/fallback LDAPS paths reach the actual directory members.
The example now supplies both replicated member URLs, a five-second connection timeout and a ten-second
read timeout through the native Keycloak module. Legacy single-member inputs remain accepted.
Tests reject comma-separated, insecure, tab-separated and empty endpoint values. A folded YAML condition
keeps the regular expression a boolean assertion across supported Ansible versions.

Protected logging now has a compact receiver / NAS / independent-backup layout with offline custody
at the bottom and external success checks outside Tier 0. Input, inventory, archive and backup source
contracts were traced. SVG combined selectors reset outlines only, following correction of a colour
inheritance override. Browser-computed colours and outlines match every assigned native palette role.

All 55 focused Linux checks passed with no skips. Coverage includes native Ansible assertions/API
arguments/syntax, diagram scopes/counts/placement, generated assets and source/generated links.
The palette sweep rendered 125 Mermaid figures in four width/background combinations before the shared
identity consolidation. Final group refinements rendered 41 affected figures again, with no errors.
The current manual contains 124 Mermaid figures and three native SVG figures. All three SVGs were
rendered at 1100px/760px on light/dark pages with computed-style checks, and key views were inspected.
The cache block-beta trial stretched cells, obscured titles and crossed the VIP, so the SVG remains
the reference. Tool versions and reproduction commands are recorded with the global snapshots.

Live directory-loss acceptance remains open, including application login with refused and silently
dropped connections. The Keycloak procedure links the upstream delayed-failover authentication report.
Hosted-renderer presentation and live logging/backup/recovery acceptance remain separate work.

### Cache request placement, 2026-11-14

Stage 1 and operations share the editable `cache-services.svg` view. Approved Tier 0/Tier 1 callers
sit below Tier 2 and request the VIP upward; Cache Services request approved Internet sources or the
configured parent proxy to the left. Actual Squid parent-proxy inputs, network key, guest names and
independent data mounts were checked against the implementation. The caption distinguishes requests
from replies and retains the single-active-owner, nonreplicating cache contract.

All 26 focused checks passed for direction/containment, palette, source counts, generated asset bytes
and documentation links. Four browser renders checked the embedded SVG at 1100px/760px on light/dark
pages; the intrinsic 960x720 image scales to 720x540 at the narrow width. No runtime settings changed;
hosted presentation and live traffic were not tested. The project diagram guide records the general
rule for callers below their provider and outbound requests to external peers on the left.

### Identity operations placement, 2026-11-14

The operations overview now embeds an editable SVG with explicit coordinates. Its IdP database is
aligned below Keycloak inside the namespace, and Offline Custody spans the bottom below all connected
services. This replaces the operations Mermaid view whose nested directions and disconnected custody
did not provide reliable placement. The incoming rule still targets actual ingress outside Tier 0.

Twenty-five focused checks passed for scope, geometric placement, palette, source counts, generated
asset bytes and documentation links. Four browser renders checked inline geometry and the embedded
image at 1100px/760px on light/dark pages. The image has an intrinsic 960x720 canvas; the narrow embedded
image measures 720x540. The SVG itself is the editable source; no export toolchain is required.
No infrastructure behavior changed. Hosted-site presentation and live services remain unqualified.

### Concise diagram language, 2026-11-14

Boundary titles now name their scope directly: Tier 2; Cache Edge Network / external_edge; Cache Services.
The same noun-phrase pattern removes narrative status, counts and step references from enclosing labels
throughout the documentation. Useful IaC keys and instance names remain; captions retain important scope,
trust and selected-configuration details. Cluster runtimes identify Tier 0, Tier 1 or Tier 2 Kubernetes.
Global AGENTS.md, its visual reference, the project diagram guide and repository context capture this language.

Sixty-six focused Linux checks passed together, covering source/generated diagrams, input correspondence,
reader routes, refresh ownership and links. All 129 Mermaid figures rendered at both widths/backgrounds;
targeted final renders followed the last title refinements. Visual inspection focused on operations
cache, identity, delivery and observability views, with the inventory reviewed in contact sheets.
These wording changes do not change IaC behavior or qualify hosted-renderer parity or live infrastructure.

### Network, service and policy boundaries, 2026-11-14

The follow-up diagram sweep separates real network/runtime placement from logical deployment groups.
Generic physical-host wrappers were removed from service views; host placement remains explicit for
capacity, host operations, attached storage, USB affinity and failure-domain views. Distinct networks
were retained. Identity uses a dotted functional grouping, Kubernetes on `control_cluster`, the
`keycloak` namespace and directory VMs on `identity`. Its incoming policy annotation sits outside
Tier 0 and points directly to ingress. IdP state sits below the application; recovery custody stays
outside connected runtimes at the bottom. The global guidance and project palette capture these roles.

Fifty-nine distinct Linux checks passed for source/generated figures, input/count correspondence,
contrast, refresh ownership, reading routes and local links. All 129 Mermaid figures rendered without
errors at 1100px and 760px on light/dark page backgrounds (516 review images). Contact-sheet review
covered the inventory; focused inspection checked identity, cache, issuer custody, replica stacks and
modified network views. Review used Mermaid 11.17.2 and Edge 157.0.4341.46. Native interface aggregates
retain the depicted members without duplicating each identical connection. No IaC behavior changed;
live deployment, failure/recovery behavior and hosted-renderer parity remain unqualified.

### Diagram composition and operating views, 2026-11-14

The global AGENTS.md and project diagram guide now state opening-figure placement for architecture,
deployment and operations, including substantial enhancements and links from their related actions.
Existing global reference drawings remain unchanged; the reference prose and semantic palette agree.
Tier shades strengthen from Tier 2 to Tier 0, independently of DMZ/Services/Control zone colours.
Kubernetes, traffic interfaces, actions and inner groups remain distinct; violet storage and amber
offline/recovery custody retain their original values. Policy matrices retain their severity legend.
Colour and grouped instances confer no access or HA.

The complete inventory contains 129 Mermaid figures and one editable VMID reference SVG. The sweep
corrected remaining tier/runtime colours, empty heading bands, long labels, source/input captions,
actual polling directions, replica groups and state/recovery ownership. VMID annotations were removed
from deployment views; the allocation-convention SVG remains the intentional reference exception.
NetBox's single web instance and worker are distinguished from its database instances. Native HSM
variants retain qualified provider/failover contracts without implying automatic key replication.
Twelve added figures introduce eleven Operations capability entries; backup and recovery task views
also precede their input/task lists. Reusable procedures point to their owning result where appropriate.
Stage 9's CI-authority path now applies the reviewed saved plan rather than repeating an input copy.

Fifty-eight distinct Linux regression checks passed, covering source/generated figures, contrast,
architecture order, guest/product correspondence, refresh ownership, reader routes and local links.
All 129 Mermaid figures rendered on light/dark page backgrounds at 1100px and 760px; the static SVG
also rendered in those four contexts (520 final review images). Contact-sheet review covered the full
inventory; detailed inspection concentrated on changed layouts, headings, dense views and source
boundaries. Final targeted renders/checks followed visual refinements. A successful parse alone was
not treated as visual acceptance, and not every screenshot was individually inspected at full size.

Review used Mermaid 11.17.2 and Edge 157.0.4341.46. Editable fences remain authoritative;
[export instructions](../docs/04-development/diagrams.md#export-a-review-copy) describe portable review.
No live infrastructure, HA/recovery behavior or hosted GitLab/GitHub renderer was qualified.

### Logging producer inventory reuse, 2026-11-13

All tier inventory templates now expose the producer selection group. Tier 0 includes
the existing receiver group as a child, reusing host identities and connection settings.
The initial route explains how to merge that membership into older local inventories;
refresh continues to preserve those local files. Producer host inputs add stream/health
settings without overwriting UUID guards or repeating address/login inputs.
Forwarding examples reuse the service DNS name for the connection target and certificate
peer, retaining an explicit fixed-IP target option before service DNS is available.

Eight focused native first-run, generated-payload, deployment-route and source/generated
link checks passed. The native Ansible 2.16.16 fixture executes the documented argument
sequences against the actual receiver inventory and verifies group membership, retained
connection settings and endpoint reuse. No live forwarding or deployment was performed.

### Scaling architecture, 2026-11-13

The hosting runtime owns vertical/horizontal scaling and physical-host capacity guidance.
Its illustrative memory-packing view uses Shared's actual `small`, `medium` and `large`
profiles; a correspondence check ties column spans and the adjacent CPU/RAM table to the
catalog. Host memory reserve is illustrative, not automatically enforced or live inventory.
VM/node definitions, application replicas, physical expansion and HA/rebalancing retain
their distinct lifecycle and state owners. No autoscaler or runtime behavior was added.

All 26 focused diagram, architecture-order and source/generated navigation checks passed.
The two runtime figures rendered with Mermaid 11.17.2 on light/dark page backgrounds at
1100px and 760px; the new capacity figure was visually inspected at both reading widths.
Its shared grid keeps profile widths comparable across hosts. Editable Markdown remains
authoritative; [diagram export instructions](../docs/04-development/diagrams.md#export-a-review-copy)
describe reproduction. Local rendering does not establish hosted-renderer parity or live capacity acceptance.

### Commit preparation, 2026-11-13

The final review keeps NetBox's immutable collection pin in Shared's existing source catalog and
retains the tier-owned imported precheck as the first entry point. The verified runtime metadata
includes that release; controller fixtures select Python clients by collection name rather than
catalogue position. Layout checks distinguish executable playbooks from their variable files and
account for the explicitly shared dependency builders and backup-storage helper.

The backup PV/PVC guard accepts Kubernetes' equivalent BinarySI capacity representation, such as
`1024Gi` returned as `1Ti`; changed capacity, source, owner and retained binding remain rejected.
Four native loopback checks cover the correction without changing a live cluster.

Full source parsing passed for 676 YAML files, four JSON files, 165 Python files and 28 Bash scripts.
Native Terraform parsed 55 selected HCL inputs/configuration files without backend initialization.
Controller precheck/source/dependency and disk-binding verification passed all 32 selected cases
across the native batch and two prerequisite-enabled follow-ups. The latter used cached HCL parsing
and an existing local wheelhouse; offline client convergence and inherited proxy settings passed.

The broad portable run completed 772 methods: 389 passed and 364 explicitly required unavailable
native tools. Its 19 failed/error methods exposed stale catalogue/layout and guide contracts plus
missing orientation or route labels. Every failed method passed after correction in the focused
native and documentation follow-ups, including 19 final documentation checks. This is combined
evidence, not one clean 772-method run. Source/generated playbook syntax and documented first-run
inputs passed; the final ownership, monitor-address and template-runtime guidance checks passed too.
All 725 historical migration keys remain preserved. No live infrastructure was contacted.
Final deployment syntax checked all 468 Bash blocks and 40 YAML blocks without skips or failures.
Redacted Gitleaks checks passed for the staged diff and all 131 locally available commits.
Whitespace checks passed; the reviewed changes were staged for the owner's commit. No commit or push
was performed, and the feature branch matched its fetched upstream at the handoff.

### Continuous deployment paths, 2026-11-13

Reviewed Foundation and all ten stages, including their selectable paths and reusable procedures.
Main pages now number actual configuration, execution and verification actions, rather than hiding
another installation sequence under a few numbered phases. Required first-install work stays on the
owning route; reusable enrollment, protected signing ceremonies and independently owned integrations
retain explicit handoffs. Later reconciliations identify the resources they reuse.

Fourteen additional option/procedure routes were renamed or consolidated to match their actual callers.
Generated checklists, source comments, links and migration destinations follow those routes; historical
manifest keys and existing project records remain protected. Initial template publication does not
introduce a second template-refresh state owner. The bootstrap LVM commands and supported OS choices
retain their supplied technical sequence.

The audit also exposed implementation gaps: optional controller-local ClamAV definition import,
explicit backup-only NFS CSI PV/PVC creation, bind-only FreeIPA reader preparation and dedicated
read-only NetBox audit credential bootstrap. These are opt-in native workflows; accepted external
resources remain supported. NAS exports, access/custody and source markers remain explicit storage-owner
interfaces. No normal post-bootstrap path requires logging into a newly created guest to install or
format its disks. The fresh independent-monitor example no longer collides with an API gateway address.
The shared volume role prints the actual optional UUID guard key for cache, intake, issuer, VM-based
observability/GitLab, OpenBao and recovery-disk callers; the receiver retains its specific file handoff.
The message distinguishes persistent UUID mounting from optional pinning and explains host/extra-vars precedence.

Validation: 46 focused navigation/ownership checks passed, followed by final source/generated link and
checklist-preservation reruns. All 468 deployment Bash blocks and 40 changed YAML examples parsed.
New native fixture checks passed: 13 offline-definition cases, nine account-bootstrap cases and
13 backup-storage/review cases. Twenty-two existing consumer/schema checks passed after enabling
their cached prerequisites; the optional Nginx HTTPS fixture was unavailable and skipped.
Seven synthetic service UUID handoffs and the unselected no-op passed under Ansible 2.16.16 without
disk access. Snapshot secret scans and whitespace checks passed. Combined evidence spans focused
runs, not a single complete native suite; interrupted superseded storage batches are not counted.
The final generated-volume correspondence check passed after the shared UUID output change.

Verification uses isolated local fixtures and source/generated outputs. It does not establish live
LDAP authorization, real NetBox-version interoperability, NFS binding/mount behavior, current scanner
definitions, failover or recovery acceptance. Those remain in the operational verification register.

### Continuous logging installation, 2026-11-13

Stage 2 now has sixteen sequential edit/run/check actions on its main page. The first
receiver, requests, explicit signing choices and first producer no longer require a
receiver/trust/source document cycle. Storage is prepared once; later reconciliation
explicitly reuses it. Receiver and authority leaf pages own adoption/diagnosis and
maintenance; the source procedure remains reusable for later tier-owned enrollment.
Topology options are 14a/14b and retention options 15a/15b. Filenames, generated
checklists, source references and historical migration destinations follow that order.
The three main figures retain their rendered Mermaid source and original order.

The storage recipe preserves its verified binding and prints the actual UUID input
and destination. Multi-receiver guidance uses inventory-adjacent host variables and
explains extra-vars precedence. Native Ansible 2.16.16 synthetic checks covered single,
multiple and limited runs without device access or automatic local-input edits.

Of 64 integration cases, 62 passed initially. Two old reading-contract failures were
corrected: actions may reference an earlier result figure, and the architecture index
retains recognizable deployment-capability names. Both corrected cases and source/generated
link/prose checks passed in the four-case follow-up. Native documented command checks
cover both first-producer runs, later source inputs and archive/backup inputs. All 46
logging Bash/YAML guide blocks and three edited Ansible files passed syntax checks.
Legacy option routes, owned records and input preservation remain covered. No live
receiver, signing ceremony, failover, retention denial or restore was performed.

### Service DNS convention, 2026-11-13

`docs/02-conventions/service-dns.md` now owns familiar service labels, optional
environment/project scope and the separation from individual machine identities.
Architecture, deployment inputs and the generated platform-standards worksheet link
to that rule. New examples coordinate Git/CI, CA portal, data-service, observability
and Kubernetes API endpoints without changing their domains. FreeIPA member identities,
replication peers, protocol discovery, pinned recovery targets and external provider
names retain their contracts; aliases require matching listeners, DNS and TLS identities.
Refresh continues to preserve project-owned local inputs and deployment records.

Fifteen changed YAML examples and four Terraform examples passed YAML/native HCL syntax
checks. Of 46 focused regression cases, 45 passed; the optional native Netdata reader
check was skipped because its approved binary was unavailable. Coverage includes
source/generated links, local-input preservation, database rendering/refusal paths,
cluster-endpoint contracts and observability templates. The snapshot secret scan passed.
No DNS records or deployed services were changed; live endpoint acceptance remains separate.

### Diagram reading pass, 2026-11-13

Foundation and all ten deployment stage READMEs now lead with their expected result.
Major installation additions retain their own figures at the point of introduction;
named anchors connect configuration, execution and verification actions to those views.
All 434 deployment command/configuration fences matched the baseline at completion of
this figure-only pass; the subsequent service-DNS example changes are recorded above.

Architecture leads with placement and communication rather than repeated link catalogs.
New or refined sequences cover proxy use, protected execution, certificate issuance,
key custody, seals, delivery and independent log checkpoints. Composite block labels that
overlapped their contents were replaced with native boundaries; dependencies and providers
stay to the right where tier, hosting and real transfer direction do not take precedence.
Repeated placement/interface tables were consolidated, and reference VLAN ranges moved to
the network conventions while the old architecture section remains a linked route.

The final documentation, diagram, deployment correspondence, reader-path and CA-boundary
run passed 58 tests. Fourteen relevant checks passed again after final foundation/hosting
refinements. Source and generated links, native palette pairs, custody boundaries and
selected guest/release mappings are covered. The snapshot secret scan found no leaks.

107 figures in the changed guides rendered successfully in 428 combinations: Mermaid
11.17.2, Edge 157.0.4341.46, light/dark themes on matching white/dark backgrounds, and
1100/760-pixel review widths. Representative placement and communication views were
visually inspected; parsing alone was not used as layout acceptance. Near-4:3 composition
is a target, with small comparisons and protection-layer views remaining naturally wider.
The inline fences remain authoritative; the diagram guide documents native Markdown export.
GitHub renderer parity and live infrastructure acceptance were not performed in this pass.

### Collection-source automation, 2026-11-12

Controller prechecks now default to native Git acquisition for missing or incompatible collections.
All twelve declared sources have verified release identities and full upstream commit pins. Compatible
installed copies remain in place; configured search precedence and final effective versions are checked.
The native batch resolves dependencies without consulting Galaxy distribution servers. FreeIPA's
upstream release builder is invoked automatically in temporary controller storage, cleaned after install.
The standalone Tier 0 template runtime mirrors only the Proxmox pin and retains its Shared-independent
bootstrap contract. Explicit Galaxy selection and acquisition-free dependency check mode remain available.

Validation includes real local Git installs with a distribution server that receives no requests,
dependency resolution, rerun preservation, incompatible-copy replacement and generated tier execution.
Thirteen existing version/cache/compatibility tests passed. The pinned upstream FreeIPA builder passed
41 native tasks, isolated installation, module discovery, repeat-build reuse and cleanup. Pin alignment,
source/generated documentation and bootstrap checks passed separately. Standalone template preparation
passed eight tests, with one wheelhouse-dependent repeat skipped. No running cache, proxy policy,
remote infrastructure or production controller environment was changed by these repository checks.
The complete parent FreeIPA flow also passed with only community.general pre-staged: install and
temporary workspace cleanup succeeded, then rerun made zero changes with no Git, build or Galaxy requests.

### Final handover review, 2026-11-11

Scope: the complete pending change set, all ten stage routes, generated repositories,
capability-to-source correspondence and maintenance/recovery handoffs. No live deployment was run.

- Align the optional hardware-provider/remoting and independent signing-API routes with their actual
  stages, separate state and recovery ownership; retain PKI/HashiCorp Vault as the initial path.
- Complete the project deployment checklist's CSI, human SSO, registry and hosting options without
  resetting existing completion records. Correct final architecture/operations and source links.
- Pass the selected ordered configuration overlays into controller prechecks as well as deployment;
  reject an unselected software-consumer group before contacting any guest.
- Preserve the saved template plan's context artifact in protected CI and reuse the tier-owned
  dependency catalog for immutable builds.
- Resolve extra-disk classes lazily: explicit datastores work with an empty class map, omitted classes
  inherit the VM datastore and unknown selected classes fail before resource changes.
- Refuse template replacement of ordinary VMs. Refuse backup initialization over partial repositories,
  linked configurations or recovered filesystem data; retain original files on rejection.
- Scan history with redacted Gitleaks output. Six exact historical public-stage-name test assertions
  are documented false positives; only those fingerprints are excluded, not their files or rules.
- Complete seal/signing option metadata and record the independent log-backup VM's reservation in
  the central VMID reference. Update assertions for readiness/prechecks and native product installers
  while retaining baseline ordering, controller-interpreter, evidence and ownership guarantees.

Validation is combined evidence, not one clean all-native suite:

- Broad portable run: 725 methods, 322 tool-dependent skips. Twelve failed methods exposed guide
  metadata/wording gaps and stale contract assumptions; all passed in the final ten-method and
  four-method reruns. The latter also rechecks every VMID allocation/category and collision guard.
- All 230 source/generated playbook syntax invocations and two baseline host-list checks passed.
- All 27 native Terraform VM mock cases passed across the three tiers. Four focused safety tests
  passed, including preservation of ordinary VM disks, partial repositories and recovered data.
- Native Ceph chart rendering passed for all three tiers, and the NFS contract passed, using the
  accepted Core 2.16.16/setuptools 81 environment. The newer fixture's incompatible setuptools
  stopped at precheck before rendering; no dependency guard was weakened.
- Controller execution/input-overlay, signing, bootstrap and source/generated navigation checks
  passed in their scoped runs. Redacted scans passed for 129 commits and staged source changes;
  whitespace checks passed. No runtime/private artifacts were selected for the index.

This handover prepares the index for the owner's signed commit. It does not commit or push.
Physical HSM qualification, live SSO/failover and clean-target recovery remain separate acceptance.

### Deployment automation audit, 2026-11-11

Scope: Foundation and every numbered deployment/option, source inputs through native resources and
generated repositories. No real infrastructure, key authority or remote state was changed.

- [x] Remove post-bootstrap guest SSH setup; retain explicit physical/offline custody interfaces.
- [x] Align all 16 Linux VM root contracts with native firmware, clone, NIC, media, disk and lifecycle
  settings. Preserve the private gateway's distinct-host guard. All 21 roots validate; 97 native
  provider-mocked VM/LXC/template/cluster/gateway cases passed across the final scoped runs.
- [x] Supply native Ceph RBD CSI alongside retained existing/NFS interfaces, with scoped credentials,
  Talos preparation and selected storage before consumers.
- [x] Supply seven-host native observability installation, protected persistence and scoped UIs.
- [x] Supply GitLab VM OIDC, scheduled encrypted exports, sensitive controller access and isolated recovery.
- [x] Supply Vault VM audit/OIDC API reconciliation and configurable VM/Kubernetes seal interfaces;
  refuse implicit seal changes. Independent recovery can mount a configured native NAS export.
- [x] Supply pre-Headlamp public PKCE/RBAC workflow and Kubernetes-native backup-repository commissioning.
- [x] Correct integrated controller-runtime fixtures and native Spinnaker commissioning rendering;
  preserve behavioral assertions and source/generated correspondence.
- [x] Supply initial bootc image build, shared PKCS#11 remoting and independent OpenBao external-key
  signing selected during this review. Keep PKI/HashiCorp Vault first and advanced options distinct.
- [x] Bound collection versions for the OS Ansible baseline, reject unsupported Proxmox runtimes before
  acquisition, align manifests/catalogs and include the OpenBao host client's cryptographic dependency.
- [x] Guard ordinary OpenXPKI PKCS#11 activation as well as direct key operations; reject unaccepted
  custody and factory credentials without preventing inactive installation.
- [ ] Complete physical HSM, live SSO/failover, NAS and clean-target recovery acceptance independently.

Native Collector and Data Prepper parsers accepted the dedicated VM inputs. Isolated native backup,
key-identity, seal-migration and original-state guards passed. Completed final scoped checks include:

- 18 controller/VM-contract/data-binding/Vault/bootc checks; 21 reader/navigation/source-view checks.
- 312 source/generated playbook and task syntax checks, plus 54 updated HSM task checks.
- 17 compatibility checks with 11 installed collection versions supporting Core 2.16; Proxmox refuses
  that runtime and requires its separately prepared newer environment.
- 15 final activation/Vault/OpenBao checks on the declared compatible runtime: 12 passed, three
  artifact-dependent repeats skipped. The separate native OpenBao run passed all nine tests using
  OpenBao 2.7.2, PKCS11 plugin 0.2.1 and SoftHSM 2.6.1, including real RSA-PSS/P-256 signing,
  certificate authorization, idempotence and the artifact-only route.
- Provider suite: eight passed; direct issuer guards: three passed including 12 rejection cases.
  Native remoting: four passed, one Node-dependent test skipped and passed separately on Windows.
  Native p11-kit/OpenSSH/SoftHSM tests cover SPKI identity, denial, extra-key refusal and reconnection.
- Eleven changed figures rendered in both light/normal and dark/narrow views; source/generated
  palette, allocation, link and diagram/input checks passed. Netdata CLI checking remains skipped
  without its matching executable; fourteen focused VM service tests and Collector validation passed.
- Native PKCS1-to-PKCS8 conversion also passed on the bounded crypto collection, preserving public
  identity through rerun and key rotation.

Physical YubiHSM/PicoHSM, live PC/SC, enforcing EL10 policy, application/HSM failover, SSO and disaster
recovery remain target acceptance. Automatic review blocked fixture cleanup of WSL's generic `sshd`
account because ownership was not uniquely established. It was left untouched; the fixture now
requires that OS account to exist and never creates/removes it.

### Controller-owned guest setup, 2026-11-11

- [x] Cross-check every active Terraform extra-disk reference against its service's stable
  by-id selector in source and generated repositories: cache, receiver, issuer and verified intake,
  plus the independent backup starter. Correct stale disk-letter references; preserve local UUID pins.
- [x] Replace Stage 2 action 1.4's interactive SSH with the storage-only Ansible recipe.
  Terraform allocates the guest/scsi1 disk; Shared prepares and verifies its filesystem/UUID mount
  before receiver TLS enrollment. Receiver verification and diagnostics run from the controller.
- [x] Wait for managed guests before facts/configuration, including issuer, logging, runner,
  VM delivery, lab and diagnostic paths. GitLab data-host waiting follows its controller checks.
  Prepare the receiver firewall and retained deployment SSH port through native modules.
- [x] Supply guarded public issuer-certificate transfer and separately selected native token
  operations from the controller. Offline signing/custody approval remains outside guest setup.
- [x] Supply native RPM/APT consumer source/trust configuration and strict refresh through
  tier-owned entry points using Shared execution code. Retain vendor keyrings and backup replaced APT files.
- [x] Supply runner collection handover, state digest validation, public keys, known-host trust
  and non-secret CI environment deployment. Preserve executability, exclude bootstrap environment
  and provider/plan caches, distinguish authoritative state from disposable backend metadata,
  refuse different destination state and retain the stopped-writer boundary.
- [x] Add the optional managed recovery VM/disk definition to syslog inputs; use the stable
  scsi1 device instead of Linux letter ordering. Existing independent hosts remain adoption interfaces.
  Replace manual Kubernetes clone/bootstrap instructions with accepted existing-cluster adoption.
- [x] Pass final targeted controller/guard/syntax and reader-route checks with Ansible Core 2.16,
  generated-source link checks and native rsync copy verification. Exercise real filesystem creation,
  persistent UUID mount, rerun, growth and replacement-disk refusal on disposable XFS and ext4 loops
  in private mount namespaces. Render and inspect the compact syslog provisioning view.

These are source/offline checks; no live Proxmox, issuer, runner or service deployment was performed.

### Numbering and operations follow-through, 2026-11-11

- [x] Renumber architecture chapters 01–11 and close gaps in the nested Hosting and
  Software Intake files. Keep installation order with the ten deployment stages.
- [x] Consolidate Operations into six domain entries matching the designs, with local
  configuration, executable tasks and recovery links before deeper reference material.
  Replace thin per-stage landing folders with the actual runbook or shared task home.
- [x] Update incoming links, source-side guide references, generated templates and migration
  destinations. Keep retired numbered aliases only while project-owned records reference
  them; retain legacy routes separately and preserve original section anchors.
- [x] Pass focused documentation, graph/reachability, refresh, reader-journey, diagram and
  ten-stage correspondence checks across the final runs. Correct the new migration test's
  existing-parent fixture and rerun it successfully with the final links and review checks.
- [x] Validate all 21 Terraform roots and pass 94 native mock cases in isolation.
  Render 47 architecture figures; inspect the updated HTTP/HTTPS sequence on light/normal
  and dark/narrow pages. No live deployment or hosted-renderer acceptance was performed.

### Architecture reading and consolidation, 2026-11-11

- [x] Group architecture by substantive domain rather than duplicating deployment-stage
  landing pages: Hosting owns Kubernetes/labs, Cryptography owns trust/secrets,
  Delivery owns development, and Operations owns logging/observability.
- [x] Separate background from organizational authority; place communication sequences
  beside their capability and explain which decision each chapter supports.
- [x] Reduce 46 pages/15 chapter folders to 37 pages/10 folders, update current links and
  migration targets, and retain needed numbered aliases for project-owned Markdown links.
- [x] Check the 81 documentation, navigation, migration, refresh and correspondence cases
  across focused runs after fixes. Render all 47 architecture figures locally; inspect
  changed views at normal/narrow widths on light/dark pages. Hosted-renderer parity is unverified.

No infrastructure definitions or live resources were changed by this documentation work.

### Template OS classification, 2026-11-11

- [x] Expand Linux-family choices with generic Linux, Windows and other guests;
  keep distribution identifiers open-ended and legacy Alma/Rocky inputs valid.
- [x] Match uploaded raw/qcow2 filenames, guest OS types, optional EFI keys/TPM and
  Shared catalog synchronization; reject non-Linux images in the Linux guest resolver.
- [x] Pass 13 focused regression checks, including 28 locked-provider template mock plans,
  native discovery/adoption fixtures, consumer placement guards and generated documentation links.
- [ ] Clone-test each selected new OS image on the target platform. Windows guest preparation
  and OS-specific consumers remain separate from publishing an approved disk image.

### Final repository correspondence review, 2026-11-11

- [x] Restore the deployment-picture checks to the numbered source directories and
  reject empty architecture discovery, so retired paths cannot silently bypass the audit.
- [x] Check the depicted starter guests, selected runtime releases and cluster log streams
  against the actual inputs, inventory and native release configuration.
- [x] Align the generated Tier 1 software-supply starter with the supplied verified-intake installer.
- [x] Bind the issuer, protected receiver and verified-intake reference volumes to the
  Proxmox scsi1 by-id identity rather than boot-dependent Linux disk letters.
- [x] Retain the architecture figure/caption convention in the project diagram guide.
- [x] Validate all 21 Terraform roots with their locked provider schemas in an isolated copy;
  run the supplied VM, LXC, template, cluster and API-endpoint mock plans.
- [ ] Complete live stage acceptance, failover and clean-target recovery on the selected infrastructure.
- [ ] Supply or qualify an independent pre-Headlamp OIDC login client/token and namespace RBAC.
  The serial API rollout does not create that verification path; do not mark API human SSO
  accepted simply to pass the later Headlamp installation gate.

No deployment state or remote infrastructure was changed by this source review.

Validation completed in isolated WSL copies: all 21 Terraform roots passed schema
validation and 86 native mock plan cases passed; 94 source playbooks and their generated
copies passed 188 syntax checks. Clean focused runs passed 72 documentation/journey
checks, 30 source/payload/first-run checks, 26 figure/correspondence checks and seven
late-stage/PKI command checks. A final 20-check refresh/link/correspondence run passed
after correcting the retired-route fixture. These runs overlap. Snapshot secret scans
reported no leaks. This is source qualification, not live service or recovery acceptance.

After the stable-disk correction, the volume/issuer/receiver/intake and payload run completed
29 tests: 20 passed and nine root/private-mount/loop-device cases were skipped. Guard probes,
source/generated syntax and mocked VM/disk plans passed; actual formatting, mounts and
growth still need the isolated native storage fixture or target acceptance.

### Capability and reader-journey review, 2026-11-11

- [x] Trace Foundation and all ten deployment stages to their IaC entry points, architecture
  and operations routes. Align the readiness and implementation-support tables with those names.
- [x] Correct the Stage 9 VM option's return to runner selection and separate the Stage 8
  VM integration requirements from the Kubernetes path.
- [x] Align the generated software-intake checklist with the new-cache and existing-supply
  alternatives. Preserve compatibility links to the headings of locally retained documents.
- [x] Clarify the logging receiver count, database availability, optional integrations and
  Windows client acceptance without treating a design or local check as a live result.
- [ ] Qualify the selected paths on the target infrastructure, including recovery and failover.

The follow-up automation audit above supersedes this pass's observability, HSM-provider and
GitLab VM OIDC implementation gaps. Lab self-service allocation and its portal are not supplied.
Foundation hosts, networking and storage remain commissioned prerequisites.

Verification: focused WSL runs passed 27 navigation/migration/ownership checks and
32 capability, generated-documentation and deployment-path checks (the runs overlap).
The source sweep checked local links and 21 documented IaC entry points. The full
regression run was interrupted; its initial ownership-test failure was corrected and
passed separately, while native environment-dependent checks were skipped. No live
deployment, failure or recovery was performed in this review.

### Controller and cache repair follow-up, 2026-11-10

- [x] Check the selected network-filter Python dependency independently of collection presence.
  Install OS `python3-netaddr` or the active venv's declared requirement; `check` remains acquisition-free.
- [x] Expose explicit approved DNF baseurls for existing selected sections, preserving keys,
  verification settings, other repositories and timestamped backups. Explain dynamic-mirror limitations
  in the bootstrap path and distinguish source selection from the cache allowlist.
- [x] Select cache `scsi1` by its existing stable by-id identity. Replace the legacy unguarded
  filesystem sequence with Shared data-volume qualification before stopping Squid or preparing storage.
- [x] Reject malformed VIP prefixes, including a retained placeholder marker and `/0`.
  Require every keepalived member in the active play/batch before gathering facts or stopping its owner.
- [ ] Finish live acceptance after correcting site disk/prefix inputs: qualify both service members,
  VIP prefix/ownership, source retrieval, takeover/restoration, denied destinations and ordinary OS refresh.

Evidence so far: 10 controller/dependency/syntax checks passed; five Python-runtime checks passed
(OS acquisition simulated, venv pip/filter execution native); four source-selection checks passed
against temporary files; four VIP-gate checks covered 14 native inventory/play scenarios. Native
invalid-input and source/generated-link checks passed. Live feedback confirmed OS netaddr 1.3.0;
remaining cache/storage/network acceptance is separate from those local fixtures.
The cache-volume follow-up passed six regressions and eight Shared volume checks without skips:
OS/partitioned/root devices stop before service/storage changes, accepted volumes retain identity,
and blank-volume preparation uses the Shared UUID path. Device/service/filesystem boundaries in
the cache integration fixture are simulated; no live block writes or mounts were performed locally.
Live inspection identified reversed Linux disk letters and the existing scsi1 by-id link on both guests.
The malformed VIP input retained a placeholder marker; the unconfigured peer still had stock keepalived
addresses. Corrected site inputs and a complete pair rerun remain required for operational acceptance.

### Galaxy acquisition behind the cache, 2026-11-10

- [x] Select `ansible.utils` for cache CIDR validation before guest changes, retaining its
  collection bounds and controller `netaddr` dependency in source/generated output.
- [x] Include the Galaxy API and document explicit artifact-route approval or prepared archives;
  do not make one observed regional redirect hostname a universal dependency. Document retained-policy
  adoption and the one-time approved-source repair for an existing cache.
- [x] Use native Galaxy `--no-cache` acquisition to bypass malformed API-response metadata;
  preserve installed collections, version bounds, TLS/proxy policy and offline `check` behavior.
- [x] Reproduce the poisoned-response failure and real collection installation through a loopback
  proxy; verify retained collection/cache files and an idempotent, network-free second run.
- [ ] Complete site acceptance after proxy denial and subsequent VIP connection timeout:
  verify services/VIP ownership, approved API plus redirected artifact download and denied destinations.

Validation: 11 focused controller/version/link/preflight checks passed; two Squid-binary checks were
explicitly skipped in that harness. The new native metadata-cache regression passed on Ansible
2.16 and 2.21; removing `--no-cache` reproduced the failure. No live cache changes were executed.

### Numbered guide ownership follow-up, 2026-11-10

- [x] Name the dedicated bootstrap consumer guide for Stage 1 Step 6 and the infrastructure
  monitoring guide for Stage 8 Step 3; keep their README entry and return points explicit.
- [x] Keep cache installation in the Stage 1 README and update reconciliation in option 2b.
  Move policy/tuning lookup to reference, removing repeated installation instructions.
- [x] Group reusable logging, monitoring, Observability and isolated-cluster guides under
  their stage's procedures directory. Preserve diagrams, implementation and lifecycle scope.
- [x] Update source/generated links, source pointers and direct refresh-migration targets;
  check numbered filenames/titles and separation of steps, procedures and references.

Validation: 564 portable cases, including 240 explicit tool-dependent skips. The first run exposed
two documentation-coverage checks: an option-only filename assumption and missing checklist rows.
Both were corrected and passed focused reruns; all other executed portable cases passed.
All 20 focused navigation, source/generated-link, graph and source-pointer checks passed.
The guide-command/monitoring fixture run passed 12 checks with three explicit root-only skips.
All 220 public pages remain reachable/referenced; moved Mermaid bodies are unchanged.
No live deployment or hosted-renderer acceptance is implied.

### Connectivity and consolidation follow-up, 2026-11-10

- [x] Trace all 220 public Markdown pages, including the root README, from the front door;
  no unreachable pages or pages without incoming references remain.
- [x] Add whole-manual source/generated reachability checks, including diagram assets and
  detection of orphan cycles. Keep selectable deployment-path checks separate and stricter.
- [x] Consolidate refresh, developer dependency setup, host registration and partial-publication
  recovery into their existing authoritative guides, with explicit return points.
- [x] Remove the repeated architecture service inventory and centralize search permissions,
  tenant separation and retention detail. Retain task-local commands, prerequisites and short summaries.
- [x] Recheck affected local links and the consolidated OpenSearch access references.

Validation: **561 portable cases; 322 passed and 239 explicit native/tool-dependent skips**.
All 12 targeted security-contract, source/generated link and reachability checks passed.
The isolated redacted secret scan and final staged-file whitespace check also passed.

The earlier operational and external-link exclusions still apply. Publication is explicitly
authorized in this follow-up; preserve the configured signed-commit policy.

### Repository audit, 2026-11-10

Reviewed the front doors, all 219 public documentation pages, generated repository
navigation and all ten stage-to-IaC paths. The deployment subtree has 91 guides,
including 30 numbered option files. This is source/local qualification, not live acceptance.

- [x] Align numbered choices, dedicated filenames, branch returns and legacy link migration;
  separate bootstrap preparation from Proxmox-specific guides.
- [x] Place verified intake after accepted logging/trust at Stage 3 option 3b, and host hardening
  after service hosts exist. Correct detailed coverage tables and retired source/runtime doc links.
- [x] Preserve manual-cluster credentials through later guides, qualify Talos 1.13.x before
  image/node selection, and disclose the manual-cluster SSO implementation gap before that choice.
- [x] Supply the optional Stage 6 `mon-1` VM/disks through the existing foundation root/state;
  preserve issuer/directory maps, run Terraform only, then baseline, enroll logging and install monitoring.
  Keep the existing-host alternative and single-monitor outage limits explicit.
- [x] Correct receiver/export target selection, actual host connection inputs, native render commands,
  accepted-registry pipeline examples and required certificate enrollment handoffs.
- [x] Align implementation diagrams, source/input links, completion records and VMID reservations;
  keep deployment allocations out of figures and retain stable architecture role labels.
- [x] Replace three missing external references: Flux community chart documentation, Vault snapshot
  commands and the RHEL bootc catalog page. HEAD false negatives were retried with GET.

Validation:

- Full portable suite: **558 cases; 319 passed, 239 explicit native/tool-dependent skips**.
- **21 Terraform roots** validated with tracked locks and cached providers; **86 mocked cases** passed.
  The optional monitor also passed before/after mocked plans, retaining the original three guests.
- Two bounded native/source/generated runs passed: **81 cases (10 explicit skips)** and **34 cases**.
  These include real module/task/configuration paths against disposable local fixtures, not remote hosts.
  The final documentation-only changes passed **25 targeted monitoring, diagram, link and navigation checks**.
- **543 YAML files, 27 Bash scripts and 133 Python files** passed source syntax/duplicate-key checks.
- Amended figures rendered locally with Mermaid 11.17.2 on light/dark backgrounds at normal/narrow
  widths; nested-heading clipping was corrected. Hosted-renderer parity remains a separate review.
- **550 distinct public pages** were probed. Three confirmed missing links were replaced;
  26 pages remain unverified because of access controls, throttling, TLS trust or timeout.
  URL reachability does not establish that every cited claim or remote fragment is correct.

Live outage, recovery, identity, durability and denial checks remain unchecked in
[operational verification](operational-verification.md) and
[platform acceptance](platform-verification.md). Remaining alternative implementations
and intake integration work stay in their respective unchecked lists below.

<details>
<summary>External pages requiring manual verification (26)</summary>

- [ ] [HTTP 403](https://developers.redhat.com/articles/2026/02/12/how-build-image-mode-pipeline-gitlab)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/installing_and_using_dynamic_programming_languages/installing-and-using-python)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_file_systems/index)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_external_red_hat_utilities_with_identity_management/setting-up-samba-on-an-idm-domain-member)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/managing_idm_users_groups_hosts_and_access_control_rules/managing-public-ssh-keys-for-users-and-hosts)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_image_mode_for_rhel_to_build_deploy_and_manage_operating_systems/introducing-image-mode-for-rhel)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/managing_smart_card_authentication/managing_smart_card_authentication)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/installing_and_using_dynamic_programming_languages/assembly_installing-and-using-python_installing-and-using-dynamic-programming-languages)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/securing_networks/using-shared-system-certificates_securing-networks)
- [ ] [HTTP 403](https://docs.redhat.com/en/documentation/red_hat_satellite/6.18/html/configuring_capsules_with_a_load_balancer/installing-and-configuring-the-load-balancer)
- [ ] [HTTP 403](https://files.openstack.org/docs/keystone/latest/index.html)
- [ ] [HTTP 403](https://fedora.gitlab.io/bootc/docs/bootc/base-images/)
- [ ] [HTTP 403](https://help.ui.com/hc/en-us/articles/19133507506711-Configuring-MC-LAG-in-UniFi-Network)
- [ ] [HTTP 403](https://help.ui.com/hc/en-us/articles/26136855808919-Switch-Port-VLAN-Assignment-Trunk-Access-Ports)
- [ ] [HTTP 403](https://help.ui.com/hc/en-us/articles/360007279753-Port-Aggregation-FAQs)
- [ ] [HTTP 403](https://help.ui.com/hc/en-us/articles/360012622613-UniFi-Device-Adoption)
- [ ] [HTTP 403](https://static.openstack.org/docs/keystone/2024.1/admin/cli-manage-projects-users-and-roles.html)
- [ ] [HTTP 403](https://support.hashicorp.com/hc/en-us/articles/10773573595923-How-to-restore-a-snapshot-to-a-Vault-cluster-running-on-Kubernetes)
- [ ] [HTTP 403](https://www.cisa.gov/audiences/small-and-medium-businesses/secure-your-business/back-up-business-data)
- [ ] [HTTP 403](https://www.cisa.gov/sites/default/files/2023-01/fact-sheet-implementing-phishing-resistant-mfa-508c.pdf)
- [ ] [TLS trust](https://www.haproxy.com/documentation/haproxy-configuration-manual/new/latest/management/)
- [ ] [TLS trust](https://www.haproxy.com/documentation/haproxy-configuration-tutorials/protocol-support/tcp/)
- [ ] [TLS trust](https://www.haproxy.com/documentation/haproxy-configuration-tutorials/reliability/health-checks/)
- [ ] [HTTP 403](https://www.hhs.gov/hipaa/for-professionals/security/guidance/cybersecurity-newsletter-october-2022/index.html)
- [ ] [HTTP 429](https://www.hashicorp.com/en/trust/security)
- [ ] [Timeout](https://www.cyber.gov.au/publication/best-practices-for-event-logging-and-threat-detection)

</details>

### Previous review, 2026-11-09

The 2026-11-09 repository-wide follow-up traces the ten stages and alternatives from
documentation through generated repositories, local inputs, entry points and actual
Terraform/Ansible implementation. It also checks architecture placement, backup custody
and recovery state. The earlier guide-only results above are historical evidence.

- [x] Correct selection-scoped database preparation so Vault/Headlamp-only runs install and configure their products.
- [x] Install the logging verifier's complete dependency set on independent recovery hosts.
- [x] Bind saved template plans to reviewed inputs, configuration and execution targets before apply/refresh.
- [x] Stop template publication when cloud-init cleanup fails.
- [x] Correct runner registration for package-created empty configs and modern authentication tokens;
  enforce the selected Kubernetes context and required GitLab TLS Secret type.
- [x] Align Observability source/API/kubelet CIDRs and Netdata ACLs to current cluster inputs;
  keep independent Tier 0 monitoring on Management with later-tier export disabled initially.
- [x] Align architecture placement, Grafana/registry coverage, bootstrap recovery and direct-CI trust
  with their installers. Keep resource ownership separate from hosting and network access.
- [x] Correct fresh repository quick starts and retired source-side documentation links;
  retain project inputs/state and the explicit refresh conflict policy.
- [x] Move the Tier 1 service-capacity decision before cluster provisioning; the compact bootstrap
  profile alone is insufficient for the complete Delivery/Observability/development stack.

Validation of the integrated changes:

- Full portable suite: **458 cases; 286 passed, 172 explicit native/tool-dependent skips**.
  Final Management monitoring inputs also passed their two focused source/generated checks.
- All **20 Terraform deployment roots** validated using tracked locks and cached providers;
  **86 mocked Terraform cases** passed. No real provider apply or original state was used.
- **495 YAML files, 26 Bash scripts and 113 Python files** passed source syntax checks;
  **583 documentation Bash blocks** parsed without execution.
- Five figures in the three amended architecture pages rendered in **20 theme/width combinations**
  and were visually inspected. Local Mermaid 11.17.2 does not establish hosted-renderer parity.
- Native phase/selection, template-plan invalidation, cleanup refusal, runner/Secret/network gates,
  encrypted backup/restore and scoped telemetry replay checks exercise actual task/helper paths
  against disposable local fixtures. They do not accept live infrastructure.
- Native qualification was split across bounded runs, not one clean full-native invocation.
  Expired Collector/chart paths and missing syslog validator libraries were repaired in the local
  harness; affected Collector, Observability and receiver cases passed reruns. The unchanged extended
  Spinnaker variant sweep was stopped after main-reference source/generated rendering passed.
  Root/mount-namespace backup tests, native rsyslog/GnuTLS sender tests and unavailable-tool cases
  remain explicit exclusions; do not interpret the portable skip count as native acceptance.

The [implementation map](../docs/08-reference/implementation-support.md#stage-coverage)
remains the public source of truth. Client-auth certificate issuance is a commissioned
integration; the default issuer profile supplies server certificates. Kubernetes SSO
qualifies Talos 1.13, not 1.14. Hardware HSM/ACME and tenant allocation retain their
explicit integration boundaries. Follow [platform acceptance](platform-verification.md)
and [operational verification](operational-verification.md) before checking live results.

## Software-intake review, 2026-11-10

- [x] Keep the existing Tier 2 cache pair; require explicit clients/sources, preserve HTTP
  privacy/freshness, reject unsafe retained rules, and test denied requests as well as successful retrieval.
- [x] Emit sanitized JSON access decisions and document later per-host Tier 0 forwarding.
- [x] Apply native package verification/failure defaults independently of proxy selection, including
  bootstrap mirror mode and Proxmox's separate policy file. Repository overrides remain a reviewed boundary.
- [x] Define staged verification, quarantine and promotion as an optional Tier 1 design, not an installer.
  Keep malware detection, publisher authentication and vulnerability assessment distinct.

The subsequent verified-intake implementation adds the optional Tier 1 `intake` setup and
source-mapped [deployment guide](../docs/03-deployment/stage-03-trust/step-15b-verified-intake.md).
It supplies native RPM/APT acquisition, copied-content verification, ClamAV gates, private quarantine,
immutable HTTPS publication and scheduling. Terraform supplies its VM/disks; guarded Ansible supplies
the dedicated filesystem and UUID mount. The single worker still requires approved native tools,
trust material and current definitions; it is not HA or automatic patch management.
Live acceptance remains [INTAKE-6–9](operational-verification.md#software-intake).

Proposal-completeness review, 2026-11-10: the core staged-intake installer is supplied;
the following implementation/integration work remains before the entire proposal is covered:

- [x] Supply [tier-owned native consumer recipes](../docs/03-deployment/stage-03-trust/step-15b-verified-consumers.md)
  for RPM/APT selections, publisher keyrings, public trust and strict metadata refresh.
  Independent network bypass denial remains a live acceptance check, not an Ansible assertion.
- [ ] Add intake-specific health metrics and severity-based alerts: definition age, scanner/job
  failure, last successful intake and quarantine/storage capacity. Generic Netdata/OpenSearch
  installation and local error-priority syslog events do not supply these rules.
- [ ] Connect the worker/cache decision streams to explicit Tier 0 source registrations and
  approved OpenSearch projections. Existing logging automation is reusable, but the intake installer
  does not commission that path. Add run/incident and candidate-hash correlation without inventing
  a requesting client for a scheduled pull or exposing private URLs/scanner diagnostics.
- [ ] Automate or accept an existing independently retained Tier 0 critical-software supply.
  Selecting a URL on intake-1 alone does not retain usable packages/tools outside Tier 1/2 failure.
- [ ] Complete the optional OCI publisher-verification and vulnerability-policy promotion path.
  Harbor installs Trivy later; that does not connect Cosign or a Trivy gate to this worker.
- [ ] Define and qualify a separate VM-image intake path if templates are included in staged supply.
  The current worker deliberately holds raw/qcow2/ISO and other opaque images; scanning the outer
  file must never be described as checking every guest file.
- [ ] Record the proposal's selected NIST control-to-implementation/test/evidence mapping.
  Product selection and design descriptions alone are not an accepted control-evidence record.

Live network/failover, current-definition scans, confinement, delivery and restore results remain
in [INTAKE-1–9](operational-verification.md#software-intake), separate from this implementation list.

Guest-storage automation review, 2026-11-10: normal intake, logging and issuer deployment now
prepares dedicated filesystems and persistent UUID mounts through Shared's guarded data-volume
role. The issuer also manages its database bind; backup recipes manage their selected client/disk
mounts. No manual guest mkfs/fstab prerequisite remains on those new-install paths. Independent
NAS commissioning, existing-service adoption and signing/recovery custody remain explicit.
Native disposable XFS (Ansible 2.16.16) and ext4 lifecycle tests passed creation, unchanged reruns,
growth, retained data/UUIDs, declared binds and refusal of missing-volume replacements.
Nineteen focused native storage/NAS/backup checks passed; CA loopback provisioning, retained
database ownership, refusal gates and source/generated syntax passed separately.
The portable suite ran 518 cases with 226 explicit skips and one stale guide-wording assertion;
that assertion was corrected and the five affected correspondence/documentation checks passed.
Source syntax and light/dark intake figures at normal/narrow widths also passed local checks.
These results do not satisfy [STORE-3](platform-verification.md#capability-gates) or any live
reboot, Proxmox, NAS-outage or recovery acceptance gate.

Verified-extension evidence: the portable regression run completed **493 cases: 287 passed,
206 explicit native/tool skips**. Separate native fixtures passed 19 RPM/APT adapter cases,
12 artifact-pipeline cases (one current-definition positive explicitly skipped), nine focused
runtime gates, source/generated installer checks and Terraform mocks/correspondence. These use
disposable local HTTPS, GPG, RPM/APT, ClamAV and Nginx fixtures, not a live deployment. Positive
artifact scans used a disclosed old upstream CVD with fixture-only age relaxation; production
still enforces its configured 1–7 day bound, and the default two-day stale rejection passed.
Current official database download returned HTTP 403. Real EL10/RPM6, systemd confinement,
SELinux, network cutover, independent forwarding and restore remain unverified.
The final source/generated HTTPS timestamp and private native logrotate checks also passed;
local rotation does not replace protected forwarding. All 600 guide Bash blocks passed syntax
checking; YAML/Python/Bash source validation and diff whitespace checks passed. The three new/
updated figures were inspected in light/dark at normal and narrow widths; hosted parity remains manual.

Evidence: the portable suite passed **468 cases: 286 passed, 182 explicit native/tool skips**.
The integrated native profile reported **18 passed and four explicit root/parser skips**;
the separate 12-case package/bootstrap run passed those Ansible 2.16 and root fixtures too.
Real Squid exercises source/generated ACLs, caching/revalidation and JSON privacy. Native APT exercises
transient refresh failures, unsigned/expired metadata and the source-level `trusted=yes` exception.
DNF configuration/idempotence is tested; a native DNF engine and live hosts were not available.
The new architecture figure was rendered/inspected in four light/dark and reading-width combinations;
hosted-renderer parity and [INTAKE-1–5](operational-verification.md#software-intake) remain manual.

## Current journey verdict

The engineer can generate repositories and follow native installation recipes for
all ten selected capability stages. This is a staged, commissioned platform, not
a zero-touch appliance or an operationally accepted deployment.
The first security gate is verified Proxmox API trust; all supplied Terraform roots
now verify TLS, and provisioning entry points reject inherited insecure flags.
Stage 2 now has a selected Linux/NAS main path: reviewed-CSR producer trust, native
host forwarding, create-only checkpoints, audited file views and independent encrypted
backup. NAS snapshots/accounts and the recovery filesystem require commissioning;
physical faults and access/restore results remain manual verification. This is
asynchronous bounded-loss custody, not replicated/lossless intake. The Stage 3 policy issues
TLS-server leaves, not producer client-auth certificates. Do not bypass that gate to
declare a production PKI or assume Stage 3 automatically replaces producer trust.

The generated collection keeps resources, inventory, inputs and state tier-local.
Shared owns native chart execution and reusable cluster roles. Tier-owned application
recipes now cover platform add-ons, Identity, Secrets, Delivery, Observability,
the development platform and a bounded lab application. Empty GitOps directories
remain adoption points, not the installation executor. Direct infrastructure CI
explicitly trusts the dedicated GitLab project and its control/hosting authorities.

The [stage coverage](../docs/08-reference/implementation-support.md#stage-coverage)
is the authoritative installation/prerequisite map. Independent API endpoints,
prepared storage, approved images, certificate custody, external GitLab data services
and selected product interfaces still require commissioning. Separate API-endpoint and
GitLab data-service setups supply those reference realizations. Storage uses its actual
commissioned native interface, without a NAS object gateway. Existing qualified services
remain valid. Native Spinnaker and Argo CD are explicit alternatives.
Optional HSM and tenant allocation are not silently supplied. Household/team,
maintenance and product-recovery procedures exist; live qualification remains open.
No live acceptance box is checked by this consistency review.

## Corrected reading and execution gaps

- [x] Review complete task sequences, not only wording within inherited phase headings.
- [x] Test intake before host cutover; retire temporary WAN access only after its replacement works.
- [x] Complete foundation checks after HA/SDN branches; document actual workspace disk preparation.
- [x] Initialize and register existing Proxmox hosts before host recipes; separate SSH administration
  from API provisioning and the foundation guest deployment.
- [x] Prepare receivers before exporters, product runtimes before their backup tests, and original
  state before CI handover. Keep incomplete alternatives separate from runnable installers.
- [x] Make the front door distinguish runnable workflows from integration starters.
- [x] Keep foundation prerequisites outside numbered capability stages; logging remains Stage 2.
- [x] Prevent the Proxmox preparation guide from skipping logging and jumping to identity/clusters.
- [x] Add gateway/controller adoption and VLAN/port preparation before the UniFi policy matrix.
- [x] Distinguish ordinary client access ports from server trunks and supported multi-switch aggregation.
- [x] Put the existing Linux-provider TLS exception in the API setup gate, not only the HA guide.
- [x] Document verified Proxmox bootstrap trust and optional API certificate migration after PKI.
- [x] Add a logging fault/restore drill, seed-owned evidence record and offline reconciliation checks.
- [x] Supply a Tier 0 syslog-ng receiver with mount/TLS guards, raw JSON records and native local tests.
- [x] Explain that `--env` does not allocate unique VMIDs, addresses, VIPs or security boundaries.
- [x] Keep directory deployment in the trust stage's existing context/state instead of silently switching to test.
- [x] Put cache initialization, exact input edits and deployment directly in Stage 1's main path;
  expose existing approved supply as branch 1b, rejoining at intake testing before host configuration.
- [x] Initialize test inputs before VM source-control, runner and image-builder commands.
- [x] Use one normal Linux deployment command with Terraform's inline plan/approval;
  keep preview opt-in, unattended CI explicit, and dedicated saved-plan/signing/activation gates intact.
- [x] Add Vault CLI endpoint/trust selection and authentication before audit configuration.
- [x] Remove repeated identity-authentication and Vault-shape explanations in favor of their authoritative homes.
- [x] Align generated setup ownership and template references with logging and unnumbered foundation.
- [x] Use an ignored Python virtual environment for the generator dependency instructions.
- [x] Reproduce and fix missing-role failures in direct PKI/scheduler commands; test the documented invocations.
- [x] Connect edge publication and total-loss recovery to the new HTTPS and issuer-restore procedures.
- [x] Separate NAS-backed trusted-admin retention from optional storage-enforced locks;
  link both Stage 2 branches and record custody/review triggers in the evidence template.
- [x] Use `syslog` in fresh Tier 0 README quick starts, in the same base state context as
  Stage 2; link environment isolation beside optional `--env`, and retain storage/TLS preparation gates.
- [x] Point test source-control, runner and image-builder instructions at their selected
  Ansible test vars and explicit complete-map Terraform overlays, including final conversion.
- [x] Prepare/test local-input recovery before provisioning; test guest restore after the
  first disposable clone, and accept verified existing backup services without requiring PBS.
- [x] Clarify the independent producer-authority handoff instead of assuming the software
  PKI's TLS-server profile also issues logging client certificates.
- [x] Align remaining IdP wording and the image-builder's shared-catalog comment with their authoritative contracts.
- [x] Align fresh FreeIPA inputs with the sibling-CA design; preserve existing internal-mode local inputs.
- [x] Keep Stage 3 issuer acceptance separate from Stage 5 identity and later public-edge deployment.
- [x] Move the numbered hardware-rollover procedure into administration and preserve managed-guide redirects.
- [x] Disclose installer coverage before every main path; make the delivery outcome conditional.
- [x] Rejoin the observability VM alternative at source/reader checks after its project-owned service
  installation, never the Kubernetes installer; disclose missing Netdata capacity/installation.
- [x] Check the moved Stage 5 IdP and actual Stage 6 Vault/NetBox/Headlamp starters against deployment figures.
- [x] Default newly initialized local files/backups and deployment working files to private permissions;
  existing file access, Windows ACLs and off-host recovery still require manual verification.
- [x] Remove unused baseline SSH/package/firewall/NTP switches and disclose the implemented baseline scope.
- [x] Keep new-host security logging early; add explicit directory/delivery handoffs and a cluster audit gate.
- [x] Keep the logging recovery host/copies inside Tier 0 ownership while retaining separate failure/custody boundaries.
- [x] Restore the May software-intake intent as an explicit design; distinguish HTTP caching,
  HTTPS forwarding, retained mirrors, internal HTTP and target-tier update authority.
- [x] Reject empty software-source lists and remove Squid's unrestricted remote-client fallback.
- [x] Number Software intake as Stage 1 and Kubernetes as Stage 4, separate from foundation and identity;
  connect later Stage 7 Harbor/OCI supply without creating a bootstrap dependency.
- [x] Expose native Kubernetes-node image-access inputs in all three tier roots;
  retain Linux/Talos separation and require live supply/egress acceptance separately.
- [x] Preserve LF endings in source Bash entry points and compare generated text independent of checkout endings.

## Implemented priority mechanisms

- [x] **P1: Secure provider defaults (implementation).** All supplied Terraform roots explicitly
  verify Proxmox TLS. Linux, Kubernetes and template entry points reject true or malformed
  current/legacy insecure environment flags before Terraform. Bootstrap uses independently
  verified Proxmox CA trust; no automatic verification bypass is needed.
- [x] **P1: Initial trust (selected software implementation).** Native policy construction,
  explicit key/CSR preparation, offline root templates, token/CRL procedures, encrypted
  backup/clean-target restore and phased FreeIPA installation are supplied.
  Optional HSM/internal-ACME work remains separate in the [CA checklist](ca-implementation.md).
  This checks mechanism coverage, not package qualification or operational acceptance.

- [x] **P1: Logging integration - sources (selected Linux path).** Shared isolated native
  rsyslog journal/file instances with host-local keys, disk queues, cursors and independent
  source health checks; tier-local recipes/inputs include collector OS, audit and CA files.
  Native cluster-source collection has its own recipe and per-node identities;
  appliance firmware still requires product-native configuration. Register unsupported
  devices and actual kernel/runtime source gaps in the live record.
- [x] **P1: Logging integration - producer trust.** Protected Tier 0 native CSR signing,
  explicit initialization, encrypted CA key, bounded leaf renewal and cumulative CRLs;
  source private keys never leave their hosts. Client/server profiles and key fingerprints
  are explicitly approved. Existing-session withdrawal/CRL distribution remain operator recipes.
- [x] **P1: Logging integration - durable archive (NAS main path).** Create-only complete
  JSONL chunks, source catalogue, hashed linked checkpoints, cursor-after-NAS ordering,
  bounded source queues and independent health gates. Native sender release is transport-based;
  exposed tails and replay windows are explicit. No replicated-intake or zero-loss claim.
- [x] **P1: Logging integration - custody (trusted-admin NAS).** Separate transfer/read/backup
  credentials, NAS-owned snapshot commissioning contract, independent restic jobs with no prune,
  offline verifier and restore procedure, native raw/view read audit and fixed application-only
  filesystem views. Actual NAS grants/snapshots/audit and physical independence need live proof.
  [Locked retention](../docs/03-deployment/stage-02-logging/step-15b-retention-lock.md), replicated intake
  remain separate variants, not supplied by this NAS implementation. Tier 1 search is
  independently installed; approved projections and their scoped persistent exporter
  have a separate Tier 0 recipe and require live access/replay qualification.

## Remaining implementation before an end-to-end installation

Secure provider defaults and the selected software-first Initial Trust mechanisms are
supplied. Their live proof is tracked in the separate
[manual verification list](operational-verification.md), not mixed with missing implementation.

- [x] **P1: Cluster endpoint contract.** Private independent endpoint, DHCP/MAC, DNS/time
  and storage are explicit pre-bootstrap prerequisites; no public Tier 2 edge dependency.
- [x] **P1: Cluster services.** Native pinned platform, SOPS/decryption and per-node
  protected collection recipes replace the empty-starter installation gap. The
  [cluster foundation](../docs/03-deployment/stage-04-kubernetes/procedures/kubernetes.md#cluster-foundation)
  still requires live endpoint, persistence, audit and recovery acceptance.
- [x] **P1: Control application installers.** Native Keycloak, Vault, NetBox and Headlamp
  recipes include data dependencies, scoped authentication and explicit recovery gates.
  Manual initialization, enrollment and independently commissioned backup custody remain visible.
- [x] **P1: Independent monitoring and Observability installers.** Tier 1 native product
  releases and Tier 0 scoped infrastructure polling/export are supplied. Their budgets,
  replication/read routing and source coverage are explicit, not inferred from pod count.
- [ ] **Alternative: manual-cluster human SSO.** The guarded supplied rollout requires
  the original Terraform-owned plan. The manual cluster branch needs its own configuration
  persistence, reviewed rollout and recovery implementation before it can pass the complete
  Identity/Headlamp path. This is an implementation gap, not merely an unperformed live test.
- [x] **P1: Product integration mechanisms.** Tier 0 supplies approved-copy publication,
  non-root mTLS export, GET-only NetBox audit capture and independent native Vault
  snapshot/input/media transport. Search copies never acquire original-archive authority.
  Exact native qualifications and release gates are tracked in [implementation readiness](v1-readiness.md).
- [x] **P1: Recovery procedures.** Product-specific clean-target procedures cover original
  inputs/state/etcd, Vault, databases/media, identity and shared products. They do not
  equate a new bootstrap, replica count or successful backup with recovery acceptance.
- [x] **P1: Host security implementation.** Separate guarded tier-local recipes call
  Shared's native key-only SSH, chrony, firewalld and audit profile. Site allowlists,
  effective controls, out-of-band access and product compatibility still require verification.

Destructive-change drills, actual exposure enforcement and clean-room restores belong
to [manual operational verification](operational-verification.md) and
[platform acceptance](platform-verification.md). None is checked by supplying these mechanisms.
The separate tenant request dispatcher/allocation/expiry/portal is deferred, not part of
the selected v1 reference. The direct trusted-CI path is not an ordinary-user self-service boundary.

## Paths reviewed

"Reviewed" below means the entry, owner, branch/return and automation boundary were
inspected. Every selected path still needs its own live acceptance evidence.

| Path | Entry | Review outcome / remaining proof |
| --- | --- | --- |
| Bootstrap workspace | [Foundation 3a](../docs/03-deployment/foundation/bootstrap/step-3a-bootstrap-storage.md) | Local filesystem, persistent UUID mount and reboot path; independent backup/restore proof remains manual |
| Bootstrap LVM root | [Foundation 3b](../docs/03-deployment/foundation/bootstrap/step-3b-bootstrap-lvm.md) | Disk/PV/root growth or added PV; verify the real layout and retain every required disk in recovery copies |
| Bootstrap home bind | [Foundation 3c](../docs/03-deployment/foundation/bootstrap/step-3c-bootstrap-home.md) | Ownership, SSH and SELinux checks before repository/key creation; console/reboot/rollback proof remains manual |
| Offline bootstrap tooling | [Foundation 3e](../docs/03-deployment/foundation/bootstrap/step-3e-bootstrap-offline.md) | Matching OS/Python/CPU, verified bundle/provider artifacts; does not imply every later stage is disconnected-ready |
| Alternative balancing | [Foundation 10b](../docs/03-deployment/foundation/proxmox/step-10b-proxlb.md) | ProxLB qualification after API and a movable guest exist; one scheduling owner and live failover proof required |
| Existing cache update | [Software intake 2b](../docs/03-deployment/stage-01-software-intake/step-2b-adopt-update.md) | Preserve original inputs/state, refresh automation and retest consumers; verified worker installation remains Stage 3 |
| Windows Update | [Software intake 7b](../docs/03-deployment/stage-01-software-intake/step-7b-windows-update.md) | Review source and client scope, configure the chosen route and validate a representative Windows consumer |
| Bootstrap intake | [Software intake Steps 10-13](../docs/03-deployment/stage-01-software-intake/procedures/bootstrap-consumer.md) | Apply the accepted endpoint, activate the shell and prove package/tool access before retiring temporary egress |
| Infrastructure health | [Observability Step 13](../docs/03-deployment/stage-08-observability/step-13-infrastructure-monitoring.md) | Connect Tier 0-owned hardware/host collection and approved Tier 1 metric delivery; verify alerts and isolation |
| Protected search projections | [Observability 14b](../docs/03-deployment/stage-08-observability/step-14b-protected-log-search.md) | Tier 0-approved copies and scoped ingestion; test denial/replay without granting original-archive authority |
| Private application | [Lab 3a](../docs/03-deployment/stage-10-lab-environments/step-3a-application.md) | Native namespace/application path; verify access isolation, update/rollback and recovery |
| Public website | [Lab 4b](../docs/03-deployment/stage-10-lab-environments/step-4b-public-https.md) | Existing edge or explicitly provision it first; real DNS, origin TLS, renewal/failover and denied-route proof required |
| Workload signals | [Lab 5b](../docs/03-deployment/stage-10-lab-environments/step-5b-telemetry.md) | Scoped Collector, queues and distinct credentials; verify source-to-query delivery and recovery |
| Foundation | [Preparation](../docs/03-deployment/foundation/README.md) | Network, access, templates and recovery precede capability deployment; live commissioning required |
| Software intake | [Stage 1](../docs/03-deployment/stage-01-software-intake/README.md) | Early Squid/VIP path; independent bootstrap supply and later repository/Harbor extensions; no complete patch controller |
| Logging | [Stage 2](../docs/03-deployment/stage-02-logging/README.md) | Linux/NAS recipes supplied; actual NAS custody, devices, bounded-loss fault and restore acceptance outstanding |
| Trust | [Stage 3](../docs/03-deployment/stage-03-trust/README.md) | Software PKI, native YubiHSM/PicoHSM provider and original-key issuer operations supplied; qualify physical mechanisms, CA audit, ceremonies and live recovery |
| Kubernetes | [Stage 4](../docs/03-deployment/stage-04-kubernetes/README.md) | Native node/platform/audit recipes; independent endpoint, storage, enrollment and live acceptance required |
| Identity | [Stage 5](../docs/03-deployment/stage-05-identity/README.md) | Dedicated directory, Keycloak/LDAP and staged Kubernetes SSO; ceremony, accounts and live denial/recovery acceptance required |
| Secrets | [Stage 6](../docs/03-deployment/stage-06-secrets/README.md) | Native cluster Vault/NetBox/Headlamp and independent monitoring; initialization and qualified recovery custody required |
| Delivery | [Stage 7](../docs/03-deployment/stage-07-delivery/README.md) | Native platform/Harbor plus Argo CD or complete native Spinnaker; exact selected controller, targets and live acceptance remain explicit |
| Observability | [Stage 8](../docs/03-deployment/stage-08-observability/README.md) | Native Kubernetes signal backends/UIs and independent Tier 0 polling; scoped projections and live availability/access tests remain required |
| Development platform | [Stage 9](../docs/03-deployment/stage-09-development/README.md) | Native GitLab/runner charts and separate native data VMs, dedicated infrastructure runner, Vault JWT root and saved-plan handover; data/backup commissioning and live acceptance required |
| Lab environments | [Stage 10](../docs/03-deployment/stage-10-lab-environments/README.md) | VM/cluster, bounded application/policy/RBAC, scoped telemetry and opt-in HTTPS; profiles are not an allocator; live tenant acceptance required |
| Proxmox HA | [Foundation 1b](../docs/03-deployment/foundation/proxmox/step-1b-cluster-ha.md) | Quorum/storage/fencing separate from VM creation; physical failure tests outstanding |
| Guest SDN | [Foundation 1c](../docs/03-deployment/foundation/proxmox/step-1c-sdn.md) | Manual VNet setup; verify every eligible node and one tagging owner |
| Redundant logging | [Logging 14b](../docs/03-deployment/stage-02-logging/step-14b-redundant-intake.md) | Added hosts do not establish replicated commitment or retention |
| NAS-backed evidence | [Logging 15a](../docs/03-deployment/stage-02-logging/step-15a-nas-archive.md) | Checkpoint/backup/audit-view recipes supplied; NAS-owned snapshots/accounts and live failure/access proof remain commissioning |
| Retention-locked evidence | [Logging 15b](../docs/03-deployment/stage-02-logging/step-15b-retention-lock.md) | Stronger deletion boundary documented; actual lock mode, publication, replica and recovery integration still required |
| Shared USB HSM | [Trust 1b](../docs/03-deployment/stage-03-trust/step-1b-usb-hsm.md) | Native host/provider/remoting installation and original-key checks; physical key copies, application sessions and actual failure recovery remain acceptance |
| Network HSM | [Trust 1c](../docs/03-deployment/stage-03-trust/step-1c-network-hsm.md) | Vendor commissioning/client/HA procedure required |
| Single USB device | [Trust 1d](../docs/03-deployment/stage-03-trust/step-1d-single-usb.md) | Custody/backup procedure required; availability is not inferred from a token |
| Existing managed cluster | [Kubernetes 1b](../docs/03-deployment/stage-04-kubernetes/step-1b-existing-cluster.md) | Existing IaC lifecycle owner; adoption/restore distinct from fresh bootstrap |
| Vault VM | [Secrets 1b](../docs/03-deployment/stage-06-secrets/step-1b-vault-vm.md) | Supplied host/service recipe; initialization, authorization, audit forwarding and restore remain explicit |
| Seal choice | [Secrets 1c](../docs/03-deployment/stage-06-secrets/step-1c-seal-integration.md) | Shamir/Transit/PKCS#11 capability and edition checks; no automatic migration |
| Observability VMs | [Observability 1b](../docs/03-deployment/stage-08-observability/step-1b-dedicated-vms.md) | Native seven-host products, data mounts and two-parent/five-child Netdata; live service/recovery checks remain separate from Tier 0 monitoring |
| Independent signing API | [Secrets 11b](../docs/03-deployment/stage-06-secrets/step-11b-openbao.md) | Native OpenBao/plugin and original external-key mappings, scoped certificate clients and audit; native software-token integration passed, actual Yubi/Pico/HA/recovery proof remains |
| Operator hardware authentication | [Secrets 21b](../docs/03-deployment/stage-06-secrets/step-21b-hardware-authentication.md) | Enrollment and lost-token recovery are manual; retain break-glass access |
| Argo CD | [Delivery 2a](../docs/03-deployment/stage-07-delivery/step-2a-argocd.md) | Native installation guide; restricted projects, SSO, destination and rollback acceptance required |
| Spinnaker | [Delivery 2b](../docs/03-deployment/stage-07-delivery/step-2b-spinnaker.md) | Native installation guide; storage, service identities and pipeline commissioning required |
| Source-control VM | [Development 1b](../docs/03-deployment/stage-09-development/step-1b-source-control-vm.md) | Supplied container recipe; pin image, prepare TLS and verify product backup/restore |
| Kubernetes build runner | [Development 14a](../docs/03-deployment/stage-09-development/step-14a-kubernetes-runners.md) | Native runner manager and bounded job policy; approved runner identity, images, Secret ownership and live denied-job proof required |
| General build runner | [Development 14b](../docs/03-deployment/stage-09-development/step-14b-podman-runner.md) | Supplied host recipe; registration/credentials/trust required; no Tier 0 authority |
| Image-based Linux | [Development 15b](../docs/03-deployment/stage-09-development/step-15b-image-based-linux.md) | Conversion is distro/product-specific; retain source image and test rollback |

## User and operating paths still needed

- [ ] **P2: First useful private app.** Provide one small, complete service example from
  owner/allocation through deployment, authentication, TLS, scoped logs and restoration;
  avoid requiring every optional platform service merely to validate an application.
- [x] **P2: Household/team procedures.** [Access lifecycle](../docs/05-operations/04-identity.md)
  covers client/guest/IoT networks, outage behavior, role scopes and join/leave duties.
  Actual per-product mappings, session/token withdrawal and denied access remain live checks;
  no automatic cross-product role synchronizer is claimed.
- [ ] **P2: Remote entry and publication.** Public HTTP-01, origin verification and renewal
  now have a concrete guide/recipes. A chosen VPN/admin-entry path, complete private-app path
  and live DNS/NAT/IPv6, expiry-alert and failover checks are still needed.
- [x] **P2: Upgrade and hardware procedures.** [Maintenance](../docs/05-operations/01-hosting/maintenance.md)
  defines compatibility, recovery, canary/serial health gates and host replacement.
  No universal automatic patch or rolling-upgrade controller is supplied.
- [ ] **P2: State and local inputs.** Test OS file permissions, encrypted off-host copies,
  one writer per state and retained ignored inputs. Git history alone excludes live inventory,
  secrets and state, so cloning the private repositories alone is not a disaster recovery.
- [x] **P2: Secret scanning mechanism.** Native redacted staged/history/artifact commands
  and an unprivileged fail-closed CI example are supplied. Project merge enforcement,
  runner image admission and live leakage-response exercises remain administration duties.
- [x] **P2: Provider reproducibility.** All 20 retained deployment roots have tracked provider
  locks and pass isolated provider-schema validation. Retain these locks and qualify
  future updates deliberately; no live infrastructure plan or OpenTofu parity is implied.
- [ ] **P2: Cache hardening variants.** Implement client authentication or TLS/mTLS listener
  only for a selected requirement, with support/acceptance documented; keep the HTTP proxy
  reference's limits visible and avoid implying TLS interception is required.
- [ ] **P2: Wider software intake and patch management.** The selected Linux repository/artifact
  worker is supplied; Windows, OCI vulnerability gates and broader repository-management products
  remain optional integrations. Qualify retained releases without direct client WAN access.
  Add tier-owned maintenance recipes, test rings, reboot/health gates and patch-status evidence;
  Tier 1 content services must not acquire Tier 0 execution credentials. Product selection and
  implementation for those additions remain open; transparent/TLS-intercepting proxy modes are not supplied.
  The [staged verification/quarantine contract](../docs/01-architecture/07-software-intake/01-verification.md)
  defines policy, ownership and failure behavior; distinguish its implemented Linux reference from
  unimplemented target types and from site acceptance.
- [ ] **P3: Reading density.** Split historic generated-repository upgrade detail away from
  first-use contracts; separate advanced direct-mesh storage and large cache-sizing material
  from the main path. Preserve old anchors and generated-project edits when moving content.
- [ ] **P3: GitHub diagram review.** Inspect the hosted rendering and refine layout details
  separately. Local rendering does not prove hosted parity. Check labels, replica groups,
  tier ordering and layer placement rather than equating local render success with hosted visual acceptance.

## Manual operational verification

Follow the [manual verification list](operational-verification.md) for provider trust,
Initial Trust, protected logging and development-platform handover, then the wider walkthrough.
It states prerequisites,
pass conditions and evidence for each check. No live infrastructure was available for
this preparation; all operational checks remain unchecked.

Keep private evidence in the generated project's administration records. The logging
drill already has a seed-owned record; a source review or passing local test must never
be relabelled as a deployed-system pass.


## Repeat cadence

Implementation release review, 2026-10-27: added native Spinnaker with SQL/cache and
independent backup jobs, separate GitLab data services, native storage-interface contracts, private
cluster API gateways, host controls, approved log-copy export, NetBox audit and recovery
transport. The [release qualification](v1-readiness.md) records exact tests, corrected
fixture failures, exclusions and remaining gates; historical results below are not a
claim of a single clean current run. The platform/manual operational lists remain open.

Native platform implementation review, 2026-10-26: all ten selected stages now have
explicit native execution paths and commissioning contracts. Shared supplies reusable
platform/chart/cluster-source roles; tiers retain resources, inventory, inputs and state.
Added guarded serial Kubernetes OIDC, native control applications, Delivery and
Observability, scoped lab application/telemetry and protected infrastructure CI.
Native checks found and corrected the Talos hostname-document conflict and OpenSearch
discovery/first-cluster bootstrap configuration. Database schemas now match the selected
platform operator version.

The initial **256-case** full sweep reported six documentation/visual-contract failures,
all corrected; the final **91 affected regressions passed, zero skipped**. A separate
final **38 native application/configuration checks passed, zero skipped**, including
actual provider-generated Talos configurations and matching database schemas. All
**18 Terraform roots** validated and **33 mocked plan cases** passed. Repository syntax/
duplicate-key checks covered **357 YAML files, 21 Bash scripts and 66 Python files**.
Native cluster logging also exercised local mTLS rejection and crash/queue replay.

The full sweep skipped two existing fixture-dependent cases: native offline clca
and rsyslog/GnuTLS sender recovery. These are not closed by Fluent Bit replay tests.
Selected figures were rendered on light/dark pages at normal and narrow widths;
GitHub parity and live deployment, authorization, durability, failover and restoration
remain unverified. Use [platform acceptance](platform-verification.md) for live results;
optional/remaining integrations stay listed above rather than being called installed.

Development-platform review, 2026-10-26: Stage 7 selects Argo CD or Spinnaker;
Stage 9 owns GitLab/ephemeral runners, Vault CI roles and the dedicated `iac-1` runner;
lab environments move to Stage 10. Direct CI explicitly accepts GitLab and hosting
administrators as Tier 0 authorities. A bounded tenant allocator is not supplied.
External GitLab PostgreSQL, Redis, Gitaly and object storage remain commissioned prerequisites.

Offline evidence: **181 regression cases: 179 passed, two fixture-dependent skips**
(offline clca and native rsyslog fixtures). **36 subsequent focused checks passed,
zero skipped**, covering final
installer/dependency, source/generated payload, CI safety, documentation and refresh changes.
All **18 Terraform roots** passed provider-schema validation; **30 cluster mocks and
three Vault authorization mocks** passed. The five changed figures rendered in light/dark
themes at 1100px and 760px reading widths (20 combinations). GitHub renderer parity,
live installation, SSO, policy enforcement and recovery remain unverified.

Capability and IaC alignment, 2026-10-23: foundation remains unnumbered. The nine
capabilities are Software intake, Protected logging, Cryptographic trust, Kubernetes,
Identity, Secrets, Delivery and handover, Observability and Workloads. Kubernetes now
owns node/bootstrap and add-on/audit/recovery gates; Identity consumes that platform.
Updated indexes, source pointers, generated templates and managed-guide redirects.
Existing project records, local edits/deletions, inventories and original state paths
remain protected; stage renumbering does not rename infrastructure or resource addresses.

Found and fixed missing native cluster image-access inputs and CRLF source Bash entry
points. All three roots now accept ordered Talos proxy/DNS/time/mirror patches; default
`[]` preserves the prior configuration. Native multi-document parsing checks the actual
generated configuration, including retained hostname/disk and disabled mirror fallback.
These tests do not prove routing, image availability or live policy enforcement.

**175 regression cases: 173 passed, two fixture-dependent skips** in a fresh Linux
scratch checkout. Skips were native offline clca and rsyslog/GnuTLS sender recovery;
their previous evidence is not substituted for a current run. All **16 Terraform
deployment roots** passed provider-schema validation, preserving existing locks and
resolving missing locks only in scratch. All **30 source-cluster cases** passed;
the generated-root test repeats those suites with structured native-output assertions,
not 30 additional unique mechanisms. Proxmox was mocked and all remote Talos resources
overridden; only local configuration/key generation used the real Talos provider.
Affected figures produced **36 local renders** across light/dark themes and desktop/
760px widths. HCL formatting and `git diff --check` passed. GitHub parity and all live
bootstrap, failover, access and restore acceptance remain unverified.

The support map still identifies missing product installers: the private API endpoint
is an explicit prerequisite, Stage 4 Step 2 add-ons remain the first main-path application
gap, and later cluster applications, delivery/registry, protected execution and
Observability are not installed by their empty starters. This review does not close
those implementation boxes or turn the reference into an end-to-end installer.

Software-intake capability placement, 2026-10-22: moved the proxy/cache guide out
of foundation into `deployment/stage-01-software-intake/`, with a short numbered capability
overview and the existing source-backed deployment figure. Foundation now links
to intake; Stage 5's registry procedure extends it with OCI supply without adding
a second proxy or making early bootstrap depend on Harbor. Stage numbers, resource
names and state paths are unchanged. Managed-guide moves preserve legacy anchors
and locally owned edits/deletions. **63 affected tests passed, zero skipped** in a
fresh Linux scratch repository. Both deployment figures render in light/dark themes
at normal and 760px widths. No new product installer, hosted-renderer parity or live
acceptance is established by this organization change.

Software-intake review, 2026-10-22: compared the May cache path and Squid template
at `5801e46` with the Tier 2 implementation; the template had survived unchanged.
Restored the controlled-intake design and linked foundation, host-update and
firewall references without selecting a new repository-manager product. Empty
software-source policies now fail preflight and cannot render an unrestricted
remote-client allow rule. **44 affected tests passed, zero skipped**, including
native Ansible rejection/render checks in source and freshly generated repositories.
The new architecture figure renders in both themes at desktop and 760px widths;
GitHub parity and live proxy/cache, gateway, Windows-update and patch acceptance
remain unverified. No Pulp/WSUS installer or automatic patch workflow was added.

Full consistency review, 2026-10-22: **170 native regression tests: 168 passed,
2 tool-dependent skips**, in a fresh Linux scratch copy. Skipped the offline clca
fixture and rsyslog sender outage/restart fixture; they are not new acceptance proof.
The run covered source/generated ownership and navigation, Terraform input resolution,
Ansible syntax and FreeIPA phase orchestration, native PKI policy/TLS/CRL behavior,
syslog-ng TLS/raw identity/crash restart, HAProxy parsing and restic backup/clean restore.
After final handoff/diagram changes, **45 affected tests passed, zero skipped**;
these overlap the full suite rather than adding unique cases.

All **16 Terraform deployment roots** passed provider-schema validation; existing
locks were retained, with missing locks resolved only in scratch. All three cluster
roots passed their **24 mocked plan tests**. No real infrastructure plan/apply ran.
All **76 Mermaid figures** rendered in both themes (**152 renders**). Reviewed
contact sheets and rerendered the corrected logging figures at desktop and 760px;
coordinate checks confirm tier order and Tier 0 recovery custody outside the
collector/NAS runtimes. The audit corrected reader handoffs, misplaced hardware
administration, fresh FreeIPA CA mode, private-file defaults and no-op baseline
controls. The coverage map now discloses missing installers before each main path.
Live product qualification, fault/access/restore acceptance and GitHub renderer
parity remain unverified; no operational box is checked by this review.

Stage capability naming, 2026-10-21: **163 tests: 134 passed, 29 tool-dependent skips**
in a fresh Linux scratch copy. Stage 3 is Identity, including directory authority,
the supporting cluster foundation and Keycloak/OIDC federation. Stage 4 is Secrets,
starting with Vault/audit/recovery and its renamed 1b/1c options. Removed the empty
retired workload directory: source and fresh generated trees contain exactly seven
uniquely numbered stages. Refresh redirects unchanged old guides, while preserving
local edits/deletions and project-owned records. New federation figures distinguish
existing services from an unimplemented IdP integration; no installer or live
acceptance is implied by the reorganization. Changed figures render in both themes
at desktop and 760px reading widths; hosted review remains separate.

Dependency-placement and compactness review, 2026-10-21: inventoried all **74 diagrams**
and rendered their baseline in both themes (**148 renders**). Corrected same-tier
source/controller, cluster/dedicated-control, foundation/add-on and runner/source
placement. The Vault operator now enters from the left, with recovery custody below
and outside its connected runtime. Tier 1 application starters are contained inside
Kubernetes, not beside it. Selected control-plane and edge replicas stack vertically;
protected state stacks below its runner without changing instance counts or ownership.
The **161-test** offline suite passed **132 tests, with 29 tool-dependent skips**.
New tests guard declared placement; separate Mermaid 11.17.2 coordinate checks confirm
the actual dependency order, tier stacking, compact peers and runtime containment on
light/dark pages at desktop and 760px widths. Chronological workflows, alerts and
signal-delivery arrows retain their real semantics. No infrastructure was changed;
hosted rendering and live acceptance remain separate.

Capability-stage and layout review, 2026-10-21: **154 tests: 125 passed, 29 tool-dependent skips**
in a fresh Linux scratch copy. Observability now has its own Stage 6 after control
services and the Tier 1 runtime; workloads move to Stage 7. Source/generated navigation,
managed-document redirects and local ownership preservation pass the offline suite.
Changed figures render with Mermaid 11.17.2 in light/dark themes at desktop and 760px
reading widths. Rendered coordinates confirm stacked directory peers, infrastructure
CA placement right of IdM, and administrators left of the protected alert runtime and
outside its external notification service. Heartbeats retain their actual direction.
Global diagram goals and the local diagram guide record these conventions.
No product installer, live acceptance or hosted-renderer parity is established by this review.

Observability review, 2026-10-21: **152 tests: 123 passed, 29 tool-dependent skips**
in a fresh Linux scratch copy. A separate **12-test native Terraform/Ansible run passed,
zero skipped**, covering source/generated inventory resolution, network references,
local key validation and playbook syntax; it overlaps the full suite, not an additional
12 unique cases. HCL formatting and `git diff --check` passed. Changed observability
figures render in light/dark themes at desktop and narrower reading widths.
The design is Kubernetes-first with separate workload budgets and OpenSearch initially;
the product starter remains empty. No runtime installation, failure/restore qualification,
GitHub visual acceptance or manual operational box is satisfied by these checks.

Logging installation, 2026-10-19: **142 full regression tests passed, zero skipped**;
after final probe-credential/audit changes, **37 affected tests passed, zero skipped**.
Coverage includes native reviewed-CSR client/server issuance, actual expiry-window renewal,
CRL rejection, rsyslog outage plus abrupt process restart, first-batch source identity,
create-only NAS checkpoint fixtures, application-scope denial, tamper detection, native
encrypted restic backup/clean restore, generated ownership and source/generated syntax/links.
`git diff --check` passed. No live hosts, SMB server, physical faults or NAS grants were exercised.

Native tools: syslog-ng **4.11.0**, rsyslog **8.2312.0** with GnuTLS, restic **0.16.4**,
Ansible core **2.21.5** and Python **3.12.3**. The older cached 4.3.1 receiver exposed
upstream first-read missing TLS metadata (syslog-ng #5603); the runtime now requires 4.11+.
The official Ubuntu test package was extracted, not installed; SHA-256 matched its
official index: `49d548107fcfac677892284c879d73b72bc78213bb52c202c3aca76a7c237052`.
This qualifies local interoperability, not the selected EL 10 package/SELinux/SMB deployment.
NAS snapshots, external dead-man services, independent storage and all manual operational
checks remain commissioning/acceptance work. Existing diagrams were not changed in this pass.

Operator journey, 2026-10-19: **129 baseline tests passed, zero skipped** in the isolated
Linux/WSL checkout. After handoff corrections and three new tests, **42 affected tests
passed, zero skipped**. Source/generated links, formal language, branch metadata,
state/input ownership and preservation of owned records were included.
Exercised a separate fresh five-repository collection, Tier 0 template/syslog/cluster
initialization and Tier 1 named-test initialization; no live plan or apply was run.
The test setup creates Ansible overlays but no Terraform environment overlay, matching
the corrected guide. Existing owned READMEs remain unchanged on refresh.
Diagrams were not changed or reaccepted in this pass; GitHub visual review remains separate.

Diagram review, 2026-10-19: all **65 Mermaid diagrams** render in light and dark themes
with Mermaid 11.17.2 (**130 renders**). Placement views use six block grids; interaction
views retain flowcharts and the existing sequence. Reviewed overview sheets and detailed
figures at 1100px; key placement/containment views also render at 760px without canvas
clipping. Identity coordinates verify Tier 2 above Tier 1 above the Tier 0 boundary,
with enrolled hosts to its left. Dense diagrams still require zoom at narrow widths.

The 129-case offline run passed 125 cases; one old literal signing-edge assertion needed
the new wrapped/dashed form, and three native invocations used stale local fixture paths.
All four cases passed on recheck: **16 PKI/logging/diagram tests**, then **27 final
documentation/diagram tests**, zero skipped. This is combined evidence, not a single clean
129-case run. The new palette asset follows managed auto-docs refresh/preservation rules;
no live acceptance box is satisfied by diagram or repository tests.

Archive-choice review, 2026-10-19: the full 124-case run exposed two new-option navigation
gaps. After correcting branch metadata and checklist links, **all 46 affected tests passed,
zero skipped**; the other 78 cases passed in the full run. Coverage includes both archive
choices, source/generated navigation, formal language and preservation of project records.
This archive-choice update changes documentation/templates, not receiver or storage runtime.

Previous clean full run, 2026-10-18: **123 tests passed, zero skipped** in an isolated Linux/WSL
copy. Coverage includes source/generated provider TLS defaults, environment-bypass rejection,
manual-verification separation, fresh-shell documented commands, generator refresh/link contracts,
native Terraform inputs, FreeIPA sequencing, policy construction, offline clca constraints,
HAProxy parsing and loopback syslog-ng TLS/raw-record/crash recovery.

Test tools: Python 3.12.3, Ansible core 2.21.5, Terraform 1.16.6, HAProxy 2.8.16 and
syslog-ng 4.3.1 with matching extracted modules. The latter checks isolated engine
behavior, not qualification of the documented EL 10/syslog-ng 4.8+ deployment target.
Native PKI tests used `PKI_CONFIG_REPOSITORY` at `0aa2db093e6f0573dd296c69c98c0e61d03bdf48`,
`PKI_CLCA_REPOSITORY` at `d560135cf4bbdc1916fa4c5545012085b96d4a21`,
`PKI_HAPROXY_BINARY` and `SYSLOG_NG_TEST_BINARY`/`SYSLOG_NG_TEST_MODULE_PATH`.
Those earlier changes did not alter diagrams; the 64-diagram render remains historical evidence.
No live infrastructure acceptance box above is satisfied by these results.

From an upstream checkout on Linux/WSL with the documented test tools/collections:

```bash
python3 -B -m unittest discover -s tests -p 'test_tier*.py' -v
```

Review skipped tests explicitly. For permission-sensitive WSL tests, use a checkout
on the Linux filesystem. Render changed diagrams and inspect their labels/flow in
addition to checking Markdown links and command wiring.

Repeat this walkthrough after meaningful documentation, topology, generator, inventory
or execution changes and before a release/operational handover. Reopen checks when their
contracts change. Offline tests validate the repository; only recorded live exercises
validate the selected installation. No scheduled automation is configured by this checklist.
