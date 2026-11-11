# Foundation and prerequisites

Prepare the hosts and the execution machine, then import or publish tested VM templates.
Complete this path before **Stage 1: Software intake**. Foundation is a prerequisite,
not a numbered capability stage.

For planned teardown and a new installation, use [resource retirement](../../05-operations/provisioning.md).
For an existing environment lost to failure, use [backup recovery](../../05-operations/recovery.md) with its original state.

**Start on:** an independent privileged workstation with physical/console recovery access.
**Working repository:** `<prefix>-tier-0` after generation (source: `tier-0/`).
**Continue on:** `boot-1`, then the generated `<prefix>-tier-0` repository.
**Design:** [hosting](../../01-architecture/10-hosting/README.md) and
[network boundaries](../../01-architecture/11-networking/README.md).

## Contents

- [Step 1: Prepare hosts and networks](#step-1-prepare-hosts-and-networks)
- [Step 2: Create the first Linux template manually](#step-2-create-the-first-linux-template-manually)
- [Step 3: Prepare the bootstrap execution host](#step-3-prepare-the-bootstrap-execution-host)
- [Step 4: Publish and test VM templates](#step-4-publish-and-test-vm-templates)
- [Foundation ready](#foundation-ready)

<a id="step-1-prepare-compute-and-templates"></a>
<a id="step-1-prepare-hosts-and-networks"></a>
<a id="before-starting-hosts-and-networks"></a>

## Step 1: Prepare hosts and networks

Complete these in order. Existing infrastructure is valid after the same checks.

| Order | Action | Complete when |
| --- | --- | --- |
| 1 | [Prepare the gateway, switches and VLANs](network/unifi.md#bring-up-the-network) | Management access, DNS/time, guest VLANs and a recovery path work |
| 2 | [Install Proxmox and configure its host network](proxmox/README.md#first-deployment-order) | Console/UI work; `vmbr0` and the approved VLAN trunks are active |
| 3 | [Select live storage and an independent backup destination](storage/README.md) | Actual datastore IDs and recovery access are recorded |
| 4 | [Apply and test firewall policy](network/firewall.md) | Required paths work and unauthorized paths fail |

After host action **2**, choose the host/network paths below, then finish storage/firewall actions **3–4**.
HA enrollment and failure testing need a disposable guest later in this Foundation path; cluster membership
alone does not establish HA. Retain persistent local host logs from first boot until Stage 2 can collect them.
Object storage is needed before its first consuming application, not for these initial steps.

| Path / option | Action now | Continue |
| --- | --- | --- |
| 1a: single host | Use one prepared host; no cluster or automatic failover | Storage/firewall checks above, then Step 2 |
| 1b: cluster | [Join empty hosts and prepare HA](proxmox/step-1b-cluster-ha.md) | Storage/firewall checks, then Step 2; enroll/test a disposable guest in Step 4 |
| 1c: SDN, optional with either host path | [Create and apply VNets, Steps 1–3](proxmox/step-1c-sdn.md) | Storage/firewall checks above, then Step 2; finish SDN authorization after bootstrap in Step 3 |

<a id="step-1-create-the-first-linux-template-manually"></a>

## Step 2: Create the first Linux template manually

Use the [VMID quick reference](../../02-conventions/vmid-convention.md) before reserving
template or guest IDs; its allocation plan applies to Terraform-managed VMs and containers too.

Follow [VM templates: Steps 1–3](proxmox/templates.md):

1. Download and verify one approved Linux cloud image; unpack it before uploading.
2. Create the unbooted VM in Proxmox, import its disk and add the CloudInit drive.
3. Convert it to a template and test a disposable clone.

One AlmaLinux or Rocky Linux template is sufficient for the bootstrap VM. An accepted
existing Linux template is also valid. Add Talos and other candidates in Step 4 below.
No API token, Terraform or GitLab is needed for this first manual template.

<a id="step-2-protect-provisioning-access-and-state"></a>
<a id="step-2-prepare-the-bootstrap-execution-host"></a>

## Step 3: Prepare the bootstrap execution host

Follow [Bootstrap execution host: Steps 1–4](bootstrap/README.md) without skipping ahead.
That guide provides the VM, tooling, repository generation, SSH key and API setup.

Choose workspace **3a or 3b**, optionally **3c**, then acquisition **3d or 3e** at bootstrap Step 2.
Finish that guide's SSH/trust Steps 3–4 before **3f** below. An accepted existing execution host
can use the same tooling/trust path without creating another VM.

| Path / option | Detailed guide | Rejoin |
| --- | --- | --- |
| 3a: separate workspace, main | [Prepare the attached data disk](bootstrap/step-3a-bootstrap-storage.md) | Bootstrap Step 2, create workspace directories |
| 3b: LVM root instead | [Expand the existing disk or add an LVM PV](bootstrap/step-3b-bootstrap-lvm.md) | Bootstrap Step 2, create workspace directories; skip separate-mount actions |
| 3c: home on data disk, optional after 3a | [Bind-mount home](bootstrap/step-3c-bootstrap-home.md) | Bootstrap Step 2, before repositories/keys are created |
| 3d: connected tools, main | [Install approved tools and generate repositories](bootstrap/README.md#2a-install-git-terraform-and-ansible) | Bootstrap Step 3 |
| 3e: offline tools instead | [Prepare, transfer and install the bundle](bootstrap/step-3e-bootstrap-offline.md) | Bootstrap Step 3 |
| 3f: manage hosts | [Initialize host management](../../05-operations/hosts/management.md), then [API trust and credentials](proxmox/api-access.md) | SDN Step 4 if 1c was selected; then Foundation Step 4 |

| Location | Configure before continuing |
| --- | --- |
| Bootstrap VM | Tooling, independently verified Proxmox CA trust and a usable execution-account SSH key/agent |
| Architecture `platform-standards.md` | Actual node names, VMIDs, network/VLAN allocations and selected options |
| Shared `config/platform.tfvars` | Initial destination node, live-disk storage classes and common application network |
| Tier 0 `.env.local` | Verified API endpoint, scoped token and local public-key paths |
| Outside the platform | Recoverable copies of original state, ignored inputs, tools and credentials |

**Gate:** verified API TLS and independent console/recovery access must work. A VM on
Proxmox cannot be the only means of recovering Proxmox. Keep approved package/artifact
access independent of the cache deployed in Stage 1.
Test recovery of the original state and credentials on the independent execution path
before provisioning; guest backup/restore is tested on the first disposable clone in Step 4.

<a id="2a-connect-bootstrap-to-proxmox-host-management"></a>

### 3f: Connect bootstrap to Proxmox host management

Once `boot-1` and the generated Tier 0 repository are ready, follow
[Manage existing Proxmox hosts from bootstrap](../../05-operations/hosts/management.md).
Its numbered steps initialize the local files, register `hypervisors`, authorize the execution
key and verify SSH/Ansible access. The registered hosts already exist; this does not deploy VMs.

If **1c** was selected, finish [SDN Step 4](proxmox/step-1c-sdn.md#step-4-authorize-and-connect-iac) now.
Return here for **Step 4**. After Stage 1 establishes the selected software-supply route, use
[Proxmox update access](../../05-operations/hosts/update-access.md) to configure and test host
updates through it. Host-management tasks use SSH; `deploy.sh foundation` provisions CA/directory VMs.

<a id="step-3-publish-and-test-vm-templates"></a>

## Step 4: Publish and test VM templates

**Run on:** the bootstrap execution host, from generated **Tier 0**. An existing accepted
privileged Linux workstation can perform the same role. No hosted runner is required.

Before adding a Talos build, select its [version contract](proxmox/templates.md#talos-version-contract).
The complete reference through Stage 5 uses an approved exact **1.13.x** release; choosing the
newest Factory entry does not establish compatibility with the later platform/SSO recipes.

Run from **`<prefix>-tier-0/`** on the protected execution host.

```bash
bash scripts/proxmox-templates.sh init
```

`init` preserves existing files. Configure the selected builds before planning:

Edit in **`<prefix>-tier-0/`**.

- `templates/proxmox.yml`: Select builds, existing VMIDs and approved local image paths/hashes.

| Field | Set to |
| --- | --- |
| `all.node_name` | Actual node holding the templates |
| `all.storage_class` | A live-disk class configured in Shared; an explicit `datastore_id` overrides it |
| `all.image_datastore_id` | Existing datastore accepting **Import** files, often `local` |
| `all.bridge`, `all.vlan_id` | Prepared `vmbr0`/VLAN, or activated SDN VNet with `vlan_id: null` |
| Each selected build | Actual `vm_id`, `name`, OS family/distribution, exact release, local `image_path` and unpacked `sha256` |
| Existing uploaded files | `image_file_name`: exact Import basename, even if its prefix uses an older VMID |

Keep only managed builds. Use `sha256sum` on each approved unpacked artifact to obtain
its catalog hash. For the first Linux template, remove unused build blocks and replace
every remaining placeholder before import. Set `name` to the existing Proxmox display
name; the YAML candidate names need not match the earlier manual naming examples.
For adoption, match existing hardware and firmware before reviewing changes. Existing
uploads are matched by filename; verify their provenance or remote checksum independently.
Import does not establish that the stored bytes match a checksum embedded in the filename.
The [field reference](../../05-operations/virtual-machines/template-lifecycle.md#catalog-fields-and-defaults)
contains optional settings; fixed RAM, 1500-MTU NICs, NIC firewall and OS-specific
controller defaults do not need repeating for every build.

### 4a: Adopt existing templates or uploaded images

This is the normal first-run path after creating the manual template:

Run from **`<prefix>-tier-0/`** on the protected execution host.

```bash
bash scripts/proxmox-templates.sh import --env-file .env.local
```

`import` creates a **saved adoption plan**; imports are written to state only at apply.
Missing resources may still be creations. Continue with **Apply and qualify** below. Do not replace this saved
adoption plan with a normal plan before applying it.

### 4b: Publish an entirely new catalog

Use this alternative only when none of the catalogued templates or uploaded files exists:

Run from **`<prefix>-tier-0/`** on the protected execution host.

```bash
bash scripts/proxmox-templates.sh plan --env-file .env.local
```

Continue with **Apply and qualify** below.

<a id="3c-review-apply-and-qualify"></a>

### Apply and qualify

After either **4a** or **4b**, complete all actions below.

1. Inspect imports and every hardware/disk change in the saved plan. Stop on unexpected
   replacement/deletion; correct the catalog and repeat **4a** or **4b** first.
   Keep the catalog, platform profile and execution target unchanged until apply.
   The saved plan and its `.context` file belong together; regenerate an older plan
   without this context file rather than applying it with changed inputs.
2. Apply the accepted saved plan. This command applies a previously reviewed plan;
   do not rely on another approval prompt.

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/proxmox-templates.sh apply --env-file .env.local
   ```

   **Expected:** publication completes successfully. Stop on errors before continuing.
3. Verify fixed RAM and empty template accounts, from **`<prefix>-tier-0/`**:

   ```bash
   bash scripts/proxmox-templates.sh verify --env-file .env.local
   ```

   `verify` checks RAM/accounts, not clone networking or image boot.
   An optional drift check should produce a no-change plan:

   Run from **`<prefix>-tier-0/`** on the protected execution host.

   ```bash
   bash scripts/proxmox-templates.sh plan --env-file .env.local
   ```

4. [Boot and qualify disposable clones](proxmox/templates.md#clone-and-guest-control-checks).
   Check disks, network, guest control and operator access. Qualify the
   selected template firmware, CloudInit and guest-agent settings.
5. [Back up and restore a disposable clone](../../05-operations/backups/virtual-machines.md#quick-steps),
   including required data disks. Record the result before relying on that backup path.
6. Successful apply updates **Shared's `templates/proxmox-catalog.tfvars`**. After clone
   acceptance, edit its `default_linux_vm_template_id` to the tested Linux VMID:

   ```hcl
   default_linux_vm_template_id = 9101
   ```

   `9101` is the Rocky example; select the actual tested catalog entry. Apply preserves
   this selection. Talos is not the default image for Linux services.

**IaC:** Tier 0 owns the [publication inputs](../../../tier-0/templates/proxmox.yml.example),
[script](../../../tier-0/scripts/proxmox-templates.sh),
[resources/state](../../../tier-0/terraform/deployments/templates/main.tf).
Shared holds [consumer references](../../../shared/templates/proxmox-catalog.tfvars).
Adoption leaves the bootstrap VM outside Terraform and retains existing boot disks;
intentional image replacement uses [boot-disk maintenance](../../05-operations/virtual-machines/template-disk.md).

### 4c: Finish selected HA and balancing options

For **1b**, enroll the disposable test VM and complete the [HA failover exercise](proxmox/failover.md).
Use native rebalancing by default. If a different balancer is selected, qualify
[ProxLB](proxmox/step-4c-proxlb.md) now, with one placement authority per guest. Return to the readiness checks below.
For **1a**, skip this option; no automatic host failover is claimed.

### 4d: Refresh a Linux image before publishing — optional

For a mutable Linux candidate, follow [template refresh](../../05-operations/virtual-machines/template-refresh.md),
then repeat **4a/4b** and clone qualification above. Direct verified image publication remains valid;
this does not apply to Talos. Return to the readiness checks below.

<a id="capability-available"></a>

## Foundation ready

- [ ] Hosts/networks are reachable through protected, tested paths.
- [ ] Bootstrap tools, verified API access, SSH and independent recovery copies work.
- [ ] Template clones boot and the selected Linux VMID is recorded in Shared.
- [ ] Guest backup/restore and original-state recovery have recorded results.

Continue to **[Stage 1: Software intake](../stage-1-software-intake/README.md)**.
The cache is the next deployment in the main track and runs from **Tier 2**; stay on
the bootstrap host and change repository as the stage directs. After that stage,
return to Tier 0 for **[Stage 2: Protected logging](../stage-2-logging/README.md)**.
Neither capability waits for FreeIPA or Kubernetes.

This completes the compute portion of the
[reference platform](../../01-architecture/06-reference-platform.md#service-placement).
