# Native delivery installation

**Working repository:** `<prefix>-tier-1` (source: `tier-1/`). The
[delivery role](../../../../tier-1/ansible/roles/delivery_platform/) owns product
configuration; Shared executes Helm releases without owning inventory or state.
Choose `argocd`, `spinnaker`, or `none` explicitly. There is no default controller.
Spinnaker supplies a pinned native base and provisions its SQL/Redis dependencies;
follow its [native installation contract](../step-2b-spinnaker.md#installation-decision).

## Contents

- [Prerequisites](#prerequisites)
- [Inputs and secrets](#inputs-and-secrets)
- [Render and apply](#render-and-apply)
- [Readiness and recovery](#readiness-and-recovery)
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

## Inputs and secrets

Copy [delivery_platform.yml.example](../../../../tier-1/ansible/group_vars/delivery_platform.yml.example)
to its ignored `.yml` counterpart. Review the central `files/software.yml` pins, controller
selection, ingress, names, identity and storage inputs. Set
`delivery_platform_install_harbor: false` when only installing a controller.

| Input | Contract |
| --- | --- |
| `delivery_platform_controller` | Explicit `argocd`, `spinnaker` or `none`; an empty choice fails |
| `delivery_platform_action` | `render` by default; `apply` changes the selected cluster |
| `delivery_platform_kubeconfig`, `delivery_platform_context` | Both explicit for apply |
| `delivery_platform_oidc_issuer`, `delivery_platform_oidc_ca_pem` | Exact HTTPS issuer without trailing slash and public IdP CA chain |
| `delivery_platform_ca_path` | Local trusted CA bundle for HTTPS discovery and endpoint health checks |
| `delivery_platform_output` | Private render directory; default `secrets/delivery-platform/` |
| `delivery_platform_manage_secrets` | `false` uses existing secret-controller ownership; `true` explicitly provisions private bootstrap inputs |

The [secret example](../../../../tier-1/ansible/group_vars/delivery_platform_secrets.yml.example)
lists exact namespace/name/key contracts. Provision selected Secrets through the
accepted Vault controller, or fill an encrypted/private extra-vars file for explicit
bootstrap ownership. Do not run both owners. Required fields are checked before
release changes; sensitive values stay out of task output.

Harbor's bundled PostgreSQL password is a native chart value. Supply it privately
even for rendering. Rendered values/manifests and Helm's release Secrets contain
sensitive data: keep them private, encrypted in backup and outside Git/CI artifacts.

## Render and apply

From Tier 1, after preparing local inputs:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-platform.yml \
  -e @ansible/group_vars/delivery_platform.yml -e @/absolute/private/delivery-secrets.yml
```

Omit the final extra-vars file when using pre-existing Secrets, but supply Harbor's
database password through an accepted private input. Rendering downloads exact
official charts; native Spinnaker builds its supplied pinned base without downloads. Rendering never contacts
Kubernetes. It does not establish that existing Secrets or services are usable.

Review `<release>-values.yml`, `<release>-manifests.yml`, and any `before`/`after`
resources under the private output directory. Follow the selected
[Argo CD](../step-2a-argocd.md), [Spinnaker](../step-2b-spinnaker.md) and
[Harbor](registry.md) preparation contracts before applying:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/delivery-platform.yml \
  -e @ansible/group_vars/delivery_platform.yml -e @/absolute/private/delivery-secrets.yml \
  -e delivery_platform_action=apply
```

Apply checks credentials, storage where selected and verified OIDC discovery.
The Shared Helm executor waits for chart resources. Spinnaker requires the exact
reviewed output hash and stages certificates, persistence, schema initialization,
scoped identities and application startup in dependency order. Native filesystem
backups check the retained PVC/PV before resource changes and the actual mount and
repository marker inside each backup Job. Both modes require a verified first
snapshot before publishing ingress. It never executes
Halyard. No release is uninstalled or pruned by this procedure.

## Readiness and recovery

The recipe checks Harbor's component health and the controller HTTPS endpoint.
Then test accepted and denied SSO users, ordinary direct API access, rejected
sources/destinations, push/pull or a bounded deployment, rollback and clean-target
restoration. Readiness probes do not prove authorization or recoverability.
Keep bootstrap administrators until SSO and independent recovery have passed.

Record one owner for every release/resource. Stop direct Ansible apply before
adopting resources into a delivery controller. Back up original application data,
private configuration, encryption/signing keys and bootstrap credentials independently.
Retain bootstrap Git/image supply until the replacement is accepted.

## Native tests

From the upstream repository with the native tools and collections installed:

```bash
python3 -B -m unittest discover -s tests -p test_tier_delivery_platform.py -v
```

Tests render the centrally pinned official Harbor and Argo CD charts through Ansible/Helm
in both source and generated repositories. They inspect actual native workloads,
storage, ingress, OIDC and RBAC output. Spinnaker tests render the supplied native
installation in both source and generated repositories, check payload/license
preservation, schema/auth/TLS/storage wiring and stable private credentials.
Install `kubernetes-validate` for strict Kubernetes schema checks. Run:

```bash
python3 -B -m unittest discover -s tests -p test_tier_spinnaker_reference.py -v
python3 -B -m unittest discover -s tests -p test_tier_spinnaker_backup.py -v
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
