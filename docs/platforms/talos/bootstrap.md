# Bootstrap a Talos Kubernetes cluster

Use this procedure for a Tier 0 control cluster or a Tier 1 platform cluster.
Only the owning repo, allocations, credentials, API endpoint, and GitOps path
change. **This is an operator-run bootstrap.** For automated Tier 0 VM creation
and Talos configuration, start with [Talos Terraform](terraform.md) instead;
both routes use the verification and handover steps below. Flux service
directories are starters, not installed services.

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
| Automation alternative | [Tier 0 Terraform](terraform.md) in `terraform/talos/` | Add tier-owned VM and Talos roots when automating |
| GitOps path | `clusters/tier0/` | `clusters/tier1/` |
| Recovery | Independent of higher-tier services | Approved foundation services plus local break-glass inputs |

Before starting, have:

- Prepared [Proxmox hosts](../proxmox/README.md#first-deployment-order), storage,
  guest networks, and optional [HA/SDN](../proxmox/cluster-ha.md).
- A tested [Talos template](../proxmox/talos-template.md), its pinned release
  and schematic, and the matching installer image retained for recovery.
  Obtain its approved ID, title, and source node from the [shared catalog](../proxmox/template-catalog.md).
- Matching `talosctl`, compatible `kubectl`, and the required container images.
- Recorded node IPs, names, VMIDs, API endpoint, and non-overlapping pod/service
  CIDRs. Provide DNS, time, and image access before this cluster exists.

The fast path below uses **DHCP reservations** and the generated default CNI.
For static addressing, generate and review separate per-node configurations;
never apply one static address to every node. For restricted networks, prepare
image mirrors and discovery/network settings using the matching Talos release
documentation before applying configuration. [1][2]

For HA, prepare an independent TCP load balancer for the Kubernetes API on
port 6443, or use a release-supported endpoint design from the production guide.
It must not depend on ingress inside this new cluster. Tier 0 must not depend on
the general Tier 1 edge service for recovery. A single control-plane IP is
acceptable only for a non-HA pilot. Restrict Talos API port 50000 to authorized
operators and cluster traffic; the Kubernetes endpoint is not a Talos endpoint. [1]

## Create VMs

In the Proxmox UI, make **full clones** of the approved, stopped template with
new VMIDs. Do not boot or configure the reusable template itself.

| Setting | Initial project choice |
| --- | --- |
| Control plane | Three VMs on different physical hosts for HA |
| Workers | Capacity for the intended services; normally at least one worker |
| Suggested sizing | Control plane: 2 vCPU, 4 GiB RAM, 32 GiB disk; workers: 2 vCPU, 4 GiB RAM, 40 GiB disk |
| Storage and network | Reviewed datastore and bridge/VNet available on every eligible destination |
| Firmware, CPU, boot order | Preserve the tested template settings and common host CPU baseline |
| Guest agent | Enable only when the recorded image schematic includes the extension |

Sizing here is a starting allocation, not a capacity guarantee. Record the
actual VMIDs and attachments in project inventory. Boot the clones into
maintenance mode and record their console-reported IPs. [2]

Do **not** use the Linux cloud-init VM module or `deploy.sh` to configure Talos.
When replacing manual VM creation with Terraform later, explicitly import and
review existing resources; an empty state is not an adoption plan.

## Generate configuration

For a **new cluster only**, run this from the owning repo root. Prompts keep
project-specific addresses and image references out of the copied command.
Use the exact installer reference matching the template schematic and release,
not the raw disk download URL. [3]

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

For each node, inspect disks in maintenance mode and verify `machine.install.disk`
in the configuration intended for that node: [2]

```bash
read -r -p "Node IP from its console: " NODE_IP
talosctl get disks --insecure --nodes "$NODE_IP"
```

## Configure and bootstrap

Repeat this block for **each node**, choosing its reviewed control-plane or
worker file. Installation writes to the selected disk. Use `--insecure` only
for initial maintenance-mode configuration on the protected bootstrap network. [2]

```bash
read -r -p "Node IP from its console: " NODE_IP
read -r -p "Reviewed machine configuration file: " MACHINE_CONFIG
talosctl apply-config --insecure --nodes "$NODE_IP" --file "$MACHINE_CONFIG"
```

Wait for all nodes to accept configuration and reboot. Stop and resolve failures
before proceeding. Bootstrap **once, on one control-plane node**; this is not an
update command and is not the disaster-recovery procedure. [1]

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
  talosctl health
  talosctl kubeconfig "$KUBECONFIG"
  kubectl get nodes -o wide
  kubectl get pods -A
)
```

If health checks time out after bootstrap was accepted, troubleshoot networking,
images, and node state; do not simply run bootstrap again. In a new shell, set
`CLUSTER_DIR`, `TALOSCONFIG`, and `KUBECONFIG` to these existing files. [3]

## Verify and hand over

Continue only when expected nodes are Ready, system pods are healthy, and the
stable API endpoint works from the intended operator network. Save the actual
node allocations and recovery references in project documentation. The manual
route does not generate Terraform state or Ansible inventory; the Terraform
route uses Tier 0's existing inventory and retains its own state.

For HA, perform the [Proxmox failure checks](../proxmox/cluster-ha.md#prove-failover)
and verify Kubernetes quorum/API availability separately. A VM restart alone
does not prove cluster or application availability.

Then install Flux using its [generic Git bootstrap procedure][4], with the owning
repository and GitOps path from the table above. Review its commit/push actions,
credentials, and controller permissions before running it. The starter
Kustomizations do not install Flux or the named services. Keep reviewed local
controller manifests and images for Tier 0 recovery without hosted source control.

Continue with the shared [cluster foundation checklist](../../paths/application-platform/kubernetes.md#cluster-foundation)
for SOPS/bootstrap secrets, storage, cert-manager, ingress, and CloudNativePG
before adding the owning tier's service clients.

## Recovery

Retain cluster secrets, machine configurations, client credentials, release and
schematic records, images, and etcd snapshots outside the cluster. Follow the
matching release's [disaster-recovery procedure][5] and test it before relying on
this cluster. Back up application data separately; etcd is not a volume backup.

## References

Official guidance checked 2026-09-21. Select documentation matching your pinned release.

1. [Talos production notes](https://docs.siderolabs.com/talos/v1.13/getting-started/prodnotes).
2. [Talos on Proxmox](https://docs.siderolabs.com/talos/v1.13/platform-specific-installations/virtualized-platforms/proxmox).
3. [Talos CLI reference](https://docs.siderolabs.com/talos/v1.13/reference/cli).
4. [Flux generic Git bootstrap](https://fluxcd.io/flux/installation/bootstrap/generic-git-server/).
5. [Talos disaster recovery](https://docs.siderolabs.com/talos/v1.13/build-and-extend-talos/cluster-operations-and-maintenance/disaster-recovery).

[4]: https://fluxcd.io/flux/installation/bootstrap/generic-git-server/
[5]: https://docs.siderolabs.com/talos/v1.13/build-and-extend-talos/cluster-operations-and-maintenance/disaster-recovery
