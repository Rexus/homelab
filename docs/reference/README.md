# Reference

Exact inputs and command contracts. Use the [design](../architecture/README.md),
[deployment](../deployment/README.md), [development](../development/README.md), or
[administration](../administration/README.md) guides for an end-to-end task.

Naming and allocation guides are grouped under [Conventions](../conventions/README.md).

| Contract | Reference |
| --- | --- |
| CLI flags, defaults and manual equivalents | [Repository scripts](repository-scripts.md) |
| Deployment-host tools, Ansible runtimes and prechecks | [Control-node tooling](control-node-tooling.md) |
| Cache input locations, storage/tuning and consumer behavior | [Proxy/cache reference](proxy-cache.md) |
| Synthetic log manifests and reconciliation reports | [Logging evidence checker](logging-evidence.md) |
| Tier 0 receiver inputs, files and limits | [Syslog receiver contract](syslog-receiver.md) |
| Producer trust, forwarding, NAS checkpoints and independent backup | [Logging pipeline](logging-pipeline.md) |
| Tier 0 native CA runtime and production bundle | [OpenXPKI inputs](openxpki.md) |
| HSM signing and wrapping timings | [YubiHSM 2 vendor performance](yubihsm-performance.md) |
| Shared defaults and tier-local overrides | [Platform inputs](platform-inputs.md) |
| Guest network attachment fields | [Network inputs](network-inputs.md) |
| Zone/VNet allocations and actual deployment attachments | [Network plan](../conventions/network-plan.md) |
| Approved image references | [Template catalog](template-catalog.md) |
| Template publisher fields, defaults and provider compatibility | [Publication inputs](template-publication.md) |
| VM names, tags and IDs | [Proxmox conventions](../conventions/proxmox-conventions.md) |
| VMID groups, categories and Tier 0 Kubernetes exception | [VMID convention](../conventions/vmid-convention.md) |
| HA menu, affinity and native balancing | [Proxmox HA controls](proxmox-ha.md) |
| Runtime variables | [Environment conventions](environment-variables.md), [example](environment-file-example.md) |
