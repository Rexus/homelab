# Foundation and prerequisites

Prepare Proxmox, networks, approved VM templates and independent provisioning/recovery
access before deploying platform capabilities. Existing infrastructure is valid when
it passes these checks. Foundation is not a numbered capability stage.

**Prerequisites:** physical hosts, network equipment, approved installation sources
and a privileged workstation with independent console access.
**Working repository:** `<prefix>-tier-0` (source: `tier-0/`).
**Design:** [compute](../../architecture/compute/README.md) and
[network boundaries](../../architecture/networking/README.md).

## Preparation checklist

| Area | Detailed guides |
| --- | --- |
| Proxmox | [Host setup](proxmox/README.md), [host networking](proxmox/network.md), [API access](proxmox/api-access.md), [VM templates](proxmox/templates.md) |
| Optional host availability | [Cluster/HA](step-1b-cluster-ha.md), [menu settings](../../reference/proxmox-ha.md), [failover example](proxmox/failover.md) |
| Network equipment and policy | [UniFi setup](network/unifi.md), [firewall rollout](network/firewall.md) |
| Storage | [Live storage interfaces and backup destinations](storage/README.md) |
| Bootstrap execution | [Manual bootstrap VM, tooling, artifacts, CA trust and API inputs](proxmox/bootstrap.md) |

