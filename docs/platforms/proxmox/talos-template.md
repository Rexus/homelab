# Talos template on Proxmox

Tier 0 publishes unconfigured Talos templates for control and workload clusters
across all tiers. Its own first control cluster needs a tested template on Day 0-1.
Use the [template lifecycle](template-lifecycle.md) for publication and CD jobs;
this guide owns Talos-specific image selection and bootstrap boundaries.

## Table of contents

- [Prepare the image](#prepare-the-image)
- [Publish and verify](#publish-and-verify)
- [Cluster bootstrap](#cluster-bootstrap)
- [Updates and recovery](#updates-and-recovery)
- [References](#references)

## Prepare the image

Use [Image Factory](https://factory.talos.dev/) to select a pinned Talos release
and schematic, the **NoCloud** platform, `amd64`, and a standard non-secure-boot
raw disk image. Retain the schematic definition/ID and image verification
material with the recovery bundle. Image Factory separates customization
(the schematic) from the Talos version. [1]

Download and verify `nocloud-amd64.raw.xz` using the matching published
verification material. Unpack it, calculate the `.raw` file's SHA256, and make
the approved image and records available to the Tier 0 execution host. For an
offline custody deployment, use the approved transfer procedure across the air
gap. Record the unpacked hash in `templates/proxmox.yml`; a compressed artifact
checksum cannot verify the unpacked bytes.

The shipped template module uses SeaBIOS, a SCSI boot disk, a serial device,
and no initialization media. Secure Boot/UEFI images require a separately
reviewed firmware and disk configuration; do not substitute them into this
example. Choose a CPU baseline supported by all target hosts. The catalog
exposes CPU, memory, disk, and guest-agent settings. [2]

If enabling `qemu_agent`, include `siderolabs/qemu-guest-agent` in the recorded
schematic. Otherwise leave it disabled. The agent is optional; it does not
provide an SSH or Ansible configuration path. [2]

## Publish and verify

Populate the Talos entry in the Tier 0 catalog with the exact version,
schematic ID, local raw-image path, checksum, unused VMID, and protected network placement.
Use the Tier 0 publisher's `plan` and `apply` commands from the
[local workflow](template-lifecycle.md#local-workflow).

The template must remain unbooted and contain **no** machine configuration,
cluster secrets, node certificates, etcd data, or installed workload state.
Test only disposable full clones. Reject a template captured from an existing
cluster node; rebuilding from approved image bytes is the intended path.

Before promotion, verify a clone can boot, receive its own machine config,
reach only approved services, and complete a disposable cluster bootstrap
and recovery test. Record results alongside the project's allocations and
recovery runbook. Template publication alone is not a successful cluster test.

## Cluster bootstrap

Use [Tier 0 Talos Terraform](../talos/terraform.md) for the control-cluster VMs,
machine configuration, and bootstrap. The [manual Talos procedure](../talos/bootstrap.md)
remains available for Tier 1 or operator-run installation.
The same procedure applies to Tier 1 with different inputs and a separate state owner.

| Responsibility | Tier 0 control-cluster owner |
| --- | --- |
| Base Talos template and publication state | Tier 0 `terraform/templates/` |
| Control-plane/worker clones and network attachments | Tier 0 `terraform/talos/` and local inventory |
| Per-node config, secrets, bootstrap, Talos API lifecycle | Tier 0 `terraform/talos/` and protected recovery inputs |
| Add-ons and Day 2 services after cluster readiness | Tier 0 `clusters/tier0/` |

NoCloud can consume Talos machine configuration through cloud-init-compatible
media, but that data is **Talos configuration**, not ordinary cloud-init users
or shell commands. Generate it for each clone, never for the reusable template.
The existing Linux `vm` module injects Linux user settings and is not a complete
Talos bootstrap module. Do not put Talos nodes into `template_refresh_builders`
or `immutable_template_builders`. [3]

Keep cluster secrets and machine configuration in ignored secret storage with
an offline recovery copy, not the template catalog or CI artifacts. Prepare
the required installer/container images, cluster networking, DNS/time, and
bootstrap tools before bringing up nodes. Retain local recovery copies so an
image factory, registry, hosted source control, or inventory UI is not required
to restore Tier 0. For an offline cluster, all required artifacts and services
must remain available inside custody without a connected path.

## Updates and recovery

Publish each new Talos release/schematic as a new template candidate. Clone
creation then uses the approved revision; existing nodes continue running their
current version. Their Talos upgrade and Kubernetes upgrade procedures are
separate, version-compatible, reviewed operations. Retain compatible installer
artifacts and the previous template for recovery. [4]

Keep template state, source images, provider/tool binaries, the Tier 0 and shared
checkouts, and cluster recovery material outside the cluster being recovered.
The local publication path must remain usable when the cluster and its CI
service are both unavailable.

## References

1. [Talos Image Factory](https://docs.siderolabs.com/talos/v1.12/learn-more/image-factory), accessed 2026-09-17.
2. [Talos on Proxmox](https://docs.siderolabs.com/talos/v1.12/platform-specific-installations/virtualized-platforms/proxmox), accessed 2026-09-17.
3. [Talos NoCloud configuration](https://docs.siderolabs.com/talos/v1.12/platform-specific-installations/cloud-platforms/nocloud), accessed 2026-09-17.
4. [Talos upgrades](https://docs.siderolabs.com/talos/v1.12/configure-your-talos-cluster/lifecycle-management/upgrading-talos), accessed 2026-09-17.
