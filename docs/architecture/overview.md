# Architecture overview

## Table of contents

- [Intent](#intent)
- [Model](#model)
- [Automation flow](#automation-flow)
- [Boundaries](#boundaries)

## Intent

This repository is a private-cloud baseline built around clear trust
boundaries, layered networking, and a strict split between image creation,
resource provisioning, and configuration management.

The design is meant to stay stable as the environment grows. The number of
segments, hosts, and services can change without changing the core model.

## Goals:

- clear separation of edge, application, and infrastructure concerns
- no implicit trust between zones
- controlled remote user and administrator access
- reusable structure for IaC and multi-cloud thinking
- clear placement of identity, secrets, and hardware-backed systems

## Layered Overview

```text
PRIVATE CLOUD

┌─────────────────────────────────────────────────────────────┐
│ EDGE LAYER                                                  │
│   External Zone        Internet, WAN, Partner Networks      │
│   DMZ Zone             Ingress, VPN, ZTNA, Egress           │
├─────────────────────────────────────────────────────────────┤
│ APPLICATION LAYER                                           │
│   Shared Services      DNS, AD, Identity, Vault, Logging    │
│   User Services        Internal Apps, APIs, Portals         │
├─────────────────────────────────────────────────────────────┤
│ INFRASTRUCTURE LAYER                                        │
│   Management Zone      Bastion, IaC, Ops, Hypervisor Mgmt   │
│   Restricted HW Zone   HSM, Storage, Backup, HW Roots       │
└─────────────────────────────────────────────────────────────┘

## Model

The architecture uses a small set of durable zones:

- management for operators, runners, and platform APIs
- edge for published entry points such as VPN and ingress
- workload segments for applications, clusters, and projects
- shared services for common platform capabilities such as DNS and identity
- storage and backup for images, snapshots, and recovery data
- restricted services for secrets, PKI, and other high-trust systems

```text
Lower trust
  Internet, WAN, remote users
           |
           v
+-----------------------+
| Edge / published      |
+-----------+-----------+
            |
            v
+-----------+-----------+
| Workload segments     |
+---+-----------+---+---+
    |           |   |
    |           |   +--> Restricted services
    |           +------> Storage and backup
    +------------------> Shared services

Management plane
  operators, runners, APIs
  separate control path into managed zones
```

This is a pattern model, not a public-cloud feature match. Proxmox is the
current foundation layer, but the architecture is broader than a single
platform.

## Automation flow

Each tool has one primary job:

- Packer builds reusable images when custom templates are needed
- Terraform provisions VMs, containers, and platform resources
- Ansible applies baseline system configuration after provisioning

```text
Secret source -> Packer -> Terraform -> Ansible
```

## Boundaries

Current repository scope:

- platform-facing automation
- reusable templates and images
- VM and container provisioning
- baseline guest and host configuration

Outside current scope:

- router, firewall, and switch underlay configuration
- end-to-end network fabric automation

Operating assumptions:

- management paths stay separate from workloads
- edge services do not get implicit access to management or restricted systems
- workload access to secrets and other high-trust services is explicit
- network segmentation must already exist before full platform automation
