# Project documentation

Generated repositories separate selected project designs and operating procedures
from upstream reference material. The folder name identifies the reading task.

## Table of contents

- [Start with project values](#start-with-project-values)
- [Project layout](#architecture-repository-layout)
- [Design document contents](#design-document-contents)
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

The architecture repository records platform relationships and technical-domain
choices. Each tier records the design and implementation it owns. Shared records
its reusable automation and reference-data contract, not resources.

## Architecture repository layout

All five repositories have project-owned `docs/architecture/`, `docs/deployment/`,
`docs/development/` and `docs/administration/` records, indexed by `docs/README.md`.

The architecture repository provides focused domain starters:

```text
docs/
  naming-conventions.md
  architecture/
    README.md              # platform relationships and shared constraints
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
principles, tier ownership, service boundaries and a reference platform. Its
`deployment/README.md` indexes six capability stages. Each stage folder has a main README
with numbered steps, diagrams, an acceptance result and links to the implemented design.
Adjacent `step-<number><letter>-*.md` files hold options; `procedures/` holds detailed instructions.

Add focused records where needed; avoid copying guides or duplicating inventory.
Keep credentials and private keys out of every documentation area.

## Design document contents

| Concern | Content |
| --- | --- |
| Purpose and scope | Function, consumers, boundaries and exclusions |
| Structure | Components, owners, interfaces and dependencies |
| Choices | Selected pattern, alternatives, rationale and trade-offs |
| Constraints | Access, availability, failure behavior and recovery independence |
| Review | Conditions that invalidate the design or require a new decision |

The platform README connects domains. Each domain explains its own design;
neither records deployment progress. Procedures and evidence belong in deployment,
implementation changes in development, and recurring operations in administration.

## Operating order

| Step | Record | Reference |
| --- | --- | --- |
| Select the design | Platform relationships, conventions and domain choices | [Architecture](../architecture/README.md) |
| Deploy and verify | Chosen stages, inputs, commands and acceptance evidence | [Deployment](../deployment/README.md) |
| Change implementation | Review, validation and adoption procedures | [Code layout](code-layout.md) |
| Operate and recover | Maintenance, custodians and restore evidence | [Administration](../administration/README.md) |

Deployment starters cover six capability stages, from compute foundation to workload provisioning.
A repository records consumed prerequisites where another tier owns the work;
listing a stage or step does not transfer ownership.

## Ownership and refresh

Root READMEs and project records are seeded once and recorded as owned in
`.generated-files.json`. Refresh never replaces their edits or recreates recorded
deletions. New record paths may be seeded without changing older files.

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
| Owned README or design | Preserved; update its navigation manually |
| Flat `docs/architecture.md` or architecture `docs/owned/` records | Retained; newly seeded records link to the previous design where applicable |
| Previous `system-design/` and `subsystem-design/` project records | Retained; domain starters link to the previous domain index when present |
| Unchanged auto-doc at a moved path | Replaced with a pointer to its current home, retaining old section anchors |
| Edited or deleted auto-doc | Preserved as edited or deleted |
| Earlier `docs/generated/upstream/` tree | Retained for manual comparison |

New collections contain only the current layout. Existing project designs are not
automatically merged, moved or deleted. Review and transfer local decisions before
retiring old records; do not remove the manifest to force an update.

## Maintaining the starter templates

`scripts/tier-repos/templates/readmes/` contains repository front doors.
`templates/project/platform-design.md` owns the platform record;
`domain-design.md` supplies the reusable domain record. Workflow templates keep
deployment, development and administration separate.

`project_docs.py` seeds owned records. `documentation.py` publishes upstream
references. `documentation-moves.json` records compatible reference relocations;
a live canonical path must not also be a relocation source.
