# Proxmox API setup

Create scoped API access for template publication and guest provisioning.
Complete this after installing verified CA trust on the [bootstrap host](../bootstrap/README.md).
This procedure does not deploy guests.

**Working repository:** `<prefix>-tier-0` for bootstrap inputs (source: `tier-0/`).
**Run Steps 1–10 on:** a Proxmox host as an authorized administrator.
**Continue at Step 11 on:** the bootstrap host, in the owning generated tier.
**Design:** [protected provisioning](../../../01-architecture/04-hosting/02-provisioning.md).

> [!TIP]
> **Recovery and maintenance:**
> [Review API roles and rotate access](../../../05-operations/01-hosting/proxmox-hardening.md#api-and-identity) or
> [repair API TLS trust](../../../05-operations/01-hosting/proxmox-tls.md).

## Contents

- [Before starting](#prerequisites)
- [1. Create roles](#step-1-create-the-roles)
- [2. Create the automation group](#step-2-create-the-automation-group)
- [3. Grant VM scope](#step-3-grant-vm-scope)
- [4. Grant live-storage scope](#step-4-grant-live-storage-scope)
- [5. Grant image-publishing scope](#step-5-grant-image-publishing-scope)
- [6. Grant node-read scope](#step-6-grant-node-read-scope)
- [7a/7b. Grant network scope](#step-7-grant-network-scope)
- [8. Create the user](#step-8-create-the-user)
- [9. Create the token](#step-9-create-the-token)
- [9a. Authorize selected USB mappings: optional](#usb-mapping-access)
- [10. Validate effective permissions](#step-10-validate-effective-permissions)
- [11. Continue with local inputs](#step-11-continue-with-local-inputs)
- [Existing or privilege-separated tokens](#existing-or-privilege-separated-tokens)
- [Optional HA automation identity](#ha-automation-identity)
- [Ceremony automation identities](#ceremony-automation-identity)
- [Role patterns for teams](#role-patterns-for-teams)
- [References](#references)

<a id="purpose"></a>
<a id="before-you-start"></a>

## Prerequisites

Record these actual values before copying commands. Examples must match the selected
[names and allocations](../../../02-conventions/proxmox-conventions.md).

| Selection | Example | Used for |
| --- | --- | --- |
| Target node | `pve01` | Node-read ACL and initial guest placement |
| Live-disk datastore | `local-zfs` | VM and CloudInit disks |
| Import datastore | `local` or `cephfs` with Import content | Tier 0 uploaded images, not live VM disks |
| Guest attachment | `vmbr0` plus VLAN, or `dmz/edge` VNet | Scoped network ACL |
| Automation identity | `automation@pve!provision` | Token ID without its secret |

<a id="what-this-repo-needs"></a>

Guest provisioning needs VM lifecycle, disk allocation, node-read and network access.
Template publication additionally needs image-upload permission on its Import datastore.
Ansible normally uses SSH to guests, not the Proxmox token. Do not use `root@pam` or
a personal administrator token for routine deployments. [1]

<a id="tls-gate"></a>

**TLS gate:** [Bootstrap Step 14](../bootstrap/README.md#step-14-trust-the-proxmox-api) already installed
and verified API trust on the execution host. Retain that accepted trust; do not repeat its installation. Supplied provider roots set
`insecure = false`; entry points reject bypass flags. Existing projects must review
retained local provider edits too. Neither FreeIPA nor platform PKI is required first. [5]

<a id="create-platform-automation-access"></a>
<a id="step-1-create-the-roles-and-group"></a>

## Step 1: Create the roles

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

For **Tier 0 template publishers**, also create this role once:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum role add PlatformTemplateUpload --privs "Datastore.AllocateTemplate"
```

<a id="2-create-the-automation-group"></a>

## Step 2: Create the automation group

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum group add platform-automation --comment "Platform automation"
```

| Role | Permitted work |
| --- | --- |
| `PlatformAutomationVM` | Clone/create/configure/start/stop/remove authorized guests |
| `PlatformAutomationStorage` | `Datastore.Audit` and `Datastore.AllocateSpace`: inspect storage and allocate guest disks |
| `PlatformTemplateUpload` | `Datastore.AllocateTemplate`: upload source images; template publishers only |
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

<a id="step-2-grant-only-the-selected-resource-paths"></a>
<a id="3-grant-vm-permissions-to-the-group"></a>

## Step 3: Grant VM scope

**VMs:** the current Terraform model uses explicit VMIDs without pool placement:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum acl modify /vms --groups platform-automation --roles PlatformAutomationVM
```

If pool placement is deliberately added, use the reviewed pool boundary instead.
Cloning still needs access to the source template. [1]

<a id="4-grant-storage-permissions-to-the-group"></a>

## Step 4: Grant live-storage scope

**Live storage:** enter an actual datastore ID; repeat for every approved disk/CloudInit target:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
read -r -p "Live VM datastore ID (for example local-zfs): " VM_DATASTORE
pveum acl modify "/storage/$VM_DATASTORE" --groups platform-automation --roles PlatformAutomationStorage
```

## Step 5: Grant image-publishing scope

**Tier 0 images:** enter the actual Import datastore selected by
`all.image_datastore_id` in Tier 0's `templates/proxmox.yml`, such as `local` or `cephfs`.
Grant both storage roles there to publishing automation. [6][7]

Run on **the selected Proxmox host as an authorized root operator**.

```bash
read -r -p "Import datastore ID (for example local or cephfs): " IMAGE_DATASTORE
pveum acl modify "/storage/$IMAGE_DATASTORE" --groups platform-automation --roles PlatformAutomationStorage,PlatformTemplateUpload
```

Roles contain privileges, not other roles. The ACL above assigns both roles at
the same storage path, giving the publishing identity **three effective privileges**.
`PlatformAutomationStorage` itself still contains only two.
Keep upload rights out of ordinary consuming-tier access.
A separate publisher uses its own group/token grants. Importing existing files does
not upload them, but an adoption plan can include creation of missing files.

<a id="5-grant-proxmox-node-read-access-to-the-group"></a>

## Step 6: Grant node-read scope

**Node:** repeat for each allowed destination and source-template node:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
read -r -p "Authorized Proxmox node name: " PVE_NODE
pveum acl modify "/nodes/$PVE_NODE" --groups platform-automation --roles PlatformAutomationNode
```

<a id="6-grant-bridge-vlan-or-sdn-use-to-the-group"></a>

<a id="step-7a7b-grant-network-scope"></a>

## Step 7: Grant network scope

**Network:** choose **7a or 7b** below for each selected attachment. Local bridge grants
do not authorize an SDN VNet. GUI equivalent: **Datacenter > Permissions > Add > Group Permission**. [1][2]

<a id="2a-direct-bridgevlan-attachment"></a>

### 7a: Direct bridge/VLAN attachment

Use the narrowest prepared path. This example allows VLAN 10 on `vmbr0`:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum acl modify /sdn/zones/localnetwork/vmbr0/10 --groups platform-automation --roles PlatformAutomationNetwork
```

For an intentional bridge-wide grant, use `/sdn/zones/localnetwork/vmbr0`.
Repeat for the actual selected VLANs, then continue at **Step 8**.

<a id="2b-existing-sdn-vnet"></a>

### 7b: Existing SDN VNet

For VNet `edge` in zone `dmz`:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum acl modify /sdn/zones/dmz/edge --groups platform-automation --roles PlatformAutomationNetwork
```

Repeat for every selected VNet, including stopped templates' attachments. Complete
[SDN activation](step-1c-sdn.md#step-3-activate-sdn-on-the-nodes) before use,
then continue at **Step 8**. Subnet lookup uses the same scoped role's `SDN.Audit`.

<a id="step-3-create-the-user-and-token"></a>

## Step 8: Create the user

<a id="7-create-the-automation-user-and-assign-the-group"></a>

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum user add automation@pve --comment "Platform automation from deployment machine"
pveum user modify automation@pve --groups platform-automation
```

<a id="8-create-the-api-token"></a>

## Step 9: Create the token

The established group-managed bootstrap example inherits this dedicated user's
permissions. Adding the user to other groups also expands this token's permissions. [1]

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum user token add automation@pve provision --privsep 0 --comment "Platform provisioning token"
```

**Save the secret immediately into protected custody; Proxmox displays it only once.**
Use separate credentials when job/tier scope differs. For a privilege-separated token,
use the [matching ACL procedure](#existing-or-privilege-separated-tokens) before validation.

<a id="usb-mapping-access"></a>

### 9a: Authorize selected USB mappings: optional

For USB HSM passthrough, first create the reviewed device/port mapping under **Datacenter > Resource
Mappings > USB**. Use that exact mapping ID in Terraform `usb_devices[].mapping`.
Mapped-device use additionally requires `Mapping.Use` on `/mapping/usb/<mapping-id>`; raw physical
`host` selectors require `root@pam` and are unsuitable for the routine provisioning token. [11]

On **the Proxmox host as an authorized root operator**, create the role once, then grant only the
selected mapping. Repeat the ACL for each approved device; reuse an accepted existing role:

```bash
pveum role add PlatformAutomationMapping --privs 'Mapping.Use'
read -r -p 'Approved USB mapping ID (example ca-1-token): ' USB_MAPPING
pveum acl modify "/mapping/usb/$USB_MAPPING" --groups platform-automation --roles PlatformAutomationMapping
```

For a **privilege-separated token**, also grant its matching mapping scope on **the Proxmox host**:

```bash
pveum acl modify "/mapping/usb/$USB_MAPPING" --tokens 'automation@pve!provision' --roles PlatformAutomationMapping
```

Verify the actual consuming token on **the Proxmox host**; expect `Mapping.Use`, then continue at Step 10:

```bash
pveum user permissions 'automation@pve!provision' --path "/mapping/usb/$USB_MAPPING"
```

Replace the example token/group with the identity used by the owning tier. Mapping use grants no
mapping-creation or host-administration rights. A mapping also does not replicate a USB device or its keys.

<a id="validate-access"></a>

## Step 10: Validate effective permissions

**Still on the Proxmox host**, inspect the actual token ID and actual resource paths.
The commands contain no token secret:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum user permissions 'automation@pve!provision' --path "/storage/$IMAGE_DATASTORE"
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
| Selected USB device mapping | `Mapping.Use` on its exact `/mapping/usb/<mapping-id>` path |

A plan can pass read checks without proving later upload/NIC-write permission.
Investigate a 403 at its exact path; do not broaden the grant to `/`.
After provisioning, test permitted and denied operations on disposable guests. [1]

<a id="use-the-token"></a>
<a id="step-4-set-inputs-on-the-bootstrap-host"></a>

## Step 11: Continue with local inputs

For first installation, return directly to [Bootstrap Step 16](../bootstrap/README.md#step-16-initialize-template-inputs)
to initialize **Tier 0**, edit `.env.local`, configure Shared and protect recovery inputs.
The API roles, scoped ACLs and token are complete; do not create them again.

The remaining examples are for adding another consuming tier later, not extra first-install tasks.

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
| Kubernetes command, currently Talos | Uses exported native `PROXMOX_VE_ENDPOINT` and `PROXMOX_VE_API_TOKEN`; follow its [configuration step](../../stage-04-kubernetes/procedures/talos-terraform.md#configure) |
| Packer | Uses `PROXMOX_URL=https://pve01.example.internal:8006/api2/json` and its separate build inputs |

Terraform endpoints use the HTTPS root, **without `/api2/json`**. [3][4]
The bootstrap workflow owns the remaining first-install inputs and handoff to host management.
Do not skip directly to a guest deployment from this permission procedure.
Do not deploy the `foundation` Linux setup merely to validate this token.

## Existing or privilege-separated tokens

Separated tokens need both group/user and token grants. Their effective permissions
are the intersection; token ACLs cannot expand the owning user's rights. [1]
Retain the selected privilege-separation mode; changing a role does not change it.

For a separated token, mirror each selected VM, node, datastore and attachment grant
from Steps 3–7 using `--tokens 'automation@pve!provision'` instead of `--groups`.
For example, the Tier 0 Import datastore and an allowed VNet:

Run on **the selected Proxmox host as an authorized root operator**.

```bash
pveum acl modify "/storage/$IMAGE_DATASTORE" --tokens 'automation@pve!provision' --roles PlatformAutomationStorage,PlatformTemplateUpload
pveum acl modify /sdn/zones/dmz/edge --tokens 'automation@pve!provision' --roles PlatformAutomationNetwork
```

Keep base storage read/allocation roles when adding upload rights. Repeat
[effective-permission validation](#validate-access) using the exact consuming token.
If `SDN.Use` appears without `SDN.Audit`, check the case-sensitive role ID and both ACL sides.

<a id="ha-automation-identity"></a>

## Optional HA automation identity

The [HA recipe](../../../05-operations/01-hosting/proxmox-ha.md#configure-through-iac) manages
cluster-wide guest enrollment and affinity. The current Proxmox API requires **`Sys.Audit` and
`Sys.Console` on `/`**, plus **`VM.Audit`** to resolve the selected guests, including the effective
rights of a separated token. The example grants the VM read privilege cluster-wide for name lookup.
`Sys.Console` also
authorizes host-console access; this is a privileged infrastructure identity. Keep it separate
from normal template/provisioning tokens. [8][9][10]

Run once in **an authorized Proxmox host shell**. Reuse accepted existing objects on later runs;
do not create a replacement token merely to repeat enrollment.

```bash
pveum role add PlatformAutomationHA --privs 'Sys.Audit Sys.Console VM.Audit'
pveum group add ha-automation
pveum acl modify / --groups ha-automation --roles PlatformAutomationHA
pveum user add ha-automation@pve --groups ha-automation
pveum user token add ha-automation@pve manage --privsep 1
pveum acl modify / --tokens 'ha-automation@pve!manage' --roles PlatformAutomationHA
```

Retain the newly displayed secret privately for the HA invocation. Confirm its effective rights
in **the Proxmox host shell**; this check uses only the token ID.

```bash
pveum user permissions 'ha-automation@pve!manage' --path /
```

Supply this identity only to the [HA run](../../../05-operations/01-hosting/proxmox-ha.md#configure-through-iac).
The ordinary VM automation identity and its ACLs retain their existing role.

<a id="ceremony-automation-identity"></a>

## Ceremony automation identities

Use this for the optional [on-demand ceremony VMs](../../stage-02-trust/procedures/ceremony-environment.md).
**Controller prerequisite:** activate [Bootstrap 9b's isolated reference runtime](../bootstrap/README.md#9b-isolated-reference-runtime).
These native modules need Ansible core 2.17 or later plus `proxmoxer` and `requests` from
Tier 0 `ansible/requirements.txt`; OS-packaged core 2.16 used by the cache path is insufficient.
**Tier 0 IaC** creates separate identities, roles, exact resource grants, the ceremony pool and a
dedicated ISO-only datastore. It leaves the provisioner disabled. Root signing secrets never enter
these inputs, the API credentials or the public ISO.
An existing ISO store is adopted only when its directory, type, content and selected nodes already
match; symlink directories and aliases of another datastore are rejected. Changing an existing binding
requires a new dedicated store selection so previous public images remain discoverable.

| Identity | Granted authority | Scope |
| --- | --- | --- |
| `ceremony-provision@pve` | Allocate/configure the selected VMs; publish public ISOs; use selected USB mappings | Exact future/existing VMIDs, ceremony pool, selected nodes, dedicated ISO store and mappings |
| `ceremony-power@pve` | `VM.Audit`, `VM.PowerMgmt` | Exact ceremony VMIDs only |
| Existing human custodians | `VM.Audit`, `VM.Console` | Exact ceremony VMIDs only; GUI login with MFA |

Neither routine token has console, guest execution, permission administration or host-power rights.
VM allocation can be granted on `/vms/<id>` before the VM exists; no `/vms` or `/` grant is needed.
The provisioner has no network-configuration privilege. [1][11][12]

### 1. Initialize and select the ceremony resources

On **bootstrap, in `<prefix>-tier-0`**, initialize the access inputs:

```bash
bash scripts/init-local-files.sh --setup ceremony-access
```

Edit `ansible/group_vars/ceremony_access.yml`:

| Input | What to enter |
| --- | --- |
| `ceremony_access_endpoint` | The verified Proxmox HTTPS root, such as `https://pve01.example.internal:8006/` |
| `ceremony_access_audit_host` | One existing `hypervisors` inventory key; existing host-management SSH/sudo must work |
| `ceremony_access_sessions` | Match every selected `ceremony_sessions` name, `vm_id` and `node_name` in `terraform/deployments/ceremony/terraform.tfvars` |
| `ceremony_access_pool` | The same dedicated ceremony pool selected by Terraform |
| `ceremony_access_iso_datastore` | Dedicated `ceremony-*` ISO store, default `ceremony-iso`; select this store in Terraform too |
| `ceremony_access_usb_mappings` | The exact existing mapping IDs assigned to these sessions; omit unused devices |
| `ceremony_access_excluded_users` | Every ordinary provisioning/publishing token's **owner**, such as `automation@pve` |
| `ceremony_access_custodians` | Existing named human GUI users; optional, never an automation identity |
| `ceremony_access_token_expire` | Explicit Unix expiration for both separated tokens |

Choose an expiration that covers the next approved activation and the credential-maintenance interval.
For a 45/60-day ceremony cadence, a 30-day token expires before the next wake: use a suitable longer
deadline or rotate it beforehand. The provisioner still has a separate one-hour lease and remains locked
between maintenance windows. Get a proposed 90-day token deadline on **bootstrap**, then paste that
number into `ceremony_access_token_expire`:

```bash
date -d '+90 days' +%s
```

**Existing broad access matters:** another identity's inherited `/vms` or storage permissions do not
disappear when a narrower identity is created. This role adds explicit per-resource `NoAccess` grants
for the listed ordinary owners and verifies their effective permissions. Their tokens are bounded
by the owner's denial, including privilege-separated tokens. Selected ceremony mappings are therefore
reserved for ceremony provisioning; do not list a mapping still required by an ordinary deployment.
Keep the ISO store separate from normal template publishing so its denial does not break those jobs.
Hypervisor administrators remain trusted. [1]
This includes any host-management SSH/sudo access already held by bootstrap: API denials do not
constrain that route. Use a separate administration workstation and restrict host-administrator access
during ceremonies if required by the threat model, or choose physical offline root execution.
This role does not alter SSH keys or host-admin accounts.

### 2. Configure the identities

On **bootstrap, in `<prefix>-tier-0`**, run the native Ansible workflow:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook \
  -i ansible/inventory/hosts.yml ansible/playbooks/ceremony-access.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/ceremony_access.yml
```

Enter the authorized administrator's password at the private prompt. No administrator credential is
written to a file. For an MFA-protected account, use a short-lived **commissioning** token instead:
sign in through the approved MFA GUI, create a root-owned token authorized for this access-maintenance
task with a short expiration, and enter its **token name**, without `root@pam!`, and secret below.
Leave the playbook password prompt empty. Reusing one TOTP across repeated module logins is unsupported.

On **bootstrap**, read the temporary commissioning credential without recording it in shell history:

```bash
read -r -p 'Temporary commissioning token name: ' CEREMONY_ADMIN_TOKEN_ID
read -r -s -p 'Temporary commissioning token secret: ' CEREMONY_ADMIN_TOKEN_SECRET
printf '\n'
export CEREMONY_ADMIN_TOKEN_ID CEREMONY_ADMIN_TOKEN_SECRET
```

Rerun the workflow above, then unset these variables and revoke the commissioning token through the
GUI. Its administrator authority is only for access maintenance; neither ceremony token receives it.

```bash
unset CEREMONY_ADMIN_TOKEN_ID CEREMONY_ADMIN_TOKEN_SECRET
```

Expected: `.env.ceremony-provisioner` and `.env.ceremony-operator` are written with mode `0600`,
outside Terraform state. The role replaces unexpected direct grants and clears inherited groups
for its two dedicated owners, then checks owner/token intersections and ordinary-owner denials.
Proxmox returns new secrets only once; retain these files privately. [1][13]

### 3. Open a bounded provisioning window

Keep ceremony VMs shut down and custody media locked/detached. Finish any outstanding power jobs.
On **bootstrap, in `<prefix>-tier-0`**, enable provisioning for the configured window:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook \
  -i ansible/inventory/hosts.yml ansible/playbooks/ceremony-access.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/ceremony_access.yml \
  -e ceremony_access_action=unlock
```

The role disables the routine power identity before checking stopped VMs. A fixed local systemd lease
on the audit hypervisor disables provisioning and restores power access when the window ends; it holds
no API secret. Provisioning also has the same absolute account expiration if that timer cannot run.
If the audit host is down, run `lock` after recovery to restore routine power access.
Already-started tasks and other trusted administrators require an exclusive maintenance window. [1]

Return to the [ceremony VM provisioning step](../../stage-02-trust/procedures/ceremony-environment.md#7-prepare-the-selected-runtime)
and use **`.env.ceremony-provisioner`** for that Terraform run. Then lock the identity immediately:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook \
  -i ansible/inventory/hosts.yml ansible/playbooks/ceremony-access.yml \
  -e @ansible/group_vars/all.yml -e @ansible/group_vars/ceremony_access.yml \
  -e ceremony_access_action=lock
```

Locking disables provisioning before restoring routine power. Human custodians receive console access
without power privileges. Configuration also suspends existing dedicated owners before reconciliation;
a failed configure/unlock can leave routine power disabled. Correct the inputs and rerun configure,
or use `lock` to revoke provisioning and restore power access with the retained approved scopes.

### 4. Inspect or start a selected session

On **bootstrap, in `<prefix>-tier-0`**, load only the power identity and select the configured session:

```bash
set -a
source .env.ceremony-operator
set +a
CONTROL_NODE_COLLECTIONS_MODE=check ANSIBLE_CONFIG=ansible/ansible.cfg \
  ansible-playbook -i localhost, ansible/playbooks/ceremony-power.yml \
  -e @ansible/group_vars/ceremony_access.yml -e ceremony_power_session=orca-1
```

Default action is `status`. Add `-e ceremony_power_action=start` to request activation.
This recipe never creates a VM, changes hardware, unlocks keys, runs a guest command or forces shutdown.
Before starting, it rejects NICs, an enabled guest agent and persistent OS disks in both current and
pending configuration. The operator still verifies the approved ISO and intended physical custody media.
The optional timer below invokes this same start recipe after dependencies are prepared and provisioning
is locked; activation is **not** proof of CRL renewal. Continue at the local console and verify the
published CRL independently. Power down from the ceremony environment after backup and media removal.
Schedule credential renewal before the token deadline; the independent public-CRL watchdog must
continue reporting overdue publication even if an expired power token prevents activation.

For a read-only rights audit, rerun the access workflow with `-e ceremony_access_action=verify`.
To rotate a lost/expired token, choose a **new** `ceremony_access_token_id` and future expiration, then
rerun `configure` with VMs stopped. The dedicated users' previous tokens are revoked and new protected
files replace them; keep all other identities' credentials unchanged.

### 5. Optionally schedule one approved activation window

On **bootstrap, in `<prefix>-tier-0`**, initialize the optional timer inputs:

```bash
bash scripts/init-local-files.sh --setup ceremony-schedule
```

Edit `ansible/group_vars/ceremony_schedule.yml`: set `ceremony_schedule_session` to a configured
session, set `ceremony_schedule_calendar` to the approved future UTC time in the format
`2027-01-15 09:00:00 UTC`, and set `ceremony_schedule_enabled: true`. The operator token expiration
must cover that window. Run as the **unprivileged controller account with sudo available**:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook -i localhost, \
  ansible/playbooks/ceremony-schedule.yml -e @ansible/group_vars/ceremony_access.yml \
  -e @ansible/group_vars/ceremony_schedule.yml
```

Expected: a root-managed `ceremony-wake-<session>.timer` invokes the prepared native client as the
unprivileged account. A root-only `0600` environment file holds **only** the power token. The timer
has `Persistent=false`, so a missed window never causes an unexpected later activation. It neither
forces shutdown nor unlocks the root. Keep provisioning locked before the window and attend the
local-console ceremony; the independent public-CRL watchdog remains the completion check.

Change the UTC time and rerun to reschedule. After token rotation, rerun to update the protected
copy. To remove the timer and its copied credential, set `ceremony_schedule_enabled: false` and
rerun the same command. Removing a timer does not stop a VM or interrupt an active ceremony.
VM deletion removes per-VM ACLs too: rerun access `configure` before reusing a deleted session VMID.

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
8. [Proxmox HA resource API permissions](https://raw.githubusercontent.com/proxmox/pve-ha-manager/master/src/PVE/API2/HA/Resources.pm).
9. [Proxmox HA rule API permissions](https://raw.githubusercontent.com/proxmox/pve-ha-manager/master/src/PVE/API2/HA/Rules.pm).
10. [Proxmox VM visibility checks](https://raw.githubusercontent.com/proxmox/pve-manager/master/PVE/API2/Cluster.pm).
11. [Proxmox USB configuration permission checks](https://github.com/proxmox/qemu-server/blob/master/src/PVE/API2/Qemu.pm).
12. [Proxmox VM creation permission checks](https://raw.githubusercontent.com/proxmox/qemu-server/master/src/PVE/API2/Qemu.pm).
13. [Native Ansible Proxmox user/token module](https://docs.ansible.com/projects/ansible/latest/collections/community/proxmox/proxmox_user_module.html).
