# Application platform path

## Purpose

Use this path for capabilities that host, build, and run applications on top of
the shared private-cloud foundation.

This is where development services, source control, CI/CD, registries,
image-based Linux builds, Kubernetes, GitOps, and future application runtime
patterns belong.

## Current guides

- [Development platform path](development.md)
- [Podman image runner guide](podman-runner.md)
- [Container registry path](registry.md)
- [Image-based Linux path](image-based-linux.md)
- [Kubernetes platform path](kubernetes.md)

## Path boundaries

| Path | Owns | Usually depends on |
| --- | --- | --- |
| development | GitLab on a dedicated Podman VM, repositories, and CI/CD coordination | shared identity, PKI, Vault |
| Podman image runner | runner VM for bootc and container image builds | development path |
| registry | Harbor and shared OCI artifacts | development path for automated builds |
| image-based Linux | `immutable-template` setup and bootc template lifecycle | Podman image runner, then shared registry later |
| Kubernetes | application runtime and GitOps direction | shared services, registry, and development paths |

## How this path grows

Start with GitLab on one VM, then add runners, registry, image-based hosts,
and cluster guides as those setups are introduced. They should consume shared
identity, PKI, Vault, cache, edge, and system-control services when those are
available instead of redeploying their own foundations.
