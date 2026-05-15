# USB HSM Active-Active Deployment Guide

## Table of contents

- [Purpose](#purpose)
- [Prerequisite](#prerequisite)
- [Default deployment](#default-deployment)
- [What you configure](#what-you-configure)
- [IaC used for this](#iac-used-for-this)
- [How to shape the deployment](#how-to-shape-the-deployment)
- [How to maintain it](#how-to-maintain-it)
- [References](#references)

## Purpose

Use this guide when you want to deploy the USB HSM pattern from this repo.

It stays focused on:

- what you need to configure
- what the Terraform and Ansible layers deploy
- what you still do manually around the HSM devices
- what to maintain after the first rollout

The current reference implementation is `Pico HSM`. You can keep the same
topology with `SoftHSM` when you want a software-only rehearsal path, or adapt
it to other USB-backed PKCS#11 devices such as `YubiHSM 2` [1][2][3][4][5].

## Prerequisite

Before you start:

- the shared-service edge load-balancer set is already deployed in
  `external_edge`
- the deployment machine already has `ansible-core` and `terraform`
- the edge load-balancer hosts already exist in `ansible/inventory/hosts.yml`
- this guide only reruns edge load-balancer Ansible to add or refresh HSM
  gateway backends

If not, start with
[Identity foundation path](../paths/shared-services/identity.md).

## Default deployment

The default shape in this repo is:

- `2` deployed edge load-balancer VMs, or a larger load-balancer set, from the
  `foundation` setup
- `2` gateway hosts in the `cryptography` zone
- `1` local USB HSM or software token per gateway host
- `0-1` helper or recovery VM in `ceremony`
- `1` offline backup device or equivalent recovery artifact

```mermaid
flowchart TD
  Client[Clients or internal callers]

  subgraph ExternalEdge["external_edge"]
    LB[Edge load-balancer pair]
  end

  subgraph HostA["Host B"]
    GW1[Gateway service B]
    H1[USB HSM 2]
    GW1 -->|USB connection| H1
  end

  subgraph HostB["Host A"]
    GW2[Gateway service A]
    H2[USB HSM 1]
    GW2 -->|USB connection| H2
  end

  Backup[Offline backup USB HSM]

  Client --> LB
  LB -->|HTTPS or mTLS| GW1
  LB -->|HTTPS or mTLS| GW2

  style ExternalEdge fill:#ecfdf5,stroke:#15803d,stroke-width:2px,color:#1f2937
  style HostA fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1f2937
  style HostB fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1f2937

  classDef edgeNode fill:#dcfce7,stroke:#15803d,color:#1f2937
  classDef gatewayNode fill:#93c5fd,stroke:#1d4ed8,color:#1f2937
  classDef hsmNode fill:#bbf7d0,stroke:#15803d,color:#1f2937

  class Client,LB edgeNode
  class GW1,GW2 gatewayNode
  class H1,H2,Backup hsmNode
```

Figure: the default path is the deployed shared-service edge load-balancer in
front of two gateway hosts, one local USB HSM per host, and one offline backup
device.

Keep these boundaries:

- one gateway service talks only to one local token
- the deployed edge load balancer stays in the shared-service layer and is a
  prerequisite here
- active devices are independent replicas, not a native HSM cluster
- USB or PKCS#11 access stays host-local

## What you configure

Before you deploy, fill in these inputs.

### Network zones

Use the shared zone keys from
[Network architecture](../architecture/network.md).

You mainly add these zones here:

| Zone key | Use in this guide |
| --- | --- |
| `cryptography` | active gateway hosts and optional issuing CA placement |
| `ceremony` | optional helper, recovery VM, or root-CA path when you want a separate ceremony network |

These existing zones are only references here:

| Zone key | Why it still matters here |
| --- | --- |
| `external_edge` | already deployed edge load balancer or load-balancer set reaches the cryptography hosts |
| `management` | admin access, automation, and metrics reach the HSM hosts |
| `application` | shared internal callers may reach the cryptography hosts if you expose them internally |
| `identity` | identity or PKI dependencies may still need controlled reachability to issuing services on the cryptography network |

Copy these examples to your local Terraform variable files and edit the shared
network mappings in `terraform/common.tfvars`:

- [`terraform/common.tfvars.example`](../../terraform/common.tfvars.example)
  for the default platform node, shared storage, deployable guest networks,
  template IDs, and SSH keys
- [`terraform/environments/hsm/terraform.tfvars.example`](../../terraform/environments/hsm/terraform.tfvars.example)
  for the gateway and helper layer

Set the values your environment needs for `cryptography` and optional
`ceremony`, such as bridge, VLAN, subnet, gateway, and addressing conventions.
Reuse the existing `external_edge`, `management`, `identity`, and
`application` mappings from your prerequisite deployments.

### Firewall openings

Use these default openings unless you have intentionally changed the service
ports:

| Source zone | Destination zone | Default port or protocol | Purpose |
| --- | --- | --- | --- |
| `external_edge` | `cryptography` | `8443/TCP` | deployed edge load balancer to gateway service |
| `management` | `cryptography` | `22/TCP` | SSH, Ansible, and troubleshooting |
| `management` | `ceremony` | `22/TCP` | helper or recovery host administration |
| `application` | `cryptography` | `8443/TCP` optional | internal callers using the same gateway service endpoint |
| `ceremony` | `cryptography` | none by default | open only when a helper host needs a direct admin path |

Keep these boundaries:

- the default gateway backend port in this repo is `8443/TCP` through
  `hsm_proxy_ingress_backend_port` in `ansible/inventory/hosts.yml`, with the
  same default in `roles/hsm_proxy_ingress`
- the default Ansible SSH port in this repo is `22/TCP`
- if you change the gateway service port from `8443`, update both the firewall
  rule and `hsm_proxy_ingress_backend_port`
- do not open extra metrics or observability ports unless you explicitly
  configure and need them
- do not expose raw USB devices or generic PKCS#11 endpoints over the network
- keep USB or token access host-local on each gateway
- if you do not deploy a helper host, keep `ceremony` to `cryptography` closed

### VM layout

Edit the `vm_instances` maps to match the shape you want.

| Component | Terraform default | Inventory action | Current example range | Edit here |
| --- | --- | --- | --- | --- |
| gateway VMs | `hsm-1`, `hsm-2` active | `hsm-1`, `hsm-2` present by default | `1-8` | `terraform/environments/hsm/terraform.tfvars` |
| helper VMs | `crypto-admin-1` commented, default `0` | uncomment `crypto-admin-1` when enabled | `0-2+` as needed | `terraform/environments/hsm/terraform.tfvars` |

The deployed edge load balancer stays in the shared-service layer. Start here with
the gateway and helper hosts.

The shared Ansible inventory includes `hsm-1` and `hsm-2` for the default HSM
shape. If you add or remove HSM hosts, update both the HSM Terraform
`vm_instances` map and the Ansible IP map.

### HSM mode

Choose one of these before rollout:

| Mode | What changes |
| --- | --- |
| `Pico HSM` | hardware attach, device initialization, backup or restore ceremony [2][3] |
| `SoftHSM` | no USB device, software token per host [1] |
| `YubiHSM 2` | same host pattern, but connector or product-specific runtime details may differ [4][5] |

Keep the host layout the same across all three modes.

## IaC used for this

Use these repo paths here:

| IaC path | Used for here | You edit |
| --- | --- | --- |
| [`terraform/common.tfvars.example`](../../terraform/common.tfvars.example) | shared Terraform inputs used across environments, including the default platform node | your local `terraform/common.tfvars` |
| [`terraform/environments/hsm/terraform.tfvars.example`](../../terraform/environments/hsm/terraform.tfvars.example) | deploys the gateway VMs and optional helper VMs | `terraform/environments/hsm/terraform.tfvars` based on `.example` |
| [`ansible/inventory/hosts.yml.example`](../../ansible/inventory/hosts.yml.example) | stable HSM host keys and inventory groups | your local `ansible/inventory/hosts.yml` |
| [`ansible/group_vars/all.yml.example`](../../ansible/group_vars/all.yml.example) | shared Ansible defaults and the default environment | your local `ansible/group_vars/all.yml` |
| [`ansible/group_vars/all.env.yml.example`](../../ansible/group_vars/all.env.yml.example) | environment-specific hostname decoration and domain | your local `ansible/group_vars/all.<env>.yml` |
| [`ansible/group_vars/hsm.yml.example`](../../ansible/group_vars/hsm.yml.example) | HSM and edge host IPs needed by the HSM rollout | your local `ansible/group_vars/hsm.yml` |
| [`ansible/playbooks/hsm.yml`](../../ansible/playbooks/hsm.yml) | reruns baseline OS preparation on the HSM hosts | inventory and host variables |
| [`ansible/playbooks/ingress.yml`](../../ansible/playbooks/ingress.yml) | reruns edge load-balancer configuration so the deployed edge layer points at the HSM gateways | inventory and edge load-balancer variables |
| [`scripts/deploy.sh`](../../scripts/deploy.sh) | repository wrapper for the mapped precheck, Terraform, and Ansible flow | choose the `hsm` setup when you are ready to run it |

You do not use foundation Terraform as part of this HSM rollout. It only
assumes that the deployed edge load-balancer prerequisite already exists.

Use the shared ownership rule from
[Infrastructure automation layout](../reference/infrastructure-automation-layout.md):
Ansible inventory owns stable logical host keys and service groups. Ansible
`all` group vars own hostname decoration and domain. HSM group vars own the
HSM rollout IP map, while the HSM Terraform environment owns hardware
placement and Proxmox tags.

## How to shape the deployment

Shape the HSM deployment around one stable service pattern and then change the size by
data only.

- keep the edge load balancer in the shared-service layer and treat it as a
  prerequisite here
- keep the default `2` gateway hosts unless you have measured reasons to change
  the count
- grow or shrink gateway and helper counts only through `vm_instances`
- keep active gateways in `cryptography`
- enable `ceremony` only when you really want a helper, recovery, or root-CA
  adjacency path
- keep the inventory aligned with host intent:
  `edge_load_balancers`, `hsm_gateways`, and optional `crypto_admin`
- keep one local token or software token per gateway host
- keep the live traffic path and the ceremony path separate even when they use
  the same HSM product family

When you are ready to run the setup, use the repository deployment wrapper with
the `hsm` setup. Keep the exact execution flow in the wrapper rather than
repeating it in this guide. That wrapper also checks the required local config
files for the setup before it runs.

After the wrapper run:

- attach the intended USB HSM device to each gateway host, or initialize one
  software token per host if you are using `SoftHSM` [1]
- validate host-local PKCS#11 access on every gateway host before sending any
  traffic through the edge load balancer
- initialize one device as the source of truth, create the intended keys, and
  replicate only the approved wrapped objects to the other active device and
  the offline backup [2][3][4][5]
- test gateway health, device loss, host loss, and restore from the offline
  backup before you treat the setup as production-ready

Useful local checks:

```bash
opensc-tool -l
pkcs11-tool --list-slots
pkcs11-tool --list-objects --pin <PIN>
openssl x509 -in cert.pem -text -noout
```

## How to maintain it

Keep maintenance simple and repeatable.

### Health checks

Treat a gateway as healthy only when:

- the service is reachable
- login and session setup work against the expected local token
- a harmless crypto operation succeeds with the expected key label or ID

Do not rely on slot visibility or object listing alone.

### Device identity

Keep one gateway bound to one expected local token:

- do not rely on transient slot numbering alone
- pin by stable reader, token label, serial, or similar identity when possible
- start gateway services only after the expected local token is present
- fail closed when the expected token is missing or mismatched

### Replica updates

When you change key material:

1. change it on the source-of-truth device
2. export under the approved wrap or backup process
3. restore to the other active device
4. refresh the offline backup device
5. verify labels, IDs, and expected objects before returning traffic

Do not treat the offline backup device as a routine active peer.

### Routine checks

Keep at least these checks in your normal maintenance cycle:

- verify gateway health from the edge load-balancer path
- verify local PKCS#11 access on each gateway host
- compare expected object inventory across active devices
- test restore from the offline backup on a controlled schedule
- review whether your current `vm_instances` layout still matches the load

## References

1. [SoftHSM](https://www.softhsm.org/) (accessed 2026-04-19)
2. [PicoKeys Documentation: Supported features](https://docs.picokeys.com/picohsm/features/) (accessed 2026-04-19)
3. [PicoKeys Documentation: Backup and restore](https://docs.picokeys.com/picohsm/backup-restore/) (accessed 2026-04-19)
4. [Yubico: YubiHSM PKCS#11 Module](https://developers.yubico.com/yubihsm-shell/yubihsm-pkcs11.html) (accessed 2026-04-20)
5. [Yubico: yubihsm-connector](https://developers.yubico.com/yubihsm-connector/) (accessed 2026-04-20)
