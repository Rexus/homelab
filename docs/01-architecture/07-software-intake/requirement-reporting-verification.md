# Requirement reporting verification — 2026-11-20

The homelab model's four requirements and eleven verification cases were assessed through the new
reporting entry point. Four actual Squid/APT test methods cover eight isolated obligations; four site
obligations remain missing. All four requirements therefore remain missing overall, while the isolated
implementation gate passes for its declared scope.

## Contents

- [Executed checks](#executed-checks)
- [Evidence and repeatability](#evidence-and-repeatability)
- [SysON views](#syson-views)
- [Remaining limits](#remaining-limits)

## Executed checks

| Exercise | Observed result |
| --- | --- |
| Current implementation | All four bound test methods pass; isolated gate exits 0 |
| No evidence directory | All executable bindings are missing; gate exits 1 |
| Material input change without rerun | All previous bindings become stale; gate exits 1 |
| Defective admission policy in disposable checkout | Inserted `http_access allow all` before policy checks; real denial assertion fails, `REQ-policy` reports failed, gate exits 1 |
| Restore source after failed attempt | Newer failed attempt remains stale; older pass is not reused; gate exits 1 |
| Rerun corrected policy | Actual assertions pass; gate exits 0 |
| Unavailable Squid binary | Native unittest skips; assessment reports blocked and gate exits 1 |
| Restore tool and rerun | Current passing result replaces the blocked verdict; history remains |
| Include site obligations | `--scope all` exits 1 with TLS/trust, custody and egress gaps visible |
| Change generated SVG | Native CI validation rejects artifact drift; exact original is restored and manifest passes |
| Complete clean-container CI job | Native reparse/source/artifact checks, 31 focused regression tests and requirement execution all pass |
| Broader focused regression suite | 51 reporting, view, boundary and subscription checks pass on Windows |

The clean Ubuntu 24.04 job exposed a missing `community.general` dependency; setup now installs the
tested collection. It also exposed platform-dependent Graphviz geometry. The final native `validate`
path reparses the model and checks source-bound generated-artifact checksums. The ordinary local `check`
retains exact rerender comparison. No test expectation or modeled requirement was relaxed to obtain a pass.

An initial WSL run on the Windows-mounted checkout timed out in repository generation and an Ansible
fixture; those unsuccessful attempts remain recorded locally. The clean-container entry point passes
with its own complete recorded environment. Tests use loopback ports and temporary package/trust state;
no host package is installed by the test and no deployed network is exercised.

## Evidence and repeatability

Open the [requirement assessment](../../../artifacts/architecture/evidence/software-intake/requirement-assessment-2026-11-20.md),
[machine-readable verification record](../../../artifacts/architecture/evidence/software-intake/requirement-verification-2026-11-20.json)
and [raw attempts, reports and CI logs](../../../artifacts/architecture/evidence/software-intake/requirement-proof-2026-11-20.zip).
The archive retains early setup failures and later passing attempts, not only the final summary.
After extracting it, use `requirements.py gate --evidence <extracted>/evidence/runs` from the owning
checkout to reassess current source freshness. A historical snapshot is not automatically current evidence.

Follow [Requirement results and CI](../../04-development/requirement-reporting.md) for the normal commands.
The repository GitLab job was rehearsed through its actual setup/check scripts in a disposable container.
Hosted pipeline execution has not occurred; it follows the user's normal signed commit/push handoff.

## SysON views

The verified [Homelab review](http://localhost:8080/projects/167086f3-227f-4db7-9fb2-83c7019b8de4/edit/fc7f1e81-a750-4d52-be48-6d62941dc99e)
contains six deliberately selected representations. System Overall's saved labels, styles, positions,
sizes and edges match the accepted prior review exactly. The complete named semantic projection is
unchanged. Repeating the normal publication reuses this project without extra views.

| Where in SysON | Question answered |
| --- | --- |
| `Views / System Overall` | Which main subsystems connect? |
| `Views / Homelab \| Use cases` | Which actors pursue the two modeled goals, on which subjects? |
| `Views / software-intake / Connected software intake and its consumers` | Which logical responsibilities and interfaces form intake? |
| `Views / software-intake / Retrieve and verify software` | Which actor/subject bindings and eight scenarios belong to retrieval? |
| `Views / software-intake / Software intake \| Functions` | How are five functions allocated to three responsible logical roles? |
| `Views / software-intake / Software intake \| Deployment placement` | Which listener, VM, runtime and virtual-disk instances realize intake? |

System and intake use-case selections, all native actor/subject/composition edges, and function
allocations match their SVG catalogue selections. Native layout persistence is verified. Placement
checks its nested ownership, five actual flows, shared colours and annotation membership. It remains
level 1 beside logical intake; level 2 belongs to the proxy/cache component designs.

Three views retain explicit rendering gaps: logical intake's contained item, placement's two contained
items, and the previously accepted outer System Overall boundary. Their semantic elements remain in
the model. See [exact coverage](../../../artifacts/architecture/evidence/syson-view-coverage.md).

The three superseded generated reviews were archived and removed only after confirming that their
semantic state had not changed. The two original user projects remain. ZIPs and sealed return baselines
are retained in the workspace's `SysON-archives/2026-11-20-requirement-views/` directory.

## Remaining limits

The browser webview did not attach for a new visual inspection. Saved native representation content,
geometry, colours, annotations and repeat publication were verified through SysON's APIs; this record
does not claim a new screenshot review. Site-evidence import and arbitrary untraced-code discovery are
not implemented. The isolated evidence does not establish deployed operation or full SysML conformance.
