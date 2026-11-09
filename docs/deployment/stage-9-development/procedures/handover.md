# Bootstrap-to-CI handover

**Working repositories:** `<prefix>-tier-0` for the dedicated infrastructure project and
runner; each target tier keeps its definitions, inventory, inputs and state.
**Prerequisites:** accepted [runner](infrastructure-runner.md), [Vault job authority](vault-ci.md),
GitLab backup/recovery and a maintained independent Tier 0 workstation.
This path runs **trusted operator IaC**, not untrusted Tier 2 request code.
It continues the [foundation bootstrap-host workflow](../../foundation/proxmox/bootstrap.md):
`boot-1` runs the initial deployments; the new `iac-1` becomes the protected runner.
Push the reviewed local repository histories after GitLab is accepted, but transfer
ignored inputs/state separately through the protected restore path below.

## Contents

- [1. Create the private projects](#1-create-the-private-projects)
- [2. Restore the persistent collection](#step-1-restore-one-persistent-collection)
- [3. Stop bootstrap writes and check state](#3-stop-bootstrap-writes-and-check-state)
- [4. Create the pipeline file](#step-2-configure-the-protected-pipeline)
- [5. Protect the project and set variables](#5-protect-the-project-and-set-variables)
- [6. Run the first plan job](#step-3-prove-plan-apply-and-recovery)
- [7. Authorize the saved-plan apply](#7-authorize-the-saved-plan-apply)
- [8. Verify the job and failure handling](#8-verify-the-job-and-failure-handling)
- [9. Prove independent recovery](#9-prove-independent-recovery)

## 1. Create the private projects

In **GitLab**, use the private infrastructure project already bound to Vault and `iac-1`.
Create any missing tier/Shared repositories and import the reviewed histories/branches.
Do not replace the bound infrastructure project with a new project ID.
Restrict it to accepted Tier 0 principals.
Do not push ignored inputs or state with the Git history.

<a id="step-1-restore-one-persistent-collection"></a>

## 2. Restore the persistent collection

On **`boot-1`**, stop deployment writes before taking the final state/input copy for handover;
keep hosted plan/apply jobs disabled during the transfer.
On **`iac-1`**, restore that collection beneath `/srv/iac/`, preserving the sibling repository names
and approved Shared revision. Restore ignored inventories, vars, known hosts, original state and
recovery inputs from the protected backup. Use the accepted
[recovery set](../../../administration/backups/recovery-set.md), not a fresh generation.

## 3. Stop bootstrap writes and check state

On **`boot-1`**, confirm deployment writes remain stopped.
On **`iac-1`**, verify workspace ownership/permissions, backend lineage and resource addresses against
the original deployment. Keep one writer per root. An empty checkout or `init` is not a restore.

Do not generate replacement secrets or bootstrap another cluster. Retain the
existing `.terraform/state/<setup>/prod/terraform.tfstate` and separate cluster/
template states. If a backend actually changes, migrate that existing state
deliberately and test recovery; merely enabling GitLab does not change the backend.

<a id="step-2-configure-the-protected-pipeline"></a>

## 4. Create the pipeline file

Use Tier 0's [CI example](../../../../tier-0/ci/gitlab-iac.yml.example).
The supplied helper currently runs the Linux Terraform/Ansible setup path;
cluster/template lifecycle retains its dedicated commands and state contracts.
Do not imply that this example implements their upgrade/recovery workflows.

Run from **`<prefix>-tier-0/`**.

```bash
cp -n ci/gitlab-iac.yml.example .gitlab-ci.yml
```

Edit in **`<prefix>-tier-0/`**.

- `.gitlab-ci.yml`: Selected setup/context and protected pipeline settings below.

If `.gitlab-ci.yml` already exists, review and merge the protected jobs explicitly; `cp -n` preserves it.
Submit the reviewed pipeline through the project's protected change process.

## 5. Protect the project and set variables

In **GitLab > the dedicated infrastructure project**, protect the selected branch and
verify the [project runner's server-side protection](infrastructure-runner.md#step-1-accept-direct-ci-trust).
Add these **protected variables**. Keep plans/state in the restored persistent runner workspace,
never CI artifacts.

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

<a id="step-3-prove-plan-apply-and-recovery"></a>

## 6. Run the first plan job

In **GitLab**, start a pipeline for the reviewed commit on the protected default branch.
Require `iac-plan` to run on `iac-1` against the restored original state.
Stop on unexpected replacements, deletions, missing resources or a new empty lineage.

## 7. Authorize the saved-plan apply

On **`iac-1`**, review the private runner-local saved plan. Then, in **GitLab**, authorize
the same pipeline's manual `iac-apply` job. `--plan-file` applies that exact plan;
failed replans invalidate older plans. The private context fingerprints inventory, ordered
local inputs, roles and Shared automation. Changed configuration requires a new plan and review.
Plans, state, credentials and private inputs are never CI artifacts.

Jobs are serialized and Terraform retains backend locking. Do not run another
pipeline or workstation change between plan and acceptance; state changes can
invalidate a saved plan. A project variable change does not authorize another scope.

## 8. Verify the job and failure handling

Require the intended change, successful Ansible results, log/audit delivery and temporary-key cleanup.
Test denied jobs and state locking. Retain encrypted independent copies.

If Terraform succeeds but Ansible fails, retry the same apply job with unchanged inputs.
A private completion context resumes configuration without applying Terraform again.
Changing inputs instead requires a new reviewed plan. Successful completion removes
the context; a completed apply cannot be replayed.

## 9. Prove independent recovery

In **an authorized recovery rehearsal**:

1. Make GitLab, Vault or SSO unavailable and stop/disable hosted execution.
2. On **the independent Tier 0 workstation**, restore original inputs, state and recovery credentials.
3. Run the existing tier-local commands and verify their state continuity and required access.
4. Stop workstation writes before returning the accepted scope to `iac-1`.

Normal hosted execution may stop during an outage; Tier 0 recovery must not depend on it.
Keep recovery credentials outside Vault too. Restrict routine bootstrap access only after this rehearsal passes.

After acceptance, use [Stage 10](../../stage-10-lab-environments/README.md) for lab requests.
Never execute arbitrary user Terraform, providers, hooks or CI definitions on this runner.
