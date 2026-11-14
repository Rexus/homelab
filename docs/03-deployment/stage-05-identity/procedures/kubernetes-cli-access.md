# Kubernetes CLI access before Headlamp

Commission a human login path after the [API OIDC rollout and state commit](kubernetes-sso.md#commit-the-reviewed-state).
This installs a public Keycloak client and namespace RoleBindings, then renders a separate human kubeconfig.
It runs without Headlamp, Vault or another application installer. Human login and denial remain live acceptance.

**Working repository:** `<prefix>-tier-0/`, on an authorized workstation with a local browser.
**Prerequisites:** accepted Keycloak/FreeIPA federation, the API's existing `headlamp` audience,
retained X509 recovery credentials, selected existing namespaces, and controller HTTPS trust for Keycloak.
Acquire an approved **int128/kubelogin** executable through the accepted software-intake process; record its
release/checksum and absolute local path. Azure's same-named kubelogin is a different client.
The recipe checks the native help interface before changes; it does not download a login executable. [1]

## Contents

- [1. Configure the public integration](#1-configure-the-public-integration)
- [2. Render and inspect](#2-render-and-inspect)
- [3. Register the client and namespace access](#3-register-the-client-and-namespace-access)
- [4. Verify real human access](#4-verify-real-human-access)
- [5. Revoke, recover and return](#5-revoke-recover-and-return)
- [Offline verification](#offline-verification)
- [References](#references)

## 1. Configure the public integration

Run from **`<prefix>-tier-0/`**.

```bash
cp -n ansible/group_vars/kubernetes_human_access.yml.example ansible/group_vars/kubernetes_human_access.yml
```

Edit **`ansible/group_vars/kubernetes_human_access.yml`**. The
[SSO defaults](../../../../tier-0/ansible/roles/control_applications/defaults/sso-human.yml) own optional settings.

| Input | Required selection |
| --- | --- |
| `sso_human_keycloak_url`, `sso_human_realm` | Existing HTTPS provider origin and federation realm; together match the API issuer |
| `sso_human_api_server`, `sso_human_api_ca_pem` | Exact accepted API endpoint and public CA from the retained recovery context |
| `sso_human_oidc_ca_pem` | Public issuer CA bundle, independently retained |
| `sso_human_admin_kubeconfig`, `sso_human_admin_context` | Existing certificate-only recovery identity; used only by the installer |
| `sso_human_kubelogin` | Absolute approved int128/kubelogin executable on this workstation |
| `sso_human_group` | Exact prefixed reader group, such as `oidc:platform-viewers`; no automatic user/group creation |
| `sso_human_namespaces` | Explicit existing namespace names; choose the namespace used for the read/denial checks below |
| `sso_human_output` | Optional private absolute output directory; default `secrets/kubernetes-human-access/` in Tier 0 |

Keep `sso_human_client_id: kubernetes-cli` unless a dedicated alternative name is approved.
The client uses authorization code with PKCE S256, one exact loopback callback
`http://localhost:8000`, no shared secret, and no password/service-account grant. Its direct group mapper
emits flat groups. Its custom audience mapper adds `headlamp` to the **ID token**, independently of the
later confidential Headlamp client. The API continues to authenticate `sub` with the `oidc:` prefix. [2][3]

Select a directory user belonging to the reader group and a separate unbound user. Review other existing
RBAC grants for both accounts; this workflow adds only namespaced `view` bindings and removes no existing grants.
Reserve a different existing namespace where neither user has access for the denial check.

## 2. Render and inspect

Run from **`<prefix>-tier-0/`**.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/kubernetes-human-access.yml
```

**Expected:** offline render creates `keycloak-client.yml`, `namespace-rbac.yml` and `kubeconfig.yml`
under `sso_human_output`, with private permissions. Inspect the exact client callback, audience/group mappers,
namespace list and group. The kubeconfig contains public endpoint/CA data and an exec login command;
it contains no recovery certificate/key, static bearer token or client secret. Render never obtains a human token.
The [SSO tasks](../../../../tier-0/ansible/roles/control_applications/tasks/sso-human.yml) invoke only this workflow.

## 3. Register the client and namespace access

Supply a private encrypted override containing `sso_human_keycloak_auth` with `auth_realm`, `auth_username`
and `auth_password`, using the accepted [Ansible Vault workflow](../../../05-operations/03-cryptography/ansible-vault.md).
This is an existing realm-administration identity; do not place it in the public input or human kubeconfig.

Run from **`<prefix>-tier-0/`** after reviewing the rendered output.

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/deployment/kubernetes-human-access.yml \
  -e @/absolute/private/identity-administration.yml --ask-vault-pass \
  -e sso_human_action=apply
```

For unattended authorized execution, replace `--ask-vault-pass` with the existing `--vault-id` mechanism.
The [apply tasks](../../../../tier-0/ansible/roles/control_applications/tasks/sso-human-apply.yml)
first verify the retained X509 target matches the configured endpoint/CA and each selected namespace is Active.
Native Keycloak and Kubernetes modules then converge only this public client and `oidc-cli-viewers`
RoleBindings to the built-in `view` ClusterRole. They create no namespace or ClusterRoleBinding. [2][4]

**Expected:** a repeated apply converges the same client and bindings; there is no login prompt,
Headlamp installation, machine patch, reboot, realm creation or replacement of recovery credentials.
Removing a namespace from the input does not prune its old binding: explicitly review/revoke that binding.

## 4. Verify real human access

On **the same browser-capable human workstation**, set the rendered kubeconfig path and selected names.
Keep this separate from the recovery kubeconfig. Use the private output directory selected above.

```bash
export HUMAN_KUBECONFIG=/absolute/private/kubernetes-human-access/kubeconfig.yml
export READ_NAMESPACE=approved-existing-namespace
export DENIED_NAMESPACE=other-existing-namespace
kubectl --kubeconfig "$HUMAN_KUBECONFIG" auth whoami -o json
```

**Expected:** the native exec plugin opens the existing IdP login in the local browser. Sign in as the
reader user. Record the returned `oidc:<subject>` and expected `oidc:` groups, without recording tokens.
Successful API `whoami` establishes authenticated identity; do not substitute `--as` impersonation or X509. [1][4]

Run on **the same workstation**, using that human kubeconfig.

```bash
kubectl --kubeconfig "$HUMAN_KUBECONFIG" -n "$READ_NAMESPACE" get pods
```

**Expected:** the selected namespace read succeeds. Check deployment writes on **the same workstation**.

```bash
kubectl --kubeconfig "$HUMAN_KUBECONFIG" -n "$READ_NAMESPACE" auth can-i create deployments
```

**Expected:** `no` and a nonzero exit status. Check Secret access on **the same workstation**.

```bash
kubectl --kubeconfig "$HUMAN_KUBECONFIG" -n "$READ_NAMESPACE" auth can-i get secrets
```

**Expected:** `no` and a nonzero exit status. Check the unbound namespace on **the same workstation**.

```bash
kubectl --kubeconfig "$HUMAN_KUBECONFIG" -n "$DENIED_NAMESPACE" get pods
```

**Expected:** Forbidden and a nonzero exit status. Namespace `view` does not permit Secrets. [4]

For a fresh login, run the approved executable's `clean` command with the same private cache directory,
sign out of the IdP browser session, and repeat `whoami`/namespace reads as the unbound user.

Run on **the same workstation**, replacing the executable/output paths with the configured values.

```bash
/absolute/approved/bin/kubelogin clean --token-cache-dir=/absolute/private/kubernetes-human-access/tokens
```

**Expected:** the unbound user's identity authenticates but selected namespace reads are Forbidden.
Remove the reader user's group through the directory owner, wait for federation synchronization and
token expiry or clear the cache/reissue, then verify the old permission is denied. Restore only the
approved membership. Existing tokens may retain claims until expiry; cache cleanup alone does not revoke them.
Record real accepted/denied subjects, namespaces, timestamps and API/IdP audit evidence.

## 5. Revoke, recover and return

The identity owner disables/removes the dedicated CLI client to stop new login/refresh; existing
tokens remain subject to their expiry and API validation. To revoke namespace permission immediately,
the cluster owner removes the exact `oidc-cli-viewers` RoleBinding from the affected namespace through
the Kubernetes API. Review other grants separately. Keep the reader group and client distinct from recovery access.

Continue at [API outage and recovery acceptance](kubernetes-sso.md#outage-and-recovery-acceptance)
with these real human credentials and the retained X509 context. Only after those gates pass may Stage 6
enable `control_applications_headlamp_api_oidc_accepted`. The CLI setup and offline checks do not prove
live login, denial, outage or UI acceptance. Return to [Stage 5 action 23](../README.md#step-23-accept-api-outage-and-independent-recovery).

## Offline verification

Run from **the upstream deployment-kit checkout** with the declared native Ansible collections installed.

```bash
PYTHONPATH=tests python3 -B -m unittest test_tier_deployment_automation_paths.HumanAccessContracts -v
```

These tests render native resources, check unsafe-input/recovery-identity guards and use a
nonauthenticating CLI-help fixture for repeatable offline execution. They do not validate a real plugin
login, Keycloak token issuance or live Kubernetes authorization. Complete Step 4 with actual users separately.

## References

Sources checked 2026-11-11.

1. [int128/kubelogin usage, PKCE, loopback login and token cache](https://github.com/int128/kubelogin/blob/master/docs/usage.md).
2. [Ansible native Keycloak client module](https://docs.ansible.com/projects/ansible/latest/collections/community/general/keycloak_client_module.html).
3. [Keycloak audience mapping](https://www.keycloak.org/docs/latest/server_admin/index.html)
   and [ID-token/custom-audience mapper implementation](https://github.com/keycloak/keycloak/blob/main/services/src/main/java/org/keycloak/protocol/oidc/mappers/AudienceProtocolMapper.java).
4. [Kubernetes OIDC and exec authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
   and [namespace RoleBindings and view](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).
