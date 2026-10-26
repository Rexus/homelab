# Native delivery installation

**Working repository:** `<prefix>-tier-1` (source: `tier-1/`). The
[delivery role](../../../../tier-1/ansible/roles/delivery_platform/) owns product
configuration; Shared executes Helm releases without owning inventory or state.
Choose `argocd`, `spinnaker`, or `none` explicitly. There is no default controller.

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
| Control node | Linux, Ansible Core, Helm and `kubernetes.core >=6.6,<7`; Python `kubernetes`, `jsonpatch`, `PyYAML` for apply |
| Spinnaker only | Native Kustomize or kubectl with Kustomize; Git for obtaining reviewed official resources |
| Tier 1 cluster | Accepted Stage 4/7 cluster, CNI policy enforcement, image access and sufficient worker capacity |
| Networking | Private DNS, accepted ingress class, matching TLS certificates and node/consumer CA trust |
| Identity | Existing Keycloak clients, group claims and matching callback URLs; CA PEM and a local CA bundle |
| Harbor storage | An existing persistent StorageClass, five volume allocations and tested volume/data backup |
| Privileged tools | Explicit Tier 1 kubeconfig and context; no Tier 0 or Proxmox credentials |

The playbook does not create a cluster, ingress controller, storage provisioner or
identity provider. Use the common cluster lifecycle rather than duplicating it.
Prepare accepted existing services for these prerequisites before apply.

## Inputs and secrets

Copy [delivery_platform.yml.example](../../../../tier-1/ansible/group_vars/delivery_platform.yml.example)
to its ignored `.yml` counterpart. Set the exact reviewed chart versions, controller
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
official charts and builds a selected local Spinnaker overlay; it never contacts
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
reviewed output hash, submits all resources before waiting for their workloads,
and never executes Halyard. No release is uninstalled or pruned by this procedure.

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

Tests render official Harbor `1.18.0` and Argo CD `8.5.6` charts through Ansible/Helm
in both source and generated repositories. They inspect actual native workloads,
storage, ingress, OIDC and RBAC output. Kustomize tests check a scoped fixture,
rejected images/authority/review hashes and an exact official Spinnaker demo revision.
The versions are test fixtures, not deployment defaults. These checks never apply
to a cluster and do not establish live SSO, storage, failover or restore acceptance.
The tests use PyYAML's LibYAML loader, included in standard PyYAML wheels, to parse
the official Harbor TLS template's trailing-tab YAML.

## References

Sources checked 2026-10-26; qualify chart, application and cluster releases together.

1. [Official Harbor chart](https://github.com/goharbor/harbor-helm).
2. [Official Argo Helm charts](https://github.com/argoproj/argo-helm/tree/main/charts/argo-cd).
3. [Spinnaker native installation](https://spinnaker.io/docs/setup/install/).
4. [Ansible native Kustomize lookup](https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/kustomize_lookup.html).
