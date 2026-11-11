# Project documentation

Use the maintained auto-docs as the manual. Keep local documentation small:
selected paths, naming standards, exceptions and verification evidence.
Generation must not require a team to author a second architecture before deploying.

## Contents

- [Start with project values](#start-with-project-values)
- [Architecture repository layout](#architecture-repository-layout)
- [Operating order](#operating-order)
- [Existing collections](#existing-collections)
- [Maintaining the starter templates](#maintaining-the-starter-templates)
- [Writing numbered guides](#writing-numbered-guides)
- [Writing command examples](#writing-command-examples)

<a id="purpose"></a>
<a id="architecture-reading-path"></a>
<a id="design-document-contents"></a>
<a id="variants-and-site-selections"></a>

## Start with project values

Every repository README links to the architecture repository's platform standards:
VM/DNS names, role abbreviations, domains, Proxmox tags and the selected network plan.
The root `platform-standards.md` records local choices; conventions such as VMID
allocation are links to the maintained manual rather than copied rules.
Replace the reference values with agreed standards; exact hosts and addresses remain
in tier-local inventory, not a second documentation inventory.

Edit in **`<prefix>-architecture/`**.

- `platform-standards.md`: agreed naming, tags, VMID reservations and network choices
- `docs/README.md`: selected design, navigation and operating records
- `deployments.md`: completed deployments, nested options and links to guides/owning repositories

After a successful Terraform and/or Ansible installation, update the matching entry
and selected options in `deployments.md`: use `- [x]` for completed paths and `~~text~~`
for unselected options. A Terraform-only run can leave service configuration pending;
note that status until the full linked path is complete. Keep live acceptance and
restore evidence separate from deployment progress. Existing accepted services can
satisfy prerequisites without being redeployed.

## Architecture repository layout

```text
README.md                    # short front door: 1, 2, 3
platform-standards.md        # local standards beside the front door
deployments.md               # editable completion checklist and options
docs/
  README.md                  # local design selections, evidence links and navigation
  auto-docs/                 # full upstream manual, refreshed with provenance notices
```

There are no initially generated local domain designs, workflow folders, recovery
skeletons or documentation-site directory in this repository. Add a focused local
record only when a site exception or operating procedure needs it, then link it
from the platform record. Recovery evidence is still required; a pre-created empty
runbook is not evidence. Keep secrets and actual recovery credentials outside docs.

Tier/Shared repositories retain their code-specific records. Their READMEs lead
to owned inputs and the common platform record; shared never owns inventory/state.
The architecture repository's single checklist is the cross-repository progress view.

Earlier `naming-conventions.md` and `docs/naming-conventions.md` files stay preserved
on refresh. The new root worksheet links the previous record for review; transfer approved choices before
adopting the new worksheet. Existing project-owned READMEs remain unchanged.

## Operating order

| Step | Local action | Maintained guide |
| --- | --- | --- |
| 1. Set standards | Complete naming conventions and record selected infrastructure/variants | [Architecture](../01-architecture/README.md) |
| 2. Deploy | Follow the chosen main path and adjacent options; execute from the named owning repo | [Foundation and ten capabilities](../03-deployment/README.md) |
| 3. Verify | Link acceptance evidence and mark deployed/verified independently | [Readiness](../03-deployment/readiness.md) |
| Operate | Record custodians, maintenance decisions and restore tests only where local detail is needed | [Administration](../05-operations/README.md) |
| Change | Test code and review upstream adoption; retain local inputs/state | [Development](README.md) |

Architecture remains the stable design; stage diagrams show the selected IaC
realization. A project exception that changes trust boundaries or interfaces needs
a focused local design record, not silent divergence. Reuse the upstream
[variant contracts](../01-architecture/02-organization/README.md#selected-design) and [diagram language](diagrams.md).
Do not copy complete guide bodies into project records.

<a id="ownership-and-refresh"></a>

## Existing collections

Root READMEs, the platform record, deployment checklist and standards are seeded when missing.
Refresh preserves their existing edits and restores missing current starter files.
Unchanged auto-docs update; missing copies return and obsolete auto-doc paths are removed.
Compatibility pages keep former unnumbered and numbered guide paths and section anchors usable by
existing project records. Former asset paths also remain available; new links should use current paths.
For an existing collection, transfer any deployment checks from `docs/README.md`
into the new `deployments.md`; the old record is preserved for review.

Use the [refresh procedure, actions 1–3](generated-repositories.md#refresh-and-local-ownership)
to preview and update the existing collection. Then review the local documentation below;
refresh does not migrate project-authored content.

| Existing material | Adoption |
| --- | --- |
| Local architecture/domain/workflow documents | Preserved, even unchanged; transfer real 07-decisions/evidence into the compact record or retain useful detail |
| Existing `docs/README.md` and root README | Not rewritten; adopt current starter navigation manually after comparing local edits |
| Existing `deployments.md` | Preserve completed checks and evidence; compare the upstream kit's `scripts/tier-repos/templates/project/deployments.md` and add newly selected paths/options as unchecked entries |
| Missing current starter or guide | Recreated from its current template; review restored project defaults before use |
| Obsolete or extra file in `docs/auto-docs/` | Removed automatically; known moves report the current guide |
| Unused starters and site skeleton outside auto-docs | Remove manually only after reviewing local content and references |
| Earlier `docs/generated/upstream/` | Retained for comparison; use current `docs/auto-docs/` going forward |

New collections have the compact layout. Existing collections are not forcibly
reorganized. Do not delete `.generated-files.json` to force an update. See the
[refresh contract](generated-repositories.md#refresh-and-local-ownership).

## Maintaining the starter templates

`scripts/tier-repos/templates/readmes/architecture.md` owns the short front door;
`templates/project/index.md` supplies the single local platform record;
`templates/project/deployments.md` supplies the completion checklist;
`templates/project/platform-standards.md` supplies the standards worksheet.
`project_docs.py` seeds these records, while `documentation.py` publishes the full
manual. Tier-specific project/workflow templates remain separate.

Maintain links, selections and stage coverage with focused generator tests.
Fresh-output tests must reject accidental extra local scaffolding; refresh tests
must preserve existing project records/edits, restore missing targets and confine automatic cleanup to auto-docs.
Template improvements are
not permission to overwrite project-authored documents.

## Writing numbered guides

Use the historical manual VM-template guide's action-by-action style: a short numbered heading,
the action or command to perform, then a brief expected result. Use as many steps as the task needs;
“1, 2, 3” means sequential actions, not a fixed three-phase format.

- Re-evaluate the workflow before rewriting its prose. Derive the sequence from the actual installer,
  prerequisites, current operator state, decisions and completion criteria; existing headings are not constraints.
  Separate configuring existing systems from preparing defaults for systems created later.
- Keep the real execution order. Preserve supplied command sequences and technical meaning;
  correct spelling and connect references without reshaping them into broad phases.
- Give each concrete action one copyable block. Keep OS package installation separate from
  Python environments and application configuration.
- End a block before a manual comparison or decision. Print a checksum in one action, compare it,
  then unpack/install in the next; a copyable block must not run past its own acceptance gate.
- Name the machine/repository and exact file or field at the action. Keep explanation short;
  link architecture for rationale and reference docs for optional detail.
- Put a choice where it occurs, such as **2a/2b**. Complete the selected path in order and state
  its rejoin point; never make an alternative look like the next required action.
- Name dedicated main-step files `step-<number>-<task>.md` and options
  `step-<number><letter>-<task>.md`, matching the owning README route and `Step` title.
  Use the same prefix for companion guides belonging to that path. Reusable procedures live under
  `procedures/`; optional lookup material belongs under `docs/08-reference/`. Both keep descriptive names
  and links from their consuming steps, rather than appearing as extra installations.
  When numbering changes, rename affected files and update links and refresh-move targets together.
- Link every deployment guide/option from the owning README at its numbered decision or required action.
  A guide-to-guide link alone must not hide a selectable path. Keep each selected stage completable before
  the next: place enhancements after their real prerequisites, even when they extend an earlier capability.
  State external/manual prerequisites and supplied automation separately; never imply a missing installer exists.
- Number required actions consecutively; reserve lettered alternatives for real choices.
  A genuine capability milestone may contain required numbered sub-actions, with a clear continuation.
- Use EL10 and Talos examples where appropriate. Add Debian/Ubuntu package or layout substitutions
  beside the affected step; do not imply that an OS-specific service installer supports another distro.
- Retain useful diagrams, checks and rollback instructions. A shorter guide must still include
  the prerequisites and verification needed to complete it.

See [bootstrap LVM expansion](../03-deployment/foundation/bootstrap/step-3b-bootstrap-lvm.md) for two sequential storage paths.

## Writing command examples

Put the **working repository or machine** immediately above each command/configuration example.
Use inline code for file paths and exact variable names; state the edits in a short paragraph or
file list above the example. Avoid commented path lists and repeated `# Edit:` instructions.

Use the actual fence language: `bash` for commands, `yaml`/`hcl`/`dotenv` for configuration,
and `text` for output or file trees. Do not style instructions as executable code.
When a comment is needed inside an example, keep it short, indent wrapped lines consistently,
and separate logical groups with blank lines. Preserve required native syntax,
such as shebangs, Cloud-Init headers and literal configuration content.
Use the [command conventions](../README.md#read-command-examples) for placeholders and context.
