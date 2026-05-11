# Podman image runner guide

## Table of contents

- [Purpose](#purpose)
- [What this deploys](#what-this-deploys)
- [Prerequisites](#prerequisites)
- [Terraform configuration](#terraform-configuration)
- [Ansible configuration](#ansible-configuration)
- [GitLab runner setup](#gitlab-runner-setup)
- [Bootc image project](#bootc-image-project)
- [GitLab CI example](#gitlab-ci-example)
- [Promotion path](#promotion-path)
- [Read more](#read-more)
- [References](#references)

## Purpose

Use this guide when GitLab exists and you want a dedicated internal runner that
can build bootc images for your server templates and hosts.

This is the first image-based Linux implementation path. It does not require
Kubernetes, Harbor, or Dragonfly. The runner builds with Podman and pushes the
image to the GitLab built-in registry. When the shared registry path exists,
the same pipeline can promote or copy images into Harbor.

## What this deploys

This path has dedicated IaC:

| Layer | File | Responsibility |
| --- | --- |
| Terraform | `terraform/environments/podman-runner/terraform.tfvars` | deploys runner VM(s) |
| Ansible inventory | `ansible/inventory/hosts.yml` | keeps the stable `podman_runner` host group |
| Ansible vars | `ansible/group_vars/podman_runner.yml` | controls packages, runner tags, and optional registration |
| Ansible role | `ansible/roles/podman_runner/` | installs Podman, Buildah, Skopeo, Git, and GitLab Runner |
| GitLab | runner registration token and project settings | runs the bootc image pipeline |
| GitLab registry | project or group registry | stores the first internal bootc images |

Default to one runner VM. Add more runners when build time, project isolation,
or trust boundaries require it.

## Prerequisites

Before starting, have:

| Requirement | Notes |
| --- | --- |
| GitLab | from the [development platform path](development.md) |
| GitLab registry | enabled on the GitLab instance or project |
| Linux template | normal cloud-init template from the Proxmox template guide |
| runner network access | runner can reach GitLab, GitLab registry, and upstream image registries |
| package path | runner can install `gitlab-runner` through configured repos or cache |
| registry credentials | Red Hat credentials only when building from RHEL bootc images |

GitLab recommends installing runners on a server separate from the GitLab
server, and runner registration links that runner to the GitLab instance.[1]

## Terraform configuration

The runner is deployed like any other application-platform VM.

Edit:

| File | What you change |
| --- | --- |
| `terraform/environments/podman-runner/terraform.tfvars` | runner count, size, storage, network zone, and tags |
| `ansible/inventory/hosts.yml` | `podman_runner` hosts when you add or remove runners |
| `ansible/group_vars/podman_runner.yml` | `platform_host_ips` for each runner |
| `ansible/group_vars/podman_runner.<env>.yml` | environment-specific runner IPs when `--env` is used |

Default Terraform shape:

| Setting | Default example | Notes |
| --- | --- | --- |
| inventory key | `runner-1` | keep the numeric suffix even for one runner |
| VM name | generated from environment naming | for example `runner-test-1` or `runner-1` |
| role tag | `runner` | generic role |
| service tag | `gitlab-runner`, `podman` | exact implementation tags |
| network zone | application or automation network | runner must reach GitLab and registries |
| size | small or medium | increase disk when builds cache many layers |
| template | normal Linux template | bootc is built by the runner, not required on the runner OS |

Plan a test environment first:

```bash
bash scripts/deploy.sh podman-runner --env test --plan-only
```

Deploy after you have reviewed the plan:

```bash
bash scripts/deploy.sh podman-runner --env test
```

Keep reusable runner VM shape in Terraform. Keep GitLab tokens, registry
credentials, and package choices in Ansible or ignored local vars.

## Ansible configuration

Ansible configures the VM into a Podman-capable build runner.

Edit:

| File | What you change |
| --- | --- |
| `ansible/group_vars/podman_runner.yml` | GitLab URL, registration mode, runner tags, and package behavior |
| `ansible/group_vars/podman_runner.<env>.yml` | environment-specific runner settings when `--env` is used |
| encrypted extra vars or Vault | real runner authentication tokens and registry credentials |

The role handles:

| Task | Purpose |
| --- | --- |
| install packages | `podman`, `buildah`, `skopeo`, `git`, `gitlab-runner` |
| trust private CA | allow runner to reach GitLab and registry over private TLS |
| configure runner user | keep builds isolated from normal admin users |
| register GitLab runner | use a project or group runner authentication token |
| set runner tags | use tags such as `bootc` and `podman` |
| protect secrets | keep registry credentials in GitLab CI/CD variables or Vault |

Use the Shell executor first. It keeps the build simple because Podman runs
directly on the runner VM. GitLab documents that the Shell executor runs jobs
locally on the runner machine.[2]

Set `podman_runner_register: true` only after you have a project or group
runner authentication token. Store the real token in an encrypted vars file,
runner secret, or external secret system.

## GitLab runner setup

The Ansible role installs the build tools on the runner VM:

```bash
sudo dnf install -y podman buildah skopeo git
```

Install GitLab Runner from the official GitLab package flow for the runner
host OS.[3] Register the runner with a project or group runner authentication
token:

```bash
sudo gitlab-runner register \
  --url "https://git.corp.example.com" \
  --token "$RUNNER_AUTHENTICATION_TOKEN" \
  --executor "shell" \
  --description "podman-runner-1" \
  --tag-list "bootc,podman" \
  --run-untagged="false" \
  --locked="true"
```

Use a project runner when only one bootc image project should use it. Use a
group runner when several internal server image projects should share it.

## Bootc image project

Create a GitLab project that owns the server OS image definition.

Recommended repository shape:

```text
Containerfile
.gitlab-ci.yml
etc/
  systemd/
    system/
```

Start with one image project per OS family or server baseline. Keep normal
application code out of the base server image unless the host is intentionally
an appliance.

Minimal Fedora/CentOS-style `Containerfile`:

```Dockerfile
FROM quay.io/fedora/fedora-bootc:42

RUN dnf -y install cloud-init qemu-guest-agent && dnf clean all
RUN systemctl enable qemu-guest-agent.service
RUN bootc container lint
```

Minimal RHEL `Containerfile`:

```Dockerfile
FROM registry.redhat.io/rhel10/rhel-bootc:10.0

RUN dnf -y install cloud-init qemu-guest-agent && dnf clean all
RUN systemctl enable qemu-guest-agent.service
RUN bootc container lint
```

Red Hat's image mode workflow uses `Containerfile`, standard container tools,
and bootc images as operating system artifacts.[4][5]

## GitLab CI example

GitLab provides predefined variables for its registry, including
`CI_REGISTRY`, `CI_REGISTRY_IMAGE`, `CI_REGISTRY_USER`, and
`CI_REGISTRY_PASSWORD`.[6]

If the image is based on RHEL, add protected and masked GitLab CI/CD variables:

| Variable | Purpose |
| --- | --- |
| `RH_REGISTRY_USER` | username for `registry.redhat.io` |
| `RH_REGISTRY_PASSWORD` | password or token for `registry.redhat.io` |

Example `.gitlab-ci.yml`:

```yaml
stages:
  - build

variables:
  BOOTC_IMAGE: "$CI_REGISTRY_IMAGE/server-base"

build_bootc_image:
  stage: build
  tags:
    - bootc
  script:
    - set -euxo pipefail
    - |
      printf '%s' "$CI_REGISTRY_PASSWORD" |
        podman login "$CI_REGISTRY" -u "$CI_REGISTRY_USER" --password-stdin
    - |
      if [ -n "${RH_REGISTRY_USER:-}" ]; then
        printf '%s' "$RH_REGISTRY_PASSWORD" |
          podman login registry.redhat.io -u "$RH_REGISTRY_USER" --password-stdin
      fi
    - podman build --pull=always -t "$BOOTC_IMAGE:$CI_COMMIT_SHORT_SHA" .
    - podman push "$BOOTC_IMAGE:$CI_COMMIT_SHORT_SHA"
    - |
      if [ "$CI_COMMIT_BRANCH" = "$CI_DEFAULT_BRANCH" ]; then
        podman tag "$BOOTC_IMAGE:$CI_COMMIT_SHORT_SHA" "$BOOTC_IMAGE:stable"
        podman push "$BOOTC_IMAGE:stable"
      fi
```

Use the short SHA tag for traceability. Use the `stable` tag only from a
protected branch or protected tag after the image has passed review.

RHEL bootc images are subject to Red Hat subscription and redistribution rules,
so do not publish derived RHEL OS images to a public registry.[7]

## Promotion path

Start with this flow:

```text
GitLab project -> Podman runner -> GitLab registry -> bootc template or host
```

Later, when Harbor exists:

```text
GitLab project -> Podman runner -> GitLab registry -> Harbor -> bootc hosts
```

Use GitLab's registry as the early artifact location. Move to Harbor when the
registry becomes a shared platform service with project boundaries, scanning,
retention, and Kubernetes pull scaling.

## Read more

- [Development platform path](development.md)
- [Container registry path](registry.md)
- [Image-based Linux path](image-based-linux.md)
- [Enterprise Linux template](../../platforms/proxmox/enterprise-linux-template.md)

## References

1. [GitLab runner registration](https://docs.gitlab.com/runner/register/)
2. [GitLab Shell executor](https://docs.gitlab.com/runner/executors/shell/)
3. [Install GitLab Runner from Linux repositories](https://docs.gitlab.com/runner/install/linux-repository/)
4. [Red Hat image mode pipeline with GitLab](https://developers.redhat.com/articles/2026/02/12/how-build-image-mode-pipeline-gitlab)
5. [Red Hat image mode for RHEL](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/using_image_mode_for_rhel_to_build_deploy_and_manage_operating_systems/introducing-image-mode-for-rhel)
6. [GitLab predefined CI/CD variables](https://docs.gitlab.com/ci/variables/predefined_variables/)
7. [RHEL bootc base image](https://catalog.redhat.com/en/software/containers/rhel9/rhel-bootc/)
