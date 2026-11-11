# Native delivery installation

**Stage route:** [Stage 7, Step 2](../README.md#step-2-select-and-qualify-delivery) for the selected
controller; [Step 3](../README.md#step-3-connect-approved-artifact-supply) for Harbor.
**Return:** to that step's acceptance checks. Select only its component; these are separate runs.

**Working repository:** `<prefix>-tier-1` (source: `tier-1/`). The
[delivery role](../../../../tier-1/ansible/roles/delivery_platform) owns product
configuration; Shared executes Helm releases without owning inventory or state.
Choose `argocd`, `spinnaker`, or `none` explicitly. There is no default controller.
Spinnaker supplies a pinned native base and provisions its SQL/Redis dependencies;
follow its [native installation contract](../step-2b-spinnaker.md#installation-decision).

## Contents

- [Prerequisites](#prerequisites)
- [1. Create local inputs](#inputs-and-secrets)
- [2. Select the installation](#2-select-the-installation)
- [3. Choose the Secret owner](#3-choose-the-secret-owner)
- [4. Render](#render-and-apply)
- [5. Review the output](#5-review-the-output)
- [6. Apply the reviewed inputs](#6-apply-the-reviewed-inputs)
- [7. Verify access and recovery](#readiness-and-recovery)
- [Native tests](#native-tests)
- [References](#references)

## Prerequisites

| Dependency | Required preparation |
| --- | --- |
| Control node | Linux, Ansible Core, Helm and `kubernetes.core >=6.6,<7`; Python `kubernetes`, `jsonpatch`, `PyYAML` for apply; native Spinnaker also uses declared `ansible.utils` and `netaddr` |
| Spinnaker only | Native Kustomize or kubectl with Kustomize; Kubernetes >=1.33, Traefik CRD, preissued TLS (or commissioned issuer), and existing independent backup storage: NAS file PVC or native HTTPS S3-compatible endpoint |
| Tier 1 cluster | Accepted Stage 4/7 cluster, CNI policy enforcement, image access and sufficient worker capacity |
| Networking | Private DNS, accepted ingress class, matching TLS certificates and node/consumer CA trust |
| Identity | Existing Keycloak clients, group claims and matching callback URLs; CA PEM and a local CA bundle |
| Harbor storage | An existing persistent StorageClass, five volume allocations and tested volume/data backup |
| Privileged tools | Explicit Tier 1 kubeconfig and context; no Tier 0 or Proxmox credentials |

The playbook does not create a cluster, ingress controller, storage provisioner or
identity provider. Use the common cluster lifecycle rather than duplicating it.
Prepare accepted existing services for these prerequisites before apply.
For Spinnaker, choose [backup storage](../step-2b-spinnaker.md#choose-backup-storage):
`s3` remains the default for existing inputs; `filesystem` consumes a dedicated,
preprovisioned NAS-backed PVC and initialized repository directly. No additional
object server or NAS-to-S3 gateway is installed. Retain the restic password separately
from the cluster and storage service. The storage owner commissions the export,
node/CSI access, permissions, retained PV and exact PVC binding before apply.

<a id="inputs-and-secrets"></a>
<a id="step-1-edit-inputs-and-prepare-secrets"></a>

## 1. Create local inputs

Run from **`<prefix>-tier-1/`**.

```bash
cp -n ansible/group_vars/delivery_platform.yml.example ansible/group_vars/delivery_platform.yml
```

Existing inputs are preserved. Continue with that file, not a second copy.

## 2. Select the installation

In **`<prefix>-tier-1/`**, edit `ansible/group_vars/delivery_platform.yml` using the table below.
Retain the approved `ansible/roles/delivery_platform/files/software.yml` pins.
For the controller-only installation, set `delivery_platform_install_harbor: false`.
[Stage 7, Step 3](../README.md#step-3-connect-approved-artifact-supply) adds Harbor later.

| Input | Contract |
| --- | --- |
| `delivery_platform_controller` | Explicit `argocd`, `spinnaker` or `none`; an empty choice fails |
| `delivery_platform_action` | `render` by default; `apply` changes the selected cluster |
| `delivery_platform_kubeconfig`, `delivery_platform_context` | Both explicit for apply |
| `delivery_platform_oidc_issuer`, `delivery_platform_oidc_ca_pem` | Exact HTTPS issuer without trailing slash and public IdP CA chain |
| `delivery_platform_ca_path` | Local trusted CA bundle for HTTPS discovery and endpoint health checks |
| `delivery_platform_output` | Private render directory; default `secrets/delivery-platform/` |
| `delivery_platform_manage_secrets` | `false` uses existing secret-controller ownership; `true` explicitly provisions private bootstrap inputs |

Complete the selected [Argo CD](../step-2a-argocd.md),
[Spinnaker](../step-2b-spinnaker.md) or [Harbor](registry.md) input/TLS/SSO contract before rendering.
Return here for the commands; do not start a second installer.

## 3. Choose the Secret owner

The [secret example](../../../../tier-1/ansible/group_vars/delivery_platform_secrets.yml.example)
lists exact namespace/name/key contracts. Choose **3a** or **3b**, then continue at Step 4.

### 3a. Existing Secret controller

In **`<prefix>-tier-1/`**, keep `delivery_platform_manage_secrets: false`.
Provision the selected product's required Secrets through the existing owner.
Use commands **4a** and **6a** below; no local bootstrap Secret file is required.

### 3b. Encrypted bootstrap inputs

Run from **`<prefix>-tier-1/`**.

```bash
umask 077
mkdir -p secrets
cp -n ansible/group_vars/delivery_platform_secrets.yml.example secrets/delivery-platform.yml
```

In **`<prefix>-tier-1/`**, edit `secrets/delivery-platform.yml`: retain
`delivery_platform_manage_secrets: true` and fill the selected product's required values.
For native Spinnaker, follow its stable-password and preissued-keystore contract.
Then encrypt the completed file:

Run from **`<prefix>-tier-1/`**.

```bash
ansible-vault encrypt secrets/delivery-platform.yml
```

Retain the decryption material independently. Use commands **4b** and **6b** below.
Do not run both Secret owners. Required fields are checked before release changes.

Harbor's bundled PostgreSQL password is a native chart value. Supply it privately
even for rendering. Rendered values/manifests and Helm's release Secrets contain
sensitive data: keep them private, encrypted in backup and outside Git/CI artifacts.

<a id="render-and-apply"></a>
<a id="step-2-render-and-apply"></a>

## 4. Render

Choose the command matching Step 3. Both render without contacting Kubernetes.

### 4a. Existing Secrets

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-platform.yml \
  -e @ansible/group_vars/delivery_platform.yml -e delivery_platform_action=render
```

If installing Harbor, supply `delivery_platform_harbor_database_password` through an accepted
private input even with externally managed Kubernetes Secrets.

### 4b. Encrypted bootstrap inputs

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-platform.yml \
  -e @ansible/group_vars/delivery_platform.yml \
  -e @secrets/delivery-platform.yml --ask-vault-pass -e delivery_platform_action=render
```

Rendering downloads exact official charts; native Spinnaker builds its supplied pinned base
without downloads. Expect private values/manifests under `secrets/delivery-platform/`, unless
`delivery_platform_output` selects another directory. Rendering does not test live prerequisites.

## 5. Review the output

In **`<prefix>-tier-1/`**, inspect `<release>-values.yml`, `<release>-manifests.yml` and any
`before`/`after` resources in the selected output directory. Check destinations, permissions,
TLS, storage and product pins against the selected branch.

For Spinnaker, record `spinnaker.sha256` as `delivery_platform_spinnaker_review_sha256`
in `ansible/group_vars/delivery_platform.yml`. Complete its certificate and backup commissioning
before continuing. Do not apply the combined Spinnaker YAML directly.

## 6. Apply the reviewed inputs

Apply changes the selected cluster without an interactive confirmation. Use the same inputs and
Secret owner as the render. For unattended execution, supply an approved Ansible Vault identity
instead of `--ask-vault-pass`; keep its decryption material outside the repository.

### 6a. Existing Secrets

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-platform.yml \
  -e @ansible/group_vars/delivery_platform.yml -e delivery_platform_action=apply
```

### 6b. Encrypted bootstrap inputs

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-platform.yml \
  -e @ansible/group_vars/delivery_platform.yml \
  -e @secrets/delivery-platform.yml --ask-vault-pass \
  -e delivery_platform_action=apply
```

Apply checks credentials, storage where selected and verified OIDC discovery.
The Shared Helm executor waits for chart resources. Spinnaker requires the exact
reviewed output hash and stages certificates, persistence, schema initialization,
scoped identities and application startup in dependency order. Native filesystem
backups check the retained PVC/PV before resource changes, commission or validate the
repository in a one-shot Job, and check its actual mount and marker inside each backup Job.
Initialization requires the explicit new-repository input; existing repositories retain their identity.
Both modes require a verified first
snapshot before publishing ingress. It never executes
Halyard. No release is uninstalled or pruned by this procedure.

<a id="readiness-and-recovery"></a>
<a id="step-3-verify-access-and-recovery"></a>

## 7. Verify access and recovery

The recipe checks Harbor's component health and the controller HTTPS endpoint. Then:

1. Test accepted and denied SSO users and ordinary direct API access.
2. Verify rejected sources/destinations, push/pull or a bounded deployment, then rollback.
3. Restore on a clean target with independently retained data, configuration and keys.
4. Record one owner per release/resource; stop direct Ansible apply before controller adoption.

Readiness probes do not prove authorization or recoverability. Keep bootstrap administrators
and Git/image supply until SSO, independent recovery and replacement supply have passed.

Back up original application data, private configuration, encryption/signing keys and
bootstrap credentials independently.
Use the selected [Tier 1 product recovery procedure](../../../05-operations/06-resilience/recovery/tier-1-products.md#select-the-authoritative-product-procedure)
for Argo CD or Harbor, or [native Spinnaker recovery](../step-2b-spinnaker.md#maintenance-and-recovery).
The Argo CD/Harbor installer does not schedule those recovery copies.

**Continue:** return to the selected [Argo CD](../step-2a-argocd.md#step-3-install-and-verify),
[Spinnaker](../step-2b-spinnaker.md#step-4-qualify-delivery) or [Harbor](registry.md#acceptance)
acceptance path, then rejoin Stage 7.

## Native tests

From the upstream repository with the native tools and collections installed:

Run from **the upstream deployment-kit checkout**.

```bash
python3 -B -m unittest discover -s tests -p test_tier_delivery_platform.py -v
```

Tests render the centrally pinned official Harbor and Argo CD charts through Ansible/Helm
in both source and generated repositories. They inspect actual native workloads,
storage, ingress, OIDC and RBAC output. Spinnaker tests render the supplied native
installation in both source and generated repositories, check payload/license
preservation, schema/auth/TLS/storage wiring and stable private credentials.
Install `kubernetes-validate` for strict Kubernetes schema checks. Run:

Run from **the upstream deployment-kit checkout**.

```bash
python3 -B -m unittest discover -s tests -p test_tier_spinnaker_reference.py -v
python3 -B -m unittest discover -s tests -p test_tier_spinnaker_backup.py -v
python3 -B -m unittest discover -s tests -p test_tier_deployment_automation_paths.py -v
```

Set `RESTIC_BINARY` to the pinned native restic executable (or put it on `PATH`)
to run real repository backup/restore and failure tests. Filesystem tests use an
existing local tmpfs mount and test actual Ansible storage assertions with API fixtures;
they do not mount or verify a live NAS. Optional
`SPINNAKER_CRD_CACHE` holds `cert-manager.yaml` (released CRDs) and `traefik.yaml`
(ServersTransport CRD); the test module records their exact revisions/checksums.
It enables strict custom-resource validation without network downloads. Missing
native executables, schema libraries or optional caches produce explicit skips.

An optional `SPINNAKER_UPSTREAM_CACHE=/absolute/reviewed/spinnaker` checkout must
match the central pinned revision and unmodified `spinnaker-kustomize/` files.
It enables provenance correspondence and upstream-demo rejection checks; native
installation tests do not require that cache. Synthetic overlay fixtures only
exercise the advanced custom-overlay admission path. No tests fetch upstream source.
These checks never apply to a cluster and do not establish live SSO, storage,
failover or restore acceptance.
The tests use PyYAML's LibYAML loader, included in standard PyYAML wheels, to parse
the official Harbor TLS template's trailing-tab YAML.

## References

Sources checked 2026-10-26; qualify chart, application and cluster releases together.

1. [Official Harbor chart](https://github.com/goharbor/harbor-helm).
2. [Official Argo Helm charts](https://github.com/argoproj/argo-helm/tree/main/charts/argo-cd).
3. [Spinnaker native installation](https://spinnaker.io/docs/setup/install/).
4. [Ansible native Kustomize lookup](https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/kustomize_lookup.html).
