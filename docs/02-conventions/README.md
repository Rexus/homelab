# Conventions

Shared rules and examples for names, tags, guest IDs and network allocations.
Record selected project values in `platform-standards.md`, beside the generated
architecture repository's README; individual guests remain in tier-local IaC inputs.

| Need | Guide |
| --- | --- |
| Assign VM, container or template IDs | [VMID quick reference](vmid-convention.md) |
| Choose individual VM names and Proxmox tags | [Names and tags](proxmox-conventions.md) |
| Choose stable, familiar service endpoints | [Service DNS names](service-dns.md) |
| Plan VLANs, zones, SDN IDs and subnets | [Network plan](network-plan.md) |
| Understand environment-specific inputs | [Environment contract](../08-reference/environment-variables.md) |
| Record local choices and exceptions | [Project standards and records](../04-development/project-documentation.md) |

For implementation, continue with [deployment](../03-deployment/README.md).
For the system model, use [architecture](../01-architecture/README.md).
