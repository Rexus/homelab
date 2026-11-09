# Work across the kit and private repositories

The public upstream is the reusable deployment kit. A private generated collection
contains separate tier, Shared and Architecture repositories with their own history
and responsibility. The collection directory itself is not a Git repository.

<a id="safe-repository-usage"></a>
<a id="purpose"></a>

<a id="table-of-contents"></a>

## Contents

- [Where does a change belong?](#where-does-a-change-belong)
- [Step 1: Select the private working model](#recommended-usage-models)
- [Step 2: Keep local history before hosted source control](#local-history-before-hosted-source-control)
- [Step 3: Refresh from the kit without replacing project work](#step-3-refresh-from-the-kit-without-replacing-project-work)
- [Step 4: Review before publishing](#pre-push-checks)
- [Step 5: Attach private source control and push](#example-private-mirror-in-gitlab)

## Where does a change belong?

| Change | Working location / owner |
| --- | --- |
| Reusable role, helper, module or safe starter | Upstream `tier-0/`, `tier-1/`, `tier-2/`, `shared/` or generator source; [code map](code-layout.md) |
| Project resource definitions and application code | Owning private tier repository; retain its inventory and original state |
| Site inventories, IPs, `.env.local`, local tfvars | Owning tier's ignored local files and protected backups |
| Reusable stateless code, sizes and common platform/image references | Shared; never inventories, deployed resources, private keys or another tier's state |
| Selected paths, naming and project runbooks | Project-owned Architecture/tier documents |
| Maintained reference manual | Upstream `docs/`; generated Architecture `docs/auto-docs/` is refreshed from it |

Reusable fixes belong in the kit and pass generation/refresh checks; project edits
belong in their private owner. See [local setup](local-setup.md) and
[generated ownership](generated-repositories.md#repository-ownership).

<a id="recommended-usage-models"></a>
<a id="option-1-private-fork"></a>
<a id="option-2-private-mirror"></a>
<a id="option-3-local-only-copy"></a>

## Step 1: Select the private working model

| Model | Use |
| --- | --- |
| Generated private repositories | Separate Tier 0/1/2, Shared and Architecture owners; normal collection workflow |
| Private fork | Independent project history with reviewed upstream integration |
| Private mirror/copy | Separate private operational repository, retaining the upstream reference |
| Local-only checkout/archive | Local/offline work without a remote; independent protected backups still required |

Run deployment from the owning source/generated tier root, never the upstream or
collection root. Hosted source control is optional for initial deployment;
[generation](generated-repositories.md#purpose-and-prerequisites) creates files without Git or remotes.

<a id="local-history-before-hosted-source-control"></a>

## Step 2: Keep local history before hosted source control

1. On the bootstrap execution host, enter one generated repository. For a new repo
   without Git history, initialize it and inspect ignored paths:

   Run from **the owning generated repository root**.

   ```bash
   git init -b main
   git status --short --ignored
   ```

2. Review `.gitignore` and stage explicit safe files. Complete the
   [staged secret check](secret-scanning.md#local-checks) and inspect the staged diff before committing
   under the project's identity/signing policy. Repeat per repo; never initialize the collection directory.
3. Back up ignored operational inputs, original Terraform state and credentials
   independently. A commit or future push does not contain or recover those files.

<a id="publishing-rules"></a>
<a id="file-naming-conventions"></a>
<a id="bootstrap-secret-strategy"></a>

| Material | Publishing/custody rule |
| --- | --- |
| Reusable code/docs, safe defaults and `*.example` | Eligible for upstream after content review; suffix alone is not a secret check |
| Project-specific non-secret code/configuration | Private project history when deliberately selected; not public upstream |
| `*.local`, `.env.local`, `secrets/`, private keys and tokens | Ignored/private custody; never force-add |
| `ansible/inventory/hosts.yml`, local `group_vars/*.yml`, `terraform.tfvars` | Ignored live inputs; examples are tracked separately |
| Packer `variables.auto.pkrvars.hcl` and Ansible environment overlays | Ignored live values; publish only reviewed examples |
| State, plans and image artifacts | Protected operational storage/backups; not source commits |

Keep structured non-secret inputs local/private and bootstrap credentials in
protected injection or [Ansible-only encryption](../administration/secret-handling/ansible-vault.md).
Use an accepted secret service for normal scoped delivery; retain independent
bootstrap/recovery custody under the [secret strategy](../administration/secret-handling/strategy.md).

## Step 3: Refresh from the kit without replacing project work

This action is needed when adopting a kit update. Otherwise continue at **Step 4**.

From the **upstream kit root**, after updating its source, preview the same collection:

Run from **upstream kit root**.

```bash
read -r -p 'Original project prefix: ' PROJECT_PREFIX
read -r -p 'Parent directory containing the existing collection (absolute path): ' PROJECT_PARENT
python3 scripts/tier-repos/generate.py --prefix "$PROJECT_PREFIX" --root "$PROJECT_PARENT" --refresh --dry-run
```

Use the existing collection's parent, not the collection directory itself. Review the preview's
destination and changes, preserve private changes/backups, then apply that same refresh:

Run from **upstream kit root**.

```bash
python3 scripts/tier-repos/generate.py --prefix "$PROJECT_PREFIX" --root "$PROJECT_PARENT" --refresh
```

Follow the [refresh contract](generated-repositories.md#refresh-and-local-ownership): kit automation updates,
with a backup before local code edits are replaced. Site inputs and project-owned records stay protected.
Keep project extensions in new playbooks, roles or module paths. For edits inside existing kit code,
use `--code-conflicts ask` to choose interactively or `--code-conflicts preserve` during development.
Missing current generation targets are restored; obsolete files under `docs/auto-docs/` are removed.
Refresh does not merge live YAML/HCL/dotenv, move state or deploy infrastructure.
Review replacements, backups and preserved differences before any affected deployment.

<a id="before-you-push"></a>
<a id="pre-push-checks"></a>
<a id="step-5-review-before-publishing"></a>

## Step 4: Review before publishing

Run from **the owning generated repository root**.

```bash
git status --short --ignored
git diff --cached --check
git diff --cached --stat
```

Inspect staged content locally, run the [secret scan](secret-scanning.md) and [focused checks](testing.md).
Before the first remote push, scan the complete local history too; staged checks alone omit earlier commits.
Exclude live secrets/state/host plans and approve the intended disclosure before continuing.

<a id="example-private-mirror-in-gitlab"></a>
<a id="step-4-attach-private-source-control-later"></a>

## Step 5: Attach private source control and push

After hosted source control and **Step 4** are accepted, create an empty **private** remote per repo.
From each generated repo with reviewed local commits and no `origin` yet:

Run from **the owning generated repository root**:

```bash
read -r -p 'Private repository SSH or HTTPS URL without embedded credentials: ' PRIVATE_REMOTE_URL
git remote add origin "$PRIVATE_REMOTE_URL"
git remote -v
```

Verify that `origin` points to the intended private project. If a remote already exists, inspect it
instead of reinitializing or replacing it blindly. Then push from **that same repository**:

```bash
git push -u origin main
```

Use the actual reviewed branch if different. GitLab is the reference; other private source control is valid.
[CI handover](../deployment/stage-9-development/procedures/handover.md) transfers original state/ignored inputs
separately; it never recreates the infrastructure. Infrastructure runners require the explicit Tier 0
trust contract, not general build access.
