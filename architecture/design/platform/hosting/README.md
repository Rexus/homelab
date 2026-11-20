# Hosting and execution

[Up: containing design](../README.md) · Level 2


Virtual execution supplies compute and guest resources. Physical servers provide the execution backing; software runtimes and equipment remain distinct.

This is a mapped overview. Detailed design stays with the following owners; no complete native
subsystem model or runtime verification is claimed.

| Explore | Existing owner |
| --- | --- |
| Runtime design | [04-hosting](../../../../docs/01-architecture/04-hosting/01-runtime.md) |
| Hosting overview | [04-hosting](../../../../docs/01-architecture/04-hosting/README.md) |
| VM module | [vm](../../../../tier-2/terraform/modules/vm/main.tf) |

Open the [bootstrap foundation reference](../../../views/platform/hosting/bootstrap-reference.svg)
for the existing host design, then return to its goal from the SVG.

The [bootstrap clone use case](../../../use-cases/bootstrap/README.md) references the existing
bootstrap host through [bootstrap.sysml](bootstrap.sysml). It does not assign that host to Proxmox
or add a managed resource; the existing bootstrap guide retains deployment ownership.

[Provider contracts](../contracts.sysml) connect this area to the
[software-intake consumer](../../software-intake/README.md).

<!-- BEGIN DESIGN CONTEXT -->
## Connected views

[Owning documentation](../../../../docs/01-architecture/04-hosting/README.md).

Mapped provider design. Native concerns shown here belong to supported intake consumers; direct provider goals, guardrails and allocations remain with the documented owner.
<!-- END DESIGN CONTEXT -->
