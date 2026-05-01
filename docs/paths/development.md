# Development platform path

## Table of contents

- [Purpose](#purpose)
- [Target direction](#target-direction)
- [Shared services](#shared-services)
- [Starting shape](#starting-shape)
- [Growth shape](#growth-shape)
- [Environment model](#environment-model)
- [Read more](#read-more)

## Purpose

Use this path when the private cloud needs a place for source control,
automation, registries, CI/CD, and internal software projects.

This is a path guide, not a deployment guide yet. It gives the future GitLab
and GitOps work a clear home without making the shared services path carry
development-platform details.

## Target direction

The reference direction is:

| Stage | Shape | Why |
| --- | --- | --- |
| first development platform | one dedicated GitLab VM | simple to operate and easy to back up |
| stronger development platform | GitLab plus dedicated runners and registry storage | separates build work from the source-control host |
| application-platform phase | Kubernetes-hosted GitLab components or GitOps tooling | supports scaling, policies, and workload separation |

Keep the product choice separate from the role. The role is `development
platform`; GitLab is the current reference implementation.

## Shared services

The development path should consume shared services when they exist:

| Shared service | How the development path uses it |
| --- | --- |
| identity | user login, groups, project ownership, runner access |
| PKI | internal TLS for Git, registry, and web UI endpoints |
| Vault | CI/CD secrets, deploy tokens, runner credentials |
| observability | logs, metrics, audit events, runner health |
| backup | repository, registry, database, and configuration recovery |

Do not deploy a new identity system just for the development platform unless
the project is intentionally isolated.

## Starting shape

Start with one dedicated VM when the environment is small:

| Role | Example name | Notes |
| --- | --- | --- |
| development platform | `dev-1` or `git-1` | GitLab reference host |
| runner host | `runner-1` | separate when builds should not run on the GitLab host |
| registry storage | shared storage, NAS, or object target | choose based on backup and retention needs |

The VM should use the shared private domain, trusted certificate path, Vault
handoff, and observability intake when those services are available.

## Growth shape

Move toward Kubernetes when the main scaling problem becomes application and
automation workload growth.

Use Kubernetes for:

- GitOps controllers
- isolated worker clusters
- horizontally scaled runners
- application namespaces and policy boundaries
- deployment automation for internal projects

Keep Proxmox as the VM and cluster boundary. Use Kubernetes as the application
platform on top, not as a replacement for the shared private-domain services.

## Environment model

The development path should follow the same environment model as the rest of
the repository:

- use `--env test`, `--env dev`, or another environment name for disposable or
  parallel copies
- omit `--env` for production
- keep shared settings in the base files
- override subnet, VLAN, IP, storage, or VM size only when that environment
  needs a different shape

## Read more

- [Shared services model](../architecture/shared-services.md)
- [Private cloud model](../architecture/private-cloud.md)
- [Private cloud maturity path](private-cloud-maturity.md)
- [Infrastructure automation layout](../reference/infrastructure-automation-layout.md)
