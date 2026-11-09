# GitLab on Kubernetes

**Working repository:** `<prefix>-tier-1`. Branch from
[Stage 9, Step 1](../README.md#step-1-deploy-source-control-and-sso).
The native Ansible recipe renders or installs the official Helm chart.
The main path installs Community Edition; no paid Vault CI integration is required.

## Contents

- [1. Accept the data services](#prepare-dependencies)
- [2. Register GitLab SSO](#2-register-gitlab-sso)
- [3. Create the application inputs](#render-and-install)
- [4. Install controller dependencies](#4-install-controller-dependencies)
- [5. Prepare the GitLab Secrets](#5-prepare-the-gitlab-secrets)
- [6. Render the chart](#6-render-the-chart)
- [7. Review the rendered resources](#7-review-the-rendered-resources)
- [8. Choose the release owner](#delivery-ownership)
- [9. Apply with Ansible](#9-apply-with-ansible)
- [10. Verify access and recovery](#acceptance-and-recovery)
- [References](#references)

<a id="prepare-dependencies"></a>
<a id="step-1-prepare-dependencies"></a>

## 1. Accept the data services

1. Qualify the chart's current external-data requirements. PostgreSQL, Redis,
   Gitaly and object storage are separately managed prerequisites. The production
   reference is Cloud Native Hybrid, not an all-in-one Kubernetes installation. [1]
2. Provision the dependency VMs, buckets, scoped accounts and backups with
   [GitLab data services](data-services.md), or qualify existing services against
   the following contracts before installation.

| Dependency | Contract |
| --- | --- |
| Tier 1 runtime | Healthy cluster, compatible Helm/Ansible collection, capacity, DNS and accepted ingress class |
| PostgreSQL | Supported version, `gitlabhq_production`, `gitlab` role, extensions, verified server identity and a permitted client certificate [2][7] |
| Redis | Supported external service, authentication and trusted TLS listener on 6379 [5] |
| Gitaly | External `default` storage, TLS on 8076, matching RPC token and `gitlab-shell-auth` internal API secret for hooks [6] |
| Object storage | Distinct configured buckets plus `gitlab-backups` / `gitlab-backup-tmp`; scoped credentials and independent backups [3] |
| TLS/CA | `gitlab-tls` and `gitlab-ca` in the selected namespace; trusted by users, jobs and dependencies |
| OIDC | Exact issuer, stable subject and callback `https://<gitlab>/users/auth/openid_connect/callback` [4] |
| Logging | GitLab authentication/admin events and runner execution reach protected intake |

No data service is silently created by this installer. For an existing service,
record ownership, version, endpoint and accepted backup/restore procedure.
Two web pods do not make PostgreSQL, Gitaly or the whole installation highly available.
The `gitlab-postgresql-tls` Secret supplies `tls.crt`, `tls.key` and `ca.crt`.
The chart mounts these files and exports libpq's verified-TLS settings; its database
host must match the server certificate. A password-only Secret is insufficient. [7]

## 2. Register GitLab SSO

In **Keycloak**, create the confidential GitLab client using the
[service SSO gate](../../stage-5-identity/procedures/service-sso.md).
Set the exact callback `https://<gitlab>/users/auth/openid_connect/callback`, stable `sub`
and approved group/membership policy. Retain its client credential for Step 5.

<a id="render-and-install"></a>
<a id="step-2-edit-render-and-install"></a>

## 3. Create the application inputs

Run from **`<prefix>-tier-1/`**.

```bash
umask 077
cp -n ansible/group_vars/development_platform.yml.example ansible/group_vars/development_platform.yml
```

In **`<prefix>-tier-1/`**, edit `ansible/group_vars/development_platform.yml`:

| Field | Set |
| --- | --- |
| `development_platform_components` | `[gitlab]` for this step |
| `development_platform_kubeconfig`, `development_platform_context` | Private Tier 1 kubeconfig and its exact context; `KUBECONFIG` may supply the path |
| `development_platform_gitlab_version` | Exact accepted chart pin matching the data-service package |
| `development_platform_host`, `development_platform_domain`, `development_platform_ingress_class` | Actual GitLab hostname/domain and accepted ingress class |
| `development_platform_oidc_issuer` | Existing Keycloak realm's HTTPS issuer |

The main-path data recipe produces `secrets/development-data/platform-inputs.yml`.
Load it last in every render/apply command below to retain endpoints, buckets and backup settings.
For independently commissioned existing services, fill those same fields in the authored inputs
and omit only that overlay argument.

## 4. Install controller dependencies

Use **the prepared deployment virtual environment**, from **`<prefix>-tier-1/`**.
Install Python requirements through approved sources:

Run from **`<prefix>-tier-1/`**.

```bash
python3 -m pip install -r ansible/requirements.txt
```

Run from **`<prefix>-tier-1/`**.

```bash
ansible-galaxy collection install -r ansible/requirements.yml
```

Qualify and pin the project toolchain. Current chart qualification uses Helm 4 and
`kubernetes.core` 6.6 or newer; the precheck reports missing tooling.

## 5. Prepare the GitLab Secrets

Supply the exact Secrets named in
[the secret example](../../../../tier-1/ansible/group_vars/development_platform_secrets.yml.example)
through **5a** or **5b**, then continue at Step 6. Never run both owners.

### 5a. Existing Secret controller

Use the accepted Vault-backed controller to provision the selected namespace's Secrets.
Merge the data recipe's `dependency-secrets.yml` with the root, ingress and OIDC entries;
it is not a complete replacement map. Keep `development_platform_manage_secrets: false`.
Rendering creates no cluster Secrets.

### 5b. Encrypted bootstrap inputs

Run from **`<prefix>-tier-1/`**:

```bash
umask 077
mkdir -p secrets
cp -n ansible/group_vars/development_platform_secrets.yml.example secrets/gitlab-secrets.yml
```

In **`<prefix>-tier-1/`**, edit `secrets/gitlab-secrets.yml`:

1. Keep `development_platform_manage_secrets: true` and only the GitLab entries.
2. Rename its `development_platform_secrets` map to `bootstrap_gitlab_secrets`.
3. Fill the root, ingress TLS and OIDC values, then add the
   [native dependency-map merge](data-services.md#connect-the-chart).
   This retains the exact database, Redis, Gitaly, hook and object credentials produced by the data recipe.

For existing services without that generated file, fill the complete original map instead of
renaming/merging it. The OIDC `gitlab-oidc.provider` value is native GitLab YAML:

```yaml
name: openid_connect
label: Platform SSO
args:
  name: openid_connect
  scope: [openid, profile, email]
  response_type: code
  issuer: https://sso.internal.example.com/realms/platform
  discovery: true
  uid_field: sub
  pkce: true
  client_options:
    identifier: gitlab
    secret: REPLACE_IN_PRIVATE_SECRET_ONLY
    redirect_uri: https://gitlab.internal.example.com/users/auth/openid_connect/callback
```

Encrypt the completed bootstrap file from **`<prefix>-tier-1/`**:

```bash
ansible-vault encrypt secrets/gitlab-secrets.yml
```

Retain the decryption material independently. Use commands **6b** and **9b** for this branch;
the existing-controller branch uses **6a** and **9a**.
For an approved unattended job, use an Ansible Vault identity instead of the password prompt.

## 6. Render the chart

Choose the command matching Step 5. Both use the main-path data-service overlay last.
For independently commissioned existing services without that file, fill the equivalent authored
settings from Step 3 and omit `-e @secrets/development-data/platform-inputs.yml`.

### 6a. Existing Secret controller

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/development-platform.yml \
  -e @ansible/group_vars/development_platform.yml \
  -e @secrets/development-data/platform-inputs.yml -e development_platform_action=render
```

### 6b. Encrypted bootstrap inputs

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/development-platform.yml \
  -e @ansible/group_vars/development_platform.yml \
  -e @secrets/gitlab-secrets.yml --ask-vault-pass \
  -e @secrets/development-data/platform-inputs.yml -e development_platform_action=render
```

Expect private `secrets/development-platform/gitlab-values.yml` and `gitlab-manifests.yml`.
Render does not contact Kubernetes.

## 7. Review the rendered resources

In **`<prefix>-tier-1/`**, inspect those two output files. Check the chart pin, private host,
ingress, verified dependency TLS, Secret names and toolbox backup schedule.
Treat outputs as private; edit the authored inputs, not a second copy of the
[values template](../../../../tier-1/ansible/roles/development_platform/templates/gitlab-values.yml.j2).

<a id="delivery-ownership"></a>

## 8. Choose the release owner

Direct Ansible installation is a valid first path. Alternatively, render values
and use the selected [Argo CD](../../stage-7-delivery/step-2a-argocd.md) or
[Spinnaker](../../stage-7-delivery/step-2b-spinnaker.md) owner.
Pre-provision Secrets in that path too; rendering creates no live Secrets.
Record one owner and stop direct Ansible apply before adopting an existing release.
Review the adoption diff with pruning disabled; never uninstall a stateful release to hand it over.

For direct Ansible ownership, continue at Step 9. For controller ownership, complete that
selected controller's installation/adoption path, then rejoin at Step 10; skip Step 9.

## 9. Apply with Ansible

Choose the same Secret branch as the render. For independently commissioned existing services,
omit the generated overlay argument as described in Step 6.

### 9a. Existing Secret controller

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/development-platform.yml \
  -e @ansible/group_vars/development_platform.yml \
  -e @secrets/development-data/platform-inputs.yml -e development_platform_action=apply
```

### 9b. Encrypted bootstrap inputs

Run from **`<prefix>-tier-1/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/development-platform.yml \
  -e @ansible/group_vars/development_platform.yml \
  -e @secrets/gitlab-secrets.yml --ask-vault-pass \
  -e @secrets/development-data/platform-inputs.yml -e development_platform_action=apply
```

Apply checks required Secrets and OIDC issuer/callback before Helm and waits for readiness.
Namespace creation, Secret reads/writes and Helm use the same selected context. Existing inputs
without a context retain kubeconfig-default behavior; use a Tier 1-only file or set the context explicitly.
It changes the cluster without another confirmation prompt; it never formats disks.
The release owner reconciles the toolbox backup CronJob on every run. Retain its independent-copy
and restore duties from the data-service procedure.

<a id="acceptance-and-recovery"></a>
<a id="step-3-verify-access-and-recovery"></a>

## 10. Verify access and recovery

1. Verify health and SSO with accepted, denied and unapproved users.
2. Test scoped clone/push, repository hooks, artifact access and audit delivery.
3. Complete the [first backup and matching-version restore](data-services.md#backups-and-recovery).

Retain GitLab secrets/configuration, external databases, Git repositories, object
data and backup credentials independently. Helm values alone are not a backup.
Do not disable the bootstrap administrator until SSO and break-glass recovery pass.
Return to [Stage 9, Step 2](../README.md#step-2-add-on-demand-build-execution).

## References

Checked 2026-10-26; qualify exact chart and data-service versions together.

1. [GitLab chart installation and hybrid requirements](https://docs.gitlab.com/charts/installation/).
2. [External PostgreSQL requirements](https://docs.gitlab.com/charts/advanced/external-db/).
3. [External object storage](https://docs.gitlab.com/charts/advanced/external-object-storage/).
4. [GitLab OpenID Connect](https://docs.gitlab.com/administration/auth/oidc/).
5. [External Redis](https://docs.gitlab.com/charts/advanced/external-redis/).
6. [External Gitaly](https://docs.gitlab.com/charts/advanced/external-gitaly/).
7. [PostgreSQL TLS certificate mapping](https://docs.gitlab.com/charts/charts/globals/#postgresql-ssl).
