# Bootstrap-to-CI handover

**Working repositories:** `<prefix>-tier-0` for the dedicated infrastructure project and
runner; each target tier keeps its definitions, inventory, inputs and state.
**Prerequisites:** accepted [runner](infrastructure-runner.md), [Vault job authority](vault-ci.md),
GitLab backup/recovery and a maintained independent Tier 0 workstation.
This path runs **trusted operator IaC**, not untrusted Tier 2 request code.

## Step 1: Restore one persistent collection

1. Create private repositories for the generated tiers and Shared; import reviewed
   history/branches. Keep the infrastructure project restricted to Tier 0 principals.
2. Restore the collection beneath `/srv/iac/` on `iac-1`, with the same sibling
   names and approved Shared revision. Restore ignored inventories, vars, known hosts,
   original state and recovery inputs from the protected backup.
3. Stop workstation writes and verify ownership, permissions, lineage and resource
   addresses. Keep one writer per root. An empty checkout or `init` is not a restore.

Do not generate replacement secrets or bootstrap another cluster. Retain the
existing `.terraform/state/<setup>/prod/terraform.tfstate` and separate cluster/
template states. If a backend actually changes, migrate that existing state
deliberately and test recovery; merely enabling GitLab does not change the backend.

## Step 2: Configure the protected pipeline

Use Tier 0's [CI example](../../../../tier-0/ci/gitlab-iac.yml.example).
The supplied helper currently runs the Linux Terraform/Ansible setup path;
cluster/template lifecycle retains its dedicated commands and state contracts.
Do not imply that this example implements their upgrade/recovery workflows.

| Protected setting | Contract |
| --- | --- |
| `IAC_TRUST_CI_CONTROL_PLANE` | `true` only after the direct-CI trust decision |
| `IAC_REPOSITORY_DIR` | Absolute persistent owning-tier checkout, not the ephemeral CI checkout |
| `IAC_SHARED_DIR`, `IAC_SHARED_REVISION` | Sibling Shared checkout and reviewed exact commit |
| `IAC_SETUP` | One registered Linux setup; use separate reviewed jobs for different roots |
| `IAC_ENV_FILE` | Absolute approved **non-secret** environment file; remove old bootstrap API credentials so they cannot override Vault injection |
| `VAULT_ADDR`, `VAULT_CACERT` | Exact trusted Vault endpoint and local CA file |
| `VAULT_ROLE`, `VAULT_SECRET_PATH` | Accepted role and CLI path such as `kv/ci/tier0` |

Supply approved SSH **public-key paths** through the non-secret environment.
The private key is fetched per job. Do not enable CI debug tracing.
General Tier 1 jobs must not reach these settings, the Tier 0 runner or its
Vault secret path. Test server-side runner protection, not just a matching tag.

The helper checks the persistent repository is clean, fetches the exact CI commit,
and switches without discarding local work. Dirty tracked files stop execution.
Ignored project inputs/state remain intact. Shared is checked against its approved
commit rather than silently updated; execution calls that verified Shared checkout directly.

The pipeline and persistent target checkout must represent the **same GitLab
project**: `CI_COMMIT_SHA` selects that repository's reviewed commit. Cross-project
or tenant requests require the separate bounded controller; changing a directory
variable is not a cross-repository authorization mechanism.

## Step 3: Prove plan, apply and recovery

1. Run the plan job against the restored original state. Stop on unexpected
   replacements, deletions, missing resources or a new empty lineage.
2. Review the private runner-local saved plan, then authorize the manual apply job.
   `--plan-file` applies that exact plan; failed replans invalidate older plans.
   The private context fingerprints inventory, ordered local inputs, roles and Shared
   automation. Changed configuration requires a new plan and review.
   Plans, state, credentials and private inputs are never CI artifacts.
3. Verify the intended change, Ansible results, log/audit delivery and temporary-key
   cleanup. Test denied jobs and state locking. Retain encrypted independent copies.

Jobs are serialized and Terraform retains backend locking. Do not run another
pipeline or workstation change between plan and acceptance; state changes can
invalidate a saved plan. A project variable change does not authorize another scope.
If Terraform succeeds but Ansible fails, retry the same apply job with unchanged inputs.
A private completion context resumes configuration without applying Terraform again.
Changing inputs instead requires a new reviewed plan. Successful completion removes
the context; a completed apply cannot be replayed.

Test recovery with GitLab, Vault or SSO unavailable: stop/disable hosted execution,
restore original inputs/state/credentials to the independent workstation, then run
the existing tier-local commands. Normal hosted execution may stop during an outage;
Tier 0 recovery must not depend on it. Keep recovery credentials outside Vault too.

After acceptance, use [Stage 10](../../stage-10-lab-environments/README.md) for lab requests.
Never execute arbitrary user Terraform, providers, hooks or CI definitions on this runner.