Prepare [hosts and networks](#before-starting-hosts-and-networks), then follow:

1. [Create the first Linux template manually](#step-1-create-the-first-linux-template-manually)
2. [Prepare the bootstrap execution host](#step-2-prepare-the-bootstrap-execution-host)
3. [Publish and test VM templates](#step-3-publish-and-test-vm-templates)

The [bootstrap deployment view](proxmox/bootstrap.md#step-1-clone-the-bootstrap-vm)
shows the VM created in Step 2 and its hosting/management boundaries.
**Manual:** host installation, switches, VLANs, storage, first image and bootstrap VM clone.
**IaC:** Tier 0 [template publisher](../../../tier-0/scripts/proxmox-templates.sh)
uses [publication inputs](../../../tier-0/templates/proxmox.yml.example) and
[publication resources](../../../tier-0/terraform/deployments/templates/main.tf).
Shared [consumer references](../../../shared/templates/proxmox-catalog.tfvars) select approved templates;
they do not create guests or install the physical foundation.

<a id="step-1-prepare-compute-and-templates"></a>
<a id="step-1-prepare-hosts-and-networks"></a>

## Before starting: hosts and networks

Use an independent privileged workstation to bring up the external
network; the [UniFi starting path](network/unifi.md#bring-up-the-network)
includes controller adoption and VLAN/port preparation. Install
[Proxmox](proxmox/README.md), then configure [host networking](proxmox/network.md)
and storage. Verify management access, DNS, time and permitted guest networks.
Select existing [block, file and object interfaces](../../architecture/compute/runtime.md#storage-interfaces)
deliberately. Use direct NAS file storage where supported; qualify an existing
object endpoint only for consumers that require it. The
[storage prerequisites](storage/README.md) add no gateway service.
Object storage must be available before the first consuming database or application,
not before unrelated early logging or trust deployments.

The main path uses bridges and VLANs. **Before important guests**, select
[1b: cluster HA](step-1b-cluster-ha.md) or [1c: SDN guest networks](step-1c-sdn.md)
where required. These options return here after their own checks.

Apply the [firewall policy](network/firewall.md), using the
[UniFi translation](network/unifi.md) where applicable. Verify permitted
and denied paths; cluster membership alone is not evidence of HA.

Keep persistent local host logs from first boot and export network-device logs where
supported. Preserve these early records until the Stage 2 collector can receive them;
central collection must not wait for FreeIPA or Kubernetes.

## Step 1: Create the first Linux template manually

Use the [common VM template guide](proxmox/templates.md) to download/verify an
approved AlmaLinux or Rocky Linux cloud image on the independent workstation,
upload it through the Proxmox GUI and create the unbooted template. Clone-test
it before using it as the bootstrap VM's source. No generated repository,
Terraform API token or running GitLab is needed for this manual first image.

Only one Linux template is needed here. Talos and other image candidates can
be added from the bootstrap host in Step 3. Existing accepted templates are
valid; do not rebuild them merely to follow the path.

<a id="step-2-protect-provisioning-access-and-state"></a>

## Step 2: Prepare the bootstrap execution host

Follow [bootstrap execution host, Steps 1-3](proxmox/bootstrap.md): clone
`bootstrap-1` onto the protected `management` network, install tools, obtain the kit,
generate/restore the collection and stage approved image artifacts. An already
accepted privileged Linux workstation may perform the same execution role instead.
Install the verified **Proxmox cluster CA on that execution host**, then configure
[scoped API access](proxmox/api-access.md); the earlier GUI browser's trust is not sufficient.

Use protected local state or an independent backend. Back up local state, inventory and bootstrap inputs now;
test their recovery before provisioning. Prepare the
[backup destination](../../administration/compute/backup-restore.md), using PBS or
a verified existing service. Guest backup/restore follows the first disposable clone in Step 3.
Keep code, tools and recovery credentials outside the systems being created.

A bootstrap VM cannot replace recovery access outside Proxmox.
Software supply must work independently of future platform services; an existing
mirror or approved offline artifacts are valid inputs.
Select the [software-intake design](../../architecture/delivery/software-intake.md):
controlled proxy access can serve connected clients in every tier, while retained
mirrors or offline copies provide independent approved content.

## Step 3: Publish and test VM templates

**Complete template import/publication here, before Stage 1: Software intake.**
Run these commands on the accepted execution host (`bootstrap-1` in the VM path),
from the generated Tier 0 repository root. No hosted CI or cluster is required.

1. Initialize local inputs; existing files are preserved:

   ```bash
   bash scripts/proxmox-templates.sh init
   ```

   Edit `templates/proxmox.yml` and `.env.local`. Keep only selected images and
   record their actual VMIDs, names, node, storage, unpacked artifact paths and hashes.
   Common template defaults are `bridge: vmbr0` and `memory_mb: 2048`; each build
   can override them. Set the common `vlan_id` under `all:`; the starter's VLAN 10
   is an example. MTU 1500, NIC firewall enabled and OS-specific SCSI are automatic.
   For adoption, match existing hardware rather than imposing
   new defaults, and set `image_file_name` to the exact existing Import basename.
   See the [catalog fields](../../administration/compute/template-lifecycle.md#catalog-fields-and-defaults).

2. Choose **one** planning command for this catalog:

   | Starting point | Command | Detailed guide |
   | --- | --- | --- |
   | Any catalogued templates or image files already exist, including the first manual template | `bash scripts/proxmox-templates.sh import --env-file .env.local` | [Adopt existing templates](../../administration/compute/template-lifecycle.md#adopt-existing-templates) |
   | All catalogued resources are new | `bash scripts/proxmox-templates.sh plan --env-file .env.local` | [Publish new templates](../../administration/compute/template-lifecycle.md#local-workflow) |

   `import` prepares a saved adoption plan; it does not write state yet. Missing
   resources can still be planned as creations. Do not run a normal plan over
   the adoption plan before applying it.

3. Review imports **and all changes**. Stop on unexpected hardware updates,
   replacements or deletion; align the catalog first. Apply only the accepted plan:

   ```bash
   bash scripts/proxmox-templates.sh apply --env-file .env.local
   bash scripts/proxmox-templates.sh verify --env-file .env.local
   ```

   Rerun `bash scripts/proxmox-templates.sh plan --env-file .env.local` and check
   for the expected no-change result. Continue with the clone tests below.

   Apply completes [fixed RAM and empty template accounts](../../administration/compute/template-lifecycle.md#verify-fixed-ram-after-adoption)
   through native API modules, preserving the CloudInit drive and DHCP. The separate
   verification command checks raw settings that the pinned provider may miss.

Adoption does not enroll the
bootstrap VM itself into Terraform. Use the [common image guide](proxmox/templates.md) for AlmaLinux, Rocky Linux and
Talos artifact/firmware choices. Add the Kubernetes node image here when needed.
Tier 0 publishes templates; other tiers consume approved references.
Adoption retains an existing template's OS disk. For an intentional disk-image
replacement at the same VMID, use the separate
[boot-disk maintenance path](../../administration/compute/template-disk.md)
after applying the reviewed publication plan.

Publication code and inputs are in Tier 0's
[terraform/deployments/templates/](../../../tier-0/terraform/deployments/templates) and
[templates/proxmox.yml.example](../../../tier-0/templates/proxmox.yml.example).
Approved consumer references are in Shared's
[templates/proxmox-catalog.tfvars](../../../shared/templates/proxmox-catalog.tfvars).

Qualify the [Linux guest security profile](proxmox/host-security.md) on the disposable clone.
Each later Linux deployment applies its tier-owned operator/service allowlist before acceptance;
Talos and Proxmox retain their own native security configuration. The generic baseline alone is not hardening.

Boot disposable clones and verify disks, network and access before creating service
VMs. Back up and restore a disposable clone, including every required data disk,
through the [backup procedure](../../administration/compute/backup-restore.md#quick-steps)
before important guests depend on that path.
After its VM prerequisites exist, deploy the separate
[Software intake capability](../stage-1-software-intake/README.md) when controlled update
access is needed. Keep its initial software supply independent of the cache being deployed.

Before the later Kubernetes stage starts Flux, provide a reachable approved Git or OCI
source with independent credentials. A local checkout is not itself a reachable Flux source.

<a id="capability-available"></a>

## Foundation ready

**Result:** independently recoverable virtualization with tested templates and enforced
network boundaries, realizing the compute portion of the
[reference platform](../../architecture/reference-platform.md#service-placement).

Record template boot, network allow/deny and state-restore evidence. Begin numbered
deployment with [Stage 1: Software intake](../stage-1-software-intake/README.md),
then [Stage 2: Protected logging](../stage-2-logging/README.md), before PKI,
FreeIPA or Kubernetes. Logging can start as soon as one approved Linux template and supply path are ready;
it does not wait for every optional foundation variant.
