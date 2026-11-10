# Proxmox API setup

Create scoped API access for template publication and guest provisioning.
Complete this after installing verified CA trust on the [bootstrap host](../bootstrap/README.md).
This procedure does not deploy guests.

**Working repository:** `<prefix>-tier-0` for bootstrap inputs (source: `tier-0/`).
**Run Steps 1–3 on:** a Proxmox host as an authorized administrator.
**Run Step 4 on:** the bootstrap host, in the owning generated tier.
**Design:** [protected provisioning](../../../architecture/hosting/provisioning.md).

## Contents

- [Before starting](#prerequisites)
- [Create platform automation access](#create-platform-automation-access)
- [Validate access](#validate-access)
- [Use the token](#use-the-token)
- [Existing or privilege-separated tokens](#existing-or-privilege-separated-tokens)
- [Role patterns for teams](#role-patterns-for-teams)
- [References](#references)

<a id="purpose"></a>
<a id="before-you-start"></a>

## Prerequisites

Record these actual values before copying commands. Examples must match the selected
[names and allocations](../../../conventions/proxmox-conventions.md).

| Selection | Example | Used for |
| --- | --- | --- |
| Target node | `pve01` | Node-read ACL and initial guest placement |
| Live-disk datastore | `local-zfs` | VM and CloudInit disks |
| Import datastore | `local` | Tier 0 uploaded images, not live VM disks |
| Guest attachment | `vmbr0` plus VLAN, or `dmz/edge` VNet | Scoped network ACL |
| Automation identity | `automation@pve!provision` | Token ID without its secret |

<a id="what-this-repo-needs"></a>

Guest provisioning needs VM lifecycle, disk allocation, node-read and network access.
Template publication additionally needs image-upload permission on its Import datastore.
Ansible normally uses SSH to guests, not the Proxmox token. Do not use `root@pam` or
a personal administrator token for routine deployments. [1]

<a id="tls-gate"></a>

**TLS gate:** complete [bootstrap CA trust and caller verification](../../../administration/hosts/proxmox-tls.md)
on the execution host before using the token. Supplied provider roots set
`insecure = false`; entry points reject bypass flags. Existing projects must review
retained local provider edits too. Neither FreeIPA nor platform PKI is required first. [5]

## Create Platform Automation Access

### Step 1: Create the roles and group

**Run on a Proxmox host.** Create these once; reuse accepted existing roles/groups.
The matching GUI pages are **Datacenter > Permissions > Roles** and **Groups**.
Use the same authorized host shell through creation and permission checks so the selected
node/storage variables remain available; re-enter them if starting another session.

<a id="1-create-focused-roles"></a>

Run on **the selected Proxmox host as an authorized root operator**.

```bash
platform_vm_privs="VM.Allocate VM.Audit VM.Clone VM.Config.CDROM"
platform_vm_privs="$platform_vm_privs VM.Config.CPU VM.Config.Cloudinit"
platform_vm_privs="$platform_vm_privs VM.Config.Disk VM.Config.HWType"
platform_vm_privs="$platform_vm_privs VM.Config.Memory VM.Config.Network"
platform_vm_privs="$platform_vm_privs VM.Config.Options VM.GuestAgent.Audit"
platform_vm_privs="$platform_vm_privs VM.GuestAgent.Unrestricted VM.PowerMgmt"
pveum role add PlatformAutomationVM --privs "$platform_vm_privs"
pveum role add PlatformAutomationStorage --privs "Datastore.Audit Datastore.AllocateSpace"
pveum role add PlatformAutomationNode --privs "Sys.Audit"
pveum role add PlatformAutomationNetwork --privs "SDN.Use SDN.Audit"
```

<a id="2-create-the-automation-group"></a>

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum group add platform-automation --comment "Platform automation"
```

| Role | Permitted work |
| --- | --- |
| `PlatformAutomationVM` | Clone/create/configure/start/stop/remove authorized guests |
| `PlatformAutomationStorage` | Inspect storage and allocate guest disks |
| `PlatformAutomationNode` | Inspect authorized nodes; no host power/configuration |
| `PlatformAutomationNetwork` | Attach NICs (`SDN.Use`) and read subnet metadata (`SDN.Audit`); no network modification |

Keep host/cluster administration and permission management outside these roles.
Role names are case-sensitive. For an older network role containing only `SDN.Use`,
append the missing privilege instead of creating a second role:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum role modify PlatformAutomationNetwork --append 1 --privs "SDN.Audit"
```

This changes every ACL using that role; it preserves the existing privileges and scope.

### Step 2: Grant only the selected resource paths

<a id="3-grant-vm-permissions-to-the-group"></a>

**VMs:** the current Terraform model uses explicit VMIDs without pool placement:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum acl modify /vms --groups platform-automation --roles PlatformAutomationVM
```

If pool placement is deliberately added, use the reviewed pool boundary instead.
Cloning still needs access to the source template. [1]

<a id="4-grant-storage-permissions-to-the-group"></a>

**Live storage:** enter an actual datastore ID; repeat for every approved disk/CloudInit target:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
read -r -p "Live VM datastore ID (for example local-zfs): " VM_DATASTORE
pveum acl modify "/storage/$VM_DATASTORE" --groups platform-automation --roles PlatformAutomationStorage
```

**Tier 0 images:** also grant storage visibility/allocation on the Import datastore.
For the example `local` datastore:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum acl modify /storage/local --groups platform-automation --roles PlatformAutomationStorage
```

**Tier 0 upload permission:** create this role once and assign it only to publishing
automation on its actual Import datastore. Keep it out of ordinary consuming-tier access. [6][7]

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum role add PlatformTemplateUpload --privs "Datastore.AllocateTemplate"
pveum acl modify /storage/local --groups platform-automation --roles PlatformTemplateUpload
```

A separate publisher uses its own group/token grants. Importing existing files does
not upload them, but an adoption plan can include creation of missing files.

<a id="5-grant-proxmox-node-read-access-to-the-group"></a>

**Node:** repeat for each allowed destination and source-template node:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
read -r -p "Authorized Proxmox node name: " PVE_NODE
pveum acl modify "/nodes/$PVE_NODE" --groups platform-automation --roles PlatformAutomationNode
```

<a id="6-grant-bridge-vlan-or-sdn-use-to-the-group"></a>

**Network:** choose **2a or 2b** below for each selected attachment. Local bridge grants
do not authorize an SDN VNet. GUI equivalent: **Datacenter > Permissions > Add > Group Permission**. [1][2]

#### 2a: Direct bridge/VLAN attachment

Use the narrowest prepared path. This example allows VLAN 10 on `vmbr0`:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum acl modify /sdn/zones/localnetwork/vmbr0/10 --groups platform-automation --roles PlatformAutomationNetwork
```

For an intentional bridge-wide grant, use `/sdn/zones/localnetwork/vmbr0`.
Repeat for the actual selected VLANs, then continue at **Step 3**.

#### 2b: Existing SDN VNet

For VNet `edge` in zone `dmz`:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum acl modify /sdn/zones/dmz/edge --groups platform-automation --roles PlatformAutomationNetwork
```

Repeat for every selected VNet, including stopped templates' attachments. Complete
[SDN activation](step-1c-sdn.md#step-3-activate-sdn-on-the-nodes) before use,
then continue at **Step 3**. Subnet lookup uses the same scoped role's `SDN.Audit`.

### Step 3: Create the user and token

<a id="7-create-the-automation-user-and-assign-the-group"></a>

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum user add automation@pve --comment "Platform automation from deployment machine"
pveum user modify automation@pve --groups platform-automation
```

<a id="8-create-the-api-token"></a>

The established group-managed bootstrap example inherits this dedicated user's
permissions. Adding the user to other groups also expands this token's permissions. [1]

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum user token add automation@pve provision --privsep 0 --comment "Platform provisioning token"
```

**Save the secret immediately into protected custody; Proxmox displays it only once.**
Use separate credentials when job/tier scope differs. For a privilege-separated token,
use the [matching ACL procedure](#existing-or-privilege-separated-tokens) before validation.

## Validate access

**Still on the Proxmox host**, inspect the actual token ID and actual resource paths.
The commands contain no token secret:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum user permissions 'automation@pve!provision' --path /storage/local
pveum user permissions 'automation@pve!provision' --path "/storage/$VM_DATASTORE"
pveum user permissions 'automation@pve!provision' --path "/nodes/$PVE_NODE"
```

For the selected SDN example:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum user permissions 'automation@pve!provision' --path /sdn/zones/dmz/edge
```

For direct bridge/VLAN attachment, substitute its selected path instead.

| Check | Required effective privileges |
| --- | --- |
| Live disk and CloudInit storage | `Datastore.Audit`, `Datastore.AllocateSpace` |
| Tier 0 Import datastore | The two storage privileges above plus `Datastore.AllocateTemplate` for uploads |
| Target/source node | `Sys.Audit` |
| Selected attachment with subnet lookup | `SDN.Use` and `SDN.Audit` |
| Guest operations | The scoped VM role, including access to the clone source |

A plan can pass read checks without proving later upload/NIC-write permission.
Investigate a 403 at its exact path; do not broaden the grant to `/`.
After provisioning, test permitted and denied operations on disposable guests. [1]

## Use the token

### Step 4: Set inputs on the bootstrap host

Return to [Bootstrap Step 4](../bootstrap/README.md#step-4-configure-trust-credentials-and-platform-inputs)
to initialize **Tier 0** and edit its ignored **`.env.local`**.

For another consuming tier, create that tier's file if absent, from its repository root:

Run from the selected **`<prefix>-tier-0/`**, **`<prefix>-tier-1/`** or **`<prefix>-tier-2/`** repository.

```bash
cp -n env.local.example .env.local
chmod 600 .env.local
```

Edit these fields using that tier's authorized token:

```dotenv
PROXMOX_API_URL=https://pve01.example.internal:8006/
PROXMOX_API_TOKEN_ID=automation@pve!provision
PROXMOX_API_TOKEN_SECRET=replace-with-the-issued-secret
```

Each tier owns its own credentials; Shared and another tier's file do not supply them.
Also configure the [execution account's SSH public-key path](../bootstrap/README.md#step-3-prepare-the-execution-accounts-ssh-key)
before Linux clones are created.

<a id="endpoint-values"></a>

| Entry point | Credential loading |
| --- | --- |
| Linux `scripts/deploy.sh SETUP` | Loads `.env.local` by default; maps the three fields above into Terraform |
| Template publisher | Requires `--env-file .env.local`; no manual exports or concatenation |
| Kubernetes command, currently Talos | Uses exported native `PROXMOX_VE_ENDPOINT` and `PROXMOX_VE_API_TOKEN`; follow its [configuration step](../../stage-4-kubernetes/procedures/talos-terraform.md#configure) |
| Packer | Uses `PROXMOX_URL=https://pve01.example.internal:8006/api2/json` and its separate build inputs |

Terraform endpoints use the HTTPS root, **without `/api2/json`**. [3][4]
Return to [foundation template publication](../README.md#step-4-publish-and-test-vm-templates)
after the bootstrap host's remaining Shared profile and recovery checks.
Do not deploy the `foundation` Linux setup merely to validate this token.

## Existing or privilege-separated tokens

Separated tokens need both group/user and token grants. Their effective permissions
are the intersection; token ACLs cannot expand the owning user's rights. [1]
Retain the selected privilege-separation mode; changing a role does not change it.

For a separated token, mirror each selected VM, node, datastore and attachment grant
from Step 2 using `--tokens 'automation@pve!provision'` instead of `--groups`.
For example, the Tier 0 Import datastore and an allowed VNet:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum acl modify /storage/local --tokens 'automation@pve!provision' --roles PlatformAutomationStorage,PlatformTemplateUpload
pveum acl modify /sdn/zones/dmz/edge --tokens 'automation@pve!provision' --roles PlatformAutomationNetwork
```

Keep base storage read/allocation roles when adding upload rights. Repeat
[effective-permission validation](#validate-access) using the exact consuming token.
If `SDN.Use` appears without `SDN.Audit`, check the case-sensitive role ID and both ACL sides.

## Role patterns for teams

Use groups and pools for human access; do not reuse the provisioning token.
The selected pool must already contain the team's guests. [1]

| Role on `/pool/<team-pool>` | Intended access |
| --- | --- |
| `PVEAuditor` | Inspect assigned systems |
| Custom console/power role | Operate existing guests |
| `PVEVMUser` | Common VM-user operations |
| `PVEVMAdmin` plus selected datastore rights | Maintain authorized guests |

<a id="when-to-split-automation-identities"></a>

Split identities for publishing/Packer, monitoring, routine provisioning and emergency
administration. Packer upload/build rights stay separate; monitoring is read-only.
Break-glass access remains interactive and outside routine automation.

## References

1. [Proxmox user management and API-token permissions](https://raw.githubusercontent.com/proxmox/pve-docs/master/pveum.adoc).
2. [Proxmox software-defined networking](https://raw.githubusercontent.com/proxmox/pve-docs/master/pvesdn.adoc).
3. [Terraform Provider for Proxmox VE](https://bpg.sh/docs/).
4. [HashiCorp Packer Proxmox ISO builder](https://developer.hashicorp.com/packer/plugins/builders/proxmox/iso).
5. [BPG provider TLS behavior](https://raw.githubusercontent.com/bpg/terraform-provider-proxmox/v0.112.0/docs/index.md).
6. [Proxmox storage-content API permissions](https://raw.githubusercontent.com/proxmox/pve-storage/master/src/PVE/API2/Storage/Content.pm).
7. [Proxmox image-upload API permissions](https://raw.githubusercontent.com/proxmox/pve-storage/master/src/PVE/API2/Storage/Status.pm).
