# ${prefix} Documentation

Start with the complete platform, follow a function into its domain, then inspect
the detailed design and selected variant. Project records join this environment's
choices into one design; auto-docs explain reusable patterns and tooling.
Populate the project records before provisioning and keep acceptance evidence in
deployment.

## Project records

| Start here | Purpose |
| --- | --- |
| [Platform architecture](architecture/README.md) | complete intended environment, functions, relationships and boundaries |
| [Runtime relationships](architecture/README.md#runtime-relationships) | how the selected functions cooperate across domains |
| [Technical domains](architecture/README.md#technical-domains) | expanded internal designs and links to detailed records |
| [Selected variants](architecture/README.md#selected-variants) | chosen implementations, required contracts and local alternatives |
| [Naming conventions](naming-conventions.md) | VM names, Proxmox tags, VMID ranges, and VLAN conventions |
| [Deployment](deployment/README.md) | selected stages and cross-repository readiness |
| [Development](development/README.md) | review, testing and upstream adoption |
| [Administration](administration/README.md) | operating procedures and recovery evidence |
| [Recovery runbook](administration/recovery.md) | local recovery inputs, steps, and verification |

Keep selected domain designs, decisions and network policy under
`architecture/`. Each detailed design links to its parent view and the procedure
that establishes it. Put execution procedures in their matching workflow folder;
their stage diagrams explain the path toward the completed architecture.

## Repository guides

Each repository records its selected domain patterns and local deployment,
development, and administration procedures. Cross-repository design belongs here;
service-specific instructions stay beside the owning code.

| Owner | Selected architecture | Local guides |
| --- | --- | --- |
| Tier 0 | [Design](../../${prefix}-tier-0/docs/architecture/README.md) | [Procedures](../../${prefix}-tier-0/docs/README.md) |
| Tier 1 | [Design](../../${prefix}-tier-1/docs/architecture/README.md) | [Procedures](../../${prefix}-tier-1/docs/README.md) |
| Tier 2 | [Design](../../${prefix}-tier-2/docs/architecture/README.md) | [Procedures](../../${prefix}-tier-2/docs/README.md) |
| Shared | [Contract](../../${prefix}-shared/docs/architecture/README.md) | [Procedures](../../${prefix}-shared/docs/README.md) |

## Upstream reference

`auto-docs/` is refreshed from the upstream kit. Do not put local decisions
there; refresh preserves local edits but cannot update those edited files.

- [Guide index](auto-docs/README.md)
- [Whole-platform reference](auto-docs/architecture/README.md)
- [Integrated reference design](auto-docs/architecture/reference-platform.md)
- [Runtime flows](auto-docs/architecture/runtime-flows.md)
- [Variant contracts](auto-docs/architecture/variants.md)
- [Network placement](auto-docs/architecture/networking/README.md)
- [Firewall policy](auto-docs/architecture/networking/firewall-policy.md)
- [Deployment commands](auto-docs/reference/repository-scripts.md)
- [Refresh and ownership](auto-docs/development/generated-repositories.md#refresh-and-local-ownership)
