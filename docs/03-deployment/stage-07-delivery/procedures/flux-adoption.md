# Adopt existing Tier 1 resources into Flux

Use this procedure for an existing installation changing owner. Fresh installations use
[Flux platform installation](flux-platform.md) directly. Refresh preserves authored `clusters/`, CI,
live inputs and deployment records; it performs no adoption. Review the
[selected ownership model](../../../01-architecture/10-delivery/flux-ownership.md) first.

## Contents

- [Inventory and protect](#inventory-and-protect)
- [Match desired configuration](#match-desired-configuration)
- [Transfer one writer](#transfer-one-writer)
- [Accept adoption](#accept-adoption)
- [Stop and recovery](#stop-and-recovery)

## Inventory and protect

1. Select the actual Tier 1-only context and record every selected release, resource, namespace,
   chart/app version, Helm storage namespace, values, PVC/PV identity and reclaim policy.
2. Back up original state, complete product data, stable Secrets, certificate/keystore passwords,
   SOPS keys and source credentials independently. Verify a clean-target retrieval before changes.
3. Inventory writers: Ansible schedules, Helm CLI jobs, Argo applications, Spinnaker accounts,
   RoleBindings, token Secrets, webhooks and existing Flux sources. Include direct API access.
4. Fence delivery triggers, runners and stale Spinnaker executions. Record the resource owner and
   accepted backup/revision per product in the project deployment record.

From **the authorized Tier 1 execution host**, with the exact context selected:

```bash
kubectl --context "$TIER1_CONTEXT" get helmreleases,kustomizations,gitrepositories -A
helm --kube-context "$TIER1_CONTEXT" list --all-namespaces
kubectl --context "$TIER1_CONTEXT" get pvc -A
```

If Flux CRDs are not installed, the first query is unavailable; retain Helm/native inventory instead.
Store exports containing values, certificates or token material only in protected independent custody.

## Match desired configuration

1. Render from accepted site inputs and existing pins. Export real service payloads and SOPS-encrypted
   Secrets; never replace stable credentials or initialize existing data to match a fresh example.
2. Review native desired resources against inventory with deletion/pruning disabled. Platform
   HelmReleases live in `flux-system`, with the existing `releaseName`, `targetNamespace` and
   `storageNamespace`; those fields must point to the original Helm release storage.
3. Match Flux's own `flux2` release in `flux-system` through `platform-base`. Bootstrap `platform`
   remains RBAC/canary only. Do not install a second Flux release or put its HelmRelease in both sources.
4. Match existing non-Helm resource identities and field ownership. Review the actual server-side
   apply/adoption diff, Jobs, storage selectors, certificates and data-ready gates before resuming.
   Do not force ownership or recreate objects to dismiss a conflict without product-specific review.
5. Keep unconverted services as named transition exceptions with a reason, previous owner, migration
   work and acceptance criteria. An exception is unfinished migration, not target completion.

## Transfer one writer

1. Disable the selected previous writer and its credentials before enabling Flux for that scope.
   For Flux-managed components normal Ansible runs render/export only; they stop Helm/resource apply.
   Set `cluster_platform_flux_adoption_accepted: true` only after this review for existing Cilium/Flux.
   For Stage 8/9 set the corresponding `*_flux_migration: adopt` and
   `observability_previous_writer_disabled` / `development_platform_previous_writer_disabled: true`
   only after actually stopping those writers. Spinnaker selects lifecycle `adopt` with retained data.
   For node collectors set `cluster_security_logging_flux_migration: adopt` and
   `cluster_security_logging_previous_writer_disabled: true`; keep the original enrolled identities.
2. Apply the externally approved bootstrap/platform source refs and reconcile one reviewed dependency
   group at a time. Suspend the application source while adopting platform and stateful services.
3. Preserve all storage and stable identities. For Spinnaker, adopt repository validation, SQL/Redis,
   schema Jobs, backups, TLS and ingress gates as one lifecycle; do not apply combined native YAML.
4. Revoke old Spinnaker application deployment RoleBindings and long-lived token Secrets. Replace
   account mounts with the promotion namespace Run Job account and read-only application observation.
   Updating a template does not revoke tokens already issued. Verify denial with those identities.
   The native renderer supplies a private `spinnaker-revoke-direct-access.yml` recipe; inspect its
   actual destination list, then run it from the independent host with explicit adoption kubeconfig,
   context and stopped-writer acknowledgement. Confirm old account Secrets and bindings are absent.
5. Import reviewed pipeline definitions with stable IDs. Remove obsolete accounts and schedules only
   after observing the new owner and retaining independent recovery material.

## Accept adoption

Verify the original Helm identity/history, bound storage, known product data, Secrets and private TLS
are intact. Make an approved reversible drift change and require Flux correction. Test pipeline/API/Git
bypasses, application namespace denial, exact-revision promotion, upgrade and compatible rollback.
Exercise external maintenance during a Spinnaker outage and recovery without GitLab/Harbor/runners.
Record live evidence using [the acceptance matrix](flux-platform.md#promotion-and-acceptance).

## Stop and recovery

On unexplained replacements, storage change, credential rotation, schema mismatch or competing writes,
suspend the affected Flux reconciliation and keep triggers fenced. Retain snapshots and failed targets.
Recover using [the product procedure](../../../05-operations/06-resilience/recovery/tier-1-products.md).
Returning ownership requires disabling Flux first and explicitly restoring the former writer's scope;
a Git revert cannot reverse schema migration or recover PVC contents.
