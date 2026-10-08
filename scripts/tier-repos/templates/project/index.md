# ${prefix} Documentation

Project records describe this environment; auto-docs explain the reusable
design and tooling. Populate the project records before provisioning.

## Project records

| Start here | Purpose |
| --- | --- |
| [Naming conventions](naming-conventions.md) | VM names, Proxmox tags, VMID ranges, and VLAN conventions |
| [Platform architecture](architecture/README.md) | topology, ownership and shared constraints |
| [Technical domains](architecture/README.md#technical-domains) | selected components, interfaces and alternatives |
| [Deployment](deployment/README.md) | selected stages and cross-repository readiness |
| [Development](development/README.md) | review, testing and upstream adoption |
| [Administration](administration/README.md) | operating procedures and recovery evidence |
| [Recovery runbook](administration/recovery.md) | local recovery inputs, steps, and verification |

Keep selected domain designs, decisions and network policy under
`architecture/`. Put execution procedures in their matching workflow folder.

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
- [Architecture and zone view](auto-docs/architecture/README.md)
- [Network placement](auto-docs/architecture/networking/README.md)
- [Firewall policy](auto-docs/architecture/networking/firewall-policy.md)
- [Deployment commands](auto-docs/reference/repository-scripts.md)
- [Refresh and ownership](auto-docs/development/generated-repositories.md#refresh-and-local-ownership)
