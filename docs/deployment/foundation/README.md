# Foundation and prerequisites

Prepare the hosts and the execution machine, then import or publish tested VM templates.
Complete this path before **Stage 1: Software intake**. Foundation is a prerequisite,
not a numbered capability stage.

For planned teardown and a new installation, use [resource retirement](../../administration/provisioning.md).
For an existing environment lost to failure, use [backup recovery](../../administration/recovery.md) with its original state.

**Start on:** an independent privileged workstation with physical/console recovery access.
**Working repository:** `<prefix>-tier-0` after generation (source: `tier-0/`).
**Continue on:** `boot-1`, then the generated `<prefix>-tier-0` repository.
**Design:** [compute](../../architecture/hosting/README.md) and
[network boundaries](../../architecture/networking/README.md).

## Contents

- [Before starting: hosts and networks](#before-starting-hosts-and-networks)
- [Step 1: Create the first Linux template manually](#step-1-create-the-first-linux-template-manually)
- [Step 2: Prepare the bootstrap execution host](#step-2-prepare-the-bootstrap-execution-host)
- [Step 3: Publish and test VM templates](#step-3-publish-and-test-vm-templates)
- [Foundation ready](#foundation-ready)

<a id="step-1-prepare-compute-and-templates"></a>
<a id="step-1-prepare-hosts-and-networks"></a>

## Before starting: hosts and networks

Complete these in order. Existing infrastructure is valid after the same checks.

| Order | Action | Complete when |
| --- | --- | --- |
| 1 | [Prepare the gateway, switches and VLANs](network/unifi.md#bring-up-the-network) | Management access, DNS/time, guest VLANs and a recovery path work |
| 2 | [Install Proxmox and configure its host network](proxmox/README.md#first-deployment-order) | Console/UI work; `vmbr0` and the approved VLAN trunks are active |
| 1b, optional branch | [Create the cluster and select HA](step-1b-cluster-ha.md) | Quorum and guest-mobility prerequisites pass; return here before populating hosts |
| 1c, optional branch | [Configure guest SDN](step-1c-sdn.md) | VNets are activated with **Datacenter > SDN > Apply** on every eligible node |
| 3 | [Select live storage and an independent backup destination](storage/README.md) | Actual datastore IDs and recovery access are recorded |
| 4 | [Apply and test firewall policy](network/firewall.md) | Required paths work and unauthorized paths fail |

HA enrollment and failure testing need a disposable guest later; cluster membership
alone does not establish HA. Retain persistent local host logs from first boot until Stage 2 can collect them.
Object storage is needed before its first consuming application, not for these initial steps.

## Step 1: Create the first Linux template manually

Use the [VMID quick reference](../../conventions/vmid-convention.md) before reserving
template or guest IDs; its allocation plan applies to Terraform-managed VMs and containers too.

Follow [VM templates: Steps 1–3](proxmox/templates.md):

1. Download and verify one approved Linux cloud image; unpack it before uploading.
2. Create the unbooted VM in Proxmox, import its disk and add the CloudInit drive.
3. Convert it to a template and test a disposable clone.

One AlmaLinux or Rocky Linux template is sufficient for the bootstrap VM. An accepted
existing Linux template is also valid. Add Talos and other candidates in Step 3 below.
No API token, Terraform or GitLab is needed for this first manual template.

<a id="step-2-protect-provisioning-access-and-state"></a>

## Step 2: Prepare the bootstrap execution host

Follow [Bootstrap execution host: Steps 1–4](proxmox/bootstrap.md) without skipping ahead.
That guide provides the VM, tooling, repository generation, SSH key and API setup.

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
before provisioning; guest backup/restore is tested on the first disposable clone in Step 3.

## Step 3: Publish and test VM templates

**Run on:** the bootstrap execution host, from generated **Tier 0**. An existing accepted
privileged Linux workstation can perform the same role. No hosted runner is required.

```bash
# Run from <prefix>-tier-0/ on the protected execution host.
bash scripts/proxmox-templates.sh init
```

`init` preserves existing files. Configure the selected builds before planning:

```text
# Edit in <prefix>-tier-0/
templates/proxmox.yml # Select builds, existing VMIDs and approved local image paths/hashes.
```

| Field | Set to |
| --- | --- |
| `all.node_name` | Actual node holding the templates |
| `all.storage_class` | A live-disk class configured in Shared; an explicit `datastore_id` overrides it |
| `all.image_datastore_id` | Existing datastore accepting **Import** files, often `local` |
| `all.bridge`, `all.vlan_id` | Prepared `vmbr0`/VLAN, or activated SDN VNet with `vlan_id: null` |
| Each selected build | Actual `vm_id`, `name`, OS family/distribution, exact release, local `image_path` and unpacked `sha256` |
| Existing uploaded files | `image_file_name`: exact Import basename, even if its prefix uses an older VMID |

Keep only managed builds. Use `sha256sum` on each approved unpacked artifact to obtain
its catalog hash. For adoption, match existing hardware and firmware before reviewing
changes. The [field reference](../../administration/virtual-machines/template-lifecycle.md#catalog-fields-and-defaults)
contains optional settings; fixed RAM, 1500-MTU NICs, NIC firewall and OS-specific
controller defaults do not need repeating for every build.

### 3a: Adopt existing templates or uploaded images

This is the normal first-run path after creating the manual template:

```bash
# Run from <prefix>-tier-0/ on the protected execution host.
bash scripts/proxmox-templates.sh import --env-file .env.local
```

`import` creates a **saved adoption plan**; imports are written to state only at apply.
Missing resources may still be creations. Continue at **3c**. Do not replace this saved
adoption plan with a normal plan before applying it.

### 3b: Publish an entirely new catalog

Use this alternative only when none of the catalogued templates or uploaded files exists:

```bash
# Run from <prefix>-tier-0/ on the protected execution host.
bash scripts/proxmox-templates.sh plan --env-file .env.local
```

Continue at **3c**.

### 3c: Review, apply and qualify

1. Inspect imports and every hardware/disk change in the saved plan. Stop on unexpected
   replacement/deletion; correct the catalog and repeat **3a** or **3b** first.
2. Apply the accepted saved plan, then verify fixed RAM and empty template accounts:

   ```bash
   # Run from <prefix>-tier-0/ on the protected execution host.
   bash scripts/proxmox-templates.sh apply --env-file .env.local
   bash scripts/proxmox-templates.sh verify --env-file .env.local
   ```

   Unlike the Linux `deploy.sh` command, this template command
   applies a previously reviewed saved plan; do not rely on another approval prompt.
   `verify` checks RAM/accounts, not clone networking or image boot.
   An optional drift check should produce a no-change plan:

   ```bash
   # Run from <prefix>-tier-0/ on the protected execution host.
   # Optional: check for drift after the accepted apply.
   bash scripts/proxmox-templates.sh plan --env-file .env.local
   ```

3. [Boot and qualify disposable clones](proxmox/templates.md#clone-and-guest-control-checks).
   Check disks, network, guest control and operator access. Qualify the
   [Linux guest security profile](proxmox/host-security.md) with its console/SSH gates.
4. [Back up and restore a disposable clone](../../administration/backups/virtual-machines.md#quick-steps),
   including required data disks. Record the result before relying on that backup path.
5. Successful apply updates **Shared's `templates/proxmox-catalog.tfvars`**. After clone
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
intentional image replacement uses [boot-disk maintenance](../../administration/virtual-machines/template-disk.md).

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
[reference platform](../../architecture/reference-platform.md#service-placement).
