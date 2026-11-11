# Step 1b: Manual cluster bootstrap

**Working repository:** the cluster owner's `<prefix>-tier-0`, `<prefix>-tier-1`
or `<prefix>-tier-2` (source: matching `tier-N/`). Stage 4 uses Tier 0;
see the [cluster repository map](procedures/kubernetes.md#repository-locations).

<a id="bootstrap-kubernetes-with-talos"></a>

**Branch from:** [Step 1](README.md#step-1-create-the-kubernetes-cluster), instead of the supplied Terraform cluster lifecycle.
**Change:** Bootstrap Kubernetes manually while retaining one lifecycle owner.
**Return:** [Step 2](README.md#step-2-establish-the-basic-platform) for the common cluster foundation checklist.

**Design:** [cluster runtime variants](../../01-architecture/10-hosting/README.md).

This is the manual Talos implementation of the [Kubernetes cluster goal](procedures/kubernetes.md).
Use this procedure for a Tier 0 control, Tier 1 platform or Tier 2 workload cluster.
Only the owning repo, allocations, credentials, API endpoint, and GitOps path
change. **This is an operator-run bootstrap.** For automated tier-local VM creation
and Talos configuration, start with [Talos Terraform](procedures/talos-terraform.md) instead;
both routes use the verification and handover steps below. Cluster service
directories are starters, not installed services.

**Downstream integration:** the supplied Stage 5 serial SSO recipe requires an original Terraform
plan, so it cannot manage this manual lifecycle. This branch requires a separately qualified native
OIDC rollout/recovery procedure before Stage 5 acceptance. Do not bootstrap Terraform over these nodes
or fabricate a plan to bypass that ownership gate.

## Table of contents

- [Prepare](#prepare)
- [Create VMs](#create-vms)
- [Generate configuration](#generate-configuration)
- [Configure and bootstrap](#configure-and-bootstrap)
- [Verify and hand over](#verify-and-hand-over)
- [Recovery](#recovery)
- [References](#references)

## Prepare

Work from the owning generated repository in Bash on Linux or WSL. Keep that
checkout and the required tools available outside the cluster being built.

| Choice | Tier 0 | Tier 1 |
| --- | --- | --- |
| Repository root | `<prefix>-tier-0` | `<prefix>-tier-1` |
| Automation alternative | [Tier-local Terraform](procedures/talos-terraform.md) in `terraform/deployments/kubernetes/` | Same path in the owning tier |
| GitOps path | `clusters/tier0/` | `clusters/tier1/` |
| Recovery | Independent of higher-tier services | Approved foundation services plus local break-glass inputs |

Tier 2 uses the same workflow with its own repository, API, credentials and
`clusters/tier2/` path; never reuse another tier's machine secrets.

Before starting, have:

- Prepared [Proxmox hosts](../foundation/proxmox/README.md#first-deployment-order), storage,
  guest networks, and optional [HA/SDN](../foundation/proxmox/step-1b-cluster-ha.md).
- A tested [Talos template](../foundation/proxmox/templates.md), its pinned release
  and schematic, and the matching installer image retained for recovery.
  Obtain its approved ID, title, and source node from the [shared catalog](../../08-reference/template-catalog.md).
- Matching `talosctl`, compatible `kubectl`, and the required container images.
- Recorded node IPs, names, VMIDs, API endpoint, and non-overlapping pod/service
  CIDRs. Provide DNS, time, and image access before this cluster exists.

Retain the [approved Talos 1.13.x reference pin](../foundation/proxmox/templates.md#talos-version-contract)
across the template, installer and CLI. Another minor requires complete platform and SSO qualification.

The fast path uses the tested NoCloud template, a **network-only CloudInit drive**
for each clone's static IP/gateway. For the Stage 4 reference, change the generated node configurations to
the [CNI/proxy/KubePrism settings](procedures/basic-platform.md#prepare-talos)
before applying them; the linked Terraform heredoc contains the native YAML.
Do this before first bootstrap, rather than installing the generated default CNI and replacing it later.
Another CNI is a separately qualified platform variant; the supplied Cilium installer is not its migration path.
Keep each clone's NoCloud address distinct; do not add conflicting static addresses
to one common machine-config file. DHCP reservations remain an explicit alternative.
For restricted networks, prepare
image mirrors and discovery/network settings using the matching Talos release
documentation before applying configuration. [1][2]

For HA, prepare an independent TCP load balancer for the Kubernetes API on
port 6443, or use a release-supported endpoint design from the production guide.
It must not depend on ingress inside this new cluster. Tier 0 must not depend on
the public Tier 2 edge service for recovery. A single control-plane IP is
acceptable only for a non-HA pilot. Restrict Talos API port 50000 to authorized
operators and cluster traffic; the Kubernetes endpoint is not a Talos endpoint. [1]

## Create VMs

In the Proxmox UI, make **full clones** of the approved, stopped template with
new VMIDs. Do not boot or configure the reusable template itself.

| Setting | Initial project choice |
| --- | --- |
| Control plane | Three VMs on different physical hosts for HA |
| Workers | Optional for the compact reference; enable control-plane scheduling when no workers exist |
| Suggested sizing | Control plane: 2 vCPU, 4 GiB RAM, 32 GiB disk; workers: 2 vCPU, 4 GiB RAM, 40 GiB disk |
| Storage and network | Reviewed datastore and bridge/VNet available on every eligible destination |
| Firmware, CPU, boot order | Preserve the tested template settings and common host CPU baseline |
| Guest agent | Enable only when the recorded image schematic includes the extension |
| CloudInit drive | Retain/add `ide2`; set only the clone's `IP Config (net0)` static CIDR/gateway, leaving user/password/SSH and other fields at defaults |

Sizing here is a starting allocation, not a capacity guarantee. Record the
actual VMIDs and attachments in project inventory. Boot the clones into
maintenance mode and record their console-reported IPs. [2]
Use the [common template guide](../foundation/proxmox/templates.md) for the exact GUI path.
Inherited DNS must work without this cluster; commission independent defaults before boot.

Do **not** use the Linux cloud-init VM module or `deploy.sh` to configure Talos.
When replacing manual VM creation with Terraform later, explicitly import and
review existing resources; an empty state is not an adoption plan.

## Generate configuration

For a **new cluster only**, run this from the owning repo root. Prompts keep
project-specific addresses and image references out of the copied command.
Use the exact installer reference matching the template schematic and release,
not the raw disk download URL. [3]

Run from **`<prefix>-tier-0/`**.

```bash
read -r -p "Cluster name: " CLUSTER_NAME
read -r -p "Kubernetes API URL (https://name:6443): " KUBERNETES_ENDPOINT
read -r -p "Approved installer image with exact tag or digest: " INSTALLER_IMAGE
read -r -p "Compatible Kubernetes version: " KUBERNETES_VERSION
export CLUSTER_DIR="$PWD/secrets/$CLUSTER_NAME"
(
  set -eu
  test -n "$CLUSTER_NAME" && test -n "$KUBERNETES_ENDPOINT"
  test -n "$INSTALLER_IMAGE" && test -n "$KUBERNETES_VERSION"
  umask 077
  mkdir -p "$CLUSTER_DIR"
  talosctl gen secrets -o "$CLUSTER_DIR/secrets.yaml"
  talosctl gen config "$CLUSTER_NAME" "$KUBERNETES_ENDPOINT" \
    --with-secrets "$CLUSTER_DIR/secrets.yaml" \
    --install-image "$INSTALLER_IMAGE" --kubernetes-version "$KUBERNETES_VERSION" \
    --output "$CLUSTER_DIR"
)
```

Stop if any command fails. Do not use `--force` to overwrite an existing
cluster's secrets; restore its recovery material instead. `secrets/` is ignored
by the generated repositories, but still needs protected external backup.

Review `controlplane.yaml`, `worker.yaml`, and `talosconfig`. Check installation
disk, endpoint, DNS/time, address ranges, image access, and CNI settings before
continuing. The empty `infrastructure/cni/` directory installs nothing.

Create a separate reviewed machine file for each node from its role's generated file.
For the reference control planes, run from **the owning tier's root** in the same shell:

```bash
cp -n "$CLUSTER_DIR/controlplane.yaml" "$CLUSTER_DIR/k8ctl-1.yaml"
cp -n "$CLUSTER_DIR/controlplane.yaml" "$CLUSTER_DIR/k8ctl-2.yaml"
cp -n "$CLUSTER_DIR/controlplane.yaml" "$CLUSTER_DIR/k8ctl-3.yaml"
```

For the reference Talos 1.13 schema, append one native hostname document per node,
matching the names selected in the logging inputs. For `k8ctl-1`, use:

```yaml
---
apiVersion: v1alpha1
kind: HostnameConfig
hostname: k8ctl-1
auto: "off"
```

Use each node's own hostname in its own file. Do not apply `k8ctl-1`'s completed file to every
control plane. This matches the [Terraform realization](../../../tier-0/terraform/deployments/kubernetes/machines.tf);
do not add a conflicting legacy `machine.network.hostname` field. Other schemas require qualification.

Before applying any node file, also complete [logging preparation Steps 1–3](procedures/security-logging.md#configure-and-render).
Merge its native system/API audit settings into the appropriate node files alongside image-access/CNI settings,
then return here. Rendering those patches needs charts, not a live cluster. Keep manual ownership;
do not run the Terraform lifecycle for these VMs.

For the compact reference, set `cluster.allowSchedulingOnControlPlanes: true`
in the reviewed control-plane configurations before applying them. Otherwise
provide workers; unschedulable control planes alone cannot run ordinary services.

For each node, inspect disks in maintenance mode and verify `machine.install.disk`
in the configuration intended for that node: [2]

Run from **`<prefix>-tier-0/`**.

```bash
read -r -p "Node IP from its console: " NODE_IP
talosctl get disks --insecure --nodes "$NODE_IP"
```

## Configure and bootstrap

Repeat this block for **each node**, choosing its reviewed control-plane or
worker file. Installation writes to the selected disk. Use `--insecure` only
for initial maintenance-mode configuration on the protected bootstrap network. [2]

Run from **`<prefix>-tier-0/`**.

```bash
read -r -p "Node IP from its console: " NODE_IP
read -r -p "Reviewed machine configuration file: " MACHINE_CONFIG
talosctl apply-config --insecure --nodes "$NODE_IP" --file "$MACHINE_CONFIG"
```

Wait for all nodes to accept configuration and reboot. Stop and resolve failures
before proceeding. Bootstrap **once, on one control-plane node**; this is not an
update command and is not the disaster-recovery procedure. [1]

Run from **`<prefix>-tier-0/`**.

```bash
read -r -p "Control-plane IPs, separated by spaces: " -a CONTROL_PLANES
export TALOSCONFIG="$CLUSTER_DIR/talosconfig"
export KUBECONFIG="$CLUSTER_DIR/kubeconfig"
(
  set -eu
  test "${#CONTROL_PLANES[@]}" -gt 0
  talosctl config endpoint "${CONTROL_PLANES[@]}"
  talosctl config node "${CONTROL_PLANES[0]}"
  talosctl bootstrap --nodes "${CONTROL_PLANES[0]}"
  talosctl kubeconfig "$KUBECONFIG"
  kubectl get nodes -o wide
  kubectl get pods -A
)
```

**Stage 4 checkpoint:** with API access and exported credentials working, return now to
[Step 2](README.md#step-2-establish-the-basic-platform). Complete its interleaved Cilium,
protected logging, storage and remaining add-on sequence. Nodes may remain NotReady before CNI;
do not wait for `talosctl health` or install the full platform a second time here.
After that sequence, run `talosctl health` and the handover checks below.

If health checks time out after bootstrap was accepted, troubleshoot networking,
images, and node state; do not simply run bootstrap again. In a new shell, set
`CLUSTER_DIR`, `TALOSCONFIG`, and `KUBECONFIG` to these existing files. [3]

## Verify and hand over

Continue only when expected nodes are Ready, system pods are healthy, and the
stable API endpoint works from the intended operator network. Save the actual
node allocations and recovery references in project documentation. The manual
route does not generate Terraform state or Ansible inventory; the Terraform
route uses the owning tier's inventory and retains its own state.

For HA, perform the [Proxmox failure checks](../foundation/proxmox/step-1b-cluster-ha.md#prove-failover)
and verify Kubernetes quorum/API availability separately. A VM restart alone
does not prove cluster or application availability.

Tier 0's [Step 2](README.md#step-2-establish-the-basic-platform) already installed the selected
platform and Flux/SOPS. Verify that result here; do not rerun an alternative bootstrap.
The starter Kustomizations
do not install Flux or the named services. The alternative [Flux CLI bootstrap][4]
has commit/push side effects and needs separate review and a single controller owner.
Keep reviewed controller manifests and images for recovery without hosted source control.

Tier 1 selects [Argo CD or Spinnaker](../../01-architecture/20-delivery/02-controllers.md)
separately. Tier 2 consumes scoped delivery or a local controller. Do not copy
Tier 0's controller credentials or automatically bootstrap Flux in other tiers.

Continue with the shared [cluster foundation checklist](procedures/kubernetes.md#cluster-foundation)
for SOPS/bootstrap secrets, storage, cert-manager, ingress, and CloudNativePG
before adding the owning tier's service clients. Return to
[Stage 4, Step 3](README.md#step-3-verify-operation-and-recovery) for the Tier 0 acceptance gate.

## Recovery

Retain cluster secrets, machine configurations, client credentials, release and
schematic records, images, and etcd snapshots outside the cluster. Follow the
matching release's [disaster-recovery procedure][5] and test it before relying on
this cluster. Back up application data separately; etcd is not a volume backup.

## References

Official guidance checked 2026-09-21. Select documentation matching the pinned release.

1. [Talos production notes](https://docs.siderolabs.com/talos/v1.13/getting-started/prodnotes).
2. [Talos on Proxmox](https://docs.siderolabs.com/talos/v1.13/platform-specific-installations/virtualized-platforms/proxmox).
3. [Talos CLI reference](https://docs.siderolabs.com/talos/v1.13/reference/cli).
4. [Flux generic Git bootstrap](https://fluxcd.io/flux/installation/bootstrap/generic-git-server/).
5. [Talos disaster recovery](https://docs.siderolabs.com/talos/v1.13/build-and-extend-talos/cluster-operations-and-maintenance/disaster-recovery).

[4]: https://fluxcd.io/flux/installation/bootstrap/generic-git-server/
[5]: https://docs.siderolabs.com/talos/v1.13/build-and-extend-talos/cluster-operations-and-maintenance/disaster-recovery
