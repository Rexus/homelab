# Secret scanning

Use native Gitleaks checks for staged changes, repository history and explicitly selected
artifact directories. Ignore rules prevent accidental additions, not tracked/forced secret leaks.
Detection is defense in depth, not a proof that arbitrary passwords or private data are absent. [1]

## Local checks

Install an approved Gitleaks CLI from verified release artifacts. Run from the owning tier repository:

```bash
bash ../homelab-shared/scripts/check-secrets.sh staged
```

Substitute the generated prefix. `history` scans all locally available Git history;
`artifacts /absolute/path` scans the selected directory without uploading results.
The helper fails if the tool is missing and always redacts findings from output.

Use an existing hook manager without replacing another hook. For a native `pre-commit`
installation, add the official pinned `gitleaks-system` hook to the project's configuration:

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks-system
        args: [--ignore-gitleaks-allow]
```

Run `pre-commit install` from each actual repository. Hooks remain bypassable; they are not
server enforcement. In the upstream kit, run the shared helper as `bash shared/scripts/check-secrets.sh staged`.

## CI enforcement

The [Shared GitLab job](../../shared/ci/gitlab-secrets.yml.example) scans a full-history checkout
with a pinned tool image. Adopt it in each generated repository's developer-owned pipeline;
pin any cross-project include to a reviewed commit. A normal unprivileged runner executes this
job; scanning must not require the infrastructure runner or Vault/Proxmox credentials.
The job uses the `tier1-build` tag and disables inherited job defaults and YAML variables,
including infrastructure `before_script`, JWT configuration and artifact rules.
This does not revoke project/group CI variables or the normal job token. Keep infrastructure
credentials in the bounded Vault path, not globally injected CI variables.
Allow its exact scanner image in `development_platform_runner_additional_allowed_images`
and reapply the runner recipe; the default runner otherwise admits only its main build image.
For example, the supplied job needs `ghcr.io/gitleaks/gitleaks:v8.30.1`. Qualify and pin a
digest in both the job and allowed-image input when promoting the local configuration.

Require the job to pass before merge, protect its includes/configuration and test the server-side
rules with a disposable synthetic secret. A shallow clone proves only the available history.
Scan intended artifacts before publication and keep plans/state/raw scan reports out of CI artifacts.
CI masking does not protect arbitrary script output: retain `no_log`, disable shell tracing for
secret-bearing operations, scope credentials and review job scripts.

If a real credential is committed, rotate/revoke it first, assess exposure and then follow a
reviewed history-cleanup procedure. Deleting the current file does not revoke the credential.

## References

1. [Gitleaks native commands and hooks](https://github.com/gitleaks/gitleaks/tree/v8.30.1).
