# Integrate service authentication

**Working repositories:** `<prefix>-tier-0` for the Keycloak client/
identity policy; the consuming tier owns application roles and configuration.
**Prerequisites:** accepted Identity, trusted TLS and independent break-glass access.

Apply this gate to every later service with supported federation. Revisit earlier
installations after Identity acceptance; SSO is not a reason to remove recovery access.

## Step 1: Register an explicit client

Record exact HTTPS issuer, client ID, redirect/logout URIs, audience, supported flow,
scopes and the stable subject identifier. Use Authorization Code with PKCE where
supported; keep confidential-client secrets in the accepted secret service.
Do not use wildcard redirects or infer administrative rights from a verified email.

## Step 2: Configure supported native federation

| Consumer | Normal access | Separate responsibility |
| --- | --- | --- |
| GitLab | [Native OIDC installer contract](../../stage-9-development/procedures/gitlab.md) | Approve accounts, project membership and privileged CI maintainers |
| Argo CD | [Keycloak OIDC / PKCE](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/keycloak/) | Map groups to bounded projects/destinations |
| Spinnaker | [Supported authentication](https://spinnaker.io/docs/setup/other_config/security/authentication/) | Application/account permissions and release approval |
| Vault administrators | [Human OIDC](https://developer.hashicorp.com/vault/docs/auth/jwt) | Named role/group policies; CI has its own GitLab JWT backend |
| Kubernetes / cluster UI | Selected API/UI OIDC integration | Scoped RBAC; never distribute bootstrap administrator credentials to users |
| Earlier hypervisor/control tools | Qualify the product's supported realm/federation interface | Keep local emergency access; do not assume every product supports OIDC |
| Unsupported service | Explicit documented exception, restricted network and separate credentials | Review replacement/integration options instead of claiming SSO |

Authentication and authorization are different. Service accounts, runner tokens
and CI workload identity are not human SSO. Record each application's approved
read/write/admin mappings and test a denied role.

## Step 3: Accept and migrate normal use

Verify an authorized user, unauthorized user, removed membership, expired session,
sign-out/revocation behavior and IdP outage. Forward authentication and role-change
events to protected logging. Migrate normal logins only after these pass; disable
or restrict bootstrap credentials according to the product's supported procedure.
Retain independently tested emergency access and audit its use.

Return to the consuming stage and record its acceptance evidence. This shared gate
does not itself install or configure every service's federation adapter.
