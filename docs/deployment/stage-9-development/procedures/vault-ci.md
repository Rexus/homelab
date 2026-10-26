# Vault authentication for infrastructure CI

**Working repository:** `<prefix>-tier-0`.
**Prerequisites:** accepted Vault with audit/backup/recovery, GitLab HTTPS,
independently authorized Vault administration and accepted direct-CI trust.
This configures an existing Vault; it does not initialize, unseal or replace it.

## Contents

- [Configure exact job authority](#configure-exact-job-authority)
- [Place scoped credentials](#place-scoped-credentials)
- [Prove authorization](#prove-authorization)
- [References](#references)

## Configure exact job authority

1. Configure normal Vault administration through Keycloak using the
   [service SSO gate](../../stage-5-identity/procedures/service-sso.md). Retain independent
   recovery access. CI authentication is separate: its issuer is GitLab, not Keycloak.
2. From Tier 0, seed `terraform/deployments/ci-auth/terraform.tfvars` from its example.
   Set exact project/namespace IDs, protected branch, HTTPS issuer/audience,
   approved runner source CIDRs and the public GitLab CA chain if private.
   Set `accept_trusted_ci = true` only after recording the explicit trust decision.
3. With a short-lived independently authorized Vault operator token, review/apply
   this root. `VAULT_ADDR`, `VAULT_CACERT` and `VAULT_TOKEN` stay outside Git.

```bash
umask 077
mkdir -p .terraform/state/ci-auth .terraform/plans
terraform -chdir=terraform/deployments/ci-auth init -backend-config="path=$PWD/.terraform/state/ci-auth/terraform.tfstate"
terraform -chdir=terraform/deployments/ci-auth plan -out="$PWD/.terraform/plans/ci-auth.tfplan"
```

Review the authentication backend, exact claims, policy path and planned changes.

```bash
terraform -chdir=terraform/deployments/ci-auth apply "$PWD/.terraform/plans/ci-auth.tfplan"
```

This is a Vault root with its own protected state, not a Linux/Proxmox setup.
Back it up with the other original state files. Do not recreate an existing auth
backend under another state owner.

The role binds `job_project_id`, namespace, branch type/name, protected status and
audience. It grants only one KV-v2 read path, omits the default policy and caps
token lifetime. These checks require a GitLab version that emits the selected claims. [1][2]

## Place scoped credentials

Prepare a private JSON file with `proxmox_api_url`, `proxmox_api_token_id`,
`proxmox_api_token_secret` and `ssh_private_key`. Use the least-privilege API/SSH
identities required for this repository; never reuse a human or root credential.

```bash
vault kv put kv/ci/tier0 @/absolute/private/tier0-ci.json
```

The file must be private and outside Git. The supplied auth root does not store
these values in Terraform state. Ensure a KV-v2 engine exists at `kv` first.
The example policy's `kv/data/ci/tier0` is the API path; CLI requests use
`kv/ci/tier0`.

The CI helper exchanges a job ID token through the native Vault CLI, writes only
a temporary private SSH file, exports API credentials in the process environment
and revokes its Vault token on exit. It does not use the paid `secrets:vault`
convenience integration. GitLab ID tokens are available across editions. [2]
Vault token expiry does not rotate an underlying static Proxmox/SSH credential;
record its independent rotation/revocation schedule.

## Prove authorization

Test the accepted project/branch/audience and deny another project, namespace,
unprotected branch, merge-request ref, wrong audience and wrong source address.
Confirm no credential appears in job output, artifacts, shell history or persistent
checkout files. Restrict Vault network access and audit reads/role changes.
Short-lived tokens and SSO do not compensate for compromise of the trusted CI issuer.
Continue with [handover](handover.md).

## References

1. [Vault JWT role and claim binding](https://developer.hashicorp.com/vault/api-docs/auth/jwt).
2. [GitLab CI ID tokens and claims](https://docs.gitlab.com/ci/secrets/id_token_authentication/).
