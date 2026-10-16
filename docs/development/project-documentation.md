# Project documentation

Generated repositories separate selected project designs and operating procedures
from upstream reference material. Architecture starts with the complete intended
environment, then expands its functions into domain and detailed designs.
Deployment guides explain the steps that establish that result.

## Table of contents

- [Start with project values](#start-with-project-values)
- [Project layout](#architecture-repository-layout)
- [Architecture reading path](#architecture-reading-path)
- [Design document contents](#design-document-contents)
- [Variants and site selections](#variants-and-site-selections)
- [Operating order](#operating-order)
- [Ownership and refresh](#ownership-and-refresh)
- [Existing collections](#existing-collections)
- [Maintaining the starter templates](#maintaining-the-starter-templates)

<a id="purpose"></a>

## Start with project values

Every root README links to the architecture repository's
`docs/naming-conventions.md`: VM names, role abbreviations, domains, Proxmox tags,
VMID ranges and VLAN conventions. Replace reference values with agreed standards.
Exact hosts, addresses and attachments stay in inventory.

The architecture repository joins the site's selected capabilities into one
platform design, showing how the important functions fit together. Each domain
expands part of that view. Each tier records the detailed design and
implementation it owns. Shared records its reusable automation and reference-data
contract, not resources.

## Architecture repository layout

All five repositories have project-owned `docs/architecture/`, `docs/deployment/`,
`docs/development/` and `docs/administration/` records, indexed by `docs/README.md`.

The architecture repository provides focused domain starters:

```text
docs/
  naming-conventions.md
  architecture/
    README.md              # complete platform, relationships and shared constraints
    decisions/
    networking/README.md
    compute/README.md
    identity/README.md
    cryptography/README.md
    delivery/README.md
    operations/README.md
  deployment/README.md     # stages, readiness and acceptance evidence
  development/README.md
  administration/
    README.md
    recovery.md
  auto-docs/               # upstream-managed references, never project decisions
```

The upstream `auto-docs/architecture/` has the same domain navigation, alongside
principles, tier ownership, service boundaries, an integrated reference design,
runtime flows and variant contracts. Its `deployment/README.md` indexes six
capability stages. Each stage folder has a main README with numbered steps,
diagrams, an acceptance result and links to the resulting architecture.
Adjacent `step-<number><letter>-*.md` files hold options; `procedures/` holds detailed instructions.

Domain READMEs are seeded as project-owned records. Add focused detail records
inside the relevant domain directory where needed; avoid copying guides or
duplicating inventory. The reading hierarchy does not require intermediate
`system-design/` or `subsystem-design/` directories.
Keep credentials and private keys out of every documentation area.

## Architecture reading path

| View | Question answered | Content and onward links |
| --- | --- | --- |
| Whole platform | What does the environment provide, and how does it fit together? | Named service capabilities placed by owning tier and security layer; external consumers, shared constraints and links into domain views |
| Runtime relationships | How do those functions cooperate? | Access, software supply, privileged changes and observation or recovery across domain boundaries; links to participating designs |
| Domain | How does a platform function work internally? | Selected components, supplied and consumed interfaces, ownership, trust boundaries and required guarantees; links to detailed designs |
| Detailed design | Which arrangement fulfills the contract? | Completed topology for the selected variant, focused alternatives, rationale, compatibility conditions and failure behavior; links back to the domain and to realization procedures |

The platform map shows the combined result of the selected deployment paths:
Tier 2, Tier 1, Tier 0 vertically and Edge, Application, Control horizontally.
Boxes name service capabilities; domains organize their detailed designs.
For example, directory authority (IdM) and the identity provider (IdP) are separate
boxes expanded together in the identity view, with their VM/cluster runtimes and
cross-tier consumers. Detailed diagrams expand those components or relationships. Keep names and boundary
interfaces consistent across these views. An external dependency remains visible
at the boundary when its internal components are outside the current scope.

Use several focused diagrams where a single drawing would hide the relationships.
Group components by function in the overview and show their internal structure
only in the appropriate detail view. Distinguish service consumption,
administrative control and offline transfers. Tier ownership and network
protection are separate views of the same design.

The [whole-platform reference](../architecture/README.md),
[integrated reference design](../architecture/reference-platform.md) and
[runtime flows](../architecture/runtime-flows.md) illustrate this reading path.
Architecture diagrams describe the intended completed configuration. Deployment
stage diagrams describe intermediate results and the steps that connect them.

## Design document contents

| Concern | Content |
| --- | --- |
| Purpose and scope | Function, consumers, boundaries and exclusions |
| Parent and scope | Functions expanded from the parent view; links back to that view |
| Resulting structure | Completed design diagram, components, owners, interfaces and dependencies |
| Relationships | Providers, consumers, direction, authority and behavior at each boundary |
| Choices | Selected pattern, focused alternatives, stable contracts, rationale and trade-offs |
| Constraints | Access, availability, failure behavior and recovery independence |
| Realization | Links to the selected deployment procedure, owning implementation and acceptance record |
| Review | Conditions that invalidate the design or require a new decision |

The platform README connects domains. Each domain explains its own design;
neither records deployment progress. Procedures and evidence belong in deployment,
implementation changes in development, and recurring operations in administration.

## Variants and site selections

The upstream kit can describe several valid implementations of a capability.
The project design selects a compatible combination and shows the resulting
environment. Keep these records distinct:

| Record | Responsibility |
| --- | --- |
| Upstream architecture and `auto-docs/` | Reusable functional model, integrated reference design and detailed alternatives |
| Project architecture | Reviewed site selections, their combined topology, interface contracts and required guarantees |
| Project deployment | Chosen procedures, current readiness and evidence that the intended result has been achieved |

Keep alternatives beside the detailed capability they change. For example, key
custody choices belong in the cryptographic design, while the platform overview
continues to show the trust services and their consumers. A detail record shows
the resulting structure for each relevant variant and explains which properties
change, rather than drawing a separate whole platform for every combination.

Use the [variant contract](../architecture/variants.md) to record the common role
and consumer interfaces, the selected implementation, and differences in
placement, custody, availability and recovery. Check the combined choices against
the platform's required guarantees. If a choice changes a consumer contract or
trust boundary, update the affected domain and platform views as part of the
same design change.

Link each selected design to its realization procedure and acceptance record.
Deployment guides link back to the design they establish, including the relevant
variant. This preserves one deployment sequence and one authoritative design for
each scope. A documented alternative does not establish an available installer
or prove that a site has deployed it; implementation coverage remains in the
[support map](../reference/implementation-support.md).

## Operating order

| Step | Record | Reference |
| --- | --- | --- |
| Select the design | Complete platform, conventions, domain designs and compatible detailed variants | [Architecture](../architecture/README.md) |
| Deploy and verify | Chosen stages, inputs, commands and acceptance evidence | [Deployment](../deployment/README.md) |
| Change implementation | Review, validation and adoption procedures | [Code layout](code-layout.md) |
| Operate and recover | Maintenance, custodians and restore evidence | [Administration](../administration/README.md) |

Deployment starters separate foundation prerequisites from six capability stages,
from protected logging to workload provisioning.
A repository records consumed prerequisites where another tier owns the work;
listing a stage or step does not transfer ownership.

## Ownership and refresh

Root READMEs and project records are seeded once and recorded as owned in
`.generated-files.json`. Refresh preserves their existing contents, including
unchanged starters, and never recreates recorded deletions. New record paths may
be seeded without changing older files.

Upstream references under `docs/auto-docs/` display **AUTO-DOCS - DO NOT EDIT**.
Refresh updates unchanged managed files; edited copies and recorded deletions
remain protected. See the [refresh contract](generated-repositories.md#refresh-and-local-ownership).

Generated projects select their own licensing. Copied upstream material retains
its attribution and applicable license.

## Existing collections

From the updated upstream checkout:

```bash
bash scripts/init-tier-repos.sh --refresh --dry-run
```

Reuse the original `--prefix` and `--root` flags when customized. Review the
preview, then omit `--dry-run`. No infrastructure, inventory or state is moved.

| Existing material | Adoption behavior |
| --- | --- |
| Owned README or design | Preserved, including unedited starters; adopt new content and navigation manually |
| Flat `docs/architecture.md` or architecture `docs/owned/` records | Retained; newly seeded records link to the previous design where applicable |
| Previous `system-design/` and `subsystem-design/` project records | Retained; domain starters link to the previous domain index when present |
| Unchanged auto-doc at a moved path | Replaced with a pointer to its current home, retaining old section anchors |
| Edited or deleted auto-doc | Preserved as edited or deleted |
| Earlier `docs/generated/upstream/` tree | Retained for manual comparison |

New collections contain only the current layout. Existing project designs are not
automatically merged, moved or deleted. Review and transfer local decisions before
retiring old records; do not remove the manifest to force an update.

To adopt the reading hierarchy in an existing collection, manually update the
platform record with its completed composition and domain links. Expand the
existing domain records with resulting designs and links to focused variants,
then connect each selection to its deployment procedure and acceptance record.
Retain established local decisions and anchors while updating navigation. A
refresh supplies the current upstream references; it does not rewrite the
project's design to match new templates.

## Maintaining the starter templates

`scripts/tier-repos/templates/readmes/` contains repository front doors.
`templates/project/platform-design.md` owns the whole-platform record and its
domain navigation; `domain-design.md` supplies the domain expansion and detailed
variant contract. `repository-design.md` maps those selections to the owning
implementation. The project index preserves the same reading path. Workflow
templates keep deployment, development and administration separate.

Maintain the architecture reference and these starters together so newly
generated collections use the same diagram scopes, relationships and selection
rules. Template changes improve new records; existing owned records require the
manual adoption described above.

`project_docs.py` seeds owned records. `documentation.py` publishes upstream
references. `documentation-moves.json` records compatible reference relocations;
a live canonical path must not also be a relocation source.
