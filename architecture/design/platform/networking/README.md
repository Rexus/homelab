# Networking and physical attachment

[Up: containing design](../README.md) · Level 2


Guest attachments use logical transports realized over physical switches, NICs and links. Fabric and optional storage transport share equipment only as the selected site design permits.

This is a mapped overview. Detailed design stays with the following owners; no complete native
subsystem model or runtime verification is claimed.

| Explore | Existing owner |
| --- | --- |
| Networking design | [05-networking](../../../../docs/01-architecture/05-networking/README.md) |
| Host network realization | [proxmox](../../../../docs/03-deployment/foundation/proxmox/network.md) |
| Selected network examples | [terraform](../../../../tier-2/terraform/common.tfvars.example) |

[Provider contracts](../contracts.sysml) connect this area to the
[software-intake consumer](../../software-intake/README.md).

<!-- BEGIN DESIGN CONTEXT -->
## Connected views

[Owning documentation](../../../../docs/01-architecture/05-networking/README.md).

Mapped provider design. Native concerns shown here belong to supported intake consumers; direct provider goals, guardrails and allocations remain with the documented owner.
<!-- END DESIGN CONTEXT -->
