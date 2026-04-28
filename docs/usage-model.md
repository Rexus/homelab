# Safe repository usage

## Table of contents

- [Purpose](#purpose)
- [Recommended usage models](#recommended-usage-models)
- [Publishing rules](#publishing-rules)
- [File naming conventions](#file-naming-conventions)
- [Bootstrap secret strategy](#bootstrap-secret-strategy)
- [Example: private mirror in GitLab](#example-private-mirror-in-gitlab)
- [Before you push](#before-you-push)

## Purpose

This repository is meant to be shared safely. Treat it as a reusable baseline,
not as the required home of your live configuration. This public repository is a
curated upstream reference and is not intended to receive operational changes.

## Recommended usage models

### Option 1: Private fork

Use a private fork when you want your own history while keeping a clean path to
pull updates from the curated upstream baseline. Continue development in the
fork, not in this public upstream.

### Option 2: Private mirror

Use a private mirror when you want a separate operational copy in private source
control while keeping this repository as the public upstream reference.

Suggested model:

- public upstream repository for examples and reusable automation
- private mirror for environment-specific non-secret configuration
- external secret storage or runner variables for secrets

### Option 3: Local-only copy

Use a local clone or downloaded archive when you do not need a remote at all.
This is simple and safe for one-user or offline setups.

## Publishing rules

Commit only:

- documentation
- example files ending in `.example`
- safe defaults
- reusable code and modules

Do not commit:

- passwords
- private keys
- tokens
- live secret files
- live local overlays
- environment-specific files unless they are intentionally non-secret and stored
  only in a private operational copy

## File naming conventions

Use these conventions consistently:

- `*.example` = safe to publish
- `*.local` = local-only and ignored
- `secrets/` = untracked secret material
- live files should either be ignored or kept in a private operational copy

Examples:

- `packer/variables.auto.pkrvars.hcl.example` committed
- `packer/variables.auto.pkrvars.hcl` ignored
- `ansible/inventory/hosts.yml.example` committed
- `ansible/inventory/hosts.yml` ignored
- `ansible/group_vars/all.yml.example` committed
- `ansible/group_vars/all.yml` ignored
- `ansible/group_vars/all.env.yml.example` committed
- `ansible/group_vars/all.lab1.yml` ignored

## Bootstrap secret strategy

Use a simple model first, then move to Vault quickly.

Recommended order:

1. external secret manager such as Vault when available
2. protected runner variables or local environment variables for bootstrap
3. ignored local files for structured non-secret configuration
4. committed example files for defaults and templates only

Practical guidance:

- use ignored files for network plans, host group structure, names, and similar
  non-secret values
- use environment variables for API tokens, provider authentication, and other
  sensitive runtime values
- avoid storing long-lived secrets in plain-text local files when environment
  variables or secret systems are available
- reduce direct secret handling as soon as Vault is introduced

## Example: private mirror in GitLab

One workable pattern is:

- keep this repository as the public upstream baseline
- mirror or copy it into a private GitLab project
- use self-hosted runners for infrastructure access
- use masked and protected CI variables for secrets
- keep private environment overlays in the private project, not upstream here

GitLab is only one example. The same pattern applies to other private source
control systems and runner platforms.

## Before you push

Check these questions every time:

1. Is this file an example, default, or reusable automation?
2. Does it contain a token, password, private key, real IP plan, or live host list?
3. Should this live only in a private fork, mirror, local copy, or in runner
   variables instead?
4. Did `.gitignore` already cover the live version of this file?
5. Would you be comfortable with this exact content being public forever?
