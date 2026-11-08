# Deploy Kubernetes with Talos: Terraform

**Working repository:** select Tier 0, Tier 1 or Tier 2 in the
[cluster repository map](kubernetes.md#repository-locations). Stage 4 uses `<prefix>-tier-0`.
Run commands from the selected tier's root; Shared is not the cluster's working directory.

**Design:** [cluster runtime variants](../../../architecture/hosting/README.md).

This is the current Talos implementation of the [Kubernetes cluster goal](kubernetes.md).
Each tier owns its cluster VMs, inventory, Talos configuration, bootstrap,
credentials, and state. Shared supplies the stateless command, approved template
references and size profiles. This workflow creates a **new cluster**, not an adoption or restore.
For manual installation, use the [operator procedure](../step-1b-manual-cluster.md).

## Table of contents

- [Prerequisites](#prerequisites)
- [Step 1: Initialize and edit inputs](#configure)
- [Step 2: Prepare node configuration](#controlled-image-access)
- [Step 3: Plan and deploy](#plan-and-deploy)
- [Step 4: Install the platform](#install-the-platform)
- [Step 5: Verify and hand over](#verify-and-hand-over)
- [State and lifecycle](#state-and-lifecycle)
- [Worker capacity](#worker-capacity)
- [References](#references)

## Prerequisites

Work from the owning tier's repository root in Bash on Linux or WSL, using an
independent authorized execution host. Tier 0 recovery must not depend on Tier 1/2.
Install Terraform, matching `talosctl`, and compatible `kubectl`. Provider constraints
and checksums live in `terraform/deployments/kubernetes/`.

- Complete [Proxmox preparation](../../foundation/proxmox/README.md#first-deployment-order),
  optional [HA](../../foundation/step-1b-cluster-ha.md), and [Talos template publication](../../foundation/proxmox/templates.md).
- Approve the template ID, title, and source node in the sibling shared
  [catalog](../../../reference/template-catalog.md). Retain the disk and matching installer image.
- Reserve each VM's inventory IP outside DHCP, and configure `bootstrap_network`
  with its subnet prefix/gateway. A NoCloud drive supplies static network settings,
  not Linux users or Talos machine configuration. Legacy `null` retains DHCP reservations.
  Bootstrap DNS/time and image access must work independently; Terraform does not configure DNS servers.
- Provide an independent Kubernetes API endpoint on TCP 6443. For HA, use a
  load balancer targeting the control-plane IPs; it cannot depend on this cluster's
  ingress or Tier 1 services. Tier 0 supplies an [independent endpoint pair](api-endpoint.md)
  when no qualified existing endpoint is available. Permit the operator to reach node Talos APIs on
  TCP 50000 over a protected bootstrap network. [1]
- Review storage/bridge availability on every eligible Proxmox host and choose
  non-overlapping node, pod, and service networks.

Fresh examples use the [common imported template](../../foundation/proxmox/templates.md):
amd64 NoCloud, UEFI (`ovmf`/`q35`), `virtio-scsi-pci`, `scsi0` installed as `/dev/sda`,
fixed RAM and the schematic's guest agent. A CloudInit drive at `ide2` supplies static
NoCloud networking only. User/password/SSH and other fields remain unset; Talos machine
config uses the native API. The default Talos CNI applies unless patched.
For Tier 0's Cilium path, apply the [native CNI/proxy patches](basic-platform.md#prepare-talos)
before bootstrap. Use native patches below for proxy, DNS/time and mirrors.
Firmware or CNI changes require review before deployment. Enable the guest agent only
if the image includes it. [1]

`bootstrap_network` selects the static prefix/gateway; IPs come from the existing
inventory map. DNS fields are left at Proxmox defaults unless `dns_servers` is
explicitly supplied. Qualify those defaults before bootstrap. A null input keeps
the previous DHCP path without adding a drive to existing VMs automatically.

Match `vm_firmware` to the approved template before creating VMs. Existing inputs
without it retain BIOS/Single-controller defaults; a refresh is not a firmware
migration. Do not apply a new UEFI profile to existing nodes without a reviewed
replacement/recovery plan. The EFI volume lives on each node's selected live datastore.

<a id="configure"></a>

## Step 1: Initialize and edit inputs

```bash
# Run from the selected cluster owner: <prefix>-tier-0/, <prefix>-tier-1/ or <prefix>-tier-2/.
bash scripts/kubernetes-cluster.sh init
```

Initialization copies missing examples only. Existing files are never overwritten
or merged; add the Talos groups from the inventory example when upgrading.

For an existing applied SDN subnet, select
[`bootstrap_network.sdn_vnet`](../../../reference/network-inputs.md#sdn-subnet-lookup)
instead of repeating prefix/gateway values. Node IPs remain in this tier's group vars;
all node bridges must select that VNet with no additional VLAN tag.

Edit these files:

```text
# Edit in the selected cluster owner: <prefix>-tier-0/, <prefix>-tier-1/ or <prefix>-tier-2/.
ansible/inventory/hosts.yml
# Edit: Retain/add control planes and workers under talos_control_plane / talos_workers, both under talos.
#       Tier 0 starts with k8ctl-1/2/3; retain the other tiers' own host keys.
ansible/group_vars/talos.yml
# Edit: One reserved platform_host_ips address for every node.
terraform/deployments/kubernetes/terraform.tfvars
# Edit: The fields below; this root does not read Linux common.tfvars.
```

Shared supplies [common sizes](../../../../shared/config/guest-sizes.json), read directly by
tier-local Terraform, and [approved image metadata](../../../../shared/templates/proxmox-catalog.tfvars),
loaded by the command. Resource definitions, inventory and state remain in the selected tier.

Edit **`terraform/deployments/kubernetes/terraform.tfvars`**:

| Field | Set before first bootstrap |
| --- | --- |
| `template_vm_id`, `vm_firmware`, `qemu_agent` | Approved Talos template VMID and matching firmware/agent; not the Linux default |
| `cluster.endpoint` | Verified private endpoint DNS/VIP from the preceding endpoint procedure, including `https://` and `:6443` |
| `cluster.talos_version`, `cluster.kubernetes_version`, `cluster.installer_image` | Exact compatible release pins and NoCloud installer matching the template schematic |
| `cluster.pod_cidr`, `cluster.service_cidr` | Networks that do not overlap nodes, site routes or other required peers |
| `nodes` | Each inventory key's unused VMID from the [allocation plan](../../../conventions/vmid-convention.md), real initial Proxmox host, unique MAC, actual live `datastore_id`, bridge and size |
| `bootstrap_network` | Actual prefix/gateway, or `sdn_vnet` for applied lookup; add `dns_servers` only for an independent bootstrap resolver override |
| `machine_config_patches` | Ordered image-access, CNI and logging patches prepared in Step 2; retain every required patch |

Every Talos inventory host must have one hardware entry and one reserved IPv4
address. Each new-cluster example starts with three schedulable control-plane
VMs and no workers; review capacity and failure domains for the services.
Existing clusters retain their local worker definitions and scheduling settings.
Talos names are these inventory keys; Linux hostname prefix/suffix settings are not applied.
The selected native schema uses one `HostnameConfig` document with that exact name
and automatic naming disabled; do not add a legacy `machine.network.hostname`
patch beside it. Native configuration tests qualify the reference Talos 1.13 path.
Other release/schema choices need their own complete-config validation, not only
a syntactically valid version string.

For existing clusters, review this configuration change against the original state
and live configuration before any apply. Preserve node identities and all ordered
patches; a code refresh is not an automatic OS/schema migration. Bootstrap commands
are not a health-gated parallel upgrade procedure.

| Tier | Starter attachment | IP reservations | Manifest path |
| --- | --- | --- | --- |
| 0 | `control` VNet | `10.10.13.10-12` | `clusters/tier0/` |
| 1 | `app` VNet | `10.20.20.110-112` | `clusters/tier1/` |
| 2 | `vmbr0`, VLAN 420 | `10.42.20.10-12` | `clusters/tier2/` |

These are reviewed example allocations from the [network map](../../../architecture/networking/README.md#example-network-plan).
Create the selected attachment on every eligible Proxmox node before planning.

Supply `PROXMOX_VE_ENDPOINT` and `PROXMOX_VE_API_TOKEN` through the protected
shell/runner environment. Use a trusted Proxmox TLS certificate. This command
does not load `.env.local`, Linux `common.tfvars`, or Linux environment overlays.
Talos never runs through the Linux `deploy.sh`/Ansible workflow.

On the independent execution host, load the already configured owning tier's local
environment and export the provider's native names. Run in a protected shell;
never enable shell tracing or print token values:

```bash
# Run from the selected cluster owner: <prefix>-tier-0/, <prefix>-tier-1/ or <prefix>-tier-2/.
set -a
source .env.local
set +a
export PROXMOX_VE_ENDPOINT="${PROXMOX_API_URL:?Set the real Proxmox API URL}"
export PROXMOX_VE_API_TOKEN="${PROXMOX_API_TOKEN_ID:?Set the token ID}=${PROXMOX_API_TOKEN_SECRET:?Set the token secret}"
```

An approved CI job may inject the two native provider variables directly instead.
Retain the trusted-CA configuration used for template publication; do not bypass TLS.

<a id="controlled-image-access"></a>

## Step 2: Prepare node configuration

Before creating any nodes, complete these tasks in order:

1. Add the [controlled image-access patch](image-access.md#configure-node-access)
   for the selected proxy or existing mirror. Qualify required bootstrap artifacts.
2. Append the [Cilium/KubePrism patch](basic-platform.md#prepare-talos) for the actual
   Talos schema. Do not replace the entire patch list with that one example.
3. [Configure and render cluster logging](security-logging.md#configure-and-render).
   Copy its two generated Talos patches into `machine_config_patches` as additional
   YAML heredoc strings; preserve proxy/CNI patches. Validate the complete merged
   configuration with the matching Talos CLI before applying.

Rendering the logging inputs requires chart access, not a live cluster. Its
collectors and enrollment are completed after CNI installation, in Step 4.

Before planning, configure the [node image-access procedure](image-access.md).
Each tier's `machine_config_patches` input appends native Talos patches after its
base configuration. The default `[]` preserves existing behavior; it does not
establish restricted-network connectivity. Linux proxy settings are not inherited.
The provider merges patches; review their final effect and keep internal API,
node and service traffic outside the proxy. This input is not an installer for
a registry, resolver, time service or firewall policy.

<a id="plan-and-deploy"></a>

## Step 3: Plan and deploy

```bash
# Run from the selected cluster owner: <prefix>-tier-0/, <prefix>-tier-1/ or <prefix>-tier-2/.
bash scripts/kubernetes-cluster.sh plan
```

Review every VMID, source template, initial host, disk, MAC, endpoint, and secret
resource before continuing. A failed re-plan removes the saved plan so an older
plan cannot be applied accidentally.

```bash
# Run from the selected cluster owner: <prefix>-tier-0/, <prefix>-tier-1/ or <prefix>-tier-2/.
bash scripts/kubernetes-cluster.sh apply
bash scripts/kubernetes-cluster.sh credentials
```

`apply` requires the saved plan. Terraform clones the VMs, generates cluster
secrets and per-node configurations, applies them through the Talos API, then
bootstraps Kubernetes once on the selected control-plane node. [2]
Initial configuration uses maintenance mode; protect that network from untrusted clients.

Unlike Linux `deploy.sh`, this helper **requires** the separate saved-plan step.
Applying a saved plan does not ask Terraform's interactive `yes` question. In CI,
gate the apply job on approval of that exact protected plan; there is no additional
`--auto-approve` option for this script.

| Action | Side effects |
| --- | --- |
| `init` | Seed missing local input files; no infrastructure access |
| `plan` | Initialize providers/local backend, validate, refresh, and save `.terraform/plans/talos.tfplan` |
| `apply` | Apply the reviewed saved plan; remove it after success |
| `credentials` | Export client files and per-node configurations to ignored `secrets/talos/` |

<a id="install-the-platform"></a>

## Step 4: Install the platform

1. Export the client paths from the Tier 0 repository root:

   ```bash
   # Run from the selected cluster owner: <prefix>-tier-0/, <prefix>-tier-1/ or <prefix>-tier-2/.
   export TALOSCONFIG="$PWD/secrets/talos/talosconfig"
   export KUBECONFIG="$PWD/secrets/talos/kubeconfig"
   kubectl get --raw='/readyz'
   ```

2. Complete [basic platform Steps 2-3](basic-platform.md#configure): install Cilium
   first, then prepare Flux/SOPS and install the remaining selected products.
3. Return to [cluster logging](security-logging.md#enroll-node-streams) to enroll
   node identities, install collectors and test delivery at Tier 0 intake.

<a id="verify-and-hand-over"></a>

## Step 5: Verify and hand over

```bash
# Run from the selected cluster owner: <prefix>-tier-0/, <prefix>-tier-1/ or <prefix>-tier-2/.
export TALOSCONFIG="$PWD/secrets/talos/talosconfig"
export KUBECONFIG="$PWD/secrets/talos/kubeconfig"
talosctl health
kubectl get nodes -o wide
kubectl get pods -A
```

With CNI disabled for Cilium, nodes/DNS can remain unready until the
[network installer](basic-platform.md#render-and-apply) runs; API access must already work.
After installation, stop on unhealthy nodes or system pods. Confirm the independent API endpoint,
CNI, and [failover checks](../../foundation/step-1b-cluster-ha.md#prove-failover) before services
depend on this cluster. Terraform completion alone does not prove readiness.

Continue with the [cluster-foundation checklist](kubernetes.md#cluster-foundation).
Tier 0 uses Flux against `clusters/tier0/`. Tier 1 selects Argo CD or Spinnaker
separately; Tier 2 consumes scoped application delivery or a local controller.
The supplied manifest directories remain placeholders; Tier 0's Ansible platform
installer is their separate installation path.
FreeIPA remains on the two dedicated Tier 0 Linux VMs; Keycloak is a later Tier 0 service.

## State and lifecycle

| Artifact | Tier-local path |
| --- | --- |
| Authoritative bootstrap state | `.terraform/state/talos/terraform.tfstate` |
| Provider/module working data | `.terraform/data/talos/` |
| Client credentials and per-node recovery configs | `secrets/talos/` |

The public command and root use Kubernetes names. The `talos` state, plan,
working-data, inventory-group, and credential names are retained for compatibility
with the existing implementation; the rename does not move state or replace
resources. Tier 0's `scripts/talos-cluster.sh` delegates to the current command. Existing
collections must follow the [layout upgrade](../../../development/generated-repositories.md#terraform-layout-upgrade)
before using either command.

State and saved plans contain private keys and machine secrets; marking outputs
sensitive does **not** encrypt these files. [3] Restrict filesystem access and
encrypt backups outside the cluster. The wrapper uses `umask 077`; verify Windows
ACLs as well when using WSL. Keep one state owner and serialized operations.
For a remote backend, deliberately adapt the root and wrapper and migrate this
existing state; the supplied command configures a local backend.

VMs, cluster secrets, and bootstrap carry `prevent_destroy` guards. Proxmox owns
later VM placement; Terraform ignores node moves, not other hardware changes.
These guards are not backups and do not survive removal of their resource blocks.

This is **not a rolling upgrade controller**. Configuration changes use Talos
`auto` apply mode and may reboot multiple nodes. Do not use a broad apply for
reboot-requiring updates; plan a health-gated, one-node-at-a-time maintenance
procedure. Changing the installer reference is not an OS upgrade workflow. [2]
Use release-matched Talos upgrade and recovery procedures, with etcd and workload backups.

Never initialize replacement state or regenerate secrets for an existing cluster.
Restore its state and recovery material. Existing manually built clusters need
an explicit resource/secret adoption plan before using this root; see
[Recovery](../step-1b-manual-cluster.md#recovery) and the [repository upgrade notes](../../../development/generated-repositories.md#automation-ownership-upgrade).

## Worker capacity

Add workers explicitly to the owning tier's inventory, IP map and `nodes` map.
Optional `pool = "compute"` emits `node-pool=compute`; Tier 1 may use infrastructure,
stateful or compute pools, and Tier 2 development, testing or lab pools. No nodes
are automatically scaled. Use the [pool operations](../../../administration/kubernetes-pools.md)
for selectors, taints and transition checks. Do not remove existing workers simply
to match a newer example. `allow_scheduling_on_control_planes` defaults to false
for existing input objects; new compact examples explicitly set it to true.

## References

Official guidance checked 2026-09-24; select Talos documentation matching the pinned release.

1. [Talos on Proxmox](https://docs.siderolabs.com/talos/v1.13/platform-specific-installations/virtualized-platforms/proxmox).
2. [Talos provider configuration apply](https://github.com/siderolabs/terraform-provider-talos/blob/v0.11.0/docs/resources/machine_configuration_apply.md).
3. [Terraform sensitive data in state](https://developer.hashicorp.com/terraform/language/state/sensitive-data).
