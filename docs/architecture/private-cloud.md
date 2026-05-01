# Private cloud model

## Table of contents

- [Purpose](#purpose)
- [What cloud means here](#what-cloud-means-here)
- [Where this repository fits](#where-this-repository-fits)
- [Shared services first](#shared-services-first)
- [When Proxmox is the right layer](#when-proxmox-is-the-right-layer)
- [When Kubernetes changes the scale](#when-kubernetes-changes-the-scale)
- [When OpenStack becomes the better fit](#when-openstack-becomes-the-better-fit)
- [Practical decision table](#practical-decision-table)
- [References](#references)

## Purpose

Use this document to understand what this repository means by private cloud and
why the current reference path starts with Proxmox instead of OpenStack.

This is a scope guide, not a deployment guide.

## What cloud means here

Cloud is more than virtualization. A cloud model adds pooled resources, broad
network access, repeatable provisioning, and reduced manual interaction for the
people consuming the platform.[1]

A private cloud means those cloud capabilities are operated for one
organization. It can be hosted on-premises, in a small datacenter, or by a
provider, but the important part is that the environment serves a private
organization boundary rather than the public internet as a shared utility.[1]

## Where this repository fits

This repository is a private-cloud baseline for a small platform team,
homelab-scale datacenter, or security-focused small business environment.

It aims for private-cloud operating patterns:

- infrastructure is described as code
- VM names, networks, identities, and secrets are repeatable
- platform setup starts from a known foundation
- services are separated by trust boundary and lifecycle
- disposable test environments are encouraged before production

It does not try to be a full self-service cloud portal on day one. The current
model assumes a small number of trusted platform administrators who own the
Proxmox cluster and control what is deployed.

## Shared services first

The first private-cloud capability is not a VM count. It is a shared trust
base that other paths can consume.

For this repository, that means:

- identity, DNS, and PKI for a private domain
- Vault or an existing secret platform for shared secrets
- syslog and observability for operational control
- HSM hardening paths for selected cryptographic keys

These services can be deployed by the repo or supplied by an existing
environment. Read [Shared services model](shared-services.md) for the reusable
service boundary and key-custody model.

## When Proxmox is the right layer

Use Proxmox when you need a strong virtualization foundation with low
operational overhead.

It is a good fit when:

- one platform owner or a small trusted team administers the cluster
- the environment needs VMs, containers, storage, backup, and clustering
  without a large cloud-control-plane project
- tenants are mostly projects, services, or teams represented through IaC
  reviews rather than self-service infrastructure administration
- you want the smallest reliable base for identity, PKI, Vault, edge services,
  and later Kubernetes

Proxmox is a virtualization management platform that integrates KVM, LXC,
software-defined storage, networking, clustering, and a web UI.[2]

That makes it a good small-platform foundation, but it is not the same thing as
a full multi-tenant IaaS cloud control plane.

## When Kubernetes changes the scale

Kubernetes is the next scale layer when most of the growth is application
workload growth rather than VM growth.

Use a smaller Proxmox foundation plus Kubernetes when:

- the platform team still owns the infrastructure
- application teams need repeatable deployment paths
- workloads are mostly containerized
- teams can consume namespaces, GitOps, policies, and platform services instead
  of creating their own VMs

Kubernetes manages containerized workloads and services with declarative
configuration and automation.[3] It can support multi-team patterns, but
Kubernetes itself notes that shared clusters require careful design around
security, fairness, noisy neighbors, RBAC, quotas, and network policy.[4]

For many smaller organizations, Proxmox plus Kubernetes gives enough cloud-like
behavior without taking on the operational cost of OpenStack.

## When OpenStack becomes the better fit

OpenStack becomes the stronger private-cloud fit when the environment needs a
real IaaS control plane for many tenants.

Move toward OpenStack when:

- multiple teams need to act as their own infrastructure administrators
- users need self-service VM, network, image, volume, quota, and project
  workflows
- tenant boundaries must be represented in the platform API itself
- delegated administration and project quotas are core requirements
- the operational cost of a larger control plane is justified by the number of
  internal consumers

OpenStack describes itself as a cloud operating system that controls large
pools of compute, storage, and networking resources and lets users provision
resources through a dashboard.[5] Its identity layer, Keystone, provides
multi-tenant authorization, and OpenStack projects are the ownership unit for
cloud resources.[6][7]

This is the point where Proxmox starts to look like a platform substrate, while
OpenStack is the user-facing private cloud.

## Practical decision table

| Need | Better fit | Why |
| --- | --- | --- |
| one trusted admin or small platform team | Proxmox | simpler operations and strong VM/container foundation |
| a few internal teams consuming reviewed IaC | Proxmox plus Ansible/Terraform | teams get repeatability without direct cluster admin rights |
| many app teams deploying containers | Proxmox plus Kubernetes | Proxmox hosts the base, Kubernetes becomes the app platform |
| teams need namespace-level app autonomy | Kubernetes | app teams can work through GitOps, namespaces, RBAC, and policy |
| teams need VM/network/storage self-service | OpenStack | tenant/project model is part of the cloud control plane |
| users must be their own infrastructure admins | OpenStack | delegated cloud administration is a first-class design goal |

For this repository, the default path is:

1. Proxmox as the reference virtualization foundation.
2. Terraform and Ansible for repeatable platform provisioning.
3. Identity, PKI, Vault, backup, and security foundations.
4. Kubernetes later for application-platform scale.
5. OpenStack only if the organization outgrows small-platform administration
   and needs true multi-tenant IaaS self-service.

## References

1. [NIST SP 800-145, The NIST Definition of Cloud Computing](https://csrc.nist.gov/pubs/sp/800/145/final)
2. [Proxmox VE overview](https://www.proxmox.com/en/proxmox-ve)
3. [Kubernetes concepts](https://kubernetes.io/docs/concepts/)
4. [Kubernetes multi-tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
5. [OpenStack documentation](https://docs.openstack.org/)
6. [Keystone, the OpenStack Identity Service](https://files.openstack.org/docs/keystone/latest/index.html)
7. [OpenStack Keystone projects, users, and roles](https://static.openstack.org/docs/keystone/2024.1/admin/cli-manage-projects-users-and-roles.html)
