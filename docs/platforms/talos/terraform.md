# Deploy the Tier 0 Talos cluster

Tier 0 owns the control-cluster VMs, inventory, Talos configuration, bootstrap,
credentials, and state. Shared supplies only approved template references and
size profiles. This workflow creates a **new cluster**, not an adoption or restore.
For manual installation or Tier 1, use the [operator procedure](bootstrap.md).

## Table of contents

- [Prerequisites](#prerequisites)
- [Configure](#configure)
- [Plan and deploy](#plan-and-deploy)
- [Verify and hand over](#verify-and-hand-over)
- [State and lifecycle](#state-and-lifecycle)
- [References](#references)

## Prerequisites

Work from the Tier 0 repository root in Bash on Linux or WSL, using an independent
Tier 0 execution host. Install Terraform, matching `talosctl`, and compatible
`kubectl`. Provider constraints and checksums live in `terraform/talos/`.

- Complete [Proxmox preparation](../proxmox/README.md#first-deployment-order),
  optional [HA](../proxmox/cluster-ha.md), and [Talos template publication](../proxmox/talos-template.md).
- Approve the template ID, title, and source node in the sibling shared
  [catalog](../proxmox/template-catalog.md). Retain the disk and matching installer image.
- Prepare DHCP reservations for each VM's MAC/IP, bootstrap DNS/time, and image
  access. IPs come from inventory; Terraform does not configure DHCP or DNS.
- Provide an independent Kubernetes API endpoint on TCP 6443. For HA, use a
  load balancer targeting the control-plane IPs; it cannot depend on this cluster's
  ingress or Tier 1 services. Permit the operator to reach node Talos APIs on
  TCP 50000 over a protected bootstrap network. [1]
- Review storage/bridge availability on every eligible Proxmox host and choose
  non-overlapping node, pod, and service networks.

The supplied root uses an amd64 NoCloud template with SeaBIOS, `scsi0` installed
as `/dev/sda`, DHCP, and the default Talos CNI. It does not use cloud-init or SSH.
Custom networking, mirrors, firmware, or CNI require reviewed changes in this
tier's root before deployment. Enable the guest agent only if the image includes it. [1]

## Configure

```bash
bash scripts/talos-cluster.sh init
```

Initialization copies missing examples only. Existing files are never overwritten
or merged; add the Talos groups from the inventory example when upgrading.

| File, relative to Tier 0 | Edit or purpose |
| --- | --- |
| `ansible/inventory/hosts.yml` | Logical hosts in `talos_control_plane` and `talos_workers`, both under `talos` |
| `ansible/group_vars/talos.yml` | `platform_host_ips`, matching the external DHCP reservations |
| `terraform/talos/terraform.tfvars` | Cluster endpoint, pinned releases/installer, template selection, VMIDs, MACs, placement, disks, and size selections |
| Sibling shared `config/guest-sizes.json` | Common sizing data, read directly by Tier 0 Terraform |
| Sibling shared `templates/proxmox-catalog.tfvars` | Approved image metadata, loaded by the command |

Every Talos inventory host must have one hardware entry and one fixed IPv4
reservation. The example has three control-plane VMs and one worker; review
capacity and failure domains for your services. Talos names are these inventory
keys; Linux hostname prefix/suffix settings are not applied.

Supply `PROXMOX_VE_ENDPOINT` and `PROXMOX_VE_API_TOKEN` through your protected
shell/runner environment. Use a trusted Proxmox TLS certificate. This command
does not load `.env.local`, Linux `common.tfvars`, or Linux environment overlays.
Talos never runs through the Linux `deploy.sh`/Ansible workflow.

## Plan and deploy

```bash
bash scripts/talos-cluster.sh plan
```

Review every VMID, source template, initial host, disk, MAC, endpoint, and secret
resource before continuing. A failed re-plan removes the saved plan so an older
plan cannot be applied accidentally.

```bash
bash scripts/talos-cluster.sh apply
bash scripts/talos-cluster.sh credentials
```

`apply` requires the saved plan. Terraform clones the VMs, generates cluster
secrets and per-node configurations, applies them through the Talos API, then
bootstraps Kubernetes once on the selected control-plane node. [2]
Initial configuration uses maintenance mode; protect that network from untrusted clients.

| Action | Side effects |
| --- | --- |
| `init` | Seed missing local input files; no infrastructure access |
| `plan` | Initialize providers/local backend, validate, refresh, and save `.terraform/plans/talos.tfplan` |
| `apply` | Apply the reviewed saved plan; remove it after success |
| `credentials` | Export client files and per-node configurations to ignored `secrets/talos/` |

## Verify and hand over

```bash
export TALOSCONFIG="$PWD/secrets/talos/talosconfig"
export KUBECONFIG="$PWD/secrets/talos/kubeconfig"
talosctl health
kubectl get nodes -o wide
kubectl get pods -A
```

Stop on unhealthy nodes or system pods. Confirm the independent API endpoint,
CNI, and [failover checks](../proxmox/cluster-ha.md#prove-failover) before services
depend on this cluster. Terraform completion alone does not prove readiness.

Continue at [Verify and hand over](bootstrap.md#verify-and-hand-over) for Flux
bootstrap against `clusters/tier0/`, then the shared cluster-foundation checklist.
The supplied Flux/service directories remain placeholders, not installed add-ons.
FreeIPA remains on the two dedicated Linux VMs; Keycloak is a later cluster service.

## State and lifecycle

| Artifact | Tier-local path |
| --- | --- |
| Authoritative bootstrap state | `.terraform/state/talos/terraform.tfstate` |
| Provider/module working data | `.terraform/data/talos/` |
| Client credentials and per-node recovery configs | `secrets/talos/` |

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
[Recovery](bootstrap.md#recovery) and the [repository upgrade notes](../../reference/generated-repository-model.md#automation-ownership-upgrade).

## References

Official guidance checked 2026-09-24; select Talos documentation matching your pinned release.

1. [Talos on Proxmox](https://docs.siderolabs.com/talos/v1.13/platform-specific-installations/virtualized-platforms/proxmox).
2. [Talos provider configuration apply](https://github.com/siderolabs/terraform-provider-talos/blob/v0.11.0/docs/resources/machine_configuration_apply.md).
3. [Terraform sensitive data in state](https://developer.hashicorp.com/terraform/language/state/sensitive-data).
