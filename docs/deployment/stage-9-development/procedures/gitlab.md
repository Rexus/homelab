# GitLab on Kubernetes

**Working repository:** `<prefix>-tier-1`. Branch from
[Stage 9, Step 1](../README.md#step-1-deploy-source-control-and-sso).
The native Ansible recipe renders or installs the official Helm chart.
The main path installs Community Edition; no paid Vault CI integration is required.

## Contents

- [Prepare dependencies](#prepare-dependencies)
- [Render and install](#render-and-install)
- [Delivery ownership](#delivery-ownership)
- [Acceptance and recovery](#acceptance-and-recovery)
- [References](#references)

## Prepare dependencies

1. Qualify the chart's current external-data requirements. PostgreSQL, Redis,
   Gitaly and object storage are separately managed prerequisites. The production
   reference is Cloud Native Hybrid, not an all-in-one Kubernetes installation. [1]
2. Provision the dependency VMs, buckets, scoped accounts and backups with
   [GitLab data services](data-services.md), or qualify existing services against
   the following contracts before installation.
3. Create the Keycloak confidential client using the
   [service SSO gate](../../stage-5-identity/procedures/service-sso.md).

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

## Render and install

From Tier 1, seed private inputs without replacing existing files:

```bash
umask 077
cp -n ansible/group_vars/development_platform.yml.example ansible/group_vars/development_platform.yml
```

Set exact chart pins, endpoints, issuer and ingress class. In the accepted deployment
virtual environment, install Tier 1's control-node dependencies from approved sources:

```bash
python3 -m pip install -r ansible/requirements.txt
ansible-galaxy collection install -r ansible/requirements.yml
```

Qualify and pin these tools in the project toolchain. Current chart qualification
uses Helm 4 and `kubernetes.core` 6.6 or newer. The precheck reports missing tooling.
The main-path data-service recipe produces `secrets/development-data/platform-inputs.yml`;
load it last to retain its endpoint, bucket and backup settings. For independently
commissioned existing dependencies, author the same settings locally and omit that overlay.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/development-platform.yml -e @ansible/group_vars/development_platform.yml -e @secrets/development-data/platform-inputs.yml
```

The default `render` action does not contact Kubernetes. Review private
`secrets/development-platform/gitlab-values.yml` and `gitlab-manifests.yml`.
These are rendered outputs, not a second authored configuration.
The [values template](../../../../tier-1/ansible/roles/development_platform/templates/gitlab-values.yml.j2)
is the implementation source.

Supply the exact Secrets named in
[the secret example](../../../../tier-1/ansible/group_vars/development_platform_secrets.yml.example)
through an accepted Vault-backed controller, or explicit encrypted bootstrap inputs.
Never run both secret owners. The OIDC `provider` value is native GitLab YAML:

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

After dependency/Secret preparation, choose `apply` for bootstrap-owned installation:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, ansible/playbooks/deployment/development-platform.yml -e @ansible/group_vars/development_platform.yml -e @secrets/development-data/platform-inputs.yml -e development_platform_action=apply
```

For explicit bootstrap Secret management, add `-e @/absolute/private/gitlab-secrets.yml`;
encrypt that file or keep it outside Git. Apply checks required Secrets and OIDC
issuer/callback before Helm, then waits for release readiness. It never formats disks.
The same release owner reconciles the native toolbox backup CronJob on every run;
retain its independent-copy and restore duties from the data-service procedure.

## Delivery ownership

Direct Ansible installation is a valid first path. Alternatively, render values
and use the selected [Argo CD](../../stage-7-delivery/step-2a-argocd.md) or
[Spinnaker](../../stage-7-delivery/step-2b-spinnaker.md) owner.
Pre-provision Secrets in that path too; rendering creates no live Secrets.
Record one owner and stop direct Ansible apply before adopting an existing release.
Review the adoption diff with pruning disabled; never uninstall a stateful release to hand it over.

## Acceptance and recovery

Verify health, SSO with denied/unapproved users, scoped clone/push, repository and
artifact access, audit delivery and a matching-version clean-target restore.
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
