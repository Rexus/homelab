# Proxmox API setup

## Table of contents

- [Purpose](#purpose)
- [Before you start](#before-you-start)
- [What this repo needs](#what-this-repo-needs)
- [Endpoint values](#endpoint-values)
- [Create Terraform provisioning access](#create-terraform-provisioning-access)
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

The default goal is a dedicated Terraform token that can clone templates,
create VMs or containers, attach disks, apply cloud-init, place guests on the
right networks, and clean up disposable test deployments.

Do not use `root@pam` or a personal administrator token for normal repo runs.

## Before you start

Have this ready:

- Proxmox cluster access as an administrator
- the Proxmox node names the automation will target
- the datastore IDs Terraform may use, such as `local-lvm`
- the bridge or SDN paths Terraform may use
- the VM ID range you intend to reserve for repo-managed systems
- a place to store the token according to the
  [secret strategy](../../security/secret-strategy.md)

## What this repo needs

Use separate access paths for different automation jobs:

| Job | Needs Proxmox API token | Notes |
| --- | --- | --- |
| Terraform provisioning | yes | Creates, clones, updates, starts, stops, and destroys VMs or containers |
| Ansible guest configuration | no, normally | Uses SSH to the provisioned guests after Terraform has created them |
| Packer template builds | yes, separate token recommended | Creates temporary build VMs and converts them into templates |

The default Terraform role below is intentionally focused on guest
provisioning. It does not grant Proxmox user management, permission management,
node power, storage administration, cluster configuration, backup job
management, or host network modification.

## Endpoint values

Use different endpoint formats depending on the tool:

| Tool | Variable | Format |
| --- | --- | --- |
| Terraform `bpg/proxmox` provider | `PROXMOX_API_URL` | `https://pve.example.com:8006/` |
| Packer Proxmox plugin | `PROXMOX_URL` | `https://pve.example.com:8006/api2/json` |

For Terraform in this repo, do not append `/api2/json`. The deployment wrapper
maps `PROXMOX_API_URL`, `PROXMOX_API_TOKEN_ID`, and
`PROXMOX_API_TOKEN_SECRET` into the Terraform provider variables.[3][4]

## Create Terraform provisioning access

The command-line flow is the least ambiguous path. Run it from a Proxmox node
as an administrator.

If you prefer the web UI, use the same objects:

1. go to `Datacenter` → `Permissions` → `Users` and create `terraform@pve`
2. go to `Datacenter` → `Permissions` → `Roles` and create the custom roles
3. go to `Datacenter` → `Permissions` → `API Tokens` and create the token
   with privilege separation enabled
4. go to `Datacenter` → `Permissions` and add matching permissions for both
   the user and the token on `/vms`, each datastore, and each node

### 1. Create the automation user

```bash
pveum user add terraform@pve --comment "Terraform provisioning from automation host"
```

This user exists to own tokens. Do not use its password for automation.

### 2. Create focused roles

Create one VM role and one storage role so the path assignments stay easy to
reason about.

```bash
terraform_vm_privs="VM.Allocate VM.Audit VM.Clone VM.Config.CDROM"
terraform_vm_privs="$terraform_vm_privs VM.Config.CPU VM.Config.Cloudinit"
terraform_vm_privs="$terraform_vm_privs VM.Config.Disk VM.Config.HWType"
terraform_vm_privs="$terraform_vm_privs VM.Config.Memory VM.Config.Network"
terraform_vm_privs="$terraform_vm_privs VM.Config.Options VM.PowerMgmt"
pveum role add HomelabTerraformVM --privs "$terraform_vm_privs"
```

```bash
pveum role add HomelabTerraformStorage --privs "Datastore.Audit Datastore.AllocateSpace"
```

Add this only when your Proxmox version or SDN setup requires explicit bridge
or VLAN use permissions:

```bash
pveum role add HomelabTerraformNetwork --privs "SDN.Use"
```

Keep `Datastore.Allocate`, `Datastore.AllocateTemplate`, `Permissions.Modify`,
`Sys.Modify`, `Sys.PowerMgmt`, `Pool.Allocate`, and `Realm.Allocate*` out of
the Terraform provisioning role unless a specific workflow proves it needs
one of them.

### 3. Create a separated API token

```bash
pveum user token add terraform@pve provision --privsep 1 \
  --comment "Terraform provisioning token"
```

Copy the token secret immediately. Proxmox only shows the secret once.[1]

With privilege separation enabled, assign permissions to both the user and the
token. The token can only use permissions that are also allowed to the backing
user.[1]

### 4. Grant VM permissions

This repo currently creates new VM IDs from Terraform, so grant VM permissions
on `/vms` unless you have changed the Terraform model to create guests inside a
specific Proxmox pool.

```bash
pveum acl modify /vms --users terraform@pve --roles HomelabTerraformVM
pveum acl modify /vms --tokens 'terraform@pve!provision' --roles HomelabTerraformVM
```

If you later add pool placement to the Terraform module, prefer granting the
same role on `/pool/<poolid>` for that environment instead of all `/vms`.

### 5. Grant storage permissions

Repeat this for every datastore Terraform can place VM disks or cloud-init
media on.

```bash
pveum acl modify /storage/local-lvm --users terraform@pve --roles HomelabTerraformStorage
pveum acl modify /storage/local-lvm --tokens 'terraform@pve!provision' --roles HomelabTerraformStorage
```

If you use a separate datastore for cloud-init snippets or initialization
media, grant the same storage role there too.

### 6. Grant node read access

Repeat this for every Proxmox node Terraform may target.

```bash
pveum acl modify /nodes/pve01 --users terraform@pve --roles PVEAuditor
pveum acl modify /nodes/pve01 --tokens 'terraform@pve!provision' --roles PVEAuditor
```

### 7. Grant SDN or bridge use when required

If Terraform fails with a missing `SDN.Use` permission, grant the network role
on the path Proxmox reports in the error message or in the API viewer.

```bash
pveum acl modify /sdn/zones/localnetwork/vmbr0 --users terraform@pve --roles HomelabTerraformNetwork
pveum acl modify /sdn/zones/localnetwork/vmbr0 --tokens 'terraform@pve!provision' --roles HomelabTerraformNetwork
```

Use the most specific path your environment supports, especially when VLANs are
delegated to different teams or environments.

## Use the token

Store the token in your ignored `.env.local` file or provide the same values
through your runner.

```dotenv
PROXMOX_API_URL=https://pve.example.com:8006/
PROXMOX_API_TOKEN_ID=terraform@pve!provision
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

Use these checks on the Proxmox node when troubleshooting:

```bash
pveum user list
pveum role list
pveum acl list
```

Expected validation result:

| Check | Expected result |
| --- | --- |
| token authentication | Terraform can read cluster, node, storage, and template data |
| VM clone | Terraform can clone the selected template |
| disk allocation | Terraform can create disks only on the datastores you granted |
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
| read-only view | `PVEAuditor` on `/pool/team-app-test` | inspect assigned VMs without changing them |
| operator access | custom operator role on `/pool/team-app-test` | open console and start, stop, or reboot assigned VMs |
| normal VM user | `PVEVMUser` on `/pool/team-app-test` | use console, power controls, backup, and limited VM user actions |
| VM maintainer | `PVEVMAdmin` on `/pool/team-app-test` plus one datastore | administer assigned VMs without full platform administration |
| platform operator | `PVEAdmin` on selected platform paths | manage most platform tasks without granting full `Administrator` |

Custom operator role example:

```bash
pveum role add HomelabTeamOperator --privs "VM.Audit VM.Console VM.PowerMgmt"
pveum acl modify /pool/team-app-test --groups team-app --roles HomelabTeamOperator
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
| `terraform@pve!provision` | normal repo Terraform runs | VM, node read, datastore space, optional SDN use |
| `packer@pve!template` | image and template builds | template upload or conversion, ISO/template datastore access |
| `monitoring@pve!metrics` | monitoring and inventory | read-only roles such as `PVEAuditor` |
| `breakglass@pam` | emergency administration | interactive use only, not stored in repo automation |

For Packer, keep the role separate from Terraform because template builds often
need `Datastore.AllocateTemplate` and temporary build-VM lifecycle permissions.

## References

1. [Proxmox VE User Management](https://pve.proxmox.com/pve-docs/chapter-pveum.html)
2. [Proxmox VE API](https://pve.proxmox.com/mediawiki/index.php?title=Proxmox_VE_API)
3. [Terraform Provider for Proxmox VE](https://bpg.sh/docs/)
4. [HashiCorp Packer Proxmox ISO builder](https://developer.hashicorp.com/packer/plugins/builders/proxmox/iso)
