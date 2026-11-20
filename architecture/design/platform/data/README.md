# Storage and persistence

[Up: containing design](../README.md) · Level 2


Storage services provide virtual disks backed by equipment or a selected storage service. Disposable cache objects, durable service state and independent recovery have different obligations.

This is a mapped overview. Detailed design stays with the following owners; no complete native
subsystem model or runtime verification is claimed.

| Explore | Existing owner |
| --- | --- |
| Data design | [06-data](../../../../docs/01-architecture/06-data/README.md) |
| Selected cache disks | [cache](../../../../tier-2/terraform/deployments/cache/terraform.tfvars.example) |
| Platform inputs | [config](../../../../shared/config/platform.tfvars) |

[Provider contracts](../contracts.sysml) connect this area to the
[software-intake consumer](../../software-intake/README.md).

<!-- BEGIN DESIGN CONTEXT -->
## Connected views

[Owning documentation](../../../../docs/01-architecture/06-data/README.md).

Mapped provider design. Native concerns shown here belong to supported intake consumers; direct provider goals, guardrails and allocations remain with the documented owner.
<!-- END DESIGN CONTEXT -->
