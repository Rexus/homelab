# Development platform path

## Table of contents

- [Purpose](#purpose)
- [Before you start](#before-you-start)
- [What this deploys](#what-this-deploys)
- [IaC used for this](#iac-used-for-this)
- [Configure the deployment](#configure-the-deployment)
- [Ports and DNS](#ports-and-dns)
- [Operations](#operations)
- [High availability direction](#high-availability-direction)
- [Read more](#read-more)
- [References](#references)

## Purpose

Use this path when the private cloud needs source control, CI/CD coordination,
and a starting point for internal software projects.

The reference implementation is GitLab on one dedicated Podman VM. This keeps
the first deployment simple and movable. Dedicated runners, Harbor, bootc image
builds, and Kubernetes build on top of this path later.

## Before you start

Have these in place first:

| Requirement | Why it matters |
| --- | --- |
| Identity foundation | GitLab should use the shared private-domain DNS name and later consume central identity. |
| PKI certificate | The default deployment expects HTTPS with a certificate from the shared PKI. |
| Linux template | Terraform clones the normal Linux cloud-init template. |
| Backup target | Repository and database data live on the VM and must be backed up before the platform matters. |

## What this deploys

Default deployment:

| Role | Default host | Default count | Notes |
| --- | --- | --- | --- |
| development platform | `git-1` | `1` | Podman host running the GitLab container |

Default VM shape:

| Setting | Default |
| --- | --- |
| size | `xl` |
| disk | `200 GB` |
| storage class | `shared` |
| network zone | `application` |

This path does not deploy runners by default. Use the
[Podman image runner guide](podman-runner.md) when build jobs should run away
from the GitLab host.

## IaC used for this

| Layer | File |
| --- | --- |
| Terraform setup | `terraform/environments/development/terraform.tfvars` |
| Ansible inventory | `ansible/inventory/hosts.yml` |
| Ansible environment vars | `ansible/group_vars/all.yml` or `all.<env>.yml` |
| Ansible setup vars | `ansible/group_vars/development.yml` |
| Ansible role | `ansible/roles/gitlab_container/` |

## Configure the deployment

Edit `terraform/environments/development/terraform.tfvars`:

| Value | What to choose |
| --- | --- |
| `vm_instances.git-1.size` | keep `xl` unless this is a small test deployment |
| `vm_instances.git-1.disk_size_gb` | increase before storing important repositories |
| `vm_instances.git-1.storage_class` | use storage that matches your backup and restore plan |
| `vm_instances.git-1.network_zone_key` | normally `application` |

Edit `ansible/group_vars/development.yml`:

| Value | What to choose |
| --- | --- |
| `gitlab_container_image` | pin a GitLab image tag before production use |
| `gitlab_hostname` | the DNS name GitLab should present to users |
| `gitlab_external_url` | the final HTTPS URL for GitLab |
| `gitlab_tls_cert_src` | certificate file from the shared PKI |
| `gitlab_tls_key_src` | private key file from the shared PKI |
| `gitlab_ssh_host_port` | host port used for Git over SSH, default `2222` |

Deploy a test environment first:

```bash
bash scripts/deploy.sh development --env test --plan-only
bash scripts/deploy.sh development --env test
```

Run production by omitting `--env`:

```bash
bash scripts/deploy.sh development
```

## Ports and DNS

Publish these ports to users or to the edge proxy, depending on your network
design:

| Port | Purpose |
| --- | --- |
| `80/tcp` | HTTP redirect and GitLab internal web handling |
| `443/tcp` | HTTPS web UI and Git over HTTPS |
| `2222/tcp` | Git over SSH, mapped to container port `22` |

Use the DNS name from `gitlab_external_url`. Do not use `localhost` as the
GitLab hostname.

## Operations

Persistent data is mounted under `gitlab_home`, default `/srv/gitlab`:

| Host path | Container path | Purpose |
| --- | --- | --- |
| `/srv/gitlab/config` | `/etc/gitlab` | GitLab configuration and TLS files |
| `/srv/gitlab/logs` | `/var/log/gitlab` | GitLab logs |
| `/srv/gitlab/data` | `/var/opt/gitlab` | repositories, database, uploads, and runtime data |

Maintenance notes:

- Back up `/srv/gitlab` before upgrades.
- Pin the GitLab image tag before production use.
- Keep runners on separate hosts when build workloads become noisy.
- Route logs and metrics into the system-control path when observability exists.

For the first login, retrieve the initial root password from the container:

```bash
sudo podman exec -it gitlab grep 'Password:' /etc/gitlab/initial_root_password
```

Store the new admin credential in the chosen secret-management path after
login. The initial password file is temporary.

## High availability direction

The first deployment is a single GitLab VM. Treat it as simple, early, and easy
to back up.

The HA direction is Kubernetes. Move there when the platform needs stronger
separation, dedicated scaling, and Kubernetes-native operations. Use the
GitLab Helm chart or operator path there instead of running the Docker image as
a single container.

Do not scale this by starting several independent GitLab containers. The later
Kubernetes path needs shared stateful services and the GitLab cloud-native
deployment model.

## Read more

- [Application platform path](README.md)
- [Podman image runner guide](podman-runner.md)
- [Container registry path](registry.md)
- [Kubernetes platform path](kubernetes.md)
- [Shared services model](../../architecture/shared-services.md)
- [Infrastructure automation layout](../../reference/infrastructure-automation-layout.md)
- [Repository scripts](../../reference/repository-scripts.md)

## References

1. [GitLab Docker installation](https://docs.gitlab.com/install/docker/installation/)
2. [GitLab Docker configuration](https://docs.gitlab.com/ee/install/docker/configuration.html)
3. [GitLab SSL configuration](https://docs.gitlab.com/omnibus/settings/ssl/)
4. [GitLab Helm chart installation](https://docs.gitlab.com/charts/installation/)
