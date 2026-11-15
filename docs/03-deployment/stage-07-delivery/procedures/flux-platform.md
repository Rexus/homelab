# Install and maintain the Tier 1 Flux platform

**Selected path:** independent Tier 1 Flux installs platform services; Spinnaker promotes application
Git. Start at [Stage 7](../README.md). Existing installations first complete
[explicit adoption](flux-adoption.md). The [selected ownership figure](../../../08-reference/tier-1-delivery.md#figure-tier1-flux-ownership)
shows the resulting boundary, including independent maintenance and recovery.

**Working repository:** `<prefix>-tier-1/`, from the authorized independent execution host.

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
   only in the application project. Commission [CE branch permissions and roles](../../../08-reference/spinnaker-approval.md).
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

For a recovery rebuild, follow the independently retained recovery contract. The recovery bootstrap
installs `platform`, `tier1-platform` and `tier1-applications` suspended and verifies their live pause
before data work. It fetches the immutable bootstrap source; controlled platform resumption checks
the accepted canary hash. Normal bootstrap below still requires immediate canary reconciliation.
[Independent recovery workflow](../../../05-operations/06-resilience/recovery/tier-1-products.md).

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

For Spinnaker set `delivery_platform_spinnaker_delivery_mode: flux` and select
`delivery_platform_spinnaker_lifecycle` from the table. Retain stable credentials, the job revision
and native TLS/backup inputs.
[Native contracts](../step-2b-spinnaker.md).

| Select | Before publishing the platform revision |
| --- | --- |
| `fresh` | Accept empty MySQL/Redis claims. Each read-only guard mounts one claim and runs before persistence starts; the claims may attach on different nodes |
| `adopt` | Preserve the existing namespace, claims, credentials and product versions. The guards use authenticated SQL/Redis service connections; retain the Envoy TLS/SAN path and verify service/migration users |
| `upgrade` | Retain the accepted current manifest and checksum before rendering. Follow the dedicated upgrade runbook to obtain the independently verified backup before advancing the source |
| `recover` | Use the recovery workflow's accepted restore identity. Guards check exact per-claim markers and product data; application replicas stay zero and ingress absent until verified cutover |

[Existing-owner adoption](flux-adoption.md),
[upgrade runbook](../../../05-operations/05-delivery.md#upgrade-spinnaker),
[product recovery](../../../05-operations/06-resilience/recovery/tier-1-products.md).

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
3. For a Spinnaker upgrade, use the dedicated backup/staging entry point before source advancement.
   [Upgrade runbook](../../../05-operations/05-delivery.md#upgrade-spinnaker).
   For other platform changes, use [the external maintenance playbook](../../../05-operations/05-delivery.md#advance-an-approved-platform-revision)
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

The authority holds application Git/signing credentials in `delivery-promotion-authority`.
Spinnaker creates secretless clients in `delivery-promotion`. The approval sequence shows the
preview, judgment and authority checks.
[Approval sequence and limits](../../../08-reference/spinnaker-approval.md).

### 1. Initialize and edit the policy

Run from **`<prefix>-tier-1/`**.

```bash
bash scripts/init-local-files.sh --setup delivery-promotions
```

Edit `ansible/group_vars/delivery_promotion.yml` using the refreshed example.

| Set | Expected input |
| --- | --- |
| Application repository, branch, manifest and target | Separate application project and exact allowed namespace/resource |
| `delivery_promotion_application_namespaces`, `delivery_promotion_kustomization_path` | Match the cluster's approved application source |
| Chart/image pins and `delivery_promotion_worker_image` | Real accepted versions and worker `registry/image@sha256:…` |
| Requester, approver, executor and admin roles | Match native Fiat application/account permissions; requesters use their requester role |
| `delivery_promotion_reader_role` | Match the native Spinnaker reader group, default `tier1-delivery-readers`; the authority's Gate service identity belongs to this group |
| `delivery_promotion_authority_gate_url`, `delivery_promotion_authority_fiat_url` | Verified HTTPS endpoints; native Fiat defaults to `https://fiat.spinnaker.svc.cluster.local:7003` |
| `delivery_promotion_authority_ca_file` | Controller-local public CA file validating the authority's service certificate |
| `delivery_promotion_egress` | Client DNS destinations; authority HTTPS access is rendered automatically |
| `delivery_promotion_authority_egress` | Actual DNS, Kubernetes API, application Git, Gate and Fiat destinations/ports |
| `delivery_promotion_flux_output`, `delivery_promotion_flux_sops_age_recipients` | Absolute private platform checkout `clusters/tier1` directory and accepted age recipients |

Record the three `delivery_promotion_controls_accepted` limits after reviewing the approval contract.
Build the worker from `scripts/promotion/Dockerfile` using an approved base with Git, OpenSSH, Python
and private Git CA trust. Retain that image independently. Preserve stable pipeline IDs during adoption.

### 1a. Adopt the current pipeline template after refresh

For an existing generated collection, refresh updates the worker and roles while preserving the
project-owned `pipelines/flux-promotion.yml.j2`. Compare that file before rendering or adopting the
new authority. A preserved credential-bearing template needs the secretless client changes to work
with the new admission and credential-retirement controls.
[Current upstream template](../../../../tier-1/pipelines/flux-promotion.yml.j2).

From **`<prefix>-tier-1/`**, enter the updated upstream kit checkout, such as `/srv/src/homelab`.

```bash
read -r -p 'Updated upstream checkout (e.g. /srv/src/homelab): ' PROMOTION_UPSTREAM
git diff --no-index -- "$PROMOTION_UPSTREAM/tier-1/pipelines/flux-promotion.yml.j2" pipelines/flux-promotion.yml.j2
```

Git returns status `1` when differences are present. Merge the current client Job structure into
the project template. Keep its integration stages and stable pipeline IDs, and adopt the authority
URL, execution ID, approval ticket/instructions, projected token/public CA and secretless Job volumes.
Remove the old Git/signing Secret mounts and client-side publication commands. Review both rendered
promote/rollback definitions in Step 3 before import/adoption. Fresh generated collections already
include the current template and continue with Step 2.

### 2. Supply retained encrypted credentials

From **`<prefix>-tier-1/`**, create the private input or edit its existing encrypted version.

```bash
ansible-vault create secrets/delivery-promotion.yml
```

Set `delivery_promotion_credentials` to a mapping of **exact Secret names to `stringData` mappings**.
The defaults below follow `delivery_promotion_git_secret`, `delivery_promotion_signing_secret` and
`delivery_promotion_authority_secret` when those names are customized.

| Mapping key | Required fields |
| --- | --- |
| `delivery-promotion-git` | `username`, `password` for the separate application-project bot |
| `delivery-promotion-signing` | `key`, the retained SSH Ed25519 private signing key |
| `delivery-promotion-authority` | `ticket-key` with at least 32 independent random bytes, `gate-headers.json`, `gate-ca.pem`, `fiat-ca.pem`, `tls.crt`, `tls.key` |

`gate-headers.json` contains JSON authentication headers for a service identity in
`delivery_promotion_reader_role`, matching the native Spinnaker reader group. The promotion
application grants this group `READ` only. Its certificate authorities validate Gate and Fiat.
The authority TLS certificate must cover the service name in `delivery_promotion_authority_url`.
Retain all three credential sets
in independent custody. Reuse accepted material during recovery.

In the same encrypted input, set `delivery_promotion_gate_headers` for the operator's Gate import
session. Set its HTTPS URL and public CA through `delivery_promotion_gate_url` and
`delivery_promotion_gate_ca_path` in the local group vars. The operator can update application/pipeline
definitions, while the authority service uses its scoped read identity.

### 3. Render and publish the authority and application

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-promotions.yml \
  -e @ansible/group_vars/delivery_promotion.yml \
  -e @secrets/delivery-promotion.yml --ask-vault-pass -e delivery_promotion_action=render
```

Expect private `secrets/delivery-promotion/` artifacts containing `promote.json`, `rollback.json`,
`promotion-resources.yml` and `application-source/`. The platform export encrypts the three authority
Secrets with SOPS. Review only encrypted Secret documents into the private platform source.

For an existing credential-bearing promotion path, run the `adopt` command in Step 4 **before
publishing the replacement**. It applies the Gate execution fence first. If the new authority is
pending, keep that fence, publish the reviewed resources below, then rerun `adopt`.

Publish the updated native Spinnaker payload as well as the promotion component. For an existing
installation, use its retained `adopt` lifecycle inputs in the service-rendering step. This deploys
the Orca HTTP restrictions and automatic configuration hashes required by adoption's rollout check.
[Render the native service payload](#render-services-into-the-platform-source).

Review `platform/delivery-promotion`, add `delivery-promotion` to
`clusters/tier1/platform/kustomization.yaml`, and approve/reconcile that platform revision through the
preceding platform-maintenance step. Verify the authority Deployment, Secrets, admission policy and
binding, scoped RBAC, trusted HTTPS and network-policy paths before opening release execution.
Verify `spinnaker-authenticated-identity` is bound to the Gate Ingress and strips caller-supplied
`X-Spinnaker-User`, `X-Spinnaker-Accounts`, `X-Spinnaker-User-Origin` and `X-Spinnaker-Anonymous`.
Keep direct Gate access confined to the accepted ingress/private service policies.
Common/service configuration hashes automatically roll native service Pods. Adoption also waits for
the hardened Orca `deny-user-http-v1` profile and complete replica convergence before reopening.
The worker policy and platform-owned HelmRepository must be ready for the selected application.

In **the separate application Git project**, copy the reviewed files under
`secrets/delivery-promotion/application-source/` to their matching repository paths. Merge an existing
Kustomize index with its accepted entries. Publish the seed through the established signed-commit
process and retain its full SHA. Application reconciliation starts suspended. Resume that accepted
revision using the scoped maintenance workflow and its data/execution checks.
[Maintenance and resumption](../../../05-operations/05-delivery.md#suspend-and-recover-applications).

### 4. Import or adopt pipelines

For a **fresh installation**, run from **`<prefix>-tier-1/`** after authority/application acceptance.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-promotions.yml \
  -e @ansible/group_vars/delivery_promotion.yml \
  -e @secrets/delivery-promotion.yml --ask-vault-pass -e delivery_promotion_action=import
```

For an **existing Job-mounted credential path**, also set the adoption fields in
`ansible/group_vars/delivery_promotion.yml` and the encrypted input.

| Set | Find it in |
| --- | --- |
| `delivery_promotion_kubeconfig`, `delivery_promotion_context` | Retained Tier 1 administrator kubeconfig and selected context |
| `delivery_promotion_gitlab_url`, `delivery_promotion_gitlab_ca_path` | Existing GitLab CE endpoint and its trusted CA |
| `delivery_promotion_retired_token_id` | Old bot personal access token ID in GitLab, such as `42` |
| `delivery_promotion_gitlab_headers` | Encrypted administrator API headers used to inspect/revoke that old token |

Use replacement bot/ticket credentials. Keep ordinary execution fenced until the replacement
authority is ready. Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-promotions.yml \
  -e @ansible/group_vars/delivery_promotion.yml \
  -e @secrets/delivery-promotion.yml --ask-vault-pass -e delivery_promotion_action=adopt
```

Adoption verifies the authority/hardened Orca rollouts, revokes and verifies the old GitLab CE token,
stops old Jobs and orphan Pods, removes their Git/signing Secrets from `delivery-promotion`, then
restores the intended application permissions. On failure,
correct the reported condition and rerun `adopt` with the same retained inputs. The fence remains.
Complete the existing platform handoff's direct-deploy RoleBinding/token revocation as well.

### 5. Qualify the release path

| Live scenario | Required evidence |
| --- | --- |
| Fresh bootstrap | Flux owns selected releases after bootstrap; authority HTTPS/admission/RBAC and all required egress paths work |
| Existing adoption | Data/credentials retained; Gate fence observed; retired token, old Jobs/orphan Pods and old namespace Secrets removed |
| Approval | Authorized continuation succeeds; requester UI/API patches, restarts and unapproved execution fail at publication |
| Gate identity | Forged `X-Spinnaker-*` identity/account headers through the ingress cannot impersonate an approver or select privileged accounts |
| Credential access | Arbitrary client Secret volumes/env imports and authority-account/namespace selection denied by the installed API server |
| Exact operation | Changed digest/configuration/target/diff/policy, execution identity or expired ticket denied |
| Retry/concurrency | Exact candidate retry observes; changed delivery head requires fresh judgment; supersession fails |
| Promotion | Accepted signed candidate and exact Flux revision/target health recorded |
| Drift and upgrade | Scoped drift correction and accepted backup/data-compatibility gates exercised |
| Service outage/recovery | Independent inputs/artifacts retrieved; product restoration verified before triggers/runners resume |

The authorization tests use mocked Gate/Fiat responses and real local Git compare-and-swap. Rendered
admission resources require live API-server denial tests. Record those results, administrator limits
and any self-approval role overlap in `<prefix>-architecture/deployments.md`.
[Promotion operations](../../../05-operations/05-delivery.md#operate-promotions-and-pipeline-definitions).

## Recovery and stop conditions

Follow [Tier 1 product recovery](../../../05-operations/06-resilience/recovery/tier-1-products.md).
Before reconnecting a rebuilt cluster, prepare and externally approve a recovery platform revision
derived from accepted configuration. Select the product's recovery lifecycle, retained identities and
data/consumer fences, then retain that exact revision in a verified custody package. Do not point an
empty replacement cluster at a historical fresh-install payload and expect a later restore to undo
its initialization. Reconcile only guarded prerequisites until native data restoration is accepted.

For the [accepted-plan recovery coordinator](../../../05-operations/06-resilience/recovery/platform-recovery-contract.md),
Spinnaker's final accepted payload uses `adopt`. The coordinator restores and verifies data with roots
paused, then checks the operating consumers and normal Git ownership before network cutover.
The standalone `recover` rendering keeps consumers at zero and does not activate the recovered service.

Suspend applications through external maintenance, fence webhooks/runners/stale executions and retain
data/keys before repairs. Do not clear completed Jobs to force migrations, rotate stable passwords,
reinitialize a backup repository or restore data through normal reconciliation. On unexpected deletion,
schema/storage drift or conflicting writers, keep affected sources/consumers suspended until reviewed.
