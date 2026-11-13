# Vault authentication for infrastructure CI

**Stage route:** [Stage 9, Step 17](../README.md#step-17-configure-exact-vault-job-authority) creates exact job authority.
**Return:** to Step 17 after policy configuration. Credential placement and real job tests belong to
[Step 19](../README.md#step-19-place-scoped-credentials-and-prove-real-job-authorization), after `iac-1` is installed at Step 18;
finish them before state handover.

**Working repository:** `<prefix>-tier-0`.
**Prerequisites:** accepted Vault with audit/backup/recovery, GitLab HTTPS,
independently authorized Vault administration and accepted direct-CI trust.
This configures an existing Vault; it does not initialize, unseal or replace it.

## Contents

- [Step 1: Configure exact job authority](#configure-exact-job-authority)
- [Step 2: Place scoped credentials](#place-scoped-credentials)
- [Step 3: Prove authorization](#prove-authorization)
- [References](#references)

<a id="configure-exact-job-authority"></a>

## Step 1: Configure exact job authority

From the **Tier 0 root**, create the local input file:

Run from **`<prefix>-tier-0/`**.

```bash
cp -n terraform/deployments/ci-auth/terraform.tfvars.example terraform/deployments/ci-auth/terraform.tfvars
```

Edit in **`<prefix>-tier-0/`**.

- `terraform/deployments/ci-auth/terraform.tfvars`: GitLab issuer/project/ref claims, Vault policy and
  scoped credential paths.

| Field in `terraform/deployments/ci-auth/terraform.tfvars` | Set |
| --- | --- |
| `gitlab_issuer`, `vault_audience` | Exact accepted GitLab/Vault HTTPS origins |
| `gitlab_ca_pem` | Public GitLab CA chain if private; no CA key |
| `projects.tier0-infrastructure` | Exact numeric project/namespace IDs, protected branch, KV-v2 read path and runner CIDRs |
| `accept_trusted_ci` | `true` only after recording the direct-CI trust decision |

1. Configure normal Vault administration through Keycloak using the
   [service SSO gate](../../stage-5-identity/procedures/service-sso.md). Retain independent
   recovery access. CI authentication is separate: its issuer is GitLab, not Keycloak.
2. Complete the exact fields in the table above; no wildcard project or branch authority.
3. With a short-lived independently authorized Vault operator token, review/apply
   this root. `VAULT_ADDR`, `VAULT_CACERT` and `VAULT_TOKEN` stay outside Git.

Run from **`<prefix>-tier-0/`**.

```bash
umask 077
mkdir -p .terraform/state/ci-auth .terraform/plans
terraform -chdir=terraform/deployments/ci-auth init -backend-config="path=$PWD/.terraform/state/ci-auth/terraform.tfstate"
terraform -chdir=terraform/deployments/ci-auth plan -out="$PWD/.terraform/plans/ci-auth.tfplan"
```

Review the authentication backend, exact claims, policy path and planned changes.

Run from **`<prefix>-tier-0/`**.

```bash
terraform -chdir=terraform/deployments/ci-auth apply "$PWD/.terraform/plans/ci-auth.tfplan"
```

This is a Vault root with its own protected state, not a Linux/Proxmox setup.
Back it up with the other original state files. Do not recreate an existing auth
backend under another state owner.

The role binds `job_project_id`, namespace, branch type/name, protected status and
audience. It grants only one KV-v2 read path, omits the default policy and caps
token lifetime. These checks require a GitLab version that emits the selected claims. [1][2]

**Pause here if `iac-1` is not installed yet.** Return to
[Stage 9, Step 18](../README.md#step-4-hand-over-infrastructure-execution) to commission its protected
project runner. Continue below from that runner's accepted network/identity before enabling IaC jobs;
general Tier 1 build runners are not a substitute for testing this authority.

<a id="place-scoped-credentials"></a>

## Step 2: Place scoped credentials

Keep infrastructure plan/apply jobs disabled while commissioning authentication.
Prepare a private JSON file with `proxmox_api_url`, `proxmox_api_token_id`,
`proxmox_api_token_secret` and `ssh_private_key`. Use the least-privilege API/SSH
identities required for this repository; never reuse a human or root credential.

Run from **`<prefix>-tier-0/`**.

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

<a id="prove-authorization"></a>

## Step 3: Prove authorization

Test the accepted project/branch/audience and deny another project, namespace,
unprotected branch, merge-request ref, wrong audience and wrong source address.
Confirm no credential appears in job output, artifacts, shell history or persistent
checkout files. Restrict Vault network access and audit reads/role changes.
Short-lived tokens and SSO do not compensate for compromise of the trusted CI issuer.
After the real protected-runner tests pass, continue with [handover](handover.md).

## References

1. [Vault JWT role and claim binding](https://developer.hashicorp.com/vault/api-docs/auth/jwt).
2. [GitLab CI ID tokens and claims](https://docs.gitlab.com/ci/secrets/id_token_authentication/).
