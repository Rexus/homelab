# Install and maintain the Tier 1 Flux platform

**Selected path:** independent Tier 1 Flux installs platform services; Spinnaker promotes application
Git. Start at [Stage 7](../README.md). Existing installations first complete
[explicit adoption](flux-adoption.md). The [ownership figure](../../../01-architecture/10-delivery/flux-ownership.md#figure-tier1-flux-ownership)
shows the resulting boundary, including independent maintenance and recovery.

## Contents

- [Prepare independent sources and custody](#prepare-independent-sources-and-custody)
- [Create the encrypted bootstrap canary](#create-the-encrypted-bootstrap-canary)
- [Bootstrap and transfer platform ownership](#bootstrap-and-transfer-platform-ownership)
- [Render services into the platform source](#render-services-into-the-platform-source)
- [Approve a platform revision](#approve-a-platform-revision)
- [Promotion and acceptance](#promotion-and-acceptance)
- [Recovery and stop conditions](#recovery-and-stop-conditions)

## Prepare independent sources and custody

Use **an authorized Linux/WSL execution host**, independent of Spinnaker, GitLab and ordinary runners.
Prepare declared Ansible collections/Python clients, Helm, Kustomize, Git, SOPS and age. Select Tier 1's
kubeconfig/context only. Retain initial Git/chart/image supply reachable before Stage 9 exists.

1. Create/accept the private bootstrap/platform Git project and an entirely different application
   delivery project. Give Flux read credentials for each source; give the promotion bot write rights
   only in the application project. Commission [CE branch permissions and roles](../../../01-architecture/10-delivery/approval-controls.md).
2. Check out the approved platform source independently. `clusters/tier1/bootstrap` contains RBAC and
   the SOPS canary only. The selected platform root contains `platform-base` and enabled service graphs.
   Exports must enter the actual checked-out source, not an untracked sibling assumed to be deployed.
3. Retain independent age keys and original private inputs. Import bootstrap source/decryption Secrets
   through the approved credential owner. Separate source credentials and decryption Secrets by scope.
   Encrypt exported service Secrets with SOPS; never commit private rendered values/manifests.
4. Record accepted bootstrap/platform commits, application branch, artifact digests, key/backup IDs,
   custodian and external configuration-bundle location. Retrieve/verify that bundle before proceeding.
   Preserve the manual signed-commit and push policy; rendering performs no publication or approval.

From **`<prefix>-tier-1/`**, initialize the cluster-platform local inputs:

```bash
bash scripts/init-local-files.sh --setup cluster-platform
ansible-vault encrypt ansible/group_vars/cluster_platform_secrets.yml
ansible-vault edit ansible/group_vars/cluster_platform_secrets.yml
```

Fill the six separate Tier 1 Git/SOPS Secrets in the encrypted example, including private age keys;
keep `cluster_platform_manage_secrets: true`. For SSH select identity/public-key/known-hosts fields
and matching required-key lists rather than HTTPS username/password. Retain those keys independently.
An accepted external Secret owner may instead provide the same six contracts; omit the private-file
argument below only for that explicit branch. Bootstrap keys are never Tier 0 keys.

## Create the encrypted bootstrap canary

Follow the existing [SOPS mechanism](../../stage-04-kubernetes/procedures/flux-sops.md#prepare-the-source)
using the **Tier 1 bootstrap source checkout**, not its Tier 0 path or keys. Create
`clusters/tier1/bootstrap/canary.sops.yaml` there with:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: platform-sops-canary
  namespace: flux-system
type: Opaque
stringData:
  accepted: platform-sops-ok
```

Run **from that source checkout's root**, with `TIER1_BOOTSTRAP_AGE_RECIPIENT` set to its public recipient:

```bash
sops --encrypt --in-place --age "$TIER1_BOOTSTRAP_AGE_RECIPIENT" \
  --encrypted-regex '^(data|stringData)$' clusters/tier1/bootstrap/canary.sops.yaml
printf %s platform-sops-ok | sha256sum
```

Use the digest as `cluster_platform_flux_canary_sha256`. The cluster renderer writes `ownership.yaml`
and registers an existing `canary.sops.yaml`; inspect `bootstrap/kustomization.yaml` and preserve both
resource entries before approving/publishing the bootstrap commit. An empty bootstrap index is safe
as a starter but cannot satisfy live acceptance. The exact committed reconciliation must inventory
the canary, decrypt it with the retained key and match the expected plaintext digest.
Never publish the plaintext canary version or include moving source refs/Flux HelmReleases in bootstrap.

## Bootstrap and transfer platform ownership

If Stage 7 Step 1 already accepted this runtime and base reconciliation, retain those inputs,
source receipts and credentials and continue at service rendering below. Do not create/bootstrap
another cluster or repeat ownership transfer for every product.

Complete [the platform-cluster lifecycle](platform-cluster.md), including saved-plan review,
credential export, capacity and independent API access. In **Tier 1's local
`ansible/group_vars/cluster_platform.yml`**, explicitly select:

```yaml
cluster_platform_tier: 1
cluster_platform_management: flux
cluster_platform_components: [cilium, storage, cert_manager, ingress, cloudnative_pg, flux]
cluster_platform_flux_path: ./clusters/tier1/bootstrap
cluster_platform_flux_applications_suspended: true
```

Add `barman_cloud` only for the selected object/WAL database backup integration. Fill exact chart pins,
approved repositories, qualified storage and the following fields from the
[owning defaults](../../../../shared/ansible/roles/cluster_platform/defaults/main.yml):

| Input | Required value |
| --- | --- |
| `cluster_platform_flux_url`, `cluster_platform_flux_commit` | Independent bootstrap URL and exact immutable accepted commit |
| `cluster_platform_flux_platform_url`, `cluster_platform_flux_platform_commit`, `cluster_platform_flux_platform_path` | Platform project, exact approved service revision and its authored entry path |
| `cluster_platform_flux_application_url`, `cluster_platform_flux_application_branch`, `cluster_platform_flux_application_path` | Entirely separate app project, protected delivery branch and entry path |
| `cluster_platform_flux_application_namespaces` | Approved dedicated app namespaces; no privileged identities or unrelated Secrets |
| `cluster_platform_flux_additional_platform_namespaces` | Every customized platform-service namespace, excluded from application RBAC in addition to the built-in platform names |
| `cluster_platform_gitops_root`, `cluster_platform_gitops_age_recipients` | Absolute private checkout's `clusters/tier1` directory and independently held age recipients |
| Source/decryption Secret names and canary fields | Six distinct scoped credential/decryption Secret names; retained encrypted canary and expected plaintext hash |

Render and inspect **from `<prefix>-tier-1/`**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/cluster-platform.yml \
  -e @ansible/group_vars/cluster_platform.yml \
  -e @ansible/group_vars/cluster_platform_secrets.yml --ask-vault-pass \
  -e cluster_platform_action=render
```

Review and publish the generated bootstrap/platform content through the authorized manual process,
retain its accepted revisions, then run the same command with `cluster_platform_action=apply`.
Initial apply installs minimum Cilium/Flux and source access. Flux adopts the matching Cilium and
`flux2` Helm releases through `platform-base`; CSI, certificates, ingress and database controllers
follow declaratively. After that adoption normal Ansible runs stop writing those Helm releases.
Require platform health before installing services. A ready controller does not qualify storage/TLS.

The bootstrap marker is HelmRelease `platform-base-flux2` in `flux-system`, preserving Helm
`releaseName: flux2` and target/storage namespace `flux-system`; its readiness child is
`platform-base-flux2-release`. The initial platform entry includes only `base` (`platform/base`).

## Render services into the platform source

Configure products through their existing native inputs. These renderers own configuration contracts;
Flux is the ongoing Kubernetes writer. Flux mode is render/export only and rejects direct apply.

| Stage / renderer | Explicit owner and export inputs |
| --- | --- |
| 7 cluster security collectors | `cluster_security_logging_owner: flux`; prepare Talos first, then publish retained node identities through [the collector procedure](../../stage-04-kubernetes/procedures/security-logging.md) |
| 7 / `delivery-platform.yml` | `delivery_platform_owner: flux`; `delivery_platform_flux_output`; `delivery_platform_flux_sops_age_recipients`; retained private Secret contract |
| 8 / `observability-platform.yml` | `observability_owner: flux`; `observability_flux_root`; `observability_flux_age_recipients`; `observability_flux_migration: fresh` (or reviewed `adopt`) |
| 9 / `development-platform.yml` | `development_platform_owner: flux`; `development_platform_flux_root`; `development_platform_flux_age_recipients`; `development_platform_flux_migration: fresh` (or reviewed `adopt`) |

Use absolute export paths into that private platform checkout. Review the generated component
`kustomization.yaml` and reconciliation graph, then include only selected components in the authored
platform root. Refresh/export must preserve unrelated authored configuration. Stage 8/9 stay disabled
until their own prerequisites are accepted; exporting a component does not select every later stage.

In the private checkout edit `clusters/tier1/platform/kustomization.yaml` after a successful render.
Keep `base`, add reviewed `security-logging`, `delivery` and separately exported `artifact-registry` entries for Stage 7,
then add `observability`, `source-control`
or `ci-runners` only at their selected later stages. Promotion worker publication uses its configured
component path, which must also be explicitly reachable from the approved platform root. Do not
select the top-level repository skeleton as if every service below it were installed.
Use `delivery_platform_flux_component: platform/artifact-registry` for a Harbor-only export; retaining
the default `platform/delivery` would replace that component graph rather than append another product.
Keep the controller and registry input profiles and root entries separate.

For Spinnaker set `delivery_platform_spinnaker_delivery_mode: flux` and a deliberate
`delivery_platform_spinnaker_lifecycle` (`fresh`, `adopt`, `upgrade` or `recover`). Retain stable
credentials, the job revision and [native TLS/backup contracts](../step-2b-spinnaker.md).
`delivery_platform_manage_secrets: true` supplies the export's retained private Secret map;
`delivery_platform_flux_secret_data` supplies already base64-encoded binary TLS/PKCS12 values.
Select `delivery_platform_flux_secret_owner: retained`, or explicitly select `generated` with an
independent absolute credential cache and custody acknowledgement. Do not regenerate against live data.
New generated credential custody requires the explicit one-time initialization setting; disable it
after retaining the cache. Subsequent adoption/upgrade/recovery uses the same stable credentials.

Render **from `<prefix>-tier-1/`**, using the private encrypted input prepared in Stage 7:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-platform.yml \
  -e @ansible/group_vars/delivery_platform.yml \
  -e @secrets/delivery-platform.yml --ask-vault-pass -e delivery_platform_action=render
```

For unattended runs supply the approved Vault identity instead of `--ask-vault-pass`. Review native
render checksums, encrypted exports, Helm identity, stage dependencies, finite Job retries/completion,
network/identity restrictions, retained storage and data-ready conditions before publication.
Commission the independent backup repository before normal backups; require a verified first backup
and service readiness before publishing Spinnaker ingress. Recovery must hold initialization/consumers
until data restore is accepted. Job revision changes are reviewed actions, not a routine reconcile knob.

## Approve a platform revision

1. Render only selected changes with the accepted pins and private inputs. Review the actual Git diff,
   including SOPS files and lifecycle Job revisions. Preserve Helm `releaseName`, `targetNamespace`
   and `storageNamespace`; platform HelmRelease objects remain in `flux-system`.
2. Complete manual signed approval/publication. Store the approved commit and artifact bundle in
   independent custody with a receipt; do not rely on the new GitLab/Harbor to hold its sole copy.
3. Use [the external maintenance playbook](../../../05-operations/05-delivery.md#advance-an-approved-platform-revision)
   to advance `tier1-platform` to that exact
   commit. Bootstrap `platform` keeps its immutable revision unless an explicit bootstrap change is
   approved. Application promotions have no access to either operation.
4. Observe exact source revision, Kustomization generation, HelmRelease readiness, completed Jobs and
   product health. Stop on suspended, stalled, superseded or failed resources; Ready on an old revision
   is insufficient. Retain the previous accepted revision and product-compatible rollback plan.

Inspect **from the external Tier 1 maintenance host**:

```bash
kubectl --context "$TIER1_CONTEXT" -n flux-system get gitrepositories,kustomizations,helmreleases
```

The inspection command does not authorize advancement. Site accepted-revision records and custody
receipts must match the reviewed change before the maintenance operation.

## Promotion and acceptance

### 1. Configure and render promotion inputs

Run from **`<prefix>-tier-1/`**.

```bash
bash scripts/init-local-files.sh --setup delivery-promotions
```

Edit `ansible/group_vars/delivery_promotion.yml`. Match `delivery_promotion_application_namespaces`
and `delivery_promotion_kustomization_path` to the cluster's approved application source. Set the
separate application repository, exact target/chart/image pins, real digest-pinned worker image,
judgment roles, egress and accepted bypass limits. Set `delivery_promotion_flux_output` to the absolute
private platform checkout's `clusters/tier1` directory and fill its SOPS age recipients.
Build and independently retain the worker using `scripts/promotion/Dockerfile` and its approved base.
The input example describes the build context and required Git, OpenSSH, Python and CA contents.

Run from **`<prefix>-tier-1/`** with those completed inputs.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-promotions.yml \
  -e @ansible/group_vars/delivery_promotion.yml -e delivery_promotion_action=render
```

Expect private `secrets/delivery-promotion/` containing `promote.json`, `rollback.json`,
`promotion-resources.yml` and an `application-source/` tree. Git and SOPS are checked before export.

### 2. Publish platform permissions and the initial application

Review the exported `platform/delivery-promotion` component, add `delivery-promotion` to
`clusters/tier1/platform/kustomization.yaml`, then approve/reconcile its platform revision above.
Provision `delivery-promotion-git` (`username`, `password`) and `delivery-promotion-signing`
(`key`, retained SSH Ed25519) through the selected encrypted Secret owner in `delivery-promotion`.
Require worker policy and its platform-owned HelmRepository, when selected, before application use.

In **the separate application Git project**, review and copy the files under
`secrets/delivery-promotion/application-source/` into their matching repository-relative paths.
The default seed creates `clusters/tier1/applications/kustomization.yaml` and
`clusters/tier1/applications/example/helmrelease.json`. For an existing application index, merge its
resource entry with the accepted entries. Publish the reviewed seed on the protected delivery branch
through the existing signed-commit process and record its full commit SHA.

Application reconciliation starts suspended. Use the independent maintenance input with
`flux_maintenance_operation: resume`, `flux_maintenance_source: tier1-applications` and that exact
SHA as `flux_maintenance_revision`. Complete its data and execution checks before setting the two
acceptance flags `flux_maintenance_data_restored` and `flux_maintenance_executions_fenced` to `true`.
Match `flux_maintenance_application_branch` to the actual protected branch, set
`flux_maintenance_approved: true` for this reviewed resumption and select the application's actual
workload in `flux_maintenance_health_checks`. For the fresh stateless reference, data acceptance
records that there is no retained application state to restore. Existing applications require their
actual recovery checks.
Render/review and apply through the linked maintenance procedure before running a promotion.
[Maintenance and resumption](../../../05-operations/05-delivery.md#suspend-and-recover-applications).

### 3. Import and qualify the pipelines

Retain stable pipeline IDs and supply authenticated Gate headers in an encrypted private
`secrets/delivery-promotion.yml` input using `delivery_promotion_gate_headers`. Set the actual
`delivery_promotion_gate_url` and trusted `delivery_promotion_gate_ca_path` in the local inputs.
Create the encrypted file from **`<prefix>-tier-1/`**.

```bash
ansible-vault create secrets/delivery-promotion.yml
```

Enter the header map below using the operator's accepted Gate session cookie, then save the file.

```yaml
delivery_promotion_gate_headers:
  Cookie: REPLACE_WITH_AUTHENTICATED_GATE_SESSION_COOKIE
```

Run from **`<prefix>-tier-1/`** after the application and worker resources are accepted.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-promotions.yml \
  -e @ansible/group_vars/delivery_promotion.yml \
  -e @secrets/delivery-promotion.yml --ask-vault-pass -e delivery_promotion_action=import
```

Expect the representative application's permissions and stable promotion/rollback definitions in
Gate. Present the exact digest/configuration diff before judgment and require the intended Flux
revision and target health. The Run Job account is confined to `delivery-promotion`; adoption also
revokes old direct application RoleBindings/token Secrets. Complete both positive and denial checks
below before normal delivery. Subsequent import, update and rollback use the operating guide.
[Promotion operations](../../../05-operations/05-delivery.md#operate-promotions-and-pipeline-definitions).

| Live scenario | Required evidence |
| --- | --- |
| Fresh bootstrap | Only bootstrap networking/Flux installed imperatively; Flux owns all selected releases including itself |
| Existing adoption | Preserved Helm histories, storage, known data and stable credentials; old writer/tokens denied |
| Approval | Authorized continuation and denied UI/API judgment, pipeline edit and direct Git bypass attempts; documented admin limits |
| Promotion | Exact approved digest/config/diff; expected-head concurrency check; intended Flux revision and relevant workload/Helm health |
| Retry/supersession | No duplicate release from retry; conflicting or superseded change cannot report success |
| Drift | Approved reversible workload change corrected by Flux, including Helm drift correction |
| Upgrade/rollback | Controlled Flux self-upgrade and product/schema gate; approved compatible Git rollback |
| Spinnaker outage | External authorized platform/source maintenance succeeds while promotion remains fenced |
| GitLab/Harbor outage | Independent configuration, keys and pinned artifacts actually retrievable; no empty fallback deployment |
| Full recovery | Tier 0 first, Tier 1 rebuild, explicit data restoration and known-content checks before triggers/runners resume |

Record live results and transition exceptions in `<prefix>-architecture/deployments.md`. Render/unit
checks, Kubernetes Ready and recreated PVCs do not prove approval controls or full recovery.

## Recovery and stop conditions

Follow [Tier 1 product recovery](../../../05-operations/06-resilience/recovery/tier-1-products.md).
Before reconnecting a rebuilt cluster, prepare and externally approve a recovery platform revision
derived from accepted configuration. Select the product's recovery lifecycle, retained identities and
data/consumer fences, then retain that exact revision in a verified custody package. Do not point an
empty replacement cluster at a historical fresh-install payload and expect a later restore to undo
its initialization. Reconcile only guarded prerequisites until native data restoration is accepted.

Suspend applications through external maintenance, fence webhooks/runners/stale executions and retain
data/keys before repairs. Do not clear completed Jobs to force migrations, rotate stable passwords,
reinitialize a backup repository or restore data through normal reconciliation. On unexpected deletion,
schema/storage drift or conflicting writers, keep affected sources/consumers suspended until reviewed.
