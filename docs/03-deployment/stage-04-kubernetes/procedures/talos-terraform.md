# Deploy Kubernetes with Talos: Terraform

**Working repository:** select Tier 0, Tier 1 or Tier 2 in the
[cluster repository map](kubernetes.md#repository-locations). Stage 4 uses `<prefix>-tier-0`.
Run commands from the selected tier's root; Shared is not the cluster's working directory.

**Design:** [cluster runtime variants](../../../01-architecture/04-hosting/README.md).

For the continuous Tier 0 installation, follow [Stage 4, actions 1-20](../README.md).
This reusable cross-tier procedure owns the native node lifecycle; it is not another installer to run afterward.

This is the current Talos implementation of the [Kubernetes cluster goal](kubernetes.md).
Each tier owns its cluster VMs, inventory, Talos configuration, bootstrap,
credentials, and state. Shared supplies the stateless command, approved template
references and size profiles. This workflow creates a **new cluster**, not an adoption or restore.
To consume an existing cluster, use the [adoption procedure](../step-1b-existing-cluster.md).

[Stage 4 Figure 1](../README.md#figure-1-control-cluster-runtime) shows the Tier 0 starter's three
control-plane VMs and independent API endpoint. Later tiers select their own nodes and state.

> [!TIP]
> **Recovery and maintenance:** [Change cluster capacity](../../../05-operations/01-hosting/kubernetes-and-labs.md),
> [update Talos](../../../05-operations/01-hosting/maintenance.md#talos-updates), or
> [restore original cluster state](../../../05-operations/06-resilience/recovery/original-state-etcd.md).

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

For the complete Tier 0 reference through Stage 5, select the approved exact **Talos 1.13.x**
release from the [Foundation version contract](../../foundation/proxmox/templates.md#talos-version-contract).
The example's version placeholders do not select that minor automatically. Keep the image,
installer, `cluster.talos_version`, CLI and logging schema consistent before planning.
Talos 1.14 requires separate full-platform/SSO qualification, not just a different version string.

- Complete [Proxmox preparation](../../foundation/proxmox/README.md#first-deployment-order) and
  selected [HA preparation](../../foundation/proxmox/step-1b-cluster-ha.md).
- Choose the [fresh signed ISO installation](secure-boot.md) for new permanent nodes. Retain its
  approved local ISO/hash and matching signed NoCloud installer. The retained template option uses
  [Talos template publication](../../foundation/proxmox/templates.md) and an approved template
  ID/title/source node in the sibling Shared [catalog](../../../08-reference/template-catalog.md).
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

The signed ISO path creates fresh EFI/TPM state and blank OS disks. The retained template path
uses an approved amd64 NoCloud disk and its recorded firmware. Both use `scsi0` installed as
`/dev/sda`, fixed RAM and the schematic's guest agent. A CloudInit drive at `ide2` supplies static
NoCloud networking. Talos machine configuration uses the native API. The default CNI applies unless patched.
For Tier 0's Cilium path, apply the [native CNI/proxy patches](basic-platform.md#prepare-talos)
before bootstrap. Use native patches below for proxy, DNS/time and mirrors.
Firmware or CNI changes require review before deployment. Enable the guest agent only
if the image includes it. [1]

`bootstrap_network` selects the static prefix/gateway; IPs come from the existing
inventory map. DNS fields are left at Proxmox defaults unless `dns_servers` is
explicitly supplied. Qualify those defaults before bootstrap. A null input keeps
the previous DHCP path without adding a drive to existing VMs automatically.

Match `vm_firmware` to the selected installation before creating VMs. Signed ISO installs require
OVMF/q35/`virtio-scsi-pci`. Existing template inputs
without it retain BIOS/Single-controller defaults; a refresh is not a firmware
migration. Do not apply a new UEFI profile to existing nodes without a reviewed
replacement/recovery plan. The EFI volume lives on each node's selected live datastore.

<a id="configure"></a>

## Step 1: Initialize and edit inputs

### 1. Initialize this tier's cluster inputs

Run from the selected cluster owner: **`<prefix>-tier-0/`**, `<prefix>-tier-1/` or `<prefix>-tier-2/`.

```bash
bash scripts/kubernetes-cluster.sh init
```

Initialization copies missing examples only. Existing files are never overwritten
or merged; add the Talos groups from the inventory example when upgrading.

### 2. Edit inventory, addresses and hardware

For an existing applied SDN subnet, select
[`bootstrap_network.sdn_vnet`](../../../08-reference/network-inputs.md#sdn-subnet-lookup)
instead of repeating prefix/gateway values. Node IPs remain in this tier's group vars;
all node bridges must select that VNet with no additional VLAN tag.

Edit in the selected cluster owner: **`<prefix>-tier-0/`**, **`<prefix>-tier-1/`** or **`<prefix>-tier-2/`**.

- `ansible/inventory/hosts.yml`: Retain/add control planes and workers under `talos_control_plane` /
  `talos_workers`, both under talos. Tier 0 starts with k8ctl-1/2/3; retain the other tiers' own host keys.
- `ansible/group_vars/talos.yml`: One reserved `platform_host_ips` address for every node.
- `terraform/deployments/kubernetes/terraform.tfvars`: The fields below; this root does not read Linux
  common.tfvars.

Shared supplies [common sizes](../../../../shared/config/guest-sizes.json), read directly by
tier-local Terraform, and [approved image metadata](../../../../shared/templates/proxmox-catalog.tfvars),
loaded by the command. Resource definitions, inventory and state remain in the selected tier.

Edit **`terraform/deployments/kubernetes/terraform.tfvars`**:

| Field | Set before first bootstrap |
| --- | --- |
| `template_vm_id`, `secure_boot`, `vm_firmware`, `qemu_agent` | Choose the signed fresh-install contract below or the retained template/firmware contract |
| `cluster.endpoint` | Verified private endpoint DNS/VIP from the preceding endpoint procedure, including `https://` and `:6443` |
| `cluster.talos_version`, `cluster.kubernetes_version`, `cluster.installer_image` | Exact compatible release pins and the chosen ordinary or Secure Boot NoCloud installer, matching the image schematic |
| `cluster.pod_cidr`, `cluster.service_cidr` | Networks that do not overlap nodes, site routes or other required peers |
| `nodes` | Each inventory key's unused VMID from the [allocation plan](../../../02-conventions/vmid-convention.md), real initial Proxmox host, unique MAC, actual live `datastore_id`, bridge and size |
| `bootstrap_network` | Actual prefix/gateway, or `sdn_vnet` for applied lookup; add `dns_servers` only for an independent bootstrap resolver override |
| `machine_config_patches` | Ordered image-access, CNI and logging patches prepared in Step 2; retain every required patch |

Choose the boot contract before first provisioning.

| Choice | Exact inputs |
| --- | --- |
| **Fresh signed ISO — recommended** | `template_vm_id = null`; `vm_firmware` selects `ovmf`, `q35`, `virtio-scsi-pci`; `secure_boot.iso_path` is the absolute local verified ISO, `iso_sha256` its lowercase 64-character digest and `iso_datastore_id` ISO-capable storage. `encrypt_system_disks` and `install_media_attached` default to `true` |
| **Retained template** | `secure_boot = null`; approved Talos `template_vm_id` and its recorded firmware/agent profile |

For signed installation, use `factory.talos.dev/nocloud-installer-secureboot/<schematic>:v1.13.x`
with the exact approved patch release and schematic. Terraform checks the local media hash and
discovers whether its ISO datastore is shared or local on the selected nodes. It creates a fresh
TPM 2.0 for every node. The selected system-disk encryption configures STATE and EPHEMERAL at first
provisioning. Follow the [signed-media procedure](secure-boot.md) for acquisition and acceptance.

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

These are reviewed example allocations from the [network map](../../../01-architecture/05-networking/README.md#example-network-plan).
Create the selected attachment on every eligible Proxmox node before planning.

### 3. Load this tier's API credentials

Supply `PROXMOX_VE_ENDPOINT` and `PROXMOX_VE_API_TOKEN` through the protected
shell/runner environment. Use a trusted Proxmox TLS certificate. This command
does not load `.env.local`, Linux `common.tfvars`, or Linux environment overlays.
Talos never runs through the Linux `deploy.sh`/Ansible workflow.

On the independent execution host, load the already configured owning tier's local
environment and export the provider's native names. Run in a protected shell;
never enable shell tracing or print token values:

Run from the selected cluster owner: **`<prefix>-tier-0/`**, **`<prefix>-tier-1/`** or **`<prefix>-tier-2/`**.

```bash
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

Complete actions 4–6 before creating nodes. Each adds to the **same** ordered
`machine_config_patches` in the selected tier's `terraform/deployments/kubernetes/terraform.tfvars`.

### 4. Add image access

In **the selected tier's inputs**, add the [controlled image-access patch](image-access.md#configure-node-access)
for the accepted proxy or existing mirror, then return here. Qualify required bootstrap artifacts.

### 5. Add the Cilium node settings

In **the same patch list**, append the [Cilium/KubePrism patch](basic-platform.md#prepare-talos)
for the actual Talos schema. Preserve image-access and other existing patches.

If selecting Ceph RBD CSI, append its [native RBD preparation](basic-platform.md#ceph-rbd-node-preparation-when-selected)
to this same list before bootstrap. An existing CSI selection uses its accepted node requirements.

### 6. Render and add the security-logging patches

From **the selected tier root**, complete [cluster logging Steps 1–3](security-logging.md#configure-and-render).
Append both generated Talos patches as YAML heredoc strings, preserving proxy/CNI entries.
Validate the complete merged configuration with the matching Talos CLI, then return here.

Rendering the logging inputs requires chart access, not a live cluster. Its
collectors and enrollment are completed after CNI installation, in Step 4.

Each tier's `machine_config_patches` input appends native Talos patches after its
base configuration. The default `[]` preserves existing behavior; it does not
establish restricted-network connectivity. Linux proxy settings are not inherited.
The provider merges patches; review their final effect and keep internal API,
node and service traffic outside the proxy. This input is not an installer for
a registry, resolver, time service or firewall policy.

<a id="plan-and-deploy"></a>

## Step 3: Plan and deploy

### 7. Save and review the plan

Run from the selected cluster owner: **`<prefix>-tier-0/`**, `<prefix>-tier-1/` or `<prefix>-tier-2/`.

```bash
bash scripts/kubernetes-cluster.sh plan
```

Review every VMID, chosen boot artifact, initial host, disk, EFI/TPM state, MAC, endpoint and secret
resource before continuing. A failed re-plan removes the saved plan so an older
plan cannot be applied accidentally.

### 8. Apply that exact plan

Run from the selected cluster owner: **`<prefix>-tier-0/`**, **`<prefix>-tier-1/`** or **`<prefix>-tier-2/`**.

```bash
bash scripts/kubernetes-cluster.sh apply
```

`apply` requires the saved plan. Terraform creates signed-path VMs or clones retained-path VMs, generates cluster
secrets and per-node configurations, applies them through the Talos API, then
bootstraps Kubernetes once on the selected control-plane node. [2]
Initial configuration uses maintenance mode; protect that network from untrusted clients.
For the signed path, apply then checks every node's authenticated Secure Boot/UKI state and the
selected STATE/EPHEMERAL encryption. Resolve failed checks before continuing to the platform.

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
| `verify-security` | Recheck authenticated Secure Boot/UKI and selected TPM-bound system volumes for signed-path nodes; report the retained policy for template-path nodes |

### 9. Export the credentials

After apply succeeds, run from **the same selected tier root**:

```bash
bash scripts/kubernetes-cluster.sh credentials
```

**Expected:** protected client files and per-node configurations under `secrets/talos/`.
Keep them and the original Terraform state in independent recovery custody before continuing.
For signed nodes, follow the signed guide's [media ejection and controlled installed-disk checks](secure-boot.md#5-eject-installation-media-and-capture-recovery).
Set `secure_boot.install_media_attached = false` through the same reviewed plan/apply sequence.

<a id="install-the-platform"></a>

## Step 4: Continue the owning stage

**Stage 4 first install:** continue at [action 11](../README.md#step-11-configure-the-platform-target)
with the already exported credentials. Its actions 11-19 own CNI, collection, storage and the remaining
platform in order. Do not also run the cross-tier continuation below.

**Other cluster owners:** use the following sequence only when the owning stage calls this reusable procedure.

For **Tier 1 Flux ownership**, complete [platform bootstrap/handover actions 7–9](../../stage-07-delivery/procedures/platform-cluster.md#7-select-the-basic-platform),
including protected collector publication, then continue at [Step 5](#verify-and-hand-over).
For Ansible-owned add-ons, follow actions 10–13 below.

### 10. Select the exported client files

Run from the selected cluster owner: **`<prefix>-tier-0/`**, **`<prefix>-tier-1/`** or **`<prefix>-tier-2/`**.

```bash
export TALOSCONFIG="$PWD/secrets/talos/talosconfig"
export KUBECONFIG="$PWD/secrets/talos/kubeconfig"
kubectl get --raw='/readyz'
```

**Expected:** private API access works. Nodes/CoreDNS can remain unready until Cilium is installed.

<a id="11-install-cni-and-the-selected-platform-services"></a>

### 11. Install CNI first

From **the same tier root**, complete [basic platform Step 2](basic-platform.md#configure), then
[actions 5–7](basic-platform.md#5-render-cilium-only) to render/review/apply Cilium and verify nodes/DNS.
Stop before the remaining platform apply and continue below.

### 12. Enroll and install cluster log collectors

Complete [cluster logging Steps 4–6](security-logging.md#enroll-node-streams): enroll node identities,
install collectors and verify real events at protected Tier 0 intake. Return here after delivery passes.

### 13. Complete the remaining platform

Qualify the [live CSI/storage prerequisite](basic-platform.md#persistence), then complete
[basic platform action 9](basic-platform.md#8a-prepare-flux-and-managed-bootstrap-secrets--main-path).
Tier 0 prepares Flux/SOPS. Tier 1 uses its [independent Flux bootstrap/handover](../../stage-07-delivery/procedures/platform-cluster.md#7-select-the-basic-platform).
Tier 2 uses its own components and Secret owner. Complete the selected installation once, then continue below.

<a id="verify-and-hand-over"></a>

## Step 5: Verify and hand over

<a id="13-check-the-completed-cluster"></a>

### 14. Check the completed cluster

Run from the selected cluster owner: **`<prefix>-tier-0/`**, **`<prefix>-tier-1/`** or **`<prefix>-tier-2/`**.

```bash
export TALOSCONFIG="$PWD/secrets/talos/talosconfig"
export KUBECONFIG="$PWD/secrets/talos/kubeconfig"
talosctl health
kubectl get nodes -o wide
kubectl get pods -A
```

With CNI disabled for Cilium, nodes/DNS can remain unready until the
[network installer](basic-platform.md#render-and-apply) runs; API access must already work.
After installation, stop on unhealthy nodes or system pods. Confirm the independent API endpoint,
CNI, and [failover checks](../../foundation/proxmox/step-1b-cluster-ha.md#prove-failover) before services
depend on this cluster. Terraform completion alone does not prove readiness.

Continue with the [cluster-foundation checklist](kubernetes.md#cluster-foundation).
Tier 0 uses Flux against `clusters/tier0/`. Tier 1 uses its independent Flux platform source with
Spinnaker application promotion, or an explicitly selected alternative. Tier 2 consumes scoped
application delivery or a local controller. Tier 1's native renderers export selected deployable
payloads. Review and publish those payloads before enabling reconciliation.
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
collections must follow the [layout upgrade](../../../04-development/generated-repositories.md#terraform-layout-upgrade)
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

The wrapper refuses to change existing nodes between template and Secure Boot modes or toggle their
selected system-disk encryption. Use the signed fresh-install/recovery path for that transition.
Keep the original node TPM/EFI state with its coherent backup. If TPM-bound data must be recovered
after losing that state, use the original complete VM recovery set or rebuild nodes and recover
cluster/application data from independent backups.

This is **not a rolling upgrade controller**. Configuration changes use Talos
`auto` apply mode and may reboot multiple nodes. Do not use a broad apply for
reboot-requiring updates; plan a health-gated, one-node-at-a-time maintenance
procedure. Changing the installer reference is not an OS upgrade workflow. [2]
Use release-matched Talos upgrade and recovery procedures, with etcd and workload backups.

Never initialize replacement state or regenerate secrets for an existing cluster.
Restore its state and recovery material. Existing manually built clusters need
an explicit resource/secret adoption plan before using this root; see
[Recovery](../step-1b-existing-cluster.md#recovery) and the [repository upgrade notes](../../../04-development/generated-repositories.md#automation-ownership-upgrade).

## Worker capacity

Add workers explicitly to the owning tier's inventory, IP map and `nodes` map.
Optional `pool = "compute"` emits `node-pool=compute`; Tier 1 may use infrastructure,
stateful or compute pools, and Tier 2 development, testing or lab pools. No nodes
are automatically scaled. Use the [pool operations](../../../05-operations/01-hosting/kubernetes-and-labs.md)
for selectors, taints and transition checks. Do not remove existing workers simply
to match a newer example. `allow_scheduling_on_control_planes` defaults to false
for existing input objects; new compact examples explicitly set it to true.

## References

Official guidance checked 2026-09-24; select Talos documentation matching the pinned release.

1. [Talos on Proxmox](https://docs.siderolabs.com/talos/v1.13/platform-specific-installations/virtualized-platforms/proxmox).
2. [Talos provider configuration apply](https://github.com/siderolabs/terraform-provider-talos/blob/v0.11.0/docs/resources/machine_configuration_apply.md).
3. [Terraform sensitive data in state](https://developer.hashicorp.com/terraform/language/state/sensitive-data).
