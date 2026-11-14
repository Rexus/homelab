# Tier 1 Flux implementation review

User request: attachment `52993950-2722-4262-a2ea-a33a9469e21b`, 2026-11-14.
Base commit: `fcb1c33`. No live deployment, commit or push is authorized for this change.
Prepare changes and signed commit/push commands only. Decision identifier: D-041.

## Ownership and source contract

- Existing Tier 0 Flux and immutable commit/canary validation stay intact.
- Fresh Tier 1 selects `cluster_platform_management: flux`, `cluster_platform_tier: 1`.
  Legacy role defaults remain `ansible`; refresh preserves existing live inputs.
- Ansible bootstraps Cilium and Flux with the existing shared installer. After Flux's own HelmRelease
  exists, normal runs render platform configuration and validate bootstrap, without reinstalling it.
- Bootstrap source `platform` is pinned to an exact commit, path `./clusters/tier1/bootstrap`.
  It owns reconciliation RBAC and the SOPS acceptance canary, not changing source references.
- Platform source `tier1-platform` is pinned to an approved exact commit. It owns service payloads,
  including Flux's own `flux2` HelmRelease. An independent privileged maintenance path advances it.
- Application source `tier1-applications` tracks a protected delivery branch in a separate project;
  promotion cannot write bootstrap/platform repositories or their Kubernetes objects.
- Platform HelmRelease objects live in `flux-system`, use `platform-reconciler`, and retain original
  `releaseName`, `targetNamespace` and `storageNamespace`. Applications use namespace-limited SAs.
- Platform components transfer through render-only `flux_payload`; later stages stay opt-in.
  Native Jobs and data readiness require explicit versioned completion gates and recovery fencing.
  Tier 1 security collectors retain early Talos preparation, then export the same enrolled node
  Helm identities through `platform/security-logging`. Tier 0/2 collector owners remain unchanged.
- SOPS secrets, independent keys, configuration/artifact custody and accepted-revision receipts are
  part of recovery; reconstructing resources does not restore persistent data.

## Parallel implementation scopes

Parallel agents were explicitly authorized earlier in the conversation; no new permission is needed.

| Agent | ID | Exclusive scope |
| --- | --- | --- |
| Services | 01a1dc19-2e26-7943-9008-9d0dc1d45ca2 | Shared `flux_payload`; Tier 1 observability/development roles, inputs and tests; their service cluster folders |
| Spinnaker | 01a1dc19-2f1f-7121-84ed-21e229e3dea5 | `delivery_platform`, delivery inputs and tests; staged lifecycle and legacy write revocation |
| Promotions | 01a1dc19-304d-7782-919d-5159bc50c6c1 | New `delivery_promotion`, worker/scripts/pipelines/playbook/inputs/tests |
| Documentation | 01a1dc1b-3f72-7063-8e22-9ad5e68153fd | D-041, delivery architecture/deployment/operations/recovery, affected Stage 8/9 docs and diagrams |
| Parent | This thread | `cluster_platform`, external maintenance/custody, Tier 1 top cluster indexes, generator payload rules, integration tests and `.ai` records |

## Verification boundary

Use the prepared isolated Linux harness `.tmp/storage-compatible-checks.sh` with selected unittest
targets; it copies nonignored source and uses cached native Ansible/Helm/Terraform tooling.
Add tests to the existing framework, render diagrams in light/dark modes, and check generated ownership
and documentation links. Record actual checks and remaining live acceptance here and in the operator
checklist before handover. Initial seven focused lifecycle/bootstrap checks passed, followed by two
actual release-assembly and bootstrap rejection checks. These cover disposable Git bundles/artifacts,
generated refresh, real Ansible templates and source/tier separation; they do not qualify live operation.

Parent integration adds `flux_maintenance` (external approved source changes and recovery fencing),
`flux_recovery_git` (read-only SSH sources on recovered bootstrap), and `scripts/flux-recovery.py`
(export/verify/restore exact Git bundles plus actual approved artifact files). Artifact-lock SHA-256 is
independently approved, not inferred from a package's own mutable checksum listing. The candidate package
must exist and verify before a source advances. Application branch recovery remains suspended until
data/execution acceptance and exact branch-head observation. Native configuration and restore-tool checks
exercise the supplied mechanisms; live Flux, service data restoration and host recovery remain pending.

