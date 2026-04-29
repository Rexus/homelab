# Proxmox API setup

## Table of contents

- [Purpose](#purpose)
- [Before you start](#before-you-start)
- [What this repo needs](#what-this-repo-needs)
- [Endpoint values](#endpoint-values)
- [Create Platform Automation Access](#create-platform-automation-access)
- [Use the token](#use-the-token)
- [Validate access](#validate-access)
- [Role patterns for teams](#role-patterns-for-teams)
- [When to split automation identities](#when-to-split-automation-identities)
- [References](#references)

## Purpose

Use this guide to create the Proxmox API access needed by the deployment
machine that runs this repository. Proxmox uses path-based permissions where
roles are assigned to users, groups, or tokens on paths such as `/vms`,
`/storage/<id>`, `/nodes/<node>`, and `/pool/<poolid>`.[1]

The default goal is a dedicated platform automation identity that can clone
templates, create guests, attach disks, apply cloud-init, place guests on the
right networks, and clean up disposable test deployments.

Do not use `root@pam` or a personal administrator token for normal repo runs.

## Before you start

Have this ready:

- Proxmox cluster access as an administrator
- the Proxmox node names the automation will target
- the datastore IDs automation may use, such as `local-lvm`
- the bridge, VLAN, or SDN paths automation may use
- the VM ID range you intend to reserve for repo-managed systems
- a place to store the token according to the
  [secret strategy](../../security/secret-strategy.md)

## What this repo needs

Use separate access paths for different automation jobs:

| Job | Needs Proxmox API token | Notes |
| --- | --- | --- |
| Platform provisioning | yes | Creates, clones, updates, starts, stops, and destroys VMs or containers |
| Ansible guest configuration | no, normally | Uses SSH to the provisioned guests after they exist |
| Packer template builds | yes, separate token recommended | Creates temporary build VMs and templates |

The default role set below is intentionally focused on guest provisioning. It
does not grant Proxmox user management, permission management, node power,
storage administration, cluster configuration, backup job management, or host
network modification.

## Endpoint values

Use different endpoint formats depending on the tool:

| Tool | Variable | Format |
| --- | --- | --- |
| Terraform `bpg/proxmox` provider | `PROXMOX_API_URL` | `https://pve.example.com:8006/` |
| Packer Proxmox plugin | `PROXMOX_URL` | `https://pve.example.com:8006/api2/json` |

For Terraform in this repo, do not append `/api2/json`. The deployment wrapper
maps `PROXMOX_API_URL`, `PROXMOX_API_TOKEN_ID`, and
`PROXMOX_API_TOKEN_SECRET` into the Terraform provider variables.[3][4]

## Create Platform Automation Access

This guide follows the shell path because it is repeatable and easy to audit.
Run the commands from any Proxmox host in the cluster as an administrator.

If you prefer the web UI, every step maps to `Datacenter` > `Permissions`.
The guide calls out the matching view after each command group.

The default pattern is:

1. create focused roles for VM, storage, node, and network access
2. create one platform automation group
3. assign the roles to the group on the required Proxmox paths
4. create a dedicated automation user and add it to the group
5. create the API token for that user

### 1. Create focused roles

Create one role per permission area so later reviews are easy.

```bash
platform_vm_privs="VM.Allocate VM.Audit VM.Clone VM.Config.CDROM"
platform_vm_privs="$platform_vm_privs VM.Config.CPU VM.Config.Cloudinit"
platform_vm_privs="$platform_vm_privs VM.Config.Disk VM.Config.HWType"
platform_vm_privs="$platform_vm_privs VM.Config.Memory VM.Config.Network"
platform_vm_privs="$platform_vm_privs VM.Config.Options VM.GuestAgent.Audit"
platform_vm_privs="$platform_vm_privs VM.GuestAgent.Unrestricted VM.PowerMgmt"
pveum role add PlatformAutomationVM --privs "$platform_vm_privs"
```

```bash
pveum role add PlatformAutomationStorage --privs "Datastore.Audit Datastore.AllocateSpace"
pveum role add PlatformAutomationNode --privs "Sys.Audit"
pveum role add PlatformAutomationNetwork --privs "SDN.Use"
```

GUI: create these under `Datacenter` > `Permissions` > `Roles`.

Keep `Datastore.Allocate`, `Datastore.AllocateTemplate`, `Permissions.Modify`,
`Sys.Modify`, `Sys.PowerMgmt`, `Pool.Allocate`, and `Realm.Allocate*` out of
the normal platform provisioning role unless a specific workflow proves it needs
one of them.

### 2. Create the automation group

```bash
pveum group add platform-automation --comment "Platform automation"
```

GUI: create this under `Datacenter` > `Permissions` > `Groups`.

Assign permissions to this group, not directly to the user. That keeps future
permission changes in one place.

### 3. Grant VM permissions to the group

This repo currently creates new VM IDs from automation, so grant VM permissions on
`/vms` unless you have changed the Terraform model to create guests inside a
specific Proxmox pool.

```bash
pveum acl modify /vms --groups platform-automation --roles PlatformAutomationVM
```

GUI: add a `Group Permission` under `Datacenter` > `Permissions` with path
`/vms`, group `platform-automation`, and role `PlatformAutomationVM`.

If you later add pool placement to the Terraform module, prefer granting the
same role on `/pool/<poolid>` for that environment instead of all `/vms`.
Keep in mind that cloning still needs access to the source template.

### 4. Grant storage permissions to the group

Repeat this for every datastore automation can place VM disks or cloud-init
media on.

```bash
pveum acl modify /storage/local-lvm \
  --groups platform-automation \
  --roles PlatformAutomationStorage
```

GUI: add a `Group Permission` with path `/storage/local-lvm`, group
`platform-automation`, and role `PlatformAutomationStorage`.

If you use a separate datastore for cloud-init snippets or initialization
media, grant the same storage role there too.

### 5. Grant Proxmox node read access to the group

Repeat this for every Proxmox node automation may target.

```bash
pveum acl modify /nodes/pve01 --groups platform-automation --roles PlatformAutomationNode
```

GUI: add a `Group Permission` with path `/nodes/pve01`, group
`platform-automation`, and role `PlatformAutomationNode`.

This is intentionally read-only node access. It lets automation inspect the
target host without granting node power, host configuration, or cluster admin
privileges.

### 6. Grant bridge, VLAN, or SDN use to the group

If your Proxmox version enforces network permissions for guest NICs, grant
`SDN.Use` on the narrowest path that matches the networks this repo may attach
to guests. Proxmox SDN uses zones, VNets, and subnets to model virtual
networking, and local Linux bridges are exposed through the `localnetwork`
zone.[2]

Use one of these patterns:

| Scope | Permission path example |
| --- | --- |
| one local bridge | `/sdn/zones/localnetwork/vmbr0` |
| one VLAN tag on one local bridge | `/sdn/zones/localnetwork/vmbr0/20` |
| one SDN VNet | `/sdn/zones/<zone>/<vnet>` |
| one VLAN tag on one SDN VNet | `/sdn/zones/<zone>/<vnet>/<tag>` |

Example for bridge `vmbr0`:

```bash
pveum acl modify /sdn/zones/localnetwork/vmbr0 \
  --groups platform-automation \
  --roles PlatformAutomationNetwork
```

Example for only VLAN `20` on bridge `vmbr0`:

```bash
pveum acl modify /sdn/zones/localnetwork/vmbr0/20 \
  --groups platform-automation \
  --roles PlatformAutomationNetwork
```

GUI: add a `Group Permission` under `Datacenter` > `Permissions`. Use the SDN
or local bridge path that matches the network you want automation to use.

If Proxmox returns a missing `SDN.Use` error, use the path shown in the error
or in the API viewer as the source of truth for your cluster.

### 7. Create the automation user and assign the group

```bash
pveum user add automation@pve --comment "Platform automation from deployment machine"
pveum user modify automation@pve --groups platform-automation
```

GUI: create this under `Datacenter` > `Permissions` > `Users`, then assign it
to the `platform-automation` group.

This user exists to own tokens. Do not use its password for automation.

### 8. Create the API token

For the group-managed path, create a token that inherits the dedicated user's
group permissions.

```bash
pveum user token add automation@pve provision \
  --privsep 0 \
  --comment "Platform provisioning token"
```

GUI: create this under `Datacenter` > `Permissions` > `API Tokens`.

Copy the token secret immediately. Proxmox only shows the secret once.[1]

Keep this user dedicated to automation. If you add this user to more groups,
the non-privilege-separated token inherits those new permissions too.

If you require a privilege-separated token, create it with `--privsep 1` and
assign matching ACLs directly to `automation@pve!provision`. That gives you a
narrower token boundary, but it also means you must maintain token ACLs in
addition to the group ACLs.

## Use the token

Store the token in your ignored `.env.local` file or provide the same values
through your runner.

```dotenv
PROXMOX_API_URL=https://pve.example.com:8006/
PROXMOX_API_TOKEN_ID=automation@pve!provision
PROXMOX_API_TOKEN_SECRET=replace-with-the-token-secret
```

For this repository, keep the token ID and token secret separate. The
deployment wrapper combines them for the Terraform provider.

## Validate access

Before the first real apply, run a plan from the deployment machine:

```bash
bash scripts/deploy.sh foundation --plan-only
```

If the token is too narrow, Proxmox usually returns a `403` with the missing
path and privilege. Add only the missing privilege on the narrowest useful
path, then rerun the plan.

Use these checks on a Proxmox node when troubleshooting:

```bash
pveum user list
pveum group list
pveum role list
pveum acl list
```

Expected validation result:

| Check | Expected result |
| --- | --- |
| token authentication | Terraform can read cluster, node, storage, and template data |
| VM clone | Terraform can clone the selected template |
| guest agent read | Terraform can wait for guest network information when the QEMU guest agent is enabled |
| disk allocation | Terraform can create disks only on the datastores you granted |
| network placement | Terraform can attach guests only to allowed bridges, VNets, or VLAN tags |
| cleanup | `--destroy` removes the disposable test guests |
| denied access | the token cannot modify Proxmox users, roles, cluster settings, or unrelated storage |

## Role patterns for teams

Use groups and pools for human access. Proxmox recommends assigning
permissions to groups rather than individual users, and pools are intended for
permission handling across a set of VMs, containers, and storage.[1]

Example small-team setup:

```bash
pveum group add team-app
pveum pool add team-app-test --comment "Application team test systems"
```

Use these patterns as starting points:

| Setup | Permission assignment | What the team can do |
| --- | --- | --- |
| read-only view | `PVEAuditor` on `/pool/team-app-test` | inspect assigned VMs |
| operator access | custom operator role on `/pool/team-app-test` | console plus power controls |
| normal VM user | `PVEVMUser` on `/pool/team-app-test` | common VM user actions |
| VM maintainer | `PVEVMAdmin` on the pool plus one datastore | administer assigned VMs |
| platform operator | `PVEAdmin` on selected platform paths | most platform tasks, not full admin |

Custom operator role example:

```bash
pveum role add TeamVmOperator --privs "VM.Audit VM.Console VM.PowerMgmt"
pveum acl modify /pool/team-app-test --groups team-app --roles TeamVmOperator
```

Keep placement and ownership simple:

- put team VMs into a pool as soon as they are created
- grant team roles to groups, not individual users
- give teams storage access only when they need to create or resize disks
- use `NoAccess` on narrower paths when you need to block inherited access
- avoid giving teams datastore-wide or `/` permissions unless they operate the
  platform

## When to split automation identities

Use separate users and tokens when the job scope changes:

| Identity | Use it for | Extra privileges it may need |
| --- | --- | --- |
| `automation@pve!provision` | normal repo platform provisioning | VM, node read, datastore space, optional SDN use |
| `packer@pve!template` | image and template builds | template upload or conversion, ISO/template datastore access |
| `monitoring@pve!metrics` | monitoring and inventory | read-only roles such as `PVEAuditor` |
| `breakglass@pam` | emergency administration | interactive use only, not stored in repo automation |

For Packer, keep the role separate from normal platform provisioning because
template builds often need `Datastore.AllocateTemplate` and temporary build-VM
lifecycle permissions.

## References

1. [Proxmox VE User Management](https://pve.proxmox.com/pve-docs/chapter-pveum.html)
2. [Proxmox VE Software-Defined Network](https://pve.proxmox.com/pve-docs/chapter-pvesdn.html)
3. [Terraform Provider for Proxmox VE](https://bpg.sh/docs/)
4. [HashiCorp Packer Proxmox ISO builder](https://developer.hashicorp.com/packer/plugins/builders/proxmox/iso)
