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

<a id="purpose"></a>
<a id="architecture-reading-path"></a>
<a id="design-document-contents"></a>
<a id="variants-and-site-selections"></a>

## Start with project values

Every repository README links to the architecture repository's naming conventions:
VM/DNS names, role abbreviations, domains, Proxmox tags, VMID ranges and VLAN rules.
Replace the reference values with agreed standards; exact hosts and addresses remain
in tier-local inventory, not a second documentation inventory.

The single platform record, `docs/README.md`, selects the paths and tracks each
capability as deployed and verified separately. Its links point to the actual
architecture, deployment, administration and development guides under `auto-docs/`.
An existing accepted service can satisfy a prerequisite without being redeployed.

## Architecture repository layout

```text
README.md                    # short front door: 1, 2, 3
docs/
  README.md                  # local selections, capability checklist and navigation
  naming-conventions.md      # local standards
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

## Operating order

| Step | Local action | Maintained guide |
| --- | --- | --- |
| 1. Set standards | Complete naming conventions and record selected infrastructure/variants | [Architecture](../architecture/README.md) |
| 2. Deploy | Follow the chosen main path and adjacent options; execute from the named owning repo | [Foundation and ten capabilities](../deployment/README.md) |
| 3. Verify | Link acceptance evidence and mark deployed/verified independently | [Readiness](../deployment/readiness.md) |
| Operate | Record custodians, maintenance decisions and restore tests only where local detail is needed | [Administration](../administration/README.md) |
| Change | Test code and review upstream adoption; retain local inputs/state | [Development](README.md) |

Architecture remains the stable design; stage diagrams show the selected IaC
realization. A project exception that changes trust boundaries or interfaces needs
a focused local design record, not silent divergence. Reuse the upstream
[variant contracts](../architecture/variants.md) and [diagram language](diagrams.md).
Do not copy complete guide bodies into project records.

<a id="ownership-and-refresh"></a>

## Existing collections

Root READMEs, the platform record and naming conventions are seeded once.
Refresh preserves them, their edits and recorded deletions. Unchanged auto-docs
update; edited or deleted copies retain the existing safety contract.

From the upstream checkout, preview an update:

```bash
bash scripts/init-tier-repos.sh --refresh --dry-run
```

Reuse original `--prefix`/`--root` flags if customized. Review the preview before
omitting `--dry-run`. No inventory, infrastructure or state is moved.

| Existing material | Adoption |
| --- | --- |
| Local architecture/domain/workflow documents | Preserved, even unchanged; transfer real decisions/evidence into the compact record or retain useful detail |
| Existing `docs/README.md` and root README | Not rewritten; adopt current starter navigation manually after comparing local edits |
| Recorded deletions | Never recreated to force the new layout |
| Unused starters and site skeleton | Remove manually only after reviewing local content and references |
| Earlier `docs/generated/upstream/` | Retained for comparison; use current `docs/auto-docs/` going forward |

New collections have the compact layout. Existing collections are not forcibly
reorganized. Do not delete `.generated-files.json` to force an update. See the
[refresh contract](generated-repositories.md#refresh-and-local-ownership).

## Maintaining the starter templates

`scripts/tier-repos/templates/readmes/architecture.md` owns the short front door;
`templates/project/index.md` supplies the single local platform record;
`templates/project/naming-conventions.md` supplies the standards worksheet.
`project_docs.py` seeds these records, while `documentation.py` publishes the full
manual. Tier-specific project/workflow templates remain separate.

Maintain links, selections and stage coverage with focused generator tests.
Fresh-output tests must reject accidental extra local scaffolding; refresh tests
must preserve previous records, edits and deletions. Template improvements are
not permission to overwrite project-authored documents.