Primary implementation references reviewed: Flux HelmRelease adoption/identity and drift detection;
Flux multitenancy; flux2 chart 2.16.4 values; GitLab protected-branch Free/CE permissions.
Deploy-key protection via API only moved to Free in GitLab 18.10: do not assume it for an older pin.

## Integration corrections

- Added stable component readiness aggregates and explicit base controller/storage prerequisites.
  Issuance probes wait for ingress without blocking ingress on certificate issuance.
- Empty-release components emit a native empty list instead of passing one to a string indent filter.
- Long Flux metadata identities use deterministic shortened hashes; original Helm release names survive.
- Application namespace examples align with bootstrap. Reserved platform namespaces are rejected.
- Maintenance can repair an existing source despite unrelated source outages, uses conditional exact-ref
  API patches, fences recovery/resume, checks exact branch/health and correlates success receipts.
- Custody serves three distinct forced-command Git identities. Native upload commands and API-double
  maintenance tests passed; actual SSH policy/authentication and live Flux remain unqualified.
- Independently approved lock data binds every source commit and actual artifact checksum. Tests
  reject substituted valid bundles and rewritten manifests, not only accidental file corruption.
- Source/generated navigation removes unreferenced legacy asset copies while preserving referenced
  aliases. Corrected a pre-existing UTF-8 BOM interfering with an imported operations heading.

Current verification runs are recorded at handover after final scoped reruns. Do not infer live
acceptance, installed resources or completed data recovery from these offline checks.

## Completed verification, 2026-11-15

| Scope | Evidence |
| --- | --- |
| Existing installers | 38 tests passed, no skips: cluster platform, delivery platform, observability platform and development platform; real pinned source/generated charts, CA checks, native Collector/Data Prepper parsers and official database CRD schemas |
| Bootstrap / source boundary | Real Ansible assembly and render, immutable Tier 0 rejection, separate pins/credentials, application RBAC, initializer and generated refresh checks passed |
| Shared Flux payload | Native SOPS round trips, stable component aggregates, actual service graph exports, Helm/PVC identity preservation, empty-release and bounded metadata checks passed |
| Promotions | Signed deterministic Git candidates, exact diff/CAS/concurrency/retry, revision/workload HTTP fixtures, native pipeline/RBAC rendering and stable authenticated Gate import checks passed |
| Maintenance | 11 native API-double/Git-command tests passed, including unrelated outages, conditional source updates, wrong-head fencing, stale receipt rejection, recovery branch drift and distinct scoped upload identities |
| Custody | Four real Git/artifact tests passed, including exact export/verify/restore, plaintext Secret refusal and rejection of rewritten bundle/artifact manifests against independently approved lock data |
| Collectors | Encrypted Tier 1 node-identity publication, exact single-node readiness and second-writer/tier/acceptance refusals passed; retained collector regressions passed |
| Docs / diagrams | 71-test documentation scope had one missing reciprocal capability link, corrected and passed focused navigation; final 22 link/navigation/custody checks and 10 final payload/namespace/diagram checks passed. Twenty browser renders parsed without SVG overflow; normal/narrow light/dark views inspected |
| Source hygiene | Changed Python/YAML/Bash parsed, renderer JavaScript syntax and scoped whitespace checks passed. Isolated source snapshots passed redacted Gitleaks scans before native tests |

Earlier broad Flux runs exposed two fixture defects (incomplete test chart pins and one variable reused
for both prior resource content and stage names). Both fixtures were corrected and passed focused reruns.
The final native Spinnaker comparison passed for source and generated repositories with Kubernetes
1.33 schemas enabled, checking actual decrypted payload equality and retained storage/Job/RBAC contracts.
The earlier 44-case Flux scope passed 42 cases before those two fixture corrections; no production-code
failure remains from that run. Earlier AlmaLinux trials also exposed incomplete local verification
dependencies; the final isolated Ubuntu runtime uses prepared collection ranges and pinned schema validators.

Final hygiene parsed 16 Python files, 78 YAML/example files and two Bash scripts, and checked renderer
JavaScript and staged whitespace. The final handoff stages only the reviewed project changes.

No live infrastructure was changed. No commit or push was performed. Existing deployments need
explicit adoption; Argo CD/direct Spinnaker/custom overlays keep their stated alternative scope.
Rancher is unselected and has no supplied installer. Product data restoration, real authorization
bypasses, upgrades, drift, outage recovery and full Tier 0-then-Tier 1 recovery remain live acceptance.
